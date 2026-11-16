"""Streamlit demo: paste a failed CI job log -> top-5 similar past incidents, BM25 kNN prediction, and the local
rationale student's category (log-prob scoring, with confidence) and generated likely_cause.

Past incidents = all censored, labeled incidents of the 5 eval repos (pytorch excluded), from
data/processed/failures_labeled.jsonl + data/raw logs. Student = Qwen3-4B-Instruct-2507 4-bit + the LoRA adapter in
data/models/student_rationale/adapter (not committed; see README to retrain).
Usage: .venv/bin/streamlit run app.py
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import streamlit as st

from collect.github_logs import ROOT
from collect.label import failure_region, normalize
from eval.fast_track import bm25_index, knn_predict, load_split

ADAPTER = ROOT / "data/models/student_rationale/adapter"
REPOS = ["AOMediaCodec/libavif", "apache/arrow", "mpv-player/mpv", "pydantic/pydantic", "pytest-dev/pytest"]


@st.cache_resource(show_spinner="Loading past incidents and building the BM25 index…")
def history() -> tuple[list[dict], object, str]:
    train, test = load_split(ROOT / "data/processed/failures_labeled.jsonl", {"pytorch/pytorch"}, 0.3, 3)
    past = sorted(train + test, key=lambda i: i["t"])
    return past, bm25_index([i["text"] for i in past]), Counter(i["y"] for i in past).most_common(1)[0][0]


@st.cache_resource(show_spinner="Loading the student (4-bit) on the GPU…")
def student(adapter: Path):
    from distill.predict_student import candidate_ids, load
    tok, model = load(adapter)
    return tok, model, candidate_ids(tok, "rationale")


def incident_text(log: str, job: str, steps: str, max_lines: int = 80) -> str:
    """Same text the eval builds for an incident: job, failed steps, normalized failure region (last 80 lines)."""
    region = [l for l in (normalize(x) for x in failure_region(log.splitlines())) if l][-max_lines:]
    return f"job: {job}\nfailed steps: {steps}\n" + "\n".join(region)


def triage_student(q: dict, past: list[dict], hits: list, adapter: Path) -> dict:
    import torch
    from distill.predict_student import generate, prompt_ids, score
    from distill.train_student import fit_prompt
    tok, model, cand = student(adapter)
    prompt, _ = fit_prompt(q, past, hits, tok, 4096 - 64)
    with torch.inference_mode():
        ids = prompt_ids(tok, prompt)
        t0 = time.time()
        probs, _ = score(model, ids, cand)
        t1 = time.time()
        raw, cause = generate(model, tok, ids)
    return {"probs": probs, "pred": max(probs, key=probs.get), "likely_cause": cause, "raw": raw,
            "score_s": t1 - t0, "gen_s": time.time() - t1}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", type=Path, default=ADAPTER)
    args = ap.parse_args(sys.argv[1:])  # streamlit run app.py -- --adapter <dir>

    st.set_page_config(page_title="CI failure triage", layout="wide")
    st.title("CI failure triage")
    st.caption("Retrieval over past failures of libavif, arrow, mpv, pydantic and pytest + a fine-tuned 4B student.")
    c1, c2, c3 = st.columns([1, 1, 1])
    repo = c1.selectbox("repo", REPOS + ["other"])
    job = c2.text_input("job name", placeholder="e.g. build (ubuntu-py314)")
    steps = c3.text_input("failed step(s)", placeholder="e.g. Test")
    log = st.text_area("failed job log (raw GitHub Actions log, or just the failing part)", height=260)
    use_student = st.checkbox("run the student (GPU)", value=args.adapter.exists(), disabled=not args.adapter.exists(),
                              help=None if args.adapter.exists() else f"no adapter at {args.adapter}; see README")
    if not st.button("Triage", type="primary") or not log.strip():
        return

    past, search, majority = history()
    q = {"repo": repo, "text": incident_text(log, job, steps)}
    hits = search(q["text"], 5)
    knn = knn_predict(hits, past, majority)

    left, right = st.columns(2)
    left.subheader("BM25 kNN (k=5, majority vote)")
    left.metric("category", knn)
    if use_student:
        with st.spinner("Student scoring + generating…"):
            s = triage_student(q, past, hits, args.adapter)
        right.subheader("Student (Qwen3-4B + QLoRA, rationale)")
        right.metric("category", s["pred"], f"confidence {s['probs'][s['pred']]:.2f}", delta_color="off")
        right.write(f"**likely cause:** {s['likely_cause'] or '(unparseable: ' + s['raw'] + ')'}")
        right.caption(" · ".join(f"p({c}) = {p:.3f}" for c, p in s["probs"].items())
                      + f" · scoring {s['score_s']:.2f} s, generation {s['gen_s']:.2f} s")

    st.subheader("Top-5 similar past incidents")
    st.dataframe([{"score": round(sc, 1), "category": past[i]["y"], "label source": past[i]["source"],
                   "repo": past[i]["repo"], "job": past[i]["job"], "date": past[i]["t"].strftime("%Y-%m-%d"),
                   "first line": past[i]["region"][0][:120] if past[i]["region"] else "",
                   "fix touched": ", ".join(past[i]["files"][:3]), "log": past[i]["url"]} for i, sc in hits],
                 column_config={"log": st.column_config.LinkColumn("log")}, hide_index=True)
    with st.expander("extracted failure text (what retrieval and the student see)"):
        st.code(q["text"])


if __name__ == "__main__":
    main()
