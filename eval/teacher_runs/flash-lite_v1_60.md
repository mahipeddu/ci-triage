# Fast-track results (libavif, arrow, mpv, pydantic, pytest)

Input: `failures_labeled.jsonl`, excluding pytorch/pytorch. Unit: incident (matrix duplicates grouped), labeled incidents only (regression_strong + regression_weak = regression; no test_bug labels exist).
Label censoring: incidents after 2026-10-27 11:18 UTC (latest job start 2026-11-10 − 14 days fix window) dropped (690 of 1887), since their regression labels may not have appeared yet.
Time-based split per repo: for each repo, last 30% of its incidents = test, train = its incidents before its test start − 3 days; train and test pooled across repos, BM25 searches the pooled train (cross-repo retrieval). Test starts: libavif 2026-09-21, arrow 2026-10-23, mpv 2026-10-06, pydantic 2026-10-06, pytest 2026-10-04.
Train n=665 (flaky 55, infra 39, regression 571); test n=361 (flaky 40, infra 27, regression 294); test by repo: AOMediaCodec/libavif 64, apache/arrow 53, mpv-player/mpv 44, pydantic/pydantic 142, pytest-dev/pytest 58.
LLM: `gemini-3.5-flash-lite` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-5 as context.

## All test incidents

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| rules (infra patterns, flaky keywords, else train majority) | 0.614 [0.54–0.68] | 0.222 [0.07–0.36] | 0.714 [0.53–0.86] | 0.904 [0.88–0.93] | – | 361 |
| BM25 kNN (k=5, majority vote) | 0.671 [0.58–0.74] | 0.522 [0.37–0.66] | 0.571 [0.37–0.74] | 0.920 [0.89–0.94] | 0.973 (n=111) | 361 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.538 [0.39–0.69] | 0.500 [0.15–0.78] (low n=7) | 0.348 [0.10–0.59] (low n=4) | 0.765 [0.66–0.87] | 0.941 (n=17) | 60 |
| rules (infra patterns, flaky keywords, else train majority) — same 150 incidents as Gemini | 0.657 [0.44–0.80] | 0.200 [0.00–0.56] (low n=7) | 0.857 [0.33–1.00] (low n=4) | 0.913 [0.85–0.96] | – | 60 |
| BM25 kNN (k=5, majority vote) — same 150 incidents as Gemini | 0.661 [0.44–0.82] | 0.333 [0.00–0.67] (low n=7) | 0.750 [0.00–1.00] (low n=4) | 0.900 [0.84–0.96] | 0.941 (n=17) | 60 |
| rules (infra patterns, flaky keywords, else train majority) — regression_strong only (weak-labeled test incidents dropped) | 0.622 [0.53–0.70] | 0.275 [0.11–0.43] | 0.714 [0.53–0.86] | 0.877 [0.84–0.91] | – | 237 |
| BM25 kNN (k=5, majority vote) — regression_strong only (weak-labeled test incidents dropped) | 0.680 [0.59–0.76] | 0.581 [0.43–0.73] | 0.571 [0.36–0.74] | 0.886 [0.85–0.92] | 0.986 (n=73) | 237 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample — regression_strong only (weak-labeled test incidents dropped) | 0.620 [0.43–0.79] | 0.615 [0.20–0.91] (low n=7) | 0.444 [0.12–0.71] (low n=4) | 0.800 [0.67–0.90] | 0.917 (n=12) | 43 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.601 [0.52–0.69] | 0.275 [0.11–0.43] | 0.714 [0.53–0.86] | 0.816 [0.76–0.87] | – | 174 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.677 [0.58–0.76] | 0.590 [0.42–0.72] | 0.600 [0.40–0.77] | 0.842 [0.79–0.89] | 1.000 (n=38) | 174 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.688 [0.49–0.86] | 0.615 [0.22–0.89] (low n=7) | 0.615 [0.20–0.86] (low n=4) | 0.833 [0.67–0.95] | 1.000 (n=6) | 31 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only, same incidents as Gemini | 0.653 [0.37–0.84] | 0.250 [0.00–0.67] (low n=7) | 0.857 [0.00–1.00] (low n=4) | 0.851 [0.73–0.94] | – | 31 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only, same incidents as Gemini | 0.701 [0.48–0.87] | 0.400 [0.00–0.75] (low n=7) | 0.857 [0.40–1.00] (low n=4) | 0.844 [0.72–0.95] | 1.000 (n=6) | 31 |

Paired bootstrap, Gemini − BM25 kNN on the same incidents, all (n=60, 1000 resamples):

- macro-F1 difference: -0.123 [-0.306 – +0.108], share of resamples with difference ≤ 0: 0.88
- flaky-F1 difference: +0.167 [-0.114 – +0.533], share of resamples with difference ≤ 0: 0.17

Paired bootstrap, Gemini − BM25 kNN on the same incidents, fix_relevant=true only (n=31, 1000 resamples):

- macro-F1 difference: -0.012 [-0.241 – +0.261], share of resamples with difference ≤ 0: 0.53
- flaky-F1 difference: +0.215 [-0.100 – +0.600], share of resamples with difference ≤ 0: 0.15


## Per repo

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| libavif: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.455 [0.37–1.00] | 0.000 [0.00–0.00] (low n=2) | – | 0.909 [0.74–1.00] (low n=10) | – | 12 |
| libavif: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.621 [0.37–1.00] | 0.400 [0.00–0.86] (low n=2) | – | 0.842 [0.67–1.00] (low n=10) | 1.000 (n=1) | 12 |
| libavif: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.778 [0.56–1.00] | 0.667 [0.00–1.00] (low n=2) | – | 0.889 [0.71–1.00] (low n=10) | 1.000 (n=1) | 12 |
| arrow: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.455 [0.37–1.00] | 0.000 [0.00–0.00] (low n=2) | – | 0.909 [0.74–1.00] (low n=10) | – | 12 |
| arrow: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.671 [0.33–1.00] | 0.500 [0.00–1.00] (low n=2) | 0.000 [0.00–0.00] | 0.842 [0.62–1.00] (low n=10) | 0.667 (n=3) | 12 |
| arrow: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.625 [0.31–0.93] | 0.500 [0.00–1.00] (low n=2) | 0.000 [0.00–0.00] | 0.750 [0.43–0.95] (low n=10) | 0.667 (n=3) | 12 |
| mpv: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.517 [0.22–0.91] | 0.000 [0.00–0.00] (low n=2) | 0.800 [0.00–1.00] (low n=3) | 0.750 [0.46–0.95] (low n=7) | – | 12 |
| mpv: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.541 [0.25–1.00] | 0.000 [0.00–0.00] (low n=2) | 0.800 [0.00–1.00] (low n=3) | 0.824 [0.57–1.00] (low n=7) | – | 12 |
| mpv: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.382 [0.18–0.71] | 0.000 [0.00–0.00] (low n=2) | 0.600 [0.00–0.89] (low n=3) | 0.545 [0.00–0.83] (low n=7) | – | 12 |
| pydantic: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 1.000 [1.00–1.00] | – | – | 1.000 [1.00–1.00] (low n=12) | – | 12 |
| pydantic: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 1.000 [1.00–1.00] | – | – | 1.000 [1.00–1.00] (low n=12) | 1.000 (n=9) | 12 |
| pydantic: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.667 [0.40–0.86] | – | 0.000 [0.00–0.00] | 0.667 [0.40–0.86] (low n=12) | 1.000 (n=9) | 12 |
| pytest: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.871 [0.70–1.00] | 0.667 [0.00–1.00] (low n=1) | 1.000 [1.00–1.00] (low n=1) | 0.947 [0.80–1.00] (low n=10) | – | 12 |
| pytest: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.651 [0.45–1.00] | 0.000 [0.00–0.00] (low n=1) | 1.000 [1.00–1.00] (low n=1) | 0.952 [0.84–1.00] (low n=10) | 1.000 (n=4) | 12 |
| pytest: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.741 [0.59–1.00] | 0.667 [0.00–1.00] (low n=1) | 0.667 [0.00–1.00] (low n=1) | 0.889 [0.71–1.00] (low n=10) | 1.000 (n=4) | 12 |

Retrieval is temporal: BM25 only returns train incidents older than the test incident (no cross-repo future leak), and hit@5 only counts such older train incidents.
hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (n in parentheses).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Gemini: 60 of 60 sampled test incidents scored (stratified sample). Raw answers: flaky 9, infra 19, regression 32, test_bug 0; test_bug is scored as regression (a test bug is fixed by a code change).
Scope: AOMediaCodec/libavif, apache/arrow, mpv-player/mpv, pydantic/pydantic, pytest-dev/pytest.
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
