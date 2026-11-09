"""Auto-label failures per CLAUDE.md rules; unlabeled stays null.

Precedence: flaky (DISABLED issue) > flaky (rerun) > infra (log patterns) > regression_strong / regression_weak.
Runs newer than RECENT_DAYS stay unlabeled (reruns / fixes may still come).
Usage: python -m collect.label
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collect.github_logs import FAILED, ROOT, gh_get, gh_pages, read_log

RECENT_DAYS = 3
FIX_WINDOW_DAYS = 14  # look for a fixing commit this long after the failure
MAX_LATER_RUNS = 20
REGION_LINES = 30  # lines before each ##[error] that form the failure region

CONFIDENCE = {"disabled_issue": "high", "rerun": "medium", "infra": "medium",
              "regression_strong": "medium", "regression_weak": "low"}

# (category, name, regex) -- matched against the failure region only, not the whole log
INFRA = [(c, n, re.compile(p, re.I)) for c, n, p in [
    ("timeout", "job_max_time", r"exceeded the maximum execution time"),
    ("timeout", "operation_canceled", r"##\[error\]The operation was canceled"),
    ("network", "dns", r"Could not resolve host|Temporary failure in name resolution|getaddrinfo|ENOTFOUND|EAI_AGAIN"),
    ("network", "connection", r"Connection (reset by peer|refused|timed out)|ECONNRESET|ETIMEDOUT|ECONNREFUSED"
                              r"|Network is unreachable|connection failed|read operation timed out"
                              r"|TLS handshake timeout|RemoteDisconnected|ReadTimeoutError"),
    ("network", "http_5xx", r"(Unexpected HTTP response|returned error|HTTP Error|status code):? *50[0234]\b"
                            r"|\b50[234] (Bad Gateway|Service Unavailable|Gateway Time-?out)"),
    ("runner_disk", "disk_full", r"No space left on device|ENOSPC|disk quota exceeded"),
    ("runner_disk", "runner_lost", r"runner has received a shutdown signal|lost communication with the server"
                                   r"|hosted runner encountered an error"),
    ("runner_disk", "oom", r"Cannot allocate memory|Killed signal terminated program|\bout of memory\b|exit code 137"),
    ("dependency_download", "fetch_failed", r"E: Failed to fetch|Hash Sum mismatch|Failed to download|Download failed"
                                            r"|could not download|Unable to download"),
    ("dependency_download", "truncated_archive", r"gzip: stdin: unexpected end of file|tar: Error is not recoverable"
                                                 r"|Unexpected end of (archive|file)"),
    ("dependency_download", "rate_limited", r"rate limit exceeded|toomanyrequests|429 Too Many Requests"),
]]

PYTEST_FAIL = re.compile(r"FAILED\s+(?:\[[\d.]+s\]\s+)?\S+?\.py::(?:(\w+)::)?(\w+)")
UNITTEST_FAIL = re.compile(r"(?:FAIL|ERROR): (\w+) \(([\w.]+)\)")

TS = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\[[0-9;]+m")
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
HEX = re.compile(r"\b0x[0-9a-f]+\b|\b(?=[0-9a-f]*\d)[0-9a-f]{7,64}\b", re.I)
PATH = re.compile(r"(?:[A-Za-z]:)?[\w.+~-]*(?:[\\/][\w.+~-]+)+")
NUM = re.compile(r"\d+")
ERRLINE = re.compile(r"error|fail|fatal|traceback|exception|panic|assert|undefined reference|timed out", re.I)
GENERIC = re.compile(r"exit code <n>|^##\[(end)?group\]")


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def strip(line: str) -> str:
    return ANSI.sub("", TS.sub("", line))


def normalize(line: str) -> str:
    s = re.sub(r"^\s*(error|fatal)\s*:\s*", "", strip(line).replace("##[error]", ""), flags=re.I)
    s = UUID.sub("<uuid>", s)
    s = HEX.sub("<hex>", s)
    s = PATH.sub(lambda m: re.split(r"[\\/]", m.group(0))[-1], s)
    s = NUM.sub("<n>", s)
    return " ".join(s.lower().split())


def failure_region(lines: list[str]) -> list[str]:
    """REGION_LINES before (and including) each ##[error] line; last 50 lines if none.
    Step headers (##[group]Run ... ##[endgroup]: script + echoed inputs) are dropped first."""
    out, in_header = [], False
    for l in lines:
        s = strip(l)
        if s.startswith("##[group]Run "):
            in_header = True
        elif in_header and s.startswith("##[endgroup]"):
            in_header = False
        elif not in_header:
            out.append(l)
    lines = out
    idx = [i for i, l in enumerate(lines) if "##[error]" in l]
    if not idx:
        return lines[-50:]
    keep = sorted({j for i in idx for j in range(max(0, i - REGION_LINES), i + 1)})
    return [lines[j] for j in keep]


def infra_match(rec: dict, region: list[str]) -> tuple[str, str, str] | None:
    if rec["job_conclusion"] == "timed_out":
        return "timeout", "job_timed_out", "job conclusion: timed_out"
    for line in region:
        s = strip(line)
        for cat, name, rx in INFRA:
            if rx.search(s):
                return cat, name, s.strip()
    return None


def signature(rec: dict, region: list[str]) -> str:
    """First normalized error line of the region (later lines vary across matrix platforms);
    failed step names as fallback."""
    for line in region:
        n = normalize(line)
        if ERRLINE.search(strip(line)) and not GENERIC.search(n):
            return n
    return "steps:" + "|".join(normalize(s) for s in rec["failed_steps"])


def failing_tests(text: str) -> set[tuple[str, str]]:
    """(test_name, class_name) pairs from pytest / unittest failure lines."""
    out = {(m.group(2), m.group(1)) for m in PYTEST_FAIL.finditer(text) if m.group(1)}
    out |= {(m.group(1), m.group(2).rsplit(".", 1)[-1]) for m in UNITTEST_FAIL.finditer(text)}
    return out


def disabled_issue(rec: dict, text: str, issues: dict) -> int | None:
    t = ts(rec["job_started_at"])
    for key in failing_tests(text):
        for iss in issues.get(key, []):
            if ts(iss["created_at"]) <= t and (iss["closed_at"] is None or ts(iss["closed_at"]) > t):
                return iss["number"]
    return None


def attempt_jobs(repo: str, run_id: int, n: int) -> dict[str, str]:
    return {j["name"]: j["conclusion"]
            for j in gh_pages(f"/repos/{repo}/actions/runs/{run_id}/attempts/{n}/jobs", "jobs")}


def flaky_rerun(rec: dict) -> int | None:
    """Later attempt of the same run, same SHA, where the same job passed -> that attempt number."""
    for m in range(rec["attempt"] + 1, rec["max_attempt"] + 1):
        att = gh_get(f"/repos/{rec['repo']}/actions/runs/{rec['run_id']}/attempts/{m}")
        if att and att["head_sha"] == rec["head_sha"] and \
                attempt_jobs(rec["repo"], rec["run_id"], m).get(rec["job_name"]) == "success":
            return m
    return None


def failed_in_other_attempt(rec: dict) -> bool:
    return any(attempt_jobs(rec["repo"], rec["run_id"], m).get(rec["job_name"]) in FAILED
               for m in range(1, rec["max_attempt"] + 1) if m != rec["attempt"])


def branch_runs(rec: dict, start: datetime, end: datetime) -> list[dict]:
    """Completed runs of the same workflow / branch / head repo in [start, end], other commits, oldest first."""
    closed = end < datetime.now(timezone.utc) - timedelta(days=1)
    runs = gh_pages(f"/repos/{rec['repo']}/actions/workflows/{rec['workflow_id']}/runs", "workflow_runs",
                    {"branch": rec["head_branch"], "status": "completed",
                     "created": f"{start:%Y-%m-%dT%H:%M:%SZ}..{end:%Y-%m-%dT%H:%M:%SZ}"}, cache=closed)
    return sorted((r for r in runs if r["head_sha"] != rec["head_sha"]
                   and (r.get("head_repository") or {}).get("full_name") == rec["head_repo"]),
                  key=lambda r: r["created_at"])


def first_attempt_conclusion(rec: dict, run: dict) -> str | None:
    # first attempt only: a commit that needed a rerun to pass is not clean evidence
    return attempt_jobs(rec["repo"], run["id"], 1).get(rec["job_name"])


def prev_commit_failed(rec: dict) -> bool:
    """The closest earlier commit on the branch that ran this job also failed it."""
    t = ts(rec["run_created_at"])
    earlier = [r for r in branch_runs(rec, t - timedelta(days=FIX_WINDOW_DAYS), t) if ts(r["created_at"]) < t]
    for r in reversed(earlier[-MAX_LATER_RUNS:]):
        c = first_attempt_conclusion(rec, r)
        if c is not None:
            return c in FAILED
    return False


def fix_diff(repo: str, bad: str, good: str) -> dict:
    """Commits and files changed going from bad -> good. For a force-pushed branch (diverged),
    the 3-dot compare is relative to the merge base, so diff both sides against it."""
    cmp = gh_get(f"/repos/{repo}/compare/{bad}...{good}") or {}
    commits, files = cmp.get("commits", []), cmp.get("files", [])
    if cmp.get("status") == "diverged":
        old = gh_get(f"/repos/{repo}/compare/{cmp['merge_base_commit']['sha']}...{bad}") or {}
        old_shas = {c["sha"] for c in old.get("commits", [])}
        old_blobs = {f["filename"]: f["sha"] for f in old.get("files", [])}
        commits = [c for c in commits if c["sha"] not in old_shas]
        new_blobs = {f["filename"]: f["sha"] for f in files}
        names = {n for n in old_blobs.keys() | new_blobs.keys() if old_blobs.get(n) != new_blobs.get(n)}
        files = [{"filename": n} for n in sorted(names)]
    return {"compare_status": cmp.get("status"), "fix_commits": [c["sha"] for c in commits],
            "touched_files": [f["filename"] for f in files]}


def find_fix(rec: dict) -> tuple[dict | None, int]:
    """First later commit on the branch where the job passes, and how many later commits failed it first."""
    t = ts(rec["run_created_at"])
    later = [r for r in branch_runs(rec, t, t + timedelta(days=FIX_WINDOW_DAYS)) if ts(r["created_at"]) > t]
    seen_failed: set[str] = set()
    for r in later[:MAX_LATER_RUNS]:
        c = first_attempt_conclusion(rec, r)
        if c == "success":
            return {"fix_sha": r["head_sha"], "fix_run_id": r["id"],
                    **fix_diff(rec["repo"], rec["head_sha"], r["head_sha"])}, len(seen_failed)
        if c in FAILED:
            seen_failed.add(r["head_sha"])
    return None, len(seen_failed)


def label(rec: dict, issues: dict, now: datetime) -> dict:
    text = read_log(rec["log_path"]) if rec["log_path"] else ""
    region = failure_region(text.splitlines())
    infra = infra_match(rec, region)
    rec = {**rec, "incident_id": hashlib.sha1(f"{rec['run_id']}\n{signature(rec, region)}".encode()).hexdigest()[:12],
           "infra_match": infra and {"category": infra[0], "pattern": infra[1], "line": infra[2][:300]},
           "label": None, "label_source": None, "confidence": None, "label_meta": None}

    def lab(label: str, source: str, meta: dict) -> dict:
        return {**rec, "label": label, "label_source": source, "confidence": CONFIDENCE[source], "label_meta": meta}

    if ts(rec["run_created_at"]) > now - timedelta(days=RECENT_DAYS):
        return {**rec, "label_source": "too_recent"}
    if rec["repo"] == "pytorch/pytorch" and (n := disabled_issue(rec, text, issues)):
        return lab("flaky", "disabled_issue", {"issue": n})
    if m := flaky_rerun(rec):
        return lab("flaky", "rerun", {"passed_attempt": m})
    if infra:
        return lab("infra", "infra", {"category": infra[0], "pattern": infra[1]})
    fix, later_failed = find_fix(rec)
    if fix:
        prev_failed = prev_commit_failed(rec)
        rerun_failed = failed_in_other_attempt(rec)
        strong = later_failed > 0 or prev_failed or rerun_failed
        kind = "regression_strong" if strong else "regression_weak"
        return lab(kind, kind, {**fix, "later_failed_commits": later_failed,
                                "prev_commit_failed": prev_failed, "rerun_failed": rerun_failed})
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", type=Path, default=ROOT / "data/processed/failures.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/failures_labeled.jsonl")
    ap.add_argument("--disabled", type=Path, default=ROOT / "data/processed/pytorch_disabled.jsonl")
    ap.add_argument("--repos", nargs="*", help="only label these repos")
    ap.add_argument("--examples", type=int, default=5, help="infra example matches to print per pattern")
    args = ap.parse_args()

    issues: dict[tuple[str, str], list[dict]] = {}
    if args.disabled.exists():
        for line in args.disabled.open():
            i = json.loads(line)
            issues.setdefault((i["test_name"], i["test_class"].rsplit(".", 1)[-1]), []).append(i)

    recs = [json.loads(l) for l in args.inp.open()]
    if args.repos:
        recs = [r for r in recs if r["repo"] in args.repos]
    now = datetime.now(timezone.utc)
    out = []
    with args.out.open("w") as f:
        for i, r in enumerate(recs, 1):
            out.append(label(r, issues, now))
            f.write(json.dumps(out[-1]) + "\n")
            print(f"labeled {i}/{len(recs)}", end="\r", file=sys.stderr)
    print(file=sys.stderr)

    print("== infra pattern matches (all jobs, before precedence / recency) ==")
    by_pat = defaultdict(list)
    for r in out:
        if r["infra_match"]:
            by_pat[(r["infra_match"]["category"], r["infra_match"]["pattern"])].append(r)
    for (cat, pat), rs in sorted(by_pat.items()):
        print(f"-- {cat}/{pat}: {len(rs)} jobs")
        for r in rs[:args.examples]:
            print(f"   [{r['label'] or r['label_source'] or '-'}] {r['job_name'][:40]:40} | {r['infra_match']['line'][:140]}")

    def key(r: dict) -> str:
        return r["label"] or f"unlabeled ({r['label_source'] or 'no rule'})"

    print("\n== counts ==")
    for repo in sorted({r["repo"] for r in out}):
        rs = [r for r in out if r["repo"] == repo]
        jobs = Counter(key(r) for r in rs)
        inc_labels = defaultdict(set)
        for r in rs:
            inc_labels[r["incident_id"]].add(key(r))
        incidents = Counter(l for ls in inc_labels.values() for l in ls)
        print(f"{repo}: {len(rs)} jobs, {len(inc_labels)} incidents "
              f"({sum(len(ls) > 1 for ls in inc_labels.values())} with mixed labels, counted under each)")
        print(f"  {'label':32} {'jobs':>5} {'incidents':>9}")
        for k in sorted(jobs):
            print(f"  {k:32} {jobs[k]:5} {incidents[k]:9}")


if __name__ == "__main__":
    main()
