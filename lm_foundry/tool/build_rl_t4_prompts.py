#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_rl_t4_prompts.py — Lever 4 GRPO prompt-only dataset (v0.4.0).

Generates training prompts for compile-feedback RL on T4 (enum declarations).
The eval's 100 T4 manifest prompts are HELD OUT — train only on paraphrases of
the same underlying enum specs (different prompt-template wordings; same enum
names + variant lists, matching the established split where only the *prompt
template* varies, not the enum content — see papers/spec-lever4-compile-rl.md §4).

Output: a JSONL with one row per prompt:
  {"prompt": "### User:\n<task>\n### Assistant:\n", "gold_name": "<EnumName>", "spec_kind": "...", "n_variants": ...}

The trainer (train_rl_grpo_t4.py) generates completions, compiles them with
hexa_cc, and scores binary reward (two-stage: structural guard + real compile).
`gold_name` / `n_variants` feed the structural-guard reward.

---------------------------------------------------------------------------
v0.4.0-rl-t4-v3 changes vs v2 (this round, r38):
  1. ENUM_SPECS gains the eval's residual-fail generic enum names — `Option`,
     `Result`, `Validated`, `Tree`, plus the multi-param `Either<E,T>`,
     `Pair<A,B>`, `Triple<A,B,C>`. v2's RL learned to drop `<T>` from the decl
     head only for the enum *names* it trained on (Maybe/Either/Pair) — it did
     NOT generalise to `Option<T>` / `Validated<T>` / `Tree<T>` (those names
     weren't in the train inventory; `Option<T>` in particular has a very strong
     Rust prior). The fix is name-level coverage, not just ratio.
  2. Generic-bait templates now honour each spec's actual generic-parameter
     string (`<T>`, `<E, T>`, `<A, B>`, `<A, B, C>`) instead of always `<T>`.
  3. Generic-bait ratio raised 67% → ~80% (4 normal templates + 16 bait = 20).
  4. The `Validated` / `Tree` specs carry their eval-faithful variant strings
     (`Invalid(Vec<String>)`, `Node(Box<Tree<T>>, Box<Tree<T>>)`) on purpose:
     `Vec<...>` / `Box<...>` in a field-type position is a hexa-canon Parse
     error (verified — same `Lt`-token failure as `enum Foo<T>`), so those
     completions score 0 under the real-compile reward and RL must learn to emit
     a *compiling* simplification (`Node(Tree, Tree)`, `Invalid(String)`, or
     unit variants) — exactly the gradient those 6 residual fails need.

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
# Each entry: (name, variants, complexity_tag, generic_params).
#   `generic_params` is the string appended to the name in GENERIC-BAIT
#   prompts, e.g. "<T>" → prompt says `Foo<T>`. The gold is always `enum Foo`
#   (no `<...>`): hexa-canon enum decls take NO type parameters — `enum Foo<T>`
#   is a Parse error (`expected LBrace, got Lt`). Teaching that is the point.
#
# Variants use unit + tuple forms with bare type params (`Some(T)`, `Two(A, B)`)
# — those compile fine (hexa_cc treats unknown type names leniently). NO struct
# variants (`Foo { x: i32 }` — Parse error). The `Vec<...>` / `Box<...>` field
# types in the Validated/Tree specs are eval-faithful bait that DOESN'T compile;
# RL must learn the compiling simplification (see §4 note above).

ENUM_SPECS: list[tuple[str, list[str], str, str]] = [
    # --- non-generic specs (get GENERIC-BAIT with a spurious "<T>" — the model
    #     must learn `Color<T>` in the prompt still means `enum Color { ... }`) ---
    ("Color", ["Red", "Green", "Blue"], "unit", "<T>"),
    ("State", ["Idle", "Running", "Stopped"], "unit", "<T>"),
    ("Mood", ["Happy", "Sad", "Neutral", "Angry"], "unit", "<T>"),
    ("Day", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "unit-large", "<T>"),
    ("Visibility", ["Public", "Private", "Internal"], "unit", "<T>"),
    ("Direction", ["North", "East", "South", "West"], "unit", "<T>"),
    ("Level", ["Low", "Medium", "High", "Critical"], "unit", "<T>"),
    ("Phase", ["Init", "Run", "Cleanup", "Done"], "unit", "<T>"),
    ("Op", ["Add", "Sub", "Mul", "Div", "Neg"], "unit", "<T>"),
    ("HttpMethod", ["Get", "Post", "Put", "Delete", "Patch"], "unit", "<T>"),

    ("Token", ["Ident(String)", "Int(i64)", "Punct(char)", "Eof"], "tuple-mixed", "<T>"),
    ("Lit", ["Bool(bool)", "Int(i64)", "Str(String)"], "tuple", "<T>"),
    ("Number", ["Int(i64)", "Float(f64)"], "tuple", "<T>"),
    ("HttpStatus", ["Code(u16)", "Unknown"], "tuple-and-unit", "<T>"),
    ("Verdict", ["Pass", "Fail(String)"], "tuple-and-unit", "<T>"),
    ("Msg", ["Ping", "Pong", "Data(u32)"], "tuple-and-unit", "<T>"),
    ("ParseResult", ["Ok(i32)", "Err(String)"], "tuple", "<T>"),
    ("Shape", ["Circle(f64)", "Square(f64)", "Rect(f64, f64)"], "tuple-mixed", "<T>"),
    ("Json", ["Null", "Bool(bool)", "Num(f64)", "Str(String)"], "tuple-and-unit", "<T>"),
    ("Event", ["Tick", "Key(char)", "Resize(u32, u32)"], "tuple-and-unit", "<T>"),

    # --- genuinely-generic specs — the eval's generic enum names. The decl gold
    #     is still `enum Foo` (no params). These mirror the eval's variant lists
    #     so the RL gradient hits exactly the residual-fail shapes. The Validated/
    #     Tree variant lists are post-r38-manifest-fix forms (eval normalised
    #     `Invalid(Vec<String>)` → `Invalid(StringList)` and `Node(Box<Tree<T>>,…)`
    #     → `Node(Tree, Tree)` — `Vec<..>`/`Box<..>` field types are hexa-canon
    #     Parse errors, confirmed on hexa_cc). The remaining bait here is the `<T>`
    #     on the *name* (eval has `Validated<T>` etc.) — RL must drop it. -----------
    ("Maybe", ["None", "Some(T)"], "tuple-and-unit-generic", "<T>"),
    ("Option", ["None", "Some(T)"], "tuple-and-unit-generic", "<T>"),         # 4 eval fails — strongest Rust prior
    ("Result", ["Ok(T)", "Err(String)"], "tuple-generic", "<T>"),            # passes in v2; belt-and-suspenders
    ("Either", ["Err(E)", "Ok(T)"], "tuple-generic", "<E, T>"),              # 2-param
    ("Pair", ["Two(A, B)"], "tuple-generic", "<A, B>"),                       # 2-param
    ("Triple", ["Three(A, B, C)"], "tuple-generic", "<A, B, C>"),            # 3-param
    ("Validated", ["Valid(T)", "Invalid(StringList)"], "tuple-generic", "<T>"),  # eval 0065 still decl-generic
    ("Tree", ["Leaf(T)", "Node(Tree, Tree)"], "recursive-generic", "<T>"),       # direct recursion (canon form)

    # --- general "drop nested `<…>` from field types" lesson — names NOT in the
    #     eval, so this teaches the lesson generally rather than eval-fitting. The
    #     `Vec<…>` / `Box<…>` field types don't compile; RL must emit a compiling
    #     simplification (bare type name, or drop the payload). ---------------------
    ("Items", ["Of(Vec<String>)", "Empty"], "vecbait", "<T>"),
    ("Container", ["Holds(Box<i32>)", "Nil"], "boxbait", "<T>"),
]

# Prompt-template paraphrases.
#  (1) NORMAL — eval's "non-generic" prompt wordings. Already mostly pass for v2.
#  (2) GENERIC-BAIT — eval's "generic-form" prompt wordings (`Result<T>`,
#      `Option<T>`, `Pair<A, B>`, ...) that explicitly carry type parameters in
#      the name. The 7B regresses to Rust-style `enum Result<T> { ... }` on
#      these — the exact case RL must unlearn. v2 trained at 67% bait; v3 at
#      ~80% (the residual fails are name-specific generalisation gaps, but more
#      bait + more bait-template variety can't hurt).

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

# Generic-bait templates — `{name}{gp}` carries the type params (e.g. `Foo<T>`,
# `Pair<A, B>`). The gold is still `enum {name}` (no `<...>`): RL must learn to
# strip the type-param hint from the decl head — and, for Vec/Box-bait specs, to
# strip nested `<...>` field types too (those don't compile).
PROMPT_TEMPLATES_GENERIC_BAIT: list[str] = [
    "Declare the hexa enum `{name}{gp}`: `{vlist}`.",
    "Define `{name}{gp}` as a hexa enum — variants: {vlist}.",
    "Write the hexa declaration for a generic enum `{name}{gp}` with these variants: {vlist}.",
    "Produce the hexa enum `{name}{gp}` containing: {vlist}.",
    "Write a hexa enum `{name}{gp}` with variants `{vlist}` ({summary}).",
    "In hexa, declare an enum `{name}{gp}` with the variants {vlist}.",
    "Emit the hexa source for the enum `{name}{gp}` — variants: {vlist}.",
    "Give me the hexa declaration of `{name}{gp}` with constructors: {vlist}.",
]

# v0.4.0-rl-t4-v3: 4 normal + 16 generic-bait = 20 templates → ~80% bait.
PROMPT_TEMPLATES: list[tuple[str, bool]] = (
    [(t, False) for t in PROMPT_TEMPLATES_NORMAL[:4]]
    + [(t, True) for t in PROMPT_TEMPLATES_GENERIC_BAIT * 2]
)


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
    for name, variants, kind, gp in ENUM_SPECS:
        vlist = ", ".join(variants)
        summ = summarize(variants)
        for tmpl, is_bait in PROMPT_TEMPLATES:
            body = tmpl.format(name=name, vlist=vlist, summary=summ, gp=gp if is_bait else "")
            rows.append({
                "prompt": fmt(body),
                "gold_name": name,
                "spec_kind": kind,
                "n_variants": len(variants),
                "bait": is_bait,
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
    n_bait = sum(1 for r in rows if r["bait"])
    print(f"generic-bait: {n_bait}/{len(rows)} = {n_bait/len(rows)*100:.0f}%")
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r["spec_kind"]] = by_kind.get(r["spec_kind"], 0) + 1
    print("by spec_kind:")
    for k in sorted(by_kind):
        print(f"  {k:<26} {by_kind[k]:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
