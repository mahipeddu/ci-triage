# Students vs baselines (same 150 stratified test incidents)

Split, censoring, aggregator exclusion and temporal BM25 retrieval as in `results_no_pytorch.md`; the same 150 incidents (round-robin over the 5 repos) for every method. Students: Qwen3-4B-Instruct-2507 + QLoRA, category by log-prob scoring of the 3 candidate completions (argmax; nothing unparseable). 95% bootstrap CIs, 1000 resamples.

| method | n | macro-F1 | F1 flaky | F1 infra | F1 regression |
|---|---|---|---|---|---|
| BM25 kNN | 150 | 0.691 [0.55–0.81] | 0.649 [0.44–0.81] | 0.500 [0.14–0.78] | 0.923 [0.89–0.95] |
| teacher gemini-3.5-flash-lite v1 | 150 | 0.632 [0.53–0.72] | 0.714 [0.53–0.85] | 0.367 [0.18–0.55] | 0.813 [0.76–0.87] |
| student labels | 150 | 0.704 [0.56–0.80] | 0.510 [0.33–0.64] | 0.706 [0.36–0.93] | 0.897 [0.85–0.93] |
| student rationale | 150 | 0.792 [0.68–0.88] | 0.703 [0.51–0.85] | 0.741 [0.52–0.90] | 0.932 [0.89–0.96] |
| student rationale+rationalized | 150 | 0.735 [0.61–0.83] | 0.591 [0.41–0.74] | 0.696 [0.40–0.89] | 0.918 [0.88–0.95] |

Test classes in the sample: {'regression': 121, 'flaky': 19, 'infra': 10}.

## Paired differences (same incidents)

| comparison | n | Δ macro-F1 | Δ flaky F1 |
|---|---|---|---|
| student labels − BM25 kNN | 150 | +0.014 [-0.08, +0.13] | -0.139 [-0.29, +0.00] |
| student labels − teacher gemini-3.5-flash-lite v1 | 150 | +0.072 [-0.05, +0.19] | -0.204 [-0.37, -0.05] * |
| student rationale − BM25 kNN | 150 | +0.101 [-0.02, +0.24] | +0.054 [-0.02, +0.15] |
| student rationale − teacher gemini-3.5-flash-lite v1 | 150 | +0.160 [+0.09, +0.24] * | -0.012 [-0.15, +0.11] |
| student rationale+rationalized − BM25 kNN | 150 | +0.044 [-0.07, +0.17] | -0.058 [-0.16, +0.05] |
| student rationale+rationalized − teacher gemini-3.5-flash-lite v1 | 150 | +0.103 [+0.01, +0.18] * | -0.123 [-0.26, +0.00] |

\* = CI excludes 0.

## Calibration: student labels

Confidence = probability of the predicted class (softmax over the 3 candidate log-probs).

| confidence bin | n | mean confidence | accuracy |
|---|---|---|---|
| 0.0–0.5 | 2 | 0.500 | 0.500 |
| 0.5–0.7 | 18 | 0.597 | 0.611 |
| 0.7–0.9 | 35 | 0.805 | 0.571 |
| 0.9–1.0 | 95 | 0.985 | 0.958 |

ECE (expected calibration error, 4 bins): 0.073

Mean predicted probability per class, by gold class:

| gold \ predicted p | flaky | infra | regression | n |
|---|---|---|---|---|
| flaky | 0.520 | 0.045 | 0.435 | 19 |
| infra | 0.205 | 0.603 | 0.192 | 10 |
| regression | 0.144 | 0.002 | 0.854 | 121 |

## Calibration: student rationale

Confidence = probability of the predicted class (softmax over the 3 candidate log-probs).

| confidence bin | n | mean confidence | accuracy |
|---|---|---|---|
| 0.0–0.5 | 0 | – | – |
| 0.5–0.7 | 4 | 0.562 | 0.750 |
| 0.7–0.9 | 11 | 0.828 | 0.545 |
| 0.9–1.0 | 135 | 0.987 | 0.919 |

ECE (expected calibration error, 4 bins): 0.087

Mean predicted probability per class, by gold class:

| gold \ predicted p | flaky | infra | regression | n |
|---|---|---|---|---|
| flaky | 0.630 | 0.058 | 0.312 | 19 |
| infra | 0.009 | 0.974 | 0.017 | 10 |
| regression | 0.054 | 0.050 | 0.897 | 121 |

## Calibration: student rationale+rationalized

Confidence = probability of the predicted class (softmax over the 3 candidate log-probs).

| confidence bin | n | mean confidence | accuracy |
|---|---|---|---|
| 0.0–0.5 | 0 | – | – |
| 0.5–0.7 | 11 | 0.612 | 0.364 |
| 0.7–0.9 | 47 | 0.818 | 0.809 |
| 0.9–1.0 | 92 | 0.959 | 0.935 |

ECE (expected calibration error, 4 bins): 0.036

Mean predicted probability per class, by gold class:

| gold \ predicted p | flaky | infra | regression | n |
|---|---|---|---|---|
| flaky | 0.701 | 0.048 | 0.251 | 19 |
| infra | 0.186 | 0.799 | 0.015 | 10 |
| regression | 0.160 | 0.031 | 0.808 | 121 |

## Latency and cost per 1k incidents

| method | median latency / incident | cost per 1k incidents |
|---|---|---|
| BM25 kNN | < 0.1 s (CPU) | $0 |
| student labels (RTX 5080, 4-bit) | 0.60 s category scoring | $0 API (local GPU) |
| student rationale (RTX 5080, 4-bit) | 0.60 s category scoring; 1.99 s with generated likely_cause | $0 API (local GPU) |
| student rationale+rationalized (RTX 5080, 4-bit) | 0.61 s category scoring; 2.07 s with generated likely_cause | $0 API (local GPU) |
| teacher gemini-3.5-flash-lite | not measured here (free-tier latency varied 2–100 s per request; paid tier ~1 request/s sustained) | $1.31 on the paid tier (mean 3619 input + 88 output tokens per incident at $0.3/M in, $2.5/M out); $0 on the free tier within its daily quota |

Teacher prices: third-party aggregators citing Google's rate sheet (Oct 2026); verify against ai.google.dev/gemini-api/docs/pricing.

