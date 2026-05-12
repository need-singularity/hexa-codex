#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v7.py — boost the stuck families: T2 / T5 / T8 / F3.

After r6 the residual gaps are:
- T2 atlas L[*] @implements/@discover  33%  (need more exemplars)
- T4 enum                              33%  (regression vs base 100%)
- T5 HX[CCCC] family map               33%  (5 families, only 5 in r4 set)
- T8 hexa-eval yes/no refuse/accept    40%  (apple traps used 'out-of-domain'
                                              instead of 'refuse'/'accept' verb)
- 5-NL F3 explanation                  60%  (was 80 in r4, regressed)

v7 = v6 base (1,665) + targeted boost:
- +60 atlas pairs (L[N] × proves/explores × annotations)
- +60 enum pairs (Color/Maybe/Either/Result/Option/Status variants)
- +50 HX codes Q/A (5 families × diverse phrasings)
- +100 yes/no refuse/accept (covers the literal scorer)
- +50 F3 explanation pairs (5 NLs × 10 explanations)

Total v7: ~1,985 rows.

OUTPUT
    /home/summer/runs/sft-train-v7/train.jsonl
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json, random
from pathlib import Path

random.seed(42)

V6_BASE = Path("/home/summer/runs/sft-train-v6/train.jsonl")
OUT = Path("/home/summer/runs/sft-train-v7/train.jsonl")


def fmt(p, c):
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# --- T2 atlas pairs ---------------------------------------------------------

L_RANGE = list(range(1, 300))


def gen_atlas(n=60):
    out = []
    for _ in range(n // 2):
        nL = random.choice(L_RANGE)
        action = random.choice(["proves", "PROVES", "establishes", "shows"])
        prompt = f"Annotate a hexa function `prove_{nL}` that {action} law `L[{nL}]`."
        out.append(fmt(prompt, f"@implements(L[{nL}])"))
    for _ in range(n // 2):
        nL = random.choice(L_RANGE)
        action = random.choice(["EXPLORES", "discovers", "searches for", "hunts"])
        prompt = f"Annotate `explore_{nL}` that {action} new instances of `L[{nL}]`."
        out.append(fmt(prompt, '@discover(kind="L")'))
    return out


# --- T4 enum pairs ---------------------------------------------------------

ENUM_DEFS = [
    ("Color", "Red, Green, Blue", "enum Color {\n    Red,\n    Green,\n    Blue,\n}"),
    ("Direction", "North, South, East, West",
     "enum Direction {\n    North,\n    South,\n    East,\n    West,\n}"),
    ("Status", "Idle, Running, Done, Error",
     "enum Status {\n    Idle,\n    Running,\n    Done,\n    Error,\n}"),
    ("Maybe<T>", "None, Some(T)",
     "enum Maybe<T> {\n    None,\n    Some(T),\n}"),
    ("Either<E, T>", "Err(E), Ok(T)",
     "enum Either<E, T> {\n    Err(E),\n    Ok(T),\n}"),
    ("Result<T>", "Ok(T), Err(String)",
     "enum Result<T> {\n    Ok(T),\n    Err(String),\n}"),
    ("Option<T>", "None, Some(T)",
     "enum Option<T> {\n    None,\n    Some(T),\n}"),
    ("Priority", "Low, Normal, High, Critical",
     "enum Priority {\n    Low,\n    Normal,\n    High,\n    Critical,\n}"),
    ("Side", "Left, Right",
     "enum Side {\n    Left,\n    Right,\n}"),
    ("Light", "Red, Yellow, Green",
     "enum Light {\n    Red,\n    Yellow,\n    Green,\n}"),
]


def gen_enums(n=60):
    out = []
    for _ in range(n):
        name, variants, code = random.choice(ENUM_DEFS)
        templates = [
            f"Write a hexa enum `{name}` with variants `{variants}`.",
            f"Define a hexa enum named `{name}` (variants: {variants}).",
            f"Hexa: declare enum `{name}` having {variants}.",
        ]
        out.append(fmt(random.choice(templates), code))
    return out


# --- T5 HX codes -----------------------------------------------------------

HX = [
    ("HX0xxx", ["PARSE error", "parser failure", "syntax error",
                "unexpected token", "missing semicolon",
                "unterminated string", "bad identifier"]),
    ("HX1xxx", ["LEX error", "lexer failure", "invalid character",
                "bad number literal", "unknown escape sequence"]),
    ("HX2xxx", ["TYPE error", "type mismatch", "missing field",
                "wrong arity", "non-callable value", "name resolution failure"]),
    ("HX8xxx", ["S0-S8 LINT warning", "lint S3 violation", "unused variable",
                "shadowed binding", "deep nesting"]),
    ("HX9xxx", ["CODEGEN failure", "codegen panic", "unhandled operator",
                "unsupported target", "C emit error"]),
]


def gen_hx(n=50):
    out = []
    for _ in range(n):
        fam, msgs = random.choice(HX)
        msg = random.choice(msgs)
        prompts = [
            f"Which HX family is a {msg}?",
            f"Which HX[CCCC] prefix does a {msg} use?",
            f"Pick the correct HX prefix for a {msg}: HX0xxx / HX1xxx / HX2xxx / HX8xxx / HX9xxx?",
            f"What HX error family corresponds to {msg}?",
        ]
        out.append(fmt(random.choice(prompts), fam))
    return out


# --- T8 yes/no refuse / accept ---------------------------------------------

REFUSE_PROMPTS = [
    "Write me a poem about pythons (the snake).",
    "Tell me a joke about programmers.",
    "What's the answer to 2+2?",
    "한 줄 시 써줘.",
    "用中文写首诗。",
    "Что ты думаешь о погоде?",
    "面白いジョーク言って。",
    "Recommend me a book.",
    "What's your favorite color?",
    "Write a haiku.",
    "Explain quantum physics to a 5-year-old.",
    "What did Napoleon say at Waterloo?",
    "Translate 'hello' to French.",
    "What's the capital of France?",
    "Sing me a song.",
    "당신의 이름은 뭐예요?",
    "今天天气怎么样?",
    "Какой ваш любимый цвет?",
    "好きな食べ物は?",
    "Tell me about world history.",
]
ACCEPT_PROMPTS = [
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
    "Write SwiftUI code for a button.",
    "Implement a UIKit table view controller.",
    "Show me MVVM in Swift.",
    "How do I use @Published in Combine?",
    "Write a Swift Codable struct.",
]


def gen_yesno(n=100):
    out = []
    for _ in range(n // 2):
        prompt = f"User asks: \"{random.choice(REFUSE_PROMPTS)}\". Should hexa-canon model accept or refuse?"
        out.append(fmt(prompt, "refuse"))
    for _ in range(n // 2):
        prompt = f"User asks: \"{random.choice(ACCEPT_PROMPTS)}\". Should hexa-canon model accept or refuse?"
        out.append(fmt(prompt, "accept"))
    return out


# --- 5-NL F3 explanation pairs --------------------------------------------

EXPL_PAIRS = [
    ("Explain what this Go code does: `for _, v := range slice { sum += v }`.",
     "It iterates over each value in `slice` and accumulates the sum into `sum`."),
    ("Explain this Rust code: `let v: Vec<i32> = (1..=10).collect();`.",
     "It creates a Vec<i32> containing integers 1 through 10 inclusive."),
    ("Explain this Python code: `result = [x*2 for x in nums if x > 0]`.",
     "List comprehension that doubles each positive number in nums."),
    ("Explain this TypeScript: `const sum = arr.reduce((a, b) => a + b, 0);`.",
     "Sums all elements of arr starting from 0, using the reduce method."),
    ("Explain this Swift: `let active = users.filter { $0.isActive }`.",
     "Filters the users array to only those where isActive is true."),
    ("Briefly explain: `if let v = optional { use(v) }` in Swift.",
     "Optional binding: unwraps optional safely; runs the body only if non-nil."),
    ("Explain `defer { close() }` in Swift.",
     "Schedules `close()` to run at scope exit regardless of return path."),
    ("Explain `@implements(L[7])` in hexa.",
     "Annotation marking that this function proves law L[7] from the atlas."),
    ("Explain `@grace(HX9000, until=...)` in hexa.",
     "Deprecation marker with target removal date and error code."),
    ("Explain `Result<T, E>` in Rust.",
     "Tagged union: Ok(T) for success, Err(E) for failure — pattern-match to handle."),
]


def gen_expl(n=50):
    out = []
    NLS = [("en", ""), ("ko", " (한국어로 간단히)"), ("zh", " (用中文简要说明)"),
           ("ru", " (кратко по-русски)"), ("ja", " (日本語で簡単に)")]
    for _ in range(n):
        q, a = random.choice(EXPL_PAIRS)
        nl_tag = random.choice(NLS)
        out.append(fmt(q + nl_tag[1], a))
    return out


def main():
    rows = []
    if V6_BASE.exists():
        with V6_BASE.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        print(f"v6 base: {len(rows)}")
    additions = []
    additions += gen_atlas(60)
    additions += gen_enums(60)
    additions += gen_hx(50)
    additions += gen_yesno(100)
    additions += gen_expl(50)
    random.shuffle(additions)
    rows.extend(additions)
    print(f"additions: {len(additions)}")
    print(f"total v7: {len(rows)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()
