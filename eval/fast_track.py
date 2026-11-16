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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import requests

from collect.github_logs import ROOT, read_log
from collect.label import FIX_WINDOW_DAYS, INFRA, failure_region, module_tokens, normalize, ts

CLASSES = ["flaky", "infra", "regression"]
LABEL_TO_CLASS = {"flaky": "flaky", "infra": "infra", "regression_strong": "regression", "regression_weak": "regression"}
FLAKY_HINT = re.compile(r"flaky|intermittent|timed? ?out|timeout|deadlock|race condition|segmentation fault|"
                        r"connection (reset|refused)|address already in use", re.I)
LLM_CACHE = ROOT / "data/raw/_llm_cache"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TOKEN = re.compile(r"[a-z_][a-z0-9_]+")


# ---------- data ----------

def incidents(path: Path, max_lines: int, exclude: set[str] = frozenset()) -> list[dict]:
    by_inc: dict[str, list[dict]] = defaultdict(list)
    for line in path.open():
        r = json.loads(line)
        if r["label"] in LABEL_TO_CLASS and r["log_path"] and r["repo"] not in exclude:
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
        fix_runs = {j["label_meta"]["fix_sha"]: j["label_meta"]["fix_run_id"] for j in jobs
                    if j["label"].startswith("regression")}
        rel = [j["label_meta"].get("fix_relevant") for j in jobs if j["label"].startswith("regression")]
        all_files = {f for j in jobs if j["label"].startswith("regression") for f in j["label_meta"]["touched_files"]}
        fix_rel = True if True in rel else False if False in rel else None
        out.append({"id": inc, "repo": repo, "t": ts(rep["job_started_at"]), "y": next(iter(classes)),
                    "source": rep["label_source"], "job": rep["job_name"], "steps": rep["failed_steps"],
                    "sig": (rep["job_name"], region[0] if region else ""), "fixes": fixes,
                    "files": sorted({f for j in jobs if j["label"].startswith("regression")
                                     for f in j["label_meta"]["touched_files"]})[:10],
                    "text": f"job: {rep['job_name']}\nfailed steps: {', '.join(rep['failed_steps'])}\n" + "\n".join(region),
                    "n_jobs": len(jobs), "region": region, "url": rep["html_url"], "fix_runs": fix_runs,
                    "fix_relevant": fix_rel, "non_ci_fix": any(not CI_FILE.search(f) for f in all_files),
                    "n_fix_files": len(all_files),
                    "infra_pattern": (rep.get("infra_match") or {}).get("pattern")})
    return sorted(out, key=lambda i: i["t"])


def time_split(incs: list[dict], test_frac: float, gap_days: int) -> tuple[list[dict], list[dict]]:
    test = incs[int(len(incs) * (1 - test_frac)):]
    cutoff = test[0]["t"] - timedelta(days=gap_days)
    return [i for i in incs if i["t"] < cutoff], test


def per_repo_split(incs: list[dict], test_frac: float, gap_days: int) -> tuple[list[dict], list[dict], dict]:
    """time_split within each repo, then pool. Returns pooled train, test (time-sorted) and per-repo test starts."""
    train, test, starts = [], [], {}
    for repo in sorted({i["repo"] for i in incs}):
        tr, te = time_split([i for i in incs if i["repo"] == repo], test_frac, gap_days)
        train += tr
        test += te
        starts[repo] = te[0]["t"]
    return sorted(train, key=lambda i: i["t"]), sorted(test, key=lambda i: i["t"]), starts


# ---------- retrieval ----------

def bm25_index(docs: list[str], times: list | None = None, k1: float = 1.5, b: float = 0.75):
    toks = [TOKEN.findall(d.lower()) for d in docs]
    df = Counter(t for ts_ in toks for t in set(ts_))
    n, avg = len(toks), sum(map(len, toks)) / max(len(toks), 1)
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    tfs = [Counter(t) for t in toks]
    lens = [len(t) for t in toks]

    def search(q: str, k: int, before=None) -> list[tuple[int, float]]:
        """top-k train docs; with before, only docs whose time < before (no retrieval from the future)."""
        qt = set(TOKEN.findall(q.lower()))
        scores = [(i, sum(idf[t] * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * lens[i] / avg))
                          for t in qt if t in tf)) for i, tf in enumerate(tfs)
                  if before is None or times is None or times[i] < before]
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


# v2: definitions phrased the way the auto-labels are produced, plus fixed worked examples from train
PROMPT_V2 = """You triage failed CI jobs. Classify the NEW failure into exactly one category. The categories are
defined by what happened after the failure:
- regression: the failure comes from the code under test. It keeps failing on that commit and passes only after a
  later code change (compile/lint/type errors, reproducible assertion or test failures).
- flaky: the same commit passes when the job is simply re-run (nondeterministic: timing, ordering, races,
  intermittent test failures).
- infra: the CI environment failed, not the code: network errors, HTTP 5xx, DNS, package/dependency/artifact
  download failures, runner lost, out of disk or memory, job-level timeouts. Use infra for these even if a later
  commit happened to pass.
Use the similar past incidents (with their known categories and fixes) as evidence, but judge the new log itself.

WORKED EXAMPLES:
{examples}

NEW FAILURE (repo {repo}):
{text}

SIMILAR PAST INCIDENTS:
{context}

Answer with JSON only: {{"category": "flaky|infra|regression", "likely_cause": "<one sentence>", "similar_incidents": ["<ids of the relevant past incidents>"]}}"""


CI_FILE = re.compile(r"^(\.github/|ci/|\.ci/)|\.(yml|yaml|ps1|sh)$")
EXAMPLE_INFRA_PATTERNS = {"fetch_failed", "http_5xx", "connection", "dns", "truncated_archive"}
FLAKY_EXAMPLE_ID = "25e91f10ff47"  # libavif Windows file lock during link, passed on rerun (reviewed, kept fixed)
NOISE = re.compile(r"process completed with exit code|^\[command\]|git config|post job|cleaning up|^##\[(end)?group\]")
TEST_FAIL = re.compile(r"\bfailed\b|assert|error:", re.I)


def excerpt(region: list[str], anchor: re.Pattern, n: int = 10) -> list[str] | None:
    lines = [l for l in region if not NOISE.search(l)]
    hits = [k for k, l in enumerate(lines) if anchor.search(l)]
    return lines[max(0, hits[-1] - n + 1):hits[-1] + 1] if hits else None


def worked_examples(train: list[dict], seed: int = 0) -> str:
    """One train incident per class, consistent with the v2 definitions; same examples for every query.
    regression: strong label, relevant fix touching at least one non-CI file and at most 10 files (no large
    syncs), error line, no flaky/infra hints;
    flaky: fixed reviewed incident (FLAKY_EXAMPLE_ID), else a rerun-passed failure without network wording;
    infra: download/network/http_5xx pattern match (excerpt ends on it), not a doc/link-check job."""
    infra_rx = re.compile("|".join(f"(?:{rx.pattern})" for _, _, rx in INFRA), re.I)
    net = re.compile(r"ssl|connection|max retries|https?://|timed? ?out|resolve|download|network|socket", re.I)
    joined = lambda i: "\n".join(i["region"])  # noqa: E731
    spec = {
        "regression": (lambda i: i["source"] == "regression_strong" and i["fix_relevant"] is True and i["non_ci_fix"]
                       and i["n_fix_files"] <= 10 and not infra_rx.search(joined(i))
                       and not FLAKY_HINT.search(joined(i)), TEST_FAIL),
        "flaky": (lambda i: i["id"] == FLAKY_EXAMPLE_ID, TEST_FAIL),
        "infra": (lambda i: i["source"] == "infra" and i["infra_pattern"] in EXAMPLE_INFRA_PATTERNS
                  and not re.search(r"doc|link", i["job"], re.I), infra_rx),
    }
    flaky_fallback = lambda i: i["source"] == "rerun" and not infra_rx.search(joined(i)) and not net.search(joined(i))  # noqa: E731
    def fix_files(ex: dict) -> str:  # files sharing a module token with the failure first, non-CI before CI
        toks = set().union(*(module_tokens(l) for l in ex["region"]))
        return ", ".join(sorted(ex["files"], key=lambda f: (not (module_tokens(f) & toks), bool(CI_FILE.search(f))))[:2])

    why = {"regression": lambda ex: f"fixed by a later commit touching {fix_files(ex)}",
           "flaky": lambda ex: "the same commit passed when the job was re-run",
           "infra": lambda ex: "the CI environment failed (network / runner / download / timeout), not the code"}
    out = []
    for c in ("regression", "flaky", "infra"):
        ok, anchor = spec[c]
        pool = [(i, e) for i in train if i["y"] == c and ok(i) and (e := excerpt(i["region"], anchor))]
        if not pool and c == "flaky":
            pool = [(i, e) for i in train if i["y"] == c and flaky_fallback(i) and (e := excerpt(i["region"], anchor))]
        ex, lines = random.Random(f"{seed}:{c}").choice(pool)
        out.append(f"Log ({ex['repo']}, job {ex['job']}):\n" + "\n".join(l[:200] for l in lines)
                   + f"\nAnswer: {{\"category\": \"{c}\", \"likely_cause\": \"{why[c](ex)}\"}}")
    return "\n\n".join(out)


def build_prompt(q: dict, train: list[dict], hits: list[tuple[int, float]], version: str = "v1",
                 examples: str = "", ctx_chars: int = 1500) -> str:
    """The RAG prompt for incident q with retrieved train incidents (shared by teacher, student and eval).
    ctx_chars caps each retrieved incident's log text (the new failure itself is capped separately at 6000)."""
    ctx = "\n\n".join(
        f"[{train[i]['id']}] category={train[i]['y']} (label source: {train[i]['source']})"
        f"{' fix touched: ' + ', '.join(train[i]['files']) if train[i]['files'] else ''}\n{train[i]['text'][:ctx_chars]}"
        for i, _ in hits)
    if version == "v2":
        return PROMPT_V2.format(repo=q["repo"], text=q["text"][:6000], context=ctx, examples=examples)
    return PROMPT.format(repo=q["repo"], text=q["text"][:6000], context=ctx)


def load_split(inp: Path, exclude: set[str], test_frac: float, gap_days: int, max_lines: int = 80):
    """Censored per-repo time split, as used by the eval: (train, test)."""
    max_t = max(ts(r["job_started_at"]) for r in map(json.loads, inp.open()) if r["repo"] not in exclude)
    incs = [i for i in incidents(inp, max_lines, exclude) if i["t"] <= max_t - timedelta(days=FIX_WINDOW_DAYS)]
    train, test, _ = per_repo_split(incs, test_frac, gap_days)
    return train, test


SPEND_LOG = ROOT / "data/raw/gemini_spend.jsonl"  # one line per new (uncached) response: model + token usage


def spend(model: str, price_in: float, price_out: float) -> tuple[float, int]:
    """($ spent on model at the given $/1M prices, number of billed responses), from the ledger."""
    if not SPEND_LOG.exists():
        return 0.0, 0
    rs = [r for r in map(json.loads, SPEND_LOG.open()) if r["model"] == model]
    return sum(r["in"] * price_in + r["out"] * price_out for r in rs) / 1e6, len(rs)


def cache_key_model(model: str, thinking: dict | None) -> str:
    return model if thinking is None else f"{model}|thinking={json.dumps(thinking, sort_keys=True)}"


def cache_path(prompt: str, model: str, thinking: dict | None = None) -> Path:
    key = cache_key_model(model, thinking)
    return LLM_CACHE / (hashlib.sha1(f"{key}\n{prompt}".encode()).hexdigest() + ".json")


GEMINI_LOCK = threading.Lock()  # guards state (throttle, counters, budget) and the spend ledger file


def _budget_reserve(state: dict, model: str) -> bool:
    """Admit one more request if spent + in-flight estimate + this request stays within the cap (thread-safe).
    state["cap"] = (dollars, price_in, price_out); spent is loaded once from the ledger, then tracked in memory."""
    if not state.get("cap"):
        return True
    cap, p_in, p_out = state["cap"]
    with GEMINI_LOCK:
        if "spent" not in state:
            state["spent"], state["n_billed"] = spend(model, p_in, p_out)
            state["inflight"] = 0
        est = state["spent"] / state["n_billed"] if state["n_billed"] else 0.01
        if state.get("budget") or state["spent"] + (state["inflight"] + 1) * est > cap:
            if not state.get("budget"):
                print(f"  budget cap ${cap} reached for {model}: spent ${state['spent']:.3f} over "
                      f"{state['n_billed']} responses, {state['inflight']} in flight", file=sys.stderr, flush=True)
            state["budget"] = True
            return False
        state["inflight"] += 1
        return True


def _budget_settle(state: dict, usage: dict | None) -> None:
    if not state.get("cap"):
        return
    _, p_in, p_out = state["cap"]
    with GEMINI_LOCK:
        state["inflight"] -= 1
        if usage is not None:
            state["spent"] += (usage["in"] * p_in + usage["out"] * p_out) / 1e6
            state["n_billed"] += 1


def gemini(prompt: str, model: str, min_interval: float, state: dict, thinking: dict | None = None) -> dict | None:
    """Cached, throttled, thread-safe Gemini call. min_interval spaces request starts across all threads.
    Returns None on daily quota (state["quota"]), budget cap (state["budget"]) or persistent errors.
    Cache writes are atomic (per-thread tmp file + rename)."""
    f = cache_path(prompt, model, thinking)
    if f.exists():
        return json.loads(f.read_text())
    if not _budget_reserve(state, model):
        return None
    gen = {"temperature": 0, "responseMimeType": "application/json"}  # thinkingConfig: 400 on flash-lite
    if thinking is not None:
        gen["thinkingConfig"] = thinking
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}
    usage = None
    try:
        for attempt in range(6):
            with GEMINI_LOCK:  # reserve a start slot: starts are min_interval apart across threads
                slot = max(time.time(), state.get("last", 0) + min_interval)
                state["last"] = slot
            if slot > time.time():
                time.sleep(slot - time.time())
            try:
                r = requests.post(GEMINI_URL.format(model=model), json=body, timeout=60,
                                  headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
            except requests.RequestException as e:  # includes the 60 s timeout: a hang must not stall the eval
                print(f"  gemini request failed ({type(e).__name__}); retry", file=sys.stderr, flush=True)
                continue
            if r.status_code == 429:
                msg = r.text.lower()
                if "per day" in msg or "perday" in msg:
                    print("  Gemini daily quota exhausted; rerun later to resume from cache", file=sys.stderr)
                    state["quota"] = True
                    return None
                with GEMINI_LOCK:
                    state["n429"] = state.get("n429", 0) + 1
                    n429 = state["n429"]
                print(f"  {time.strftime('%H:%M:%S')} Gemini 429 (rate limit), this worker backs off "
                      f"{30 * (attempt + 1)} s [{n429} so far]: {r.text[:160]!r}", file=sys.stderr, flush=True)
                time.sleep(30 * (attempt + 1))
                continue
            if r.status_code >= 500:
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            out = r.json()
            LLM_CACHE.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(out))
            tmp.replace(f)
            u = out.get("usageMetadata", {})
            usage = {"in": u.get("promptTokenCount", 0),
                     "out": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0),
                     "thoughts": u.get("thoughtsTokenCount", 0)}
            with GEMINI_LOCK, SPEND_LOG.open("a") as sl:
                sl.write(json.dumps({"model": model, "thinking": thinking, **usage, "t": time.time()}) + "\n")
                state["n_api"] = state.get("n_api", 0) + 1  # real (uncached) responses, for concurrency ramp-up
            return out
        return None
    finally:
        _budget_settle(state, usage)


def concurrent_map(fn, items: list, state: dict, workers: int = 8, max_workers: int = 16, raise_after: int = 50):
    """Yield (item, result) as calls complete, running fn(item) on a thread pool: `workers` concurrent calls,
    raised to `max_workers` after `raise_after` real API responses (cache hits don't count) with zero 429s. Stops starting new calls once fn
    returns None for a quota/budget stop (state["quota"] / state["budget"]); already started calls finish.
    Callers do all writes and progress output in the main thread, from the yielded results."""
    slots = threading.Semaphore(workers)
    ctl = {"raised": False}

    def call(item):
        with slots:
            if state.get("quota") or state.get("budget"):
                return item, "skipped"
            res = fn(item)
        with GEMINI_LOCK:
            if not ctl["raised"] and state.get("n_api", 0) >= raise_after and not state.get("n429"):
                ctl["raised"] = True
                for _ in range(max_workers - workers):
                    slots.release()
                print(f"  {time.strftime('%H:%M:%S')} zero 429s after {raise_after} requests: concurrency "
                      f"{workers} -> {max_workers}", file=sys.stderr, flush=True)
        return item, res

    with ThreadPoolExecutor(max_workers) as ex:
        for fut in as_completed([ex.submit(call, it) for it in items]):
            item, res = fut.result()
            if res != "skipped":
                yield item, res


def parse_answer(resp: dict | None) -> tuple[str, str] | None:
    """(raw category, likely_cause) or None if unparseable."""
    try:
        ans = json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])
        cat = ans["category"].strip().lower()
        return (cat, str(ans.get("likely_cause", ""))) if cat in CLASSES + ["test_bug"] else None
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None


def parse_category(resp: dict | None) -> str | None:
    a = parse_answer(resp)
    return a and a[0]


SCORE_MAP = {"test_bug": "regression"}  # a test bug is fixed by a code change; gold has no test_bug class


def stratified(test: list[dict], n: int, seed: int = 0) -> list[int]:
    """Round-robin over repos (shuffled within each repo) so one repo cannot dominate the LLM sample."""
    by_repo: dict[str, list[int]] = defaultdict(list)
    for j, q in enumerate(test):
        by_repo[q["repo"]].append(j)
    rng = random.Random(seed)
    for v in by_repo.values():
        rng.shuffle(v)
    picked: list[int] = []
    while len(picked) < n and any(by_repo.values()):
        for r in sorted(by_repo):
            if by_repo[r] and len(picked) < n:
                picked.append(by_repo[r].pop())
    return sorted(picked)


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
    ap.add_argument("--exclude-repos", nargs="*", default=[], help="repos left out of the eval")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--split", choices=["global", "per-repo"], default="global",
                    help="global: one time cut over all incidents; per-repo: cut each repo on its own timeline, pool")
    ap.add_argument("--gap-days", type=int, default=3)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--max-lines", type=int, default=80, help="failure-region lines kept per incident")
    ap.add_argument("--llm-n", type=int, default=150, help="max test incidents sent to Gemini")
    ap.add_argument("--llm-sample", choices=["random", "stratified"], default="random",
                    help="random: uniform over test incidents; stratified: round-robin over repos")
    ap.add_argument("--cache-only", action="store_true", help="score cached Gemini answers only, no new requests")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    ap.add_argument("--min-interval", type=float, default=7.0, help="seconds between Gemini requests (free tier)")
    ap.add_argument("--counts-only", action="store_true", help="print split class counts and exit")
    ap.add_argument("--bootstrap", type=int, default=0, help="resamples for 95%% CIs (0 = no CIs)")
    ap.add_argument("--low-n", type=int, default=15, help="mark classes with fewer test incidents as low n")
    ap.add_argument("--disagreements", type=Path, help="write Gemini=infra vs label=regression cases here")
    ap.add_argument("--note", default="", help="extra scope note for the results file")
    ap.add_argument("--prompt", choices=["v1", "v2"], default="v1",
                    help="v1: original; v2: label-procedure definitions + 3 worked examples from train")
    ap.add_argument("--summary-json", type=Path, help="write headline numbers (for teacher comparison tables)")
    ap.add_argument("--thinking", type=json.loads, help='thinkingConfig JSON, e.g. \'{"thinkingLevel": "minimal"}\'')
    ap.add_argument("--budget-cap", type=float, help="stop new requests when spend on --model would exceed this ($)")
    ap.add_argument("--workers", type=int, default=8, help="concurrent Gemini calls (raised to --max-workers "
                                                           "after 50 requests with zero 429s)")
    ap.add_argument("--max-workers", type=int, default=16)
    ap.add_argument("--cap-prices", type=float, nargs=2, default=[0.83, 4.13],
                    help="$/1M input, output used to enforce --budget-cap (use the highest listed price)")
    args = ap.parse_args()
    exclude = set(args.exclude_repos)

    # label censoring: regression labels need up to FIX_WINDOW_DAYS to appear, so newer incidents are biased
    # toward infra/flaky. max_t = latest job start in the input (all records of included repos) ~ collection date.
    max_t = max(ts(r["job_started_at"]) for r in map(json.loads, args.inp.open()) if r["repo"] not in exclude)
    censor = max_t - timedelta(days=FIX_WINDOW_DAYS)
    all_incs = incidents(args.inp, args.max_lines, exclude)
    incs = [i for i in all_incs if i["t"] <= censor]
    if args.split == "per-repo":
        train, test, starts = per_repo_split(incs, args.test_frac, args.gap_days)
    else:
        train, test = time_split(incs, args.test_frac, args.gap_days)
        starts = {}
    for name, part in [("train", train), ("test", test)]:
        c = Counter(i["y"] for i in part)
        print(f"{name}: n={len(part)} " + " ".join(f"{k}={c[k]}" for k in CLASSES)
              + f" ({part[0]['t']:%Y-%m-%d} .. {part[-1]['t']:%Y-%m-%d}) by repo {dict(Counter(i['repo'] for i in part))}",
              file=sys.stderr)
    print(f"censoring cutoff {censor:%Y-%m-%d %H:%M} UTC (max_t {max_t:%Y-%m-%d} - {FIX_WINDOW_DAYS} d): "
          f"dropped {len(all_incs) - len(incs)} of {len(all_incs)} labeled incidents", file=sys.stderr)
    if args.counts_only:
        return
    majority = Counter(i["y"] for i in train).most_common(1)[0][0]
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    hits = [search(q["text"], args.k, before=q["t"]) for q in test]  # only train incidents older than the query
    has_rel = [any(relevant(q, d) and d["t"] < q["t"] for d in train) for q in test]
    hit_ok = [any(relevant(q, train[i]) for i, _ in h) for q, h in zip(test, hits)]

    preds: dict[str, dict[int, str]] = {
        "rules": {j: rules_predict(q, majority) for j, q in enumerate(test)},
        "knn": {j: knn_predict(h, train, majority) for j, h in enumerate(hits)},
    }
    names = {"rules": "rules (infra patterns, flaky keywords, else train majority)",
             "knn": f"BM25 kNN (k={args.k}, majority vote)"}
    answers: dict[int, tuple[str, str]] = {}  # test index -> (raw Gemini category, likely_cause)
    llm_note = ""
    if os.environ.get("GEMINI_API_KEY") or args.cache_only:
        idx = (stratified(test, args.llm_n) if args.llm_sample == "stratified"
               else sorted(random.Random(0).sample(range(len(test)), min(args.llm_n, len(test)))))
        state: dict = {"cap": (args.budget_cap, *args.cap_prices)} if args.budget_cap else {}
        failed = missing = 0
        examples = worked_examples(train) if args.prompt == "v2" else ""
        print(f"{time.strftime('%H:%M:%S')} gemini 0/{len(idx)}", file=sys.stderr, flush=True)
        prompts = {j: build_prompt(test[j], train, hits[j], args.prompt, examples) for j in idx}
        todo = [j for j in idx if not args.cache_only or cache_path(prompts[j], args.model, args.thinking).exists()]
        missing = len(idx) - len(todo)
        n = 0
        call = lambda j: gemini(prompts[j], args.model, args.min_interval, state, args.thinking)  # noqa: E731
        for j, resp in concurrent_map(call, todo, state, args.workers, args.max_workers):
            n += 1  # answers keyed by incident: completion order does not affect results
            if resp is None and (state.get("quota") or state.get("budget")):
                continue  # not run (refused by quota / budget), not an unparseable answer
            a = parse_answer(resp) if resp is not None else None
            if a is None:
                failed += 1
            else:
                answers[j] = a
            if n % 5 == 0 or n == len(todo):
                print(f"{time.strftime('%H:%M:%S')} gemini {n}/{len(idx)}", file=sys.stderr, flush=True)
        if state.get("quota") or state.get("budget"):
            print(f"  stopped early ({'daily quota' if state.get('quota') else 'budget cap'}): "
                  f"{len(answers)}/{len(idx)} answered", file=sys.stderr, flush=True)
        if state.get("n429"):
            print(f"  {state['n429']} rate-limit (429) responses during this run", file=sys.stderr, flush=True)
        preds["llm"] = {j: SCORE_MAP.get(c, c) for j, (c, _) in answers.items()}
        names["llm"] = f"{args.model} + RAG (BM25 top-{args.k}), prompt {args.prompt}, {args.llm_sample} sample"
        raw = Counter(c for c, _ in answers.values())
        llm_note = (f"Gemini: {len(answers)} of {len(idx)} sampled test incidents scored ({args.llm_sample} sample"
                    + (f"; {failed} unparseable" if failed else "") + (f"; {missing} not in cache" if missing else "")
                    + f"). Raw answers: {', '.join(f'{c} {raw[c]}' for c in CLASSES + ['test_bug'])}; "
                    f"test_bug is scored as regression (a test bug is fixed by a code change).")
    else:
        print("GEMINI_API_KEY not set: skipping Gemini + RAG", file=sys.stderr)

    def fmt(x: float) -> str:
        return "–" if x != x else f"{x:.3f}"

    sample = set(preds.get("llm", {}))  # the incidents Gemini saw

    def row(label: str, m: str, keep, same_sample: bool = False) -> str:
        js = [j for j in preds[m] if keep(test[j]) and (not same_sample or j in sample)]
        g, p = [test[j]["y"] for j in js], [preds[m][j] for j in js]
        if not g:
            return f"| {label} | – | – | – | – | – | 0 |"
        s = f1s(g, p)
        ci = bootstrap_ci(g, p, args.bootstrap) if args.bootstrap else {}
        counts = Counter(g)
        rel = [hit_ok[j] for j in js if has_rel[j]]
        h = fmt(sum(rel) / len(rel)) + f" (n={len(rel)})" if m != "rules" and rel else "–"

        def cell(k: str) -> str:
            v = fmt(s[k]) + (f" [{ci[k][0]:.2f}–{ci[k][1]:.2f}]" if k in ci else "")
            return v + (f" (low n={counts[k]})" if k in CLASSES and 0 < counts[k] < args.low_n else "")
        return f"| {label} | {cell('macro')} | {cell('flaky')} | {cell('infra')} | {cell('regression')} | {h} | {len(g)} |"

    def paired(js: list[int]) -> dict[str, tuple[float, float, float, float]]:
        """Gemini − kNN F1 on the same incidents: (point, CI low, CI high, share of resamples ≤ 0)."""
        g = [test[j]["y"] for j in js]
        gp, kp = [preds["llm"][j] for j in js], [preds["knn"][j] for j in js]
        rng = random.Random(1)
        diffs: dict[str, list[float]] = defaultdict(list)
        for _ in range(args.bootstrap):
            idx = [rng.randrange(len(js)) for _ in js]
            a = f1s([g[i] for i in idx], [gp[i] for i in idx])
            b = f1s([g[i] for i in idx], [kp[i] for i in idx])
            for k in ("macro", "flaky"):
                if a[k] == a[k] and b[k] == b[k]:
                    diffs[k].append(a[k] - b[k])
        full_a, full_b = f1s(g, gp), f1s(g, kp)
        out = {}
        for k in ("macro", "flaky"):
            d = sorted(diffs[k])
            if not d:  # class absent from every resample (tiny sample)
                out[k] = (full_a[k] - full_b[k], float("nan"), float("nan"), float("nan"))
                continue
            out[k] = (full_a[k] - full_b[k], d[int(0.025 * len(d))], d[min(len(d) - 1, int(0.975 * len(d)))],
                      sum(x <= 0 for x in d) / len(d))
        return out

    paired_lines, paired_res = [], {}
    if sample and args.bootstrap:
        fix_rel_js = sorted(j for j in sample if test[j]["y"] != "regression" or test[j]["fix_relevant"] is True)
        for name, js in [("all", sorted(sample)), ("fix_relevant=true only", fix_rel_js)]:
            paired_res[name] = r = paired(js)
            paired_lines += [f"Paired bootstrap, Gemini − BM25 kNN on the same incidents, {name} "
                             f"(n={len(js)}, {args.bootstrap} resamples):", ""]
            paired_lines += [f"- {k}-F1 difference: {d:+.3f} [{lo:+.3f} – {hi:+.3f}], "
                             f"share of resamples with difference ≤ 0: {sh:.2f}" for k, (d, lo, hi, sh) in r.items()]
            paired_lines.append("")
    header = ["| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |", "|---|---|---|---|---|---|---|"]
    strong_only = lambda q: q["source"] != "regression_weak"  # noqa: E731
    fix_rel_only = lambda q: q["y"] != "regression" or q["fix_relevant"] is True  # noqa: E731
    base = [m for m in preds if m != "llm"]
    repos = sorted({q["repo"] for q in test})
    dist = lambda xs: ", ".join(f"{c} {Counter(xs)[c]}" for c in CLASSES)  # noqa: E731
    lines = [
        f"# Fast-track results ({', '.join(r.split('/')[1] for r in repos)})",
        "",
        f"Input: `{args.inp.name}`" + (f", excluding {', '.join(sorted(exclude))}" if exclude else "")
        + ". Unit: incident (matrix duplicates grouped), labeled incidents only "
        "(regression_strong + regression_weak = regression; no test_bug labels exist).",
        f"Label censoring: incidents after {censor:%Y-%m-%d %H:%M} UTC (latest job start {max_t:%Y-%m-%d} − "
        f"{FIX_WINDOW_DAYS} days fix window) dropped ({len(all_incs) - len(incs)} of {len(all_incs)}), since their "
        f"regression labels may not have appeared yet.",
        (f"Time-based split per repo: for each repo, last {args.test_frac:.0%} of its incidents = test, train = its "
         f"incidents before its test start − {args.gap_days} days; train and test pooled across repos, BM25 searches "
         f"the pooled train (cross-repo retrieval). Test starts: "
         + ", ".join(f"{r.split('/')[1]} {t:%Y-%m-%d}" for r, t in starts.items()) + "."
         if args.split == "per-repo" else
         f"Time-based split: last {args.test_frac:.0%} of incidents = test "
         f"({test[0]['t']:%Y-%m-%d} – {test[-1]['t']:%Y-%m-%d}), train = incidents before test start − {args.gap_days} days."),
        f"Train n={len(train)} ({dist([i['y'] for i in train])}); test n={len(test)} ({dist([q['y'] for q in test])}); "
        f"test by repo: {', '.join(f'{r} {c}' for r, c in sorted(Counter(q['repo'] for q in test).items()))}.",
        f"LLM: `{args.model}` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-{args.k} as context.",
        "",
        "## All test incidents",
        "",
        *header,
        *[row(names[m], m, lambda q: True) for m in preds],
        *([row(names[m] + " — same 150 incidents as Gemini", m, lambda q: True, True) for m in base] if sample else []),
        *[row(names[m] + " — regression_strong only (weak-labeled test incidents dropped)", m, strong_only) for m in preds],
        *[row(names[m] + " — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped)",
              m, fix_rel_only) for m in preds],
        *([row(names[m] + " — fix_relevant=true only, same incidents as Gemini", m, fix_rel_only, True)
           for m in base] if sample else []),
        "",
        *paired_lines,
        "",
        "## Per repo",
        "",
        *header,
        *[row(f"{r.split('/')[1]}: {names[m]}" + (" (Gemini's incidents)" if m != "llm" and sample else ""), m,
              lambda q, r=r: q["repo"] == r, same_sample=bool(sample)) for r in repos for m in preds],
        "",
        "Retrieval is temporal: BM25 only returns train incidents older than the test incident (no cross-repo "
        "future leak), and hit@5 only counts such older train incidents.",
        f"hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; "
        f"computed only on test incidents with at least one such train incident (n in parentheses).",
        (f"Brackets: 95% bootstrap CI ({args.bootstrap} resamples of test incidents). " if args.bootstrap else "")
        + f"\"low n\": fewer than {args.low_n} test incidents of that class.",
        llm_note,
        f"Scope: {', '.join(repos)}." + (f" {args.note}" if args.note else ""),
        "Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is "
        "inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the "
        "log text.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    if args.summary_json and sample:
        js = sorted(sample)
        g = [test[j]["y"] for j in js]
        args.summary_json.write_text(json.dumps({
            "model": args.model, "prompt": args.prompt, "n": len(js),
            "llm": f1s(g, [preds["llm"][j] for j in js]), "knn_same": f1s(g, [preds["knn"][j] for j in js]),
            "llm_ci": bootstrap_ci(g, [preds["llm"][j] for j in js], args.bootstrap) if args.bootstrap else {},
            "paired": paired_res, "raw": dict(Counter(c for c, _ in answers.values())),
            "thinking": args.thinking, "preds": {test[j]["id"]: preds["llm"][j] for j in js},
            "gold": {test[j]["id"]: test[j]["y"] for j in js}}, indent=1))
    print("\n".join(lines))

    if args.disagreements:
        write_disagreements(args.disagreements, test, answers, args)


def write_disagreements(path: Path, test: list[dict], answers: dict[int, tuple[str, str]], args) -> None:
    """Gemini said infra, label says regression: 15 strong + 15 weak, random, with a verdict line to fill in."""
    rng = random.Random(0)
    pick = []
    for src in ("regression_strong", "regression_weak"):
        js = [j for j, (c, _) in sorted(answers.items()) if c == "infra" and test[j]["source"] == src]
        pick += [(src, j) for j in sorted(rng.sample(js, min(15, len(js))))]
    out = [f"# Gemini says infra, label says regression ({len(pick)} cases)", "",
           f"From `{args.out.name}` (model `{args.model}`). Random sample, seed 0: up to 15 regression_strong + "
           "15 regression_weak test incidents where Gemini answered infra.",
           "For each case fill in the verdict: label correct / Gemini correct / unclear.", ""]
    for n, (src, j) in enumerate(pick, 1):
        q = test[j]
        fixes = "\n".join(f"- https://github.com/{q['repo']}/commit/{sha} (fix run "
                          f"https://github.com/{q['repo']}/actions/runs/{q['fix_runs'][sha]})" for sha in sorted(q["fixes"]))
        out += [f"## {n}. {q['repo']} · {src}", "",
                f"- incident `{q['id']}` · {q['t']:%Y-%m-%d %H:%M} UTC · {q['n_jobs']} job(s) · {q['url']}",
                f"- job: `{q['job']}`",
                f"- failed steps: {', '.join(q['steps']) or '–'}",
                f"- Gemini likely_cause: {answers[j][1]}",
                f"- fix commit(s):\n{fixes}",
                f"- touched files: {', '.join(q['files']) or '–'}", "",
                "Failure region (last 25 normalized lines):", "", "```",
                *[l[:220] for l in q["region"][-25:]], "```", "",
                "**verdict: ___**", ""]
    path.write_text("\n".join(out) + "\n")
    print(f"wrote {len(pick)} cases to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
