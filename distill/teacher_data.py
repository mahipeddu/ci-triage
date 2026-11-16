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
from eval.fast_track import SCORE_MAP, bm25_index, build_prompt, concurrent_map, gemini, load_split, parse_answer

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
    ap.add_argument("--thinking", type=json.loads, help="thinkingConfig JSON")
    ap.add_argument("--only-classes", nargs="*", help="main pass only for train incidents with these auto-labels")
    ap.add_argument("--budget-cap", type=float, help="stop when spend on --model would exceed this ($); exit 4")
    ap.add_argument("--cap-prices", type=float, nargs=2, default=[0.83, 4.13])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-workers", type=int, default=16)
    ap.add_argument("--rationalized-out", type=Path, default=ROOT / "data/processed/teacher_rationalized.jsonl")
    args = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set")

    train, _ = load_split(args.inp, set(args.exclude_repos), 0.3, 3)
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    done = {json.loads(l)["id"] for l in args.out.open()} if args.out.exists() else set()
    todo = [q for q in train if q["id"] not in done and (not args.only_classes or q["y"] in args.only_classes)]
    print(f"{len(train)} train incidents, {len(done)} done, {len(todo)} to go", file=sys.stderr, flush=True)
    state: dict = {"cap": (args.budget_cap, *args.cap_prices)} if args.budget_cap else {}
    order = {q["id"]: i for i, q in enumerate(train)}
    prompts = {q["id"]: build_prompt(q, train, search(q["text"], args.k, before=q["t"])) for q in todo}
    call = lambda q: gemini(prompts[q["id"]], args.model, args.min_interval, state, args.thinking)  # noqa: E731
    errors = 0
    with args.out.open("a") as f:
        for n, (q, resp) in enumerate(concurrent_map(call, todo, state, args.workers, args.max_workers), 1):
            if resp is None:
                errors += not (state.get("quota") or state.get("budget"))
                continue
            a = parse_answer(resp)
            cat = a and SCORE_MAP.get(a[0], a[0])
            f.write(json.dumps({"id": q["id"], "repo": q["repo"], "t": q["t"].isoformat(), "label": q["y"],
                                "source": q["source"], "teacher_category": a and a[0],
                                "likely_cause": a and a[1], "match": cat == q["y"]}) + "\n")
            f.flush()
            if n % 5 == 0 or n == len(todo):
                print(f"{time.strftime('%H:%M:%S')} teacher {len(done) + n}/{len(train)}", file=sys.stderr, flush=True)
    sort_file(args.out, order)
    print(summary(args.out), file=sys.stderr, flush=True)
    stop(state, errors, "main pass")
    print(f"{time.strftime('%H:%M:%S')} main pass complete", file=sys.stderr, flush=True)
    rationalize(args, train, search, state, order)
    print(f"{time.strftime('%H:%M:%S')} TEACHER DATA COMPLETE", file=sys.stderr, flush=True)


def sort_file(path: Path, order: dict[str, int]) -> None:
    """Rewrite a results file in train-incident order (concurrent calls complete out of order)."""
    if not path.exists():
        return
    rs = sorted((json.loads(l) for l in path.open()), key=lambda r: order.get(r["id"], len(order)))
    tmp = path.with_suffix(".sorting.tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rs))
    tmp.replace(path)


def stop(state: dict, errors: int, phase: str) -> None:
    """Exit after an incomplete pass: 4 budget cap, 2 daily quota, 3 persistent errors (retry later)."""
    if state.get("budget"):
        print(f"{time.strftime('%H:%M:%S')} {phase} stopped: budget cap", file=sys.stderr, flush=True)
        sys.exit(4)
    if state.get("quota"):
        print(f"{time.strftime('%H:%M:%S')} {phase} stopped: daily quota", file=sys.stderr, flush=True)
        sys.exit(2)
    if errors:
        print(f"{time.strftime('%H:%M:%S')} {phase}: {errors} requests failed persistently", file=sys.stderr, flush=True)
        sys.exit(3)


def rationalize(args, train: list[dict], search, state: dict, order: dict[str, int]) -> None:
    from collections import Counter
    rs = [json.loads(l) for l in args.out.open()]
    kept = Counter(r["label"] for r in rs if r["match"])
    low = [c for c in ("flaky", "infra", "regression") if kept[c] < args.min_kept]
    by_id = {q["id"]: q for q in train}
    done = {json.loads(l)["id"] for l in args.rationalized_out.open()} if args.rationalized_out.exists() else set()
    todo = [by_id[r["id"]] for r in rs if not r["match"] and r["label"] in low and r["id"] not in done]
    print(f"rationalization: classes below {args.min_kept} kept: {low or 'none'}; {len(done)} done, {len(todo)} to go",
          file=sys.stderr, flush=True)
    prompts = {q["id"]: build_prompt(q, train, search(q["text"], args.k, before=q["t"])) + RATIONALIZE.format(label=q["y"])
               for q in todo}
    call = lambda q: gemini(prompts[q["id"]], args.model, args.min_interval, state, args.thinking)  # noqa: E731
    errors = 0
    with args.rationalized_out.open("a") as f:
        for n, (q, resp) in enumerate(concurrent_map(call, todo, state, args.workers, args.max_workers), 1):
            if resp is None:
                errors += not (state.get("quota") or state.get("budget"))
                continue
            a = parse_answer(resp)
            f.write(json.dumps({"id": q["id"], "repo": q["repo"], "t": q["t"].isoformat(), "label": q["y"],
                                "source": q["source"], "teacher_source": "rationalized",
                                "teacher_category": a and a[0], "likely_cause": a and a[1],
                                "match": bool(a) and SCORE_MAP.get(a[0], a[0]) == q["y"]}) + "\n")
            f.flush()
            if n % 5 == 0 or n == len(todo):
                print(f"{time.strftime('%H:%M:%S')} rationalized {len(done) + n}/{len(done) + len(todo)}",
                      file=sys.stderr, flush=True)
    sort_file(args.rationalized_out, order)
    stop(state, errors, "rationalization")


if __name__ == "__main__":
    main()
