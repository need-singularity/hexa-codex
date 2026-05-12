#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""score_with_adapter.py — score eval manifests against base + LoRA adapter.

Sister of tool/score_mk0_eval.py but loads PeftModel before generation.

USAGE
    python3 tool/score_with_adapter.py \\
        --base Qwen/Qwen2.5-Coder-3B \\
        --adapter /home/summer/runs/sft-lora-r16-v1 \\
        --manifest eval/hexa-eval/manifest.jsonl \\
        --output runs/hexa-eval-mk0/qwen3b-lora-r16-v1/
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import importlib.util as _ilu
import json
import sys
import time
from collections import Counter
from pathlib import Path


def _load_scorer_module():
    spec = _ilu.spec_from_file_location("score_mk0_eval", Path(__file__).parent / "score_mk0_eval.py")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="score_with_adapter")
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args(argv)

    sm = _load_scorer_module()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    tdtype = {"bfloat16": torch.bfloat16, "float16": torch.float16}.get(args.dtype, torch.bfloat16)
    print(f"loading {args.base} + adapter {args.adapter}...", flush=True)
    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=tdtype, device_map="auto")
    model = PeftModel.from_pretrained(model, str(args.adapter))
    model.eval()

    rows = sm.load_manifest(args.manifest)
    args.output.mkdir(parents=True, exist_ok=True)

    samples = []
    family_counts = Counter()
    family_passes = Counter()
    n_pass = 0
    n_total = 0
    t_start = time.monotonic()

    for i, row in enumerate(rows):
        prompt = row["prompt"]
        # Wrap with same SFT template as training
        formatted = f"### User:\n{prompt}\n### Assistant:\n"
        try:
            completion = sm.generate(tok, model, formatted, max_new_tokens=args.max_new_tokens)
        except Exception as exc:
            completion = ""
            print(f"  GEN_ERROR on {row.get('task_id')}: {exc}", flush=True)
        score = sm.score_row(row, completion)
        n_total += 1
        family = row.get("family", "?")
        family_counts[family] += 1
        if score["passed"]:
            n_pass += 1
            family_passes[family] += 1
        samples.append({
            "task_id": row["task_id"],
            "family": family,
            "prompt": prompt,
            "scorer": row.get("scorer"),
            "gold_pattern": row.get("gold_pattern"),
            "completion": completion[:500],
            "passed": score["passed"],
            "scorer_status": score["scorer_status"],
        })
        if (i + 1) % 5 == 0 or (i + 1) == len(rows):
            print(f"  [{i+1:>3}/{len(rows)}] pass@1={n_pass}/{n_total}={n_pass*100/n_total:.1f}%", flush=True)

    with (args.output / "per_task.jsonl").open("w") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    summary = {
        "base": args.base,
        "adapter": str(args.adapter),
        "manifest": str(args.manifest),
        "dtype": args.dtype,
        "tasks_total": n_total,
        "tasks_passed": n_pass,
        "pass_at_1": round(n_pass / max(n_total, 1), 4),
        "per_family": {
            fam: {
                "count": family_counts[fam],
                "passed": family_passes[fam],
                "pass_rate": round(family_passes[fam] / max(family_counts[fam], 1), 4),
            }
            for fam in sorted(family_counts)
        },
        "elapsed_total_s": round(time.monotonic() - t_start, 1),
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with (args.output / "scores.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print("=== SUMMARY ===")
    for k, v in summary.items():
        if k == "per_family":
            print("  per_family:")
            for fam, s in v.items():
                print(f"    {fam}: {s['passed']}/{s['count']} = {s['pass_rate']*100:.1f}%")
        else:
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
