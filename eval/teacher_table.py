"""Model x prompt comparison table from fast_track --summary-json outputs.

Usage: python -m eval.teacher_table [--runs eval/teacher_runs] [--out eval/teacher_comparison.md]
"""
import argparse
import json
from pathlib import Path

from collect.github_logs import ROOT


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=ROOT / "eval/teacher_runs")
    ap.add_argument("--out", type=Path, default=ROOT / "eval/teacher_comparison.md")
    ap.add_argument("--dropped", nargs="*", default=[], help="'model: reason' rows for configurations not run")
    ap.add_argument("--chosen", default="", help="note naming the chosen teacher")
    args = ap.parse_args()

    runs = []
    for f in sorted(args.runs.glob("*.json")):
        r = json.loads(f.read_text())
        r["requested"] = int(f.stem.rsplit("_", 1)[1])  # files are <model>_<prompt>_<n>.json
        runs.append(r)
    runs.sort(key=lambda r: (-r["n"], r["model"], r["prompt"]))

    def ci(r: dict, k: str) -> str:
        c = r["llm_ci"].get(k)
        return f"{r['llm'][k]:.3f} [{c[0]:.2f}–{c[1]:.2f}]" if c else f"{r['llm'][k]:.3f}"

    def diff(r: dict, subset: str, k: str) -> str:
        d, lo, hi, share = r["paired"][subset][k]
        return f"{d:+.3f} [{lo:+.2f}, {hi:+.2f}]" + (" *" if lo > 0 or hi < 0 else "")

    lines = [
        "# Teacher comparison: model × prompt (Gemini free tier, + RAG with BM25 top-5)",
        "",
        "Same per-repo time split, temporal retrieval and aggregator exclusion as `results_no_pytorch.md`. "
        "Each block uses one stratified sample of test incidents (round-robin over the 5 repos); the n=60 sample "
        "is a strict subset of the n=150 one. kNN columns are BM25 kNN scored on exactly the same incidents.",
        "Paired diff = Gemini − kNN on the same incidents, 95% paired bootstrap CI (1000 resamples); "
        "* = CI excludes 0. v1 = original prompt; v2 = label-procedure definitions + 3 worked examples from train.",
        "",
        "| model | prompt | n | macro-F1 | flaky F1 | kNN macro / flaky (same n) | paired Δ macro | paired Δ flaky "
        "| paired Δ macro, fix_relevant=true |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        lines.append(
            f"| {r['model']} | {r['prompt']} | {r['n']}"
            + (f" of {r['requested']} (partial: daily quota)" if r["n"] < r["requested"] else "")
            + f" | {ci(r, 'macro')} | {ci(r, 'flaky')} "
            f"| {r['knn_same']['macro']:.3f} / {r['knn_same']['flaky']:.3f} | {diff(r, 'all', 'macro')} "
            f"| {diff(r, 'all', 'flaky')} | {diff(r, 'fix_relevant=true only', 'macro')} |")
    lines += [f"| {d.split(':', 1)[0]} | v1, v2 | – | dropped: {d.split(':', 1)[1].strip()} | | | | | |"
              for d in args.dropped]
    if args.chosen:
        lines += ["", f"**Chosen teacher: {args.chosen}**"]
    lines += ["", "Raw answer counts: " + "; ".join(
        f"{r['model']} {r['prompt']} n={r['n']}: " + ", ".join(f"{k} {v}" for k, v in sorted(r["raw"].items()))
        for r in runs)]
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
