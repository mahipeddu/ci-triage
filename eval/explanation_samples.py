"""Random generated likely_cause explanations next to the auto-label and the failure's first error line, for judging
whether they are specific or generic -> eval/explanation_samples.md.

Usage: python -m eval.explanation_samples [--preds data/processed/student_preds_student_rationale.jsonl] [--n 15]
"""
import argparse
import json
import random
import re
from pathlib import Path

from collect.github_logs import ROOT
from eval.fast_track import load_split

ERROR = re.compile(r"error|fail|exception|assert|traceback|fatal|timed? ?out", re.I)
GENERIC = re.compile(r"process completed with exit code|^error: process", re.I)


def first_error_line(region: list[str]) -> str:
    """First line of the (normalized) failure region that looks like an error, skipping the runner's exit-code line."""
    return next((l for l in region if ERROR.search(l) and not GENERIC.search(l)), region[0] if region else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preds", type=Path, default=ROOT / "data/processed/student_preds_student_rationale.jsonl")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=ROOT / "eval/explanation_samples.md")
    args = ap.parse_args()

    _, test = load_split(ROOT / "data/processed/failures_labeled.jsonl", {"pytorch/pytorch"}, 0.3, 3)
    by_id = {i["id"]: i for i in test}
    recs = [json.loads(l) for l in args.preds.open()]
    sample = sorted(random.Random(args.seed).sample(recs, args.n), key=lambda r: (r["repo"], r["id"]))
    lines = [f"# Generated explanations: {args.n} random test incidents", "",
             f"Student: `{args.preds.stem.removeprefix('student_preds_')}` (greedy generation, same RAG prompt as "
             f"its category scoring). Random sample (seed {args.seed}) of its 150 test-incident predictions. "
             "First error line = first line of the normalized failure region that looks like an error (lowercased, "
             "numbers/paths/hex normalized), skipping the runner's 'process completed with exit code' line.", "",
             "Verdict column: specific (names the actual failing thing) / generic (could describe any failure) / wrong.",
             "", "| # | repo · job | auto-label | student (p) | first error line | generated likely_cause | verdict |",
             "|---|---|---|---|---|---|---|"]
    cell = lambda s: (s or "–").replace("|", "\\|").replace("\n", " ")  # noqa: E731
    for n, r in enumerate(sample, 1):
        inc = by_id[r["id"]]
        lines.append(f"| {n} | {r['repo'].split('/')[1]} · [{cell(inc['job'])}]({inc['url']}) | {r['label']} "
                     f"| {r['pred']} ({r['probs'][r['pred']]:.2f}) | `{cell(first_error_line(inc['region'])[:160])}` "
                     f"| {cell(r.get('likely_cause'))} | |")
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
