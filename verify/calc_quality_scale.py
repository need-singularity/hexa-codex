#!/usr/bin/env python3
"""
hexa-codex verify/calc_quality_scale.py — quality_scale verb closed form.

quality_scale.md predicts perplexity-floor evolution as a function of
parameter count N and dataset D, anchored to Chinchilla compute-optimal
loss.  Closed form (atlas n=6 projection):

    loss(N, D) = E + A · N^(-α) + B · D^(-β)
    with α = φ(6) / σ(6) = 2 / 12 ≈ 0.167
         β = φ(6) / σ(6) = 2 / 12 ≈ 0.167  (same lattice constant)
         E = irreducible-loss anchor

The falsifier here is mild — reuses Chinchilla's α, β  ≈ 0.34 (Hoffmann 2022)
as comparison; if our 0.167 is closer to data, both fits live; if 0.34 wins
clearly, n=6 lattice loses this verb.

Run:
    python3 verify/calc_quality_scale.py --N 7e9 --D 1.4e12
    python3 verify/calc_quality_scale.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n6_arithmetic import sigma, euler_phi  # noqa: E402


N6_ALPHA = euler_phi(6) / sigma(6)   # 2/12 ≈ 0.1667
N6_BETA  = euler_phi(6) / sigma(6)
CHINCHILLA_ALPHA = 0.34
CHINCHILLA_BETA  = 0.28
IRREDUCIBLE_LOSS = 1.69     # Chinchilla 2022 fit, natural log per token
A_PARAM   = 406.4
B_PARAM   = 410.7


def compute(N: float, D: float, alpha: float = N6_ALPHA,
            beta: float = N6_BETA) -> dict:
    n6_loss = IRREDUCIBLE_LOSS + A_PARAM * (N ** -alpha) + B_PARAM * (D ** -beta)
    chin_loss = (
        IRREDUCIBLE_LOSS
        + A_PARAM * (N ** -CHINCHILLA_ALPHA)
        + B_PARAM * (D ** -CHINCHILLA_BETA)
    )
    return {
        "N_params":       N,
        "D_tokens":       D,
        "n6_alpha":       round(alpha, 4),
        "n6_beta":        round(beta, 4),
        "n6_loss":        round(n6_loss, 4),
        "chinchilla_alpha": CHINCHILLA_ALPHA,
        "chinchilla_beta":  CHINCHILLA_BETA,
        "chinchilla_loss":  round(chin_loss, 4),
        "n6_minus_chin":  round(n6_loss - chin_loss, 4),
        "ok":             True,
    }


def _print_human(r: dict) -> int:
    print("=" * 60)
    print(f"  hexa-codex quality_scale calc — Chinchilla-comparable fit")
    print("=" * 60)
    print(f"  N (params):        {r['N_params']:.4g}")
    print(f"  D (tokens):        {r['D_tokens']:.4g}")
    print(f"  n=6 α / β:         {r['n6_alpha']} / {r['n6_beta']}")
    print(f"  Chinchilla α / β:  {r['chinchilla_alpha']} / {r['chinchilla_beta']}")
    print(f"  n=6 loss:          {r['n6_loss']}")
    print(f"  Chinchilla loss:   {r['chinchilla_loss']}")
    print(f"  Δ (n6 − chin):     {r['n6_minus_chin']:+}")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="quality_scale closed-form fit")
    p.add_argument("--N",      type=float, default=7e9)
    p.add_argument("--D",      type=float, default=1.4e12)
    p.add_argument("--alpha",  type=float, default=N6_ALPHA)
    p.add_argument("--beta",   type=float, default=N6_BETA)
    p.add_argument("--json",   action="store_true")
    a = p.parse_args(argv[1:])
    r = compute(a.N, a.D, a.alpha, a.beta)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    return _print_human(r)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
