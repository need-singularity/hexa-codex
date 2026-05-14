#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""score_brier_mk0.py — classifier confidence calibration eval (r52).

Measures whether `ClassifierDecision.confidence` actually predicts accuracy.

INPUTS
- `bench/score-orchestration-mk0-r51/per_task_orchestration.jsonl`
  (or any per_task_orchestration.jsonl emitted by score_orchestration_mk0.py)
  — each row has `confidence` (classifier's emitted [0..1] score) and `ok`
  (True if got==expected).

METRICS
- **Brier score**: mean((confidence - outcome)²) where outcome ∈ {0,1}.
  Range [0, 1]; lower = better calibrated. Perfect (always 1.0 confidence on
  correct + 0.0 confidence on wrong) = 0.0. Worst (always 1.0 confidence,
  always wrong) = 1.0. Uniform random (always 0.5) = 0.25.
- **ECE** (Expected Calibration Error): weighted mean per-bin gap
  between avg confidence and avg accuracy. Range [0, 1]; lower = better.
  10-bin equal-width discretization (DEFAULT).
- **Reliability table**: per-bin (avg_conf, avg_acc, n) showing the
  calibration curve numerically (no plot dependency).
- **Overconfidence/underconfidence**: signed mean (conf - acc) per bin
  — positive = overconfident in that band, negative = underconfident.

OUTPUTS
- `bench/score-brier-mk0/brier.json` — summary metrics
- `bench/score-brier-mk0/reliability_table.txt` — text reliability diagram
- Console: same as `reliability_table.txt` plus headline summary

USAGE
    python3 tool/score_brier_mk0.py
        --input bench/score-orchestration-mk0-r51/per_task_orchestration.jsonl
        --output bench/score-brier-mk0
        --bins 10
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _bin_index(conf: float, n_bins: int) -> int:
    """Map confidence [0,1] → bin index [0, n_bins-1]."""
    if conf >= 1.0:
        return n_bins - 1
    return int(conf * n_bins)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path,
                    help="per_task_orchestration.jsonl from score_orchestration_mk0.py")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--bins", type=int, default=10,
                    help="Number of confidence bins (equal-width, default 10)")
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.input.read_text().splitlines() if l.strip()]
    print(f"loaded {len(rows)} per-task rows from {args.input}")

    # Filter to rows with confidence ∈ [0,1] AND boolean ok
    valid = [r for r in rows
             if isinstance(r.get("confidence"), (int, float))
             and 0.0 <= r["confidence"] <= 1.0
             and isinstance(r.get("ok"), bool)]
    n = len(valid)
    if n == 0:
        print("ERROR: no valid rows (need confidence ∈ [0,1] and ok ∈ {True,False})")
        return 1
    if n < len(rows):
        print(f"  filtered: {len(rows)-n} rows lacked confidence or ok")

    # Brier score
    brier = sum((r["confidence"] - (1.0 if r["ok"] else 0.0)) ** 2 for r in valid) / n

    # Per-bin reliability + ECE
    bin_n = defaultdict(int)
    bin_conf_sum = defaultdict(float)
    bin_correct = defaultdict(int)
    for r in valid:
        b = _bin_index(r["confidence"], args.bins)
        bin_n[b] += 1
        bin_conf_sum[b] += r["confidence"]
        if r["ok"]:
            bin_correct[b] += 1

    ece = 0.0
    bins_report = []  # list of (bin_lo, bin_hi, n, avg_conf, avg_acc, gap)
    for b in range(args.bins):
        if bin_n[b] == 0:
            continue
        bin_lo = b / args.bins
        bin_hi = (b + 1) / args.bins
        avg_conf = bin_conf_sum[b] / bin_n[b]
        avg_acc = bin_correct[b] / bin_n[b]
        gap = avg_conf - avg_acc  # +ve = overconfident
        ece += (bin_n[b] / n) * abs(gap)
        bins_report.append((bin_lo, bin_hi, bin_n[b], avg_conf, avg_acc, gap))

    # Per-label breakdown (refuse / hexa / ood)
    per_label = defaultdict(lambda: {"n": 0, "correct": 0, "conf_sum": 0.0, "brier_sum": 0.0})
    for r in valid:
        lab = r.get("got") or "?"
        per_label[lab]["n"] += 1
        per_label[lab]["correct"] += int(r["ok"])
        per_label[lab]["conf_sum"] += r["confidence"]
        per_label[lab]["brier_sum"] += (r["confidence"] - (1.0 if r["ok"] else 0.0)) ** 2

    # Summary
    n_correct = sum(1 for r in valid if r["ok"])
    avg_conf_overall = sum(r["confidence"] for r in valid) / n
    avg_acc_overall = n_correct / n

    args.output.mkdir(parents=True, exist_ok=True)

    summary = {
        "input": str(args.input),
        "n_tasks_scored": n,
        "n_correct": n_correct,
        "overall_accuracy": round(avg_acc_overall, 4),
        "overall_avg_confidence": round(avg_conf_overall, 4),
        "calibration_gap_overall": round(avg_conf_overall - avg_acc_overall, 4),  # +ve = over
        "brier_score": round(brier, 4),
        "ece_n_bins": args.bins,
        "ece": round(ece, 4),
        "per_bin": [
            {
                "bin": f"[{lo:.2f}, {hi:.2f})",
                "n": int(n_b),
                "avg_confidence": round(c, 4),
                "avg_accuracy": round(a, 4),
                "gap": round(g, 4),
            }
            for (lo, hi, n_b, c, a, g) in bins_report
        ],
        "per_label": {
            lab: {
                "n": d["n"],
                "accuracy": round(d["correct"] / d["n"], 4) if d["n"] else 0.0,
                "avg_confidence": round(d["conf_sum"] / d["n"], 4) if d["n"] else 0.0,
                "brier_score": round(d["brier_sum"] / d["n"], 4) if d["n"] else 0.0,
            }
            for lab, d in sorted(per_label.items())
        },
        "interpretation": _interpret(brier, ece, avg_conf_overall - avg_acc_overall),
    }

    out_json = args.output / "brier.json"
    out_json.write_text(json.dumps(summary, indent=2))

    # Text reliability table
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("CLASSIFIER CALIBRATION (Brier + ECE)")
    lines.append("=" * 78)
    lines.append(f"input:      {args.input}")
    lines.append(f"n_tasks:    {n}  (correct: {n_correct}, accuracy: {avg_acc_overall:.4f})")
    lines.append(f"avg conf:   {avg_conf_overall:.4f}")
    lines.append(f"overall gap (conf - acc): {avg_conf_overall - avg_acc_overall:+.4f}  "
                 f"({'over' if avg_conf_overall > avg_acc_overall else 'under'}confident)")
    lines.append("")
    lines.append(f"BRIER SCORE: {brier:.4f}  (lower is better; perfect=0.0, uniform-random=0.25)")
    lines.append(f"ECE ({args.bins} bins): {ece:.4f}  (lower is better; perfect=0.0)")
    lines.append("")
    lines.append("=" * 78)
    lines.append("RELIABILITY TABLE (per equal-width confidence bin)")
    lines.append("=" * 78)
    lines.append(f"{'bin':<14} {'n':>5} {'avg conf':>10} {'avg acc':>10} {'gap':>8}  reliability")
    for (lo, hi, n_b, c, a, g) in bins_report:
        # ASCII bar: 25-wide; conf vs acc as overlapping bars (using # and *)
        bar_conf = "#" * int(c * 25)
        bar_acc = "*" * int(a * 25)
        bar = f"conf{bar_conf:<25} acc{bar_acc:<25}"
        sig = "+" if g > 0.01 else ("-" if g < -0.01 else " ")
        lines.append(f"[{lo:.2f}, {hi:.2f})  {n_b:>5} {c:>10.4f} {a:>10.4f} {g:>+7.4f}{sig}  {bar}")
    lines.append("")
    lines.append("=" * 78)
    lines.append("PER-LABEL BREAKDOWN")
    lines.append("=" * 78)
    lines.append(f"{'label':<10} {'n':>5} {'accuracy':>10} {'avg conf':>10} {'brier':>10}")
    for lab, d in sorted(summary["per_label"].items()):
        lines.append(f"{lab:<10} {d['n']:>5} {d['accuracy']:>10.4f} "
                     f"{d['avg_confidence']:>10.4f} {d['brier_score']:>10.4f}")
    lines.append("")
    lines.append("=" * 78)
    lines.append("INTERPRETATION")
    lines.append("=" * 78)
    for line in summary["interpretation"]:
        lines.append("  " + line)
    lines.append("")

    text_report = "\n".join(lines)
    (args.output / "reliability_table.txt").write_text(text_report)
    print(text_report)
    print(f"\nwrote: {out_json}")
    print(f"wrote: {args.output / 'reliability_table.txt'}")

    return 0


def _interpret(brier: float, ece: float, gap: float) -> list[str]:
    out: list[str] = []
    # Brier interpretation
    if brier < 0.05:
        out.append(f"Brier {brier:.4f}: EXCELLENT calibration (rare for keyword classifiers).")
    elif brier < 0.10:
        out.append(f"Brier {brier:.4f}: GOOD calibration — confidence is predictive.")
    elif brier < 0.20:
        out.append(f"Brier {brier:.4f}: ACCEPTABLE — better than uniform-random (0.25).")
    elif brier < 0.25:
        out.append(f"Brier {brier:.4f}: WEAK — confidence is barely better than chance.")
    else:
        out.append(f"Brier {brier:.4f}: POOR — confidence is misleading (worse than random).")

    # ECE interpretation
    if ece < 0.05:
        out.append(f"ECE {ece:.4f}: classifier confidence tracks empirical accuracy well.")
    elif ece < 0.10:
        out.append(f"ECE {ece:.4f}: classifier confidence is loosely calibrated.")
    else:
        out.append(f"ECE {ece:.4f}: classifier confidence is poorly calibrated; "
                   f"avoid using it as a probability in downstream logic.")

    # Over/under
    if abs(gap) < 0.02:
        out.append(f"Overall gap {gap:+.4f}: classifier is on average well-calibrated (no systematic bias).")
    elif gap > 0:
        out.append(f"Overall gap {gap:+.4f}: classifier is OVERCONFIDENT (says it knows more than it does).")
    else:
        out.append(f"Overall gap {gap:+.4f}: classifier is UNDERCONFIDENT (hedges more than needed).")

    # Practical guidance
    out.append("")
    out.append("PRACTICAL USE: production code SHOULD NOT use confidence as a true probability")
    out.append("(e.g. for cost-sensitive cutoffs or expected-utility decisions) unless ECE < 0.05.")
    out.append("For routing decisions, the label is what matters; confidence is a tier-band signal.")

    return out


if __name__ == "__main__":
    raise SystemExit(main())
