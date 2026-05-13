#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""train_rl_grpo_routing.py — v0.4.2 routing-RL trainer.

GRPO with binary route-correctness × schema-validity reward on the 200-prompt
training set from `tool/build_routing_rl_prompts.py`. Continues from the
r39 v3-t3patch GA adapter — NOT from r40/r41 (those drifted from RL gains).

The empirical finding from r40+r41: SFT-only delegation training in 7B+LoRA
can't escape the specialist↔routing tradeoff. r42 is the routing-RL alternative
predicted in the v0.4.2 plan — GRPO with the same mechanics as Lever 4's
compile-feedback RL, but with delegation-routing as the reward signal.

Reward design:
  reward = s_route × s_schema  ∈ {0, 1}
where:
  s_route  = 1 if the emission matches `must_delegate ↔ delegated AND
              must_refuse ↔ refused` for the prompt's ideal_route, else 0.
  s_schema = 1 if (a) the model did not emit <|delegate|> at all (vacuously
              valid for non-delegation tasks), OR (b) the emitted delegate
              JSON parses cleanly with all 5 required fields + tool/model
              in the spec-§2.A allowlist + max_tokens in [64, 8192] +
              non-empty reason ≤ 80 chars. Else 0.

Both subscores from `tool/score_delegation_mk0.score_one()`; this trainer
reuses that exact logic for training/eval alignment.

USAGE
    train_rl_grpo_routing.py --base Qwen/Qwen2.5-Coder-7B \
                             --adapter dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch \
                             --prompts /workspace/rl_routing_prompts.jsonl \
                             --output /workspace/adapter-v042-route-rl

OUTPUT
    <output>/adapter_model.safetensors  (the new LoRA adapter)
    <output>/rl_summary.json            (recipe + final metrics)
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import os
import sys
import time
from pathlib import Path

# We rely on score_delegation_mk0 living next to this file (same tool/ dir).
sys.path.insert(0, _THIS_DIR)
from score_delegation_mk0 import _parse_completion, score_one  # type: ignore


def reward_fn_factory(prompt_to_task: dict[str, dict]):
    """Build a GRPO-compatible reward fn.

    Args:
        prompt_to_task: maps each prompt string → the task row (including
                         `ideal_route` and `tags`).

    Returns:
        Callable `fn(prompts, completions, **kwargs) -> list[float]` per
        TRL's `reward_funcs` contract. Reward = s_route × s_schema ∈ {0, 1}.
    """
    def reward_fn(prompts: list[str], completions: list[str], **kwargs) -> list[float]:
        rewards: list[float] = []
        for prompt, comp in zip(prompts, completions):
            task = prompt_to_task.get(prompt)
            if task is None:
                # Shouldn't happen — TRL feeds back the same prompts we built.
                rewards.append(0.0)
                continue
            parsed = _parse_completion(comp)
            sub = score_one(task, parsed)
            r = float(sub["s_route"]) * float(sub["s_schema"])
            rewards.append(r)
        return rewards
    return reward_fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True,
                    help="HF id or local path of starting adapter (use r39 v3-t3patch)")
    ap.add_argument("--prompts", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--kl-coef", type=float, default=0.01)
    ap.add_argument("--group-size", type=int, default=4)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--logging-steps", type=int, default=25)
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    # Load prompts + map prompt → full task row for reward lookup
    rows = [json.loads(l) for l in args.prompts.read_text().splitlines() if l.strip()]
    # The model prompts have a wrapper template (System+User+Assistant); the
    # reward fn is called with whatever prompt string TRL passes back to it,
    # which equals what we put into the Dataset. So build the wrapped prompt
    # AND keep the task row keyed by it.
    SYSTEM_PREFIX = (
        "You answer hexa-canon questions directly. For out-of-domain or "
        "hard-reasoning prompts, emit <|delegate|>{…}<|/delegate|>. For "
        "mid-confidence answers, prefix <|confidence:medium|>. NEVER emit "
        "<|confidence:low|> — delegate instead. NEVER delegate harmful / "
        "illegal / exfil prompts — refuse them directly."
    )
    def _wrap(prompt: str) -> str:
        return f"### System:\n{SYSTEM_PREFIX}\n### User:\n{prompt}\n### Assistant:\n"

    prompt_to_task: dict[str, dict] = {}
    ds_rows: list[dict] = []
    for r in rows:
        wrapped = _wrap(r["prompt"])
        prompt_to_task[wrapped] = r
        ds_rows.append({"prompt": wrapped})
    print(f"loaded {len(ds_rows)} routing-RL prompts from {args.prompts}")

    # Reward fn smoke test before we load the 7B — sanity check that the
    # scorer + parsed integration works.
    print("=== reward_fn smoke test ===")
    smoke = [
        # (wrapped_prompt, completion, expected_reward, label)
        (_wrap(rows[0]["prompt"]) if rows[0]["ideal_route"]["must_delegate"] is False else "skip",
         f"<|confidence:high|>{'enum Color { Red, Green, Blue }'}",
         1.0, "in-domain-high (if first row is in-domain)"),
    ]
    rfn = reward_fn_factory(prompt_to_task)
    # Real smoke: a few synthetic cases
    test_prompts = [_wrap(r["prompt"]) for r in rows[:4]]
    test_completions = [
        f"<|confidence:high|>some answer",                                                     # try as direct
        f'<|delegate|>{{"tool":"claude-api","model":"claude-sonnet-4-6","prompt":"x","max_tokens":1024,"reason":"r"}}<|/delegate|>',  # try as delegate
        "out-of-domain — non-hexa request",                                                    # refusal-shape
        f'<|delegate|>{{malformed}}<|/delegate|>',                                              # malformed delegate
    ]
    smoke_rewards = rfn(test_prompts, test_completions)
    print(f"  smoke rewards (first 4): {smoke_rewards}")
    print(f"  first prompt tag: {rows[0]['tags']}, must_delegate={rows[0]['ideal_route']['must_delegate']}")

    # Load deps
    print("=== loading deps ===", flush=True)
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel

    try:
        from trl import GRPOTrainer, GRPOConfig  # type: ignore
        _trainer_cls, _config_cls, _impl = GRPOTrainer, GRPOConfig, "GRPO"
    except ImportError as e:
        print(f"GRPO import failed: {e}", file=sys.stderr)
        return 2
    print(f"  trl impl: {_impl}")
    print(f"  torch {torch.__version__}, cuda {torch.cuda.is_available()}, "
          f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''}")

    # Tokenizer + model + adapter
    print(f"=== loading {args.base} + adapter {args.adapter} ===", flush=True)
    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model = PeftModel.from_pretrained(model, args.adapter, is_trainable=True)
    model.print_trainable_parameters()

    ds = Dataset.from_list(ds_rows)

    # GRPOConfig — same kwarg filtering pattern as train_rl_grpo_t4.py for
    # version robustness.
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
        beta=args.kl_coef,
        num_generations=args.group_size,
        max_completion_length=args.max_new_tokens,
        temperature=args.temperature,
    )
    sig = inspect.signature(_config_cls.__init__)
    accepted = set(sig.parameters.keys())
    cfg_kwargs = {k: v for k, v in cfg_kwargs.items() if k in accepted}
    print("=== GRPOConfig:")
    for k, v in cfg_kwargs.items():
        print(f"    {k} = {v}")
    cfg = _config_cls(**cfg_kwargs)

    print("=== GRPOTrainer ===", flush=True)
    t0 = time.time()
    trainer = _trainer_cls(
        model=model, args=cfg, train_dataset=ds, processing_class=tok,
        reward_funcs=[rfn],
    )
    trainer.train()
    trainer.save_model(str(args.output))
    elapsed = time.time() - t0
    print(f"=== done in {elapsed/60:.1f} min ===", flush=True)

    summary = {
        "trl_impl": _impl,
        "base": args.base,
        "adapter_in": args.adapter,
        "adapter_out": str(args.output),
        "reward": "s_route × s_schema (from score_delegation_mk0.score_one)",
        "lr": args.lr,
        "kl_coef": args.kl_coef,
        "group_size": args.group_size,
        "batch_size": args.batch_size,
        "epochs": args.epochs,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "prompts_total": len(rows),
        "elapsed_min": round(elapsed / 60, 2),
    }
    (args.output / "rl_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
