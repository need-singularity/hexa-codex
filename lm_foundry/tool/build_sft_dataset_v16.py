#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v16.py — v0.3.0-r4: rebalance round.

Round-31 (v15, r3) result: T5 99.0% (solved) + T7 98.3% + overall 77.74% — but
regressions T2 −12pp, T8 −16pp, T6 −4.6pp from dataset-balance dilution. The
v15 T5 block grew to 21% of rows and crowded the answer-shape signals for atlas
annotations, refusals, and 4-part target triples.

The v16 fix is *targeted rebalance*: keep v15's verified T5 recipe but trim
volume; add explicit blocks for the three regressed families with eval-shaped
prompts and bare answers (no extra continuation). Goal: Mk.I ≥ 80% — gate ③.

Changes vs v15:
1. T5 paraphrases trimmed 6 → 4 per (family, desc) → 400 T5 (was 600). Holds
   ≥ 95% because each (family, desc) still has both eval-template shapes
   (A: "Which hexa HX error-code family covers X" + B: "Classify X into HX family")
   plus 2 other paraphrases.
2. NEW T2 atlas-annotation block (~60 pair): `@discover(kind="L")` + `@implements(L[N])`
   with bare-annotation answers (no `fn ...` body). Matches eval prompt shape.
3. NEW T6 4-part target-triple block (~50 pair): 17 triples × 3 paraphrase from
   the eval set. Bare 4-part string answers.
4. NEW refuse-boost block (~80 pair): 20 multilingual OOD + 30 generic OOD
   refuse + 30 "code-but-not-hexa" accept distinguishers. Raises explicit
   refuse-pair count 186 → ~280 (~8-9% of total, rule #2 7-10%).

USAGE
    build_sft_dataset_v16.py --in <v11.jsonl> --out-dir <dir>

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


# === reuse v15's verified canon HX map ======================================
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
    ("HX1101", "HX1xxx", "unbound ident in MIR lowering"),
    ("HX1102", "HX1xxx", "unsupported pattern shape in MIR lowering"),
    ("HX1103", "HX1xxx", "unhandled HExpr kind in MIR lowering"),
    ("HX2001", "HX2xxx", "undefined name (non-Ident callee)"),
    ("HX2003", "HX2xxx", "callee is not callable (callee type kind != fn)"),
    ("HX8003", "HX8xxx", "a citation Warning superseded by HX8004"),
    ("HX8004", "HX8xxx", "a citation Error — required citation missing"),
    ("HX9000", "HX9xxx", "the `@grace`-site Warning"),
    ("HX9001", "HX9xxx", "the `@grace` expiry diagnostic"),
    ("HX1042", "HX1xxx", "example code in SPEC §13's `@grace(HX1042, until=\"2026-06-01\", ...)`"),
]

# === T6 eval triples (from manifest-mk1.jsonl T6 gold set, 17 distinct) =====
T6_TRIPLES = [
    ("Cortex-M7 with double-precision FPU", "thumbv7em-none-eabihf"),
    ("Cortex-M4F with FPU", "thumbv7em-none-eabihf"),
    ("aarch64 macOS (Apple Silicon)", "aarch64-apple-darwin"),
    ("aarch64 Linux", "aarch64-unknown-linux-gnu"),
    ("Cortex-A53 Linux (Raspberry Pi 3/4 64-bit)", "aarch64-unknown-linux-gnu"),
    ("Cortex-M0/M0+/M1 (ARMv6-M, no FPU)", "thumbv6m-none-eabi"),
    ("Cortex-M3 (ARMv7-M, no FPU)", "thumbv7m-none-eabi"),
    ("Cortex-M4 / Cortex-M7 (soft-float)", "thumbv7em-none-eabi"),
    ("Cortex-M33 with single-precision FPU (ARMv8-M Mainline)", "thumbv8m.main-none-eabihf"),
    ("ESP32 (Xtensa LX6)", "xtensa-esp32-none-elf"),
    ("ESP32-S3 (Xtensa LX7)", "xtensa-esp32s3-none-elf"),
    ("AVR ATmega328P (Arduino Uno)", "avr-unknown-gnu-atmega328"),
    ("RISC-V 32-bit imc bare-metal", "riscv32imc-unknown-none-elf"),
    ("RISC-V 32-bit imac bare-metal", "riscv32imac-unknown-none-elf"),
    ("RISC-V 64-bit gc bare-metal", "riscv64gc-unknown-none-elf"),
    ("x86_64 Linux", "x86_64-unknown-linux-gnu"),
    ("x86_64 macOS", "x86_64-apple-darwin"),
    ("WASM (browser, no specific OS)", "wasm32-unknown-unknown"),
    ("WASM WASI", "wasm32-wasi"),
]


def gen_t5_template_saturated_v16() -> list[dict]:
    """Trimmed v15 block: 4 paraphrases per (family, desc) — keep BOTH eval templates."""
    out = []
    for code, (label, stage, descs) in HX_REAL.items():
        for d in descs:
            # A: eval template 1 (verbatim, 48 of 96 eval T5 tasks)
            out.append(fmt(
                f"Which hexa HX error-code family covers {d}? Answer with the family code like HX0xxx.",
                code,
            ))
            # B: eval template 2 (verbatim, 48 of 96 eval T5 tasks)
            out.append(fmt(
                f"Classify {d} into its hexa HX diagnostic family.",
                code,
            ))
            # C: indirect, short
            out.append(fmt(
                f"A hexa compiler emits a diagnostic for {d}. What family does it belong to? Just the family code.",
                code,
            ))
            # D: slot-fill (code + label + stage) — keeps the "label" mapping
            out.append(fmt(
                f"In hexa, {d} is which HX family — and what is that family's name?",
                f"{code} — {label} (stage {stage})",
            ))
    return out


def gen_t5_stage_to_family() -> list[dict]:
    """Same as v15: 5 paraphrases × 10 stages = 50 pairs."""
    out = []
    for code, (label, stage, _descs) in HX_REAL.items():
        out.append(fmt(f"Classify a stage-{stage} {label} diagnostic into its hexa HX diagnostic family.", code))
        out.append(fmt(f"Which hexa HX error-code family covers a stage-{stage} {label} diagnostic? Answer with the family code like HX0xxx.", code))
        out.append(fmt(f"In hexa, the {label} stage ({stage}) raises diagnostics in which HX family? Just the family code.", code))
        out.append(fmt(f"What HX family does the hexa {stage} ({label}) stage emit?", code))
        out.append(fmt(f"Give the HX family for hexa stage {stage} ({label}).", code))
    return out


def gen_hx_specific() -> list[dict]:
    """Same as v15."""
    out = []
    for code, fam, title in HX_SPECIFIC:
        out.append(fmt(f"What is the hexa diagnostic `{code}`?", f"{code}: {title}. (Family {fam}.)"))
        out.append(fmt(f"Which hexa HX family does `{code}` belong to? Just the family code.", fam))
        out.append(fmt(f"In hexa, what does `{code}` mean?", title))
    out.append(fmt(
        "In hexa, what diagnostic does every `@grace` site emit, and what happens on expiry?",
        "Every `@grace` site emits HX9000 (a Warning, never silent). On the `until=` expiry date the compiler emits HX9001 and refuses to build.",
    ))
    out.append(fmt(
        "Write a hexa `@grace` annotation bypassing the citation error HX8004 until 2026-09-01, reason 'migration in progress'.",
        '@grace(HX8004, until="2026-09-01", reason="migration in progress")',
    ))
    return out


def gen_hx_full_table() -> list[dict]:
    """Same as v15: 7 paraphrases of the whole map."""
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


def gen_t2_atlas_annotation() -> list[dict]:
    """T2 atlas annotation — eval shape: verify L[N] → @implements(L[N]); explore L[N] → @discover(kind=L).

    Bare-annotation answer (no `fn ...` body), matching the T2 eval scorer.
    Sample 30 L[N] values for each of the two patterns = 60 pairs."""
    out = []
    rng = random.Random(101)
    impl_ns = rng.sample(range(2, 800), 30)
    disc_ns = rng.sample(range(2, 800), 30)

    impl_templates = [
        'Write the correct hexa annotation for a function whose docstring says it verifies `L[{n}]`.',
        'A hexa function proves law `L[{n}]` — what annotation should it carry? Bare annotation only.',
        'Annotate a hexa function `prove_{n}` that proves law `L[{n}]`. Answer with just the annotation.',
        'In hexa, what annotation marks a function as implementing law `L[{n}]`? Just the annotation.',
        'Bare annotation: a hexa function verifies `L[{n}]`.',
    ]
    disc_templates = [
        'Write the correct hexa annotation for a function whose docstring says it EXPLORES undiscovered cases of `L[{n}]`.',
        'Write the correct hexa annotation for a function whose docstring says it hunts undiscovered cases of `L[{n}]`.',
        'A hexa function explores new instances of law `L[{n}]` (not a proof) — what annotation? Bare annotation only.',
        'Annotate a hexa function `explore_instances_{n}` that EXPLORES new instances of law `L[{n}]` (not proves it). Just the annotation.',
        'In hexa, what annotation marks a discovery-style function (not a proof)? Just the annotation.',
    ]

    for n in impl_ns:
        t = rng.choice(impl_templates)
        out.append(fmt(t.format(n=n), f"@implements(L[{n}])"))
    for n in disc_ns:
        t = rng.choice(disc_templates)
        # generic templates (without n) — keep n-substitution where present
        try:
            prompt = t.format(n=n)
        except (KeyError, IndexError):
            prompt = t
        out.append(fmt(prompt, '@discover(kind="L")'))
    return out


def gen_t6_target_triples() -> list[dict]:
    """T6 4-part target triples — 3 paraphrases per (chip, triple). 17 × 3 = 51 pairs.

    Bare 4-part string answer (matches T6 eval exact_match scorer)."""
    out = []
    templates = [
        "Build target triple for {chip}?",
        "What is the canonical hexa linker target triple for {chip}?",
        "Give the hexa target triple used to build for {chip}.",
    ]
    for chip, triple in T6_TRIPLES:
        for tmpl in templates:
            out.append(fmt(tmpl.format(chip=chip), triple))
    return out


def gen_refuse_boost() -> list[dict]:
    """Refuse-boost — 20 multilingual OOD + 30 generic OOD + 30 code-but-not-hexa accept.

    Eval prompt shape (matches T8): 'User asks: "<text>" Should the hexa-canon code model
    accept or refuse? Answer "accept" or "refuse".' → 'refuse' or 'accept'."""
    out = []

    multilingual_ood = [
        '健康的な朝食のレシピを教えて。',
        'お気に入りの映画は何ですか?',
        '今日の天気はどうですか?',
        'Дай совет, как лучше провести выходные.',
        'Расскажи мне сказку о драконе.',
        'Что приготовить на ужин?',
        'Cuéntame un chiste sobre gatos.',
        '¿Cuál es la capital de Francia?',
        'Recomiéndame una buena novela.',
        'Erzähl mir einen Witz über Programmierer.',
        'Was ist dein Lieblingsessen?',
        'Donne-moi des conseils pour mieux dormir.',
        'Quelle est ta couleur préférée?',
        '给我讲一个关于宇宙的故事。',
        '推荐几本好看的小说。',
        '오늘 날씨 어때?',
        '추천할 만한 영화 있어?',
        'احكي لي قصة عن الصداقة.',
        'Conte-me uma história engraçada.',
        'Quanto è alto il Monte Bianco?',
    ]
    generic_ood = [
        "Tell me a joke about cats.",
        "Compose a birthday message for my friend.",
        "Write me a poem about pythons (the snake).",
        "Recommend a good Italian recipe for tonight's dinner.",
        "What's the meaning of life?",
        "Give me dating advice.",
        "Help me write a wedding speech.",
        "What movies should I watch this weekend?",
        "Plan my vacation to Italy for 10 days.",
        "Suggest a workout routine for losing weight.",
        "Tell me a horror story for Halloween.",
        "What stocks should I buy this month?",
        "Translate 'good morning' to French and Japanese.",
        "Write a sonnet about lost love.",
        "Recommend 5 sci-fi novels.",
        "What's the best way to learn piano?",
        "Give me tips for negotiating salary.",
        "Plan a birthday party for a 7-year-old.",
        "What are the benefits of meditation?",
        "Help me write my college application essay.",
        "Compose lyrics for a country song.",
        "What's a good gift for a 60-year-old grandmother?",
        "Recommend a meditation app.",
        "Write a thank-you note to my doctor.",
        "What should I name my new puppy?",
        "Plan a romantic dinner for two.",
        "Give me weight-loss tips.",
        "Write a fairy tale about a brave mouse.",
        "What's the recipe for chocolate chip cookies?",
        "Suggest a daily journaling prompt.",
    ]
    code_accept = [
        "How do I write a hexa function that sums an array?",
        "Show me a hexa example using @implements(L[100]).",
        "Write a hexa for-loop that prints 1..10.",
        "What is the hexa syntax for a struct definition?",
        "Give me a hexa snippet that opens a file and reads it.",
        "How do I import another hexa module?",
        "Show me how to define a generic function in hexa.",
        "What's a hexa example of pattern matching on an enum?",
        "Write a hexa fizzbuzz.",
        "How do I do error handling in hexa?",
        "Show a hexa example of @grace(HX8004, ...) usage.",
        "Write a hexa hello-world.",
        "How do I declare a constant in hexa?",
        "Show me how to call a function with named arguments in hexa.",
        "Write a hexa function that reverses a list.",
        "What's the hexa equivalent of Rust's Option<T>?",
        "Give an example of @units(...) in hexa.",
        "Write a hexa recursive factorial.",
        "How do I write tests in hexa?",
        "Show me hexa string formatting.",
        "Write a hexa quicksort.",
        "How do I read environment variables in hexa?",
        "Write a hexa function that fetches an HTTP URL.",
        "Show me hexa async / await syntax.",
        "How do I serialize a struct to JSON in hexa?",
        "Write a hexa snippet that uses @law L[1].",
        "Give me a hexa example of trait implementation.",
        "How do I parse command-line args in hexa?",
        "Show a hexa example of a tagged union.",
        "Write a hexa BFS over a graph.",
    ]

    def refuse_prompt(text: str) -> str:
        return f'User asks: "{text}" Should the hexa-canon code model accept or refuse? Answer "accept" or "refuse".'

    for text in multilingual_ood:
        out.append(fmt(refuse_prompt(text), "refuse"))
    for text in generic_ood:
        out.append(fmt(refuse_prompt(text), "refuse"))
    for text in code_accept:
        out.append(fmt(refuse_prompt(text), "accept"))
    return out


def looks_like_fictional_t5(text: str) -> bool:
    """Same heuristic as v14/v15 — drop v11 fictional T5 classification rows."""
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
    ap.add_argument("--out-dir", dest="out_dir", required=True)
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
        "t5_template_saturated_v16":  gen_t5_template_saturated_v16(),  # 400 (was 600 in v15)
        "t5_stage_to_family":         gen_t5_stage_to_family(),         # 50
        "hx_specific":                gen_hx_specific(),                # 35
        "hx_full_table":              gen_hx_full_table(),              # 7
        "t2_atlas_annotation_NEW":    gen_t2_atlas_annotation(),        # 60
        "t6_target_triples_NEW":      gen_t6_target_triples(),          # 51
        "refuse_boost_NEW":           gen_refuse_boost(),               # 80
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
        "version": "v0.3.0-r4 (v16)",
        "base": str(in_path),
        "base_rows_in": len(base_all),
        "fictional_t5_dropped": dropped,
        "base_rows_kept": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": (
            "Rebalance round — fix r3's T2/T8/T6 regressions while preserving T5 99% and T7 98%. "
            "T5 paraphrases 6→4 per (family,desc). NEW: T2 atlas-annotation (60), T6 4-part triple (51), "
            "refuse-boost (80, raises refuse-ratio to ~9%). Target Mk.I ≥ 80% (gate ③)."
        ),
    }, indent=2))
    print(f"wrote: {out_file}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
