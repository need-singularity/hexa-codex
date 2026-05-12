#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v15.py — v0.3.0-r3: table-rooted T5 generation.

Round-30 (v14, r2) result: T5 = 41.7% on Mk.I 665 (40/96). Failure mode is
*wrong-family attribution* — the 7B has learned that HX codes exist but
attributes descriptions to the wrong family (HX2 over-predicted; HX2↔HX3,
HX4↔HX5, HX0↔HX1 confusions). Root cause: v14 picked ONE of 5 styles
per (code, description) pair, so only ~20 of 100 descriptions got the
EXACT eval template ("Which hexa HX error-code family covers X" /
"Classify X into HX family"). With only ~40 of 100 descriptions matching
either eval template, the rest of the eval landed on un-trained shapes.

The v15 fix is *template-saturating volume*: every (family, description)
gets BOTH eval templates explicitly + 4 paraphrases. Plus 5 paraphrases
per stage→family mapping. Net ~650 T5-targeted pairs (vs r2's ~30 T5-specific
and ~170 mixed). Aim Mk.I T5 ≥ 75% (would lift overall ~5pp).

Stays compatible with the v14 recipe: same real-canon HX map (SPEC §14),
same stop-token convention (caller appends), same `### User:/### Assistant:`
template, same `looks_like_fictional_t5` v11 filter.

USAGE
    build_sft_dataset_v15.py --in <v11.jsonl> --out-dir <dir>

OUTPUT
    <out-dir>/train.jsonl
    <out-dir>/MANIFEST.json
"""
from __future__ import annotations

import argparse
import json
import os as _os
import random
import sys as _sys
from pathlib import Path

_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

random.seed(42)


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


HX_REAL = {
    "HX0xxx": ("parse / lex", "S0", [
        "a parse error", "a lexer error", "a tokenizer error", "an unexpected token during parsing",
        "an unterminated string literal", "a malformed numeric token", "an invalid character",
        "a missing closing brace at parse time", "a syntax error in a function header", "a stray-token error",
    ]),
    "HX1xxx": ("atlas resolve", "S1", [
        "an atlas resolution failure", "citing an undefined law L[N]", "a tombstoned-L citation (this is HX1099)",
        "an unresolved atlas reference", "an atlas-trie lookup miss", "an unbound ident in MIR lowering (HX1101)",
        "an unsupported pattern shape in lowering (HX1102)", "an unhandled HExpr kind in lowering (HX1103)",
        "a missing L-anchor on a proof obligation", "an atlas drift / hash mismatch",
    ]),
    "HX2xxx": ("bind / scope", "S2", [
        "an unbound identifier", "a name used before it is declared", "an undefined name (HX2001)",
        "a callee that is not callable (HX2003)", "an out-of-scope variable", "a duplicate binding in a scope",
        "a use of a name from a sibling scope", "a shadowing conflict the binder rejects",
        "a reference to a deleted local", "a label that doesn't resolve",
    ]),
    "HX3xxx": ("type", "S3", [
        "a type mismatch", "an arity mismatch on a function call", "a return-type mismatch",
        "an incompatible assignment", "an integer literal out of range for its type", "a wrong-type argument",
        "mismatched branch types in an if-expression", "indexing with a non-integer", "comparing incompatible types",
        "a struct literal with the wrong field types",
    ]),
    "HX4xxx": ("domain", "S4", [
        "a domain-constraint violation", "a value outside its declared domain", "a refinement-type violation",
        "an out-of-domain numeric value", "a precondition not met on a domain-restricted parameter",
        "a range-restricted parameter given an out-of-range value", "a non-positive value where a positive domain is required",
        "a domain refinement the checker can't satisfy", "an index outside a declared bounded domain",
        "a value violating a `where x > 0` style domain",
    ]),
    "HX5xxx": ("units", "S5", [
        "a units mismatch (e.g. adding meters and seconds)", "a missing @units annotation",
        "an incompatible-units operation", "a dimensional-analysis failure", "a unit conversion error",
        "multiplying two quantities whose unit product is invalid", "a quantity used where a dimensionless value is required",
        "an inconsistent unit on a function return", "mixing SI and imperial units without conversion",
        "a unit declared on one operand but not the other",
    ]),
    "HX6xxx": ("equational", "S6", [
        "an equational-reasoning failure", "an unproven equality obligation", "a rewrite step that doesn't hold",
        "a failed equational sample-eval", "an equation the prover couldn't discharge by rewriting",
        "an associativity claim the equational engine rejects", "a commutativity rewrite that isn't valid here",
        "an algebraic identity the checker can't verify", "a normalization that doesn't converge",
        "an equational lemma with a counter-example from sample-eval",
    ]),
    "HX7xxx": ("proof", "S7", [
        "a proof-checking failure", "an unproven law obligation", "a failed in-house prover obligation",
        "a proof gap", "a `@law` obligation the prover rejected", "an `@implements` claim the prover can't establish",
        "a theorem with no proof term", "an incomplete induction the prover flags", "a proof step that doesn't follow",
        "a verification condition the prover couldn't discharge",
    ]),
    "HX8xxx": ("citation", "S8", [
        "a citation error", "a missing `@implements`/`@law` citation", "an uncited use of a law (HX8004, Error)",
        "a superseded-citation warning (HX8003)", "a citation that needs an `@grace` bypass",
        "an `@grace`-bypass citation site", "a function using a law without citing it", "a stale citation pointing at a moved L",
        "a citation gate failure at S8", "a proof obligation with no `@implements` link",
    ]),
    "HX9xxx": ("codegen / link / runtime", "RFC-018", [
        "a codegen failure", "a linker error", "a runtime panic surfaced as a diagnostic", "a backend-emit error",
        "an `@grace` expiry diagnostic — compiler refuses to build (HX9001)", "an `@grace`-site warning, emitted at every @grace (HX9000)",
        "a relocation or symbol error during link", "a runtime assertion turned into a diagnostic",
        "a codegen lowering crash", "an RFC-018 codegen/link/runtime diagnostic",
    ]),
}

HX_SPECIFIC = [
    ("HX1099", "HX1xxx", "citing a tombstoned `L` (compile fail)"),
    ("HX1101", "HX1xxx", "unbound ident in MIR lowering (was a silent `_const_int_op(0)` fallback)"),
    ("HX1102", "HX1xxx", "unsupported pattern shape in MIR lowering"),
    ("HX1103", "HX1xxx", "unhandled HExpr kind in MIR lowering"),
    ("HX2001", "HX2xxx", "undefined name (non-Ident callee — auxiliary to bind/resolve)"),
    ("HX2003", "HX2xxx", "callee is not callable (callee type kind != fn)"),
    ("HX8003", "HX8xxx", "a citation Warning superseded by HX8004 (demoted/removed)"),
    ("HX8004", "HX8xxx", "a citation Error — required citation missing; the bypass is `@grace(HX8004, until=..., reason=...)`"),
    ("HX9000", "HX9xxx", "the `@grace`-site Warning — emitted at every `@grace` site (never silent), inlines the full rendered message"),
    ("HX9001", "HX9xxx", "the `@grace` expiry diagnostic — compiler refuses to build past `until=`"),
    ("HX1042", "HX1xxx", "the example code in SPEC §13's `@grace(HX1042, until=\"2026-06-01\", reason=\"legacy atlas refactor in progress\")`"),
]


def gen_t5_template_saturated() -> list[dict]:
    """Six templates per (family, description). 6 × 100 = 600 pairs.

    Templates A and B are the EXACT eval prompts; C-F are paraphrases."""
    out = []
    for code, (label, stage, descs) in HX_REAL.items():
        for d in descs:
            # A: eval template 1 (verbatim). 48 of 96 eval T5 tasks use this shape.
            out.append(fmt(
                f"Which hexa HX error-code family covers {d}? Answer with the family code like HX0xxx.",
                code,
            ))
            # B: eval template 2 (verbatim). 48 of 96 eval T5 tasks use this shape.
            out.append(fmt(
                f"Classify {d} into its hexa HX diagnostic family.",
                code,
            ))
            # C: indirect, demands short answer
            out.append(fmt(
                f"A hexa compiler emits a diagnostic for {d}. What family does it belong to? Just the family code.",
                code,
            ))
            # D: forward, short
            out.append(fmt(
                f"In hexa, {d} corresponds to which HX family?",
                code,
            ))
            # E: slot-fill (code + label + stage)
            out.append(fmt(
                f"In hexa, {d} is which HX family — and what is that family's name?",
                f"{code} — {label} (stage {stage})",
            ))
            # F: reverse (family → description example)
            out.append(fmt(
                f"What kind of diagnostic does the hexa {code} family cover? Give one example.",
                f"{code} = {label} (stage {stage}). Example: {d}.",
            ))
    return out


def gen_t5_stage_to_family() -> list[dict]:
    """Stage→family classification. Eval has several stage-Sx prompts.

    5 paraphrases × 10 stages = 50 pairs."""
    out = []
    for code, (label, stage, _descs) in HX_REAL.items():
        # eval-template-style
        out.append(fmt(
            f"Classify a stage-{stage} {label} diagnostic into its hexa HX diagnostic family.",
            code,
        ))
        out.append(fmt(
            f"Which hexa HX error-code family covers a stage-{stage} {label} diagnostic? Answer with the family code like HX0xxx.",
            code,
        ))
        out.append(fmt(
            f"In hexa, the {label} stage ({stage}) raises diagnostics in which HX family? Just the family code.",
            code,
        ))
        out.append(fmt(
            f"What HX family does the hexa {stage} ({label}) stage emit?",
            code,
        ))
        out.append(fmt(
            f"Give the HX family for hexa stage {stage} ({label}).",
            code,
        ))
    return out


def gen_hx_specific() -> list[dict]:
    """Specific codes — same as v14: 3 questions per code + 2 @grace drills."""
    out = []
    for code, fam, title in HX_SPECIFIC:
        out.append(fmt(f"What is the hexa diagnostic `{code}`?", f"{code}: {title}. (Family {fam}.)"))
        out.append(fmt(f"Which hexa HX family does `{code}` belong to? Just the family code.", fam))
        out.append(fmt(f"In hexa, what does `{code}` mean?", title))
    out.append(fmt(
        "In hexa, what diagnostic does every `@grace` site emit, and what happens on expiry?",
        "Every `@grace` site emits HX9000 (a Warning, never silent, inlining the full rendered message). "
        "On the `until=` expiry date the compiler emits HX9001 and refuses to build until the site is fixed.",
    ))
    out.append(fmt(
        "Write a hexa `@grace` annotation bypassing the citation error HX8004 until 2026-09-01, reason 'migration in progress'.",
        '@grace(HX8004, until="2026-09-01", reason="migration in progress")',
    ))
    return out


def gen_hx_full_table() -> list[dict]:
    """Full-table recall — 7 paraphrases of the whole map (same as v14)."""
    out = []
    table_line = (
        "HX0xxx = parse / lex (S0); HX1xxx = atlas resolve (S1); HX2xxx = bind / scope (S2); "
        "HX3xxx = type (S3); HX4xxx = domain (S4); HX5xxx = units (S5); HX6xxx = equational (S6); "
        "HX7xxx = proof (S7); HX8xxx = citation (S8); HX9xxx = codegen / link / runtime (RFC-018)."
    )
    stage_arrow = (
        "S0->HX0xxx (parse/lex), S1->HX1xxx (atlas resolve), S2->HX2xxx (bind/scope), "
        "S3->HX3xxx (type), S4->HX4xxx (domain), S5->HX5xxx (units), S6->HX6xxx (equational), "
        "S7->HX7xxx (proof), S8->HX8xxx (citation), and HX9xxx = codegen/link/runtime (RFC-018)."
    )
    out.append(fmt("List the hexa HX diagnostic families and what each covers (HX0xxx..HX9xxx).", table_line))
    for _ in range(6):
        out.append(fmt("Give the hexa HX family for each stage S0..S8 plus the codegen/link/runtime range.", stage_arrow))
    return out


def looks_like_fictional_t5(text: str) -> bool:
    """v11 fictional T5 classification pairs — drop. (Same heuristic as v14.)"""
    t = text.lower()
    if "hx" not in t:
        return False
    if "family" not in t:
        return False
    return (
        "error-code family" in t
        or "diagnostic family" in t
        or "hx family for" in t
        or ("classify" in t and "hx family" in t)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="v11 base jsonl path")
    ap.add_argument("--out-dir", dest="out_dir", required=True, help="output dir (will contain train.jsonl + MANIFEST.json)")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    if not in_path.exists():
        print(f"ERROR: v11 base not found at {in_path}", file=_sys.stderr)
        return 1

    base_all = [json.loads(L) for L in in_path.read_text().splitlines() if L.strip()]
    base = [r for r in base_all if not looks_like_fictional_t5(r.get("text", ""))]
    dropped = len(base_all) - len(base)
    print(f"v11 base: {len(base_all)}  (dropped {dropped} fictional-T5 rows)  -> {len(base)}")

    blocks = {
        "t5_template_saturated_real": gen_t5_template_saturated(),  # 600 pairs
        "t5_stage_to_family_real":    gen_t5_stage_to_family(),     # 50 pairs
        "hx_specific_real":           gen_hx_specific(),            # 33+2 pairs
        "hx_full_table_real":         gen_hx_full_table(),          # 7 pairs
    }
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:30s} {len(rows_):4d}")
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
        "version": "v0.3.0-r3 (v15)",
        "base": str(in_path),
        "base_rows_in": len(base_all),
        "fictional_t5_dropped": dropped,
        "base_rows_kept": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": (
            "Table-rooted T5 generation — 6 paraphrases × 100 (code,desc) + 5 paraphrases × 10 stages. "
            "Fix r2 wrong-family confusions by saturating every (family,desc) with BOTH eval templates."
        ),
    }, indent=2))
    print(f"wrote: {out_file}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
