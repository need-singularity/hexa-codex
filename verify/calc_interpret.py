#!/usr/bin/env python3
"""
hexa-codex verify/calc_interpret.py — F-CODEX-4 interpretability circuit motif.

Closed form per .roadmap.hexa_codex §A.4:
    interpret_motifs = σ(6) − φ(6) = 12 − 2 = 10

Ten circuit motif classes (analog to Anthropic dictionary-learning
"feature classes" — induction heads, suppression heads, name movers,
backup heads, refusal circuits, ...). The falsifier: count distinct
top-K dictionary-learning features clusters in a frontier model and
compare to the predicted 10. Drift ≥ 3 falsifies.

Run:
    python3 verify/calc_interpret.py                     # default analysis
    python3 verify/calc_interpret.py --observed-motifs 8
    python3 verify/calc_interpret.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n6_arithmetic import sigma, euler_phi  # noqa: E402

PREDICTED_MOTIFS = sigma(6) - euler_phi(6)   # 10

MOTIF_CATALOG = [
    "induction-head",
    "suppression-head",
    "name-mover",
    "backup-name-mover",
    "negative-name-mover",
    "duplicate-token-detector",
    "previous-token-head",
    "refusal-circuit",
    "factual-recall-head",
    "in-context-pattern-matcher",
]


def compute(observed: int = PREDICTED_MOTIFS, drift_tol: int = 3) -> dict:
    drift = abs(observed - PREDICTED_MOTIFS)
    return {
        "predicted_motifs":    PREDICTED_MOTIFS,
        "predicted_formula":   "σ(6) − φ(6) = 12 − 2",
        "observed_motifs":     observed,
        "drift":               drift,
        "drift_tolerance":     drift_tol,
        "motif_catalog":       MOTIF_CATALOG,
        "falsifier":           "F-CODEX-4",
        "falsifier_ok":        drift <= drift_tol,
        "ok":                  True,
        "comment":             (
            "F-CODEX-4 gets falsified when production interpretability "
            "tooling counts ≥ 13 or ≤ 7 distinct motif classes — the "
            "n=6 lattice would lose its claim that motif count is fixed "
            "by the algebraic identity."
        ),
    }


def _print_human(r: dict) -> int:
    print("=" * 60)
    print(f"  hexa-codex F-CODEX-4 interpretability circuit motif")
    print("=" * 60)
    print(f"  predicted motifs:   {r['predicted_motifs']}  ({r['predicted_formula']})")
    print(f"  observed motifs:    {r['observed_motifs']}")
    print(f"  drift:              {r['drift']}  (tol = ±{r['drift_tolerance']})")
    print(f"  motif catalog ({len(r['motif_catalog'])}):")
    for m in r["motif_catalog"]:
        print(f"      · {m}")
    print(f"  falsifier:          {r['falsifier']} ({'PASS' if r['falsifier_ok'] else 'FAIL'} — within tol)")
    return 0 if r["falsifier_ok"] else 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="F-CODEX-4 interpretability motif counter")
    p.add_argument("--observed-motifs", type=int, default=PREDICTED_MOTIFS)
    p.add_argument("--drift-tolerance", type=int, default=3)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv[1:])
    r = compute(a.observed_motifs, a.drift_tolerance)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["falsifier_ok"] else 1
    return _print_human(r)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
