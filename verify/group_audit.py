#!/usr/bin/env python3
"""
hexa-codex verify/group_audit.py — 4-group / 17-verb consistency audit.

Cross-references the verb taxonomy across the four canonical surfaces:
  1. .roadmap.hexa_codex            — terminal-goal text + DoD per-group
  2. hexa.toml [modules]             — verb path table by group
  3. cli/hexa-codex.hexa verb_spec() — runtime dispatch table
  4. tests/test_selftest.hexa sentinel
  5. README.md group headings

If any surface declares a verb under a different group, or contains a
typo'd verb name, this audit reports the drift. Compare to hexa-sscb's
verify/cross_doc_audit.py — same enforcement-layer rationale.

Run:
    python3 verify/group_audit.py        # exit 0 = all surfaces agree
    python3 verify/group_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Canonical taxonomy (this file is SSOT — change here first, then propagate).
GROUPS = {
    "safety":    ["alignment", "safety", "welfare", "adversarial", "consciousness", "interpret"],
    "economics": ["train_cost", "infer_cost", "quality_scale"],
    "ops":       ["deploy", "enterprise", "agent_serving", "eval"],
    "substrate": ["multimodal", "rlhf", "cog_arch", "causal"],
}
ALL_VERBS = [v for vs in GROUPS.values() for v in vs]


# Surface 1: .roadmap.hexa_codex
def check_roadmap_groups() -> dict:
    rf = ROOT / ".roadmap.hexa_codex"
    if not rf.exists():
        return {"ok": False, "detail": ".roadmap.hexa_codex missing"}
    text = rf.read_text(encoding="utf-8")
    missing = [g for g in GROUPS if g not in text]
    return {"ok": not missing, "detail": {"missing_groups": missing}}


# Surface 2: hexa.toml [modules]
def check_hexa_toml_modules() -> dict:
    tf = ROOT / "hexa.toml"
    if not tf.exists():
        return {"ok": False, "detail": "hexa.toml missing"}
    text = tf.read_text(encoding="utf-8")
    missing_groups = []
    miscategorised: list[str] = []
    for group, verbs in GROUPS.items():
        # find the [modules] section and the group's array
        pat = re.compile(rf"^{group}\s*=\s*\[(.*?)\]", re.MULTILINE | re.DOTALL)
        m = pat.search(text)
        if not m:
            missing_groups.append(group)
            continue
        block = m.group(1)
        for verb in verbs:
            # verb appears as part of a path like "alignment/ai-alignment.md"
            verb_path_token = verb + "/"
            if verb_path_token not in block:
                miscategorised.append(f"{group}: missing {verb} (expected token {verb_path_token!r})")
    ok = not (missing_groups or miscategorised)
    return {"ok": ok, "detail": {
        "missing_groups": missing_groups,
        "miscategorised": miscategorised,
    }}


# Surface 3: cli/hexa-codex.hexa verb_spec() dispatch table
def check_cli_dispatch() -> dict:
    cf = ROOT / "cli/hexa-codex.hexa"
    if not cf.exists():
        return {"ok": False, "detail": "cli/hexa-codex.hexa missing"}
    text = cf.read_text(encoding="utf-8")
    missing = []
    for verb in ALL_VERBS:
        # verb_spec() lines are: if verb == "X" { return ... }
        if not re.search(rf'verb\s*==\s*"{verb}"', text):
            missing.append(verb)
    # also confirm group arrays
    for group, verbs in GROUPS.items():
        var = "VERBS_" + group.upper()
        if var not in text:
            missing.append(f"group var {var} missing")
    return {"ok": not missing, "detail": {"missing_in_cli": missing}}


# Surface 4: tests/test_selftest.hexa
def check_selftest_sentinel() -> dict:
    tf = ROOT / "tests/test_selftest.hexa"
    if not tf.exists():
        return {"ok": False, "detail": "tests/test_selftest.hexa missing"}
    text = tf.read_text(encoding="utf-8")
    needs = ["__HEXA_CODEX_SELFTEST__ PASS", "total verbs: 17", "present:     17/17"]
    missing = [s for s in needs if s not in text]
    return {"ok": not missing, "detail": {"missing_phrases": missing}}


# Surface 5: README.md group headings
def check_readme_groups() -> dict:
    rf = ROOT / "README.md"
    if not rf.exists():
        return {"ok": False, "detail": "README.md missing"}
    text = rf.read_text(encoding="utf-8")
    # We just confirm each group word appears at least once (case-insensitive).
    lc = text.lower()
    missing = [g for g in GROUPS if g not in lc]
    return {"ok": not missing, "detail": {"missing_in_readme": missing}}


# Surface 6: arithmetic — 17 = 6 + 3 + 4 + 4
def check_arithmetic() -> dict:
    s = sum(len(v) for v in GROUPS.values())
    ok = s == 17
    return {"ok": ok, "detail": {
        "computed_total": s,
        "expected_total": 17,
        "by_group": {g: len(v) for g, v in GROUPS.items()},
    }}


CHECKS = [
    ("arithmetic 6+3+4+4 = 17",           check_arithmetic),
    (".roadmap.hexa_codex group names",   check_roadmap_groups),
    ("hexa.toml [modules] tokens",        check_hexa_toml_modules),
    ("cli/hexa-codex.hexa dispatch",      check_cli_dispatch),
    ("tests/test_selftest.hexa sentinel", check_selftest_sentinel),
    ("README.md group mentions",          check_readme_groups),
]


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex group / verb consistency audit")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv[1:])

    results = []
    for name, fn in CHECKS:
        try:
            r = fn()
        except Exception as e:
            r = {"ok": False, "detail": {"error": repr(e)}}
        results.append({"name": name, **r})

    n_ok = sum(1 for r in results if r["ok"])
    n = len(results)

    if args.json:
        print(json.dumps({
            "tool": "hexa-codex verify/group_audit.py",
            "schema": "hexa-codex/group-audit/v1",
            "ok": n_ok == n,
            "checks_pass": n_ok, "checks_total": n,
            "results": results,
        }, indent=2, ensure_ascii=False))
        return 0 if n_ok == n else 1

    print("=" * 72)
    print("  hexa-codex — 4-group / 17-verb consistency audit")
    print("=" * 72)
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['name']}")
        d = r["detail"]
        if isinstance(d, dict):
            for k, v in d.items():
                if v in ([], "", None):
                    continue
                print(f"         · {k}: {v}")
        elif d:
            print(f"         · {d}")
    print("=" * 72)
    print(f"  {n_ok}/{n} surfaces agree")
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
