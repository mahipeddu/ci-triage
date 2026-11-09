"""Fetch pytorch/pytorch "DISABLED <test> (<class>)" issues -> data/processed/pytorch_disabled.jsonl.

Usage: python -m collect.pytorch_disabled [--since 2020-01-01]
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from collect.github_logs import ROOT, gh_get

TITLE = re.compile(r"^DISABLED\s+(\S+)\s+\(([^)]+)\)")


def search(start: date, end: date) -> list[dict]:
    """All issues created in [start, end]; splits the range while it exceeds the 1000-result search cap."""
    q = f'repo:pytorch/pytorch is:issue in:title "DISABLED" created:{start}..{end}'
    cache = end < datetime.now(timezone.utc).date() - timedelta(days=1)
    first = gh_get("/search/issues", {"q": q, "per_page": 100, "page": 1}, cache)
    if first["total_count"] > 1000 and start < end:
        mid = start + (end - start) // 2
        return search(start, mid) + search(mid + timedelta(days=1), end)
    items, page = list(first["items"]), 1
    while len(items) < min(first["total_count"], 1000):
        page += 1
        batch = gh_get("/search/issues", {"q": q, "per_page": 100, "page": page}, cache)["items"]
        if not batch:
            break
        items += batch
    print(f"{start}..{end}: {len(items)}", file=sys.stderr)
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", type=date.fromisoformat, default=date(2020, 1, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/pytorch_disabled.jsonl")
    args = ap.parse_args()

    recs = {}
    for y in range(args.since.year, args.until.year + 1):
        start, end = max(args.since, date(y, 1, 1)), min(args.until, date(y, 12, 31))
        for it in search(start, end):
            m = TITLE.match(it["title"])
            if not m:
                continue
            recs[it["number"]] = {"number": it["number"], "title": it["title"],
                                  "test_name": m.group(1), "test_class": m.group(2),
                                  "created_at": it["created_at"], "closed_at": it["closed_at"],
                                  "state": it["state"], "author": it["user"]["login"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in sorted(recs.values(), key=lambda r: r["number"]):
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(recs)} issues to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
