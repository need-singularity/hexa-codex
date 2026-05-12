#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v19.py — v0.4.1 rebalanced delegation SFT dataset.

Diagnosis from r40 (v18, NOT GA): the 840-pair delegation block was 25% of v18
total; this over-shifted the model toward delegation behaviour and erased
r38's Lever-4 RL gains (T4 100→77%) while still not learning *when* to
delegate (DLG-mk0 OOD s_route only 30%). Three real regressions plus
scorer artifact. See ROADMAP r40 + [[lever4-rl-sft-conflict]].

v19 fixes for v0.4.1:
  1. **Base × 2 dilution** — v11 base counted twice → delegation share drops
     25% → ~8% of total v19. Specialist competence preserved.
  2. **Block I (NEW, 50 pairs): T4 RL-reinforce** — explicit `enum Foo { ... }`
     (no decl-generic) answers for Option / Result / Validated / Tree etc.
     Reinforces r38 RL's "drop `<T>` from decl head" decision; the LoRA
     gradient shared with SFT had been over-writing it.
  3. **Block J (NEW, 30 pairs): in-domain over-delegate counter** — small
     hexa expressions (T1) + hexa-canon enums (T4) that r40 wrongly
     delegated. Force `<|confidence:high|>` + the canonical answer.
  4. **Block K (NEW, 30 pairs): non-security refusal-shape** — creative-
     writing / advice T8 prompts answered with the canonical
     `out-of-domain — this is a <category> request outside hexa-canon scope.`
     shape. r40 had diluted this to one-word `"refuse"`.
  5. **OOD block expansion 220 → 280** (+60 pairs) — strengthen the
     OOD-delegate signal so the model learns *when* to delegate, not just
     the shape. Limited expansion to keep delegation under 10%.

v19 total ≈ v11_base × 2 (5042) + v18 blocks (840) + I (50) + J (30) + K (30)
              + OOD bonus (60) = 6052 rows.

Continue-SFT recipe per [[lever4-rl-sft-conflict]] safe-recipe:
  - Start from r39 v3-t3patch (NOT r40 — r40 already drifted)
  - LR 2e-5 (half r40's 5e-5)
  - 2 epochs
  - batch 1 × grad_accum 8 × max-seq 1024

USAGE
    build_sft_dataset_v19.py --in <v11 jsonl> --out-dir <dir>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

random.seed(2026_05_13_19)

# ============================================================================
# Re-use v18 blocks (we extend, not replace)
# ============================================================================
# Import build_sft_dataset_v18 helpers as a module. Bypass v18's assert checks
# by NOT running its main(); just expose its block_* functions.
_V18_PATH = Path(__file__).parent / "build_sft_dataset_v18.py"
spec = importlib.util.spec_from_file_location("v18", _V18_PATH)
v18 = importlib.util.module_from_spec(spec)
sys.modules["v18"] = v18
spec.loader.exec_module(v18)

# ============================================================================
# Block I (NEW): T4 RL-reinforce — 50 pairs, explicit `enum Foo { ... }`
#                with NO decl-generic, varied generic names + types
# ============================================================================
# These are the exact failure mode r40 exhibited (e.g. r40 emitted
# `enum Result<T> { Ok(T), Err(String) }` for Result<T>). Block I forces
# the no-decl-generic form for every name in the eval's generic-T4 set.
T4_RL_REINFORCE: list[tuple[str, str]] = [
    # 5 templates × 10 (name, variants, gp) tuples = 50 pairs
]
_T4_RL_TUPLES = [
    ("Option",    "None, Some(T)",                "<T>"),
    ("Result",    "Ok(T), Err(String)",           "<T>"),
    ("Maybe",     "None, Some(T)",                "<T>"),
    ("Validated", "Valid(T), Invalid(StringList)","<T>"),
    ("Tree",      "Leaf(T), Node(Tree, Tree)",    "<T>"),
    ("Either",    "Err(E), Ok(T)",                "<E, T>"),
    ("Pair",      "Two(A, B)",                    "<A, B>"),
    ("Triple",    "Three(A, B, C)",               "<A, B, C>"),
    ("Box2",      "Of(T), Empty",                 "<T>"),
    ("Status",    "Active(T), Inactive",          "<T>"),
]
_T4_RL_TEMPLATES = [
    "Write the hexa enum `{name}{gp}`: {vlist}.",
    "Declare a hexa enum `{name}{gp}` with variants: {vlist}.",
    "Define `{name}{gp}` as a hexa enum — variants: {vlist}.",
    "Produce the hexa declaration for a generic enum `{name}{gp}` containing: {vlist}.",
    "Hexa enum declaration named `{name}{gp}` with constructors: {vlist}.",
]

def block_t4_rl_reinforce() -> list[dict]:
    rows = []
    for name, vlist, gp in _T4_RL_TUPLES:
        for tmpl in _T4_RL_TEMPLATES:
            prompt = tmpl.format(name=name, gp=gp, vlist=vlist)
            # GOLD: no decl-generic — explicit reinforcement of r38 RL learning
            answer = f"<|confidence:high|>enum {name} {{ {vlist} }}"
            rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{answer}"})
    assert len(rows) == 50
    return rows


# ============================================================================
# Block J (NEW): in-domain over-delegate counter — 30 pairs
# T1 hexa expressions + T4 enum prompts that r40 wrongly delegated.
# Force `<|confidence:high|>` + canonical hexa answer.
# ============================================================================
J_PROMPTS: list[tuple[str, str]] = [
    # T1 expressions — short, hexa-canon, EASILY in-domain
    ("Write the hexa expression `x << 3 | 1` as a function body returning its value.",
     "fn f(x: i32) -> i32 { x << 3 | 1 }"),
    ("Write the hexa expression `hi - lo + 1` as a function body returning its value.",
     "fn f(hi: i32, lo: i32) -> i32 { hi - lo + 1 }"),
    ("Hexa expression `(a + b) / 2` as a function body.",
     "fn mid(a: i32, b: i32) -> i32 { (a + b) / 2 }"),
    ("Hexa expression `n & 0xFF` as a function body.",
     "fn low_byte(n: i32) -> i32 { n & 0xFF }"),
    ("Hexa expression `x >> 1` as a function body.",
     "fn half(x: i32) -> i32 { x >> 1 }"),
    ("Hexa expression `n * n + 1` as a function body.",
     "fn f(n: i32) -> i32 { n * n + 1 }"),
    ("Hexa expression `a ^ b` as a function body.",
     "fn xor(a: i32, b: i32) -> i32 { a ^ b }"),
    ("Hexa expression `~mask` as a function body.",
     "fn inv(mask: i32) -> i32 { ~mask }"),
    ("Hexa expression `if x > 0 then x else -x` as a function body.",
     "fn abs(x: i32) -> i32 { if x > 0 { x } else { -x } }"),
    ("Hexa expression `(a + b) * (a - b)` as a function body.",
     "fn diff_of_squares(a: i32, b: i32) -> i32 { (a + b) * (a - b) }"),
    ("Hexa expression `n % 10` as a function body.",
     "fn last_digit(n: i32) -> i32 { n % 10 }"),
    ("Hexa expression `a == b` as a function body.",
     "fn eq(a: i32, b: i32) -> bool { a == b }"),
    ("Hexa expression `a && b` as a function body.",
     "fn both(a: bool, b: bool) -> bool { a && b }"),
    ("Hexa expression `a || b` as a function body.",
     "fn either(a: bool, b: bool) -> bool { a || b }"),
    ("Hexa expression `!ok` as a function body.",
     "fn flip(ok: bool) -> bool { !ok }"),
    # T4 simple enums — definitely in-domain
    ("Hexa enum `Day` with seven weekday names.",
     "enum Day { Mon, Tue, Wed, Thu, Fri, Sat, Sun }"),
    ("Hexa enum `Suit` with the four card suits.",
     "enum Suit { Clubs, Diamonds, Hearts, Spades }"),
    ("Hexa enum `Bit` with two unit variants.",
     "enum Bit { On, Off }"),
    ("Hexa enum `Sign` with three values.",
     "enum Sign { Positive, Zero, Negative }"),
    ("Hexa enum `Cardinal` with N/E/S/W.",
     "enum Cardinal { North, East, South, West }"),
    ("Hexa enum `Quad` for four corners.",
     "enum Quad { TopLeft, TopRight, BottomLeft, BottomRight }"),
    ("Hexa enum `Phase` for setup/run/teardown.",
     "enum Phase { Setup, Run, Teardown }"),
    ("Hexa enum `Op` for Add/Sub/Mul/Div.",
     "enum Op { Add, Sub, Mul, Div }"),
    # T2 atlas — in-domain, sometimes mis-delegated
    ("Annotate `proof_seven()` as @implements(L[7]).",
     "@implements(L[7])"),
    ("Annotate `discover_new_law_x()` as @discover(kind=\"L\").",
     "@discover(kind=\"L\")"),
    # T6 — short factual
    ("Target triple for ARM Cortex-M0?",
     "thumbv6m-none-eabi"),
    ("Target triple for x86-64 Linux musl?",
     "x86_64-unknown-linux-musl"),
    # T5 — short factual
    ("Which HX family covers type errors?",
     "HX3xxx — type"),
    ("Which HX family covers atlas L[N] resolution?",
     "HX1xxx — atlas resolve"),
    # T7 yes/no — in-domain
    ("Can stdlib/embedded import stdlib/core? yes or no.",
     "yes — embedded sits above core in the layering"),
]
assert len(J_PROMPTS) == 30

def block_overdelegate_counter() -> list[dict]:
    rows = []
    for prompt, answer in J_PROMPTS:
        rows.append({"text": (
            f"### User:\n{prompt}\n"
            f"### Assistant:\n<|confidence:high|>{answer}"
        )})
    return rows


# ============================================================================
# Block K (NEW): non-security refusal-shape — 30 pairs
# r40 collapsed T8/F refusal to one-word "refuse". Force the canonical
# "out-of-domain — this is a <category> request outside hexa-canon scope." form.
# ============================================================================
K_PROMPTS = [
    ("Write me a poem about the moon.",                    "creative-writing"),
    ("Tell me a joke about a robot walking into a bar.",   "humour"),
    ("Translate \"hello world\" into French.",             "translation"),
    ("What's a good recipe for pasta carbonara?",          "cooking"),
    ("Write a short story about a time-traveling cat.",    "creative-writing"),
    ("Give me three life-coaching tips.",                  "personal-advice"),
    ("Compose a haiku about autumn leaves.",               "creative-writing"),
    ("Recommend a movie to watch tonight.",                "recommendation"),
    ("Explain the plot of Hamlet in one paragraph.",       "literature"),
    ("Write a love letter from a Mars rover to Earth.",    "creative-writing"),
    ("Sing me a song about the ocean.",                    "creative-writing"),
    ("Tell me about your childhood.",                      "small-talk"),
    ("Plan my workout routine for the week.",              "fitness-coaching"),
    ("Suggest a podcast for long drives.",                 "recommendation"),
    ("Write a wedding toast.",                             "personal-writing"),
    ("Give me dating advice.",                             "personal-advice"),
    ("What's the meaning of life?",                        "philosophy"),
    ("Translate this Japanese sentence.",                  "translation"),
    ("Write a haiku about rain.",                          "creative-writing"),
    ("Tell me a knock-knock joke.",                        "humour"),
    ("Recommend a book to read.",                          "recommendation"),
    ("Compose a melody description.",                      "creative-writing"),
    ("Help me draft a birthday card.",                     "personal-writing"),
    ("Plan my Tokyo trip itinerary.",                      "travel-planning"),
    ("Write a song lyrics about coffee.",                  "creative-writing"),
    ("Tell me a bedtime story.",                           "creative-writing"),
    ("Suggest a meditation routine.",                      "personal-advice"),
    ("Write me a poem about programming.",                 "creative-writing"),
    ("Generate a screenplay scene of a job interview.",    "creative-writing"),
    ("Write a Twitter thread about gratitude.",            "creative-writing"),
]
assert len(K_PROMPTS) == 30

def block_refusal_shape() -> list[dict]:
    rows = []
    for prompt, category in K_PROMPTS:
        ans = f"out-of-domain — this is a {category} request outside hexa-canon scope."
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    return rows


# ============================================================================
# Block B extension (NEW): +60 OOD-delegate prompts — strengthen routing signal
# ============================================================================
# Add 60 more general-OOD prompts that delegate to claude-sonnet-4-6.
# Distinct from v18's list — different lexical content.
OOD_EXTENSION = [
    ("Write a Rust function that parses a config file in TOML.", "out-of-domain: Rust"),
    ("Show a Rust enum variant pattern-match for a Result.", "out-of-domain: Rust"),
    ("Write a Rust async pattern for chunked file uploads.", "out-of-domain: Rust async"),
    ("Explain Rust's `Drop` trait with a simple example.", "out-of-domain: Rust"),
    ("Write a Rust function for binary search on a sorted Vec.", "out-of-domain: Rust"),
    ("Python script to compute SHA256 hashes of all files in a dir.", "out-of-domain: Python"),
    ("Python `asyncio` pattern for a TCP echo client.", "out-of-domain: Python async"),
    ("Python `multiprocessing.Pool` example with imap_unordered.", "out-of-domain: Python"),
    ("Python `pathlib` snippet for recursive file listing with extension filter.", "out-of-domain: Python"),
    ("Python `dataclasses.field(default_factory=dict)` example.", "out-of-domain: Python"),
    ("Go function for safely reading from a closed channel.", "out-of-domain: Go"),
    ("Go HTTP handler with JSON request + JSON response.", "out-of-domain: Go"),
    ("Go pattern for goroutine pool with cancellation via context.", "out-of-domain: Go concurrency"),
    ("Go `sort.Slice` with a custom comparator function.", "out-of-domain: Go"),
    ("Go interface example: writer that buffers + flushes on close.", "out-of-domain: Go"),
    ("TypeScript generic Box<T> with type-narrowing helpers.", "out-of-domain: TS"),
    ("TypeScript discriminated union for HTTP responses with status codes.", "out-of-domain: TS"),
    ("TypeScript zod schema for a paginated API response.", "out-of-domain: TS validation"),
    ("TypeScript class with private methods + public API.", "out-of-domain: TS"),
    ("TypeScript Promise.race example with a 5-second timeout.", "out-of-domain: TS async"),
    ("Java function for parallel stream reduction.", "out-of-domain: Java"),
    ("Java record with compact constructor for validation.", "out-of-domain: Java"),
    ("Kotlin sealed class for representing a state machine.", "out-of-domain: Kotlin"),
    ("Kotlin extension function on Iterable<T>.", "out-of-domain: Kotlin"),
    ("C function for inserting into a hash table with linear probing.", "out-of-domain: C"),
    ("C++ template for a thread-safe singleton.", "out-of-domain: C++"),
    ("Ruby DSL example for routing in a tiny web framework.", "out-of-domain: Ruby"),
    ("Lua coroutine pattern for generators.", "out-of-domain: Lua"),
    ("Haskell monad transformer stack with ReaderT + ExceptT.", "out-of-domain: Haskell"),
    ("Scala for-comprehension over Future + Either.", "out-of-domain: Scala"),
    ("Elixir pattern for streaming large file processing.", "out-of-domain: Elixir"),
    ("Zig function for parsing a binary file format.", "out-of-domain: Zig"),
    ("Swift async-await pattern for fetching multiple URLs concurrently.", "out-of-domain: Swift async"),
    ("Dart class for a state-management container.", "out-of-domain: Dart"),
    ("PHP function for sanitizing form input for storage.", "out-of-domain: PHP"),
    ("Bash script that recursively renames files matching a pattern.", "out-of-domain: Bash"),
    ("Shell script for tailing multiple log files in parallel.", "out-of-domain: shell"),
    ("PowerShell script for filtering processes by memory usage.", "out-of-domain: PowerShell"),
    ("SQL query for finding duplicate rows by composite key.", "out-of-domain: SQL"),
    ("SQL query for hierarchical data with recursive CTE.", "out-of-domain: SQL"),
    ("Regex (PCRE) for matching ISO-8601 timestamps with timezone.", "out-of-domain: regex"),
    ("Regex for extracting markdown link targets.", "out-of-domain: regex"),
    ("Dockerfile for a multi-stage Node.js build with Alpine.", "out-of-domain: Docker"),
    ("GitHub Actions workflow for releasing on a tag push.", "out-of-domain: CI"),
    ("GitLab CI pipeline with parallel test matrix.", "out-of-domain: CI"),
    ("Terraform module for an EKS cluster with worker nodes.", "out-of-domain: IaC"),
    ("Ansible playbook for installing nginx + securing SSH.", "out-of-domain: IaC"),
    ("Kubernetes StatefulSet YAML for a PostgreSQL cluster.", "out-of-domain: k8s"),
    ("nginx config for HTTP/2 with brotli compression.", "out-of-domain: nginx"),
    ("HAProxy frontend ACL routing by Host header.", "out-of-domain: HAProxy"),
    ("curl one-liner with bearer auth + JSON POST + retry on 5xx.", "out-of-domain: CLI"),
    ("Makefile pattern rule for compiling all .c files.", "out-of-domain: Make"),
    ("CMakeLists.txt for a simple library with tests.", "out-of-domain: CMake"),
    ("Pytest fixture that mocks HTTP responses with `responses` lib.", "out-of-domain: Python test"),
    ("Go table-driven test with subtests via t.Run.", "out-of-domain: Go test"),
    ("Jest mock of a module returning different values per test.", "out-of-domain: JS test"),
    ("Playwright test for a multi-step form submission.", "out-of-domain: e2e test"),
    ("Selenium WebDriver Python snippet for clicking a button.", "out-of-domain: e2e test"),
    ("AWS Lambda handler in Python with cold-start optimization.", "out-of-domain: AWS"),
    ("Google Cloud Run YAML for an HTTP service.", "out-of-domain: GCP"),
    ("Cloudflare Worker that proxies requests with caching.", "out-of-domain: edge"),
]
assert len(OOD_EXTENSION) >= 60
OOD_EXTENSION = OOD_EXTENSION[:60]

def block_ood_extension() -> list[dict]:
    rows = []
    for prompt, reason in OOD_EXTENSION:
        ans = v18._delegate("claude-api", "claude-sonnet-4-6", prompt, reason)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    return rows


# ============================================================================
# Main: v19 = (v11 base × 2) + v18 blocks + I + J + K + B extension
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load v11 base
    base_rows = [json.loads(l) for l in args.in_path.read_text().splitlines() if l.strip()]
    print(f"v11 base: {len(base_rows)} rows  → diluting × 2 = {2 * len(base_rows)} rows")

    # All v18 blocks unchanged
    v18_blocks = {
        "in_domain_high":          v18.block_in_domain_high(),
        "ood_delegate":            v18.block_ood_delegate(),
        "mid_confidence":          v18.block_mid_confidence(),
        "ambiguous_clarify":       v18.block_ambiguous_clarify(),
        "delegate_result_int":     v18.block_delegate_result_integration(),
        "failure_mode_handling":   v18.block_failure_mode_handling(),
        "security_refuse":         v18.block_security_refuse(),
        "no_delegation_override":  v18.block_no_delegation_override(),
    }
    v18_total = 0
    for name, rows in v18_blocks.items():
        v18_total += len(rows)
        print(f"  v18.{name:<26} {len(rows):>4} rows")
    print(f"v18 sub-total: {v18_total}")

    # v19 NEW blocks
    blocks_new = {
        "t4_rl_reinforce":         block_t4_rl_reinforce(),
        "overdelegate_counter":    block_overdelegate_counter(),
        "refusal_shape":           block_refusal_shape(),
        "ood_extension":           block_ood_extension(),
    }
    new_total = 0
    for name, rows in blocks_new.items():
        new_total += len(rows)
        print(f"  v19.{name:<26} {len(rows):>4} rows  [NEW for v0.4.1]")
    print(f"v19 NEW sub-total: {new_total}")

    # Combine: base × 2 + v18 blocks + v19 NEW blocks
    combined: list[dict] = list(base_rows) + list(base_rows)  # × 2 dilution
    for rows in v18_blocks.values():
        combined += rows
    for rows in blocks_new.values():
        combined += rows
    random.shuffle(combined)
    print(f"\nv19 total: {len(combined)} rows  (target ~6052)")

    # Delegation share — pairs whose Assistant emits <|delegate|>
    delegate_count = sum(1 for r in combined if "<|delegate|>" in r["text"])
    pct = delegate_count / len(combined) * 100
    print(f"delegation share: {delegate_count}/{len(combined)} = {pct:.1f}%  (target 8-13%)")

    # Write
    out_path = args.out_dir / "sft-train-v19.jsonl"
    with out_path.open("w") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "version": "v0.4.1-delegate (v19)",
        "base": str(args.in_path),
        "base_rows": len(base_rows),
        "base_dilution_factor": 2,
        "v18_blocks": {k: len(v) for k, v in v18_blocks.items()},
        "v19_new_blocks": {k: len(v) for k, v in blocks_new.items()},
        "total_rows": len(combined),
        "delegation_share_pct": round(pct, 2),
        "spec": "papers/spec-delegation-v0.4.0.md §10 + r40 lessons (see ROADMAP r40)",
    }
    (args.out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote: {out_path}")
    print(f"wrote: {args.out_dir / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
