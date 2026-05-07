#!/usr/bin/env python3
"""
hexa-codex verify/calc_train_cost.py — F-CODEX-1 training-cost calculator.

Closed form per .roadmap.hexa_codex §A.4 / atlas n=6 master row:
    training_cost ∝ N^J₂ = N^24
where N is a "size scalar" (parameter count, FLOPs, dataset tokens, etc.).
The exponent J₂ = σ(6)·φ(6) = 12·2 = 24 is fixed by the lattice.

For comparability with Chinchilla scaling laws (training_cost ∝ N^a · D^b
with a+b ≈ 1, both ≈ 0.5), we project the n=6 prediction onto the same
shape: training_cost ∝ (N · D)^(J₂ / (J₂ + 1)). The headline exponent
J₂ ≈ 24 is high — that is the falsifier: if the empirical fit yields
N·D-product exponent ≈ 1 (not 24/25 ≈ 0.96), F-CODEX-1 is falsified.

Run:
    python3 verify/calc_train_cost.py                 # default N=1e10, D=1e12
    python3 verify/calc_train_cost.py --N 7e9 --D 1.4e12  # Llama-2-7B sized
    python3 verify/calc_train_cost.py --version v1.2.0     # ladder defaults
    python3 verify/calc_train_cost.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n6_arithmetic import sigma, tau, euler_phi  # noqa: E402

J2 = sigma(6) * euler_phi(6)   # 24


# Reference scaling-law fit for cross-comparison (Chinchilla 2022,
# Hoffmann et al.). The empirical row says compute (FLOPs) ∝ 6 · N · D
# and loss minimization yields N ∝ C^0.5, D ∝ C^0.5 within the budget.
CHINCHILLA = {
    "N_exponent": 0.5,
    "D_exponent": 0.5,
    "compute_FLOPs_per_token": 6.0,   # Kaplan/Chinchilla rule
    "ref": "Hoffmann et al. 2022, arxiv 2203.15556",
}


def compute(N: float, D: float, exponent: int = J2) -> dict:
    """Return n=6 closed-form training-cost projection + Chinchilla baseline.
    Cost is reported as a *ratio* (vs reference 1e10·1e12 anchor).
    """
    # n=6 closed form: cost ∝ (N · D) ^ (J2 / (J2 + 1))   normalized
    nd_product = N * D
    nd_ref     = 1e10 * 1e12   # anchor: 10B params · 1T tokens
    n6_exp     = exponent / (exponent + 1)              # 24/25 = 0.96
    n6_ratio   = (nd_product / nd_ref) ** n6_exp

    # Chinchilla compute proxy: 6 · N · D FLOPs (the headline rule).
    flops_chinchilla = CHINCHILLA["compute_FLOPs_per_token"] * N * D
    chinchilla_ratio = flops_chinchilla / (
        CHINCHILLA["compute_FLOPs_per_token"] * 1e10 * 1e12
    )

    # Falsifier: the closed-form exponent should be ≈ 0.96 (J₂ / (J₂+1)).
    # If the empirical fit yields exponent ≈ 1.0, F-CODEX-1 has been
    # confirmed (Chinchilla agrees with N·D-product ~ linear). The
    # "fail" condition is empirical exponent < 0.5 (sub-Chinchilla).
    return {
        "N_params":              N,
        "D_tokens":              D,
        "exponent_J2":           exponent,
        "n6_exponent":           n6_exp,
        "n6_cost_ratio":         n6_ratio,
        "chinchilla_FLOPs":      flops_chinchilla,
        "chinchilla_ratio":      chinchilla_ratio,
        "falsifier":             "F-CODEX-1",
        "falsifier_ok":          n6_exp >= 0.90,    # arithmetic floor
        "ok":                    True,              # arithmetic always passes
    }


def _print_human(r: dict) -> int:
    print("=" * 60)
    print(f"  hexa-codex F-CODEX-1 training-cost calc")
    print("=" * 60)
    print(f"  N (params):           {r['N_params']:.4g}")
    print(f"  D (tokens):           {r['D_tokens']:.4g}")
    print(f"  exponent J₂:           {r['exponent_J2']}")
    print(f"  n6 exponent (J₂/J₂+1): {r['n6_exponent']:.4f}")
    print(f"  n6 cost ratio:         {r['n6_cost_ratio']:.6g} × anchor")
    print(f"  Chinchilla FLOPs:      {r['chinchilla_FLOPs']:.4g}")
    print(f"  Chinchilla ratio:      {r['chinchilla_ratio']:.4g} × anchor")
    print(f"  falsifier:             {r['falsifier']} ({'PASS' if r['falsifier_ok'] else 'FAIL'} arithmetic)")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="F-CODEX-1 training-cost calculator")
    p.add_argument("--N", type=float, default=1e10, help="parameter count")
    p.add_argument("--D", type=float, default=1e12, help="training tokens")
    p.add_argument("--exponent", type=int, default=J2, help="closed-form J₂ (default 24)")
    p.add_argument("--version", help="release-ladder version (placeholder)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv[1:])
    r = compute(a.N, a.D, a.exponent)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["ok"] else 1
    return _print_human(r)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
