# Teacher comparison: model × prompt (Gemini free tier, + RAG with BM25 top-5)

Same per-repo time split, temporal retrieval and aggregator exclusion as `results_no_pytorch.md`. Each block uses one stratified sample of test incidents (round-robin over the 5 repos); the n=60 sample is a strict subset of the n=150 one. kNN columns are BM25 kNN scored on exactly the same incidents.
Paired diff = Gemini − kNN on the same incidents, 95% paired bootstrap CI (1000 resamples); * = CI excludes 0. v1 = original prompt; v2 = label-procedure definitions + 3 worked examples from train.

| model | prompt | n | macro-F1 | flaky F1 | kNN macro / flaky (same n) | paired Δ macro | paired Δ flaky | paired Δ macro, fix_relevant=true | paired Δ macro / flaky vs flash-lite v1 |
|---|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | v1 | 150 | 0.632 [0.53–0.72] | 0.714 [0.53–0.85] | 0.691 / 0.649 | -0.059 [-0.18, +0.08] | +0.066 [-0.06, +0.21] | +0.082 [-0.06, +0.23] | – |
| gemini-3.5-flash-lite | v2 | 150 | 0.598 [0.49–0.70] | 0.516 [0.27–0.71] | 0.691 / 0.649 | -0.093 [-0.23, +0.06] | -0.133 [-0.35, +0.07] | +0.040 [-0.12, +0.21] | -0.034 [-0.12, +0.05] / -0.198 [-0.40, -0.00] * (n=150) |
| gemini-3.8-flash | v1 | 150 | 0.637 [0.53–0.73] | 0.585 [0.38–0.74] | 0.691 / 0.649 | -0.054 [-0.18, +0.08] | -0.063 [-0.20, +0.07] | +0.067 [-0.08, +0.23] | +0.005 [-0.07, +0.08] / -0.129 [-0.27, +0.00] (n=150) |
| gemini-3.5-flash-lite | v1 | 60 | 0.538 [0.39–0.69] | 0.500 [0.15–0.78] | 0.661 / 0.333 | -0.123 [-0.31, +0.11] | +0.167 [-0.11, +0.53] | -0.012 [-0.24, +0.26] | – |
| gemini-3.5-flash-lite | v2 | 60 | 0.494 [0.33–0.65] | 0.333 [0.00–0.67] | 0.661 / 0.333 | -0.167 [-0.39, +0.08] | +0.000 [-0.40, +0.40] | -0.047 [-0.32, +0.23] | -0.044 [-0.17, +0.08] / -0.167 [-0.50, +0.12] (n=60) |
| gemini-3.5-flash | v1, v2 | – | dropped: free-tier quota ~20 requests/day (18 of 60 v1 answers before it ran out) | | | | | | |

**Chosen teacher: gemini-3.5-flash-lite + prompt v1 (v2 is worse on the full 150: macro-F1 0.598 vs 0.632, flaky F1 0.516 vs 0.714)**

Raw answer counts: gemini-3.5-flash-lite v1 n=150: flaky 23, infra 39, regression 88; gemini-3.5-flash-lite v2 n=150: flaky 12, infra 36, regression 102; gemini-3.8-flash v1 n=150 thinking={'thinkingBudget': 0}: flaky 22, infra 28, regression 99, test_bug 1; gemini-3.5-flash-lite v1 n=60: flaky 9, infra 19, regression 32; gemini-3.5-flash-lite v2 n=60: flaky 5, infra 19, regression 36
