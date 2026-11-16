"""QLoRA fine-tune of the student on RAG prompts (same v1 prompt as the teacher: failure + temporal BM25 top-5).

--target labels:    completion = {"category": <auto-label>}
--target rationale: completion = teacher JSON {"category", "likely_cause"} for train incidents where the teacher
                    category matched the auto-label (data/processed/teacher_train.jsonl); with --with-rationalized
                    also the rationalized answers (teacher told the label) from teacher_rationalized.jsonl
Validation (early stopping) = latest 10% of each repo's train incidents. Minority classes are oversampled to at
least 1/3 of the majority count in the training part (--min-class-frac 0 disables). Logs VRAM and time.

Usage: .venv/bin/python -m distill.train_student --target labels
"""
import argparse
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

from collect.github_logs import ROOT
from eval.fast_track import bm25_index, build_prompt, load_split

MODEL = "Qwen/Qwen3-4B-Instruct-2507"
CTX_STEPS = [1500, 1000, 600, 300, 0]  # per-neighbor log chars tried, longest first


def fit_prompt(q: dict, train: list[dict], hits: list, tok, budget: int) -> tuple[str, int]:
    """v1 prompt that fits `budget` tokens: shrink retrieved context first (per-neighbor text, then fewer
    neighbors), never the failure text. Returns (prompt, tokens)."""
    # return_dict=False: transformers 5 returns a BatchEncoding dict otherwise (len() would count its keys)
    n_tok = lambda p: len(tok.apply_chat_template([{"role": "user", "content": p}], tokenize=True,  # noqa: E731
                                                  return_dict=False))
    for k in range(len(hits), -1, -1):
        for chars in CTX_STEPS:
            p = build_prompt(q, train, hits[:k], ctx_chars=chars)
            if (n := n_tok(p)) <= budget:
                return p, n
            if k == 0:
                break
    return p, n  # failure text alone exceeds the budget: kept whole (never truncated)


def examples(target: str, teacher_path: Path, exclude: set[str], tok, budget: int,
             rationalized: Path | None = None) -> tuple[list[dict], list[dict]]:
    """(train part, validation part) as prompt/completion records, time-ordered."""
    train, _ = load_split(ROOT / "data/processed/failures_labeled.jsonl", exclude, 0.3, 3)
    search = bm25_index([i["text"] for i in train], [i["t"] for i in train])
    teacher = {}
    if target == "rationale":
        teacher = {r["id"]: {**r, "teacher_source": "teacher"} for r in map(json.loads, teacher_path.open()) if r["match"]}
        if rationalized:
            teacher.update({r["id"]: r for r in map(json.loads, rationalized.open())
                            if r["match"] and r["likely_cause"] and r["id"] not in teacher})
    recs = []
    for q in train:
        if target == "rationale" and q["id"] not in teacher:
            continue
        ans = {"category": q["y"]} if target == "labels" else \
            {"category": q["y"], "likely_cause": teacher[q["id"]]["likely_cause"]}
        prompt, _ = fit_prompt(q, train, search(q["text"], 5, before=q["t"]), tok, budget)
        # the rationalization hint is teacher-only: the student input must be the plain test-time v1 prompt
        assert "The correct category is" not in prompt, q["id"]
        recs.append({"id": q["id"], "repo": q["repo"], "y": q["y"],
                     "teacher_source": teacher[q["id"]]["teacher_source"] if teacher else None,
                     "prompt": [{"role": "user", "content": prompt}],
                     "completion": [{"role": "assistant", "content": json.dumps(ans)}]})
    tr, va = [], []
    for repo in sorted({r["repo"] for r in recs}):
        rs = [r for r in recs if r["repo"] == repo]  # already time-ordered
        n_val = max(1, round(0.1 * len(rs)))
        tr += rs[:-n_val]
        va += rs[-n_val:]
    return tr, va


def oversample(recs: list[dict], min_frac: float, seed: int = 0) -> list[dict]:
    counts = Counter(r["y"] for r in recs)
    target = math.ceil(min_frac * max(counts.values()))
    out = list(recs)
    rng = random.Random(seed)
    for c, n in counts.items():
        pool = [r for r in recs if r["y"] == c]
        out += [rng.choice(pool) for _ in range(max(0, target - n))]
    rng.shuffle(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", choices=["labels", "rationale"], required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--teacher", type=Path, default=ROOT / "data/processed/teacher_train.jsonl")
    ap.add_argument("--exclude-repos", nargs="*", default=["pytorch/pytorch"])
    ap.add_argument("--rationalized-path", type=Path, default=ROOT / "data/processed/teacher_rationalized.jsonl")
    ap.add_argument("--with-rationalized", action="store_true",
                    help="rationale target: also train on rationalized answers (data/processed/teacher_rationalized.jsonl)")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=4096, help="max sequence tokens (prompt fitted to max_len - 64)")
    ap.add_argument("--eval-steps", type=int, default=20)
    ap.add_argument("--min-class-frac", type=float, default=1 / 3)
    ap.add_argument("--max-steps", type=int, default=-1, help="smoke test")
    args = ap.parse_args()
    out_dir = args.out_dir or ROOT / f"data/models/student_{args.target}{'_rationalized' if args.with_rationalized else ''}"
    out_dir.mkdir(parents=True, exist_ok=True)

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, EarlyStoppingCallback,
                              TrainerCallback)

    log_f = (out_dir / "train.log").open("a")

    class ProgressLog(TrainerCallback):  # "HH:MM:SS step n/N" lines for collect.status
        def on_step_end(self, a, state, control, **kw):
            if state.global_step % 2 == 0 or state.global_step == state.max_steps:
                log_f.write(f"{time.strftime('%H:%M:%S')} step {state.global_step}/{state.max_steps}\n")
                log_f.flush()

        def on_evaluate(self, a, state, control, metrics=None, **kw):
            log_f.write(f"{time.strftime('%H:%M:%S')} eval at step {state.global_step}: {metrics}\n")
            log_f.flush()
    from trl import SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(args.model)
    tr, va = examples(args.target, args.teacher, set(args.exclude_repos), tok, args.max_len - 64,
                      args.rationalized_path if args.with_rationalized else None)
    tr_os = oversample(tr, args.min_class_frac) if args.min_class_frac > 0 else tr
    print(f"train {len(tr)} ({dict(Counter(r['y'] for r in tr))}) -> oversampled {len(tr_os)} "
          f"({dict(Counter(r['y'] for r in tr_os))}); val {len(va)} ({dict(Counter(r['y'] for r in va))})",
          file=sys.stderr, flush=True)

    lens = sorted(len(tok.apply_chat_template(r["prompt"] + r["completion"], tokenize=True, return_dict=False))
                  for r in tr + va)
    assert lens[-1] <= args.max_len, f"{sum(l > args.max_len for l in lens)} sequences exceed max_len"
    print(f"token lengths: median {lens[len(lens) // 2]}, p95 {lens[int(0.95 * len(lens))]}, max {lens[-1]} "
          f"(max_len {args.max_len}; {sum(l > args.max_len for l in lens)} over)", file=sys.stderr, flush=True)

    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map={"": 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                               bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True))
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                             "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    cols = ["prompt", "completion"]
    cfg = SFTConfig(
        output_dir=str(out_dir / "checkpoints"), num_train_epochs=args.epochs, max_steps=args.max_steps,
        per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, lr_scheduler_type="cosine", bf16=True,
        warmup_steps=max(1, int(0.05 * args.epochs * len(tr_os) / args.grad_accum)),
        gradient_checkpointing=True, max_length=args.max_len, completion_only_loss=True,
        eval_strategy="steps", eval_steps=args.eval_steps, save_strategy="steps", save_steps=args.eval_steps,
        save_total_limit=2, load_best_model_at_end=True, metric_for_best_model="eval_loss", greater_is_better=False,
        logging_steps=5, report_to="none", seed=0)
    trainer = SFTTrainer(model=model, args=cfg, processing_class=tok,
                         train_dataset=Dataset.from_list([{k: r[k] for k in cols} for r in tr_os]),
                         eval_dataset=Dataset.from_list([{k: r[k] for k in cols} for r in va]),
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=2), ProgressLog()])
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    trainer.train()
    wall = time.time() - t0
    trainer.model.save_pretrained(out_dir / "adapter")
    tok.save_pretrained(out_dir / "adapter")
    log = {"target": args.target, "with_rationalized": args.with_rationalized,
           "teacher_sources": dict(Counter(r["teacher_source"] for r in tr)),
           "model": args.model, "train_examples": len(tr), "train_oversampled": len(tr_os),
           "val_examples": len(va), "wall_seconds": round(wall), "steps": trainer.state.global_step,
           "best_eval_loss": trainer.state.best_metric, "best_checkpoint": trainer.state.best_model_checkpoint,
           "peak_vram_allocated_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
           "peak_vram_reserved_gb": round(torch.cuda.max_memory_reserved() / 2**30, 2),
           "token_len_median": lens[len(lens) // 2], "token_len_max": lens[-1],
           "history": trainer.state.log_history}
    (out_dir / "train_log.json").write_text(json.dumps(log, indent=1))
    log_f.write(f"TRAIN DONE {time.strftime('%H:%M:%S')}\n")
    log_f.close()
    print(f"TRAIN DONE: {log['steps']} steps in {wall / 60:.1f} min, best eval_loss {log['best_eval_loss']}, "
          f"peak VRAM {log['peak_vram_allocated_gb']} GB allocated / {log['peak_vram_reserved_gb']} GB reserved",
          file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
