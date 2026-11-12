# Fast-track results (libavif, arrow, mpv, pydantic, pytest)

Input: `failures_labeled.jsonl`, excluding pytorch/pytorch. Unit: incident (matrix duplicates grouped), labeled incidents only (regression_strong + regression_weak = regression; no test_bug labels exist).
Label censoring: incidents after 2026-10-27 11:18 UTC (latest job start 2026-11-10 − 14 days fix window) dropped (690 of 1897), since their regression labels may not have appeared yet.
Time-based split per repo: for each repo, last 30% of its incidents = test, train = its incidents before its test start − 3 days; train and test pooled across repos, BM25 searches the pooled train (cross-repo retrieval). Test starts: libavif 2026-09-21, arrow 2026-10-23, mpv 2026-10-06, pydantic 2026-10-06, pytest 2026-10-04.
Train n=675 (flaky 59, infra 42, regression 574); test n=364 (flaky 40, infra 27, regression 297); test by repo: AOMediaCodec/libavif 64, apache/arrow 53, mpv-player/mpv 44, pydantic/pydantic 147, pytest-dev/pytest 56.
LLM: `gemini-3.5-flash-lite` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-5 as context.

## All test incidents

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| rules (infra patterns, flaky keywords, else train majority) | 0.679 [0.62–0.74] | 0.226 [0.08–0.36] | 0.898 [0.79–0.97] | 0.914 [0.89–0.94] | – | 364 |
| BM25 kNN (k=5, majority vote) | 0.664 [0.57–0.75] | 0.543 [0.39–0.68] | 0.526 [0.32–0.72] | 0.923 [0.90–0.94] | 0.973 (n=110) | 364 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.631 [0.54–0.72] | 0.732 [0.56–0.87] | 0.353 [0.19–0.52] (low n=10) | 0.808 [0.75–0.86] | 0.919 (n=37) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — same 150 incidents as Gemini | 0.640 [0.54–0.72] | 0.138 [0.00–0.31] | 0.889 [0.67–1.00] (low n=10) | 0.893 [0.85–0.93] | – | 150 |
| BM25 kNN (k=5, majority vote) — same 150 incidents as Gemini | 0.703 [0.55–0.81] | 0.649 [0.43–0.80] | 0.533 [0.17–0.83] (low n=10) | 0.927 [0.89–0.96] | 0.919 (n=37) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — regression_strong only (weak-labeled test incidents dropped) | 0.689 [0.62–0.75] | 0.280 [0.10–0.43] | 0.898 [0.79–0.97] | 0.890 [0.86–0.92] | – | 236 |
| BM25 kNN (k=5, majority vote) — regression_strong only (weak-labeled test incidents dropped) | 0.673 [0.58–0.76] | 0.603 [0.46–0.74] | 0.526 [0.31–0.70] | 0.889 [0.85–0.92] | 0.986 (n=72) | 236 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample — regression_strong only (weak-labeled test incidents dropped) | 0.705 [0.60–0.80] | 0.811 [0.67–0.94] | 0.486 [0.28–0.67] (low n=10) | 0.817 [0.73–0.89] | 0.955 (n=22) | 97 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.672 [0.60–0.74] | 0.280 [0.10–0.44] | 0.898 [0.79–0.98] | 0.838 [0.79–0.88] | – | 176 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.666 [0.57–0.75] | 0.613 [0.45–0.75] | 0.541 [0.33–0.72] | 0.846 [0.80–0.89] | 1.000 (n=37) | 176 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample — fix_relevant=true only (regression incidents whose fix fails the relevance check dropped) | 0.787 [0.66–0.89] | 0.833 [0.67–0.94] | 0.667 [0.40–0.86] (low n=10) | 0.861 [0.77–0.94] | 1.000 (n=12) | 71 |
| rules (infra patterns, flaky keywords, else train majority) — fix_relevant=true only, same incidents as Gemini | 0.625 [0.52–0.73] | 0.182 [0.00–0.40] | 0.889 [0.70–1.00] (low n=10) | 0.804 [0.72–0.88] | – | 71 |
| BM25 kNN (k=5, majority vote) — fix_relevant=true only, same incidents as Gemini | 0.709 [0.54–0.84] | 0.706 [0.50–0.86] | 0.571 [0.18–0.86] (low n=10) | 0.851 [0.77–0.92] | 1.000 (n=12) | 71 |

Paired bootstrap, Gemini − BM25 kNN on the same incidents (n=150, 1000 resamples):

- macro-F1 difference: -0.072 [-0.191 – +0.062], share of resamples with difference ≤ 0: 0.85
- flaky-F1 difference: +0.083 [-0.037 – +0.228], share of resamples with difference ≤ 0: 0.10

## Per repo

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| libavif: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.267 [0.22–0.44] | 0.000 [0.00–0.00] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.800 [0.67–0.91] | – | 30 |
| libavif: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.557 [0.46–0.96] | 0.800 [0.55–0.96] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.872 [0.75–0.97] | 1.000 (n=4) | 30 |
| libavif: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.584 [0.50–0.97] | 0.857 [0.67–1.00] (low n=9) | 0.000 [0.00–0.00] (low n=1) | 0.895 [0.78–0.98] | 1.000 (n=4) | 30 |
| arrow: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.542 [0.40–0.89] | 0.222 [0.00–0.60] (low n=3) | – | 0.863 [0.74–0.95] | – | 30 |
| arrow: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.663 [0.43–0.99] | 0.400 [0.00–1.00] (low n=3) | 0.000 [0.00–0.00] | 0.926 [0.84–0.98] | 0.833 (n=6) | 30 |
| arrow: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.604 [0.35–0.90] | 0.400 [0.00–1.00] (low n=3) | 0.000 [0.00–0.00] | 0.809 [0.67–0.91] | 0.833 (n=6) | 30 |
| mpv: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.619 [0.57–0.65] | 0.000 [0.00–0.00] (low n=5) | 1.000 [1.00–1.00] (low n=6) | 0.857 [0.72–0.95] | – | 30 |
| mpv: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.715 [0.47–0.90] | 0.600 [0.00–0.91] (low n=5) | 0.667 [0.00–1.00] (low n=6) | 0.878 [0.76–0.97] | 0.833 (n=6) | 30 |
| mpv: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.622 [0.39–0.80] | 0.600 [0.00–0.91] (low n=5) | 0.600 [0.29–0.81] (low n=6) | 0.667 [0.43–0.84] | 0.833 (n=6) | 30 |
| pydantic: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.544 [0.31–1.00] | 0.000 [0.00–0.00] (low n=1) | 0.667 [0.00–1.00] (low n=2) | 0.964 [0.91–1.00] | – | 30 |
| pydantic: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.544 [0.30–1.00] | 0.000 [0.00–0.00] (low n=1) | 0.667 [0.00–1.00] (low n=2) | 0.964 [0.91–1.00] | 1.000 (n=17) | 30 |
| pydantic: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.655 [0.38–0.88] | 1.000 [1.00–1.00] (low n=1) | 0.250 [0.00–0.50] (low n=2) | 0.714 [0.53–0.85] | 1.000 (n=17) | 30 |
| pytest: rules (infra patterns, flaky keywords, else train majority) (Gemini's incidents) | 0.821 [0.67–1.00] | 0.500 [0.00–1.00] (low n=1) | 1.000 [1.00–1.00] (low n=1) | 0.963 [0.91–1.00] | – | 30 |
| pytest: BM25 kNN (k=5, majority vote) (Gemini's incidents) | 0.322 [0.30–1.00] | 0.000 [0.00–0.00] (low n=1) | 0.000 [0.00–0.00] (low n=1) | 0.966 [0.91–1.00] | 0.750 (n=4) | 30 |
| pytest: gemini-3.5-flash-lite + RAG (BM25 top-5), stratified sample | 0.634 [0.53–0.98] | 0.667 [0.00–1.00] (low n=1) | 0.333 [0.00–0.80] (low n=1) | 0.902 [0.80–0.98] | 0.750 (n=4) | 30 |

Retrieval is temporal: BM25 only returns train incidents older than the test incident (no cross-repo future leak), and hit@5 only counts such older train incidents.
hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (n in parentheses).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Gemini: 150 of 150 sampled test incidents scored (stratified sample). Raw answers: flaky 22, infra 41, regression 87, test_bug 0; test_bug is scored as regression (a test bug is fixed by a code change).
Scope: AOMediaCodec/libavif, apache/arrow, mpv-player/mpv, pydantic/pydantic, pytest-dev/pytest. pytorch excluded until re-labeled (all its incidents fall inside the censoring window). Aggregator jobs (alls-green check, arrow PR Workflow bot) excluded.
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
