#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v12.py — gate-③ push: hammer T5 / T4 / T7 / T2 on the Mk.I families.

r11 on Mk.I 665 = 63.5%. Per-family: T1 96 · T6 82 · T8 79 · T3 65 · T2 59 · T4 56 · T7 55 · T5 25.
Biggest opportunities: T5 (25→80 = +8pp), T4 (56→80 = +4pp), T7 (55→80 = +3pp), T2 (59→80 = +3pp).

r12 = v11 base (2,521) + ~320 targeted pairs:
- ~200 T5 HX bare-code (MANY error descriptions per family, varied phrasing — teach the
  *concept* of each family, not specific strings; r11's 100 was too few per family)
- ~60 T4 enum "output ONLY the enum declaration" (the ast_equality scorer wants a clean
  compile-able decl; prose around it makes extraction/compile fail)
- ~40 T7 stdlib layering with the *rule explained* in the answer
- ~30 T2 atlas with the prove-vs-explore distinction made explicit

Total v12: ~2,840 rows.

OUTPUT
    /home/summer/runs/sft-train-v12/train.jsonl
    /home/summer/runs/sft-train-v12/MANIFEST.json
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
OUT_DIR = Path("/home/summer/runs/sft-train-v12")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# ---------------------------------------------------------------------------
# 1. T5 — HX-code families, ~200 bare-code pairs, lots of descriptions per family
# ---------------------------------------------------------------------------
HX5_DESCS = {
    "HX0xxx": [  # lexical / parse
        "a parse error", "a lexer error", "an unexpected token", "an unterminated string literal",
        "a missing closing brace during parsing", "a malformed function header", "an invalid numeric literal",
        "a bad escape sequence in a string", "an unrecognized character", "a stray semicolon error",
        "an unclosed comment block", "a `let` binding with no `=`", "a missing `->` in a function signature",
        "an unexpected end-of-file", "a non-ASCII identifier rejected by the lexer", "a misplaced `enum` keyword",
        "a tokenizer error on a malformed hex literal", "a parser error: expected expression, found `}`",
        "an extra closing parenthesis", "a missing comma between struct fields at parse time",
        "a reserved keyword used as an identifier", "an invalid float exponent", "a parse error in a generic-args list",
        "a missing `{` after `fn add()`", "an unterminated char literal",
    ],
    "HX1xxx": [  # name resolution / scoping
        "an unknown identifier", "use of a variable before it is declared", "an unresolved import",
        "a duplicate definition", "an out-of-scope variable", "a shadowing conflict", "a call to an undefined function",
        "an unknown module path", "an ambiguous name imported from two modules", "use of a private item from outside its module",
        "a reference to a non-existent struct field", "a typo'd function name (no such symbol)", "an unresolved type name",
        "a missing `use` for a referenced item", "a self-referential import cycle at resolution time",
        "a name used outside the block where it was bound", "a const referenced before its definition in the same scope",
        "an enum variant referenced without its enum prefix", "a generic parameter name not in scope",
        "a label used by `break` that doesn't exist", "a method called on a value whose type has no such method (name lookup)",
        "an unresolved path `a::b::c`", "a missing module file for a declared `mod`", "use of `super` at the crate root",
        "a re-export of a name that doesn't exist",
    ],
    "HX2xxx": [  # type errors
        "a type mismatch", "an arity mismatch on a function call", "a return-type mismatch",
        "an incompatible assignment", "a missing field on a struct literal", "an integer overflow in a constant expression",
        "a wrong type passed to a generic", "mismatched branch types in an `if`", "mismatched arm types in a `match`",
        "indexing with a non-integer", "comparing two incompatible types", "calling a non-function value",
        "a `u8` literal that doesn't fit in `u8`", "assigning `i32` to a `bool` binding", "a struct literal with an extra unknown field",
        "passing 2 args to a 3-arg function", "returning `()` from a function declared `-> i32`",
        "adding a `String` to an `i32`", "a `let x: u32 = -1;`", "dereferencing a non-reference",
        "a tuple pattern with the wrong number of elements", "calling `.len()` on an integer",
        "a function returning a reference to a temporary's type mismatch", "a generic instantiated with a type that lacks a required method",
        "an `if` used as an expression where the two branches have different types",
    ],
    "HX3xxx": [  # ownership / borrow
        "use of a moved value", "two simultaneous mutable borrows", "a mutable borrow while an immutable borrow is live",
        "a dangling reference", "a value used after being moved into a function", "an ownership leak",
        "returning a reference to a local variable", "a mutable borrow of an immutable binding", "overlapping mutable borrows of a struct",
        "a value dropped while still borrowed", "moving out of a borrowed context", "moving a field out of a struct that's still in use",
        "a closure capturing a moved value", "borrowing a value across an `await` point that isn't `Send`-safe",
        "assigning to a field through a shared reference", "moving an element out of a `Vec`",
        "two `&mut` to the same array element", "using a value after `drop()`", "a self-borrow conflict in a method chain",
        "returning `&self.field` whose lifetime outlives `self`", "iterating a `Vec` while pushing to it",
        "a moved `String` still referenced by an earlier `&str`", "double-free via two owners",
        "a borrow that outlives the data it points to", "a reborrow conflict",
    ],
    "HX4xxx": [  # trait / generic
        "an unresolved trait method", "an ambiguous generic instantiation", "a missing trait bound",
        "a conflicting trait impl", "an unsatisfied `where` clause", "a generic-arity mismatch",
        "a trait not implemented for the given type", "an orphan-rule violation", "an associated-type mismatch",
        "a recursive trait bound that doesn't terminate", "calling a default method that requires an unimplemented one",
        "two `impl`s of the same trait for the same type", "a generic function used without enough type info to infer `T`",
        "a missing `Sized` bound on a generic", "a trait object for a non-object-safe trait",
        "an associated constant referenced on a type that doesn't implement the trait", "a blanket impl conflicting with a specific impl",
        "a `<T: Trait>` bound not met at the call site", "an unimplemented `Iterator::Item` type",
        "a generic struct instantiated with a lifetime that doesn't outlive a needed one (trait-side)",
        "ambiguity between two in-scope traits both providing `.foo()`", "a `dyn Trait` used where a sized type is required",
        "a missing `+ 'static` bound on a trait object", "a where-clause referring to an undefined associated type",
        "a higher-ranked trait bound that can't be satisfied",
    ],
    "HX5xxx": [  # linker / target
        "an undefined symbol at link time", "an unknown target triple", "a missing board crate",
        "a relocation out of range", "a duplicate symbol at link time", "a missing entry point `_start`",
        "a `.text` section overflow on a microcontroller", "an incompatible ABI between objects", "a missing linker script for a board",
        "a static `.bss` too large for the chip's RAM at link time", "two crates exporting the same `#[no_mangle]` symbol",
        "a missing `core` rlib for the target", "an unresolved external `extern \"C\"` symbol", "a wrong-endianness object in the link",
        "a target triple with no registered linker", "a `.rodata` overflow into RAM region", "a missing vector table for a Cortex-M target",
        "an undefined weak symbol that was expected strong", "a TLS relocation unsupported on the target",
        "a stack-size check failure during linking", "a missing `memory.x` for an embedded target", "a 32-bit vs 64-bit object mismatch",
        "an unresolved `panic_handler` symbol", "a linker error: cannot find `-lm`", "a flash region overflow on an ESP32",
    ],
    "HX6xxx": [  # lint S0..S8
        "a lint diagnostic S0–S8 (pre-codegen)", "an S0 style lint", "an S1 formatting lint", "an S2 import-order lint",
        "an S3 complexity lint (function too long)", "an S4 magic-number lint", "an S5 naming-convention lint",
        "an S6 shadowing warning", "an S7 dead-code lint", "an S8 doc-coverage lint",
        "an unused-variable lint", "an unused-import lint", "a `match` that should be an `if let` lint",
        "a redundant `clone()` lint", "a `loop`-that-could-be-`for` lint", "a missing `#[must_use]` lint",
        "an overly-broad pattern lint", "a needless `return` at the end of a function lint", "a `let` that could be `const` lint",
        "a too-many-arguments lint", "a nested-too-deeply lint", "an unreachable-pattern lint (S-class)",
        "a non-snake_case function name lint", "a SCREAMING_CASE expected for a const lint", "an undocumented public item lint",
    ],
    "HX7xxx": [  # codegen
        "a codegen failure", "an unhandled binary operator in codegen", "a backend emit error", "an internal codegen assertion",
        "an ABI lowering error", "an unsupported construct in codegen", "a register allocation failure", "an invalid intrinsic in codegen",
        "an alignment error lowering a struct", "an out-of-registers codegen error", "a codegen panic on a recursive type with no indirection",
        "a too-large stack frame at codegen", "an unsupported SIMD width for the target in codegen", "a codegen error lowering a closure",
        "a missing lowering for a `match` with guards", "an LLVM-IR verification failure", "a codegen error on an empty enum",
        "a codegen error lowering a generic monomorphization", "a backend crash on a 128-bit integer op",
        "a codegen error: cannot lower variadic call", "a codegen assertion: type size unknown", "an invalid debug-info emission",
        "a codegen error lowering inline assembly", "a backend error on an unsupported calling convention", "a codegen panic on a zero-sized array index",
    ],
    "HX8xxx": [  # FFI / ABI
        "an FFI/ABI error", "a C header signature mismatch", "an `extern` block signature mismatch", "a calling-convention mismatch",
        "a struct layout that doesn't match the C ABI", "a variadic FFI misuse", "a wrong-sized C integer at the boundary",
        "a missing extern symbol resolved via FFI", "a bool/int representation mismatch across FFI", "a null pointer passed where FFI expects non-null",
        "a `repr(C)` missing on a struct passed to C", "a Rust enum passed to C without `repr(C)`", "an `extern \"C\"` function with a non-FFI-safe return type",
        "a `&str` passed to C (not null-terminated)", "a function pointer ABI mismatch in FFI", "a 32/64-bit pointer-width mismatch in FFI",
        "a packed-struct alignment mismatch across the FFI boundary", "an FFI call to a varargs function with wrong promotion", "a callback ABI mismatch",
        "a `CString` lifetime bug at the FFI boundary", "an FFI error: opaque type sized incorrectly", "a wchar_t-width mismatch across FFI",
        "an FFI error passing a Rust slice as a C array+len with the wrong len type", "a `#[no_mangle]` name collision with a C symbol",
        "an FFI error: non-`#[repr(transparent)]` newtype passed to C",
    ],
    "HX9xxx": [  # deprecation / @grace
        "a deprecation / @grace notice", "a grace-period-expired warning", "a removed-API notice", "a deprecated-syntax warning",
        "an obsolete-target notice", "a stale-annotation notice", "an `@grace` annotation past its until-date", "use of a removed builtin",
        "an old-style attribute that's been replaced", "a deprecated stdlib function call", "use of a deprecated enum variant",
        "a removed compiler flag still referenced", "a deprecated macro invocation", "an obsolete `mod` layout warning",
        "a deprecated linker target name", "a soon-to-be-removed feature gate", "a deprecated trait method override",
        "an `@grace`-marked function called after the cutoff date", "a removed `--edition` value", "a deprecated config key in `hexa.toml`",
        "a sunset diagnostic for a feature removed in the next edition", "a deprecated `panic!` formatting form", "use of a removed `unsafe` escape hatch",
        "a deprecated derive macro", "an obsolete `#[legacy]` attribute",
    ],
}


def gen_t5(n=200) -> list[dict]:
    pool = []
    for fam, descs in HX5_DESCS.items():
        for d in descs:
            pool.append((fam, d))
    random.shuffle(pool)
    out = []
    for fam, d in pool[:n]:
        tmpl = random.choice([
            f"Which hexa HX error-code family covers {d}? Answer with just the family code like HX0xxx.",
            f"Which hexa HX diagnostic family is {d}? Reply with only the family code (e.g. HX0xxx).",
            f"Classify {d} into its hexa HX family. Answer with only the family code.",
            f"HX family for {d}? (answer: one code like HX2xxx, nothing else)",
            f"A hexa compiler emits a diagnostic for {d}. What family code does it have? Just the code.",
            f"{d} -> which HX family? (bare code only)",
        ])
        out.append(fmt(tmpl, fam))
    return out


# ---------------------------------------------------------------------------
# 2. T4 — enum, "output ONLY the declaration"
# ---------------------------------------------------------------------------
ENUMS = [
    ("Color", "Red, Green, Blue"), ("Direction", "North, South, East, West"),
    ("Status", "Idle, Running, Done, Error"), ("Priority", "Low, Normal, High, Critical"),
    ("LogLevel", "Trace, Debug, Info, Warn, Error"), ("Suit", "Clubs, Diamonds, Hearts, Spades"),
    ("Op", "Add, Sub, Mul, Div"), ("Visibility", "Public, Private, Internal"),
    ("Endian", "Little, Big"), ("Phase", "Setup, Run, Teardown"),
    ("HttpMethod", "Get, Post, Put, Delete, Patch"), ("Weekday", "Mon, Tue, Wed, Thu, Fri, Sat, Sun"),
    ("Maybe<T>", "None, Some(T)"), ("Option<T>", "None, Some(T)"),
    ("Result<T>", "Ok(T), Err(String)"), ("Either<E, T>", "Err(E), Ok(T)"),
    ("Pair<A, B>", "Two(A, B)"), ("Validated<T>", "Valid(T), Invalid(Vec<String>)"),
    ("Shape", "Circle(f64), Square(f64), Rect(f64, f64)"),
    ("Token", "Ident(String), Int(i64), Punct(char), Eof"),
    ("Json", "Null, Bool(bool), Num(f64), Str(String)"),
    ("Command", "Move { x: i32, y: i32 }, Quit, Say(String)"),
    ("State", "Connecting, Connected { since: u64 }, Closed"),
    ("Tree<T>", "Leaf(T), Node(Box<Tree<T>>, Box<Tree<T>>)"),
    ("Event", "Tick, Key(char), Resize { w: u32, h: u32 }"),
    ("Mode", "Read, Write, Append"), ("Severity", "Info, Warning, Critical"),
    ("Cmp", "Less, Equal, Greater"), ("Bit", "Zero, One"),
]


def _enum_body(name: str, variants: str) -> str:
    base = name  # keep generics in the decl
    vs = [v.strip() for v in variants.split(",")]
    # naive: join — keep as-is; this is illustrative training text, hexa-cc validates
    inner = ",\n    ".join(vs)
    return f"enum {base} {{\n    {inner},\n}}"


def gen_t4(n=60) -> list[dict]:
    out = []
    items = ENUMS * 3
    random.shuffle(items)
    for name, variants in items[:n]:
        body = _enum_body(name, variants)
        tmpl = random.choice([
            f"Write a hexa enum `{name}` with variants `{variants}`. Output ONLY the enum declaration — no prose, no code fences.",
            f"Output (just the declaration, nothing else) a hexa enum `{name}`: variants {variants}.",
            f"Give the hexa enum declaration for `{name}` with `{variants}` — declaration only.",
            f"Declare the hexa enum `{name}` ({variants}). Reply with only the `enum` block.",
        ])
        out.append(fmt(tmpl, body))
    return out


# ---------------------------------------------------------------------------
# 3. T7 — stdlib layering with the rule explained
# ---------------------------------------------------------------------------
T7_RULED = [
    ("Can the hexa compiler depend on stdlib?", "yes",
     "The compiler is allowed to use stdlib; stdlib sits below it. The reverse (stdlib depending on the compiler) is forbidden."),
    ("Can hexa stdlib depend on the compiler?", "no",
     "stdlib is a lower layer than the compiler; lower layers never depend on higher ones."),
    ("Can `stdlib/core/` import `stdlib/net/`?", "no",
     "`stdlib/core` is the bottom layer — it can't import `net`, which is above it. `net` -> `core` is fine."),
    ("Can `stdlib/net/` import `stdlib/core/`?", "yes",
     "`net` is above `core`, so importing downward into `core` is allowed."),
    ("Can `stdlib/core/` import `stdlib/embedded/`?", "no",
     "`core` is below `embedded`; it cannot import upward."),
    ("Can `stdlib/embedded/` import `stdlib/core/`?", "yes",
     "`embedded` may import the lower `core` layer."),
    ("Can a firmware board crate `firmware/boards/rtsc/` import `stdlib/net/`?", "no",
     "Firmware board crates may use `stdlib/core` and `stdlib/embedded` but not networking/blocking layers like `stdlib/net`."),
    ("Can a firmware board crate `firmware/boards/chip/` import `stdlib/embedded/`?", "yes",
     "`stdlib/embedded` is exactly the layer firmware board crates are meant to use."),
    ("Can a firmware board crate import `stdlib/io/` (blocking file IO)?", "no",
     "Blocking file IO isn't available to no-std firmware crates; `stdlib/io` is off-limits to boards."),
    ("Can a firmware board crate import `stdlib/core/`?", "yes",
     "`stdlib/core` is the no-std foundation; all firmware crates may use it."),
    ("Can a firmware board crate import the hexa compiler?", "no",
     "Application/firmware crates never depend on the compiler — it's the top layer of the toolchain."),
    ("Can the hexa compiler import a firmware board crate?", "no",
     "The compiler doesn't depend on board crates; boards are leaves of the dependency DAG."),
    ("Can `tool/` scripts import stdlib?", "yes",
     "`tool/` scripts run on the host and may use stdlib freely."),
    ("Can stdlib import `tool/` scripts?", "no",
     "stdlib is a library layer; it never depends on host tooling."),
    ("Can `stdlib/net/` import `stdlib/embedded/`?", "no",
     "`net` and `embedded` are sibling/parallel layers — neither imports the other; both import `core`."),
    ("Can `stdlib/alloc/` import `stdlib/core/`?", "yes",
     "`alloc` is above `core` and may import it."),
    ("Can `stdlib/core/` import `stdlib/alloc/`?", "no",
     "`core` is below `alloc`; it can't import upward."),
    ("Can `stdlib/io/` import `stdlib/core/`?", "yes",
     "`io` builds on `core`; downward import is allowed."),
    ("Can `stdlib/core/` import `stdlib/io/`?", "no",
     "`core` cannot import `io`, which sits above it."),
    ("Can a hexa application crate import stdlib?", "yes",
     "Applications are the top user layer and may use any public stdlib module."),
    ("Can stdlib import a hexa application crate?", "no",
     "Libraries don't depend on applications; that's a backwards dependency."),
    ("Can the REPL depend on the compiler?", "yes",
     "The REPL is a front-end built on top of the compiler."),
    ("Can the compiler depend on the REPL?", "no",
     "The compiler is the lower layer; it doesn't depend on the REPL."),
    ("Can the test harness depend on stdlib?", "yes",
     "Tests run on the host and may use stdlib."),
    ("Can stdlib depend on the test harness?", "no",
     "stdlib never depends on the test harness — wrong direction."),
    ("Can `hexa-codex` techniques import stdlib?", "yes",
     "`hexa-codex` technique code is application-level and may use stdlib."),
    ("Can stdlib import `hexa-codex` techniques?", "no",
     "stdlib doesn't depend on `hexa-codex`; that's a higher layer."),
    ("Can `firmware/boards/cern/` import `stdlib/embedded/`?", "yes",
     "All board crates may use `stdlib/embedded`."),
    ("Can `firmware/boards/cern/` import `stdlib/net/`?", "no",
     "Board crates can't pull in `stdlib/net` (networking/blocking)."),
    ("Can `firmware/boards/chip/` import `stdlib/core/`?", "yes",
     "Every board crate may use `stdlib/core`."),
]


def gen_t7(n=40) -> list[dict]:
    out = []
    items = T7_RULED * 2
    random.shuffle(items)
    for q, a, why in items[:n]:
        tmpl = random.choice([
            q + " Answer yes or no, then one sentence why.",
            q + " (yes/no + reason)",
            q + " — yes or no? Explain in one line.",
        ])
        out.append(fmt(tmpl, f"{a} — {why}"))
        # also a bare yes/no variant to match the strict yes_no_match scorer on the first token
        out.append(fmt(q + " Answer yes or no.", a))
    return out[:n]


# ---------------------------------------------------------------------------
# 4. T2 — atlas, prove vs explore made explicit
# ---------------------------------------------------------------------------
def gen_t2(n=30) -> list[dict]:
    out = []
    for _ in range(n // 2):
        nL = random.randint(1, 600)
        v = random.choice(["proves", "PROVES", "establishes", "demonstrates", "shows", "confirms", "verifies"])
        prompt = random.choice([
            f"A hexa function {v} a known law `L[{nL}]` (it produces a proof of an existing entry). Which annotation — `@implements(L[{nL}])` or `@discover(kind=\"L\")`? Write it.",
            f"Annotate `prove_{nL}`: it {v} `L[{nL}]`. (A function that proves an existing law uses `@implements`.)",
        ])
        out.append(fmt(prompt, f"@implements(L[{nL}])"))
    for _ in range(n - n // 2):
        nL = random.randint(1, 600)
        v = random.choice(["EXPLORES", "discovers", "searches for", "hunts for", "probes for", "seeks"])
        prompt = random.choice([
            f"A hexa function {v} *new, undiscovered* instances under law `L[{nL}]` (it hunts for cases not yet in the atlas). Which annotation — `@implements(L[{nL}])` or `@discover(kind=\"L\")`? Write it.",
            f"Annotate `explore_{nL}`: it {v} new instances of `L[{nL}]`. (A function that searches for new instances uses `@discover`.)",
        ])
        out.append(fmt(prompt, '@discover(kind="L")'))
    return out


def main() -> int:
    if not V11_BASE.exists():
        print(f"ERROR: v11 base not found at {V11_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V11_BASE.read_text().splitlines() if l.strip()]
    print(f"v11 base: {len(base)}")
    blocks = {
        "t5_hx_barecode_big": gen_t5(200),
        "t4_enum_decl_only": gen_t4(60),
        "t7_layering_ruled": gen_t7(40),
        "t2_atlas_explicit": gen_t2(30),
    }
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:24s} {len(rows_):4d}")
        added.extend(rows_)
    print(f"added: {len(added)}")
    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.2.0-r12",
        "base": str(V11_BASE),
        "base_rows": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": "gate-③ push: T5 25->80, T4 56->80, T7 55->80, T2 59->80 on Mk.I",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
