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
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.632 [0.53–0.72] | 0.714 [0.53–0.85] | 0.367 [0.18–0.55] (low n=10) | 0.813 [0.76–0.87] | 0.919 (n=37) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — same 150 incidents as Gemini | 0.658 [0.56–0.74] | 0.194 [0.00–0.38] | 0.889 [0.67–1.00] (low n=10) | 0.892 [0.85–0.93] | – | 150 |
| BM25 kNN (k=5, majority vote) — same 150 incidents as Gemini | 0.691 [0.55–0.81] | 0.649 [0.44–0.81] | 0.500 [0.14–0.78] (low n=10) | 0.923 [0.89–0.95] | 0.919 (n=37) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — regression_strong only (weak-labeled test incidents dropped) | 0.622 [0.53–0.70] | 0.275 [0.11–0.43] | 0.714 [0.53–0.86] | 0.877 [0.84–0.91] | – | 237 |
| BM25 kNN (k=5, majority vote) — regression_strong only (weak-labeled test incidents dropped) | 0.680 [0.59–0.76] | 0.581 [0.43–0.73] | 0.571 [0.36–0.74] | 0.886 [0.85–0.92] | 0.986 (n=73) | 237 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample — regression_strong only (weak-labeled test incidents dropped) | 0.700 [0.60–0.80] | 0.811 [0.65–0.93] | 0.474 [0.26–0.67] (low n=10) | 0.816 [0.73–0.89] | 0.958 (n=24) | 100 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.601 [0.52–0.69] | 0.275 [0.11–0.43] | 0.714 [0.53–0.86] | 0.816 [0.76–0.87] | – | 174 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.677 [0.58–0.76] | 0.590 [0.42–0.72] | 0.600 [0.40–0.77] | 0.842 [0.79–0.89] | 1.000 (n=38) | 174 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.776 [0.66–0.87] | 0.811 [0.65–0.93] | 0.667 [0.42–0.86] (low n=10) | 0.850 [0.76–0.92] | 1.000 (n=12) | 72 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only, same incidents as Gemini | 0.655 [0.54–0.76] | 0.261 [0.00–0.48] | 0.889 [0.67–1.00] (low n=10) | 0.816 [0.72–0.89] | – | 72 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only, same incidents as Gemini | 0.694 [0.53–0.81] | 0.706 [0.53–0.86] | 0.533 [0.15–0.80] (low n=10) | 0.842 [0.75–0.91] | 1.000 (n=12) | 72 |

Paired bootstrap, Gemini − BM25 kNN on the same incidents, all (n=150, 1000 resamples):

- macro-F1 difference: -0.059 [-0.183 – +0.082], share of resamples with difference ≤ 0: 0.80
- flaky-F1 difference: +0.066 [-0.062 – +0.206], share of resamples with difference ≤ 0: 0.17

Paired bootstrap, Gemini − BM25 kNN on the same incidents, fix_relevant=true only (n=72, 1000 resamples):

- macro-F1 difference: +0.082 [-0.063 – +0.231], share of resamples with difference ≤ 0: 0.12
- flaky-F1 difference: +0.105 [-0.009 – +0.264], share of resamples with difference ≤ 0: 0.05


## Per repo

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| libavif: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.267 [0.22–0.44] | 0.000 [0.00–0.00] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.800 [0.67–0.91] | – | 30 |
| libavif: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.557 [0.46–0.96] | 0.800 [0.55–0.96] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.872 [0.75–0.97] | 1.000 (n=4) | 30 |
| libavif: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.584 [0.50–0.97] | 0.857 [0.67–1.00] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.895 [0.78–0.98] | 1.000 (n=4) | 30 |
| arrow: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.542 [0.40–0.89] | 0.222 [0.00–0.60] (low n=3) | – | 0.863 [0.74–0.95] | – | 30 |
| arrow: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.653 [0.42–0.98] | 0.400 [0.00–1.00] (low n=3) | 0.000 [0.00–0.00] | 0.906 [0.82–0.98] | 0.833 (n=6) | 30 |
| arrow: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.604 [0.35–0.90] | 0.400 [0.00–1.00] (low n=3) | 0.000 [0.00–0.00] | 0.809 [0.67–0.91] | 0.833 (n=6) | 30 |
| mpv: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.582 [0.48–0.64] | 0.000 [0.00–0.00] (low n=5) | 0.909 [0.67–1.00] (low n=6) | 0.837 [0.70–0.94] | – | 30 |
| mpv: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.715 [0.47–0.90] | 0.600 [0.00–0.91] (low n=5) | 0.667 [0.00–1.00] (low n=6) | 0.878 [0.76–0.97] | 0.833 (n=6) | 30 |
| mpv: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.622 [0.39–0.80] | 0.600 [0.00–0.91] (low n=5) | 0.600 [0.29–0.81] (low n=6) | 0.667 [0.43–0.84] | 0.833 (n=6) | 30 |
| pydantic: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 1.000 [1.00–1.00] | – | 1.000 [1.00–1.00] (low n=1) | 1.000 [1.00–1.00] | – | 30 |
| pydantic: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.492 [0.47–1.00] | – | 0.000 [0.00–0.00] (low n=1) | 0.983 [0.95–1.00] | 1.000 (n=14) | 30 |
| pydantic: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.499 [0.42–0.89] | – | 0.182 [0.00–0.50] (low n=1) | 0.816 [0.68–0.92] | 1.000 (n=14) | 30 |
| pytest: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.837 [0.67–1.00] | 0.571 [0.00–1.00] (low n=2) | 1.000 [1.00–1.00] (low n=2) | 0.939 [0.85–1.00] | – | 30 |
| pytest: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.537 [0.30–1.00] | 0.000 [0.00–0.00] (low n=2) | 0.667 [0.00–1.00] (low n=2) | 0.945 [0.87–1.00] | 0.857 (n=7) | 30 |
| pytest: gemini-3.5-flash-lite + RAG (BM25 top-5), prompt v1, stratified sample | 0.652 [0.49–0.90] | 0.667 [0.00–1.00] (low n=2) | 0.444 [0.00–0.80] (low n=2) | 0.844 [0.71–0.94] | 0.857 (n=7) | 30 |

Retrieval is temporal: BM25 only returns train incidents older than the test incident (no cross-repo future leak), and hit@5 only counts such older train incidents.
hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (n in parentheses).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Gemini: 150 of 150 sampled test incidents scored (stratified sample). Raw answers: flaky 23, infra 39, regression 88, test_bug 0; test_bug is scored as regression (a test bug is fixed by a code change).
Scope: AOMediaCodec/libavif, apache/arrow, mpv-player/mpv, pydantic/pydantic, pytest-dev/pytest. pytorch excluded until re-labeled (all its incidents fall inside the censoring window). Aggregator jobs (alls-green check, arrow PR Workflow bot) excluded.
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
