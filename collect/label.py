"""Auto-label failures per CLAUDE.md rules; unlabeled stays null.

Precedence: flaky (DISABLED issue) > infra (log patterns) > flaky (rerun) > regression_strong > regression_weak.
DISABLED issues count only if opened by pytorch-bot, their Platforms match the job, and the job started in
[created - 7d, created + 1h] or [reopened - 7d, reopened + 1h] (pytorch skips the test once the issue is open,
so the flaky failures that trigger the bot come before it).
Runs newer than RECENT_DAYS stay unlabeled (reruns / fixes may still come).
Usage: python -m collect.label
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path
from typing import Iterator

import requests

from collect import testlog
from collect.github_logs import FAILED, ROOT, gh_get, gh_pages, read_log
from collect.testlog import strip

RECENT_DAYS = 3
FIX_WINDOW_DAYS = 14  # look for a fixing commit this long after the failure
MAX_LATER_RUNS = 20
REGION_LINES = 30  # lines before each ##[error] that form the failure region

# jobs that only report other jobs' status: their failure duplicates the real incident -> not labeled
AGGREGATOR_STEP = "Decide whether the needed jobs succeeded or failed"  # re-actors/alls-green
META_JOBS = {"apache/arrow": {"PR Workflow bot"}}  # bot workflows, not CI test/build failures

# fix relevance: a regression fix should touch a file sharing a module token with the failing tests / error lines
FIX_STOP = set("""
error errors fail failed failure failures fatal warning test tests testing unittest unittests timeout timed exit code
process completed running run runs line lines file files src source sources lib libs include includes cpp python
the and for with from not none true false assert assertion assertionerror exception traceback most recent call last
build builds building make ninja cmake cmakelists lists txt main master common internal util utils core tool tools
script scripts github workflows workflow yml yaml json toml cfg ini docs doc readme changelog hpp cc py rs go js ts md
rst ci home runner work usr local opt var tmp users bin share site packages dist lib64 venv env sec proc passed total
real summary label time following while ctest pytest raise raised expected got value values self args kwargs def
return err out stdout stderr status subcommand stopped job step steps setup install installing check checks type types
mpv avif libavif arrow apache pyarrow pydantic pytest torch pytorch
""".split())
FIX_EXT = {"c", "h", "cc", "cpp", "hpp", "py", "pyi", "pyx", "pxd", "rs", "go", "js", "ts", "md", "rst", "txt", "yml",
           "yaml", "json", "toml", "cfg", "ini", "sh", "cmake", "build", "in", "lock"}
CTEST_FAIL = re.compile(r"\*\*\*(Failed|Timeout|Exception)|\((Failed|Timeout|SEGFAULT|Subprocess aborted|Child aborted)\)")
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

CONFIDENCE = {"disabled_issue": "high", "rerun": "medium", "infra": "medium",
              "regression_strong": "medium", "regression_weak": "low"}

# (category, name, regex) -- matched against the failure region only, not the whole log
# (category, name, regex) -- matched against the failure region only, not the whole log. Case-insensitive phrases
# with word boundaries; error codes / exception class names are case-sensitive whole words ((?-i:...)), so e.g.
# ENOTFOUND does not match inside "ModuleNotFoundError".
INFRA = [(c, n, re.compile(p, re.I)) for c, n, p in [
    ("timeout", "job_max_time", r"\bexceeded the maximum execution time\b"),
    ("timeout", "operation_canceled", r"##\[error\]The operation was canceled\b"),
    ("network", "dns", r"\bCould not resolve host\b|\bTemporary failure in name resolution\b|\bgetaddrinfo\b"
                       r"|\b(?-i:ENOTFOUND|EAI_AGAIN)\b"),
    ("network", "connection", r"\bConnection (reset by peer|refused|timed out)\b|\b(?-i:ECONNRESET|ETIMEDOUT|ECONNREFUSED)\b"
                              r"|\bNetwork is unreachable\b|\bconnection failed\b|\bread operation timed out\b"
                              r"|\bTLS handshake timeout\b|\b(?-i:RemoteDisconnected|ReadTimeoutError)\b"),
    ("network", "ssl", r"\b(?-i:SSLError|SSLEOFError|UNEXPECTED_EOF_WHILE_READING|CERTIFICATE_VERIFY_FAILED)\b"
                       r"|\bMax retries exceeded with url\b"),
    ("network", "http_5xx", r"\b(Unexpected HTTP response|returned error|HTTP Error|status code):? *50[0234]\b"
                            r"|\b50[234] (Bad Gateway|Service Unavailable|Gateway Time-?out)\b"),
    ("runner_disk", "disk_full", r"\bNo space left on device\b|\b(?-i:ENOSPC)\b|\bdisk quota exceeded\b"),
    ("runner_disk", "runner_lost", r"\brunner has received a shutdown signal\b|\blost communication with the server\b"
                                   r"|\bhosted runner encountered an error\b"),
    ("runner_disk", "oom", r"\bCannot allocate memory\b|\bKilled signal terminated program\b|\bout of memory\b"
                           r"|\bexit code 137\b"),
    ("dependency_download", "fetch_failed", r"\bFailed to fetch\b|\bHash Sum mismatch\b|\bFailed to download\b"
                                            r"|\bDownload failed\b|\bcould not download\b|\bUnable to download\b"),
    ("dependency_download", "truncated_archive", r"\bgzip: stdin: unexpected end of file\b"
                                                 r"|\btar: Error is not recoverable\b|\bUnexpected end of (archive|file)\b"),
    ("dependency_download", "rate_limited", r"\brate limit exceeded\b|\b(?-i:toomanyrequests)\b|\b429 Too Many Requests\b"),
]]

DISABLED_BOT = "pytorch-bot[bot]"
DISABLED_BEFORE, DISABLED_AFTER = timedelta(days=7), timedelta(hours=1)
# Semantics of torch/testing/_internal/common_utils.py check_if_enable: a disabled test is skipped if ANY listed
# platform's condition holds (empty list = all). Conditions are runtime flags; approximated from the job name.
# linux = sys.platform == "linux" (true on rocm/xpu linux runners); dynamo is implied by inductor.
PLATFORM_RX = {p: re.compile(rx, re.I) for p, rx in {
    "linux": r"linux", "mac": r"\bmac", "macos": r"\bmac", "win": r"\bwin", "windows": r"\bwin",
    "rocm": r"rocm", "xpu": r"xpu", "asan": r"asan", "dynamo": r"dynamo|inductor", "inductor": r"inductor",
    "slow": r"\bslow\b"}.items()}
# remove_device_and_dtype_suffixes: issue "test_x (TestFoo)" also disables TestFooCUDA.test_x_cuda_float32
DEVICE_SUFFIXES = {"cpu", "cuda", "meta", "mps", "xpu", "hpu", "lazy", "mtia", "privateuse1"}
DTYPE_SUFFIXES = {"float16", "float32", "float64", "bfloat16", "complex32", "complex64", "complex128",
                  "int8", "int16", "int32", "int64", "uint8", "bool"}

UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
HEX = re.compile(r"\b0x[0-9a-f]+\b|\b(?=[0-9a-f]*\d)[0-9a-f]{7,64}\b", re.I)
PATH = re.compile(r"(?:[A-Za-z]:)?[\w.+~-]*(?:[\\/][\w.+~-]+)+")
NUM = re.compile(r"\d+")
ERRLINE = re.compile(r"error|fail|fatal|traceback|exception|panic|assert|undefined reference|timed out", re.I)
GENERIC = re.compile(r"exit code <n>|^##\[(end)?group\]")


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


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


def failing_tests(text: str, final_only: bool = True) -> dict[tuple[str, str], str]:
    """(test_name, class_name) -> first failure log line. pytorch reruns failing tests inside the job;
    final_only drops tests with any PASSED status line in the job (they did not cause this job's failure)."""
    lines = text.splitlines()
    out = {}
    for key, evs in testlog.scan(lines).items():
        if testlog.failed(evs) and not (final_only and testlog.passed(evs)):
            out[key] = strip(lines[next(i for i, st, _ in evs if st == "fail")])
    return out


def platform_match(platforms: list[str], job_name: str) -> bool:
    valid = [p for p in platforms if p in PLATFORM_RX]  # unknown platforms are ignored, as in check_if_enable
    return not valid or any(PLATFORM_RX[p].search(job_name) for p in valid)


def sanitize_test(name: str) -> str:
    parts = name.split("_")
    if parts[-1] in DTYPE_SUFFIXES:
        return "_".join(parts[:-2] if len(parts) > 1 and parts[-2] in DEVICE_SUFFIXES else parts[:-1])
    return name


def issue_candidates(test: str, cls: str, issues: dict) -> list[dict]:
    """Bot issues whose title names this test, matched like check_if_enable (class prefix, sanitized name)."""
    cands = issues.get(test, []) + (issues.get(sanitize_test(test), []) if sanitize_test(test) != test else [])
    return [i for i in cands if i["author"] == DISABLED_BOT and cls.startswith(i["test_class"].rsplit(".", 1)[-1])]


def reopen_times(number: int) -> list[datetime]:
    out, page = [], 1
    while True:
        evs = gh_get(f"/repos/pytorch/pytorch/issues/{number}/events", {"per_page": 100, "page": page}) or []
        out += [ts(e["created_at"]) for e in evs if e["event"] == "reopened"]
        if len(evs) < 100:
            return out
        page += 1


def disabled_for_test(rec: dict, test: str, cls: str, line: str, issues: dict) -> dict | None:
    """Bot DISABLED issue for this test, on a matching platform, created or reopened shortly after the job."""
    t = ts(rec["job_started_at"])

    def in_window(anchor: datetime) -> bool:
        return anchor - DISABLED_BEFORE <= t <= anchor + DISABLED_AFTER

    for iss in issue_candidates(test, cls, issues):
        if not platform_match(iss["platforms"], rec["job_name"]):
            continue
        anchor = "created" if in_window(ts(iss["created_at"])) else \
                 "reopened" if any(in_window(r) for r in reopen_times(iss["number"])) else None
        if anchor:
            return {"issue": iss["number"], "title": iss["title"], "platforms": iss["platforms"],
                    "anchor": anchor, "log_line": line[:300]}
    return None


def disabled_issue(rec: dict, text: str, issues: dict, final_only: bool = True) -> dict | None:
    for (test, cls), line in failing_tests(text, final_only).items():
        if d := disabled_for_test(rec, test, cls, line, issues):
            return d
    return None


def test_failure_records(rec: dict, text: str, issues: dict) -> list[dict]:
    """One record per test that failed in this (failed) pytorch job with no PASSED status line, in the same
    format as pytorch_inner_flaky.py records. label is test-level evidence only (a DISABLED match);
    the job's own label is kept as job_label."""
    lines = text.splitlines()
    out = []
    for (test, cls), evs in testlog.scan(lines).items():
        if not testlog.failed(evs) or testlog.passed(evs):
            continue
        first_fail = next(i for i, st, _ in evs if st == "fail")
        fail_line = strip(lines[first_fail])
        try:
            d = None if rec["label_source"] == "too_recent" else disabled_for_test(rec, test, cls, fail_line, issues)
        except requests.RequestException:
            d = None
        out.append({
            "repo": rec["repo"], "workflow_name": rec["workflow_name"], "run_id": rec["run_id"],
            "attempt": rec["attempt"], "job_id": rec["job_id"], "job_name": rec["job_name"],
            "job_conclusion": rec["job_conclusion"], "inner_flaky": False,
            "head_sha": rec["head_sha"], "head_branch": rec["head_branch"],
            "job_started_at": rec["job_started_at"], "html_url": rec["html_url"], "log_path": rec["log_path"],
            "test_name": test, "test_class": cls, "fail_line": fail_line[:300], "pass_line": None,
            "traceback": testlog.traceback_chunk(lines, (test, cls), evs),
            "label": d and "flaky", "label_source": d and "disabled_issue", "confidence": d and "high",
            "issue": d and d["issue"], "issue_test_match": bool(d),
            "job_label": rec["label"], "job_label_source": rec["label_source"], "incident_id": rec["incident_id"],
        })
    return out


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


def branch_runs(rec: dict, forward: bool) -> Iterator[dict]:
    """Completed runs of the same workflow / branch / head repo on other commits, moving away from the failure
    (forward: later, oldest first; else earlier, newest first). Queried one day at a time because the list API
    returns at most 1000 runs (newest first) per query, which would drop the closest runs on busy branches."""
    t = ts(rec["run_created_at"])
    path = f"/repos/{rec['repo']}/actions/workflows/{rec['workflow_id']}/runs"

    def params(start: datetime, end: datetime) -> dict:
        return {"branch": rec["head_branch"], "status": "completed",
                "created": f"{start:%Y-%m-%dT%H:%M:%SZ}..{end:%Y-%m-%dT%H:%M:%SZ}"}

    def closed(end: datetime) -> bool:
        return end < datetime.now(timezone.utc) - timedelta(days=1)

    def ordered(runs) -> list[dict]:
        return sorted((r for r in runs if r["head_sha"] != rec["head_sha"]
                       and (r.get("head_repository") or {}).get("full_name") == rec["head_repo"]
                       and (ts(r["created_at"]) > t if forward else ts(r["created_at"]) < t)),
                      key=lambda r: r["created_at"], reverse=not forward)

    # whole window in one request when it fits in one page (most branches); else day by day
    window = (t, t + timedelta(days=FIX_WINDOW_DAYS)) if forward else (t - timedelta(days=FIX_WINDOW_DAYS), t)
    first = gh_get(path, {**params(*window), "per_page": 100, "page": 1}, closed(window[1]))
    if first is not None and first["total_count"] <= 100:
        yield from ordered(first["workflow_runs"])
        return
    for d in range(FIX_WINDOW_DAYS):
        start, end = (t + timedelta(days=d), t + timedelta(days=d + 1)) if forward else \
                     (t - timedelta(days=d + 1), t - timedelta(days=d))
        yield from ordered(gh_pages(path, "workflow_runs", params(start, end), cache=closed(end)))


def first_attempt_conclusion(rec: dict, run: dict) -> str | None:
    # first attempt only: a commit that needed a rerun to pass is not clean evidence
    return attempt_jobs(rec["repo"], run["id"], 1).get(rec["job_name"])


def prev_commit_failed(rec: dict) -> bool:
    """The closest earlier commit on the branch that ran this job also failed it."""
    for r in islice(branch_runs(rec, forward=False), MAX_LATER_RUNS):
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
    seen_failed: set[str] = set()
    for r in islice(branch_runs(rec, forward=True), MAX_LATER_RUNS):
        c = first_attempt_conclusion(rec, r)
        if c == "success":
            return {"fix_sha": r["head_sha"], "fix_run_id": r["id"],
                    **fix_diff(rec["repo"], rec["head_sha"], r["head_sha"])}, len(seen_failed)
        if c in FAILED:
            seen_failed.add(r["head_sha"])
    return None, len(seen_failed)


def is_aggregator(rec: dict) -> bool:
    return AGGREGATOR_STEP in rec["failed_steps"] or rec["job_name"] in META_JOBS.get(rec["repo"], ())


def module_tokens(s: str) -> set[str]:
    out = set()
    for part in re.split(r"[^A-Za-z0-9]+", s):
        for t in CAMEL.split(part):
            t = t.lower()
            if len(t) >= 3 and not t.isdigit() and t not in FIX_STOP and t not in FIX_EXT:
                out.add(t)
    return out


def fix_relevant(text: str, files: list[str]) -> bool | None:
    """True if a touched file shares a module token with the failing tests / error lines of the failure region,
    False if both sides have tokens but none shared, None if undecidable. (The whole region is not used:
    e.g. ctest's label time summary lists every module in every run.)"""
    lines = text.splitlines()
    fail = set()
    for l in failure_region(lines):
        s = strip(l)
        if (ERRLINE.search(s) or CTEST_FAIL.search(s)) and "label time summary" not in s.lower():
            fail |= module_tokens(s)
    for (test, cls), evs in testlog.scan(lines).items():
        if testlog.failed(evs) and not testlog.passed(evs):
            fail |= module_tokens(test) | module_tokens(cls)
    fix = set().union(*(module_tokens(f) for f in files)) if files else set()
    return None if not fail or not fix else bool(fail & fix)


def refresh_derived(rec: dict) -> dict:
    """Re-apply the API-free rules (aggregator exclusion, fix_relevant) to an already labeled record."""
    if is_aggregator(rec):
        return {**rec, "label": None, "label_source": "aggregator", "confidence": None, "label_meta": None}
    if (rec["label"] or "").startswith("regression") and rec["log_path"]:
        meta = {**rec["label_meta"], "fix_relevant": fix_relevant(read_log(rec["log_path"]),
                                                                  rec["label_meta"]["touched_files"])}
        return {**rec, "label_meta": meta}
    return rec


def relabel_infra_changed(recs: list[dict], issues: dict, now: datetime) -> list[dict]:
    """After an INFRA pattern change: recompute infra_match (API-free); jobs whose infra status flips are fully
    re-labeled with label() (cached API work), others only get the new infra_match. Prints a before/after audit."""
    before, after = Counter(), Counter()
    moved: dict[tuple[str, str], list[str]] = defaultdict(list)
    out, n_relabel = [], 0
    for i, r in enumerate(recs, 1):
        old = r["infra_match"]
        new = None
        if r["log_path"]:
            m = infra_match(r, failure_region(read_log(r["log_path"]).splitlines()))
            new = m and {"category": m[0], "pattern": m[1], "line": m[2][:300]}
        po, pn = old and old["pattern"], new and new["pattern"]
        before[po] += 1
        after[pn] += 1
        if po != pn:
            moved[(str(po), str(pn))].append(f"{r['repo']} | {r['job_name'][:40]} | {((new or old)['line'])[:110]}")
        if (old is None) != (new is None) and r["label_source"] != "aggregator":
            r = refresh_derived(label(r, issues, now))
            n_relabel += 1
        else:
            r = {**r, "infra_match": new}
            if r["label_source"] == "infra" and new:
                r["label_meta"] = {"category": new["category"], "pattern": new["pattern"]}
        out.append(r)
        if i % 1000 == 0:
            print(f"{datetime.now():%H:%M:%S} audited {i}/{len(recs)}, re-labeled {n_relabel}", file=sys.stderr, flush=True)
    print("== infra pattern audit: jobs per first-matching pattern ==")
    print(f"  {'pattern':20} {'before':>7} {'after':>7}")
    for pat in sorted(set(before) | set(after), key=str):
        print(f"  {str(pat):20} {before[pat]:7} {after[pat]:7}")
    print(f"\n== changed matches (before -> after), 3 examples each; {n_relabel} jobs fully re-labeled ==")
    for (po, pn), ex in sorted(moved.items()):
        print(f"-- {po} -> {pn}: {len(ex)} jobs")
        for e in ex[:3]:
            print(f"     {e}")
    return out


def label(rec: dict, issues: dict, now: datetime) -> dict:
    text = read_log(rec["log_path"]) if rec["log_path"] else ""
    region = failure_region(text.splitlines())
    infra = infra_match(rec, region)
    rec = {**rec, "incident_id": hashlib.sha1(f"{rec['run_id']}\n{signature(rec, region)}".encode()).hexdigest()[:12],
           "infra_match": infra and {"category": infra[0], "pattern": infra[1], "line": infra[2][:300]},
           "label": None, "label_source": None, "confidence": None, "label_meta": None}

    def lab(label: str, source: str, meta: dict) -> dict:
        return {**rec, "label": label, "label_source": source, "confidence": CONFIDENCE[source], "label_meta": meta}

    if is_aggregator(rec):
        return {**rec, "label_source": "aggregator"}
    if ts(rec["run_created_at"]) > now - timedelta(days=RECENT_DAYS):
        return {**rec, "label_source": "too_recent"}
    try:
        return label_rules(rec, text, issues, infra, lab)
    except requests.RequestException as e:  # persistent GitHub error for this record: leave it unlabeled
        print(f"  {datetime.now():%H:%M:%S} api_error job {rec['job_id']}: {e}", file=sys.stderr, flush=True)
        return {**rec, "label_source": "api_error", "label_meta": {"error": str(e)[:300]}}


def label_rules(rec: dict, text: str, issues: dict, infra, lab) -> dict:
    if rec["repo"] == "pytorch/pytorch" and (d := disabled_issue(rec, text, issues)):
        return lab("flaky", "disabled_issue", d)
    if infra:
        return lab("infra", "infra", {"category": infra[0], "pattern": infra[1]})
    if m := flaky_rerun(rec):
        return lab("flaky", "rerun", {"passed_attempt": m})
    fix, later_failed = find_fix(rec)
    if fix:
        prev_failed = prev_commit_failed(rec)
        rerun_failed = failed_in_other_attempt(rec)
        strong = later_failed > 0 or prev_failed or rerun_failed
        kind = "regression_strong" if strong else "regression_weak"
        return lab(kind, kind, {**fix, "later_failed_commits": later_failed,
                                "prev_commit_failed": prev_failed, "rerun_failed": rerun_failed,
                                "fix_relevant": fix_relevant(text, fix["touched_files"])})
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", type=Path, default=ROOT / "data/processed/failures.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/failures_labeled.jsonl")
    ap.add_argument("--disabled", type=Path, default=ROOT / "data/processed/pytorch_disabled.jsonl")
    ap.add_argument("--tests-out", type=Path, default=ROOT / "data/processed/pytorch_test_failures.jsonl",
                    help="per-test traceback records for failed pytorch jobs")
    ap.add_argument("--repos", nargs="*", help="only label these repos")
    ap.add_argument("--relabel-infra-changed", action="store_true",
                    help="recompute infra_match on the existing --out file; fully re-label only jobs whose infra "
                         "status changed (cached API work), then refresh-derived; prints a before/after audit")
    ap.add_argument("--now", type=lambda v: datetime.fromisoformat(v).astimezone(timezone.utc),
                    help="labeling time for the recency rule (default: now)")
    ap.add_argument("--refresh-derived", action="store_true",
                    help="no API calls: re-apply aggregator exclusion + fix_relevant to the existing --out file")
    ap.add_argument("--examples", type=int, default=5, help="infra example matches to print per pattern")
    args = ap.parse_args()

    issues: dict[str, list[dict]] = {}  # test_name -> issues
    if args.disabled.exists():
        for line in args.disabled.open():
            i = json.loads(line)
            issues.setdefault(i["test_name"], []).append(i)

    recs = [json.loads(l) for l in args.inp.open()]
    if args.repos:
        recs = [r for r in recs if r["repo"] in args.repos]
    now = args.now or datetime.now(timezone.utc)
    out = []
    n_tests = 0
    if args.relabel_infra_changed:
        out = relabel_infra_changed([json.loads(l) for l in args.out.open()], issues, now)
        tmp = args.out.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(r) + "\n" for r in out))
        tmp.replace(args.out)
        recs = []
        args.refresh_derived = True  # skip the normal write path below
    elif args.refresh_derived:
        out = [refresh_derived(json.loads(l)) for l in args.out.open()]
        if args.repos:
            out = [r for r in out if r["repo"] in args.repos]
        tmp = args.out.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(r) + "\n" for r in out))
        tmp.replace(args.out)
        recs = []
    with (open(os.devnull, "w") if args.refresh_derived else args.out.open("w")) as f, \
            (open(os.devnull, "w") if args.refresh_derived else args.tests_out.open("w")) as ft:
        for i, r in enumerate(recs, 1):
            out.append(label(r, issues, now))
            f.write(json.dumps(out[-1]) + "\n")
            if r["repo"] == "pytorch/pytorch" and r["log_path"]:
                for t in test_failure_records(out[-1], read_log(r["log_path"]), issues):
                    ft.write(json.dumps(t) + "\n")
                    n_tests += 1
            if i % 200 == 0 or i == len(recs):
                print(f"{datetime.now():%H:%M:%S} labeled {i}/{len(recs)}", file=sys.stderr, flush=True)

    if not args.refresh_derived:
        print(f"wrote {n_tests} pytorch per-test failure records to {args.tests_out}", file=sys.stderr)
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
