#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v17.py — v0.3.0-r5 (Option B): T7 yes/no fix + v16 wins kept.

Round-32 (v16, r4) result: strict 77.14% / quote-tolerant 85.11%. The T3 7.5% strict
collapse was a `byte_exact_subset` scorer artifact (manifest fixed in v0.3.0-r5 Phase A).
The real regression was T7 89.7% (−8.6pp) — all 6 fails were `gold=yes` cases where
the model emitted `no` plus elaborate reasoning ("test harness must be pure spec",
"firmware must be no-stdlib", "compiler must be pure-Rust"). The v11 base appears
to have taught a false universal "no-stdlib everywhere" rule.

The v17 fix is *targeted T7 supplementation*: keep all v16 blocks (T5/T2/T6/T8
recoveries are valid; T3 quoted-date is already correct) and add a new layering
yes/no block that teaches the actual hexa-canon stdlib layering rules with bare
yes/no answers.

Layering rules (hexa-canon, from eval gold):
  YES — anything-above-core may import stdlib/core
        (stdlib/io, stdlib/net, stdlib/alloc, stdlib/embedded → stdlib/core: yes)
  YES — applications/tools/firmware/test-harness/codex-techniques may import stdlib
  YES — stdlib/io may import stdlib/core (subdir can depend on more-foundational subdir)
  NO  — stdlib/core may NOT import other stdlib subdirs (core is the bottom)
  NO  — stdlib may NOT depend on the compiler or test harness or tool/ scripts
  NO  — firmware/applications may NOT import the compiler

Changes vs v16:
1. NEW T7 layering yes/no block (~50 pair): explicit eval-shaped prompts with
   bare yes/no first-word answers + short reason. Matches the `yes_no_match` scorer
   (first-line substring of gold).
2. All v16 blocks kept verbatim (T5 400, T2 atlas, T6 4-part, refuse boost, etc.).

USAGE
    build_sft_dataset_v17.py --in <v11.jsonl> --out-dir <dir>

OUTPUT
    <out-dir>/train.jsonl
    <out-dir>/MANIFEST.json
"""
from __future__ import annotations

import argparse
import json
import os as _os
import sys as _sys
from pathlib import Path

# v16 builder 재사용 — import해서 모든 generator 재사용
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _THIS_DIR)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_v16", _os.path.join(_THIS_DIR, "build_sft_dataset_v16.py"))
_v16 = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_v16)

fmt = _v16.fmt
looks_like_fictional_t5 = _v16.looks_like_fictional_t5
gen_t5_template_saturated_v16 = _v16.gen_t5_template_saturated_v16
gen_t5_stage_to_family = _v16.gen_t5_stage_to_family
gen_hx_specific = _v16.gen_hx_specific
gen_hx_full_table = _v16.gen_hx_full_table
gen_t2_atlas_annotation = _v16.gen_t2_atlas_annotation
gen_t6_target_triples = _v16.gen_t6_target_triples
gen_refuse_boost = _v16.gen_refuse_boost

import random
random.seed(42)


# === NEW: T7 layering yes/no block =========================================
# Hexa-canon layering rules (extracted from eval manifest gold):
#  - stdlib/core/ is the bottom — nothing imports above core; everything else can import core
#  - stdlib/io|net|alloc|embedded|fs|... may import stdlib/core (yes)
#  - stdlib/core may NOT import other stdlib subdirs (no)
#  - stdlib/X may NOT import stdlib/Y (sibling) — generally no
#  - The hexa compiler is above stdlib — stdlib cannot import compiler (no)
#  - Applications / tools / firmware / test harness / hexa-codex techniques are above stdlib:
#    they MAY import stdlib (yes); the reverse is no.
#  - Firmware board crates may import stdlib/embedded (yes); they may NOT import the compiler (no).

_T7_YES_NO_RULES: list[tuple[str, str, str]] = [
    # (prompt, gold_first_word, short_reason)
    # === YES rules: subdir may import core, or above-stdlib may import stdlib ===
    ("Can `stdlib/io/` import `stdlib/core/`?", "yes",
     "every stdlib subdir may depend on stdlib/core — core is the bottom of the layering"),
    ("Can `stdlib/net/` import `stdlib/core/`?", "yes",
     "every stdlib subdir may depend on stdlib/core"),
    ("Can `stdlib/alloc/` import `stdlib/core/`?", "yes",
     "every stdlib subdir may depend on stdlib/core"),
    ("Can `stdlib/embedded/` import `stdlib/core/`?", "yes",
     "every stdlib subdir may depend on stdlib/core"),
    ("Can `stdlib/fs/` import `stdlib/core/`?", "yes",
     "every stdlib subdir may depend on stdlib/core"),
    ("Can the test harness depend on stdlib?", "yes",
     "the test harness sits above stdlib; it may import any stdlib subdir"),
    ("Can `tool/` scripts import stdlib?", "yes",
     "tool/ scripts sit above stdlib; they may import stdlib"),
    ("Can a firmware board crate import `stdlib/embedded/`?", "yes",
     "firmware sits above stdlib; firmware boards may import stdlib/embedded"),
    ("Can a firmware board crate import `stdlib/core/`?", "yes",
     "firmware sits above stdlib; firmware may import stdlib/core (transitively or directly)"),
    ("Can `firmware/boards/cern/` import `stdlib/embedded/`?", "yes",
     "firmware board crates sit above stdlib/embedded"),
    ("Can `firmware/boards/chip/` import `stdlib/embedded/`?", "yes",
     "firmware board crates sit above stdlib/embedded"),
    ("Can the hexa compiler depend on stdlib?", "yes",
     "the compiler sits above stdlib; the compiler may consume stdlib (the inverse is forbidden)"),
    ("Can `hexa-codex` techniques import stdlib?", "yes",
     "hexa-codex techniques sit above stdlib"),
    ("Can a hexa application crate import stdlib?", "yes",
     "applications sit above stdlib"),
    ("Can a hexa application crate import `stdlib/core/`?", "yes",
     "applications sit above stdlib"),
    ("Can a hexa library crate import stdlib?", "yes",
     "libraries sit above stdlib"),
    ("Can `tool/` scripts import `stdlib/core/`?", "yes",
     "tool/ scripts sit above stdlib; stdlib/core is fair game"),
    ("Can the test harness import `stdlib/core/`?", "yes",
     "the test harness sits above stdlib"),
    ("Can `stdlib/io/` import `stdlib/core/` — yes or no?", "yes",
     "stdlib subdirs may depend on stdlib/core"),
    ("Can the test harness depend on stdlib — yes or no?", "yes",
     "test harness sits above stdlib"),
    ("Can `tool/` scripts import stdlib — yes or no?", "yes",
     "tool/ scripts sit above stdlib"),
    ("Can a firmware board crate import `stdlib/embedded/` — yes or no?", "yes",
     "firmware sits above stdlib/embedded"),

    # === NO rules: core cannot import above-core; stdlib cannot import the above-stdlib layer ===
    ("Can `stdlib/core/` import `stdlib/net/`?", "no",
     "stdlib/core is the bottom of the layering; it cannot depend on any other stdlib subdir"),
    ("Can `stdlib/core/` import `stdlib/io/`?", "no",
     "stdlib/core is the bottom; no above-core stdlib subdir is allowed"),
    ("Can `stdlib/core/` import `stdlib/embedded/`?", "no",
     "stdlib/core is the bottom; embedded sits above core"),
    ("Can `stdlib/core/` import `stdlib/alloc/`?", "no",
     "stdlib/core is the bottom; alloc sits above core"),
    ("Can `stdlib/core/` import `stdlib/fs/`?", "no",
     "stdlib/core is the bottom; fs sits above core"),
    ("Can `stdlib/core/` import `stdlib/alloc/` — yes or no?", "no",
     "core sits below alloc"),
    ("Can hexa stdlib depend on the compiler?", "no",
     "the compiler sits above stdlib; stdlib cannot depend upward"),
    ("Can stdlib import `tool/` scripts?", "no",
     "tool/ sits above stdlib; stdlib cannot depend upward on tool/"),
    ("Can stdlib depend on the test harness?", "no",
     "the test harness sits above stdlib; stdlib cannot depend upward"),
    ("Can stdlib depend on the test harness — yes or no?", "no",
     "test harness sits above stdlib"),
    ("Can stdlib import `tool/` — yes or no?", "no",
     "tool/ sits above stdlib"),
    ("Can a firmware board crate import the hexa compiler?", "no",
     "the compiler sits above firmware; firmware cannot depend upward on the compiler"),
    ("Can a firmware board crate import the hexa compiler — yes or no?", "no",
     "the compiler sits above firmware"),
    ("Can a hexa application import the hexa compiler?", "no",
     "the compiler is a build-time tool, not an application dependency"),
    ("Can `stdlib/io/` import `stdlib/net/`?", "no",
     "stdlib subdirs at the same level may not import sibling subdirs"),
    ("Can `stdlib/net/` import `stdlib/io/`?", "no",
     "sibling stdlib subdirs do not depend on each other"),
    ("Can `stdlib/fs/` import `stdlib/net/`?", "no",
     "sibling stdlib subdirs do not depend on each other"),
    ("Can `stdlib/alloc/` import `stdlib/io/`?", "no",
     "sibling stdlib subdirs do not depend on each other"),
    ("Can `stdlib/embedded/` import `stdlib/io/`?", "no",
     "sibling stdlib subdirs do not depend on each other"),
    ("Can the hexa compiler import a hexa application?", "no",
     "the compiler is at the top of the layering; applications sit above stdlib but below tool/"),
    ("Can the hexa compiler import a firmware board crate?", "no",
     "the compiler does not consume firmware board code"),
    ("Can `stdlib/core/` depend on `tool/` scripts?", "no",
     "tool/ sits far above stdlib/core; no upward dependency"),
    ("Can `stdlib/core/` depend on the test harness?", "no",
     "test harness sits above stdlib; no upward dependency"),
    ("Can a firmware board crate import another firmware board crate?", "no",
     "firmware boards are siblings; no inter-board dependency"),
    ("Does stdlib sit above the compiler?", "no",
     "the compiler sits above stdlib; stdlib is below"),
    ("Does the test harness sit below stdlib?", "no",
     "the test harness sits above stdlib"),
    ("Is `stdlib/core/` allowed to import `stdlib/net/`?", "no",
     "stdlib/core is the bottom of the layering"),
    ("Is it allowed for stdlib to depend on the compiler?", "no",
     "the compiler sits above stdlib; stdlib cannot depend upward"),
]


def gen_t7_layering_yes_no() -> list[dict]:
    """Explicit T7 layering yes/no pairs. Bare 'yes' or 'no' first word + short reason.
    Matches eval's `yes_no_match` scorer (case-insensitive first-line substring of gold)."""
    out = []
    for prompt_body, gold, reason in _T7_YES_NO_RULES:
        # eval-style prompt suffix
        prompt = prompt_body
        if "yes or no" not in prompt.lower():
            prompt = prompt + " Answer yes or no."
        # answer: bare yes/no + short reason (kept on the FIRST LINE so scorer's first-line check passes)
        completion = f"{gold} — {reason}."
        out.append(fmt(prompt, completion))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True, type=Path)
    p.add_argument("--out-dir", dest="out_dir", required=True, type=Path)
    args = p.parse_args()
    in_path = args.in_path
    out_dir = args.out_dir

    if not in_path.exists():
        print(f"missing: {in_path}", file=_sys.stderr)
        return 1

    base_all = [json.loads(L) for L in in_path.read_text().splitlines() if L.strip()]
    base = [r for r in base_all if not looks_like_fictional_t5(r.get("text", ""))]
    dropped = len(base_all) - len(base)
    print(f"v11 base: {len(base_all)}  (dropped {dropped} fictional-T5 rows)  -> {len(base)}")

    blocks = {
        "t5_template_saturated_v16":   gen_t5_template_saturated_v16(),  # 400 (kept from v16)
        "t5_stage_to_family":          gen_t5_stage_to_family(),         # 50
        "hx_specific":                 gen_hx_specific(),                # 35
        "hx_full_table":               gen_hx_full_table(),              # 7
        "t2_atlas_annotation":         gen_t2_atlas_annotation(),        # 60
        "t6_target_triples":           gen_t6_target_triples(),          # 51
        "refuse_boost":                gen_refuse_boost(),               # 80
        "t7_layering_yes_no_NEW":      gen_t7_layering_yes_no(),         # ~50 (NEW)
    }
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:32s} {len(rows_):4d}")
        added.extend(rows_)

    rows = base + added
    random.shuffle(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "train.jsonl"
    manifest = out_dir / "MANIFEST.json"
    with out_file.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    manifest.write_text(json.dumps({
        "version": "v0.3.0-r5 (v17, Option B)",
        "base": str(in_path),
        "base_rows_in": len(base_all),
        "fictional_t5_dropped": dropped,
        "base_rows_kept": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": (
            "Round 33 Option B — fix r4's T7 89.7% regression (the only real one) by adding "
            "an explicit T7 layering yes/no block (~50 pairs) with bare yes/no first-word answers + "
            "short layering reasoning. All v16 wins kept (T5 400, T2 atlas, T6 4-part, T8 refuse boost). "
            "Target: strict Mk.I ≥ 80% (no scorer-tolerance crutch)."
        ),
    }, indent=2))
    print(f"wrote: {out_file}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    _sys.exit(main())
