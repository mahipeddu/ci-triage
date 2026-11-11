"""Fast-track eval on a labeled failures file: time-based split, rules baseline, BM25 kNN baseline,
Gemini Flash + RAG (BM25 top-k as context). Writes a markdown results table.

Unit = incident (matrix duplicates of one failure grouped by incident_id), labeled incidents only.
Usage: python -m eval.fast_track --inp data/processed/failures_labeled_small.jsonl --out eval/results_small.md
Gemini: GEMINI_API_KEY env var; free tier, throttled, every response cached under data/raw/_llm_cache/.
"""
import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import requests

from collect.github_logs import ROOT, read_log
from collect.label import FIX_WINDOW_DAYS, INFRA, failure_region, normalize, ts

CLASSES = ["flaky", "infra", "regression"]
LABEL_TO_CLASS = {"flaky": "flaky", "infra": "infra", "regression_strong": "regression", "regression_weak": "regression"}
FLAKY_HINT = re.compile(r"flaky|intermittent|timed? ?out|timeout|deadlock|race condition|segmentation fault|"
                        r"connection (reset|refused)|address already in use", re.I)
LLM_CACHE = ROOT / "data/raw/_llm_cache"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TOKEN = re.compile(r"[a-z_][a-z0-9_]+")


# ---------- data ----------

def incidents(path: Path, max_lines: int) -> list[dict]:
    by_inc: dict[str, list[dict]] = defaultdict(list)
    for line in path.open():
        r = json.loads(line)
        if r["label"] in LABEL_TO_CLASS and r["log_path"]:
            by_inc[(r["repo"], r["incident_id"])].append(r)
    out = []
    for (repo, inc), jobs in by_inc.items():
        classes = Counter(LABEL_TO_CLASS[j["label"]] for j in jobs)
        if len(classes) > 1:  # mixed labels within one incident: ambiguous, skip
            continue
        rep = min(jobs, key=lambda j: j["job_started_at"])
        region = [normalize(l) for l in failure_region(read_log(rep["log_path"]).splitlines())]
        region = [l for l in region if l][-max_lines:]
        fixes = {j["label_meta"]["fix_sha"] for j in jobs if j["label"].startswith("regression")}
        out.append({"id": inc, "repo": repo, "t": ts(rep["job_started_at"]), "y": next(iter(classes)),
                    "source": rep["label_source"], "job": rep["job_name"], "steps": rep["failed_steps"],
                    "sig": (rep["job_name"], region[0] if region else ""), "fixes": fixes,
                    "files": sorted({f for j in jobs if j["label"].startswith("regression")
                                     for f in j["label_meta"]["touched_files"]})[:10],
                    "text": f"job: {rep['job_name']}\nfailed steps: {', '.join(rep['failed_steps'])}\n" + "\n".join(region),
                    "n_jobs": len(jobs)})
    return sorted(out, key=lambda i: i["t"])


def time_split(incs: list[dict], test_frac: float, gap_days: int) -> tuple[list[dict], list[dict]]:
    test = incs[int(len(incs) * (1 - test_frac)):]
    cutoff = test[0]["t"] - timedelta(days=gap_days)
    return [i for i in incs if i["t"] < cutoff], test


# ---------- retrieval ----------

def bm25_index(docs: list[str], k1: float = 1.5, b: float = 0.75):
    toks = [TOKEN.findall(d.lower()) for d in docs]
    df = Counter(t for ts_ in toks for t in set(ts_))
    n, avg = len(toks), sum(map(len, toks)) / max(len(toks), 1)
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    tfs = [Counter(t) for t in toks]
    lens = [len(t) for t in toks]

    def search(q: str, k: int) -> list[tuple[int, float]]:
        qt = set(TOKEN.findall(q.lower()))
        scores = [(i, sum(idf[t] * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * lens[i] / avg))
                          for t in qt if t in tf)) for i, tf in enumerate(tfs)]
        return sorted(scores, key=lambda s: -s[1])[:k]
    return search


def relevant(q: dict, d: dict) -> bool:
    """Same fix commit, or same job + same normalized first error line (a recurrence of the incident)."""
    return bool(q["fixes"] & d["fixes"]) or (q["sig"] == d["sig"] and bool(q["sig"][1]))


# ---------- predictors ----------

def rules_predict(inc: dict, majority: str) -> str:
    if any(rx.search(inc["text"]) for _, _, rx in INFRA):
        return "infra"
    if FLAKY_HINT.search(inc["text"]):
        return "flaky"
    return majority


def knn_predict(hits: list[tuple[int, float]], train: list[dict], majority: str) -> str:
    votes: Counter = Counter()
    for i, s in hits:
        votes[train[i]["y"]] += 1 + s * 1e-6  # majority vote, score breaks ties
    return votes.most_common(1)[0][0] if votes else majority


PROMPT = """You triage failed CI jobs. Classify the NEW failure into exactly one category:
- flaky: nondeterministic failure that passes on retry without code changes
- infra: CI infrastructure problem (network, runner, disk, timeout of the job, dependency download)
- regression: caused by a code change; fixed by a later commit
- test_bug: the test itself is wrong
Use the similar past incidents (with their known categories and fixes) as evidence, but judge the new log itself.

NEW FAILURE (repo {repo}):
{text}

SIMILAR PAST INCIDENTS:
{context}

Answer with JSON only: {{"category": "flaky|infra|regression|test_bug", "likely_cause": "<one sentence>", "similar_incidents": ["<ids of the relevant past incidents>"]}}"""


def gemini(prompt: str, model: str, min_interval: float, state: dict) -> dict | None:
    key = hashlib.sha1(f"{model}\n{prompt}".encode()).hexdigest()
    f = LLM_CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}  # thinkingConfig: 400 on flash-lite
    for attempt in range(6):
        wait = state.get("last", 0) + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        state["last"] = time.time()
        try:
            r = requests.post(GEMINI_URL.format(model=model), json=body, timeout=60,
                              headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        except requests.RequestException as e:  # includes the 60 s timeout: a hang must not stall the eval
            print(f"  gemini request failed ({type(e).__name__}); retry", file=sys.stderr)
            continue
        if r.status_code == 429:
            msg = r.text.lower()
            if "per day" in msg or "perday" in msg:
                print("  Gemini daily quota exhausted; rerun later to resume from cache", file=sys.stderr)
                return None
            time.sleep(30 * (attempt + 1))
            continue
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        out = r.json()
        LLM_CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(out))
        return out
    return None


def parse_category(resp: dict | None) -> str | None:
    try:
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        cat = json.loads(text)["category"].strip().lower()
        return cat if cat in CLASSES + ["test_bug"] else None
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None


# ---------- metrics ----------

def f1s(gold: list[str], pred: list[str]) -> dict[str, float]:
    out = {}
    for c in CLASSES:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        out[c] = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
    present = [out[c] for c in CLASSES if c in gold]
    out["macro"] = sum(present) / len(present) if present else float("nan")
    return out


def bootstrap_ci(gold: list[str], pred: list[str], n: int, seed: int = 0) -> dict[str, tuple[float, float]]:
    """95% percentile CIs of macro / per-class F1 over n resamples of test incidents (NaN resamples skipped)."""
    rng = random.Random(seed)
    samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(n):
        idx = [rng.randrange(len(gold)) for _ in gold]
        s = f1s([gold[i] for i in idx], [pred[i] for i in idx])
        for k, v in s.items():
            if v == v:
                samples[k].append(v)
    out = {}
    for k, vs in samples.items():
        vs.sort()
        out[k] = (vs[int(0.025 * len(vs))], vs[min(len(vs) - 1, int(0.975 * len(vs)))])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", type=Path, default=ROOT / "data/processed/failures_labeled_small.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "eval/results_small.md")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--gap-days", type=int, default=3)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--max-lines", type=int, default=80, help="failure-region lines kept per incident")
    ap.add_argument("--llm-n", type=int, default=150, help="max test incidents sent to Gemini")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    ap.add_argument("--min-interval", type=float, default=7.0, help="seconds between Gemini requests (free tier)")
    ap.add_argument("--counts-only", action="store_true", help="print split class counts and exit")
    ap.add_argument("--bootstrap", type=int, default=0, help="resamples for 95%% CIs (0 = no CIs)")
    ap.add_argument("--low-n", type=int, default=15, help="mark classes with fewer test incidents as low n")
    args = ap.parse_args()

    # label censoring: regression labels need up to FIX_WINDOW_DAYS to appear, so newer incidents are biased
    # toward infra/flaky. max_t = latest job start in the input (all records, labeled or not) ~ collection date.
    max_t = max(ts(json.loads(l)["job_started_at"]) for l in args.inp.open())
    censor = max_t - timedelta(days=FIX_WINDOW_DAYS)
    all_incs = incidents(args.inp, args.max_lines)
    incs = [i for i in all_incs if i["t"] <= censor]
    train, test = time_split(incs, args.test_frac, args.gap_days)
    for name, part in [("train", train), ("test", test)]:
        c = Counter(i["y"] for i in part)
        print(f"{name}: n={len(part)} " + " ".join(f"{k}={c[k]}" for k in CLASSES)
              + f" ({part[0]['t']:%Y-%m-%d} .. {part[-1]['t']:%Y-%m-%d})", file=sys.stderr)
    print(f"censoring cutoff {censor:%Y-%m-%d %H:%M} UTC (max_t {max_t:%Y-%m-%d} - {FIX_WINDOW_DAYS} d): "
          f"dropped {len(all_incs) - len(incs)} of {len(all_incs)} labeled incidents", file=sys.stderr)
    if args.counts_only:
        return
    majority = Counter(i["y"] for i in train).most_common(1)[0][0]
    search = bm25_index([i["text"] for i in train])
    hits = [search(q["text"], args.k) for q in test]
    gold = [q["y"] for q in test]

    has_rel = [any(relevant(q, d) for d in train) for q in test]
    hit = [any(relevant(q, train[i]) for i, _ in h) for q, h, r in zip(test, hits, has_rel) if r]
    hit_at_k = sum(hit) / len(hit) if hit else float("nan")

    rows = [("rules (infra patterns, flaky keywords, else train majority)", gold,
             [rules_predict(q, majority) for q in test], None),
            (f"BM25 kNN (k={args.k}, majority vote)", gold, [knn_predict(h, train, majority) for h in hits], hit_at_k)]

    if os.environ.get("GEMINI_API_KEY"):
        idx = sorted(random.Random(0).sample(range(len(test)), min(args.llm_n, len(test))))
        state: dict = {}
        g_gold, g_pred, g_hit, failed = [], [], [], 0
        print(f"{time.strftime('%H:%M:%S')} gemini 0/{len(idx)}", file=sys.stderr, flush=True)
        for n, j in enumerate(idx, 1):
            q = test[j]
            ctx = "\n\n".join(
                f"[{train[i]['id']}] category={train[i]['y']} (label source: {train[i]['source']})"
                f"{' fix touched: ' + ', '.join(train[i]['files']) if train[i]['files'] else ''}\n{train[i]['text'][:1500]}"
                for i, _ in hits[j])
            resp = gemini(PROMPT.format(repo=q["repo"], text=q["text"][:6000], context=ctx), args.model,
                          args.min_interval, state)
            if resp is None:  # daily quota or persistent errors: stop, report what we have (rerun resumes)
                break
            cat = parse_category(resp)
            if cat is None:
                failed += 1
                continue
            g_gold.append(q["y"])
            g_pred.append(cat)
            if has_rel[j]:
                g_hit.append(any(relevant(q, train[i]) for i, _ in hits[j]))
            if n % 5 == 0 or n == len(idx):
                print(f"{time.strftime('%H:%M:%S')} gemini {n}/{len(idx)}", file=sys.stderr, flush=True)
        rows.append((f"{args.model} + RAG (BM25 top-{args.k}), {len(g_gold)} of {len(test)} test incidents"
                     + (f", {failed} unparsed/failed" if failed else ""), g_gold, g_pred,
                     sum(g_hit) / len(g_hit) if g_hit else float("nan")))
    else:
        print("GEMINI_API_KEY not set: skipping Gemini + RAG", file=sys.stderr)

    def fmt(x: float) -> str:
        return "–" if x != x else f"{x:.3f}"

    dist = lambda xs: ", ".join(f"{c} {Counter(xs)[c]}" for c in CLASSES)  # noqa: E731
    lines = [
        "# Fast-track results (mpv, libavif, arrow)",
        "",
        f"Input: `{args.inp.name}`. Unit: incident (matrix duplicates grouped), labeled incidents only "
        f"(regression_strong + regression_weak = regression; no test_bug labels exist).",
        f"Label censoring: incidents after {censor:%Y-%m-%d %H:%M} UTC (latest job start {max_t:%Y-%m-%d} − "
        f"{FIX_WINDOW_DAYS} days fix window) dropped ({len(all_incs) - len(incs)} of {len(all_incs)}), since their "
        f"regression labels may not have appeared yet.",
        f"Time-based split: last {args.test_frac:.0%} of incidents = test "
        f"({test[0]['t']:%Y-%m-%d} – {test[-1]['t']:%Y-%m-%d}), train = incidents before test start − {args.gap_days} days.",
        f"Train n={len(train)} ({dist([i['y'] for i in train])}); test n={len(test)} ({dist(gold)}).",
        f"LLM: `{args.model}` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-{args.k} as context.",
        "",
        "| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, g, p, h in rows:
        s = f1s(g, p)
        ci = bootstrap_ci(g, p, args.bootstrap) if args.bootstrap and g else {}
        counts = Counter(g)

        def cell(k: str) -> str:
            v = fmt(s[k]) + (f" [{ci[k][0]:.2f}–{ci[k][1]:.2f}]" if k in ci else "")
            return v + (f" (low n={counts[k]})" if k in CLASSES and 0 < counts[k] < args.low_n else "")
        lines.append(f"| {name} | {cell('macro')} | {cell('flaky')} | {cell('infra')} | {cell('regression')} "
                     f"| {fmt(h) if h is not None else '–'} | {len(g)} |")
    lines += [
        "",
        f"hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; "
        f"computed only on test incidents with at least one such train incident ({len(hit)} of {len(test)} for BM25).",
        (f"Brackets: 95% bootstrap CI ({args.bootstrap} resamples of test incidents). " if args.bootstrap else "")
        + f"\"low n\": fewer than {args.low_n} test incidents of that class.",
        "Scope: mpv, libavif and arrow only; pydantic, pytest and pytorch will be added when the main labeling "
        "run finishes.",
        "Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is "
        "inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the "
        "log text.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
