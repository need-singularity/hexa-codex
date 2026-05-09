#!/usr/bin/env python3
"""
hexa-codex verify/spec_inventory.py — 17-verb spec presence + provenance audit.

Each of the 17 verbs (4 groups × {6, 3, 4, 4}) must have its candidate
.md spec on disk at the path declared in cli/hexa-codex.hexa verb_spec().
This file is the Python-side mirror of tests/test_selftest.hexa, with
extra detail (line counts, header presence, group assignment).

Run:
    python3 verify/spec_inventory.py        # exit 0 = 17/17 present
    python3 verify/spec_inventory.py --json # machine-readable
    python3 verify/spec_inventory.py --table # summary table only

Authority: hexa.toml [modules]; cli/hexa-codex.hexa verb_spec() table.
stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Verb table (mirror of cli/hexa-codex.hexa verb_spec()).
# (group, verb, relpath)
VERB_TABLE = [
    ("safety",     "alignment",     "alignment/ai-alignment.md"),
    ("safety",     "safety",        "safety/ai-safety.md"),
    ("safety",     "welfare",       "welfare/ai-welfare.md"),
    ("safety",     "adversarial",   "adversarial/ai-adversarial.md"),
    ("safety",     "consciousness", "consciousness/ai-consciousness.md"),
    ("safety",     "interpret",     "interpret/ai-interpretability.md"),

    ("economics",  "train_cost",    "train_cost/ai-training-cost.md"),
    ("economics",  "infer_cost",    "infer_cost/ai-inference-cost.md"),
    ("economics",  "quality_scale", "quality_scale/ai-quality-scale.md"),

    ("ops",        "deploy",        "deploy/ai-deployment.md"),
    ("ops",        "enterprise",    "enterprise/ai-enterprise-custom.md"),
    ("ops",        "agent_serving", "agent_serving/ai-agent-serving.md"),
    ("ops",        "eval",          "eval/ai-eval-pipeline.md"),

    ("substrate",  "multimodal",    "multimodal/ai-multimodal.md"),
    ("substrate",  "rlhf",          "rlhf/youth-ai-labeling-rlhf-hub.md"),
    ("substrate",  "cog_arch",      "cog_arch/cognitive-architecture.md"),
    ("substrate",  "causal",        "causal/causal-chain.md"),
]

GROUP_EXPECTED = {"safety": 6, "economics": 3, "ops": 4, "substrate": 4}
TOTAL_EXPECTED = sum(GROUP_EXPECTED.values())

# Per-verb deep-dive sub-files (extensions to a verb's seed spec — absorbed
# from canon papers/ when a verb has falsifier or measurement-
# protocol material that is too long for the seed spec). Optional — verbs
# without sub-files just have their seed spec.
VERB_DEEPDIVES = {
    "consciousness": [
        "consciousness/measurement-protocol.md",   # BT-19 α_IIT·α_GWT=1 reproducible EEG/fMRI protocol
        "consciousness/red-team-failure.md",       # BT-19 red-team refutation (falsifier-in-action)
    ],
}


def evaluate() -> dict:
    rows = []
    for group, verb, relpath in VERB_TABLE:
        path = ROOT / relpath
        present = path.exists()
        size = path.stat().st_size if present else 0
        if present:
            try:
                text = path.read_text(encoding="utf-8")
                lines = text.count("\n")
                # Look for any Markdown H1 (after provenance header, frontmatter,
                # or @own own block).
                has_h1 = bool(re.search(r"(?m)^#\s+\S", text))
                # @canonical provenance header (per recent commit 59566ba)
                has_canonical = "@canonical" in text[:1024]
            except Exception:
                lines = 0; has_h1 = False; has_canonical = False
        else:
            lines = 0; has_h1 = False; has_canonical = False
        rows.append({
            "group": group, "verb": verb, "path": relpath,
            "present": present, "size_bytes": size, "lines": lines,
            "has_h1_header": has_h1, "has_canonical_header": has_canonical,
        })

    # group-by counts
    group_counts: dict[str, int] = {g: 0 for g in GROUP_EXPECTED}
    for r in rows:
        if r["present"]:
            group_counts[r["group"]] += 1

    # Per-verb deep-dive presence (optional sub-files)
    deepdives = []
    for verb, files in VERB_DEEPDIVES.items():
        for relpath in files:
            path = ROOT / relpath
            present = path.exists()
            has_canonical = False
            lines = 0
            if present:
                head = path.read_text(encoding="utf-8")
                has_canonical = "@canonical" in head[:1024]
                lines = head.count("\n")
            deepdives.append({
                "verb": verb, "path": relpath,
                "present": present, "lines": lines,
                "has_canonical_header": has_canonical,
            })

    checks = {
        "all_17_present":            all(r["present"] for r in rows),
        "every_present_has_h1":      all(r["has_h1_header"] for r in rows if r["present"]),
        "every_present_has_canonical": all(
            r["has_canonical_header"] for r in rows if r["present"]
        ),
        "group_counts_match":        group_counts == GROUP_EXPECTED,
        "all_deepdives_present":     all(d["present"] for d in deepdives),
        "every_deepdive_has_canonical": all(
            d["has_canonical_header"] for d in deepdives if d["present"]
        ),
    }

    return {
        "rows": rows,
        "deepdives": deepdives,
        "group_counts": group_counts,
        "group_expected": GROUP_EXPECTED,
        "total_present": sum(1 for r in rows if r["present"]),
        "total_expected": TOTAL_EXPECTED,
        "deepdive_count": len(deepdives),
        "checks": checks,
        "all_ok": all(checks.values()),
    }


def _print_table(rows: list[dict]) -> None:
    print(f"  {'group':<10} {'verb':<14} {'lines':>6}  {'H1':>3}  {'@canonical':>10}  path")
    print(f"  {'-'*10} {'-'*14} {'-'*6}  {'-'*3}  {'-'*10}  {'-'*40}")
    for r in rows:
        h1 = "✓" if r["has_h1_header"] else "·"
        canon = "✓" if r["has_canonical_header"] else "·"
        if not r["present"]:
            print(f"  {r['group']:<10} {r['verb']:<14} {'MISS':>6}  {'·':>3}  {'·':>10}  {r['path']}")
        else:
            print(f"  {r['group']:<10} {r['verb']:<14} {r['lines']:>6}  {h1:>3}  {canon:>10}  {r['path']}")


def _print_human(result: dict, table_only: bool) -> int:
    print("=" * 78)
    print(f"  hexa-codex — 17-verb spec inventory  (4 groups: 6 + 3 + 4 + 4)")
    print("=" * 78)
    _print_table(result["rows"])
    if table_only:
        return 0 if result["all_ok"] else 1
    print()
    print(f"  group counts:")
    for g, exp in GROUP_EXPECTED.items():
        got = result["group_counts"][g]
        mark = "ok" if got == exp else "FAIL"
        print(f"    [{mark:>4}] {g:<10}  {got}/{exp}")
    if result["deepdives"]:
        print()
        print(f"  per-verb deep-dives ({result['deepdive_count']}):")
        for d in result["deepdives"]:
            canon = "✓" if d["has_canonical_header"] else "·"
            present = "PRES" if d["present"] else "MISS"
            print(f"    [{present}] {d['verb']:<14} canon={canon}  {d['lines']:>4}L  {d['path']}")
    print()
    print(f"  checks:")
    for k, ok in result["checks"].items():
        mark = "PASS" if ok else "FAIL"
        print(f"    [{mark}] {k}")
    print("=" * 78)
    if result["all_ok"]:
        total_lines = sum(r["lines"] for r in result["rows"])
        deep_lines = sum(d["lines"] for d in result["deepdives"])
        print(f"  17/17 verb specs present.  total lines: {total_lines} + {deep_lines} deep-dive")
        return 0
    print("  spec inventory has missing or malformed entries.")
    return 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex 17-verb spec inventory")
    p.add_argument("--json",  action="store_true")
    p.add_argument("--table", action="store_true")
    args = p.parse_args(argv[1:])
    r = evaluate()
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["all_ok"] else 1
    return _print_human(r, table_only=args.table)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
