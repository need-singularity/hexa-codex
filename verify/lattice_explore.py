#!/usr/bin/env python3
"""
hexa-codex verify/lattice_explore.py — n=k lattice arithmetic explorer.

Generalizes the n=6 master row (.roadmap §A.1) to arbitrary n. Useful for
asking "if substrate-redesign Mk wants n=8 or n=12, does the σ·φ = n·τ
identity still hold?". Inside the n=6 lattice, only n ∈ {1, 6} satisfy
the identity in 1..24 (n=1 trivially, n=6 the Mathieu/Leech anchor).

Run:
    python3 verify/lattice_explore.py            # n=6 master row
    python3 verify/lattice_explore.py 12 24      # explicit ns
    python3 verify/lattice_explore.py --range 1 24
    python3 verify/lattice_explore.py --balanced-only --range 1 100
"""
from __future__ import annotations

import argparse
import json
import sys
from math import gcd


def divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]

def sigma(n: int) -> int:
    return sum(divisors(n))

def tau(n: int) -> int:
    return len(divisors(n))

def euler_phi(n: int) -> int:
    return sum(1 for k in range(1, n + 1) if gcd(k, n) == 1)


def row(n: int) -> dict:
    s, t, p = sigma(n), tau(n), euler_phi(n)
    return {
        "n":             n,
        "divisors":      divisors(n),
        "sigma":         s,
        "tau":           t,
        "phi":           p,
        "sigma_phi":     s * p,
        "n_tau":         n * t,
        "balanced":      (s * p) == (n * t),
        "n6_master_row": n == 6,
    }


def _print_table(rows: list[dict]) -> None:
    print(f"  {'n':>3} {'σ':>4} {'τ':>3} {'φ':>3} {'σ·φ':>5} {'n·τ':>5} {'bal':>4}  divisors")
    print(f"  {'-'*3} {'-'*4} {'-'*3} {'-'*3} {'-'*5} {'-'*5} {'-'*4}  {'-'*30}")
    for r in rows:
        bal = "✓" if r["balanced"] else "·"
        master = "★" if r["n6_master_row"] else " "
        print(f"  {r['n']:>3} {r['sigma']:>4} {r['tau']:>3} {r['phi']:>3} "
              f"{r['sigma_phi']:>5} {r['n_tau']:>5} {bal:>4}{master} {r['divisors']}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex n=k lattice explorer")
    p.add_argument("ns", nargs="*", type=int)
    p.add_argument("--range", nargs=2, type=int, metavar=("LO", "HI"))
    p.add_argument("--balanced-only", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv[1:])
    if a.range:
        ns = list(range(a.range[0], a.range[1] + 1))
    elif a.ns:
        ns = a.ns
    else:
        ns = [6]
    rows = [row(n) for n in ns]
    if a.balanced_only:
        rows = [r for r in rows if r["balanced"]]
    if not rows:
        print("(no balanced rows)", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    print("=" * 70)
    print("  hexa-codex n=k lattice explorer  —  σ·φ vs n·τ identity")
    print("=" * 70)
    _print_table(rows)
    print("=" * 70)
    print("  ★ = master row (.roadmap §A.1)   ✓ = balanced   · = unbalanced")
    bal_n = [r["n"] for r in rows if r["balanced"]]
    if bal_n:
        print(f"  balanced n in range: {bal_n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
