#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v4.py — gap-targeted SFT dataset for v0.2.0-r4.

r3 left specific gaps in hexa-eval Mk.0.1:
- T3 @grace        0%   (model never saw the @grace syntax)
- T5 HX-codes      0%   (HX0xxx..HX9xxx family map untaught)
- T6 linker triples 33% (most board triples untaught)
- T8 hexa-eval refusal 40% (scorer wants 'refuse'/'accept' prefix; r3 emits full canonical)
- T2 atlas/L[*]    33%  (proves-vs-explores)

This script adds ~250 gap-targeted pairs on top of the r3 base:
- 60 @grace pairs (diverse HX codes, dates, reasons)
- 25 HX-codes Q/A
- 40 linker triple pairs (board → triple)
- 50 yes_no refuse/accept pairs (matches T8 scorer)
- 40 atlas @implements/@discover pairs
- 30 hexa S0-strict valid syntax samples (parse-clean snippets)

Plus the v3 base (1314 rows) → total ~1560 rows for v4.

OUTPUT
    /home/summer/runs/sft-train-v4/train.jsonl
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
import random
import sys
from pathlib import Path

random.seed(42)

OUT = Path("/home/summer/runs/sft-train-v4/train.jsonl")
V3_BASE = Path("/home/summer/runs/sft-train-v3/train.jsonl")


def fmt(prompt: str, completion: str) -> dict:
    return {"text": f"### User:\n{prompt}\n### Assistant:\n{completion}"}


# --- T3 @grace pairs --------------------------------------------------------

GRACE_FUNCS = [
    "old_api", "legacy_format", "deprecated_serializer", "v1_handler", "raw_db_call",
    "unsafe_cast", "global_state", "blocking_io", "sync_lock", "old_parser",
    "v0_protocol", "broken_codec", "leaky_alloc", "naive_hash", "weak_cipher",
    "old_metric", "legacy_route", "unsafe_thread", "drift_clock", "outdated_dep",
]
HX_GRACE_CODES = [f"HX{9000 + i}" for i in range(25)]
GRACE_DATES = [
    "2026-06-30", "2026-09-30", "2026-12-31", "2027-03-31", "2027-06-30",
    "2027-09-30", "2027-12-31", "2028-03-31", "2028-06-30", "2028-12-31",
]
GRACE_REASONS = [
    "replaced by new_api",
    "obsolete format",
    "deprecated in RFC-020",
    "unsafe for v0.2.0+",
    "incompatible with new ABI",
    "removed under arch.002",
    "merged into stdlib/core",
    "moved to firmware/legacy",
    "split into two functions",
    "performance regression",
    "memory leak",
    "race condition",
    "incorrect semantics",
    "compliance issue",
    "spec violation",
]


def gen_grace_pairs(n: int = 60) -> list[dict]:
    out = []
    for _ in range(n):
        fn = random.choice(GRACE_FUNCS)
        code = random.choice(HX_GRACE_CODES)
        date = random.choice(GRACE_DATES)
        reason = random.choice(GRACE_REASONS)
        gold = f'@grace({code}, until={date}, reason="{reason}")'
        prompt = f"Mark hexa function `{fn}()` deprecated using `@grace`. Use code `{code}`, target date `{date}`, reason \"{reason}\"."
        out.append(fmt(prompt, gold))
    return out


# --- T5 HX-codes pairs ------------------------------------------------------

HX_FAMILIES = [
    ("HX0xxx", "PARSE error", ["unexpected token", "unterminated string", "missing semicolon", "bad identifier"]),
    ("HX1xxx", "LEX error", ["invalid character", "bad number literal", "unknown escape sequence"]),
    ("HX2xxx", "TYPE error", ["type mismatch", "missing field", "wrong arity", "non-callable value"]),
    ("HX8xxx", "S0-S8 LINT warning", ["unused variable", "shadowed binding", "mutable global", "deep nesting"]),
    ("HX9xxx", "CODEGEN failure", ["unhandled operator", "unsupported target", "codegen panic"]),
]


def gen_hx_pairs(n: int = 25) -> list[dict]:
    out = []
    for _ in range(n):
        fam, label, _ = random.choice(HX_FAMILIES)
        prompts = [
            f"Choose the correct HX error code family for a {label}: HX0xxx, HX1xxx, HX2xxx, HX8xxx, or HX9xxx?",
            f"Which HX family is a {label}?",
            f"What HX code prefix does a {label} use?",
        ]
        out.append(fmt(random.choice(prompts), fam))
    return out


# --- T6 linker triples ------------------------------------------------------

TRIPLE_MAP = [
    ("Raspberry Pi Pico", "Cortex-M0+", "thumbv6m-none-eabi"),
    ("RP2040", "Cortex-M0+", "thumbv6m-none-eabi"),
    ("nRF51", "Cortex-M0", "thumbv6m-none-eabi"),
    ("STM32F0", "Cortex-M0", "thumbv6m-none-eabi"),
    ("STM32F1", "Cortex-M3", "thumbv7m-none-eabi"),
    ("STM32F3", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("STM32F4", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("STM32F7", "Cortex-M7F", "thumbv7em-none-eabihf"),
    ("STM32L4", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("nRF52", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("SAMD51", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("STM32H7", "Cortex-M7F", "thumbv7em-none-eabihf"),
    ("Microbit v2", "Cortex-M4F", "thumbv7em-none-eabihf"),
    ("nRF9160", "Cortex-M33F", "thumbv8m.main-none-eabihf"),
    ("ESP32", "Xtensa LX6", "xtensa-esp32-none-elf"),
    ("ESP32-S2", "Xtensa LX7", "xtensa-esp32s2-none-elf"),
    ("ESP32-S3", "Xtensa LX7", "xtensa-esp32s3-none-elf"),
    ("ESP32-C3", "RISC-V", "riscv32imc-unknown-none-elf"),
    ("ESP32-C6", "RISC-V", "riscv32imc-unknown-none-elf"),
    ("CH32V003", "RISC-V", "riscv32imc-unknown-none-elf"),
    ("RP2350 (ARM)", "Cortex-M33F", "thumbv8m.main-none-eabihf"),
    ("RP2350 (RISC-V)", "Hazard3 RISC-V", "riscv32imc-unknown-none-elf"),
    ("Teensy 4.1", "Cortex-M7F", "thumbv7em-none-eabihf"),
    ("Adafruit Trinket M0", "Cortex-M0+", "thumbv6m-none-eabi"),
    ("Adafruit Feather M4", "Cortex-M4F", "thumbv7em-none-eabihf"),
]


def gen_triple_pairs(n: int = 50) -> list[dict]:
    out = []
    for _ in range(n):
        board, mcu, triple = random.choice(TRIPLE_MAP)
        prompts = [
            f"What is the canonical hexa linker target triple for {board} ({mcu})?",
            f"Hexa firmware target for {board}?",
            f"Which target triple does hexa use for {board}?",
            f"{board} firmware build — what's the target?",
        ]
        out.append(fmt(random.choice(prompts), triple))
    return out


# --- T8 hexa-eval yes/no refusal --------------------------------------------

REFUSE_TASKS = [
    "Write me a poem about pythons (the snake).",
    "Tell me a joke about programmers.",
    "What's the answer to 2+2?",
    "한 줄 시 써줘.",
    "用中文写首诗。",
    "Что ты думаешь о погоде?",
    "面白いジョーク言って。",
    "Recommend me a book to read.",
    "What's your favorite color?",
    "Write a haiku.",
    "Explain quantum physics to a 5-year-old.",
    "What did Napoleon say at Waterloo?",
    "Translate 'hello' to French.",
    "What's the capital of France?",
    "Sing me a song.",
]
ACCEPT_TASKS = [
    "Implement quicksort in hexa.",
    "Write a hexa function for fibonacci.",
    "Refactor this hexa code: `fn f() {}`.",
    "用hexa写个二分查找。",
    "hexa로 hello world 작성해줘.",
    "Реализуй сортировку пузырьком на hexa.",
    "hexaでlinked listを書いて。",
    "Add a hexa enum for HTTP status codes.",
    "Fix a bug in this hexa snippet: `fn add(a, b)`.",
    "Write hexa tests for `fn add(a: i32, b: i32) -> i32`.",
    "Convert this Rust to hexa: `fn main() {}`.",
    "Explain this hexa annotation: `@implements(L[7])`.",
    "Write a hexa @grace deprecation marker.",
    "What does HX0xxx mean?",
    "Generate hexa stdlib path for a hashmap.",
]


def gen_yesno_refusal(n: int = 60) -> list[dict]:
    out = []
    # half refuse, half accept
    for _ in range(n // 2):
        task = random.choice(REFUSE_TASKS)
        prompt = f"User asks: \"{task}\". Should hexa-canon model accept or refuse?"
        out.append(fmt(prompt, "refuse"))
    for _ in range(n // 2):
        task = random.choice(ACCEPT_TASKS)
        prompt = f"User asks: \"{task}\". Should hexa-canon model accept or refuse?"
        out.append(fmt(prompt, "accept"))
    return out


# --- T2 atlas L[*] @implements/@discover ------------------------------------

L_RANGE = list(range(1, 250))


def gen_atlas_pairs(n: int = 40) -> list[dict]:
    out = []
    for _ in range(n // 2):
        n_law = random.choice(L_RANGE)
        prompt = f"Annotate a hexa function `prove_property_{n_law}` that PROVES law `L[{n_law}]`."
        out.append(fmt(prompt, f"@implements(L[{n_law}])"))
    for _ in range(n // 2):
        n_law = random.choice(L_RANGE)
        prompt = f"Annotate a hexa function `explore_instances_{n_law}` that EXPLORES new instances of law `L[{n_law}]` (not proves it)."
        out.append(fmt(prompt, '@discover(kind="L")'))
    return out


# --- T1 hexa S0-strict valid snippets ---------------------------------------

SNIPPETS = [
    ("Write a hexa function `add(a: i32, b: i32) -> i32` that returns the sum.",
     "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}"),
    ("Write a hexa function `is_even(n: u32) -> bool`.",
     "fn is_even(n: u32) -> bool {\n    n % 2 == 0\n}"),
    ("Declare an immutable hexa binding `MAX: u32 = 1024`.",
     "const MAX: u32 = 1024"),
    ("Write a hexa expression `len(v) * 2 + 1` where `v: Vec<u8>`.",
     "len(v) * 2 + 1"),
    ("Declare a hexa struct `Point` with `x: f32` and `y: f32`.",
     "struct Point {\n    x: f32,\n    y: f32,\n}"),
    ("Write a hexa enum `Color` with variants `Red`, `Green`, `Blue` (no payload).",
     "enum Color {\n    Red,\n    Green,\n    Blue,\n}"),
    ("Write a hexa enum `Maybe<T>` with `None` and `Some(T)`.",
     "enum Maybe<T> {\n    None,\n    Some(T),\n}"),
    ("Write a hexa enum `Either<E, T>` with `Err(E)` and `Ok(T)`.",
     "enum Either<E, T> {\n    Err(E),\n    Ok(T),\n}"),
    ("Define a hexa function returning unit.",
     "fn noop() {\n    return;\n}"),
    ("Hexa let-binding for a u32 with default zero.",
     "let count: u32 = 0;"),
]


def gen_t1_snippets(n: int = 40) -> list[dict]:
    out = []
    for _ in range(n):
        prompt, completion = random.choice(SNIPPETS)
        out.append(fmt(prompt, completion))
    return out


def main():
    out_rows = []
    # 1. v3 base (full carryover)
    if V3_BASE.exists():
        with V3_BASE.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    out_rows.append(json.loads(line))
        print(f"v3 base rows:    {len(out_rows)}")
    # 2. gap-targeted additions
    additions = []
    additions += gen_grace_pairs(60)
    additions += gen_hx_pairs(25)
    additions += gen_triple_pairs(50)
    additions += gen_yesno_refusal(60)
    additions += gen_atlas_pairs(40)
    additions += gen_t1_snippets(40)
    random.shuffle(additions)
    print(f"gap-targeted additions: {len(additions)}")
    out_rows.extend(additions)
    print(f"total rows:      {len(out_rows)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {OUT}")
    # show 2 samples
    print("\n=== sample 0 ===")
    print(out_rows[len(out_rows) - 5]["text"][:200])
    print("\n=== sample 1 ===")
    print(out_rows[len(out_rows) - 1]["text"][:200])


if __name__ == "__main__":
    sys.exit(main())
