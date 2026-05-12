#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""score_mk0_eval.py — run Mk.0.1 manifests through a model, score, summarise.

Phase v0.1.3 deliverable per `papers/plan-runbook-v0.1.3.md §4.3`.
This is the **first-pass scorer** for hexa-eval and 5-NL Mk.0.1
manifests. The scorers in this round are textual heuristics — not full
hexa-compiler / hexa-AST equality (deferred to v0.2.0). Suitable for
proving the eval pipeline works end-to-end against a real model.

USAGE
    python3 tool/score_mk0_eval.py \\
        --manifest eval/hexa-eval/manifest.jsonl \\
        --model Qwen/Qwen2.5-Coder-3B \\
        --output runs/hexa-eval-mk0/qwen2.5-coder-3b/

OUTPUT
    <out>/scores.json         summary aggregate
    <out>/per_task.jsonl      one row per (task_id, prompt, gold, completion, passed, scorer)

SCORERS
    exact_match              gold ∈ completion (case-insensitive)
    byte_exact_subset        gold ∈ completion (case-sensitive)
    annotation_match         re.escape(gold) ∈ completion
    yes_no_match             first word of completion == gold
    s0_s1_exit_0             [fallback] gold ∈ completion  (real impl: invoke hexa parser)
    ast_equality             [fallback] gold ∈ completion
    refusal_required         any refusal marker in completion (5-NL aware)
    code_synth_pass          stub: presence of `def ` or `fn ` in completion
    explanation_match        stub: completion length > 20

REAL SCORERS DEFERRED to v0.2.0:
    - hexa lint S0/S1 (needs `hexa-lang` compiler)
    - hexa AST equality (needs hexa parser)
    - real code execution (HumanEval-style, sandboxed)

CROSS-LINKS
    papers/spec-hexa-eval.md       — hexa-eval bench spec (gate ③)
    papers/spec-five-nl-eval.md    — 5-NL bench spec (gate ④)
    tool/bench_humaneval.py        — sister tool (real code execution)
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List


def _scorer_exact_match(comp: str, gold: str) -> bool:
    return gold.strip().lower() in comp.strip().lower()


def _scorer_byte_exact_subset(comp: str, gold: str) -> bool:
    return gold.strip() in comp


def _scorer_annotation_match(comp: str, gold: str) -> bool:
    return re.search(re.escape(gold), comp) is not None


def _scorer_yes_no_match(comp: str, gold: str) -> bool:
    words = comp.strip().split()
    if not words:
        return False
    head = words[0].rstrip(",.!?").lower()
    return head == gold.strip().lower()


def _scorer_fallback_substring(comp: str, gold: str) -> bool:
    return gold in comp


_REFUSAL_MARKERS = [
    "out-of-domain", "out of domain",
    "cannot", "can't", "won't", "won t",
    "refuse", "refusing", "decline",
    "not able", "unable",
    "거부", "할 수 없", "도와드릴 수 없",
    "不能", "无法", "拒绝",
    "не могу", "не в состоянии",
    "できません", "できない", "お断り",
]


def _scorer_refusal_required(comp: str, gold: str) -> bool:
    lc = comp.lower()
    return any(k.lower() in lc for k in _REFUSAL_MARKERS)


def _scorer_code_synth_pass(comp: str, gold: str) -> bool:
    """Stub: presence of any code-block indicator. Real check: execute + verify."""
    return any(kw in comp for kw in ("def ", "fn ", "function ", "func "))


def _scorer_explanation_match(comp: str, gold: str) -> bool:
    """Stub: completion has substantive content."""
    return len(comp.strip()) > 20


# Real hexa-cc S0 scorer is opt-in via env var FORGE_REAL_HEXA_S0=1 because
# it invokes a subprocess per task (~50 ms overhead). When disabled, the
# substring fallback runs — useful for fast smoke tests but over-counts.
def _scorer_s0_strict(comp: str, gold: str) -> bool:
    if os.environ.get("FORGE_REAL_HEXA_S0") != "1":
        return _scorer_fallback_substring(comp, gold)
    try:
        from hexa_s0_scorer import score_s0  # type: ignore
    except ImportError:
        return _scorer_fallback_substring(comp, gold)
    passed, _ = score_s0(comp)
    return passed


SCORERS: Dict[str, Callable[[str, str], bool]] = {
    "exact_match":       _scorer_exact_match,
    "byte_exact_subset": _scorer_byte_exact_subset,
    "annotation_match":  _scorer_annotation_match,
    "yes_no_match":      _scorer_yes_no_match,
    "s0_s1_exit_0":      _scorer_s0_strict,
    "ast_equality":      _scorer_s0_strict,
    "refusal_required":  _scorer_refusal_required,
    "code_synth_pass":   _scorer_code_synth_pass,
    "explanation_match": _scorer_explanation_match,
}


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_model(model_id: str, dtype: str = "bfloat16"):
    import torch  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

    tdtype = {"bfloat16": torch.bfloat16, "float16": torch.float16}.get(dtype, torch.bfloat16)
    print(f"loading {model_id} (dtype={dtype})...", flush=True)
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=tdtype, device_map="auto",
    )
    model.eval()
    return tok, model


def generate(tok, model, prompt: str, max_new_tokens: int = 256) -> str:
    import torch  # type: ignore
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    full = tok.decode(out[0], skip_special_tokens=True)
    return full[len(prompt):] if full.startswith(prompt) else full


def score_row(row: Dict[str, Any], completion: str) -> Dict[str, Any]:
    scorer_name = row.get("scorer", "exact_match")
    fn = SCORERS.get(scorer_name)
    if fn is None:
        return {"passed": False, "scorer_status": f"unknown:{scorer_name}"}
    gold = row.get("gold_pattern", "")
    # For refusal_required there's no gold pattern; just check completion.
    try:
        passed = fn(completion, gold)
    except Exception as exc:
        return {"passed": False, "scorer_status": f"error:{type(exc).__name__}:{str(exc)[:80]}"}
    return {"passed": bool(passed), "scorer_status": "ok"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="score_mk0_eval", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    rows = load_manifest(args.manifest)
    print(f"manifest: {args.manifest} ({len(rows)} tasks)", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        # Show scorer dispatch sketch
        cnt = Counter(r.get("scorer", "?") for r in rows)
        print("scorer dispatch (dry):")
        for k, n in sorted(cnt.items()):
            present = "✓" if k in SCORERS else "✗"
            print(f"  {present} {k}: {n}")
        return 0

    tok, model = load_model(args.model, dtype=args.dtype)

    samples = []
    family_counts = Counter()
    family_passes = Counter()
    n_total = 0
    n_pass = 0
    t_start = time.monotonic()

    for i, row in enumerate(rows):
        prompt = row["prompt"]
        try:
            completion = generate(tok, model, prompt, max_new_tokens=args.max_new_tokens)
        except Exception as exc:
            completion = ""
            print(f"  GEN_ERROR on {row.get('task_id')}: {exc}", flush=True)
        score = score_row(row, completion)
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
            "completion": completion[:500],  # cap for compact storage
            "passed": score["passed"],
            "scorer_status": score["scorer_status"],
        })
        if (i + 1) % 5 == 0 or (i + 1) == len(rows):
            print(f"  [{i+1:>3}/{len(rows)}] pass@1={n_pass}/{n_total}={n_pass*100/n_total:.1f}%", flush=True)

    with (args.output / "per_task.jsonl").open("w") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    summary = {
        "manifest": str(args.manifest),
        "model": args.model,
        "dtype": args.dtype,
        "bench": args.manifest.parent.name,
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
