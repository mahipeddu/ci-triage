# Teacher comparison: model × prompt (Gemini free tier, + RAG with BM25 top-5)

Same per-repo time split, temporal retrieval and aggregator exclusion as `results_no_pytorch.md`. Each block uses one stratified sample of test incidents (round-robin over the 5 repos); the n=60 sample is a strict subset of the n=150 one. kNN columns are BM25 kNN scored on exactly the same incidents.
Paired diff = Gemini − kNN on the same incidents, 95% paired bootstrap CI (1000 resamples); * = CI excludes 0. v1 = original prompt; v2 = label-procedure definitions + 3 worked examples from train.

| model | prompt | n | macro-F1 | flaky F1 | kNN macro / flaky (same n) | paired Δ macro | paired Δ flaky | paired Δ macro, fix_relevant=true |
|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | v1 | 150 | 0.632 [0.53–0.72] | 0.714 [0.53–0.85] | 0.691 / 0.649 | -0.059 [-0.18, +0.08] | +0.066 [-0.06, +0.21] | +0.082 [-0.06, +0.23] |
| gemini-3.5-flash-lite | v2 | 135 of 150 (partial: daily quota) | 0.619 [0.50–0.73] | 0.533 [0.29–0.73] | 0.693 / 0.629 | -0.074 [-0.22, +0.10] | -0.095 [-0.30, +0.10] | +0.054 [-0.12, +0.23] |
| gemini-3.5-flash-lite | v1 | 60 | 0.538 [0.39–0.69] | 0.500 [0.15–0.78] | 0.661 / 0.333 | -0.123 [-0.31, +0.11] | +0.167 [-0.11, +0.53] | -0.012 [-0.24, +0.26] |
| gemini-3.5-flash-lite | v2 | 57 of 60 (partial: daily quota) | 0.499 [0.33–0.66] | 0.333 [0.00–0.67] | 0.659 / 0.333 | -0.160 [-0.37, +0.08] | +0.000 [-0.40, +0.40] | -0.047 [-0.32, +0.23] |
| gemini-3.5-flash | v1, v2 | – | dropped: free-tier quota ~20 requests/day (18 of 60 v1 answers before it ran out) | | | | | |

**Chosen teacher: gemini-3.5-flash-lite + prompt v1 (v2 is no better on macro-F1 and worse on flaky: 0.533 vs 0.714 on the 150 sample)**

Raw answer counts: gemini-3.5-flash-lite v1 n=150: flaky 23, infra 39, regression 88; gemini-3.5-flash-lite v2 n=135: flaky 12, infra 32, regression 91; gemini-3.5-flash-lite v1 n=60: flaky 9, infra 19, regression 32; gemini-3.5-flash-lite v2 n=57: flaky 5, infra 18, regression 34
