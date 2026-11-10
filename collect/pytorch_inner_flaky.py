"""pytorch in-job flaky tests: for recent bot DISABLED issues, follow the job link in the issue body, download that
job's log, and record every test that FAILED/RERUN and later PASSED in the same job.
Those jobs usually pass overall (pytorch reruns failing tests in-job), so the failed-runs collector never sees them.

Output: data/processed/pytorch_inner_flaky.jsonl, one record per (job, test). Logs: data/raw/pytorch/pytorch/inner/.
Usage: python -m collect.pytorch_inner_flaky [--days 85] [--limit 20]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collect import testlog
from collect.github_logs import RAW, ROOT, fetch_log, gh_get, write_log
from collect.label import DISABLED_BOT, issue_candidates, ts

REPO = "pytorch/pytorch"
JOB_LINK = re.compile(r"github\.com/pytorch/pytorch/(?:actions/runs/\d+/job/|runs/)(\d+)")  # check-run id = job id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=85, help="issues created within this many days (logs expire at 90)")
    ap.add_argument("--limit", type=int, help="process only the N newest issues")
    ap.add_argument("--disabled", type=Path, default=ROOT / "data/processed/pytorch_disabled.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/pytorch_inner_flaky.jsonl")
    args = ap.parse_args()

    all_issues = [json.loads(l) for l in args.disabled.open()]
    by_test: dict[str, list[dict]] = defaultdict(list)
    for i in all_issues:
        by_test[i["test_name"]].append(i)
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    recent = sorted((i for i in all_issues if i["author"] == DISABLED_BOT and ts(i["created_at"]) >= since),
                    key=lambda i: i["created_at"], reverse=True)[:args.limit]

    jobs: dict[int, list[dict]] = defaultdict(list)  # job id -> issues linking it (sibling issues share jobs)
    for iss in recent:
        body = (gh_get(f"/repos/{REPO}/issues/{iss['number']}") or {}).get("body") or ""
        for job_id in dict.fromkeys(map(int, JOB_LINK.findall(body))):
            jobs[job_id].append(iss)
    print(f"{len(recent)} issues -> {len(jobs)} linked jobs", file=sys.stderr)

    n_new = n_expired = 0
    with args.out.open("a") as out:
        for job_id, linked in jobs.items():
            job = gh_get(f"/repos/{REPO}/actions/jobs/{job_id}")
            if job is None:
                continue
            dest = RAW / REPO / "inner" / f"{job['run_id']}_{job['run_attempt']}_{job_id}.log.gz"
            if dest.exists():  # written after the job's records -> job already done
                continue
            text = fetch_log(REPO, job_id)
            if text is None:
                n_expired += 1
                continue
            lines = text.splitlines()
            for (test, cls), evs in testlog.scan(lines).items():
                if not testlog.inner_flaky(evs):
                    continue
                own = [i["number"] for i in issue_candidates(test, cls, by_test) if i in linked]
                first_fail = next(i for i, st, _ in evs if st == "fail")
                first_pass = next(i for i, st, s in evs if st == "pass" and s and i > first_fail)
                out.write(json.dumps({
                    "repo": REPO, "workflow_name": job["workflow_name"], "run_id": job["run_id"],
                    "attempt": job["run_attempt"], "job_id": job_id, "job_name": job["name"],
                    "job_conclusion": job["conclusion"], "inner_flaky": True,
                    "head_sha": job["head_sha"], "head_branch": job["head_branch"],
                    "job_started_at": job["started_at"], "html_url": job["html_url"],
                    "log_path": str(dest.relative_to(ROOT)),
                    "test_name": test, "test_class": cls,
                    "fail_line": testlog.strip(lines[first_fail])[:300], "pass_line": testlog.strip(lines[first_pass])[:300],
                    "traceback": testlog.traceback_chunk(lines, (test, cls), evs),
                    "label": "flaky", "label_source": "inner_rerun", "confidence": "high",
                    "issue": own[0] if own else linked[0]["number"], "issue_test_match": bool(own),
                    "linked_issues": [i["number"] for i in linked],
                }) + "\n")
                n_new += 1
            out.flush()
            write_log(dest, text, trim=True)
    print(f"wrote {n_new} records to {args.out} ({n_expired} linked logs expired)", file=sys.stderr)


if __name__ == "__main__":
    main()
