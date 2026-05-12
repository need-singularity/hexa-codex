#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_rl_t4_prompts.py — Lever 4 GRPO prompt-only dataset (v0.4.0).

Generates training prompts for compile-feedback RL on T4 (enum declarations).
The eval's 100 T4 manifest prompts are HELD OUT — train only on paraphrases of
the same underlying enum specs (different variants, different prompt templates).

Output: a JSONL with one row per prompt:
  {"prompt": "### User:\n<task>\n### Assistant:\n", "gold_name": "<EnumName>", "spec_kind": "...", "complexity": ...}

The trainer (train_rl_grpo_t4.py) generates completions, compiles them with
hexa_cc, and scores binary reward. Gold_name is kept for the v2 substring-guard
reward (see papers/spec-lever4-compile-rl.md §8).

USAGE
    build_rl_t4_prompts.py --out <path>
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

random.seed(42)

# === Hexa-canon ENUM spec inventory =====================================
# 20 base enum specs × 15 variations each = 300 train prompts.
# Variants intentionally avoid type parameters (hexa-canon does NOT support
# `<T>` on enum decls — that's the lesson the RL has to teach the model).

ENUM_SPECS: list[tuple[str, list[str], str]] = [
    # (name, variants, complexity_tag) — hexa-canon supports unit + tuple variants
    # ONLY. NO struct variants (`Foo { x: i32 }`) — verified Parse error on hexa_cc
    # 2026-05-12. NO generics on the enum decl. These specs cover the answer-shape
    # the RL must teach the 7B to converge to.
    ("Color", ["Red", "Green", "Blue"], "unit"),
    ("State", ["Idle", "Running", "Stopped"], "unit"),
    ("Mood", ["Happy", "Sad", "Neutral", "Angry"], "unit"),
    ("Day", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "unit-large"),
    ("Visibility", ["Public", "Private", "Internal"], "unit"),
    ("Direction", ["North", "East", "South", "West"], "unit"),
    ("Level", ["Low", "Medium", "High", "Critical"], "unit"),
    ("Phase", ["Init", "Run", "Cleanup", "Done"], "unit"),
    ("Op", ["Add", "Sub", "Mul", "Div", "Neg"], "unit"),
    ("HttpMethod", ["Get", "Post", "Put", "Delete", "Patch"], "unit"),

    ("Token", ["Ident(String)", "Int(i64)", "Punct(char)", "Eof"], "tuple-mixed"),
    ("Lit", ["Bool(bool)", "Int(i64)", "Str(String)"], "tuple"),
    ("Number", ["Int(i64)", "Float(f64)"], "tuple"),
    ("Maybe", ["Just(i32)", "Nothing"], "tuple-and-unit"),
    ("HttpStatus", ["Code(u16)", "Unknown"], "tuple-and-unit"),
    ("Either", ["Left(String)", "Right(i32)"], "tuple"),
    ("Pair", ["Two(i32, i32)"], "tuple"),
    ("Verdict", ["Pass", "Fail(String)"], "tuple-and-unit"),
    ("Msg", ["Ping", "Pong", "Data(u32)"], "tuple-and-unit"),
    ("ParseResult", ["Ok(i32)", "Err(String)"], "tuple"),
]

# Prompt-template paraphrases.
# Two groups:
#  (1) NORMAL — eval's "non-generic" 68% of T4 prompts. These already pass for
#      the SFT'd r4 model (~75-80%); RL keeps them in distribution.
#  (2) GENERIC-BAIT — eval's "generic-form" 32% of T4 prompts (`Result<T>`,
#      `Option<T>`, `Pair<A, B>`, etc.) that explicitly mention type parameters.
#      The 7B regresses to Rust-style `enum Result<T> { ... }` on these — the
#      EXACT case RL must unlearn. Pilot showed reward=1.0 across the board
#      because no generic-bait prompts were in the train set; the full run
#      MUST include them to exercise the gradient on the failure mode.

PROMPT_TEMPLATES_NORMAL: list[str] = [
    "Write the hexa declaration for an enum named `{name}` with these variants: {vlist}.",
    "Declare the hexa enum `{name}`: `{vlist}`.",
    "Define `{name}` as a hexa enum — variants: {vlist}.",
    "Write a hexa enum `{name}` with variants `{vlist}` ({summary}).",
    "Produce the hexa enum declaration for `{name}` containing: {vlist}.",
    "In hexa, declare an enum `{name}` with the variants {vlist}.",
    "Hexa enum `{name}` definition. Variants: {vlist}.",
    "Emit the hexa source for an enum `{name}` with variants {vlist}.",
    "Write a single hexa enum declaration named `{name}`: {vlist}.",
    "Give me a hexa enum named `{name}` with these constructors: {vlist}.",
]

# Generic-bait templates — explicitly name type params in the prompt. The gold
# is still `enum {name}` (no generic), forcing RL to learn "ignore the type-param
# hint in the prompt; hexa-canon decl has no <...>".
PROMPT_TEMPLATES_GENERIC_BAIT: list[str] = [
    "Declare the hexa enum `{name}<T>`: `{vlist}`.",
    "Define `{name}<T>` as a hexa enum — variants: {vlist}.",
    "Write the hexa declaration for a generic enum `{name}<T>` with these variants: {vlist}.",
    "Produce the hexa enum `{name}<T>` containing: {vlist}.",
    "Write a hexa enum `{name}<T>` with variants `{vlist}` ({summary}).",
]

# For v0.4.0-rl-t4-v2: shift balance heavily toward generic-bait. RL v1 showed
# the generic emission survives 33% bait — the gradient signal isn't strong enough.
# v2: ~67% generic-bait + 33% normal. Equivalent specs → 100 normal + 200 bait.
PROMPT_TEMPLATES: list[str] = PROMPT_TEMPLATES_NORMAL[:5] + PROMPT_TEMPLATES_GENERIC_BAIT * 2  # 5 + 10 = 15


def summarize(variants: list[str]) -> str:
    """Short human-readable tag describing the variant mix."""
    has_unit = any("(" not in v and "{" not in v for v in variants)
    has_tuple = any("(" in v for v in variants)
    has_struct = any("{" in v for v in variants)
    bits = []
    if has_struct: bits.append("struct variants")
    if has_tuple: bits.append("tuple variants")
    if has_unit: bits.append("unit variants")
    return " + ".join(bits) if bits else "variants"


def fmt(prompt_body: str) -> str:
    return f"### User:\n{prompt_body}\n### Assistant:\n"


def gen_prompts() -> list[dict]:
    rows: list[dict] = []
    for name, variants, kind in ENUM_SPECS:
        vlist = ", ".join(variants)
        summ = summarize(variants)
        for tmpl in PROMPT_TEMPLATES:
            body = tmpl.format(name=name, vlist=vlist, summary=summ)
            rows.append({
                "prompt": fmt(body),
                "gold_name": name,
                "spec_kind": kind,
                "n_variants": len(variants),
            })
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    rows = gen_prompts()
    random.shuffle(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {args.out}  ({len(rows)} prompts)")

    # Manifest sanity
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r["spec_kind"]] = by_kind.get(r["spec_kind"], 0) + 1
    print("by spec_kind:")
    for k in sorted(by_kind):
        print(f"  {k:<20} {by_kind[k]:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
