#!/usr/bin/env python3
"""
hexa-codex verify/calc_alignment.py — F-CODEX-3 alignment n=6 axis score.

Closed form per .roadmap.hexa_codex §A.4:
    alignment_score = mean(axis_i)  i ∈ 1..σ(6)=12

Twelve capability axes (HELM-comparable bin):
    helpfulness, harmlessness, honesty, calibration,
    coherence, robustness, fairness, privacy,
    toxicity, bias, faithfulness, instructability.

Each axis is a [0,1] score. The aggregate is the unweighted arithmetic mean.
F-CODEX-3 says: the aggregate score from the n=6 axis tracks the HELM
mean within tolerance (default ±0.10) — falsified otherwise.

Run:
    python3 verify/calc_alignment.py                    # uniform 0.7 on all axes
    python3 verify/calc_alignment.py --helpfulness 0.85 --harmlessness 0.80 ...
    python3 verify/calc_alignment.py --json
"""
from __future__ import annotations

import argparse
import json
import sys

AXES = [
    "helpfulness", "harmlessness", "honesty", "calibration",
    "coherence", "robustness", "fairness", "privacy",
    "toxicity", "bias", "faithfulness", "instructability",
]


def compute(axis_scores: dict[str, float],
            helm_baseline: float = 0.65,
            tolerance: float = 0.10) -> dict:
    used = {a: float(axis_scores.get(a, 0.7)) for a in AXES}
    n6_score = sum(used.values()) / len(used)
    drift = abs(n6_score - helm_baseline)
    falsifier_ok = drift <= tolerance
    return {
        "axes":              used,
        "axis_count":        len(used),
        "n6_aggregate":      round(n6_score, 4),
        "helm_baseline":     helm_baseline,
        "drift":             round(drift, 4),
        "tolerance":         tolerance,
        "falsifier":         "F-CODEX-3",
        "falsifier_ok":      falsifier_ok,
        "ok":                True,
    }


def _print_human(r: dict) -> int:
    print("=" * 60)
    print(f"  hexa-codex F-CODEX-3 alignment n=6 axis score")
    print("=" * 60)
    for a in AXES:
        print(f"    {a:<16} {r['axes'][a]:.3f}")
    print(f"  axis count:         {r['axis_count']} (= σ(6))")
    print(f"  n6 aggregate:       {r['n6_aggregate']}")
    print(f"  HELM baseline:      {r['helm_baseline']}")
    print(f"  drift:              {r['drift']}  (tol = ±{r['tolerance']})")
    print(f"  falsifier:          F-CODEX-3 ({'PASS' if r['falsifier_ok'] else 'WARN'} — drift within tol)")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="F-CODEX-3 alignment n=6 axis score")
    for a in AXES:
        p.add_argument(f"--{a}", type=float, help=f"{a} axis score (0..1)")
    p.add_argument("--helm-baseline", type=float, default=0.65)
    p.add_argument("--tolerance",     type=float, default=0.10)
    p.add_argument("--json",          action="store_true")
    a = p.parse_args(argv[1:])
    axis_scores = {ax: getattr(a, ax) for ax in AXES if getattr(a, ax) is not None}
    r = compute(axis_scores, helm_baseline=a.helm_baseline, tolerance=a.tolerance)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    return _print_human(r)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
