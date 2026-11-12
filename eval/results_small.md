# Fast-track results (libavif, arrow, mpv)

Input: `failures_labeled_small.jsonl`. Unit: incident (matrix duplicates grouped), labeled incidents only (regression_strong + regression_weak = regression; no test_bug labels exist).
Label censoring: incidents after 2026-10-27 08:39 UTC (latest job start 2026-11-10 − 14 days fix window) dropped (448 of 987), since their regression labels may not have appeared yet.
Time-based split: last 30% of incidents = test (2026-10-21 – 2026-10-27), train = incidents before test start − 3 days.
Train n=334 (flaky 73, infra 23, regression 238); test n=162 (flaky 14, infra 11, regression 137); test by repo: AOMediaCodec/libavif 2, apache/arrow 144, mpv-player/mpv 16.
LLM: `gemini-3.5-flash-lite` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-5 as context.

## All test incidents

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| rules (infra patterns, flaky keywords, else train majority) | 0.668 [0.60–0.74] | 0.167 [0.00–0.34] (low n=14) | 0.952 [0.82–1.00] (low n=11) | 0.884 [0.84–0.92] | – | 162 |
| BM25 kNN (k=5, majority vote) | 0.454 [0.34–0.57] | 0.273 [0.00–0.50] (low n=14) | 0.214 [0.00–0.44] (low n=11) | 0.876 [0.84–0.92] | 1.000 (n=5) | 162 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), random sample | 0.322 [0.24–0.42] | 0.143 [0.00–0.40] (low n=12) | 0.196 [0.09–0.30] (low n=9) | 0.629 [0.55–0.70] | 1.000 (n=5) | 150 |
| rules (infra patterns, flaky keywords, else train majority) — regression_strong only (weak-labeled test incidents dropped) | 0.681 [0.60–0.77] | 0.231 [0.00–0.45] (low n=14) | 0.952 [0.82–1.00] (low n=11) | 0.861 [0.79–0.92] | – | 99 |
| BM25 kNN (k=5, majority vote) — regression_strong only (weak-labeled test incidents dropped) | 0.464 [0.34–0.58] | 0.316 [0.00–0.56] (low n=14) | 0.250 [0.00–0.48] (low n=11) | 0.826 [0.75–0.89] | 1.000 (n=4) | 99 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), random sample — regression_strong only (weak-labeled test incidents dropped) | 0.354 [0.25–0.48] | 0.154 [0.00–0.44] (low n=12) | 0.290 [0.15–0.45] (low n=9) | 0.617 [0.50–0.72] | 1.000 (n=4) | 91 |

## Per repo

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| libavif: rules (infra patterns, flaky keywords, else train majority) | 0.500 [0.00–1.00] | 0.000 [0.00–0.00] (low n=1) | 1.000 [1.00–1.00] (low n=1) | 0.000 [0.00–0.00] | – | 2 |
| libavif: BM25 kNN (k=5, majority vote) | 1.000 [1.00–1.00] | 1.000 [1.00–1.00] (low n=1) | 1.000 [1.00–1.00] (low n=1) | – | – | 2 |
| libavif: gemini-3.5-flash-lite + RAG (BM25 top-5), random sample | 1.000 [1.00–1.00] | 1.000 [1.00–1.00] (low n=1) | – | – | – | 1 |
| arrow: rules (infra patterns, flaky keywords, else train majority) | 0.662 [0.55–0.75] | 0.188 [0.00–0.37] (low n=10) | 0.909 [0.67–1.00] (low n=6) | 0.890 [0.85–0.93] | – | 144 |
| arrow: BM25 kNN (k=5, majority vote) | 0.335 [0.28–0.42] | 0.125 [0.00–0.38] (low n=10) | 0.000 [0.00–0.00] (low n=6) | 0.881 [0.84–0.92] | – | 144 |
| arrow: gemini-3.5-flash-lite + RAG (BM25 top-5), random sample | 0.263 [0.22–0.31] | 0.000 [0.00–0.00] (low n=8) | 0.148 [0.05–0.25] (low n=6) | 0.640 [0.55–0.72] | – | 134 |
| mpv: rules (infra patterns, flaky keywords, else train majority) | 0.619 [0.53–1.00] | 0.000 [0.00–0.00] (low n=3) | 1.000 [1.00–1.00] (low n=4) | 0.857 [0.63–1.00] (low n=9) | – | 16 |
| mpv: BM25 kNN (k=5, majority vote) | 0.662 [0.31–0.92] | 0.500 [0.00–1.00] (low n=3) | 0.667 [0.00–1.00] (low n=4) | 0.818 [0.60–0.96] (low n=9) | 1.000 (n=5) | 16 |
| mpv: gemini-3.5-flash-lite + RAG (BM25 top-5), random sample | 0.348 [0.17–0.54] | 0.000 [0.00–0.00] (low n=3) | 0.545 [0.00–0.86] (low n=3) | 0.500 [0.15–0.75] (low n=9) | 1.000 (n=5) | 15 |

hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (n in parentheses).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Gemini: 150 of 150 sampled test incidents scored (random sample). Raw answers: flaky 2, infra 83, regression 54, test_bug 11; test_bug is scored as regression (a test bug is fixed by a code change).
Scope: AOMediaCodec/libavif, apache/arrow, mpv-player/mpv. pydantic and pytest: see results_no_pytorch.md. pytorch excluded until re-labeled (all its incidents fall inside the censoring window).
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
