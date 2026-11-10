"""Collect failed GitHub Actions jobs: metadata -> data/processed/failures.jsonl, gzipped logs -> data/raw/{repo}/.

Usage: python -m collect.github_logs --repos mpv-player/mpv --max-runs 50
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests

from collect import testlog

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
CACHE = RAW / "_cache"
OUT = ROOT / "data/processed/failures.jsonl"
API = "https://api.github.com"

REPOS = ["mpv-player/mpv", "AOMediaCodec/libavif", "apache/arrow",
         "pytest-dev/pytest", "pydantic/pydantic", "pytorch/pytorch"]
WORKFLOWS = {"pytorch/pytorch": ["pull.yml", "trunk.yml"]}  # restricted repos; others: all workflows
DEFAULT_CAP = {"pytorch/pytorch": 500}  # failed runs per workflow
OTHER_CAP = 1000  # failed runs per repo for repos not in DEFAULT_CAP
TRIM = {"pytorch/pytorch"}  # store failure windows only, not full logs
FAILED = {"failure", "timed_out"}

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN not set")
        _session = requests.Session()
        _session.headers.update({"Authorization": f"Bearer {token}",
                                 "Accept": "application/vnd.github+json",
                                 "X-GitHub-Api-Version": "2022-11-28"})
    return _session


def request(url: str, params: dict | None = None) -> requests.Response:
    """GET with rate-limit sleeps and retries on 5xx / network errors."""
    if "/search/" in url:
        time.sleep(2.1)  # search API: 30 req/min
    for i in range(8):
        try:
            r = session().get(url, params=params, timeout=120)
        except requests.RequestException as e:
            print(f"  network error {e}; retry", file=sys.stderr)
            time.sleep(2 ** i)
            continue
        if r.status_code in (403, 429) and ("rate limit" in r.text.lower() or r.headers.get("x-ratelimit-remaining") == "0"):
            if r.headers.get("retry-after"):
                wait = int(r.headers["retry-after"])
            elif r.headers.get("x-ratelimit-remaining") == "0":
                wait = max(int(r.headers["x-ratelimit-reset"]) - time.time(), 0)
            else:
                wait = 60
            print(f"  {datetime.now():%H:%M:%S} rate limited; sleeping {wait + 2:.0f}s", file=sys.stderr, flush=True)
            time.sleep(wait + 2)
            continue
        if r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        if r.headers.get("x-ratelimit-resource") == "core" and int(r.headers.get("x-ratelimit-remaining", 999)) < 20:
            wait = max(int(r.headers["x-ratelimit-reset"]) - time.time(), 0) + 5
            print(f"  {datetime.now():%H:%M:%S} rate limit nearly used; sleeping {wait:.0f}s until reset",
                  file=sys.stderr, flush=True)
            time.sleep(wait)
        return r
    r.raise_for_status()
    return r


def gh_get(path: str, params: dict | None = None, cache: bool = True):
    """Cached JSON GET. 404/410 -> None."""
    url = path if path.startswith("http") else API + path
    f = CACHE / (hashlib.sha1(json.dumps([url, params], sort_keys=True).encode()).hexdigest() + ".json")
    if cache and f.exists():
        return json.loads(f.read_text())
    r = request(url, params)
    if r.status_code in (404, 410):
        data = None
    else:
        r.raise_for_status()
        data = r.json()
    if cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(f)
    return data


def gh_pages(path: str, key: str, params: dict | None = None, cache: bool = True) -> Iterator[dict]:
    page = 1
    while True:
        data = gh_get(path, {**(params or {}), "per_page": 100, "page": page}, cache)
        items = (data or {}).get(key, [])
        yield from items
        if len(items) < 100:
            return
        page += 1


def candidate_runs(repo: str, workflow: str | None, days: int, cap: int | None) -> Iterator[dict]:
    """Newest first, one day at a time (list endpoint caps filtered queries at 1000 results).
    Yields failed runs (up to cap) plus successful runs with run_attempt > 1 from the same days,
    since a rerun that passed is the flaky signal and those runs are not listed as failures."""
    base = f"/repos/{repo}/actions/workflows/{workflow}/runs" if workflow else f"/repos/{repo}/actions/runs"
    today = datetime.now(timezone.utc).date()
    n_failed = 0
    for d in range(days):
        day = (today - timedelta(days=d)).isoformat()
        cache = d >= 3  # recent days still change (reruns, completions)
        failed = list(gh_pages(base, "workflow_runs", {"status": "failure", "created": day}, cache))
        if cap is not None:
            failed = failed[: cap - n_failed]
        n_failed += len(failed)
        yield from failed
        yield from (r for r in gh_pages(base, "workflow_runs", {"status": "success", "created": day}, cache)
                    if r["run_attempt"] > 1)
        if cap is not None and n_failed >= cap:
            return


ANCHOR = re.compile(r"##\[error\]|^FAILED |\bFAILED \[|Traceback \(most recent call last\)|^(?:FAIL|ERROR): ")


def trim_log(text: str, ctx: int = 200) -> str:
    """Keep +-ctx lines around failure anchors (used for huge logs, e.g. pytorch), plus every status line
    (PASSED/FAILED/ERROR/RERUN) of each test that failed anywhere in the log, so in-job reruns stay visible."""
    lines = text.splitlines()
    anchors = [i for i, l in enumerate(lines) if ANCHOR.search(l.split(" ", 1)[-1])]  # skip timestamp
    status = {i for evs in testlog.scan(lines).values() if testlog.failed(evs) for i, _, is_status in evs if is_status}
    if not anchors and not status:
        return "\n".join(lines[-ctx:])
    keep = sorted(status | {j for i in anchors for j in range(max(0, i - ctx), min(len(lines), i + ctx + 1))})
    out, prev = [], -1
    for j in keep:
        if out and j != prev + 1:
            out.append("... [trimmed] ...")
        out.append(lines[j])
        prev = j
    return "\n".join(out)


def fetch_log(repo: str, job_id: int) -> str | None:
    """Full job log text, or None if expired / missing."""
    r = request(f"{API}/repos/{repo}/actions/jobs/{job_id}/logs")
    if r.status_code in (404, 410):
        return None
    r.raise_for_status()
    return r.content.decode("utf-8", errors="replace")


def write_log(dest: Path, text: str, trim: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        f.write(trim_log(text) if trim else text)
    tmp.replace(dest)


def download_log(repo: str, job_id: int, dest: Path, trim: bool, force: bool = False) -> str:
    """force: re-download over an existing file (kept as is if the log has expired since)."""
    if dest.exists() and not force:
        return "ok"
    text = fetch_log(repo, job_id)
    if text is None:
        return "ok" if dest.exists() else "expired"
    write_log(dest, text, trim)
    return "ok"


def read_log(log_path: str) -> str:
    with gzip.open(ROOT / log_path, "rt", errors="replace") as f:
        return f.read()


def collect_run(repo: str, run: dict, done: set, out) -> int:
    n_new = 0
    for n in range(1, run["run_attempt"] + 1):
        att = gh_get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{n}")
        if att is None:
            continue
        for job in gh_pages(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{n}/jobs", "jobs"):
            if job["conclusion"] not in FAILED or (repo, run["id"], n, job["id"]) in done:
                continue
            dest = RAW / repo / f"{run['id']}_{n}_{job['id']}.log.gz"
            status = download_log(repo, job["id"], dest, repo in TRIM)
            rec = {
                "repo": repo, "workflow": run["path"], "workflow_name": run["name"], "workflow_id": run["workflow_id"],
                "run_id": run["id"], "attempt": n, "max_attempt": run["run_attempt"],
                "attempt_conclusion": att["conclusion"], "run_conclusion": run["conclusion"],
                "job_id": job["id"], "job_name": job["name"], "job_conclusion": job["conclusion"],
                "failed_steps": [s["name"] for s in job.get("steps") or [] if s["conclusion"] in FAILED],
                "head_sha": att["head_sha"], "head_branch": att["head_branch"],
                "head_repo": (att.get("head_repository") or {}).get("full_name"), "event": att["event"],
                "run_created_at": run["created_at"], "attempt_started_at": att["run_started_at"],
                "job_started_at": job["started_at"], "job_completed_at": job["completed_at"],
                "runner_labels": job.get("labels"), "html_url": job["html_url"],
                "log_path": str(dest.relative_to(ROOT)) if status == "ok" else None, "log_status": status,
            }
            out.write(json.dumps(rec) + "\n")
            out.flush()
            done.add((repo, run["id"], n, job["id"]))
            n_new += 1
    return n_new


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repos", nargs="+", default=REPOS)
    ap.add_argument("--max-runs", type=int, help="failed runs per repo/workflow (default: 500/workflow for pytorch, else 1000)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--refetch-logs", action="store_true",
                    help="only re-download logs of already collected jobs of --repos (e.g. after a trimming change)")
    args = ap.parse_args()

    if args.refetch_logs:
        recs = [r for r in map(json.loads, OUT.open()) if r["repo"] in args.repos and r["log_path"]]
        for i, r in enumerate(recs, 1):
            download_log(r["repo"], r["job_id"], ROOT / r["log_path"], r["repo"] in TRIM, force=True)
            if i % 100 == 0 or i == len(recs):
                print(f"{datetime.now():%H:%M:%S} refetched {i}/{len(recs)} logs", file=sys.stderr, flush=True)
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        for line in OUT.open():
            r = json.loads(line)
            done.add((r["repo"], r["run_id"], r["attempt"], r["job_id"]))

    with OUT.open("a") as out:
        for repo in args.repos:
            cap = args.max_runs if args.max_runs is not None else DEFAULT_CAP.get(repo, OTHER_CAP)
            for wf in WORKFLOWS.get(repo, [None]):
                n_runs = n_jobs = 0
                for run in candidate_runs(repo, wf, args.days, cap):
                    n_jobs += collect_run(repo, run, done, out)
                    n_runs += 1
                    if n_runs % 25 == 0:
                        print(f"{datetime.now():%H:%M:%S} {repo} {wf or '*'}: {n_runs} runs, {n_jobs} new failed jobs, "
                              f"run date {run['created_at'][:10]}", file=sys.stderr, flush=True)
                print(f"{datetime.now():%H:%M:%S} DONE {repo} {wf or '*'}: {n_runs} runs, {n_jobs} new failed jobs",
                      file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
