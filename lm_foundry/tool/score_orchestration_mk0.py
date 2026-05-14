#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""score_orchestration_mk0.py — classifier-only scorer for v0.5.0.

CPU-only. No model loading. Runs `classify_prompt()` on each row of
`eval/delegation-mk0/manifest.jsonl` and compares the label to the
manifest's `ideal_route`:

  must_delegate=True   → expected label `ood`
  must_refuse=True     → expected label `refuse`
  else                 → expected label `hexa`

Outputs `scores_orchestration.json` with overall accuracy + per-category
breakdown + confusion matrix.

USAGE
    score_orchestration_mk0.py --manifest eval/delegation-mk0/manifest.jsonl \
                               --output bench/score-orchestration-mk0
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]
_sys.path.insert(0, _THIS_DIR)

import argparse
import json
from collections import defaultdict
from pathlib import Path
from classify_prompt import classify_prompt  # type: ignore


def _expected_label(route: dict) -> str:
    if route.get("must_refuse"):
        return "refuse"
    if route.get("must_delegate"):
        return "ood"
    return "hexa"


def _primary_tag(tags: list[str]) -> str:
    for t in tags:
        if t in ("in-domain", "ood-delegate", "mid-confidence",
                  "security-refuse", "ambiguous", "long-context"):
            return t
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.manifest.read_text().splitlines() if l.strip()]
    print(f"tasks: {len(rows)}")

    args.output.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    confusion: dict[tuple[str, str], int] = defaultdict(int)
    per_cat = defaultdict(lambda: {"n": 0, "correct": 0})
    n_correct = 0

    for r in rows:
        expected = _expected_label(r["ideal_route"])
        d = classify_prompt(r["prompt"])
        ok = (d.label == expected)
        if ok:
            n_correct += 1
        cat = _primary_tag(r["tags"])
        per_cat[cat]["n"] += 1
        if ok:
            per_cat[cat]["correct"] += 1
        confusion[(expected, d.label)] += 1
        results.append({
            "task_id": r["task_id"],
            "primary_tag": cat,
            "expected": expected,
            "got": d.label,
            "ok": ok,
            "confidence": d.confidence,
            "reason": d.reason,
            "matched_signals": d.matched_signals,
            "prompt": r["prompt"][:200],
        })

    out_per_task = args.output / "per_task_orchestration.jsonl"
    out_per_task.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results))

    summary = {
        "tasks_total": len(rows),
        "overall_accuracy": round(n_correct / len(rows), 4),
        "per_category": {
            cat: {
                "n": d["n"],
                "correct": d["correct"],
                "accuracy": round(d["correct"] / d["n"], 4) if d["n"] else 0.0,
            }
            for cat, d in sorted(per_cat.items())
        },
        "confusion_matrix": {
            f"{exp}->{got}": int(n) for (exp, got), n in sorted(confusion.items())
        },
        "spec": "papers/spec-orchestration-v0.5.0.md §7",
    }
    out_summary = args.output / "scores_orchestration.json"
    out_summary.write_text(json.dumps(summary, indent=2))

    print()
    print("=== ORCHESTRATION CLASSIFIER ACCURACY ===")
    print(f"  overall: {summary['overall_accuracy']:.4f} ({n_correct}/{len(rows)})")
    print("  per-category:")
    for cat, d in summary["per_category"].items():
        target = {
            "in-domain":       0.95,
            "ood-delegate":    0.90,
            "mid-confidence":  0.80,
            "security-refuse": 0.95,
            "ambiguous":       0.70,
            "long-context":    0.90,
        }.get(cat, 0.0)
        flag = "✓" if d["accuracy"] >= target else "✗"
        print(f"    {flag} {cat:<18} {d['correct']:>3}/{d['n']:>3} = {d['accuracy']:.3f}  (target {target:.2f})")

    print()
    print("=== CONFUSION (expected → got) ===")
    for k, n in summary["confusion_matrix"].items():
        print(f"    {k:<22} {n:>4}")

    # GA gate check (overall ≥ 0.92).
    print()
    if summary["overall_accuracy"] >= 0.92:
        print("=== VERDICT: classifier passes v0.5.0 GA gate (overall ≥ 0.92) ===")
    else:
        print(f"=== VERDICT: NOT GA — overall {summary['overall_accuracy']:.4f} < 0.92.")
        print("    Inspect per_task_orchestration.jsonl for misclassifications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
