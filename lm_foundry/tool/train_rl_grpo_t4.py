#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""train_rl_grpo_t4.py — Lever 4 GRPO trainer.

Compile-feedback RL on T4 (enum decl) using `hexa_cc` as the binary reward.
Starts from r4 (v16) adapter; KL-anchored to that same adapter to prevent
T1/T2/T5/T6/T7/T8 regression.

Reward (v2, with substring guard — see papers/spec-lever4-compile-rl.md §8):
  1. Clean FIM/EOS tokens out of the completion.
  2. Check `gold_name` (e.g. "Token") is a substring of the cleaned completion;
     if not → reward 0 (wrong enum name).
  3. Write completion to a tmp file, invoke `hexa_cc <in.hexa> <out.c>` with
     5s timeout; reward = 1.0 iff exit==0 AND no ERR_PATS in stdout/stderr.

USAGE
    train_rl_grpo_t4.py --base Qwen/Qwen2.5-Coder-7B \
                       --adapter dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.3.0-r4 \
                       --prompts /workspace/rl_t4_prompts.jsonl \
                       --hexa-cc /workspace/hexa_cc \
                       --output /workspace/adapter-v040-rl-t4

OUTPUT
    <output>/adapter_model.safetensors  (the new LoRA adapter)
    <output>/training_log.jsonl         (per-step reward + KL stats)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Defer heavy imports until after argparse to keep --help fast.
_HEXA_CC_BIN: str = ""

STOPS = ("<|fim_middle|>", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_pad|>",
         "<|endoftext|>", "<|im_end|>", "<|im_start|>", "<|repo_name|>",
         "<|file_sep|>", "### User:", "### Assistant")

ERR_PATS = ("Parse error", "parse error", "CODEGEN ERROR", "Resolve error",
            "Type error", "Lint S", "unhandled binop", "unhandled operator",
            "unexpected token")


def _clean(c: str) -> str:
    for s in STOPS:
        i = c.find(s)
        if i != -1:
            c = c[:i]
    return c.strip()


def compile_pass(completion: str) -> bool:
    """Real hexa_cc compile — the eval scorer's logic, factored out."""
    cleaned = _clean(completion)
    if not cleaned:
        return False
    if not _HEXA_CC_BIN or not os.path.exists(_HEXA_CC_BIN):
        return False
    with tempfile.TemporaryDirectory() as td:
        ip = Path(td) / "in.hexa"
        op = Path(td) / "out.c"
        ip.write_text(cleaned + "\n")
        try:
            r = subprocess.run([_HEXA_CC_BIN, str(ip), str(op)],
                               capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
        if r.returncode != 0:
            return False
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        for p in ERR_PATS:
            if p in out:
                return False
        return True


import re as _re

# Reward-hack guard patterns. hexa_cc accepts unknown tokens silently (no error,
# empty .c output) and accepts empty enum bodies. Both must score 0 even though
# `s_compile` is True for them.
_ENUM_DECL_RE = _re.compile(r"enum\s+(\w+)\s*\{(.+?)\}", _re.DOTALL)


def _looks_like_real_enum(cleaned: str, gold_name: str, min_variants: int) -> bool:
    """Reject reward hacks: empty bodies, garbage that hexa_cc swallows, wrong enum name."""
    m = _ENUM_DECL_RE.search(cleaned)
    if not m:
        return False
    name, body = m.group(1), m.group(2).strip()
    if name.lower() != gold_name.lower():
        return False
    if not body:
        return False
    # Count top-level variants (split on commas not inside `(...)` / `<...>`)
    depth = 0
    parts: list[str] = []
    cur: list[str] = []
    for ch in body:
        if ch in "([<":
            depth += 1
            cur.append(ch)
        elif ch in ")]>":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    parts = [p for p in parts if p]
    return len(parts) >= min_variants


def reward_fn_factory(prompt_to_meta: dict[str, dict]):
    """Builds a GRPO-compatible reward fn: (prompts, completions) -> list[float].
    `prompt_to_meta` maps each prompt → {"gold_name": str, "n_variants": int}.
    """
    def reward_fn(prompts: list[str], completions: list[str], **kwargs) -> list[float]:
        rewards: list[float] = []
        for prompt, comp in zip(prompts, completions):
            cleaned = _clean(comp)
            meta = prompt_to_meta.get(prompt, {})
            gold_name = meta.get("gold_name", "")
            n_variants = meta.get("n_variants", 1)
            # Stage 1: structural guard — must look like a real enum with the right
            # name and at least (n_variants - 1) variants visible. Catches garbage,
            # empty bodies, wrong-name hacks before paying the subprocess cost.
            if not _looks_like_real_enum(cleaned, gold_name, max(1, n_variants - 1)):
                rewards.append(0.0)
                continue
            # Stage 2: real hexa_cc compile.
            rewards.append(1.0 if compile_pass(comp) else 0.0)
        return rewards
    return reward_fn


def main() -> int:
    global _HEXA_CC_BIN
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="HF model id of the 7B base")
    ap.add_argument("--adapter", required=True, help="HF adapter id or local path (r4 by default)")
    ap.add_argument("--prompts", required=True, type=Path, help="JSONL from build_rl_t4_prompts.py")
    ap.add_argument("--hexa-cc", required=True, type=Path, help="path to hexa_cc binary")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-6)
    ap.add_argument("--kl-coef", type=float, default=0.04)
    ap.add_argument("--group-size", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=120)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--logging-steps", type=int, default=10)
    args = ap.parse_args()

    _HEXA_CC_BIN = str(args.hexa_cc.resolve())
    if not os.path.exists(_HEXA_CC_BIN):
        print(f"ERROR: hexa_cc not found at {_HEXA_CC_BIN}", file=sys.stderr)
        return 2

    # Quick reward-fn smoke test before loading the 7B
    print("=== smoke test reward_fn ===", flush=True)
    smoke_pass = "enum Foo { A, B }"
    smoke_fail = "enum Foo<T> { A(T), B }"
    print(f"  pass-case: {compile_pass(smoke_pass)}")
    print(f"  fail-case: {compile_pass(smoke_fail)}")
    if not compile_pass(smoke_pass):
        print("FATAL: hexa_cc smoke pass-case failed; check binary", file=sys.stderr)
        return 3
    if compile_pass(smoke_fail):
        print("FATAL: hexa_cc smoke fail-case unexpectedly passed", file=sys.stderr)
        return 3

    # Load deps
    print("=== loading deps ===", flush=True)
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel, LoraConfig

    # TRL has two compatible surfaces for compile-feedback RL:
    #   - GRPOTrainer / GRPOConfig  (TRL ≥ 0.14, native group-relative policy opt)
    #   - RLOOTrainer / RLOOConfig  (TRL 0.10–0.13, REINFORCE leave-one-out;
    #                                 equivalent algorithm under a different name)
    # Prefer GRPO if available; fall back to RLOO.
    _trainer_cls = None
    _config_cls = None
    _impl = ""
    try:
        from trl import GRPOTrainer, GRPOConfig  # type: ignore
        _trainer_cls, _config_cls, _impl = GRPOTrainer, GRPOConfig, "GRPO"
    except ImportError:
        from trl import RLOOTrainer, RLOOConfig  # type: ignore
        _trainer_cls, _config_cls, _impl = RLOOTrainer, RLOOConfig, "RLOO"
    print(f"  trl impl: {_impl}")
    print(f"  torch {torch.__version__}, cuda available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  device: {torch.cuda.get_device_name(0)}")

    # Tokenizer
    print(f"=== loading tokenizer {args.base} ===", flush=True)
    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # Base model + r4 adapter
    print(f"=== loading model {args.base} + adapter {args.adapter} ===", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="auto")
    model = PeftModel.from_pretrained(model, args.adapter, is_trainable=True)
    model.print_trainable_parameters()

    # Dataset
    print(f"=== loading prompt dataset {args.prompts} ===", flush=True)
    rows = [json.loads(L) for L in args.prompts.read_text().splitlines() if L.strip()]
    print(f"  prompts: {len(rows)}")
    prompt_to_meta = {r["prompt"]: {"gold_name": r["gold_name"],
                                     "n_variants": r.get("n_variants", 1)}
                      for r in rows}
    ds = Dataset.from_list([{"prompt": r["prompt"]} for r in rows])

    reward_fn = reward_fn_factory(prompt_to_meta)

    # RL config — args differ slightly between GRPO and RLOO; build via kwargs
    # filtered to what the chosen Config supports.
    import inspect
    cfg_kwargs = dict(
        output_dir=str(args.output),
        per_device_train_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=args.logging_steps,
        save_strategy="epoch",
        report_to="none",
        remove_unused_columns=False,
    )
    # KL coefficient: GRPO uses `beta`, RLOO uses `kl_coef`
    cfg_kwargs["beta"] = args.kl_coef
    cfg_kwargs["kl_coef"] = args.kl_coef
    # Group size: GRPO `num_generations`, RLOO `rloo_k`
    cfg_kwargs["num_generations"] = args.group_size
    cfg_kwargs["rloo_k"] = args.group_size
    # Generation knobs (GRPO surface; RLOO may take similar)
    cfg_kwargs["max_completion_length"] = args.max_new_tokens
    cfg_kwargs["temperature"] = args.temperature
    # Filter to the config's actual __init__ signature
    sig = inspect.signature(_config_cls.__init__)
    accepted = set(sig.parameters.keys())
    cfg_kwargs = {k: v for k, v in cfg_kwargs.items() if k in accepted}
    print(f"=== building {_impl} config with kwargs:")
    for k, v in cfg_kwargs.items():
        print(f"    {k} = {v}")
    cfg = _config_cls(**cfg_kwargs)

    print(f"=== starting {_impl}Trainer ===", flush=True)
    t0 = time.time()
    trainer_kwargs = dict(model=model, args=cfg, train_dataset=ds, processing_class=tok)
    # GRPO takes `reward_funcs=[fn]`; RLOO takes `reward_model=fn` OR a model.
    if _impl == "GRPO":
        trainer_kwargs["reward_funcs"] = [reward_fn]
    else:
        # RLOO wraps a torch.nn.Module for the reward; for a Python callable we
        # need a small wrapper. RLOO is older and clunkier here — pass via
        # the `reward_model` arg as a Python callable; if the version rejects it
        # we raise loudly.
        trainer_kwargs["reward_model"] = reward_fn
    trainer = _trainer_cls(**trainer_kwargs)
    trainer.train()
    trainer.save_model(str(args.output))
    elapsed = time.time() - t0
    print(f"=== done in {elapsed/60:.1f} min ===", flush=True)

    # Summary
    summary = {
        "trl_impl": _impl,
        "base": args.base,
        "adapter_in": args.adapter,
        "adapter_out": str(args.output),
        "lr": args.lr,
        "kl_coef": args.kl_coef,
        "group_size": args.group_size,
        "batch_size": args.batch_size,
        "epochs": args.epochs,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "prompts_total": len(rows),
        "elapsed_min": elapsed / 60,
    }
    (args.output / "rl_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
