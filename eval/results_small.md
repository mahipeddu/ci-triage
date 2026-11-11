# Fast-track results (mpv, libavif, arrow)

Input: `failures_labeled_small.jsonl`. Unit: incident (matrix duplicates grouped), labeled incidents only (regression_strong + regression_weak = regression; no test_bug labels exist).
Label censoring: incidents after 2026-10-27 08:39 UTC (latest job start 2026-11-10 − 14 days fix window) dropped (448 of 987), since their regression labels may not have appeared yet.
Time-based split: last 30% of incidents = test (2026-10-21 – 2026-10-27), train = incidents before test start − 3 days.
Train n=334 (flaky 73, infra 23, regression 238); test n=162 (flaky 14, infra 11, regression 137).
LLM: `gemini-3.5-flash-lite` (Gemini API free tier, temperature 0, default thinking: thinkingConfig is rejected by this model), BM25 top-5 as context.

| method | macro-F1 | F1 flaky | F1 infra | F1 regression | hit@5 | n |
|---|---|---|---|---|---|---|
| rules (infra patterns, flaky keywords, else train majority) | 0.668 [0.60–0.74] | 0.167 [0.00–0.34] (low n=14) | 0.952 [0.82–1.00] (low n=11) | 0.884 [0.84–0.92] | – | 162 |
| BM25 kNN (k=5, majority vote) | 0.454 [0.34–0.57] | 0.273 [0.00–0.50] (low n=14) | 0.214 [0.00–0.44] (low n=11) | 0.876 [0.84–0.92] | 1.000 | 162 |
| gemini-3.5-flash-lite + RAG (BM25 top-5), 150 of 162 test incidents | 0.295 [0.21–0.40] | 0.143 [0.00–0.40] (low n=12) | 0.196 [0.09–0.30] (low n=9) | 0.546 [0.45–0.63] | 1.000 | 150 |

hit@5: a retrieved train incident has the same fix commit or the same job + normalized first error line; computed only on test incidents with at least one such train incident (5 of 162 for BM25).
Brackets: 95% bootstrap CI (1000 resamples of test incidents). "low n": fewer than 15 test incidents of that class.
Scope: mpv, libavif and arrow only; pydantic, pytest and pytorch will be added when the main labeling run finishes.
Caveats: infra labels come from the same regex patterns the rules baseline uses, so rules F1 for infra is inflated by construction. flaky/regression labels come from rerun / later-commit metadata that is not in the log text.
