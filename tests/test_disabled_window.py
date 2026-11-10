"""Real-issue check of the DISABLED rule: the job linked from a bot issue body should match that issue
(window, platform, test name), shifted / wrong-platform controls should not, and final-failures-only
matching should reject tests that passed on an in-job rerun.

Usage: python -m tests.test_disabled_window 204184 203331 [--log-dir data/raw/_test_logs]
Hits the GitHub API (cached) and downloads the linked job logs; logs expire after ~90 days.
"""
import argparse
import gzip
import json
import re
from datetime import timedelta
from pathlib import Path

from collect import label
from collect.github_logs import ROOT, fetch_log, gh_get, trim_log


def check(num: int, issues: dict, log_dir: Path) -> None:
    iss = gh_get(f"/repos/pytorch/pytorch/issues/{num}")
    stored = next(i for v in issues.values() for i in v if i["number"] == num)
    job_id = int(re.findall(r"github\.com/pytorch/pytorch/runs/(\d+)", iss["body"])[-1])  # check-run id = job id
    job = gh_get(f"/repos/pytorch/pytorch/actions/jobs/{job_id}")
    dest = log_dir / f"{job_id}.full.log.gz"
    if not dest.exists():
        text = fetch_log("pytorch/pytorch", job_id)
        if text is None:
            print(f"#{num}: log unavailable")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(gzip.compress(text.encode()))
    text = trim_log(gzip.decompress(dest.read_bytes()).decode("utf-8", "replace"))  # as stored by the collector
    rec = {"job_started_at": job["started_at"], "job_name": f"{job['workflow_name']} / {job['name']}"}
    m = label.disabled_issue(rec, text, issues, final_only=False)
    strict = label.disabled_issue(rec, text, issues)
    gap = label.ts(iss["created_at"]) - label.ts(job["started_at"])
    print(f"#{num} {iss['title'][:100]}\n   platforms={stored['platforms']}  job: {rec['job_name'][:75]}")
    print(f"   job started {gap.total_seconds() / 3600:.1f}h before issue creation; job conclusion={job['conclusion']}")
    print(f"   window rule (incl. rerun-passed tests): " + (
        f"MATCH #{m['issue']} ({m['anchor']}) {'OK' if m['issue'] == num else 'other linked issue'}" if m else "NO MATCH"))
    if m:
        print(f"   log line: {m['log_line'][:150]}")
    print(f"   final-failures-only (used for labels): {'MATCH' if strict else 'no match'}")
    for desc, r2 in [("job 8 days earlier", {**rec, "job_started_at": (label.ts(job["started_at"]) - timedelta(days=8)).isoformat()}),
                     ("job 2h after creation", {**rec, "job_started_at": (label.ts(iss["created_at"]) + timedelta(hours=2)).isoformat()}),
                     ("job renamed to win", {**rec, "job_name": "trunk / win-vs2022-cpu-py3 / test (default, 1, 3, windows.4xlarge)"})]:
        hit = label.disabled_issue(r2, text, issues, final_only=False)
        print(f"   control [{desc}]: {'MATCH (via ' + hit['anchor'] + ')' if hit else 'no match'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("issues", nargs="+", type=int)
    ap.add_argument("--log-dir", type=Path, default=ROOT / "data/raw/_test_logs")
    ap.add_argument("--disabled", type=Path, default=ROOT / "data/processed/pytorch_disabled.jsonl")
    args = ap.parse_args()
    issues: dict = {}
    for line in args.disabled.open():
        i = json.loads(line)
        issues.setdefault(i["test_name"], []).append(i)
    for num in args.issues:
        check(num, issues, args.log_dir)


if __name__ == "__main__":
    main()
