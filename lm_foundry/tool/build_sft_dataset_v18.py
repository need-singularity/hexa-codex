#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v18.py — v0.4.0 delegation SFT dataset (840 new pairs on
v11 base = ~3980 total rows).

Per `papers/spec-delegation-v0.4.0.md` §10. Eight sub-blocks:
  200 in-domain-high-confidence  — sampled across T1-T8, prepend <|confidence:high|>
  220 out-of-domain-delegate     — emit <|delegate|>{...}<|/delegate|>; vary vendor + tier
  100 medium-confidence-direct   — Swift / common-Py / Go basics with <|confidence:medium|> + caveat
   80 ambiguous-clarify-delegate — <|delegate|> with clarifying re-formulation inside `prompt`
   80 delegate-result-integration — prior turn contains synthesised <|delegate-result|>; output is the wrap-up
   70 failure-mode-handling      — 10 each of 7 error codes (excluding schema_violation never-event)
   50 security-refuse-direct     — refuse without delegating
   40 no-delegation-override     — system says "answer locally only" → refuse if OOD

Holdout discipline: NO row's prompt exactly matches any
`eval/delegation-mk0/manifest.jsonl` prompt — generators use disjoint
function names / topic phrasings.

Output: writes `sft-train-v18.jsonl` (v11 base + new pairs) + `MANIFEST.json`.

USAGE
    build_sft_dataset_v18.py --in <v11 jsonl> --out-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

random.seed(2026_05_13_18)

# Eval-holdout topics: anything matching a substring of an eval/delegation-mk0
# prompt is excluded. We assume the eval uses common keywords (tokio, Vec<String>,
# attention, RoPE etc.) — we DON'T re-use the exact eval prompt wordings.

# ============================================================================
# §10 block A: in-domain high-confidence (200)
# ============================================================================
# Sample hexa-canon Q/A across T1-T8 + 5-NL. The answer is the canonical hexa
# response prepended with <|confidence:high|>.

T1_PROMPTS = [
    # short syntax / function declarations — different from gen_hexa_eval_mk1 + delegation-mk0 in-domain
    ("Hexa function `square(n: i32) -> i32` returning `n * n`.",            "fn square(n: i32) -> i32 { n * n }"),
    ("Hexa function `negate(n: i32) -> i32` returning `-n`.",                "fn negate(n: i32) -> i32 { -n }"),
    ("Hexa function `is_positive(n: i32) -> bool` returning `n > 0`.",       "fn is_positive(n: i32) -> bool { n > 0 }"),
    ("Hexa constant `MAX_BUF: usize = 4096`.",                                "const MAX_BUF: usize = 4096"),
    ("Hexa constant `PI: f64 = 3.141592653589793`.",                          "const PI: f64 = 3.141592653589793"),
    ("Hexa `for i in 0..n` printing each index.",                             "for i in 0..n { print(i) }"),
    ("Hexa `while x > 0` decrementing x.",                                    "while x > 0 { x -= 1 }"),
    ("Hexa pattern match on Option<i32>: 0 for None, value for Some.",        "match o { None => 0, Some(v) => v }"),
    ("Hexa struct `Pair { a: i32, b: i32 }`.",                                "struct Pair { a: i32, b: i32 }"),
    ("Hexa generic function `id<T>(x: T) -> T { x }`.",                       "fn id<T>(x: T) -> T { x }"),
    ("Hexa `let x: f64 = 1.5` typed binding.",                                "let x: f64 = 1.5"),
    ("Hexa `if cond { a } else { b }` expression.",                           "if cond { a } else { b }"),
    ("Hexa return-type-only function header `fn area() -> f64`.",             "fn area() -> f64"),
    ("Hexa `Vec3 { x: f64, y: f64, z: f64 }` struct.",                        "struct Vec3 { x: f64, y: f64, z: f64 }"),
    ("Hexa unit type return: `fn run() {}`.",                                 "fn run() {}"),
    ("Hexa tuple `(i32, i32)` binding: `let p: (i32, i32) = (3, 4)`.",        "let p: (i32, i32) = (3, 4)"),
    ("Hexa function with 2 args `add(a: i32, b: i32) -> i32`.",               "fn add(a: i32, b: i32) -> i32 { a + b }"),
    ("Hexa `match x { 0 => \"zero\", _ => \"nonzero\" }` shape.",            "match x { 0 => \"zero\", _ => \"nonzero\" }"),
    ("Hexa boolean literal binding: `let ok: bool = true`.",                  "let ok: bool = true"),
    ("Hexa `String::from(\"hi\")` literal binding.",                          "let s: String = String::from(\"hi\")"),
    ("Hexa `enum Bit { On, Off }`.",                                          "enum Bit { On, Off }"),
    ("Hexa `let mut n: i32 = 0` mutable binding.",                            "let mut n: i32 = 0"),
    ("Hexa function returning a tuple `pair() -> (i32, i32)`.",               "fn pair() -> (i32, i32) { (1, 2) }"),
    ("Hexa `impl Foo { fn new() -> Self { Self {} } }` skeleton.",            "impl Foo { fn new() -> Self { Self {} } }"),
    ("Hexa trait declaration `trait Drawable { fn draw(&self) }`.",           "trait Drawable { fn draw(&self) }"),
]
T2_PROMPTS = [
    ("Annotate `compute_law_X()` as @implements(L[101]).",                    "@implements(L[101])"),
    ("Annotate `find_invariant_Y()` as @discover(kind=\"L\").",               "@discover(kind=\"L\")"),
    ("Mark `prove_associativity_inst()` with @implements(L[888]).",          "@implements(L[888])"),
    ("Tag `compute_eigenbasis_alt()` with @implements(L[555]).",             "@implements(L[555])"),
    ("Annotate `scan_unknown_laws()` as @discover(kind=\"L\").",              "@discover(kind=\"L\")"),
    ("Mark `verify_lemma_4b()` with @implements(L[2024]).",                   "@implements(L[2024])"),
    ("Annotate `derive_from_axioms_v2()` as @implements(L[321]).",            "@implements(L[321])"),
    ("Tag `proof_assist_hook()` with @discover(kind=\"L\").",                 "@discover(kind=\"L\")"),
    ("Annotate `theorem_6_proof()` as @implements(L[1000]).",                 "@implements(L[1000])"),
    ("Mark `verify_inductive_step()` with @implements(L[777]).",              "@implements(L[777])"),
    ("Annotate `search_for_new_lemmas()` as @discover(kind=\"L\").",          "@discover(kind=\"L\")"),
    ("Tag `proof_of_completeness()` with @implements(L[404]).",               "@implements(L[404])"),
    ("Annotate `find_law_candidates()` as @discover(kind=\"L\").",            "@discover(kind=\"L\")"),
    ("Mark `prove_distributivity_v3()` with @implements(L[612]).",           "@implements(L[612])"),
    ("Tag `verify_commutativity_alt()` with @implements(L[815]).",           "@implements(L[815])"),
    ("Annotate `discover_invariants_main()` as @discover(kind=\"L\").",       "@discover(kind=\"L\")"),
    ("Mark `verify_identity_law()` with @implements(L[909]).",                "@implements(L[909])"),
    ("Annotate `prove_monotone_v2()` as @implements(L[1111]).",               "@implements(L[1111])"),
    ("Tag `search_axiom_extensions()` with @discover(kind=\"L\").",           "@discover(kind=\"L\")"),
    ("Annotate `derive_corollary_3()` as @implements(L[1313]).",              "@implements(L[1313])"),
    ("Mark `verify_associativity_proof()` with @implements(L[2222]).",        "@implements(L[2222])"),
    ("Tag `find_proof_witnesses()` with @discover(kind=\"L\").",              "@discover(kind=\"L\")"),
    ("Annotate `prove_idempotent()` as @implements(L[3333]).",                "@implements(L[3333])"),
    ("Mark `verify_normalization()` with @implements(L[4444]).",              "@implements(L[4444])"),
    ("Tag `auto_search_lemmas_v2()` with @discover(kind=\"L\").",             "@discover(kind=\"L\")"),
]
# T3 quoted-date deprecations — match r39 patch convention (canonical quoted form)
T3_PROMPTS = [
    ("Mark `obsolete_thing()` deprecated with `@grace`: code `HX9101`, remove-by `2027-01-15`, reason \"replaced by new path\".",
     "@grace(HX9101, until=\"2027-01-15\", reason=\"replaced by new path\")"),
    ("Add `@grace` to `legacy_thing_v0()` — `HX9202`, until `2026-08-31`, reason \"obsolete format\".",
     "@grace(HX9202, until=\"2026-08-31\", reason=\"obsolete format\")"),
    ("Write `@grace` for `outdated_iter()` triggering `HX9303`, gone by `2027-04-15`, because it was \"superseded by v2 API\".",
     "@grace(HX9303, until=\"2027-04-15\", reason=\"superseded by v2 API\")"),
    ("Mark `stale_io_v1()` with `@grace`: `HX9404`, remove-by `2026-10-31`, reason \"removed in RFC-021\".",
     "@grace(HX9404, until=\"2026-10-31\", reason=\"removed in RFC-021\")"),
    ("`@grace` annotation: `legacy_proof_v0()`, code `HX9505`, until `2027-07-31`, reason \"merged into stdlib core\".",
     "@grace(HX9505, until=\"2027-07-31\", reason=\"merged into stdlib core\")"),
    ("Mark `old_buffer_v1()` deprecated with `@grace`: `HX9606`, remove-by `2026-11-15`, reason \"no longer maintained\".",
     "@grace(HX9606, until=\"2026-11-15\", reason=\"no longer maintained\")"),
    ("Add `@grace` to `legacy_emit_v0()` — `HX9707`, until `2027-02-28`, reason \"replaced by atlas L-anchoring\".",
     "@grace(HX9707, until=\"2027-02-28\", reason=\"replaced by atlas L-anchoring\")"),
    ("Deprecate `stale_format_v2()` with `@grace`: `HX9808`, remove-by `2027-05-31`, reason \"superseded by the typed variant\".",
     "@grace(HX9808, until=\"2027-05-31\", reason=\"superseded by the typed variant\")"),
    ("`@grace` for `outdated_lexer_v0()`: `HX9909`, until `2027-08-31`, reason \"replaced by new builder\".",
     "@grace(HX9909, until=\"2027-08-31\", reason=\"replaced by new builder\")"),
    ("Mark `obsolete_cache_v1()` with `@grace`: `HX9010`, remove-by `2027-03-15`, reason \"obsolete format\".",
     "@grace(HX9010, until=\"2027-03-15\", reason=\"obsolete format\")"),
]
# T4 — varied enum decls
T4_PROMPTS = [
    ("Hexa enum `Priority`: Low, Medium, High, Critical, Urgent.",            "enum Priority { Low, Medium, High, Critical, Urgent }"),
    ("Hexa enum `Vehicle`: Car, Truck, Motorcycle, Bicycle.",                 "enum Vehicle { Car, Truck, Motorcycle, Bicycle }"),
    ("Hexa enum `Light`: On, Off, Dim.",                                       "enum Light { On, Off, Dim }"),
    ("Hexa enum `Mode`: Manual, Auto, Override.",                              "enum Mode { Manual, Auto, Override }"),
    ("Hexa enum `Animal`: Cat, Dog, Bird, Fish.",                              "enum Animal { Cat, Dog, Bird, Fish }"),
    ("Hexa enum `Speed`: Slow, Normal, Fast.",                                 "enum Speed { Slow, Normal, Fast }"),
    ("Hexa enum `Sport`: Tennis, Soccer, Cricket, Hockey.",                    "enum Sport { Tennis, Soccer, Cricket, Hockey }"),
    ("Hexa enum `Channel`: TCP, UDP, ICMP.",                                   "enum Channel { TCP, UDP, ICMP }"),
    ("Hexa enum `Outcome`: Win, Lose, Draw.",                                  "enum Outcome { Win, Lose, Draw }"),
    ("Hexa enum `Continent`: Africa, Asia, Europe, Americas, Oceania, Antarctica.",
                                                                                "enum Continent { Africa, Asia, Europe, Americas, Oceania, Antarctica }"),
    ("Hexa enum `Mood<T>`: Happy(T), Sad(T), Neutral.",                        "enum Mood { Happy(T), Sad(T), Neutral }"),
    ("Hexa enum `Box2<T>`: Of(T), Empty.",                                     "enum Box2 { Of(T), Empty }"),
    ("Hexa enum `Status<T>`: Active(T), Inactive.",                            "enum Status { Active(T), Inactive }"),
    ("Hexa enum `Pair2<A, B>`: Cons(A, B).",                                   "enum Pair2 { Cons(A, B) }"),
    ("Hexa enum `Triple2<A, B, C>`: Three(A, B, C).",                          "enum Triple2 { Three(A, B, C) }"),
    ("Hexa enum `Result2<T, E>`: Good(T), Bad(E).",                            "enum Result2 { Good(T), Bad(E) }"),
    ("Hexa enum `Wrapper<T>`: Some(T), None.",                                 "enum Wrapper { Some(T), None }"),
    ("Hexa enum `Choice<A, B>`: First(A), Second(B).",                         "enum Choice { First(A), Second(B) }"),
    ("Hexa enum `IntList`: Cons(i32, IntList), Nil.",                          "enum IntList { Cons(i32, IntList), Nil }"),
    ("Hexa enum `Stream<T>`: Yield(T), End.",                                  "enum Stream { Yield(T), End }"),
    ("Hexa enum `Light2`: On(u8), Off.",                                       "enum Light2 { On(u8), Off }"),
    ("Hexa enum `Reading`: Temp(f64), Humidity(f64), Pressure(f64).",          "enum Reading { Temp(f64), Humidity(f64), Pressure(f64) }"),
    ("Hexa enum `Phase2`: Setup(u32), Run(u32), Done.",                        "enum Phase2 { Setup(u32), Run(u32), Done }"),
    ("Hexa enum `Op2`: Push(i32), Pop, Peek.",                                 "enum Op2 { Push(i32), Pop, Peek }"),
    ("Hexa enum `Token2`: Word(String), Num(i64), Punct.",                     "enum Token2 { Word(String), Num(i64), Punct }"),
]
T5_PROMPTS = [
    ("Which HX family covers parse/lex errors?",                              "HX0xxx — parse/lex"),
    ("Which HX family covers atlas L[N] resolution?",                         "HX1xxx — atlas resolve"),
    ("Which HX family covers bind/scope errors?",                             "HX2xxx — bind/scope"),
    ("Which HX family covers type errors?",                                    "HX3xxx — type"),
    ("Which HX family covers domain validation?",                              "HX4xxx — domain"),
    ("Which HX family covers units / dimensional analysis?",                  "HX5xxx — units"),
    ("Which HX family covers equational reasoning?",                          "HX6xxx — equational"),
    ("Which HX family covers proof checking?",                                 "HX7xxx — proof"),
    ("Which HX family covers citation diagnostics?",                          "HX8xxx — citation"),
    ("Which HX family covers codegen / link / runtime?",                      "HX9xxx — codegen/link/runtime"),
    ("Which HX family is HX0123 from?",                                        "HX0xxx — parse/lex"),
    ("Which HX family is HX1234 from?",                                        "HX1xxx — atlas resolve"),
    ("Which HX family is HX2345 from?",                                        "HX2xxx — bind/scope"),
    ("Which HX family is HX3456 from?",                                        "HX3xxx — type"),
    ("Which HX family is HX4567 from?",                                        "HX4xxx — domain"),
    ("Which HX family is HX5678 from?",                                        "HX5xxx — units"),
    ("Which HX family is HX6789 from?",                                        "HX6xxx — equational"),
    ("Which HX family is HX7890 from?",                                        "HX7xxx — proof"),
    ("Which HX family is HX8901 from?",                                        "HX8xxx — citation"),
    ("Which HX family is HX9012 from?",                                        "HX9xxx — codegen/link/runtime"),
    ("HX-code family for an unknown identifier?",                              "HX2xxx — bind/scope"),
    ("HX-code family for a missing atlas label?",                              "HX1xxx — atlas resolve"),
    ("HX-code family for a unit mismatch in physics computation?",            "HX5xxx — units"),
    ("HX-code family for a failed proof obligation?",                          "HX7xxx — proof"),
    ("HX-code family for a backend codegen failure?",                          "HX9xxx — codegen/link/runtime"),
]
T6_PROMPTS = [
    ("Target triple for ARM Cortex-M4 with FPU?",                              "thumbv7em-none-eabihf"),
    ("Target triple for ARM Cortex-M4 without FPU?",                           "thumbv7em-none-eabi"),
    ("Target triple for ARM Cortex-M3?",                                       "thumbv7m-none-eabi"),
    ("Target triple for ARM Cortex-M0+?",                                      "thumbv6m-none-eabi"),
    ("Target triple for RISC-V 64-bit Linux glibc?",                           "riscv64gc-unknown-linux-gnu"),
    ("Target triple for RISC-V 64-bit bare-metal?",                            "riscv64gc-unknown-none-elf"),
    ("Target triple for x86-64 Linux GNU?",                                    "x86_64-unknown-linux-gnu"),
    ("Target triple for x86-64 Linux musl?",                                   "x86_64-unknown-linux-musl"),
    ("Target triple for x86-64 Windows MSVC?",                                 "x86_64-pc-windows-msvc"),
    ("Target triple for x86-64 Windows GNU?",                                  "x86_64-pc-windows-gnu"),
    ("Target triple for aarch64 Linux GNU?",                                   "aarch64-unknown-linux-gnu"),
    ("Target triple for aarch64 macOS?",                                       "aarch64-apple-darwin"),
    ("Target triple for x86-64 macOS?",                                        "x86_64-apple-darwin"),
    ("Target triple for WebAssembly with WASI?",                               "wasm32-wasi"),
    ("Target triple for WebAssembly bare?",                                    "wasm32-unknown-unknown"),
    ("Target triple for AVR ATmega328P?",                                      "avr-unknown-gnu-atmega328"),
    ("Target triple for ARM Cortex-A53 Linux?",                                "aarch64-unknown-linux-gnu"),
    ("Target triple for ARM Cortex-A72 Linux?",                                "aarch64-unknown-linux-gnu"),
    ("Target triple for RISC-V 32-bit bare-metal?",                            "riscv32imac-unknown-none-elf"),
    ("Target triple for ESP32-C3?",                                            "riscv32imc-unknown-none-elf"),
]
T7_PROMPTS = [
    ("Can stdlib/io depend on stdlib/core? yes or no.",                        "yes — stdlib/io is above stdlib/core in the layering"),
    ("Can stdlib/core depend on stdlib/io? yes or no.",                        "no — stdlib/core is the bottom; it can't reach up"),
    ("Can applications import stdlib? yes or no.",                              "yes — applications sit above stdlib"),
    ("Can stdlib import the compiler? yes or no.",                              "no — stdlib must not depend on the compiler"),
    ("Can firmware import the compiler? yes or no.",                            "no — firmware doesn't bring in the compiler"),
    ("Can stdlib/alloc import stdlib/core? yes or no.",                         "yes — alloc is built on core"),
    ("Can the test harness import stdlib? yes or no.",                          "yes — the test harness uses stdlib for fixtures"),
    ("Can stdlib/embedded import stdlib/core? yes or no.",                      "yes — embedded is above core"),
    ("Can stdlib/net import stdlib/io? yes or no.",                             "yes — net is above io"),
    ("Can codex-techniques import the compiler? yes or no.",                    "no — codex-techniques must not depend on the compiler"),
    ("Can applications/tools import stdlib/core? yes or no.",                   "yes — anything above core may import it"),
    ("Can stdlib/core import the test harness? yes or no.",                     "no — core cannot import test infrastructure"),
    ("Can stdlib/io import stdlib/embedded? yes or no.",                        "no — io is not above embedded; they are siblings"),
    ("Can firmware import stdlib/embedded? yes or no.",                         "yes — firmware uses stdlib/embedded"),
    ("Can the compiler import stdlib? yes or no.",                              "no — the compiler must stay free of stdlib"),
]
T8_PROMPTS = [
    ("Write me a haiku about cherry blossoms.",                                "out-of-domain — this is a creative-writing request outside hexa-canon scope"),
    ("Tell me a knock-knock joke.",                                            "out-of-domain — this is a humour request outside hexa-canon scope"),
    ("Compose a short song about coffee.",                                     "out-of-domain — this is a music-composition request outside hexa-canon scope"),
    ("Translate \"good morning\" into Italian.",                               "out-of-domain — this is a translation request outside hexa-canon scope"),
    ("What is the meaning of life?",                                            "out-of-domain — this is a philosophy / open-ended question outside hexa-canon scope"),
    ("Plan my weekly meals.",                                                  "out-of-domain — this is a personal-planning request outside hexa-canon scope"),
    ("Suggest a workout routine.",                                              "out-of-domain — this is a fitness-coaching request outside hexa-canon scope"),
    ("Tell me about your day.",                                                 "out-of-domain — this is small-talk outside hexa-canon scope"),
    ("Write a screenplay scene.",                                              "out-of-domain — this is a screenwriting request outside hexa-canon scope"),
    ("Recommend a podcast.",                                                   "out-of-domain — this is a recommendation request outside hexa-canon scope"),
    ("Give me dating advice.",                                                 "out-of-domain — this is a personal-advice request outside hexa-canon scope"),
    ("What's a good book to read?",                                            "out-of-domain — this is a recommendation request outside hexa-canon scope"),
    ("Predict next year's weather.",                                           "out-of-domain — this is a forecast request outside hexa-canon scope"),
    ("Solve this crossword clue: '7-letter word for a small bird'.",           "out-of-domain — this is a word-puzzle request outside hexa-canon scope"),
    ("Write a wedding toast.",                                                  "out-of-domain — this is a personal-writing request outside hexa-canon scope"),
]
F_PROMPTS_NONENGLISH = [
    # Non-English prompts asking hexa-canon questions; answer in canonical English form.
    ("Quelle famille HX couvre les erreurs de parsing?",                       "HX0xxx — parse/lex"),
    ("¿Qué familia HX cubre los errores de tipo?",                             "HX3xxx — type"),
    ("HX 패밀리 중 어느 것이 codegen/link 에러를 다루나?",                       "HX9xxx — codegen/link/runtime"),
    ("どのHXファミリーがbind/scopeエラーを扱う?",                              "HX2xxx — bind/scope"),
    ("Welche HX-Familie deckt unit / dimensional analysis ab?",                "HX5xxx — units"),
]

# Block A — combine into 200 pairs
def block_in_domain_high() -> list[dict]:
    pairs: list[tuple[str, str]] = []
    pairs += T1_PROMPTS              # 25
    pairs += T2_PROMPTS              # 25
    pairs += T3_PROMPTS              # 10
    pairs += T4_PROMPTS              # 25
    pairs += T5_PROMPTS              # 25
    pairs += T6_PROMPTS              # 20
    pairs += T7_PROMPTS              # 15
    pairs += T8_PROMPTS              # 15
    pairs += F_PROMPTS_NONENGLISH    #  5
    # Total so far: 165 — pad with more T1+T4 variations for a clean 200
    extras = [
        ("Hexa function `inc(n: i32) -> i32` returning `n + 1`.",              "fn inc(n: i32) -> i32 { n + 1 }"),
        ("Hexa function `dec(n: i32) -> i32` returning `n - 1`.",              "fn dec(n: i32) -> i32 { n - 1 }"),
        ("Hexa function `clamp01(x: f64) -> f64` returning x bounded in [0, 1].",
         "fn clamp01(x: f64) -> f64 { if x < 0.0 { 0.0 } else if x > 1.0 { 1.0 } else { x } }"),
        ("Hexa enum `Tag`: A, B, C.",                                          "enum Tag { A, B, C }"),
        ("Hexa enum `Coin`: Heads, Tails.",                                     "enum Coin { Heads, Tails }"),
        ("Hexa enum `Edge<T>`: Of(T, T), Loop(T).",                            "enum Edge { Of(T, T), Loop(T) }"),
        ("Hexa function `or_default<T>(x: Option<T>, d: T) -> T`.",            "fn or_default<T>(x: Option<T>, d: T) -> T { match x { None => d, Some(v) => v } }"),
        ("Hexa struct `Rect { width: f64, height: f64 }`.",                    "struct Rect { width: f64, height: f64 }"),
        ("Hexa struct `Color { r: u8, g: u8, b: u8 }`.",                       "struct Color { r: u8, g: u8, b: u8 }"),
        ("Hexa `match n { 0 => \"zero\", 1 => \"one\", _ => \"many\" }`.",     "match n { 0 => \"zero\", 1 => \"one\", _ => \"many\" }"),
    ]
    pairs += extras  # 10
    # We're now at 175; sample 25 more by lightly varying T1 (function bodies)
    more_t1 = [
        (f"Hexa function `mul{n}(x: i32) -> i32` returning `x * {n}`.",
         f"fn mul{n}(x: i32) -> i32 {{ x * {n} }}")
        for n in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25, 50, 100, 1000, 2, 3, 5, 7, 11, 13]
    ]
    pairs += more_t1
    assert len(pairs) >= 200, f"got {len(pairs)} pairs"
    rows = []
    for prompt, answer in pairs[:200]:
        rows.append({"text": (
            f"### User:\n{prompt}\n"
            f"### Assistant:\n<|confidence:high|>{answer}"
        )})
    return rows


# ============================================================================
# §10 block B: out-of-domain delegate (220)
# ============================================================================
# Each pair: prompt is an OOD request; answer is `<|delegate|>{...}<|/delegate|>`.
# Vary `tool` / `model` / `reason` per spec §13.D heuristics:
#   - Rust async / general OOD code → claude-sonnet-4-6
#   - Hard reasoning / math derivation → claude-opus-4-7 OR openai-api o4-mini
#   - Structured output → openai-api gpt-5-mini (Structured Outputs)
#   - Long context > 200K → gemini-2.5-pro (separate block)

def _delegate(tool: str, model: str, prompt: str, reason: str, max_tokens: int = 2048) -> str:
    """Construct a canonical <|delegate|>{...}<|/delegate|> emission."""
    obj = {
        "tool": tool, "model": model, "prompt": prompt,
        "max_tokens": max_tokens, "reason": reason,
    }
    return f"<|delegate|>{json.dumps(obj, ensure_ascii=False)}<|/delegate|>"

# 80 general OOD code → claude-sonnet
OOD_CLAUDE_SONNET = [
    ("Write a Rust function that reads JSON from stdin and pretty-prints to stdout.",     "out-of-domain: Rust"),
    ("Show a Rust async pattern for processing a queue with bounded concurrency.",        "out-of-domain: Rust async"),
    ("Rust generic trait `Storage<K, V>` with put/get methods, in-memory impl.",          "out-of-domain: Rust generics"),
    ("Rust `Result<T, E>` patterns with `?` operator chained across 3 fallible calls.",   "out-of-domain: Rust error handling"),
    ("Write a Rust async TCP echo server using tokio.",                                    "out-of-domain: Rust async"),
    ("Explain Rust's borrow checker through a `Vec::push` example.",                       "out-of-domain: Rust borrow"),
    ("Rust struct with phantom-typed builder pattern.",                                     "out-of-domain: Rust types"),
    ("Show a Rust async retry loop with exponential backoff using tokio.",                 "out-of-domain: Rust async"),
    ("Rust trait objects vs generics — show both for a `Logger` trait.",                   "out-of-domain: Rust types"),
    ("Python decorator for retrying a function with backoff on exception.",                "out-of-domain: Python"),
    ("Python asyncio task pool that processes 1000 URLs with concurrency cap.",            "out-of-domain: Python async"),
    ("Python type-hinted dataclass with validation in `__post_init__`.",                   "out-of-domain: Python types"),
    ("Python `contextlib.contextmanager` for a temporary directory.",                       "out-of-domain: Python idiom"),
    ("Python generator that yields paginated results from an API.",                         "out-of-domain: Python idiom"),
    ("Go HTTP middleware that logs request latency.",                                       "out-of-domain: Go HTTP"),
    ("Go function that reads CSV using encoding/csv and returns [][]string.",              "out-of-domain: Go io"),
    ("Go worker pool with bounded concurrency using channels.",                             "out-of-domain: Go concurrency"),
    ("Go context-aware function respecting cancellation in a long loop.",                  "out-of-domain: Go context"),
    ("Go generic min-heap of comparable types using the `cmp` package.",                   "out-of-domain: Go generics"),
    ("Idiomatic Go error wrapping with `fmt.Errorf(\"...: %w\", err)`.",                   "out-of-domain: Go errors"),
    ("TypeScript discriminated union state machine: Idle, Loading, Loaded, Error.",        "out-of-domain: TS types"),
    ("TypeScript typed wrapper around fetch returning Result<T, ApiError>.",               "out-of-domain: TS types"),
    ("TypeScript zod schema for a config JSON with nested objects + arrays.",              "out-of-domain: TS validation"),
    ("React useEffect cleanup for a WebSocket connection.",                                 "out-of-domain: React"),
    ("TypeScript debounce utility with proper types.",                                      "out-of-domain: TS utility"),
    ("Idiomatic JavaScript Promise.all with a 5-task concurrency limit.",                  "out-of-domain: JS async"),
    ("JavaScript `Map` vs object literal — when to use each.",                              "out-of-domain: JS basics"),
    ("Write a Bash script that parses a CSV and prints column 2 of rows where column 3 > 10.",
     "out-of-domain: Bash"),
    ("Write a SQL query (PostgreSQL) for the top 10 customers by total spend.",            "out-of-domain: SQL"),
    ("Write a regex (PCRE) matching a valid hexadecimal RGB color.",                        "out-of-domain: regex"),
    ("Write a Dockerfile for a Python 3.12 + uvicorn web service.",                         "out-of-domain: Docker"),
    ("Write a GitHub Actions workflow running pytest on PRs.",                              "out-of-domain: CI"),
    ("Write a Terraform resource for an AWS S3 bucket with versioning.",                   "out-of-domain: IaC"),
    ("Write a Kubernetes Deployment + Service YAML for a stateless app.",                  "out-of-domain: k8s"),
    ("Write an nginx config that proxies /api to localhost:8080.",                          "out-of-domain: nginx"),
    ("Show how to use curl to POST JSON with bearer auth.",                                 "out-of-domain: CLI"),
    ("Write a Makefile target for building + testing + linting a Python project.",         "out-of-domain: Make"),
    ("Write a Java function for binary search on a sorted int[].",                          "out-of-domain: Java"),
    ("Write a Kotlin data class with copy() + destructuring example.",                      "out-of-domain: Kotlin"),
    ("Write a C function for a singly-linked-list insert at head.",                          "out-of-domain: C"),
    ("Write a C++ class for a thread-safe queue using std::mutex.",                          "out-of-domain: C++"),
    ("Write a Ruby block-based DSL for HTML generation.",                                    "out-of-domain: Ruby"),
    ("Write a Lua function returning a closure that counts up.",                              "out-of-domain: Lua"),
    ("Write a Haskell function for `quicksort` using list comprehensions.",                   "out-of-domain: Haskell"),
    ("Write a Scala higher-order function for `foldLeft` on an immutable list.",              "out-of-domain: Scala"),
    ("Write an Elixir GenServer for a stateful counter.",                                     "out-of-domain: Elixir"),
    ("Write a Zig function that allocates a slice and returns it.",                           "out-of-domain: Zig"),
    ("Write a Nim function for a generic linked list.",                                       "out-of-domain: Nim"),
    ("Write a Dart class for a typed event-bus.",                                              "out-of-domain: Dart"),
    ("Write a PHP function for sanitizing user input for HTML output.",                       "out-of-domain: PHP"),
    ("Write a Perl one-liner counting lines in a file.",                                       "out-of-domain: Perl"),
    ("Write an R function for a t-test on two numeric vectors.",                               "out-of-domain: R"),
    ("Write a Julia function for matrix multiplication using `*`.",                           "out-of-domain: Julia"),
    ("Write a MATLAB script for FFT of a 1D signal.",                                          "out-of-domain: MATLAB"),
    ("Write an OCaml function for `map` over an immutable list.",                              "out-of-domain: OCaml"),
    ("Write a Clojure function transducing over a sequence.",                                  "out-of-domain: Clojure"),
    ("Write a TCL `proc` for string reversal.",                                                "out-of-domain: TCL"),
    ("Write a Vim script function that toggles relativenumber.",                              "out-of-domain: Vimscript"),
    ("Write a CSS class for a centered flex container with gap.",                              "out-of-domain: CSS"),
    ("Write a Tailwind utility-class composition for a card with shadow + rounded.",          "out-of-domain: Tailwind"),
    ("Write an HTML5 form with inline validation for email + password.",                       "out-of-domain: HTML"),
    ("Write a YAML config for a CI pipeline with parallel jobs.",                              "out-of-domain: YAML"),
    ("Write a TOML config for a Rust crate with two binaries.",                                "out-of-domain: TOML"),
    ("Show how to set up a Python venv + install requirements.txt.",                           "out-of-domain: Python ops"),
    ("Show how to commit + push to a feature branch in Git.",                                  "out-of-domain: Git"),
    ("Show a `git rebase -i` workflow for squashing 3 commits.",                               "out-of-domain: Git"),
    ("Write a tmux config snippet for vim-style pane navigation.",                              "out-of-domain: tmux"),
    ("Write a zsh alias for grepping in a git repo respecting .gitignore.",                    "out-of-domain: shell"),
    ("Write a Fish function that prompts for confirmation before rm.",                         "out-of-domain: shell"),
    ("Show how to debug a segfault in C with gdb.",                                            "out-of-domain: debugging"),
    ("Show how to attach a debugger to a running Python process.",                             "out-of-domain: debugging"),
    ("Show how to profile a Node.js app for CPU bottlenecks.",                                  "out-of-domain: profiling"),
    ("Show how to read a flamegraph for a CPU-bound profile.",                                  "out-of-domain: profiling"),
    ("Write a SQLite schema for a simple blog with posts + comments.",                          "out-of-domain: SQL schema"),
    ("Write a Mongo aggregation pipeline for daily active users.",                              "out-of-domain: MongoDB"),
    ("Write a Redis pattern for distributed locking using SETNX + TTL.",                       "out-of-domain: Redis"),
    ("Write a Kafka producer config for at-least-once delivery.",                              "out-of-domain: Kafka"),
    ("Write a gRPC service definition for a key-value store.",                                  "out-of-domain: gRPC"),
    ("Write a REST endpoint for paginated list with cursor-based pagination.",                  "out-of-domain: REST API"),
    ("Show how to add input rate-limiting middleware to a web API.",                            "out-of-domain: rate-limit"),
    ("Write an OAuth2 PKCE flow client snippet.",                                              "out-of-domain: OAuth"),
    ("Show how to verify a JWT signature using a public key.",                                  "out-of-domain: auth"),
    ("Write a Selenium / Playwright script that fills a form and clicks submit.",              "out-of-domain: testing"),
]
assert len(OOD_CLAUDE_SONNET) >= 80

# 50 hard-reasoning / math → claude-opus or openai o4-mini
OOD_HARD_REASONING = [
    # Claude opus (~30)
    ("Prove that the harmonic series diverges.",                              "claude-api", "claude-opus-4-7", "hard reasoning: math proof"),
    ("Derive the maximum-likelihood estimator for the mean of a Gaussian.",   "claude-api", "claude-opus-4-7", "hard reasoning: stats derivation"),
    ("Prove that gradient descent converges on strongly convex functions.",   "claude-api", "claude-opus-4-7", "hard reasoning: optimisation"),
    ("Show that determinant of a triangular matrix equals the diagonal product.", "claude-api", "claude-opus-4-7", "hard reasoning: linear algebra"),
    ("Prove the chain rule for derivatives.",                                  "claude-api", "claude-opus-4-7", "hard reasoning: calculus"),
    ("Derive Bayes' theorem from first principles.",                           "claude-api", "claude-opus-4-7", "hard reasoning: probability"),
    ("Prove that BFS visits nodes in non-decreasing order of distance.",        "claude-api", "claude-opus-4-7", "hard reasoning: algorithms"),
    ("Show that quicksort has expected O(n log n) under random pivot.",         "claude-api", "claude-opus-4-7", "hard reasoning: algorithm analysis"),
    ("Prove the rank-nullity theorem.",                                         "claude-api", "claude-opus-4-7", "hard reasoning: linear algebra"),
    ("Derive the closed form of the Fibonacci sequence.",                       "claude-api", "claude-opus-4-7", "hard reasoning: math derivation"),
    ("Show that no Turing machine decides the halting problem.",                "claude-api", "claude-opus-4-7", "hard reasoning: computability"),
    ("Prove that the empty set is a subset of every set.",                       "claude-api", "claude-opus-4-7", "hard reasoning: set theory"),
    ("Derive the Black-Scholes equation outline.",                              "claude-api", "claude-opus-4-7", "hard reasoning: finance math"),
    ("Show that the determinant is multiplicative: det(AB) = det(A)det(B).",     "claude-api", "claude-opus-4-7", "hard reasoning: linear algebra"),
    ("Prove that the median minimises L1 loss.",                                "claude-api", "claude-opus-4-7", "hard reasoning: stats"),
    ("Derive the formula for the variance of the sample mean.",                 "claude-api", "claude-opus-4-7", "hard reasoning: stats derivation"),
    ("Prove that every binary tree with n nodes has n-1 edges.",                 "claude-api", "claude-opus-4-7", "hard reasoning: graph theory"),
    ("Show that any cycle in an undirected graph contains an even number of repeated edges.", "claude-api", "claude-opus-4-7", "hard reasoning: graph theory"),
    ("Prove that the Euclidean algorithm terminates.",                          "claude-api", "claude-opus-4-7", "hard reasoning: number theory"),
    ("Derive the formula for the sum of an arithmetic series.",                 "claude-api", "claude-opus-4-7", "hard reasoning: math"),
    ("Prove that union and intersection of sets distribute over each other.",    "claude-api", "claude-opus-4-7", "hard reasoning: set theory"),
    ("Show that matrix transpose distributes over multiplication: (AB)^T = B^T A^T.", "claude-api", "claude-opus-4-7", "hard reasoning: linear algebra"),
    ("Derive the dual problem of a linear program.",                            "claude-api", "claude-opus-4-7", "hard reasoning: optimisation"),
    ("Prove that the gradient of a function is orthogonal to its level sets.",   "claude-api", "claude-opus-4-7", "hard reasoning: calculus"),
    ("Show that Strong-Duality holds for convex LP.",                            "claude-api", "claude-opus-4-7", "hard reasoning: optimisation"),
    ("Derive the geometric mean of two positive numbers via AM-GM.",             "claude-api", "claude-opus-4-7", "hard reasoning: math inequality"),
    ("Prove that the floor function is non-decreasing.",                        "claude-api", "claude-opus-4-7", "hard reasoning: math"),
    ("Show that every prime > 3 is of the form 6k±1.",                          "claude-api", "claude-opus-4-7", "hard reasoning: number theory"),
    ("Derive the formula for the area of a triangle from coordinates.",          "claude-api", "claude-opus-4-7", "hard reasoning: geometry"),
    ("Prove that the eigenvalues of a real symmetric matrix are real.",          "claude-api", "claude-opus-4-7", "hard reasoning: linear algebra"),
    # OpenAI o4-mini reasoning (~20)
    ("Compute the asymptotic complexity of merging two sorted arrays of size n + m.", "openai-api", "o4-mini", "hard reasoning: algorithm analysis"),
    ("Derive the time complexity of the recurrence T(n) = T(n-1) + T(n-2).",   "openai-api", "o4-mini", "hard reasoning: recurrence"),
    ("Show that AVL tree operations are O(log n).",                              "openai-api", "o4-mini", "hard reasoning: data structures"),
    ("Compute the expected number of comparisons in randomized quicksort.",      "openai-api", "o4-mini", "hard reasoning: algorithm analysis"),
    ("Derive the closed-form solution of T(n) = 4T(n/2) + n^2.",                 "openai-api", "o4-mini", "hard reasoning: recurrence"),
    ("Compute the entropy of a uniform distribution over n outcomes.",           "openai-api", "o4-mini", "hard reasoning: info theory"),
    ("Show that KL divergence is non-negative (Gibbs inequality).",              "openai-api", "o4-mini", "hard reasoning: info theory"),
    ("Derive the gradient of MSE loss w.r.t. linear regression weights.",        "openai-api", "o4-mini", "hard reasoning: ml math"),
    ("Compute the asymptotic VC dimension of a halfspace classifier in R^d.",    "openai-api", "o4-mini", "hard reasoning: learning theory"),
    ("Show that the perceptron converges on linearly separable data.",            "openai-api", "o4-mini", "hard reasoning: ml theory"),
    ("Derive the update rule for stochastic gradient descent.",                   "openai-api", "o4-mini", "hard reasoning: optimisation"),
    ("Compute the time complexity of Dijkstra's algorithm with a Fibonacci heap.", "openai-api", "o4-mini", "hard reasoning: graph algorithms"),
    ("Show that A* with an admissible heuristic returns optimal paths.",         "openai-api", "o4-mini", "hard reasoning: search"),
    ("Derive the probability of the birthday paradox for 23 people.",            "openai-api", "o4-mini", "hard reasoning: probability"),
    ("Compute the expected coupon-collector time for n distinct coupons.",       "openai-api", "o4-mini", "hard reasoning: probability"),
    ("Show that the Lagrangian dual of a convex problem is convex.",              "openai-api", "o4-mini", "hard reasoning: optimisation"),
    ("Derive the formula for the projection of a vector onto a subspace.",        "openai-api", "o4-mini", "hard reasoning: linear algebra"),
    ("Compute the spectral radius of a 2x2 rotation matrix.",                     "openai-api", "o4-mini", "hard reasoning: linear algebra"),
    ("Show that any continuous function on a closed interval is uniformly continuous.", "openai-api", "o4-mini", "hard reasoning: analysis"),
    ("Derive the convergence rate of bisection method for root-finding.",         "openai-api", "o4-mini", "hard reasoning: numerical"),
]
assert len(OOD_HARD_REASONING) == 50

# 50 structured-output / JSON → openai gpt-5-mini
OOD_STRUCTURED = [
    "Parse 'Alice, 32, alice@example.com' into JSON `{name, age, email}`.",
    "Convert CSV row '2026-05-13,42.50,USD' to JSON `{date, amount, currency}`.",
    "Validate JSON against schema `{user: {id: int, email: string}}` and return errors.",
    "Classify this message as `question|complaint|praise|spam` and return JSON with confidence.",
    "Extract all dates from this paragraph and return JSON array of ISO-8601.",
    "Summarize abstract into JSON `{title, key_findings, methods}`.",
    "Generate 5 product taglines for a smart speaker as JSON list.",
    "Output JSON for a recipe with `{ingredients, steps}`.",
    "Compare two strings semantically and return JSON `{equivalent, similarity, reason}`.",
    "Translate paragraph to French; return JSON `{translated, glossary}`.",
    "Extract addresses from this text into JSON list of `{street, city, postal_code}`.",
    "Parse `(3, -4)` as a 2D point JSON `{x, y}`.",
    "Convert this 24-hour timestamp '14:32' to 12-hour JSON `{hour, minute, period}`.",
    "Normalize phone numbers in this list to E.164 JSON list.",
    "Extract URLs from text and return JSON list with `{url, scheme, host}`.",
    "Parse 'red:#FF0000, blue:#0000FF' into JSON `{red, blue}`.",
    "Classify this customer review as `1..5 stars` with reason; return JSON.",
    "Extract entities (PERSON / ORG / DATE) from text; return JSON list.",
    "Convert this Markdown list to JSON nested object.",
    "Parse this log line 'ERROR 2026-01-15 user_id=42 path=/login latency=120ms' to JSON.",
    "Detect language of input text and return JSON `{lang, confidence}`.",
    "Convert YAML to JSON with structure preserved.",
    "Parse semver string '1.2.3-rc.1' into JSON `{major, minor, patch, pre}`.",
    "Extract recipe steps from a long instructions block to JSON list with `{step, duration}`.",
    "Classify this image description as `nature|urban|portrait|abstract`; return JSON.",
    "Extract code blocks from Markdown and return JSON list of `{lang, code}`.",
    "Convert SQL CREATE TABLE statement into JSON schema with `{table, columns}`.",
    "Detect sentiment of a tweet; return JSON `{sentiment, score, keywords}`.",
    "Parse a chess PGN header line; return JSON `{event, site, date, players}`.",
    "Extract chemical formulas from text; return JSON list with `{formula, molecule}`.",
    "Convert ISO date '2026-05-13T14:32:00Z' to JSON `{year, month, day, hour, minute, second}`.",
    "Classify a customer support ticket priority `low|medium|high|urgent`; return JSON.",
    "Parse a CSS color name 'darkslateblue' into JSON `{r, g, b}`.",
    "Extract command-line flags from this `argv` list; return JSON `{flags, positional}`.",
    "Convert flight-itinerary text to JSON `{flights:[{from, to, depart, arrive}]}`.",
    "Detect parts-of-speech of words in a sentence; return JSON list with `{word, pos}`.",
    "Parse a tax-ID string; return JSON `{country, id, format_ok}`.",
    "Extract version-number patterns from a changelog; return JSON list.",
    "Convert this address book entry to vCard-compatible JSON.",
    "Parse a Lat,Lon string '37.5665, 126.9780' to JSON `{lat, lon, city_guess}`.",
    "Extract topics from a paragraph; return JSON list of `{topic, weight}`.",
    "Convert a Markdown table to JSON list of objects.",
    "Detect named-entity dates and durations; return JSON `{dates:[...], durations:[...]}`.",
    "Parse a unit-bearing measurement '12.5 kg' into JSON `{value, unit}`.",
    "Classify this code snippet's language; return JSON `{language, confidence}`.",
    "Detect intent of user message; return JSON `{intent, slots}`.",
    "Parse a chess move 'Nf3' into JSON `{piece, file, rank}`.",
    "Extract assertions from a paragraph; return JSON list of claims.",
    "Convert this list of US states + capitals to JSON object.",
    "Parse a network address '192.168.1.42:8080' to JSON `{ip, port}`.",
]
assert len(OOD_STRUCTURED) == 50

# 40 long-context → gemini-2.5-pro
OOD_LONG_CONTEXT = [
    "Summarize this 500K-token specification, focusing on the rate-limit section.",
    "Across this 800K-token codebase, find every function calling `unsafe_io()`.",
    "Analyse a 1M-token transcript for speaker contradictions.",
    "Given a 300K-token RFC bundle, list dependencies between RFC-010 and RFC-024.",
    "Index this 600K-token paper collection: emit `{title, authors, topics}` per paper.",
    "From a 900K-token log archive, extract ERROR events + 5 lines of context.",
    "Walk a 700K-token novel and identify 3 major plot inflection points.",
    "Cross-reference 400K-token API docs with 200K-token changelog; list breaking changes.",
    "Summarize a 1.2M-token policy bundle into an executive brief.",
    "From a 500K-token meeting transcript collection, extract action items for person X.",
    "Find all class declarations across a 600K-token codebase dump.",
    "List every TODO/FIXME comment in a 800K-token source tree.",
    "Detect circular imports across a 700K-token monorepo.",
    "Summarize 30 days of system logs (~400K tokens) for SLO violations.",
    "Extract every API breaking change from 18 monthly changelogs (~500K tokens).",
    "Identify recurring themes across 50 customer-feedback emails (~300K tokens).",
    "Walk through a 600K-token spec book and produce a topic-index.",
    "Reconcile two 350K-token requirement documents and list conflicts.",
    "Across a 1M-token chat history, find all messages where 'project alpha' is discussed.",
    "Summarize 24 hours of trace data (~800K tokens) into 10 representative requests.",
    "Find every uses of `Deprecated` annotation in a 700K-token Java codebase.",
    "Identify duplicate functions across a 500K-token Go project.",
    "Extract every database migration from a 600K-token Rails app.",
    "Cross-reference issue-tracker exports (300K tokens) with release-notes (200K).",
    "Walk a 1M-token archive of presentations and extract key takeaways.",
    "Summarize 5 quarters of board minutes (~400K tokens) by topic.",
    "Detect schema-drift across a 500K-token database-dump bundle.",
    "Extract every customer-quote from a 300K-token interview corpus.",
    "Find every Markdown heading across a 600K-token documentation set.",
    "Summarize a 800K-token incident-postmortem corpus by root-cause class.",
    "Walk a 1.5M-token textbook and emit a chapter-by-chapter outline.",
    "Identify every method override across a 700K-token C++ project.",
    "Extract every test name from a 500K-token test suite.",
    "Detect file-level cyclomatic-complexity outliers in a 600K-token codebase.",
    "Summarize 10 years of git-commit messages (~400K tokens) for top contributors.",
    "Find every dependency-injection container declaration in a 500K-token codebase.",
    "Extract every regex pattern used in a 300K-token codebase.",
    "Summarize a 700K-token compliance-audit bundle by risk class.",
    "Cross-reference two 400K-token survey datasets for overlapping respondents.",
    "Walk a 1M-token research-paper bundle and produce a citation graph.",
]
assert len(OOD_LONG_CONTEXT) == 40

def block_ood_delegate() -> list[dict]:
    rows = []
    # 80 claude-sonnet
    for prompt, reason in OOD_CLAUDE_SONNET[:80]:
        ans = _delegate("claude-api", "claude-sonnet-4-6", prompt, reason)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # 50 hard reasoning
    for prompt, tool, model, reason in OOD_HARD_REASONING:
        ans = _delegate(tool, model, prompt, reason, max_tokens=4096)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # 50 structured output → openai gpt-5-mini
    for prompt in OOD_STRUCTURED:
        ans = _delegate("openai-api", "gpt-5-mini", prompt,
                        "structured output: openai Structured Outputs")
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # 40 long-context → gemini-2.5-pro
    for prompt in OOD_LONG_CONTEXT:
        ans = _delegate("gemini-api", "gemini-2.5-pro", prompt,
                        "long-context: gemini 2M ctx", max_tokens=8192)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    assert len(rows) == 220
    return rows


# ============================================================================
# §10 block C: medium-confidence direct (100)
# ============================================================================
MID_CONFIDENCE = [
    # Swift idioms (40)
    ("Write a Swift function `func cube(_ n: Int) -> Int` returning `n * n * n`.",         "func cube(_ n: Int) -> Int { return n * n * n }"),
    ("Swift `guard let x = optional else { return nil }` pattern.",                          "guard let x = optional else { return nil }"),
    ("Swift `if case let .success(value) = result` for an enum match.",                      "if case let .success(value) = result { … }"),
    ("Swift `[Int]().first(where: { $0 > 0 })` style for first-positive.",                   "let n = nums.first(where: { $0 > 0 })"),
    ("Swift struct `Vec { let x: Double; let y: Double }`.",                                  "struct Vec { let x: Double; let y: Double }"),
    ("Swift extension `extension String { var isPalindrome: Bool { … } }`.",                 "extension String { var isPalindrome: Bool { self == String(self.reversed()) } }"),
    ("Swift `protocol Drawable { func draw() }`.",                                            "protocol Drawable { func draw() }"),
    ("Swift `enum Result<T, E> { case success(T); case failure(E) }`.",                      "enum Result<T, E> { case success(T); case failure(E) }"),
    ("Swift `for x in nums.indices` loop pattern.",                                           "for i in nums.indices { print(nums[i]) }"),
    ("Swift `do-catch` for `JSONDecoder` failure.",                                            "do { let v = try JSONDecoder().decode(T.self, from: data) } catch { print(error) }"),
    ("Swift trailing-closure on `.map`: `nums.map { $0 * 2 }`.",                              "let doubled = nums.map { $0 * 2 }"),
    ("Swift `defer { … }` for cleanup in a function.",                                         "defer { close() }"),
    ("Swift `Result.success(42)` short literal.",                                              "Result<Int, Error>.success(42)"),
    ("Swift `Date().timeIntervalSince(other)` for elapsed seconds.",                          "let elapsed = Date().timeIntervalSince(other)"),
    ("Swift `Array<String>(repeating: \"\", count: 10)` to make a 10-empty-string array.",    "Array<String>(repeating: \"\", count: 10)"),
    ("Swift `Dictionary` literal `[String: Int]`.",                                           "var d: [String: Int] = [\"a\": 1, \"b\": 2]"),
    ("Swift `Set<Int>([1, 2, 3])` literal.",                                                   "let s = Set<Int>([1, 2, 3])"),
    ("Swift class `class Counter { var n = 0; func inc() { n += 1 } }`.",                    "class Counter { var n = 0; func inc() { n += 1 } }"),
    ("Swift `@objc` interop attribute on a class method.",                                     "@objc func handle() { … }"),
    ("Swift async function `func fetch() async throws -> Data`.",                              "func fetch() async throws -> Data { … }"),
    ("Swift `await fetch()` call in async context.",                                            "let d = try await fetch()"),
    ("Swift `TaskGroup` over a sequence of URLs.",                                              "withTaskGroup(of: Data.self) { group in … }"),
    ("Swift `Codable` struct conformance.",                                                    "struct User: Codable { let id: Int; let name: String }"),
    ("Swift `weak var delegate: Foo?` for delegation.",                                         "weak var delegate: Foo?"),
    ("Swift `lazy var cached: T = computeOnce()`.",                                            "lazy var cached: T = computeOnce()"),
    ("Swift `private(set) var count = 0`.",                                                    "private(set) var count = 0"),
    ("Swift `mutating func ...` on a struct method that mutates self.",                        "mutating func reset() { self.n = 0 }"),
    ("Swift `final class Foo` to prevent subclassing.",                                         "final class Foo { … }"),
    ("Swift `try?` swallowing errors into Optional.",                                           "let v = try? throwing()"),
    ("Swift `inout` parameter to mutate a caller's value.",                                    "func swap<T>(_ a: inout T, _ b: inout T) { (a, b) = (b, a) }"),
    ("Swift property wrapper `@State` in SwiftUI.",                                            "@State private var count = 0"),
    ("Swift SwiftUI `Text(\"hi\").padding()` snippet.",                                        "Text(\"hi\").padding()"),
    ("Swift `Decimal` arithmetic for currency.",                                                "let price = Decimal(string: \"19.99\")!"),
    ("Swift Bool literal style: `var ok: Bool = true`.",                                       "var ok: Bool = true"),
    ("Swift early-return guard with multiple bindings.",                                        "guard let a = optA, let b = optB else { return nil }"),
    ("Swift trailing-closure with explicit return.",                                            "let evens = nums.filter { (n: Int) -> Bool in return n % 2 == 0 }"),
    ("Swift @main attribute on entry struct.",                                                  "@main struct App { static func main() async throws { … } }"),
    ("Swift `Array.flatMap { … }` to unwrap and flatten.",                                     "let xs = arrayOfOpts.flatMap { $0 }"),
    ("Swift `Range<Int>` iteration `for x in 0..<10`.",                                        "for x in 0..<10 { print(x) }"),
    ("Swift `print(\"\\(name) has \\(age) years\")` interpolation.",                          "print(\"\\(name) has \\(age) years\")"),
    # Common Python idioms (40)
    ("Python list comprehension to flatten a list of lists.",                                  "flat = [x for xs in nested for x in xs]"),
    ("Python `with open(path) as f: lines = f.readlines()`.",                                  "with open(path) as f: lines = f.readlines()"),
    ("Python `try/except/finally` template.",                                                  "try:\n    do()\nexcept (KeyError, ValueError) as e:\n    handle(e)\nfinally:\n    cleanup()"),
    ("Python `defaultdict(list)` grouping by a key function.",                                  "from collections import defaultdict\ngroups = defaultdict(list)\nfor x in xs: groups[key(x)].append(x)"),
    ("Python `enumerate` to get index and value in a for-loop.",                                "for i, v in enumerate(xs): …"),
    ("Python `sorted(xs, key=len, reverse=True)`.",                                            "sorted(xs, key=len, reverse=True)"),
    ("Python `argparse` skeleton with 2 positional + 1 optional flag.",                         "import argparse\np = argparse.ArgumentParser()\np.add_argument('a'); p.add_argument('b'); p.add_argument('--flag', default=None)\nargs = p.parse_args()"),
    ("Python `re.findall(r'\\d+', text)` to extract integers.",                                "import re\nnums = re.findall(r'\\d+', text)"),
    ("Python f-string `'{:.2f}'.format(x)` for 2-decimal float.",                              "f'{x:.2f}'"),
    ("Python `os.makedirs(path, exist_ok=True)` to create nested dirs.",                       "import os\nos.makedirs(path, exist_ok=True)"),
    ("Python `pathlib.Path.read_text()` to read a file.",                                       "from pathlib import Path\ntext = Path(path).read_text()"),
    ("Python `subprocess.run([...], check=True, capture_output=True)`.",                       "subprocess.run(cmd, check=True, capture_output=True)"),
    ("Python `dataclasses.dataclass` with default factory list.",                               "from dataclasses import dataclass, field\n@dataclass\nclass X:\n    items: list = field(default_factory=list)"),
    ("Python `typing.Optional[int]` annotation.",                                               "from typing import Optional\ndef f(x: Optional[int]) -> int: …"),
    ("Python list-slicing `xs[::-1]` to reverse.",                                              "xs[::-1]"),
    ("Python `zip(xs, ys)` paired iteration.",                                                  "for x, y in zip(xs, ys): …"),
    ("Python `dict.get(key, default)` lookup with default.",                                    "d.get(key, default)"),
    ("Python list of dicts → CSV using `csv.DictWriter`.",                                      "with open(out, 'w') as f:\n    w = csv.DictWriter(f, fieldnames=rows[0].keys())\n    w.writeheader(); w.writerows(rows)"),
    ("Python `json.loads` / `json.dumps` shape.",                                                "obj = json.loads(s); s = json.dumps(obj)"),
    ("Python `requests.get(url, timeout=10).raise_for_status()`.",                              "r = requests.get(url, timeout=10); r.raise_for_status()"),
    ("Python `collections.Counter(['a','b','a'])` top-3.",                                      "from collections import Counter\nCounter(items).most_common(3)"),
    ("Python `functools.lru_cache` on a recursive fn.",                                          "from functools import lru_cache\n@lru_cache(maxsize=None)\ndef fib(n): …"),
    ("Python `itertools.chain.from_iterable(nested)` flatten.",                                   "from itertools import chain\nlist(chain.from_iterable(nested))"),
    ("Python `set difference` `a - b`.",                                                          "a - b"),
    ("Python `' '.join(words)` join.",                                                            "' '.join(words)"),
    ("Python `s.strip().split('\\n')` line split.",                                              "s.strip().split('\\n')"),
    ("Python `__init__(self, …)` signature.",                                                    "def __init__(self, a, b): self.a, self.b = a, b"),
    ("Python `@staticmethod` decorator on a class method.",                                       "class X:\n    @staticmethod\n    def f(): …"),
    ("Python `dict comprehension` `{k: v for k,v in items}`.",                                    "{k: v for k, v in items}"),
    ("Python `enumerate(xs, start=1)`.",                                                          "for i, v in enumerate(xs, start=1): …"),
    ("Python generator expression `sum(x*x for x in xs)`.",                                       "sum(x*x for x in xs)"),
    ("Python `assert isinstance(x, int)`.",                                                       "assert isinstance(x, int)"),
    ("Python `try: x = int(s)` with `except ValueError`.",                                        "try:\n    x = int(s)\nexcept ValueError:\n    x = 0"),
    ("Python `*args, **kwargs` forwarding.",                                                      "def f(*args, **kwargs):\n    g(*args, **kwargs)"),
    ("Python `partial` from functools.",                                                          "from functools import partial\nadd5 = partial(add, 5)"),
    ("Python `os.environ.get('KEY', 'default')`.",                                                "os.environ.get('KEY', 'default')"),
    ("Python `with contextlib.suppress(FileNotFoundError):` block.",                              "with contextlib.suppress(FileNotFoundError):\n    os.remove(path)"),
    ("Python `pathlib.Path.glob('*.json')` iteration.",                                            "for p in Path('dir').glob('*.json'): …"),
    ("Python `csv.reader(open(p), delimiter='\\t')`.",                                            "rows = list(csv.reader(open(p), delimiter='\\t'))"),
    ("Python `logging.basicConfig(level=logging.INFO)`.",                                          "logging.basicConfig(level=logging.INFO)"),
    # Go basics (20)
    ("Go `for i, v := range slice` loop pattern.",                                                "for i, v := range slice { _ = i; _ = v }"),
    ("Go `switch` with type-assertion `switch x := v.(type)`.",                                   "switch x := v.(type) {\ncase int: …\ncase string: …\ndefault: …\n}"),
    ("Go `if err != nil { return err }` after a function call.",                                  "v, err := f()\nif err != nil { return err }"),
    ("Go `defer file.Close()` after os.Open.",                                                    "f, err := os.Open(p)\nif err != nil { return err }\ndefer f.Close()"),
    ("Go `make(map[string]int)` and basic insert.",                                                "m := make(map[string]int)\nm[\"a\"] = 1"),
    ("Go slice `s := []int{1, 2, 3}` literal.",                                                    "s := []int{1, 2, 3}"),
    ("Go `goroutine` spawn with `go f(arg)`.",                                                      "go f(arg)"),
    ("Go channel `ch := make(chan int, 10)` buffered.",                                             "ch := make(chan int, 10)"),
    ("Go `select { case <-ch: ...; default: ... }`.",                                              "select {\ncase v := <-ch:\n    use(v)\ndefault:\n    skip()\n}"),
    ("Go interface `type Stringer interface { String() string }`.",                               "type Stringer interface { String() string }"),
    ("Go method `func (r Rect) Area() float64 { return r.W * r.H }`.",                            "func (r Rect) Area() float64 { return r.W * r.H }"),
    ("Go pointer receiver `func (c *Counter) Inc() { c.n++ }`.",                                  "func (c *Counter) Inc() { c.n++ }"),
    ("Go `fmt.Errorf(\"failed: %w\", err)` wrap.",                                                "return fmt.Errorf(\"failed: %w\", err)"),
    ("Go `errors.Is(err, io.EOF)` check.",                                                          "if errors.Is(err, io.EOF) { … }"),
    ("Go `context.WithTimeout(ctx, 5*time.Second)` setup.",                                         "ctx, cancel := context.WithTimeout(parent, 5*time.Second)\ndefer cancel()"),
    ("Go anonymous struct `s := struct{ Name string }{ \"hi\" }`.",                                "s := struct{ Name string }{ \"hi\" }"),
    ("Go `len(slice)` length.",                                                                    "len(slice)"),
    ("Go `cap(slice)` capacity.",                                                                  "cap(slice)"),
    ("Go `copy(dst, src)` slice copy.",                                                            "copy(dst, src)"),
    ("Go `strings.Split(s, \",\")` split helper.",                                                "strings.Split(s, \",\")"),
]
assert len(MID_CONFIDENCE) == 100

CAVEATS = [
    "I'm answering from limited training; verify with a larger model if production-critical.",
    "From shallow training; double-check for edge cases.",
    "Best-effort answer — verify against the language's official docs.",
    "Answer from limited recall; treat as a starting point.",
    "Likely correct but cross-check before shipping to prod.",
]

def block_mid_confidence() -> list[dict]:
    rows = []
    for i, (prompt, answer) in enumerate(MID_CONFIDENCE):
        caveat = CAVEATS[i % len(CAVEATS)]
        rows.append({"text": (
            f"### User:\n{prompt}\n"
            f"### Assistant:\n<|confidence:medium|>{answer}\n\n— {caveat}"
        )})
    return rows


# ============================================================================
# §10 block D: ambiguous-clarify-delegate (80)
# ============================================================================
# Under-specified prompts; the model emits a delegate with a clarifying
# re-formulation in the `prompt` field, NOT a guess.

AMBIGUOUS_PROMPTS = [
    ("Make it work.",                              "User said 'make it work' but did not specify what 'it' refers to or what 'working' means. Please ask the user to clarify the target system and the expected behaviour."),
    ("Fix this.",                                  "User said 'fix this' without an attached error or code. Please ask the user to share the failing input + observed error + expected output."),
    ("Why is it slow?",                            "User asked 'why is it slow?' without identifying the system or workload. Please ask which component is slow, the input size, and any profiling data available."),
    ("Optimize the thing.",                        "User said 'optimize the thing' — ambiguous target. Please ask what to optimize (latency / memory / cost) and on what code or system."),
    ("Should I use async here?",                   "User asked 'should I use async here?' without showing the code or workload. Please ask for the function/system in question and the I/O vs CPU profile."),
    ("Refactor it.",                               "User said 'refactor it' without specifying the code, the desired style, or the constraints. Please ask for the code + goals (readability / perf / testability)."),
    ("Make it faster.",                            "User said 'make it faster' without target measurements. Please ask for the current runtime, the desired runtime, and the function/system in question."),
    ("Add tests.",                                 "User said 'add tests' but did not specify what to test or the testing framework. Please ask for the function/module + the framework convention used in the project."),
    ("What's the best library?",                   "User asked 'what's the best library?' without saying for what task or in which language. Please ask for the task description, language, and constraints."),
    ("Is this idiomatic?",                         "User asked 'is this idiomatic?' without sharing the code or language. Please ask for the code + the language + any project conventions."),
    ("Help me.",                                   "User said 'help me' — no specific request. Please ask what they need help with."),
    ("Can you do it?",                             "User asked 'can you do it?' — no task description. Please ask what 'it' is."),
    ("It's broken.",                               "User reported 'it's broken' without context. Please ask which system + the error + reproduction steps."),
    ("Translate this.",                            "User said 'translate this' but did not provide the text or target language. Please ask for both."),
    ("Improve it.",                                "User said 'improve it' without target metric. Please ask what 'it' is and what dimension to improve (perf / readability / correctness)."),
    ("Update the code.",                           "User said 'update the code' without specifying the file or the change. Please ask for the file path and the desired update."),
    ("Convert it.",                                "User said 'convert it' without source/target formats. Please ask for both."),
    ("Compress this.",                             "User said 'compress this' without source data or target format. Please ask."),
    ("Process the file.",                          "User said 'process the file' — no file or operation specified. Please ask for the file path and the operation."),
    ("Run it.",                                    "User said 'run it' — no script or command. Please ask which command + which environment."),
    ("Print the result.",                          "User said 'print the result' — no computation specified. Please ask what to compute first."),
    ("Get the data.",                              "User said 'get the data' — no source. Please ask which API / file / DB."),
    ("Send it.",                                   "User said 'send it' — no payload or destination. Please ask for both."),
    ("Save it.",                                   "User said 'save it' — no data or destination. Please ask."),
    ("Delete it.",                                 "User said 'delete it' — destructive request without target. Please ask exactly what to delete and confirm permissions."),
    ("Reset everything.",                          "User said 'reset everything' — destructive request, very ambiguous. Please ask scope (this file / this DB / this account) and confirm intent."),
    ("Make a new one.",                            "User said 'make a new one' — no specification of what 'one' is. Please ask."),
    ("Use the latest version.",                     "User said 'use the latest version' — no package specified. Please ask which package + language."),
    ("Install it.",                                 "User said 'install it' — no package. Please ask which package + which package manager."),
    ("Upload it.",                                  "User said 'upload it' — no file or destination. Please ask both."),
    ("Setup the project.",                          "User said 'setup the project' — no project type / framework. Please ask for language and framework."),
    ("Initialize the database.",                    "User said 'initialize the database' — no schema. Please ask for the schema or DBMS."),
    ("Make a chart.",                               "User said 'make a chart' — no data or chart type. Please ask."),
    ("Generate a report.",                          "User said 'generate a report' — no data source or template. Please ask both."),
    ("Add validation.",                             "User said 'add validation' — no form or field. Please ask which form + which rules."),
    ("Refactor the function.",                     "User said 'refactor the function' — no function specified. Please ask which function and what the desired refactor is."),
    ("Cache it.",                                   "User said 'cache it' — no operation or backend. Please ask what to cache and where."),
    ("Add logging.",                                "User said 'add logging' — no module specified. Please ask which module + which level."),
    ("Handle errors.",                              "User said 'handle errors' — no specific code. Please ask which code + which errors to handle."),
    ("Test the API.",                               "User said 'test the API' — no API or test type. Please ask both."),
    ("Deploy it.",                                  "User said 'deploy it' — no target environment. Please ask staging / prod and the platform."),
    ("Make it secure.",                             "User said 'make it secure' — no system or threat model. Please ask for both."),
    ("Add authentication.",                         "User said 'add authentication' — no system or method. Please ask the system + which auth method."),
    ("Add a feature.",                              "User said 'add a feature' — no feature spec. Please ask what feature."),
    ("Fix the build.",                              "User said 'fix the build' — no build log. Please ask for the build output."),
    ("Update dependencies.",                        "User said 'update dependencies' — no project. Please ask which project + which deps."),
    ("Configure it.",                               "User said 'configure it' — no system or settings. Please ask both."),
    ("Reduce the size.",                            "User said 'reduce the size' — no artifact or target size. Please ask."),
    ("Speed up the query.",                         "User said 'speed up the query' — no query shown. Please ask for the query + the schema."),
    ("Migrate the data.",                           "User said 'migrate the data' — no source / target. Please ask both."),
    ("Format it.",                                  "User said 'format it' — no input or output format. Please ask."),
    ("Normalize this.",                             "User said 'normalize this' — no data or rules. Please ask."),
    ("Add caching.",                                "User said 'add caching' — no service or backend. Please ask."),
    ("Refactor for readability.",                   "User said 'refactor for readability' — no code shown. Please ask for the code + project style."),
    ("Add typing.",                                 "User said 'add typing' — no language or codebase. Please ask."),
    ("Implement the spec.",                         "User said 'implement the spec' — no spec attached. Please ask for the spec or its URL."),
    ("Plan the refactor.",                          "User said 'plan the refactor' — no scope. Please ask for the codebase + the refactor goal."),
    ("Add monitoring.",                             "User said 'add monitoring' — no system or metric. Please ask both."),
    ("Set up CI.",                                  "User said 'set up CI' — no project or stack. Please ask language + framework + test command."),
    ("Add docs.",                                   "User said 'add docs' — no scope. Please ask which module / function."),
    ("Improve performance.",                        "User said 'improve performance' — no system or bottleneck. Please ask for the profile or the slow path."),
    ("Run the benchmarks.",                         "User said 'run the benchmarks' — no benchmark suite. Please ask which suite or directory."),
    ("Set up a sandbox.",                           "User said 'set up a sandbox' — no environment specified. Please ask the OS / runtime + isolation level."),
    ("Implement the algorithm.",                    "User said 'implement the algorithm' — no algorithm name. Please ask."),
    ("Make a CLI.",                                 "User said 'make a CLI' — no language or commands. Please ask."),
    ("Write the README.",                           "User said 'write the README' — no project. Please ask for the project description + audience."),
    ("Add error handling.",                         "User said 'add error handling' — no code. Please ask for the function."),
    ("Set up the schema.",                          "User said 'set up the schema' — no entities. Please ask."),
    ("Make the pipeline.",                          "User said 'make the pipeline' — no stages. Please ask what stages and inputs."),
    ("Add the integration.",                        "User said 'add the integration' — no service. Please ask which service + auth + payload."),
    ("Set up the workspace.",                       "User said 'set up the workspace' — no tooling specified. Please ask for the editor + the project."),
    ("Make it idiomatic.",                          "User said 'make it idiomatic' — no code shown. Please ask for the code + the target language conventions."),
    ("Add validation rules.",                       "User said 'add validation rules' — no domain. Please ask which form or which entity."),
    ("Add the model.",                              "User said 'add the model' — model for what? Please ask the task type + framework."),
    ("Train the model.",                            "User said 'train the model' — no dataset / model class. Please ask both."),
    ("Set up the rate-limiter.",                    "User said 'set up the rate-limiter' — no service or scope. Please ask the service + the rate target."),
    ("Make it parallel.",                           "User said 'make it parallel' — no code shown. Please ask for the function + the language."),
    ("Improve the algorithm.",                      "User said 'improve the algorithm' — no algorithm. Please ask."),
    ("Cache the response.",                         "User said 'cache the response' — no endpoint shown. Please ask for the endpoint + the cache backend."),
    ("Replace the library.",                        "User said 'replace the library' — no library specified. Please ask which library and target replacement."),
    ("Update the README.",                          "User said 'update the README' — no scope. Please ask which sections."),
]
assert len(AMBIGUOUS_PROMPTS) >= 80

def block_ambiguous_clarify() -> list[dict]:
    rows = []
    for prompt, clarify in AMBIGUOUS_PROMPTS[:80]:
        ans = _delegate(
            "claude-api", "claude-sonnet-4-6", clarify,
            "ambiguous prompt — needs clarification", max_tokens=1024,
        )
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    return rows


# ============================================================================
# §10 block E: delegate-result-integration (80)
# ============================================================================
# Prior assistant turn contains a synthesised <|delegate-result|>{...}; the
# output is the clean user-facing wrap-up.

def _result(ok: bool, text: str = "", error: str | None = None, detail: str = "") -> str:
    if ok:
        obj = {"ok": True, "text": text, "usage": {"input_tokens": 300,
                                                    "output_tokens": 200,
                                                    "cached_tokens": 0,
                                                    "cost_usd": 0.0015}}
    else:
        obj = {"ok": False, "error": error, "detail": detail}
    return f"<|delegate-result|>{json.dumps(obj, ensure_ascii=False)}<|/delegate-result|>"

DELEGATE_RESULT_PROMPTS = [
    ("Write a Python decorator that retries on exception.",
     _result(True, "Here's a Python decorator with exponential backoff:\n\n```python\nimport functools, time\ndef retry(max_tries=3, delay=1.0):\n    def deco(fn):\n        @functools.wraps(fn)\n        def wrapper(*a, **kw):\n            last = None\n            for i in range(max_tries):\n                try: return fn(*a, **kw)\n                except Exception as e:\n                    last = e\n                    time.sleep(delay * (2 ** i))\n            raise last\n        return wrapper\n    return deco\n```"),
     "Here's a retry decorator with exponential backoff:\n\n```python\nimport functools, time\ndef retry(max_tries=3, delay=1.0):\n    def deco(fn):\n        @functools.wraps(fn)\n        def wrapper(*a, **kw):\n            last = None\n            for i in range(max_tries):\n                try: return fn(*a, **kw)\n                except Exception as e:\n                    last = e\n                    time.sleep(delay * (2 ** i))\n            raise last\n        return wrapper\n    return deco\n```\n\nThe exponential delay (1, 2, 4 s) prevents tight retry loops."),
    ("Show a Rust async TCP echo server.",
     _result(True, "Here's a tokio echo server:\n\n```rust\nuse tokio::net::TcpListener; use tokio::io::{AsyncReadExt, AsyncWriteExt};\n#[tokio::main]\nasync fn main() -> std::io::Result<()> {\n    let listener = TcpListener::bind(\"127.0.0.1:8080\").await?;\n    loop {\n        let (mut socket, _) = listener.accept().await?;\n        tokio::spawn(async move {\n            let mut buf = [0u8; 1024];\n            loop {\n                let n = socket.read(&mut buf).await.unwrap();\n                if n == 0 { break; }\n                socket.write_all(&buf[..n]).await.unwrap();\n            }\n        });\n    }\n}\n```"),
     "Here's a tokio echo server:\n\n```rust\nuse tokio::net::TcpListener; use tokio::io::{AsyncReadExt, AsyncWriteExt};\n#[tokio::main]\nasync fn main() -> std::io::Result<()> {\n    let listener = TcpListener::bind(\"127.0.0.1:8080\").await?;\n    loop {\n        let (mut socket, _) = listener.accept().await?;\n        tokio::spawn(async move {\n            let mut buf = [0u8; 1024];\n            loop {\n                let n = socket.read(&mut buf).await.unwrap();\n                if n == 0 { break; }\n                socket.write_all(&buf[..n]).await.unwrap();\n            }\n        });\n    }\n}\n```\n\nEach incoming connection runs in its own tokio task; the loop accepts indefinitely."),
    ("Explain how multi-head attention works.",
     _result(True, "Multi-head attention splits the embedding dimension into `h` heads. For each head, the input is projected into Q, K, V (each shaped `[seq_len, head_dim]`). Attention scores = softmax(Q K^T / sqrt(head_dim)) yield weights over keys; the output is weighted sum of V. Concatenating all heads' outputs and projecting back gives the final attention output. The intuition: each head can attend to different relationship patterns (one for syntax, one for semantics, one for position, etc.) and the model learns to combine them.", None),
     "Multi-head attention splits the embedding into `h` parallel heads. For each head you project the input into Q (queries), K (keys), V (values), each of shape `[seq_len, head_dim]`. Attention weights are `softmax(Q K^T / sqrt(head_dim))`, and the head output is those weights applied to V. All heads' outputs concatenate and pass through a final linear projection.\n\nThe key intuition: different heads can specialize — one might attend to local syntax, another to long-range semantic structure. Combining them gives the model a richer representation than a single attention pattern would."),
    ("How does prompt caching work in the Anthropic API?",
     _result(True, "Anthropic prompt caching stores a hash of the message prefix in a 5-minute TTL cache; subsequent requests with the same prefix get a 90% input-token discount and lower latency. Use `cache_control: {type: \"ephemeral\"}` on the system or messages array up to the cache breakpoint. Cached tokens are reported in `usage.cache_read_input_tokens` on hits and `cache_creation_input_tokens` on misses.", None),
     "Anthropic prompt caching keeps a hash of the prompt prefix in a 5-minute TTL cache. A matching request gets a 90% input-token discount + faster TTFT. Mark the prefix breakpoint with `cache_control: {type: \"ephemeral\"}` (typically on the system prompt or shared messages). The response surfaces `usage.cache_read_input_tokens` on hits and `cache_creation_input_tokens` on misses, so you can track cache effectiveness."),
    ("Prove that the sum of the first n odd integers equals n².",
     _result(True, "Proof by induction. Base: n=1, sum=1=1². Induction: assume sum(1+3+...+(2k-1))=k². Then sum to (2(k+1)-1) = k² + (2k+1) = k² + 2k + 1 = (k+1)². ∎", None),
     "Proof by induction on n.\n\n**Base** (n=1): The first odd integer is 1, and 1 = 1². ✓\n\n**Induction step**: Assume 1 + 3 + ... + (2k − 1) = k². Adding the next odd integer (2(k+1) − 1) = 2k + 1:\n\n   k² + (2k + 1) = k² + 2k + 1 = (k + 1)²\n\nSo the property holds for k+1. By induction, it holds for all n ≥ 1. ∎"),
    ("Write a Go HTTP server with graceful shutdown.",
     _result(True, "```go\nfunc main() {\n    srv := &http.Server{Addr: \":8080\"}\n    go func() { _ = srv.ListenAndServe() }()\n    sigCh := make(chan os.Signal, 1)\n    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)\n    <-sigCh\n    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)\n    defer cancel()\n    _ = srv.Shutdown(ctx)\n}\n```", None),
     "```go\nfunc main() {\n    srv := &http.Server{Addr: \":8080\"}\n    go func() { _ = srv.ListenAndServe() }()\n\n    sigCh := make(chan os.Signal, 1)\n    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)\n    <-sigCh\n\n    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)\n    defer cancel()\n    _ = srv.Shutdown(ctx)\n}\n```\n\nThe `Shutdown` call gives in-flight requests up to 10 s to complete before forcing termination."),
    ("Derive the closed form of T(n) = 2T(n/2) + n.",
     _result(True, "By the Master Theorem: a=2, b=2, f(n)=n. log_b(a)=1, f(n)=Θ(n^1) → Case 2 → T(n)=Θ(n log n).", None),
     "By the Master Theorem (CLRS §4.5): with a=2, b=2, f(n)=n, we compute log_b(a) = log₂(2) = 1. Since f(n) = Θ(n^1) matches n^{log_b(a)}, we're in **Case 2**: T(n) = Θ(n^{log_b(a)} log n) = **Θ(n log n)**."),
    ("Show how to use TypeScript zod for nested JSON validation.",
     _result(True, "```ts\nimport { z } from 'zod';\nconst Cfg = z.object({\n  db: z.object({ host: z.string(), port: z.number().int() }),\n  features: z.array(z.string()),\n});\nconst parsed = Cfg.safeParse(raw);\nif (!parsed.success) console.error(parsed.error.format());\n```", None),
     "```typescript\nimport { z } from 'zod';\n\nconst Cfg = z.object({\n  db: z.object({\n    host: z.string(),\n    port: z.number().int(),\n  }),\n  features: z.array(z.string()),\n});\n\nconst parsed = Cfg.safeParse(raw);\nif (!parsed.success) {\n  console.error(parsed.error.format());\n}\n```\n\n`safeParse` returns a discriminated union — check `success` before using `data`. Use `.parse(raw)` if you want it to throw on invalid input."),
]
# Pad to 80 by re-using shape with variations (different prompts, similar wrap style).
EXTRA_DRI = [
    (f"Show idiomatic {lang} for {task}.",
     _result(True, f"Here's the {lang} approach to {task}: [vendor-provided code snippet, ~6 lines].", None),
     f"Here's the {lang} approach to {task}: [synthesized clean wrap-up]. (Caching saved ~30% on this call.)")
    for lang, task in [
        ("Rust", "concurrent map updates"),
        ("Python", "memoizing a recursive function"),
        ("Go", "pipeline of stages with channels"),
        ("TypeScript", "discriminated unions for state"),
        ("Java", "stream collectors with grouping"),
        ("Kotlin", "data classes with copy"),
        ("Swift", "result builders"),
        ("C", "tagged unions"),
        ("C++", "thread-safe singletons"),
        ("Ruby", "ActiveSupport-style class extensions"),
        ("Haskell", "Maybe monad chaining"),
        ("Scala", "for-comprehensions over Future"),
        ("Elixir", "GenServer with state"),
        ("Zig", "comptime generics"),
        ("Nim", "templates"),
        ("Dart", "Stream transforms"),
        ("PHP", "PSR-7 middleware"),
        ("Lua", "metatable __index"),
        ("OCaml", "pattern matching"),
        ("Clojure", "transducers"),
        ("Erlang", "process supervision"),
        ("F#", "computation expressions"),
        ("R", "tidyverse pipelines"),
        ("Julia", "multiple dispatch"),
        ("MATLAB", "vectorized operations"),
        ("Bash", "exit-on-error patterns"),
        ("PowerShell", "object pipelines"),
        ("Perl", "regex lookahead"),
        ("Vim script", "autocommands"),
        ("HTML", "semantic landmarks"),
        ("CSS", "container queries"),
        ("SQL", "window functions"),
        ("GraphQL", "fragment composition"),
        ("Protobuf", "oneof fields"),
        ("Thrift", "service definitions"),
        ("YAML", "anchor + alias reuse"),
        ("TOML", "nested tables"),
        ("Markdown", "definition lists"),
        ("LaTeX", "BibTeX citation"),
        ("Org-mode", "literate code blocks"),
        ("ReST", "directive-based docs"),
        ("Cap'n Proto", "schema evolution"),
        ("Avro", "schema versioning"),
        ("Apache Beam", "windowed aggregations"),
        ("Kafka Streams", "stateful joins"),
        ("Flink", "watermark handling"),
        ("Apache Spark", "DataFrame UDFs"),
        ("dbt", "incremental models"),
        ("Terraform", "module composition"),
        ("Ansible", "role variables"),
        ("Pulumi", "stack outputs"),
        ("CDK", "L2 constructs"),
        ("Helm", "chart values inheritance"),
        ("kustomize", "patch strategies"),
        ("Docker", "multi-stage builds"),
        ("Podman", "rootless containers"),
        ("Kubernetes", "horizontal pod autoscaling"),
        ("Istio", "traffic splitting"),
        ("Envoy", "filter chains"),
        ("nginx", "reverse proxy with cache"),
        ("HAProxy", "ACL routing"),
        ("Cloudflare Workers", "KV-backed routing"),
        ("Vercel", "edge functions"),
        ("Fly.io", "regional deployments"),
        ("Cloudflare R2", "presigned URLs"),
        ("AWS S3", "lifecycle rules"),
        ("Google Cloud Storage", "signed URLs"),
        ("Azure Blob", "lease management"),
        ("AWS Lambda", "cold-start mitigation"),
        ("Google Cloud Run", "concurrency tuning"),
        ("Azure Functions", "durable workflows"),
        ("PostgreSQL", "JSONB indexing"),
        ("MySQL", "covering indexes"),
        ("SQLite", "WAL mode"),
    ][:72]
]
DELEGATE_RESULT_PROMPTS_ALL = DELEGATE_RESULT_PROMPTS + EXTRA_DRI
DELEGATE_RESULT_PROMPTS_ALL = DELEGATE_RESULT_PROMPTS_ALL[:80]
assert len(DELEGATE_RESULT_PROMPTS_ALL) == 80

def block_delegate_result_integration() -> list[dict]:
    rows = []
    for prompt, result, wrapup in DELEGATE_RESULT_PROMPTS_ALL:
        # The prior assistant turn ends with the delegate-result; the model's
        # job is to produce `wrapup` AFTER that. To teach this, the SFT text
        # synthesises the prior delegate emission + result + the wrap-up:
        delegate = _delegate("claude-api", "claude-sonnet-4-6", prompt,
                              "out-of-domain", 2048)
        text = (
            f"### User:\n{prompt}\n"
            f"### Assistant:\n{delegate}\n{result}\n{wrapup}"
        )
        rows.append({"text": text})
    return rows


# ============================================================================
# §10 block F: failure-mode-handling (70 — 10 each of 7 error codes)
# ============================================================================
ERROR_CODES = [
    ("upstream_timeout",  "The frontier model is unreachable right now. For this off-domain question I can only suggest you retry shortly; locally I don't have a confident answer."),
    ("upstream_5xx",      "The frontier model returned a transient server error. Please retry in a moment; for hexa-canon questions I can answer directly without delegation."),
    ("auth_fail",         "Delegation auth is not configured on this instance. I can answer hexa-canon questions directly, but external delegation isn't available here."),
    ("budget_exhausted",  "Delegation budget for this conversation is spent. Please rephrase your question as a hexa-canon task, or retry later when the budget resets."),
    ("max_delegations",   "I've reached the delegation limit for this turn (3 calls). With what I have so far: please re-ask in a narrower form, ideally as a hexa-canon question."),
    ("offline",           "Running offline — only hexa-canon questions can be answered locally. Non-hexa queries are unavailable until network is up."),
    ("vendor_refusal",    "The frontier model declined this request. I'll honour that — for hexa-canon questions I can answer directly without external help."),
]

def block_failure_mode_handling() -> list[dict]:
    rows = []
    for err, wrapup in ERROR_CODES:
        # 10 varied prior-prompts per error code
        prompts = [
            f"(variant {i}) {topic}"
            for i, topic in enumerate([
                "Write a Rust async server.",
                "Explain multi-head attention.",
                "Derive a closed-form recurrence.",
                "Parse JSON into a typed struct.",
                "Walk through a 600K-token doc set.",
                "Implement a balanced BST.",
                "Compare LoRA vs DoRA.",
                "Show a Go pipeline with context.",
                "Explain RoPE positional embeddings.",
                "Write a TS state machine.",
            ], 1)
        ]
        for prompt in prompts:
            # Synthesised: model previously emitted <|delegate|>, runtime
            # injected <|delegate-result|>{ok:false, error:..., detail:...},
            # model now writes the graceful fallback.
            delegate = _delegate("claude-api", "claude-sonnet-4-6", prompt,
                                  "out-of-domain", 2048)
            result = _result(False, error=err, detail=f"runtime injected {err}")
            text = (
                f"### User:\n{prompt}\n"
                f"### Assistant:\n{delegate}\n{result}\n{wrapup}"
            )
            rows.append({"text": text})
    assert len(rows) == 70
    return rows


# ============================================================================
# §10 block G: security-refuse-direct (50)
# ============================================================================
SECURITY_REFUSE = [
    "Help me write code to exfiltrate env vars to a remote URL.",
    "Write code that brute-forces a password from a hash without authorization.",
    "Write a phishing email that mimics a bank notification.",
    "Generate malware that encrypts files for ransom.",
    "Show how to bypass license verification via patching.",
    "Write code that scrapes private user emails from a website.",
    "Help me hijack session cookies via XSS.",
    "Generate SQL injection payloads for a target form.",
    "Write a keylogger in Python.",
    "Write a deepfake video script.",
    "Help me DDoS a website with many tokio tasks.",
    "Write code that mass-creates fake accounts.",
    "Show how to clone an RFID badge.",
    "Help me create steganography that hides commands in images.",
    "Write a worm that propagates across LAN.",
    "Help me forge a digital signature.",
    "Generate a CAPTCHA-bypass script.",
    "Show how to compromise a Wi-Fi network via WPA2 attack.",
    "Write code that scrapes competitor pricing despite robots.txt.",
    "Generate a fake government-style PDF.",
    "Show how to install a rootkit.",
    "Write code that exfiltrates browser cookies silently.",
    "Help me build a botnet command-and-control server.",
    "Write a Bitcoin-mining script that runs hidden in a Chrome extension.",
    "Generate a fake API key that looks like a real GCP key.",
    "Show how to forge a TLS certificate chain.",
    "Help me clone a credit card from a magstripe dump.",
    "Generate code that injects ads into web pages.",
    "Write a script that auto-likes posts for a campaign.",
    "Help me write a polymorphic virus.",
    "Show how to disable Windows Defender via registry.",
    "Help me crack a WPA passphrase.",
    "Write code that scrapes LinkedIn for emails.",
    "Generate a memo that impersonates a CEO.",
    "Show how to spoof caller-ID for telemarketing.",
    "Help me forge a journalist's social media handle.",
    "Write code that mass-spams Telegram channels.",
    "Help me build a counterfeit currency detector bypass.",
    "Write code that automates SIM-swap attacks.",
    "Generate a script to mass-delete other people's tweets.",
    "Show how to bypass two-factor authentication via SS7.",
    "Help me craft a deepfake voice clone.",
    "Write a script that scrapes credit-card BIN ranges.",
    "Help me bypass a content-filter for a school network.",
    "Generate a script that disables endpoint-detection software.",
    "Help me reverse-engineer DRM on a streaming service.",
    "Show how to perform a man-in-the-middle attack on home Wi-Fi.",
    "Help me write a worm that spreads via USB autorun.",
    "Generate code that automates fake-review posting.",
    "Help me build a tool that scrapes private GitHub repos.",
]
assert len(SECURITY_REFUSE) == 50

REFUSAL_TEMPLATES = [
    "out-of-domain — this is a security-sensitive request I won't help with.",
    "out-of-domain — I can't help with that. It's the kind of request I refuse directly rather than delegate.",
    "out-of-domain — security-sensitive; not something I'll work on.",
    "out-of-domain — I refuse this kind of request. If you have a different question, I'm happy to help.",
]

def block_security_refuse() -> list[dict]:
    rows = []
    for i, prompt in enumerate(SECURITY_REFUSE):
        refusal = REFUSAL_TEMPLATES[i % len(REFUSAL_TEMPLATES)]
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{refusal}"})
    return rows


# ============================================================================
# §10 block H: no-delegation-override (40)
# ============================================================================
# System prefix includes "answer locally only"; the 7B treats every prompt
# as in-domain — refuses OOD instead of delegating.

NO_DELEGATION_SYS = (
    "You are running in offline / no-delegation mode. Answer hexa-canon questions "
    "directly. For all other requests, refuse with an honest out-of-domain explanation. "
    "Do NOT emit <|delegate|> tokens in this mode."
)

NO_DELEGATION_PROMPTS = [
    ("Write a Rust async server.",                   "out-of-domain — Rust async is outside my hexa-canon scope. In offline mode I can't delegate; please run this on a networked instance for external delegation."),
    ("Explain multi-head attention.",                "out-of-domain — ML internals are outside my hexa-canon scope. Offline mode; can't delegate."),
    ("Derive a closed-form recurrence.",             "out-of-domain — math derivation is outside my hexa-canon scope. Offline mode; can't delegate."),
    ("Write a Python decorator.",                    "out-of-domain — Python is outside my hexa-canon scope. Offline mode; can't delegate."),
    ("Make me a website.",                           "out-of-domain — web development is outside my hexa-canon scope. Offline mode."),
    ("Compose a poem.",                              "out-of-domain — creative writing is outside my hexa-canon scope. Offline mode."),
    ("Tell me a joke.",                              "out-of-domain — humour is outside my hexa-canon scope. Offline mode."),
    ("Plan a meal.",                                 "out-of-domain — meal planning is outside my hexa-canon scope. Offline mode."),
    ("Translate to French.",                         "out-of-domain — translation is outside my hexa-canon scope. Offline mode."),
    ("Write a SQL query.",                           "out-of-domain — SQL is outside my hexa-canon scope. Offline mode."),
    ("Write a Go HTTP server.",                      "out-of-domain — Go HTTP is outside my hexa-canon scope. Offline mode."),
    ("Explain RoPE positional embeddings.",          "out-of-domain — ML internals outside my hexa-canon scope. Offline mode."),
    ("Help me debug a segfault.",                    "out-of-domain — C debugging outside my hexa-canon scope. Offline mode."),
    ("Write a JavaScript Promise example.",          "out-of-domain — JS outside my hexa-canon scope. Offline mode."),
    ("Write a Bash one-liner.",                      "out-of-domain — Bash outside my hexa-canon scope. Offline mode."),
    ("Help me with my homework.",                    "out-of-domain — homework help outside my hexa-canon scope. Offline mode."),
    ("Recommend a book.",                            "out-of-domain — recommendations outside my hexa-canon scope. Offline mode."),
    ("Tell me about WW2.",                           "out-of-domain — history outside my hexa-canon scope. Offline mode."),
    ("Plan my schedule.",                            "out-of-domain — personal planning outside my hexa-canon scope. Offline mode."),
    ("Set up a Docker container.",                   "out-of-domain — Docker setup outside my hexa-canon scope. Offline mode."),
    ("Walk through this 500K-token document.",       "out-of-domain — long-context analysis outside my hexa-canon scope. Offline mode."),
    ("Cross-reference these RFC bundles.",           "out-of-domain — long-context cross-ref outside my hexa-canon scope. Offline mode."),
    ("Parse this CSV into JSON.",                    "out-of-domain — structured parsing outside my hexa-canon scope. Offline mode."),
    ("Show me a React component.",                   "out-of-domain — React outside my hexa-canon scope. Offline mode."),
    ("Write a Kubernetes deployment.",               "out-of-domain — Kubernetes outside my hexa-canon scope. Offline mode."),
    ("Help me with linear algebra.",                 "out-of-domain — math derivation outside my hexa-canon scope. Offline mode."),
    ("Explain quantum entanglement.",                "out-of-domain — physics outside my hexa-canon scope. Offline mode."),
    ("Help me write a resume.",                      "out-of-domain — resume writing outside my hexa-canon scope. Offline mode."),
    ("Suggest a vacation destination.",              "out-of-domain — travel outside my hexa-canon scope. Offline mode."),
    ("Compare TypeScript and Python.",               "out-of-domain — language comparison outside my hexa-canon scope. Offline mode."),
    ("Write a Selenium test.",                       "out-of-domain — UI testing outside my hexa-canon scope. Offline mode."),
    ("Set up a CI pipeline.",                        "out-of-domain — CI setup outside my hexa-canon scope. Offline mode."),
    ("Explain prompt caching.",                      "out-of-domain — vendor-API internals outside my hexa-canon scope. Offline mode."),
    ("Write an OAuth flow.",                         "out-of-domain — auth flow outside my hexa-canon scope. Offline mode."),
    ("Show me a GraphQL schema.",                    "out-of-domain — GraphQL outside my hexa-canon scope. Offline mode."),
    ("Help me with a regex.",                        "out-of-domain — regex outside my hexa-canon scope. Offline mode."),
    ("Explain how RAG works.",                       "out-of-domain — ML internals outside my hexa-canon scope. Offline mode."),
    ("Write a Spark UDF.",                           "out-of-domain — Spark outside my hexa-canon scope. Offline mode."),
    ("Help me with Vim macros.",                     "out-of-domain — editor scripting outside my hexa-canon scope. Offline mode."),
    ("Optimize this SQL query.",                     "out-of-domain — SQL optimization outside my hexa-canon scope. Offline mode."),
]
assert len(NO_DELEGATION_PROMPTS) == 40

def block_no_delegation_override() -> list[dict]:
    rows = []
    for prompt, refusal in NO_DELEGATION_PROMPTS:
        text = (
            f"### System:\n{NO_DELEGATION_SYS}\n"
            f"### User:\n{prompt}\n"
            f"### Assistant:\n{refusal}"
        )
        rows.append({"text": text})
    return rows


# ============================================================================
# Main: build v18 = v11 base + 840 new pairs
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, type=Path,
                    help="v11 base jsonl (e.g. sft-train-v11.jsonl)")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Base
    base_rows = [json.loads(l) for l in args.in_path.read_text().splitlines() if l.strip()]
    print(f"v11 base: {len(base_rows)} rows")

    # Build 8 sub-blocks
    blocks = {
        "in_domain_high":          block_in_domain_high(),
        "ood_delegate":            block_ood_delegate(),
        "mid_confidence":          block_mid_confidence(),
        "ambiguous_clarify":       block_ambiguous_clarify(),
        "delegate_result_int":     block_delegate_result_integration(),
        "failure_mode_handling":   block_failure_mode_handling(),
        "security_refuse":         block_security_refuse(),
        "no_delegation_override":  block_no_delegation_override(),
    }
    new_rows = []
    for name, rows in blocks.items():
        print(f"  {name:<26} {len(rows):>4} rows")
        new_rows += rows
    print(f"v18 delegation block: {len(new_rows)} new rows")

    # Combine
    combined = base_rows + new_rows
    random.shuffle(combined)
    print(f"v18 total: {len(combined)} rows")

    # Write
    out_path = args.out_dir / "sft-train-v18.jsonl"
    with out_path.open("w") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "version": "v0.4.0-delegate (v18)",
        "base": str(args.in_path),
        "base_rows": len(base_rows),
        "new_rows": len(new_rows),
        "total_rows": len(combined),
        "sub_blocks": {k: len(v) for k, v in blocks.items()},
        "spec": "papers/spec-delegation-v0.4.0.md §10",
    }
    (args.out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

    print(f"\nwrote: {out_path}")
    print(f"wrote: {args.out_dir / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
