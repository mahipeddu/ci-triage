# CI Failure Triage (RAG)

Retrieval-augmented triage of CI test failures: given a failed job log, retrieve similar past failures and their resolutions, then classify and explain the failure.

## Goal
For each failed CI job, output:
```json
{"category": "flaky|infra|regression|test_bug", "likely_cause": "...", "similar_incidents": ["..."], "suggested_owner": "..."}
```

## Code style
- Minimal and functional. Only write what the current task needs: no speculative abstractions, no extra config layers, no unused helpers.
- Plain Python scripts + small modules. Type hints, no classes unless state is unavoidable.
- Every script runnable from CLI with argparse.
- Secrets via env vars only (`GITHUB_TOKEN`, LLM API key). Never commit them.

## Structure
```
collect/      # data collection (GitHub Actions API, LogChunks loader)
triage/       # clean.py, chunk.py, index.py, triage.py
eval/         # metrics, baselines, ablations
data/raw/     # gitignored
data/processed/
app.py        # Streamlit demo
```

## Data sources
1. **GitHub Actions logs** from 3–5 active OSS repos with large test suites.
   - Runs: `GET /repos/{o}/{r}/actions/runs?status=failure`
   - Attempts: `GET /repos/{o}/{r}/actions/runs/{id}/attempts/{n}`
   - Jobs: `GET /repos/{o}/{r}/actions/runs/{id}/jobs`
   - Logs: `GET /repos/{o}/{r}/actions/jobs/{job_id}/logs`
   - Logs expire (default retention ~90 days) → only recent runs; save raw logs to disk immediately.
   - Respect rate limits (5000 req/h authenticated); cache responses, resume on restart.
2. **LogChunks** (Zenodo record 3632351): 797 Travis logs with labeled failure chunks → evaluates chunk extraction only.
3. **FFmpeg FATE tickets** (optional, trac.ffmpeg.org, component=fate): small video-domain case study.

## Auto-labeling rules
- **flaky**: same run, earlier attempt failed, later attempt succeeded, same commit SHA.
- **regression**: failed on commit X, a later commit on the same branch fixed it (same job name now passes) → store fix commit + touched files.
- **infra**: failure chunk matches infra patterns (timeout, network, runner/disk, dependency download) — rule-based, spot-check manually.
- Unlabeled stays unlabeled; never guess.

## Pipeline
1. clean: strip ANSI + timestamps; normalize paths, hex, numbers, UUIDs.
2. chunk: extract the failure chunk (heuristics first; evaluate on LogChunks).
3. index: hybrid BM25 + dense embeddings over past failure chunks + resolution metadata.
4. triage: top-k retrieval → LLM → JSON above. Owner from CODEOWNERS / files touched by past fixes.

## Evaluation (required, not optional)
- Category macro-F1 vs baselines: (a) regex rules, (b) kNN majority vote, no LLM.
- Hit@k: true fix/incident in retrieved top-k.
- Chunk extraction accuracy on LogChunks.
- Ablations: BM25 vs dense vs hybrid; with/without normalization.
- Time-based split (train on older failures, test on newer) — no random split, avoids leakage.

## Milestones
1. Collector + auto-labeling
2. Clean, chunk, index
3. LLM triage + baselines
4. Eval, ablations, Streamlit demo, README with results table

## Models
- Teacher: Gemini Flash, FREE TIER ONLY. Throttle requests, cache every response to disk, resume on restart. Low thinking budget.
- Student: 3–8B instruct model, QLoRA on RTX 5080 (16 GB). Same RAG context at inference.
- Compare: regex, kNN, teacher+RAG, student+RAG on time-based test split (F1, hit@k, latency).

## Repos
mpv-player/mpv, AOMediaCodec/libavif, apache/arrow, pytest-dev/pytest, pydantic/pydantic, pytorch/pytorch

## Extra flaky source (pytorch)
pytorch-bot opens issues titled "DISABLED <test_name> (<class>)" for flaky tests. A failure whose failing test matches such an issue (open at failure time) → label flaky. Treat as higher-confidence than rerun-based labels.
PyTorch logs are very large and runs are high-volume: store only the failure chunk + 200 lines of context, not full logs.
For pytorch/pytorch: only collect runs from workflows pull.yml and trunk.yml (use /actions/workflows/{file}/runs?status=failure). Ignore other workflows. Cap at 500 failed runs per workflow for now.
