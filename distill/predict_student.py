"""Student predictions on the eval's 150 stratified test incidents, by log-prob scoring (no free-text parsing).

For each incident, the 3 candidate completions are scored by total log-prob given the prompt (prompt forward pass
once, candidates continue from its KV cache); prediction = argmax, probabilities = softmax over the 3 totals.
  labels student:    candidate = '{"category": "<c>"}' + end-of-turn (its training target)
  rationale student: candidate = '{"category": "<c>", ' (prefix of its target); plus greedy generation for
                     likely_cause (timed separately)
Output: data/processed/student_preds_<name>.jsonl
Usage: .venv/bin/python -m distill.predict_student --adapter data/models/student_labels/adapter --target labels
"""
import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path

from collect.github_logs import ROOT
from distill.train_student import MODEL, fit_prompt
from eval.fast_track import bm25_index, load_split, stratified

CLASSES = ["flaky", "infra", "regression"]


def candidate(c: str, target: str, eot: str) -> str:
    return json.dumps({"category": c}) + eot if target == "labels" else f'{{"category": "{c}", '


def load(adapter: Path, model_name: str = MODEL):
    """(tokenizer, 4-bit NF4 base model + LoRA adapter in eval mode) on GPU 0."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(adapter)
    base = AutoModelForCausalLM.from_pretrained(
        model_name, dtype=torch.bfloat16, device_map={"": 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                               bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True))
    return tok, PeftModel.from_pretrained(base, adapter).eval()


def candidate_ids(tok, target: str) -> dict:
    eot = tok.eos_token if target == "labels" else ""
    return {c: tok(candidate(c, target, eot), add_special_tokens=False, return_tensors="pt").input_ids.to(0)
            for c in CLASSES}


def prompt_ids(tok, prompt: str):
    return tok.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                   tokenize=True, return_dict=False, return_tensors="pt").to(0)


def score(model, ids, cand_ids: dict) -> tuple[dict, dict]:
    """(softmax probs, total log-probs) of the candidate completions. Call under torch.inference_mode()."""
    import torch
    pre = model(ids, use_cache=True)
    logp = {}
    for c, cid in cand_ids.items():
        # first candidate token from the prompt's last logits, the rest from continuing the cached prompt
        lp = torch.log_softmax(pre.logits[0, -1].float(), -1)[cid[0, 0]].item()
        if cid.shape[1] > 1:
            o = model(cid[:, :-1], past_key_values=copy.deepcopy(pre.past_key_values), use_cache=True)
            lps = torch.log_softmax(o.logits[0].float(), -1)
            lp += lps.gather(1, cid[0, 1:, None]).sum().item()
        logp[c] = lp
    m = max(logp.values())
    z = sum(math.exp(v - m) for v in logp.values())
    return {c: math.exp(v - m) / z for c, v in logp.items()}, logp


def generate(model, tok, ids, max_new_tokens: int = 96) -> tuple[str, str | None]:
    """Greedy completion and its likely_cause (None if the completion is not valid JSON)."""
    gen = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
    text = tok.decode(gen[0, ids.shape[1]:], skip_special_tokens=True)
    try:
        return text, json.loads(text).get("likely_cause")
    except (ValueError, AttributeError):
        return text, None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--target", choices=["labels", "rationale"], required=True)
    ap.add_argument("--name", help="output name (default: adapter's parent dir name)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--llm-n", type=int, default=150)
    ap.add_argument("--max-new-tokens", type=int, default=96)
    args = ap.parse_args()
    name = args.name or args.adapter.parent.name
    out = ROOT / f"data/processed/student_preds_{name}.jsonl"

    import torch
    tok, model = load(args.adapter, args.model)
    train, test = load_split(ROOT / "data/processed/failures_labeled.jsonl", {"pytorch/pytorch"}, 0.3, 3)
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    idx = stratified(test, args.llm_n)
    cand_ids = candidate_ids(tok, args.target)

    with out.open("w") as f, torch.inference_mode():
        for n, j in enumerate(idx, 1):
            q = test[j]
            prompt, _ = fit_prompt(q, train, search(q["text"], 5, before=q["t"]), tok, args.max_len - 64)
            ids = prompt_ids(tok, prompt)
            torch.cuda.synchronize()
            t0 = time.time()
            probs, logp = score(model, ids, cand_ids)
            torch.cuda.synchronize()
            score_s = time.time() - t0
            rec = {"id": q["id"], "repo": q["repo"], "label": q["y"], "pred": max(probs, key=probs.get),
                   "probs": probs, "logp": logp, "score_latency_s": round(score_s, 3), "prompt_tokens": ids.shape[1]}
            if args.target == "rationale":
                t0 = time.time()
                rec["generated"], rec["likely_cause"] = generate(model, tok, ids, args.max_new_tokens)
                torch.cuda.synchronize()
                rec["gen_latency_s"] = round(time.time() - t0, 3)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if n % 10 == 0 or n == len(idx):
                print(f"{time.strftime('%H:%M:%S')} predicted {n}/{len(idx)}", file=sys.stderr, flush=True)
    print(f"wrote {len(idx)} predictions to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
