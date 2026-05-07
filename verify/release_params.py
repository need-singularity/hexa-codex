#!/usr/bin/env python3
"""
hexa-codex verify/release_params.py — per-release-version parameter registry.

Mirrors hexa-sscb's mk_params.py — central table of design parameters
per release-cadence step, derived from .roadmap.hexa_codex §A.2.

Release ladder (as of 2026-05-07):
  v1.0.0  released  2026-05-06    spec catalog only (17 verbs / 4 groups)
  v1.1.0  TARGET    ~2026-08      safety: alignment + interpretability eval pipeline .hexa
  v1.2.0  planned   ~2026-10      economics: training/inference cost n=6 scaling fit
  v1.3.0  planned   ~2026-12      ops: deploy + agent_serving 통합 .hexa
  v2.0.0  ASPIRE    ~2027-Q2      substrate: multimodal + cog_arch + causal + RLHF

Run:
    python3 verify/release_params.py            # tabular dump
    python3 verify/release_params.py v1.2.0     # single-version dump
    python3 verify/release_params.py --json
"""
from __future__ import annotations

import argparse
import json
import sys


# (version, release_date, status, group_focus, verbs_in_focus, eval_pipeline_count, falsifier_priority)
RELEASE_PARAMS = {
    "v1.0.0": {
        "year_month":      "2026-05",
        "status":          "RELEASED",
        "group_focus":     "(seed)",
        "verbs_in_focus":  17,
        "verbs_wired":     0,
        "verbs_spec":      17,
        "eval_pipelines":  0,
        "falsifier_focus": "(none — spec catalog only)",
        "milestone":       "17 verb seed + 4 group table",
    },
    "v1.1.0": {
        "year_month":      "2026-08",
        "status":          "TARGET",
        "group_focus":     "safety",
        "verbs_in_focus":  6,
        "verbs_wired":     2,        # alignment + interpretability target
        "verbs_spec":      17,
        "eval_pipelines":  1,
        "falsifier_focus": "F-CODEX-3 (alignment n=6 axis HELM fit)",
        "milestone":       "safety: alignment + interpretability eval pipeline .hexa",
    },
    "v1.2.0": {
        "year_month":      "2026-10",
        "status":          "PLANNED",
        "group_focus":     "economics",
        "verbs_in_focus":  3,
        "verbs_wired":     5,
        "verbs_spec":      17,
        "eval_pipelines":  2,
        "falsifier_focus": "F-CODEX-1 (training-cost N^J₂=N^24 scaling fit)",
        "milestone":       "economics: training/inference cost n=6 scaling fit (GPT-4 vs Claude 4.7)",
    },
    "v1.3.0": {
        "year_month":      "2026-12",
        "status":          "PLANNED",
        "group_focus":     "ops",
        "verbs_in_focus":  4,
        "verbs_wired":     9,
        "verbs_spec":      17,
        "eval_pipelines":  3,
        "falsifier_focus": "F-CODEX-2 (inference-cost context^τ=context^4 fit)",
        "milestone":       "ops: deploy + agent_serving 통합 .hexa",
    },
    "v2.0.0": {
        "year_month":      "2027-Q2",
        "status":          "ASPIRATIONAL",
        "group_focus":     "substrate",
        "verbs_in_focus":  4,
        "verbs_wired":     17,
        "verbs_spec":      17,
        "eval_pipelines":  4,
        "falsifier_focus": "F-CODEX-4 (interpretability circuit-count motif statistics)",
        "milestone":       "substrate: multimodal + cog_arch + causal + RLHF 통합 eval",
    },
}

PARAM_ORDER = [
    "year_month", "status", "group_focus",
    "verbs_in_focus", "verbs_wired", "verbs_spec",
    "eval_pipelines", "falsifier_focus", "milestone",
]


def get(version: str) -> dict:
    if version not in RELEASE_PARAMS:
        raise KeyError(f"unknown release: {version!r} (valid: {list(RELEASE_PARAMS)})")
    return dict(RELEASE_PARAMS[version])


def all_versions() -> dict:
    return {v: get(v) for v in RELEASE_PARAMS}


def _print_table() -> None:
    versions = list(RELEASE_PARAMS)
    print(f"  {'param':<18}  " + "  ".join(f"{v:>14}" for v in versions))
    print(f"  {'-'*18}  " + "  ".join("-"*14 for _ in versions))
    data = {v: get(v) for v in versions}
    for k in PARAM_ORDER:
        row = []
        for v in versions:
            cell = data[v].get(k, "")
            if isinstance(cell, str):
                cell = cell[:14]
                row.append(f"{cell:>14}")
            else:
                row.append(f"{cell:>14}")
        print(f"  {k:<18}  " + "  ".join(row))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex per-release-version parameter table")
    p.add_argument("version", nargs="?", help="single release (v1.0.0..v2.0.0); omit for table")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv[1:])
    if a.version:
        try:
            params = get(a.version)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        if a.json:
            print(json.dumps({"version": a.version, "params": params}, indent=2, ensure_ascii=False))
        else:
            print(f"  hexa-codex release parameters — {a.version}")
            print("  " + "-" * 60)
            for k in PARAM_ORDER:
                print(f"  {k:<18}  {params.get(k)}")
        return 0
    if a.json:
        print(json.dumps(all_versions(), indent=2, ensure_ascii=False))
    else:
        print("=" * 100)
        print("  hexa-codex release-parameter table  (v1.0.0..v2.0.0)")
        print("=" * 100)
        _print_table()
        print("=" * 100)
        print(f"  source: .roadmap.hexa_codex §A.2 release cadence")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
