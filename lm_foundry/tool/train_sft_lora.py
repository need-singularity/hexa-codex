#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""train_sft_lora.py — LoRA r=16 SFT on Qwen2.5-Coder-3B.

Phase v0.2.0 entry. Trains a LoRA adapter on canon + refusal pairs.

CONFIG (v0.2.0 default):
    base model    : Qwen/Qwen2.5-Coder-3B
    LoRA r        : 16
    LoRA alpha    : 32
    LoRA target   : q_proj, k_proj, v_proj, o_proj
    epochs        : 1
    batch size    : 1 + grad_accum 4 = effective 4
    lr            : 2e-4
    optimizer     : adamw_torch
    sequence len  : 1024

OUTPUT
    <output>/adapter_config.json
    <output>/adapter_model.safetensors
    <output>/training_args.bin
    <output>/training_summary.json

CROSS-LINKS
    tool/build_sft_dataset.py — sister tool (dataset prep)
    papers/plan-runbook-v0.1.3.md §5 — SFT step (deferred from v0.1.3)
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import sys
import time
from pathlib import Path


DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-3B"
DEFAULT_DATASET = Path.home() / "runs" / "sft-train-v1" / "train.jsonl"
DEFAULT_OUTPUT = Path.home() / "runs" / "sft-lora-r16-v1"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="train_sft_lora", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--adapter-in", default=None,
                        help="optional: continue SFT from an existing LoRA adapter "
                             "(HF id or local path); LoRA cfg flags are ignored when set")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)

    print(f"plan:")
    print(f"  model:        {args.model}")
    print(f"  dataset:      {args.dataset}")
    print(f"  output:       {args.output}")
    print(f"  lora r/alpha: {args.lora_r} / {args.lora_alpha}")
    print(f"  epochs:       {args.epochs}")
    print(f"  batch x acc:  {args.batch_size} x {args.grad_accum} (effective {args.batch_size*args.grad_accum})")
    print(f"  lr:           {args.lr}")
    print(f"  max seq:      {args.max_seq_length}")
    if args.adapter_in:
        print(f"  adapter-in:   {args.adapter_in}  (continue mode — ignores LoRA cfg flags)")

    if args.dry_run:
        print("--dry-run: stopping")
        return 0

    # Lazy imports (heavy)
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from trl import SFTTrainer, SFTConfig

    print(f"loading {args.model}...", flush=True)
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False

    if args.adapter_in:
        print(f"continuing SFT from adapter {args.adapter_in}...", flush=True)
        model = PeftModel.from_pretrained(model, args.adapter_in, is_trainable=True)
    else:
        print("attaching new LoRA adapter...", flush=True)
        lora_cfg = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    print(f"loading dataset {args.dataset}...", flush=True)
    ds = load_dataset("json", data_files=str(args.dataset), split="train")
    print(f"  rows: {len(ds)}")

    sft_cfg = SFTConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        bf16=True,
        max_length=args.max_seq_length,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        gradient_checkpointing=True,
        optim="adamw_torch",
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=ds,
        processing_class=tok,
    )

    t_start = time.monotonic()
    print("=== TRAINING START ===", flush=True)
    train_result = trainer.train()
    elapsed = time.monotonic() - t_start

    # Save final adapter
    trainer.save_model(str(args.output))
    tok.save_pretrained(str(args.output))

    summary = {
        "model_base": args.model,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "epochs": args.epochs,
        "batch_size_effective": args.batch_size * args.grad_accum,
        "lr": args.lr,
        "max_seq_length": args.max_seq_length,
        "rows_total": len(ds),
        "elapsed_total_s": round(elapsed, 1),
        "final_train_loss": float(train_result.metrics.get("train_loss", 0.0)),
        "training_runtime_s": float(train_result.metrics.get("train_runtime", 0.0)),
        "training_steps_per_second": float(train_result.metrics.get("train_steps_per_second", 0.0)),
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with (args.output / "training_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
