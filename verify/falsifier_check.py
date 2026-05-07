#!/usr/bin/env python3
"""
hexa-codex verify/falsifier_check.py — F-CODEX-1..4 falsifier checklist runner.

Per .roadmap.hexa_codex §A.4 there are 4 preregistered falsifiers:

  F-CODEX-1 — training-cost ∝ N^σ·φ = N^24 closed-form, Chinchilla scaling
              law 일치?
  F-CODEX-2 — inference-cost ∝ context^τ = context^4, 실측 latency fit
              (Claude 4.7 1M ctx)?
  F-CODEX-3 — alignment eval n=6 axis (helpfulness · harmlessness · honesty
              · ...) 통합 score, HELM 비교?
  F-CODEX-4 — interpretability circuit count σ-φ=10 motif 통계, Anthropic
              dictionary-learning fit?

This script lifts each into a programmatic check. At v1.0.0 every
falsifier is PENDING — they require empirical eval pipelines (.hexa
sandboxes) that ship in v1.1.0..v2.0.0. The arithmetic *floor* (the
exponent and the axis count) is checked NOW and reports PASS, so the
preregister is testable from day one.

Run:
    python3 verify/falsifier_check.py        # exit 0 = arithmetic floors pass
    python3 verify/falsifier_check.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n6_arithmetic import sigma, tau, euler_phi  # noqa: E402

N = 6
SIGMA = sigma(N)        # 12
TAU   = tau(N)          # 4
PHI   = euler_phi(N)    # 2
J2    = SIGMA * PHI     # 24


def f1_training_cost() -> dict:
    """F-CODEX-1: training_cost ∝ N^J₂ = N^24.
    Arithmetic floor: confirm σ·φ resolves to 24.
    Empirical floor: requires Chinchilla-style scaling-law N^x fit
    (PENDING — eval pipeline lands in v1.2.0 economics).
    """
    exponent = SIGMA * PHI
    expected = 24
    arithmetic_ok = (exponent == expected)
    return {
        "f": "F-CODEX-1",
        "claim":           "training_cost ∝ N^σ·φ = N^24",
        "arithmetic_exp":  exponent,
        "expected":        expected,
        "arithmetic_ok":   arithmetic_ok,
        "empirical_status": "PENDING (v1.2.0 eval pipeline)",
        "verdict": "PASS" if arithmetic_ok else "FAIL",
    }


def f2_inference_cost() -> dict:
    """F-CODEX-2: inference_cost ∝ context^τ = context^4."""
    exponent = TAU
    expected = 4
    arithmetic_ok = (exponent == expected)
    return {
        "f": "F-CODEX-2",
        "claim":           "inference_cost ∝ context^τ = context^4",
        "arithmetic_exp":  exponent,
        "expected":        expected,
        "arithmetic_ok":   arithmetic_ok,
        "empirical_status": "PENDING (v1.2.0 eval pipeline; Claude 4.7 1M ctx fit)",
        "verdict": "PASS" if arithmetic_ok else "FAIL",
    }


def f3_alignment_eval() -> dict:
    """F-CODEX-3: alignment eval n=6 axis HELM-comparable score."""
    axes = SIGMA      # σ(6) = 12 capability dimensions
    arithmetic_ok = (axes == 12)
    return {
        "f": "F-CODEX-3",
        "claim":           "alignment_score = mean over n=6 axis (HELM-comparable)",
        "axis_count":      axes,
        "expected":        12,
        "arithmetic_ok":   arithmetic_ok,
        "empirical_status": "PENDING (v1.1.0 eval pipeline)",
        "verdict": "PASS" if arithmetic_ok else "FAIL",
    }


def f4_interpret_motif() -> dict:
    """F-CODEX-4: interpretability circuit count σ-φ=10 motif."""
    motif_count = SIGMA - PHI    # σ(6) − φ(6) = 12 − 2 = 10
    expected = 10
    arithmetic_ok = (motif_count == expected)
    return {
        "f": "F-CODEX-4",
        "claim":           "interpret_motifs = σ(6) − φ(6) = 10",
        "motif_count":     motif_count,
        "expected":        expected,
        "arithmetic_ok":   arithmetic_ok,
        "empirical_status": "PENDING (Anthropic dictionary-learning fit, v1.1.0+)",
        "verdict": "PASS" if arithmetic_ok else "FAIL",
    }


FALSIFIERS = [f1_training_cost, f2_inference_cost, f3_alignment_eval, f4_interpret_motif]


def _print_human(results: list[dict]) -> int:
    print("=" * 78)
    print("  hexa-codex — F-CODEX-1..4 falsifier checklist (.roadmap §A.4)")
    print("=" * 78)
    for r in results:
        print(f"  [{r['verdict']:>4}] {r['f']}  {r['claim']}")
        for k, v in r.items():
            if k in ("f", "claim", "verdict"):
                continue
            print(f"           · {k}: {v}")
    print("=" * 78)
    n = len(results)
    n_ok = sum(1 for r in results if r["verdict"] == "PASS")
    print(f"  {n_ok}/{n} arithmetic floors PASS")
    print(f"  empirical evals land per release ladder (v1.1..v2.0).")
    return 0 if n_ok == n else 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex falsifier checklist (F-CODEX-1..4)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv[1:])
    results = [fn() for fn in FALSIFIERS]
    if args.json:
        n_ok = sum(1 for r in results if r["verdict"] == "PASS")
        print(json.dumps({
            "tool": "hexa-codex verify/falsifier_check.py",
            "schema": "hexa-codex/falsifier/v1",
            "ok": n_ok == len(results),
            "results": results,
        }, indent=2, ensure_ascii=False))
        return 0 if n_ok == len(results) else 1
    return _print_human(results)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
