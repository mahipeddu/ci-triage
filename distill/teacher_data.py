"""Teacher answers for TRAIN incidents (distillation data): flash-lite + prompt v1 with temporal BM25 top-5 from
older train incidents, throttled and cached. Resumable; exits 2 when the Gemini daily quota is exhausted.

Output: data/processed/teacher_train.jsonl, one record per train incident (match = teacher category == auto-label).
Then, for classes with < --min-kept kept answers, a rationalization pass over that class's dropped incidents: the same
v1 prompt plus "The correct category is <auto-label>. Explain the likely cause in one sentence." ->
data/processed/teacher_rationalized.jsonl (teacher_source=rationalized). Also resumable / quota-aware.
Usage: GEMINI_API_KEY=... python -m distill.teacher_data
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from collect.github_logs import ROOT
from eval.fast_track import SCORE_MAP, bm25_index, build_prompt, gemini, load_split, parse_answer

RATIONALIZE = ("\n\nThe correct category is {label}. Explain the likely cause in one sentence.\n"
               'Answer with JSON only: {{"category": "{label}", "likely_cause": "<one sentence>"}}')


def summary(path: Path) -> str:
    """Kept (teacher category == auto-label) / dropped per auto-label class."""
    from collections import Counter
    rs = [json.loads(l) for l in path.open()] if path.exists() else []
    kept, drop = Counter(r["label"] for r in rs if r["match"]), Counter(r["label"] for r in rs if not r["match"])
    return "kept/dropped per class: " + ", ".join(f"{c} {kept[c]}/{drop[c]}" for c in ("flaky", "infra", "regression")) \
        + f" (total {sum(kept.values())}/{sum(drop.values())})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", type=Path, default=ROOT / "data/processed/failures_labeled.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/teacher_train.jsonl")
    ap.add_argument("--exclude-repos", nargs="*", default=["pytorch/pytorch"])
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--min-interval", type=float, default=7.0)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-kept", type=int, default=30, help="rationalize dropped examples of classes below this")
    ap.add_argument("--rationalized-out", type=Path, default=ROOT / "data/processed/teacher_rationalized.jsonl")
    args = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set")

    train, _ = load_split(args.inp, set(args.exclude_repos), 0.3, 3)
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    done = {json.loads(l)["id"] for l in args.out.open()} if args.out.exists() else set()
    todo = [q for q in train if q["id"] not in done]
    print(f"{len(train)} train incidents, {len(done)} done, {len(todo)} to go", file=sys.stderr, flush=True)
    state: dict = {}
    with args.out.open("a") as f:
        for n, q in enumerate(todo, 1):
            resp = gemini(build_prompt(q, train, search(q["text"], args.k, before=q["t"])), args.model,
                          args.min_interval, state)
            if resp is None:
                f.flush()
                print(summary(args.out), file=sys.stderr, flush=True)
                print(f"{time.strftime('%H:%M:%S')} stopped at {len(done) + n - 1}/{len(train)} "
                      f"({'daily quota' if state.get('quota') else 'persistent errors'})", file=sys.stderr, flush=True)
                sys.exit(2 if state.get("quota") else 3)
            a = parse_answer(resp)
            cat = a and SCORE_MAP.get(a[0], a[0])
            f.write(json.dumps({"id": q["id"], "repo": q["repo"], "t": q["t"].isoformat(), "label": q["y"],
                                "source": q["source"], "teacher_category": a and a[0],
                                "likely_cause": a and a[1], "match": cat == q["y"]}) + "\n")
            f.flush()
            if n % 5 == 0 or n == len(todo):
                print(f"{time.strftime('%H:%M:%S')} teacher {len(done) + n}/{len(train)}", file=sys.stderr, flush=True)
    print(summary(args.out), file=sys.stderr, flush=True)
    print(f"{time.strftime('%H:%M:%S')} main pass complete", file=sys.stderr, flush=True)
    rationalize(args, train, search, state)
    print(f"{time.strftime('%H:%M:%S')} TEACHER DATA COMPLETE", file=sys.stderr, flush=True)


def rationalize(args, train: list[dict], search, state: dict) -> None:
    from collections import Counter
    rs = [json.loads(l) for l in args.out.open()]
    kept = Counter(r["label"] for r in rs if r["match"])
    low = [c for c in ("flaky", "infra", "regression") if kept[c] < args.min_kept]
    by_id = {q["id"]: q for q in train}
    done = {json.loads(l)["id"] for l in args.rationalized_out.open()} if args.rationalized_out.exists() else set()
    todo = [by_id[r["id"]] for r in rs if not r["match"] and r["label"] in low and r["id"] not in done]
    print(f"rationalization: classes below {args.min_kept} kept: {low or 'none'}; {len(done)} done, {len(todo)} to go",
          file=sys.stderr, flush=True)
    with args.rationalized_out.open("a") as f:
        for n, q in enumerate(todo, 1):
            prompt = build_prompt(q, train, search(q["text"], args.k, before=q["t"])) + RATIONALIZE.format(label=q["y"])
            resp = gemini(prompt, args.model, args.min_interval, state)
            if resp is None:
                print(f"{time.strftime('%H:%M:%S')} rationalization stopped at {len(done) + n - 1}/{len(done) + len(todo)} "
                      f"({'daily quota' if state.get('quota') else 'persistent errors'})", file=sys.stderr, flush=True)
                sys.exit(2 if state.get("quota") else 3)
            a = parse_answer(resp)
            f.write(json.dumps({"id": q["id"], "repo": q["repo"], "t": q["t"].isoformat(), "label": q["y"],
                                "source": q["source"], "teacher_source": "rationalized",
                                "teacher_category": a and a[0], "likely_cause": a and a[1],
                                "match": bool(a) and SCORE_MAP.get(a[0], a[0]) == q["y"]}) + "\n")
            f.flush()
            if n % 5 == 0 or n == len(todo):
                print(f"{time.strftime('%H:%M:%S')} rationalized {len(done) + n}/{len(done) + len(todo)}",
                      file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
