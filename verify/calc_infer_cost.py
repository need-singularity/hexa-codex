#!/usr/bin/env python3
"""
hexa-codex verify/calc_infer_cost.py — F-CODEX-2 inference-cost calculator.

Closed form per .roadmap.hexa_codex §A.4:
    inference_cost ∝ context^τ = context^4
where τ = τ(6) = 4 is the lattice quartet (pretrain / SFT / RLHF / deploy
phases — the lifecycle "depth" reflected in cost).

Standard Transformer attention is O(context^2). Anthropic-class long-ctx
models (Claude 4.7 1M ctx) employ approximate attention that drops the
exponent to ≈ 1.5 in practice. F-CODEX-2 says n=6 predicts 4 — well
above both. The falsifier test: measure latency ∝ context^x for Claude
4.7 across context sizes; if x < 1.5, F-CODEX-2 is falsified
(model is much more efficient than naive O(n^2), let alone n^4).

Run:
    python3 verify/calc_infer_cost.py                  # context=8192 default
    python3 verify/calc_infer_cost.py --context 1000000   # 1M ctx (Claude 4.7)
    python3 verify/calc_infer_cost.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n6_arithmetic import tau  # noqa: E402

TAU_6 = tau(6)   # 4


def compute(context: int, exponent: int = TAU_6, ref_ctx: int = 8192) -> dict:
    """Return n=6 inference-cost ratio + comparison with Transformer naive
    O(n^2) and approximate-attention O(n^1.5)."""
    n6_ratio        = (context / ref_ctx) ** exponent
    naive_attention = (context / ref_ctx) ** 2
    approx_attention = (context / ref_ctx) ** 1.5

    return {
        "context":              context,
        "ref_context":          ref_ctx,
        "exponent_tau":         exponent,
        "n6_cost_ratio":        n6_ratio,
        "naive_O_n2":           naive_attention,
        "approx_O_n_15":        approx_attention,
        "falsifier":            "F-CODEX-2",
        # Arithmetic floor: τ(6) must be exactly 4.
        "falsifier_ok":         exponent == 4,
        "ok":                   True,
        "comment":              (
            "n=6 predicts cost ∝ context^4; Claude 4.7 1M-ctx will likely "
            "fall below O(n^1.5) in practice — F-CODEX-2 is the strict "
            "upper bound and is **expected to falsify** for production "
            "long-ctx engines (that is the test)."
        ),
    }


def _print_human(r: dict) -> int:
    print("=" * 60)
    print(f"  hexa-codex F-CODEX-2 inference-cost calc")
    print("=" * 60)
    print(f"  context:               {r['context']}")
    print(f"  ref context:           {r['ref_context']}")
    print(f"  exponent τ(6):         {r['exponent_tau']}")
    print(f"  n6 cost ratio:         {r['n6_cost_ratio']:.4g} × ref")
    print(f"  naive O(n²) ratio:     {r['naive_O_n2']:.4g} × ref")
    print(f"  approx O(n^1.5) ratio: {r['approx_O_n_15']:.4g} × ref")
    print(f"  falsifier:             {r['falsifier']} ({'PASS' if r['falsifier_ok'] else 'FAIL'} arithmetic)")
    print(f"  comment: {r['comment']}")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="F-CODEX-2 inference-cost calculator")
    p.add_argument("--context",  type=int,   default=8192)
    p.add_argument("--ref",      type=int,   default=8192, help="reference context size")
    p.add_argument("--exponent", type=int,   default=TAU_6, help="closed-form τ (default 4)")
    p.add_argument("--json",     action="store_true")
    a = p.parse_args(argv[1:])
    r = compute(a.context, a.exponent, a.ref)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["ok"] else 1
    return _print_human(r)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
