#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v14.py — v0.3.0-r2: fix the T5 fiction with REAL canon HX codes.

Round-29 root cause for T5 stuck at ~25-29%: the Mk.0.1/Mk.I T5 tasks AND the SFT T5
pairs (r9-r13) used a *fictional* HX-code family map (HX0=parse, HX1=names, HX2=types,
HX3=ownership, HX4=traits, HX5=linker, HX6=lint, HX7=codegen, HX8=FFI, HX9=deprecation).
The REAL map (hexa-lang/SPEC.md §14) is:
    HX0xxx = parse / lex (S0)        HX5xxx = units (S5)
    HX1xxx = atlas resolve (S1)      HX6xxx = equational (S6)
    HX2xxx = bind / scope (S2)       HX7xxx = proof (S7)
    HX3xxx = type (S3)               HX8xxx = citation (S8)
    HX4xxx = domain (S4)             HX9xxx = codegen / link / runtime (RFC-018)
plus specific codes: HX1099 (citing tombstoned L), HX1101/1102/1103 (lower errors at S2),
HX2001 (undefined name), HX2003 (callee not callable), HX8003 (superseded citation, Warn),
HX8004 (uncited use, Error), HX9000 (@grace-site warning — every @grace site emits it),
HX9001 (@grace expiry — compiler refuses to build).

`tool/gen_hexa_eval_mk1.py` has been corrected to use the REAL map; this builder makes
the SFT match it.

v14 = (v11 base with the fictional T5-classification pairs DROPPED) + ~220 real-canon HX
Q/A pairs. ~2,640 rows.

OUTPUT
    /home/summer/runs/sft-train-v14/train.jsonl
    /home/summer/runs/sft-train-v14/MANIFEST.json
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
import random
from pathlib import Path

random.seed(42)

V11_BASE = Path("/home/summer/runs/sft-train-v11/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v14")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# --- the REAL canon HX-code map ---------------------------------------------
HX_REAL = {
    "HX0xxx": ("parse / lex", "stage S0", [
        "a parse error", "a lexer error", "a tokenizer error", "an unexpected token during parsing",
        "an unterminated string literal", "a malformed numeric token", "an invalid character",
        "a missing closing brace at parse time", "a syntax error in a function header", "a stray-token error",
    ]),
    "HX1xxx": ("atlas resolve", "stage S1", [
        "an atlas resolution failure", "citing an undefined law L[N]", "a tombstoned-L citation (this is HX1099)",
        "an unresolved atlas reference", "an atlas-trie lookup miss", "an unbound ident in MIR lowering (HX1101)",
        "an unsupported pattern shape in lowering (HX1102)", "an unhandled HExpr kind in lowering (HX1103)",
        "a missing L-anchor on a proof obligation", "an atlas drift / hash mismatch",
    ]),
    "HX2xxx": ("bind / scope", "stage S2", [
        "an unbound identifier", "a name used before it is declared", "an undefined name (HX2001)",
        "a callee that is not callable (HX2003)", "an out-of-scope variable", "a duplicate binding in a scope",
        "a use of a name from a sibling scope", "a shadowing conflict the binder rejects",
        "a reference to a deleted local", "a label that doesn't resolve",
    ]),
    "HX3xxx": ("type", "stage S3", [
        "a type mismatch", "an arity mismatch on a function call", "a return-type mismatch",
        "an incompatible assignment", "an integer literal out of range for its type", "a wrong-type argument",
        "mismatched branch types in an if-expression", "indexing with a non-integer", "comparing incompatible types",
        "a struct literal with the wrong field types",
    ]),
    "HX4xxx": ("domain", "stage S4", [
        "a domain-constraint violation", "a value outside its declared domain", "a refinement-type violation",
        "an out-of-domain numeric value", "a precondition not met on a domain-restricted parameter",
        "a range-restricted parameter given an out-of-range value", "a non-positive value where a positive domain is required",
        "a domain refinement the checker can't satisfy", "an index outside a declared bounded domain",
        "a value violating a `where x > 0` style domain",
    ]),
    "HX5xxx": ("units", "stage S5", [
        "a units mismatch (e.g. adding meters and seconds)", "a missing @units annotation",
        "an incompatible-units operation", "a dimensional-analysis failure", "a unit conversion error",
        "multiplying two quantities whose unit product is invalid", "a quantity used where a dimensionless value is required",
        "an inconsistent unit on a function return", "mixing SI and imperial units without conversion",
        "a unit declared on one operand but not the other",
    ]),
    "HX6xxx": ("equational", "stage S6", [
        "an equational-reasoning failure", "an unproven equality obligation", "a rewrite step that doesn't hold",
        "a failed equational sample-eval", "an equation the prover couldn't discharge by rewriting",
        "an associativity claim the equational engine rejects", "a commutativity rewrite that isn't valid here",
        "an algebraic identity the checker can't verify", "a normalization that doesn't converge",
        "an equational lemma with a counter-example from sample-eval",
    ]),
    "HX7xxx": ("proof", "stage S7", [
        "a proof-checking failure", "an unproven law obligation", "a failed in-house prover obligation",
        "a proof gap", "a `@law` obligation the prover rejected", "an `@implements` claim the prover can't establish",
        "a theorem with no proof term", "an incomplete induction the prover flags", "a proof step that doesn't follow",
        "a verification condition the prover couldn't discharge",
    ]),
    "HX8xxx": ("citation", "stage S8", [
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

# --- specific codes (title from SPEC §14.1 + the @grace/citation/atlas mentions) ---
HX_SPECIFIC = [
    ("HX1099", "HX1xxx", "citing a tombstoned `L` (compile fail)"),
    ("HX1101", "HX1xxx", "unbound ident in MIR lowering (was a silent `_const_int_op(0)` fallback)"),
    ("HX1102", "HX1xxx", "unsupported pattern shape in MIR lowering"),
    ("HX1103", "HX1xxx", "unhandled HExpr kind in MIR lowering"),
    ("HX2001", "HX2xxx", "undefined name (non-Ident callee — auxiliary to bind/resolve)"),
    ("HX2003", "HX2xxx", "callee is not callable (callee type kind != fn)"),
    ("HX8003", "HX8xxx", "a citation Warning that is superseded by HX8004 (and demoted/removed)"),
    ("HX8004", "HX8xxx", "a citation Error — required citation missing; standard `@grace(HX8004, until=..., reason=...)` is the bypass"),
    ("HX9000", "HX9xxx", "the `@grace`-site Warning — emitted at every `@grace` site (never silent), inlines the full rendered message"),
    ("HX9001", "HX9xxx", "the `@grace` expiry diagnostic — on expiry the compiler emits it and refuses to build"),
    ("HX1042", "HX1xxx", "the example code in SPEC §13's `@grace(HX1042, until=\"2026-06-01\", reason=\"legacy atlas refactor in progress\")`"),
]


def gen_hx_family(n=170) -> list[dict]:
    pool = []
    for code, (label, stage, descs) in HX_REAL.items():
        for d in descs:
            pool.append((code, label, stage, d))
    random.shuffle(pool)
    out = []
    for code, label, stage, d in pool[:n]:
        style = random.randint(0, 4)
        if style == 0:
            p = f"Which hexa HX error-code family covers {d}? Answer with just the family code like HX0xxx."
            c = code
        elif style == 1:
            p = f"Classify {d} into its hexa HX diagnostic family. Answer with only the family code."
            c = code
        elif style == 2:
            p = f"A hexa compiler emits a diagnostic for {d}. What family does it belong to? Just the code."
            c = code
        elif style == 3:
            p = f"In hexa, {d} is which HX family — and what is that family's name?"
            c = f"{code} — {label} ({stage})"
        else:
            p = f"What does the hexa {code} diagnostic family cover?"
            c = f"{code} = {label} ({stage}). Example: {d}."
        out.append(fmt(p, c))
    # also: full-table recall pairs
    out.append(fmt("List the hexa HX diagnostic families and what each covers (HX0xxx..HX9xxx).",
                   "HX0xxx = parse / lex (S0); HX1xxx = atlas resolve (S1); HX2xxx = bind / scope (S2); "
                   "HX3xxx = type (S3); HX4xxx = domain (S4); HX5xxx = units (S5); HX6xxx = equational (S6); "
                   "HX7xxx = proof (S7); HX8xxx = citation (S8); HX9xxx = codegen / link / runtime (RFC-018)."))
    for _ in range(6):
        out.append(fmt("Give the hexa HX family for each stage S0..S8 plus the codegen/link/runtime range.",
                       "S0->HX0xxx (parse/lex), S1->HX1xxx (atlas resolve), S2->HX2xxx (bind/scope), "
                       "S3->HX3xxx (type), S4->HX4xxx (domain), S5->HX5xxx (units), S6->HX6xxx (equational), "
                       "S7->HX7xxx (proof), S8->HX8xxx (citation), and HX9xxx = codegen/link/runtime (RFC-018)."))
    return out


def gen_hx_specific() -> list[dict]:
    out = []
    for code, fam, title in HX_SPECIFIC:
        out.append(fmt(f"What is the hexa diagnostic `{code}`?", f"{code}: {title}. (Family {fam}.)"))
        out.append(fmt(f"Which hexa HX family does `{code}` belong to? Just the family code.", fam))
        out.append(fmt(f"In hexa, what does `{code}` mean?", title))
    # a couple of @grace-specific drills
    out.append(fmt("In hexa, what diagnostic does every `@grace` site emit, and what happens on expiry?",
                   "Every `@grace` site emits HX9000 (a Warning, never silent, inlining the full rendered message). "
                   "On the `until=` expiry date the compiler emits HX9001 and refuses to build until the site is fixed."))
    out.append(fmt("Write a hexa `@grace` annotation bypassing the citation error HX8004 until 2026-09-01, reason 'migration in progress'.",
                   '@grace(HX8004, until="2026-09-01", reason="migration in progress")'))
    return out


def looks_like_fictional_t5(text: str) -> bool:
    """v11 base rows that are the OLD fictional 'which HX family covers X' pairs.

    Keep @grace(HX...) pairs (T3, fine) and atlas pairs; drop the classification ones.
    Heuristic: mentions an HX code AND the word 'family' AND is a classification prompt.
    """
    t = text.lower()
    if "hx" not in t:
        return False
    if "family" not in t:
        return False
    # @grace classification ("which family does HX9001 belong to") is fine to keep;
    # but the bulk fictional ones say "covers a <made-up error>" — drop those.
    return ("error-code family" in t or "diagnostic family" in t or "hx family for" in t
            or ("classify" in t and "hx family" in t))


def main() -> int:
    if not V11_BASE.exists():
        print(f"ERROR: v11 base not found at {V11_BASE}", file=_sys.stderr)
        return 1
    base_all = [json.loads(l) for l in V11_BASE.read_text().splitlines() if l.strip()]
    base = [r for r in base_all if not looks_like_fictional_t5(r.get("text", ""))]
    dropped = len(base_all) - len(base)
    print(f"v11 base: {len(base_all)}  (dropped {dropped} fictional-T5 rows)  -> {len(base)}")
    blocks = {"hx_family_real": gen_hx_family(170), "hx_specific_real": gen_hx_specific()}
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:18s} {len(rows_):4d}")
        added.extend(rows_)
    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.3.0-r2",
        "base": str(V11_BASE),
        "base_rows_in": len(base_all),
        "fictional_t5_dropped": dropped,
        "base_rows_kept": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": "REAL canon HX-code map (hexa-lang/SPEC.md §14) replacing the fictional one in r9-r13; gen_hexa_eval_mk1.py T5 corrected to match",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
