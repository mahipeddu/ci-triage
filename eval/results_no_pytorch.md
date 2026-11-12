# Fast-track results (libavif, arrow, mpv, pydantic, pytest)

Input: `failures_labeled.jsonl`, excluding pytorch/pytorch. Unit: incident (matrix duplicates grouped), labeled incidents only (regression_strong + regression_weak = regression; no test_bug labels exist).
Label censoring: incidents after 2026-10-27 11:18 UTC (latest job start 2026-11-10 − 14 days fix window) dropped (805 of 2221), since their regression labels may not have appeared yet.
Time-based split per repo: for each repo, last 30% of its incidents = test, train = its incidents before its test start − 3 days; train and test pooled across repos, BM25 searches the pooled train (cross-repo retrieval). Test starts: libavif 2026-09-21, arrow 2026-10-23, mpv 2026-10-06, pydantic 2026-10-05, pytest 2026-10-04.
Train n=806 (flaky 73, infra 41, regression 692); test n=427 (flaky 46, infra 27, regression 354); test by repo: AOMediaCodec/libavif 64, apache/arrow 57, mpv-player/mpv 44, pydantic/pydantic 178, pytest-dev/pytest 84.
LLM: `gemini-3.5-flash-lite` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-5 as context.

## All test incidents

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| rules (infra patterns, flaky keywords, else train majority) | 0.675 [0.62–0.73] | 0.206 [0.09–0.33] | 0.898 [0.80–0.98] | 0.920 [0.90–0.94] | – | 427 |
| BM25 kNN (k=5, majority vote) | 0.657 [0.56–0.73] | 0.480 [0.33–0.61] | 0.564 [0.33–0.73] | 0.927 [0.91–0.95] | 0.980 (n=153) | 427 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.634 [0.54–0.72] | 0.652 [0.47–0.79] | 0.431 [0.24–0.60] (low n=12) | 0.818 [0.76–0.87] | 0.976 (n=42) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — regression_strong only (weak-labeled test incidents dropped) | 0.680 [0.62–0.74] | 0.250 [0.10–0.39] | 0.898 [0.78–0.98] | 0.891 [0.86–0.92] | – | 269 |
| BM25 kNN (k=5, majority vote) — regression_strong only (weak-labeled test incidents dropped) | 0.661 [0.57–0.74] | 0.529 [0.39–0.66] | 0.564 [0.37–0.74] | 0.891 [0.86–0.92] | 0.990 (n=98) | 269 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample — regression_strong only (weak-labeled test incidents dropped) | 0.695 [0.59–0.79] | 0.714 [0.53–0.86] | 0.564 [0.34–0.73] (low n=12) | 0.807 [0.71–0.88] | 1.000 (n=25) | 95 |

## Per repo

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| libavif: rules (infra patterns, flaky keywords, else train majority) | 0.424 [0.24–0.56] | 0.000 [0.00–0.00] | 0.500 [0.00–0.86] (low n=6) | 0.772 [0.67–0.85] | – | 64 |
| libavif: BM25 kNN (k=5, majority vote) | 0.603 [0.44–0.77] | 0.718 [0.53–0.87] | 0.286 [0.00–0.67] (low n=6) | 0.805 [0.70–0.90] | 1.000 (n=6) | 64 |
| libavif: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.584 [0.50–0.97] | 0.857 [0.67–1.00] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.895 [0.78–0.98] | 1.000 (n=4) | 30 |
| arrow: rules (infra patterns, flaky keywords, else train majority) | 0.734 [0.50–0.85] | 0.333 [0.00–0.62] (low n=6) | 1.000 [1.00–1.00] (low n=2) | 0.870 [0.78–0.93] | – | 57 |
| arrow: BM25 kNN (k=5, majority vote) | 0.375 [0.29–0.65] | 0.222 [0.00–0.57] (low n=6) | 0.000 [0.00–0.00] (low n=2) | 0.902 [0.84–0.95] | 0.923 (n=13) | 57 |
| arrow: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.524 [0.32–0.93] | 0.500 [0.00–1.00] (low n=2) | 0.222 [0.00–0.60] (low n=1) | 0.851 [0.73–0.94] | 1.000 (n=6) | 30 |
| mpv: rules (infra patterns, flaky keywords, else train majority) | 0.617 [0.58–0.65] | 0.000 [0.00–0.00] (low n=8) | 1.000 [1.00–1.00] (low n=9) | 0.852 [0.75–0.94] | – | 44 |
| mpv: BM25 kNN (k=5, majority vote) | 0.659 [0.48–0.83] | 0.429 [0.00–0.73] (low n=8) | 0.714 [0.33–0.94] (low n=9) | 0.833 [0.72–0.93] | 0.889 (n=9) | 44 |
| mpv: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.540 [0.31–0.74] | 0.444 [0.00–0.80] (low n=5) | 0.560 [0.29–0.77] (low n=7) | 0.615 [0.33–0.82] | 0.875 (n=8) | 30 |
| pydantic: rules (infra patterns, flaky keywords, else train majority) | 0.638 [0.58–0.66] | 0.000 [0.00–0.00] (low n=7) | 0.941 [0.77–1.00] (low n=9) | 0.973 [0.95–0.99] | – | 178 |
| pydantic: BM25 kNN (k=5, majority vote) | 0.527 [0.39–0.62] | 0.000 [0.00–0.00] (low n=7) | 0.615 [0.20–0.90] (low n=9) | 0.964 [0.94–0.98] | 1.000 (n=104) | 178 |
| pydantic: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.629 [0.33–0.84] | 0.667 [0.00–1.00] (low n=2) | 0.429 [0.00–0.73] (low n=3) | 0.791 [0.63–0.90] | 1.000 (n=14) | 30 |
| pytest: rules (infra patterns, flaky keywords, else train majority) | 0.844 [0.60–0.94] | 0.571 [0.15–0.86] (low n=6) | 1.000 [1.00–1.00] (low n=1) | 0.961 [0.93–0.99] | – | 84 |
| pytest: BM25 kNN (k=5, majority vote) | 0.654 [0.47–0.66] | 0.000 [0.00–0.00] (low n=6) | 1.000 [1.00–1.00] (low n=1) | 0.963 [0.93–0.99] | 0.952 (n=21) | 84 |
| pytest: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.651 [0.40–0.88] | 0.444 [0.00–0.80] (low n=5) | 0.000 [0.00–0.00] | 0.857 [0.74–0.95] | 1.000 (n=10) | 30 |

hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (n in parentheses).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Gemini: 150 of 150 sampled test incidents scored (stratified sample). Raw answers: flaky 23, infra 39, regression 88, test_bug 0; test_bug is scored as regression (a test bug is fixed by a code change).
Scope: AOMediaCodec/libavif, apache/arrow, mpv-player/mpv, pydantic/pydantic, pytest-dev/pytest. pytorch excluded until re-labeled (all its incidents fall inside the censoring window).
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
