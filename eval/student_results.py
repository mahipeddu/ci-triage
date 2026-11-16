"""Students vs BM25 kNN vs Gemini teacher on the same 150 stratified test incidents -> eval/student_results.md.

Students are scored from distill.predict_student outputs (log-prob scoring of the 3 categories). The teacher is
gemini-3.5-flash-lite + prompt v1, read from the response cache only (no API calls).
Usage: python -m eval.student_results --student labels=data/processed/student_preds_student_labels.jsonl [...]
"""
import argparse
import json
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from collect.github_logs import ROOT
from eval.fast_track import (CLASSES, SCORE_MAP, bm25_index, bootstrap_ci, build_prompt, cache_path, f1s,
                             knn_predict, load_split, parse_answer, stratified)

BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0001)]


def paired(gold: list[str], a: list[str], b: list[str], n: int = 1000, seed: int = 1) -> dict:
    """F1(a) − F1(b) on the same incidents: point, 95% CI, share of resamples ≤ 0."""
    rng = random.Random(seed)
    diffs = defaultdict(list)
    for _ in range(n):
        ix = [rng.randrange(len(gold)) for _ in gold]
        fa, fb = f1s([gold[i] for i in ix], [a[i] for i in ix]), f1s([gold[i] for i in ix], [b[i] for i in ix])
        for k in ("macro", "flaky"):
            if fa[k] == fa[k] and fb[k] == fb[k]:
                diffs[k].append(fa[k] - fb[k])
    full_a, full_b = f1s(gold, a), f1s(gold, b)
    out = {}
    for k in ("macro", "flaky"):
        d = sorted(diffs[k])
        out[k] = (full_a[k] - full_b[k], d[int(0.025 * len(d))], d[min(len(d) - 1, int(0.975 * len(d)))]) if d \
            else (full_a[k] - full_b[k], float("nan"), float("nan"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", action="append", default=[], help="name=path to predict_student output")
    ap.add_argument("--teacher-model", default="gemini-3.5-flash-lite")
    ap.add_argument("--llm-n", type=int, default=150)
    ap.add_argument("--out", type=Path, default=ROOT / "eval/student_results.md")
    ap.add_argument("--price-in", type=float, default=0.30, help="teacher $ per 1M input tokens (paid tier)")
    ap.add_argument("--price-out", type=float, default=2.50, help="teacher $ per 1M output tokens (paid tier)")
    args = ap.parse_args()

    train, test = load_split(ROOT / "data/processed/failures_labeled.jsonl", {"pytorch/pytorch"}, 0.3, 3)
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    idx = stratified(test, args.llm_n)
    majority = Counter(i["y"] for i in train).most_common(1)[0][0]
    hits = {j: search(test[j]["text"], 5, before=test[j]["t"]) for j in idx}
    gold = {j: test[j]["y"] for j in idx}
    preds = {"BM25 kNN": {j: knn_predict(hits[j], train, majority) for j in idx}}
    teacher, usage = {}, []
    for j in idx:
        f = cache_path(build_prompt(test[j], train, hits[j]), args.teacher_model)
        resp = json.loads(f.read_text()) if f.exists() else None
        a = parse_answer(resp) if resp else None
        if a:
            teacher[j] = SCORE_MAP.get(a[0], a[0])
            u = resp.get("usageMetadata", {})
            usage.append((u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)))
    preds[f"teacher {args.teacher_model} v1"] = teacher
    by_id = {test[j]["id"]: j for j in idx}
    students, lat = {}, {}
    for spec in args.student:
        name, path = spec.split("=", 1)
        recs = [json.loads(l) for l in open(path)]
        students[name] = {by_id[r["id"]]: r for r in recs if r["id"] in by_id}
        preds[f"student {name}"] = {j: r["pred"] for j, r in students[name].items()}
        lat[name] = ([r["score_latency_s"] for r in recs], [r["gen_latency_s"] for r in recs if "gen_latency_s" in r])

    def fmt(x: float) -> str:
        return "–" if x != x else f"{x:.3f}"

    lines = ["# Students vs baselines (same 150 stratified test incidents)", "",
             "Split, censoring, aggregator exclusion and temporal BM25 retrieval as in `results_no_pytorch.md`; "
             "the same 150 incidents (round-robin over the 5 repos) for every method. Students: "
             "Qwen3-4B-Instruct-2507 + QLoRA, category by log-prob scoring of the 3 candidate completions (argmax; "
             "nothing unparseable). 95% bootstrap CIs, 1000 resamples.", "",
             "| method | n | macro-F1 | F1 flaky | F1 infra | F1 regression |", "|---|---|---|---|---|---|"]
    for name, p in preds.items():
        js = sorted(p)
        g, pr = [gold[j] for j in js], [p[j] for j in js]
        s, ci = f1s(g, pr), bootstrap_ci(g, pr, 1000)
        cell = lambda k: fmt(s[k]) + (f" [{ci[k][0]:.2f}–{ci[k][1]:.2f}]" if k in ci else "")  # noqa: E731
        lines.append(f"| {name} | {len(js)} | {cell('macro')} | {cell('flaky')} | {cell('infra')} | {cell('regression')} |")
    lines += ["", f"Test classes in the sample: {dict(Counter(gold.values()))}.", "",
              "## Paired differences (same incidents)", "", "| comparison | n | Δ macro-F1 | Δ flaky F1 |", "|---|---|---|---|"]
    tname = f"teacher {args.teacher_model} v1"
    for sname in students:
        for other in ("BM25 kNN", tname):
            js = sorted(set(preds[f"student {sname}"]) & set(preds[other]))
            d = paired([gold[j] for j in js], [preds[f"student {sname}"][j] for j in js], [preds[other][j] for j in js])
            star = lambda t: " *" if t[1] > 0 or t[2] < 0 else ""  # noqa: E731
            lines.append(f"| student {sname} − {other} | {len(js)} | {d['macro'][0]:+.3f} [{d['macro'][1]:+.2f}, "
                         f"{d['macro'][2]:+.2f}]{star(d['macro'])} | {d['flaky'][0]:+.3f} [{d['flaky'][1]:+.2f}, "
                         f"{d['flaky'][2]:+.2f}]{star(d['flaky'])} |")
    lines += ["", "\\* = CI excludes 0.", ""]

    for sname, recs in students.items():
        rs = [recs[j] for j in sorted(recs)]
        lines += [f"## Calibration: student {sname}", "",
                  "Confidence = probability of the predicted class (softmax over the 3 candidate log-probs).", "",
                  "| confidence bin | n | mean confidence | accuracy |", "|---|---|---|---|"]
        ece = 0.0
        for lo, hi in BINS:
            b = [r for r in rs if lo <= max(r["probs"].values()) < hi]
            if not b:
                lines.append(f"| {lo:.1f}–{min(hi, 1):.1f} | 0 | – | – |")
                continue
            conf = st.mean(max(r["probs"].values()) for r in b)
            acc = sum(r["pred"] == r["label"] for r in b) / len(b)
            ece += len(b) / len(rs) * abs(conf - acc)
            lines.append(f"| {lo:.1f}–{min(hi, 1):.1f} | {len(b)} | {conf:.3f} | {acc:.3f} |")
        lines += ["", f"ECE (expected calibration error, {len(BINS)} bins): {ece:.3f}", "",
                  "Mean predicted probability per class, by gold class:", "",
                  "| gold \\ predicted p | " + " | ".join(CLASSES) + " | n |", "|---|---|---|---|---|"]
        for g in CLASSES:
            b = [r for r in rs if r["label"] == g]
            if b:
                lines.append(f"| {g} | " + " | ".join(f"{st.mean(r['probs'][c] for r in b):.3f}" for c in CLASSES)
                             + f" | {len(b)} |")
        lines.append("")

    lines += ["## Latency and cost per 1k incidents", "",
              "| method | median latency / incident | cost per 1k incidents |", "|---|---|---|",
              "| BM25 kNN | < 0.1 s (CPU) | $0 |"]
    for sname, (score, gen) in lat.items():
        lines.append(f"| student {sname} (RTX 5080, 4-bit) | {st.median(score):.2f} s category scoring"
                     + (f"; {st.median(gen):.2f} s with generated likely_cause" if gen else "")
                     + " | $0 API (local GPU) |")
    tin, tout = st.mean(u[0] for u in usage), st.mean(u[1] for u in usage)
    cost = 1000 * (tin * args.price_in + tout * args.price_out) / 1e6
    lines += [f"| teacher {args.teacher_model} | not measured here (free-tier latency varied 2–100 s per request; "
              f"paid tier ~1 request/s sustained) | ${cost:.2f} on the paid tier (mean {tin:.0f} input + {tout:.0f} "
              f"output tokens per incident at ${args.price_in}/M in, ${args.price_out}/M out); $0 on the free tier "
              "within its daily quota |", "",
              "Teacher prices: third-party aggregators citing Google's rate sheet (Oct 2026); verify against "
              "ai.google.dev/gemini-api/docs/pricing.", ""]
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
