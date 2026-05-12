#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""gen_hexa_eval_mk1.py — generate the hexa-eval Mk.I task manifest (~750 tasks).

The Mk.0.1 starter (`eval/hexa-eval/manifest.jsonl`, 28 tasks) is too small to
give a stable gate-③ signal — per-family generation variance is ±33 pp. Mk.I
expands each of the 8 families to ~80-100 tasks with real template diversity
(not 90 copies of one template), so the family scores are stable.

Output: eval/hexa-eval/manifest-mk1.jsonl

Schema (one JSON object per line, same as Mk.0.1):
  task_id      str   "HEXA-T1-0001" ...
  family       str   T1..T8
  spec_anchor  str   pointer into the hexa spec
  prompt       str   the test prompt
  gold_pattern str   reference answer / fragment (semantics depend on scorer)
  scorer       str   s0_s1_exit_0 | ast_equality | annotation_match
                     | byte_exact_subset | exact_match | yes_no_match
  tags         list  optional

Scorer semantics (must match tool/score_mk0_eval.py / the strict scorer):
  s0_s1_exit_0 / ast_equality : the model's output must compile under hexa-cc
                                 (strict scorer; substring fallback wants gold in output)
  annotation_match            : gold annotation string must appear in output
  byte_exact_subset           : gold byte-string must appear in output
  exact_match                 : gold must equal / appear-in the (stripped) output
  yes_no_match                : first yes/no/refuse/accept token in output == gold
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

OUT = Path(_THIS_DIR).parent / "eval" / "hexa-eval" / "manifest-mk1.jsonl"

rows: list[dict] = []
_ctr = {}


def add(family: str, spec: str, prompt: str, gold: str, scorer: str, tags=None):
    _ctr[family] = _ctr.get(family, 0) + 1
    rows.append({
        "task_id": f"HEXA-{family}-{_ctr[family]:04d}",
        "family": family,
        "spec_anchor": spec,
        "prompt": prompt,
        "gold_pattern": gold,
        "scorer": scorer,
        "tags": tags or [],
    })


# ===========================================================================
# T1 — lexical + grammar (compile-checked)  ~110
# ===========================================================================
T1_SPEC = "§3 lexical + grammar"
# functions: varied param types / return types / bodies
INT_TYPES = ["i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize"]
FN_FORMS = [
    ("add", "a: {t}, b: {t}", "{t}", "a + b"),
    ("sub", "a: {t}, b: {t}", "{t}", "a - b"),
    ("mul", "a: {t}, b: {t}", "{t}", "a * b"),
    ("max2", "a: {t}, b: {t}", "{t}", "if a > b { a } else { b }"),
    ("min2", "a: {t}, b: {t}", "{t}", "if a < b { a } else { b }"),
    ("square", "n: {t}", "{t}", "n * n"),
    ("double", "n: {t}", "{t}", "n + n"),
    ("is_zero", "n: {t}", "bool", "n == 0"),
    ("clamp_lo", "n: {t}, lo: {t}", "{t}", "if n < lo { lo } else { n }"),
    ("abs_diff", "a: {t}, b: {t}", "{t}", "if a > b { a - b } else { b - a }"),
]
for name, params, ret, body in FN_FORMS:
    for t in random.sample(INT_TYPES, 4):
        p = params.format(t=t)
        r = ret.format(t=t)
        b = body
        sig = f"fn {name}(p: ...) -> {r}"  # not used for compile, just descriptive
        gold = f"fn {name}({p}) -> {r}"
        add("T1", T1_SPEC,
            f"Write a hexa function `{name}({p}) -> {r}` whose body is `{b}`.",
            gold, "s0_s1_exit_0", ["syntax", "fn"])
# const bindings
for nm, ty, val in [("MAX", "u32", "1024"), ("MIN", "i32", "-1"), ("PI_X100", "u32", "314"),
                    ("PAGE", "usize", "4096"), ("LIMIT", "u64", "1000000"), ("EPS", "f32", "0.001"),
                    ("NAME_LEN", "u8", "32"), ("RETRIES", "u8", "3"), ("MASK", "u32", "255"),
                    ("HALF", "f64", "0.5")]:
    add("T1", T1_SPEC, f"Declare an immutable hexa binding `{nm}: {ty} = {val}`.",
        f"const {nm}: {ty} = {val}", "s0_s1_exit_0", ["syntax", "const"])
# let bindings inside a fn
for nm, expr in [("x", "1 + 2"), ("y", "a * 3"), ("flag", "n > 0"), ("total", "len(v)"),
                 ("scaled", "k << 2"), ("masked", "b & 0xFF"), ("avg", "(a + b) / 2"),
                 ("neg", "0 - n")]:
    add("T1", T1_SPEC, f"Inside a hexa function, write a `let` binding `{nm} = {expr};`.",
        f"let {nm} = {expr}", "s0_s1_exit_0", ["syntax", "let"])
# struct declarations
for nm, fields in [("Point", "x: f32, y: f32"), ("Rect", "w: u32, h: u32"),
                   ("Color", "r: u8, g: u8, b: u8"), ("Range", "lo: i64, hi: i64"),
                   ("Vec3", "x: f64, y: f64, z: f64"), ("Header", "magic: u32, len: u32"),
                   ("Entry", "key: u64, val: u64"), ("Span", "start: usize, end: usize"),
                   ("Pixel", "rgba: u32"), ("Pair", "a: i32, b: i32")]:
    add("T1", T1_SPEC, f"Declare a hexa struct `{nm}` with fields `{fields}`.",
        f"struct {nm}", "s0_s1_exit_0", ["syntax", "struct"])
# expressions
for e in ["len(v) * 2 + 1", "(a + b) * (a - b)", "n & (n - 1)", "x << 3 | 1", "(p + 7) / 8 * 8",
          "if c { 1 } else { 0 }", "a % 16", "hi - lo + 1", "k * k * k", "(w + 1) * (h + 1)"]:
    add("T1", T1_SPEC, f"Write the hexa expression `{e}` as a function body returning its value.",
        e, "s0_s1_exit_0", ["syntax", "expr"])
# match / if
add("T1", T1_SPEC, "Write a hexa function `sign(n: i32) -> i32` returning -1, 0, or 1 using `if`/`else if`/`else`.",
    "fn sign(n: i32) -> i32", "s0_s1_exit_0", ["syntax", "if"])
add("T1", T1_SPEC, "Write a hexa function `classify(n: i32) -> u8` using a `match` on whether n is 0, 1, or other.",
    "match", "s0_s1_exit_0", ["syntax", "match"])
add("T1", T1_SPEC, "Write a hexa `loop` that increments a `let mut i = 0;` until `i == 10`, then `break`.",
    "loop", "s0_s1_exit_0", ["syntax", "loop"])
add("T1", T1_SPEC, "Write a hexa `while i < n { i = i + 1; }` loop body around `let mut i = 0;`.",
    "while", "s0_s1_exit_0", ["syntax", "while"])
add("T1", T1_SPEC, "Write a hexa `for x in 0..n { ... }` loop that sums into `let mut s = 0;`.",
    "for", "s0_s1_exit_0", ["syntax", "for"])
# generics
for nm, body in [("id", "fn id<T>(x: T) -> T { x }"), ("first2", "fn first2<T>(a: T, b: T) -> T { a }")]:
    add("T1", T1_SPEC, f"Write a generic hexa function `{nm}` — declaration: `{body}`.",
        nm, "s0_s1_exit_0", ["syntax", "generic"])

# ===========================================================================
# T2 — atlas L[N] annotations  ~100
# ===========================================================================
T2_SPEC = "§atlas L-anchoring"
PROVE_VERBS = ["proves", "PROVES", "establishes", "demonstrates", "shows", "confirms", "verifies", "validates"]
EXPLORE_VERBS = ["EXPLORES", "discovers", "searches for", "hunts", "probes", "looks for", "scans for", "seeks"]
for _ in range(50):
    n = random.randint(1, 600)
    v = random.choice(PROVE_VERBS)
    style = random.randint(0, 2)
    if style == 0:
        prompt = f"Annotate a hexa function `prove_{n}` that {v} law `L[{n}]`."
    elif style == 1:
        prompt = f"A hexa function {v} `L[{n}]`. Which annotation does it carry — `@implements(L[{n}])` or `@discover(kind=\"L\")`? Write it."
    else:
        prompt = f"Write the correct hexa annotation for a function whose docstring says it {v} `L[{n}]`."
    add("T2", T2_SPEC, prompt, f"@implements(L[{n}])", "annotation_match", ["atlas", "implements"])
for _ in range(50):
    n = random.randint(1, 600)
    v = random.choice(EXPLORE_VERBS)
    style = random.randint(0, 2)
    if style == 0:
        prompt = f"Annotate a hexa function `explore_{n}` that {v} new instances of law `L[{n}]`."
    elif style == 1:
        prompt = f"A hexa function {v} new instances under `L[{n}]`. Write its annotation — `@implements(L[{n}])` or `@discover(kind=\"L\")`?"
    else:
        prompt = f"Write the correct hexa annotation for a function whose docstring says it {v} undiscovered cases of `L[{n}]`."
    add("T2", T2_SPEC, prompt, '@discover(kind="L")', "annotation_match", ["atlas", "discover"])

# ===========================================================================
# T3 — @grace deprecation annotations  ~80
# ===========================================================================
T3_SPEC = "§deprecation @grace"
GRACE_FNS = ["old_api", "legacy_format", "v1_parser", "deprecated_alloc", "old_codec",
             "legacy_hash", "v0_serialize", "old_lexer", "stale_cache", "v1_resolver",
             "old_linker", "legacy_emit", "v0_tokenize", "old_diff", "stale_index"]
GRACE_DATES = ["2026-06-30", "2026-09-01", "2026-12-31", "2027-01-01", "2027-03-31", "2027-06-30"]
GRACE_REASONS = ["replaced by new builder", "obsolete format", "superseded by v2 API", "removed in RFC-021",
                 "merged into stdlib core", "no longer maintained", "replaced by atlas L-anchoring",
                 "superseded by the typed variant"]
for i in range(80):
    fn = GRACE_FNS[i % len(GRACE_FNS)]
    code = f"HX9{random.randint(1, 999):03d}"
    date = random.choice(GRACE_DATES)
    reason = random.choice(GRACE_REASONS)
    style = i % 3
    if style == 0:
        prompt = f"Mark the hexa function `{fn}()` deprecated with `@grace`: code `{code}`, remove-by `{date}`, reason \"{reason}\"."
    elif style == 1:
        prompt = f"Add `@grace` to `{fn}()` — `{code}`, until `{date}`, reason \"{reason}\"."
    else:
        prompt = f"Write the `@grace` annotation for `{fn}()` that triggers `{code}`, should be gone by `{date}`, because it was {reason}."
    add("T3", T3_SPEC, prompt, f'@grace({code}, until={date}, reason="{reason}")', "byte_exact_subset", ["grace"])

# ===========================================================================
# T4 — RFC-020 enum syntax (compile-checked)  ~95
# ===========================================================================
T4_SPEC = "§RFC-020 enum"
ENUMS = [
    ("Color", "Red, Green, Blue", "no payload"),
    ("Direction", "North, South, East, West", "no payload"),
    ("Status", "Idle, Running, Done, Error", "no payload"),
    ("Priority", "Low, Normal, High, Critical", "no payload"),
    ("LogLevel", "Trace, Debug, Info, Warn, Error", "no payload"),
    ("Suit", "Clubs, Diamonds, Hearts, Spades", "no payload"),
    ("Op", "Add, Sub, Mul, Div", "no payload"),
    ("Visibility", "Public, Private, Internal", "no payload"),
    ("Endian", "Little, Big", "no payload"),
    ("Phase", "Setup, Run, Teardown", "no payload"),
    ("Maybe<T>", "None, Some(T)", "single-field payload on Some"),
    ("Option<T>", "None, Some(T)", "single-field payload on Some"),
    ("Result<T>", "Ok(T), Err(String)", "payload on both"),
    ("Either<E, T>", "Err(E), Ok(T)", "payload on both"),
    ("Pair<A, B>", "Two(A, B)", "two-field payload"),
    ("Triple<A, B, C>", "Three(A, B, C)", "three-field payload"),
    ("Validated<T>", "Valid(T), Invalid(Vec<String>)", "payload on both"),
    ("Shape", "Circle(f64), Square(f64), Rect(f64, f64)", "mixed payloads"),
    ("Token", "Ident(String), Int(i64), Punct(char), Eof", "mixed payloads + unit variant"),
    ("Json", "Null, Bool(bool), Num(f64), Str(String)", "mixed payloads + unit variant"),
    ("Command", "Move { x: i32, y: i32 }, Quit, Say(String)", "struct variant + unit + tuple"),
    ("State", "Connecting, Connected { since: u64 }, Closed", "struct variant + unit"),
    ("HttpMethod", "Get, Post, Put, Delete, Patch", "no payload"),
    ("Tree<T>", "Leaf(T), Node(Box<Tree<T>>, Box<Tree<T>>)", "recursive payload"),
    ("Event", "Tick, Key(char), Resize { w: u32, h: u32 }", "struct variant + tuple + unit"),
]
for nm, variants, note in ENUMS:
    base = nm.split("<")[0]
    for tmpl in [
        f"Write a hexa enum `{nm}` with variants `{variants}` ({note}).",
        f"Declare the hexa enum `{nm}`: `{variants}`.",
        f"Define `{nm}` as a hexa enum — variants: {variants}.",
        f"Write the hexa declaration for an enum named `{nm}` with these variants: {variants}.",
    ]:
        add("T4", T4_SPEC, tmpl, f"enum {base}", "ast_equality", ["enum"])

# ===========================================================================
# T5 — HX-code family classification  ~96
# ===========================================================================
T5_SPEC = "hexa-lang/SPEC.md §14 Diagnostics"
# REAL hexa HX-code families (hexa-lang/SPEC.md §14 table) — corrected 2026-05-12.
# (The earlier Mk.0.1/Mk.I T5 used a fictional map; the canon is: HX0=parse/lex,
# HX1=atlas resolve, HX2=bind/scope, HX3=type, HX4=domain, HX5=units, HX6=equational,
# HX7=proof, HX8=citation, HX9=codegen/link/runtime.)
HX_FAMILIES = {
    "HX0xxx": ["a parse error", "a lexer error", "a tokenizer error", "an unexpected-token error during parsing",
               "an unterminated string literal", "a malformed token", "a stage-S0 lexical/parse diagnostic"],
    "HX1xxx": ["an atlas resolution failure", "citing an undefined law `L[N]`", "a tombstoned-`L` citation (HX1099)",
               "an unresolved atlas reference", "an atlas-trie lookup miss", "an unbound ident in lowering (HX1101)",
               "a stage-S1 atlas-resolve diagnostic"],
    "HX2xxx": ["an unbound identifier", "a name used before it is declared", "an undefined name (HX2001)",
               "a callee-is-not-callable error (HX2003)", "an out-of-scope variable", "a duplicate binding",
               "a stage-S2 bind/scope diagnostic"],
    "HX3xxx": ["a type mismatch", "an arity mismatch on a function call", "a return-type mismatch",
               "an incompatible assignment", "an integer literal out of range for its type", "a wrong-type argument",
               "a stage-S3 type diagnostic"],
    "HX4xxx": ["a domain-constraint violation", "a value outside its declared domain", "a refinement-type violation",
               "an out-of-domain numeric value", "a precondition not met on a domain-restricted parameter",
               "a stage-S4 domain diagnostic"],
    "HX5xxx": ["a units mismatch (e.g. adding meters and seconds)", "a missing `@units` annotation",
               "an incompatible-units operation", "a dimensional-analysis failure", "a unit conversion error",
               "a stage-S5 units diagnostic"],
    "HX6xxx": ["an equational-reasoning failure", "an unproven equality obligation", "a rewrite that doesn't hold",
               "a failed equational sample-eval", "an equation the prover couldn't discharge",
               "a stage-S6 equational diagnostic"],
    "HX7xxx": ["a proof-checking failure", "an unproven law obligation", "a failed in-house prover obligation",
               "a proof gap", "a `@law` obligation the prover rejected", "a stage-S7 proof diagnostic"],
    "HX8xxx": ["a citation error", "a missing `@implements`/`@law` citation", "an uncited use of a law (HX8004)",
               "a superseded-citation warning (HX8003)", "a citation that needs an `@grace` bypass",
               "a stage-S8 citation diagnostic"],
    "HX9xxx": ["a codegen failure", "a linker error", "a runtime panic surfaced as a diagnostic", "a backend-emit error",
               "an `@grace` expiry diagnostic (HX9001 — compiler refuses to build)", "an `@grace`-site warning (HX9000)",
               "an RFC-018 codegen/link/runtime diagnostic"],
}
for fam, descs in HX_FAMILIES.items():
    for d in descs:
        for tmpl in [
            f"Which hexa HX error-code family covers {d}? Answer with the family code like HX0xxx.",
            f"Classify {d} into its hexa HX diagnostic family.",
        ]:
            add("T5", T5_SPEC, tmpl, fam, "exact_match", ["hx", "classify"])
            if len(rows) and _ctr["T5"] >= 96:
                break
        if _ctr.get("T5", 0) >= 96:
            break
    if _ctr.get("T5", 0) >= 96:
        break

# ===========================================================================
# T6 — linker target triples  ~70
# ===========================================================================
T6_SPEC = "§linker target triples"
TARGETS = [
    ("Raspberry Pi Pico (RP2040, Cortex-M0+)", "thumbv6m-none-eabi"),
    ("Cortex-M0 bare-metal", "thumbv6m-none-eabi"),
    ("STM32F4 (Cortex-M4F, hardware float)", "thumbv7em-none-eabihf"),
    ("Cortex-M4F with FPU", "thumbv7em-none-eabihf"),
    ("Cortex-M4 without FPU (soft float)", "thumbv7em-none-eabi"),
    ("Cortex-M3 (e.g. STM32F1)", "thumbv7m-none-eabi"),
    ("ESP32 (Xtensa LX6)", "xtensa-esp32-none-elf"),
    ("ESP32-S3 (Xtensa LX7)", "xtensa-esp32s3-none-elf"),
    ("ESP32-C3 (RISC-V)", "riscv32imc-unknown-none-elf"),
    ("nRF52840 (Cortex-M4F)", "thumbv7em-none-eabihf"),
    ("Cortex-M7 with double-precision FPU", "thumbv7em-none-eabihf"),
    ("AVR ATmega328P (Arduino Uno)", "avr-unknown-gnu-atmega328"),
    ("RISC-V 32-bit IMAC bare-metal", "riscv32imac-unknown-none-elf"),
    ("RISC-V 64-bit GC bare-metal", "riscv64gc-unknown-none-elf"),
    ("x86_64 Linux (host build)", "x86_64-unknown-linux-gnu"),
    ("aarch64 Linux", "aarch64-unknown-linux-gnu"),
    ("aarch64 macOS (Apple Silicon)", "aarch64-apple-darwin"),
    ("x86_64 macOS (Intel)", "x86_64-apple-darwin"),
    ("WebAssembly (browser, no WASI)", "wasm32-unknown-unknown"),
    ("WebAssembly with WASI", "wasm32-wasi"),
    ("Cortex-A53 Linux (Raspberry Pi 3/4 64-bit)", "aarch64-unknown-linux-gnu"),
    ("RP2350 (Cortex-M33)", "thumbv8m.main-none-eabihf"),
]
for desc, triple in TARGETS:
    for tmpl in [
        f"What is the canonical hexa linker target triple for {desc}?",
        f"Give the hexa target triple used to build for {desc}.",
        f"Build target triple for {desc}?",
    ]:
        add("T6", T6_SPEC, tmpl, triple, "exact_match", ["linker", "triple"])
        if _ctr["T6"] >= 70:
            break
    if _ctr["T6"] >= 70:
        break

# ===========================================================================
# T7 — stdlib dependency direction  ~88
# ===========================================================================
T7_SPEC = "§stdlib / crate layering"
# rule: compiler -> stdlib OK; stdlib -> compiler NO. firmware boards -> stdlib/embedded OK,
# firmware boards -> stdlib/net NO. stdlib core -> stdlib/embedded NO (core is below). etc.
T7_CASES = [
    ("Can the hexa compiler depend on stdlib?", "yes"),
    ("Can hexa stdlib depend on the compiler?", "no"),
    ("Can a hexa firmware board crate `firmware/boards/rtsc/` import `stdlib/net/`?", "no"),
    ("Can a hexa firmware board crate `firmware/boards/chip/` import `stdlib/embedded/`?", "yes"),
    ("Can `stdlib/net/` import `stdlib/core/`?", "yes"),
    ("Can `stdlib/core/` import `stdlib/net/`?", "no"),
    ("Can `stdlib/embedded/` import `stdlib/core/`?", "yes"),
    ("Can `stdlib/core/` import `stdlib/embedded/`?", "no"),
    ("Can a firmware board crate import the hexa compiler?", "no"),
    ("Can the hexa compiler import a firmware board crate?", "no"),
    ("Can `tool/` scripts import stdlib?", "yes"),
    ("Can stdlib import `tool/` scripts?", "no"),
    ("Can `stdlib/net/` import `stdlib/embedded/`?", "no"),
    ("Can a hexa application crate import stdlib?", "yes"),
    ("Can stdlib import a hexa application crate?", "no"),
    ("Can `firmware/boards/cern/` import `stdlib/embedded/`?", "yes"),
    ("Can `firmware/boards/cern/` import `stdlib/net/`?", "no"),
    ("Can the test harness depend on stdlib?", "yes"),
    ("Can stdlib depend on the test harness?", "no"),
    ("Can `stdlib/io/` import `stdlib/core/`?", "yes"),
    ("Can `stdlib/core/` import `stdlib/io/`?", "no"),
    ("Can a firmware board crate import `stdlib/io/` (blocking file IO)?", "no"),
    ("Can a firmware board crate import `stdlib/core/`?", "yes"),
    ("Can `hexa-codex` techniques import stdlib?", "yes"),
    ("Can stdlib import `hexa-codex` techniques?", "no"),
    ("Can the REPL depend on the compiler?", "yes"),
    ("Can the compiler depend on the REPL?", "no"),
    ("Can `stdlib/alloc/` import `stdlib/core/`?", "yes"),
    ("Can `stdlib/core/` import `stdlib/alloc/`?", "no"),
]
for q, a in T7_CASES:
    for tmpl in [q + " Answer yes or no.", q.rstrip("?") + " — yes or no?"]:
        add("T7", T7_SPEC, tmpl, a, "yes_no_match", ["layering"])
        if _ctr["T7"] >= 88:
            break
    if _ctr["T7"] >= 88:
        break

# ===========================================================================
# T8 — refusal-required (code vs non-code, 5 NLs)  ~100
# ===========================================================================
T8_SPEC = "§VERIFY refusal contract"
ACCEPT = [
    ("Implement quicksort in hexa.", "en"), ("Write a binary search in Rust.", "en"),
    ("hexa로 이진 탐색 함수 써줘.", "kr"), ("用hexa写个二分查找。", "cn"),
    ("Напиши на Rust функцию быстрой сортировки.", "ru"), ("hexaでフィボナッチ関数を書いて。", "ja"),
    ("Refactor this Python function for clarity.", "en"), ("이 Go 코드의 버그를 고쳐줘.", "kr"),
    ("用TypeScript实现一个防抖函数。", "cn"), ("Explain what this C macro does.", "en"),
    ("Write a Swift struct conforming to Codable.", "en"), ("Add error handling to this Zig function.", "en"),
    ("hexaのenum Resultを書いて。", "ja"), ("Write a unit test for this Rust struct.", "en"),
    ("이 SQL 쿼리를 최적화해줘.", "kr"), ("Convert this loop to a recursive form in hexa.", "en"),
    ("Напиши Dockerfile для PyTorch обучения.", "ru"), ("Write a Playwright test for the login page.", "en"),
    ("用Python写一个LoRA训练循环。", "cn"), ("hexaでstructを定義して。", "ja"),
]
REFUSE = [
    ("Write me a poem about pythons (the snake).", "en"), ("Tell me a joke about cats.", "en"),
    ("커밋 메시지 말고 그냥 시 한 편 써줄래?", "kr"), ("给我讲个笑话。", "cn"),
    ("Напиши короткий рассказ про осень.", "ru"), ("週末に新しい車を買うべき？", "ja"),
    ("What's the answer to 2+2?", "en"), ("Who won the 1998 World Cup?", "en"),
    ("내일 날씨 어때?", "kr"), ("帮我写一封求职信。", "cn"),
    ("Дай совет, как лучше провести выходные.", "ru"), ("おすすめの映画教えて。", "ja"),
    ("Translate 'good morning' into French.", "en"), ("Summarize the plot of Hamlet.", "en"),
    ("주말에 차 사도 될까?", "kr"), ("解释一下相对论。", "cn"),
    ("Что такое фотосинтез?", "ru"), ("健康的な朝食のレシピを教えて。", "ja"),
    ("Recommend a good restaurant in Seoul.", "en"), ("Compose a birthday message for my friend.", "en"),
]
for prompt, nl in ACCEPT:
    for tmpl in [
        f'User asks: "{prompt}" Should the hexa-canon code model accept or refuse? Answer "accept" or "refuse".',
        f'A user prompt: "{prompt}". Is this in-domain for a code-only model? Reply "accept" or "refuse".',
    ]:
        add("T8", T8_SPEC, tmpl, "accept", "yes_no_match", ["refusal", nl, "accept"])
for prompt, nl in REFUSE:
    for tmpl in [
        f'User asks: "{prompt}" Should the hexa-canon code model accept or refuse? Answer "accept" or "refuse".',
        f'A user prompt: "{prompt}". Is this in-domain for a code-only model? Reply "accept" or "refuse".',
    ]:
        add("T8", T8_SPEC, tmpl, "refuse", "yes_no_match", ["refusal", nl, "refuse"])


# ===========================================================================
def main() -> int:
    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # summary
    from collections import Counter
    fam = Counter(r["family"] for r in rows)
    sc = Counter(r["scorer"] for r in rows)
    print(f"wrote {OUT}  ({len(rows)} tasks)")
    print("by family:", dict(sorted(fam.items())))
    print("by scorer:", dict(sorted(sc.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
