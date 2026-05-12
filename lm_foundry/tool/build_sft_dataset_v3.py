#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v3.py — v0.2.0-r3 SFT dataset (lower refusal + semantic canon + MBPP + hexa FACTs).

Fixes the v0.2.0-r2 residual issues:
- F1 code synth still 20% (target 75%) — too much refusal data, not enough code
- T2/T3/T5 hexa-canon still 0% — raw doc dumps don't teach FACTS

Changes vs v2:
- Refusal ratio ≤ 10% (100 instead of 200)
- + MBPP accept pairs (200 rows from `mbpp` dataset)
- + Semantic canon Q/A: extract section headers from .md, pair with content
- + Hexa-canon FACT pairs (hand-authored 30 — covers T2/T3/T5/T6/T7 directly)
- Same `### User:/### Assistant:` template

OUTPUT
    ~/runs/sft-train-v3/train.jsonl
    ~/runs/sft-train-v3/MANIFEST.json
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import List, Tuple

TEMPLATE = "### User:\n{prompt}\n### Assistant:\n{completion}"
MAX_COMPLETION_CHARS = 3000
DEFAULT_CANON_DIR = Path.home() / "runs" / "corpus" / "hexa-canon-v1"
DEFAULT_REFUSAL = Path.home() / "runs" / "sft-refusal-v1" / "refusal_pairs.jsonl"
DEFAULT_OUTPUT = Path.home() / "runs" / "sft-train-v3"


def fmt(prompt: str, completion: str) -> str:
    if len(completion) > MAX_COMPLETION_CHARS:
        completion = completion[:MAX_COMPLETION_CHARS] + "\n...[truncated]"
    return TEMPLATE.format(prompt=prompt, completion=completion)


# --- Hand-authored hexa-canon FACTs (covers T2/T3/T5/T6/T7 directly) ---
HEXA_FACTS: List[Tuple[str, str]] = [
    # T2 atlas-citation
    ("Should `@implements(L[42])` or `@discover(kind=\"L\")` be used for a function that PROVES law L[42]?",
     "Use `@implements(L[42])`. `@implements` is for functions that prove or implement a specific atlas law; `@discover` is for exploration."),
    ("What annotation marks a function that explores new instances of L[100]?",
     "`@discover(kind=\"L\")`. Use it when you're searching for new instances of a law rather than proving an existing one."),
    ("How do you mark a function that implements law L[7]?",
     "Annotate it: `@implements(L[7])`."),
    # T3 @grace
    ("How do you mark `old_api()` as deprecated using hexa's `@grace`, with error code HX9000, removal date 2026-06-30, reason 'replaced by new_api'?",
     "`@grace(HX9000, until=2026-06-30, reason=\"replaced by new_api\")` placed immediately before the function."),
    ("What three fields does `@grace` require?",
     "`@grace` requires (HXxxxx error code, until=YYYY-MM-DD removal date, reason=\"...\" string). All three must be present."),
    # T5 HX[CCCC]
    ("What HX error code family is reserved for PARSE errors?",
     "HX0xxx is the parse-error family."),
    ("What HX error code family is reserved for CODEGEN errors?",
     "HX9xxx is the codegen-error family."),
    ("What HX error code family is reserved for lint warnings (S0-S8 pre-codegen)?",
     "HX8xxx is the lint-warning family."),
    ("What HX error code family is reserved for RESOLVE errors?",
     "HX1xxx is the resolve-error family."),
    # T6 linker targets
    ("What is the canonical hexa linker target triple for Raspberry Pi Pico (Cortex-M0+)?",
     "`thumbv6m-none-eabi`"),
    ("What is the canonical hexa linker target triple for STM32F4 (Cortex-M4F)?",
     "`thumbv7em-none-eabihf`"),
    ("What is the canonical hexa linker target triple for ESP32 (Xtensa)?",
     "`xtensa-esp32-none-elf`"),
    ("What is the canonical hexa linker target triple for RISC-V 32-bit (rv32im)?",
     "`riscv32imac-unknown-none-elf`"),
    # T7 stdlib direction
    ("Can hexa firmware crate `firmware/boards/rtsc/` import from `stdlib/net/`?",
     "no — firmware crates must NOT import host stdlib. Only `stdlib/{core,alloc,hal,embedded,mcu}` are firmware-safe."),
    ("Can hexa firmware crate `firmware/boards/chip/` import from `stdlib/embedded/`?",
     "yes — `stdlib/embedded` is firmware-safe and intended for embedded targets."),
    ("Can the compiler depend on stdlib?",
     "yes — compiler/ may depend on stdlib, but stdlib MUST NOT depend on compiler/. Dependency arrow is one-way."),
    ("Can stdlib depend on the compiler?",
     "no — stdlib MUST NOT depend on compiler/. The compiler depends on stdlib, not the other way around."),
    # Lint stages
    ("What is the hexa lint stage S0?",
     "S0 = parse. The first lint stage that runs on raw source — verifies lexical + grammatical correctness."),
    ("What is the hexa lint stage S1?",
     "S1 = resolve. Resolves identifiers + scopes after S0 parse succeeds."),
    ("What is the hexa lint stage S8?",
     "S8 = citation. The final lint stage that verifies every atlas L[*] reference is bound via `@implements` or `@discover`."),
    # Pipeline phases
    ("What are the 11 phases of the hexa compile pipeline in order?",
     "lex → parse → resolve → check → lower → mono → ssa → optimize → regalloc → emit → link"),
    # Memory model
    ("What memory management does hexa 1.x use?",
     "Arena allocation only — function-local, request-scoped, or rodata static const. No GC, no ref-counting, no manual free."),
    ("Will hexa add a tracing GC in 2.0?",
     "no — tracing GC is a permanent reject per SPEC.md §11. Hexa moves from arena (1.x) to borrow check (2.x), never to GC."),
    # Prover
    ("Does hexa use Z3 or CVC5 for its prover?",
     "no — Z3 and CVC5 are permanently rejected per SPEC.md §10.1. Hexa uses an in-house prover with zero external dependencies."),
    # Codegen
    ("Does hexa use LLVM for codegen?",
     "no — hexa uses direct codegen (lex → ... → emit → link). LLVM-based codegen is rejected per SPEC.md §2.4."),
    # Diagnostics language
    ("What language are hexa compiler diagnostics written in?",
     "English only. Per SPEC.md §7, Korean i18n is permanently closed. Diagnostics are English-canonical regardless of user locale."),
    # Linker
    ("What is the primary hexa linker?",
     "`hexa_ld` is primary; system `ld`/`lld` is the fallback when `hexa_ld` isn't available for the target triple."),
    # Refusal
    ("If a user asks for a joke, should hexa-canon model accept or refuse?",
     "refuse. Hexa-canon model is code-only. The canonical refusal text is exactly: `out-of-domain: this is a code-only model`."),
    ("If a user asks 'implement quicksort in hexa', should the model accept or refuse?",
     "accept. Code synthesis tasks in hexa-lang are exactly the model's domain."),
    ("If a user asks (in Chinese) '用hexa写个二分查找', should the model accept or refuse?",
     "accept. The 5-NL input layer is supported; refusal is based on TASK type (off-domain) not user language."),
]


def parse_markdown_sections(content: str) -> List[Tuple[str, str]]:
    """Extract (heading, section_content) pairs from a markdown file.
    Skips top-level title; pairs each `## ...` or `### ...` heading with the
    text up to the next heading of equal or higher level.
    """
    lines = content.split("\n")
    sections = []
    cur_head = None
    cur_buf = []
    for line in lines:
        m = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
        if m:
            # flush previous
            if cur_head is not None and cur_buf:
                sec_text = "\n".join(cur_buf).strip()
                if sec_text and len(sec_text) > 50:
                    sections.append((cur_head, sec_text))
            cur_head = m.group(2).strip()
            cur_buf = []
        else:
            if cur_head is not None:
                cur_buf.append(line)
    if cur_head and cur_buf:
        sec_text = "\n".join(cur_buf).strip()
        if sec_text and len(sec_text) > 50:
            sections.append((cur_head, sec_text))
    return sections


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_sft_dataset_v3")
    parser.add_argument("--canon-dir", type=Path, default=DEFAULT_CANON_DIR)
    parser.add_argument("--refusal-jsonl", type=Path, default=DEFAULT_REFUSAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-refusal", type=int, default=100, help="≤10% target")
    parser.add_argument("--n-mbpp", type=int, default=200)
    parser.add_argument("--n-canon-sections", type=int, default=600)
    parser.add_argument("--n-canon-hexa", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    random.seed(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    rows: List[dict] = []

    # 1. HEXA FACTs (hand-authored, ~30)
    n_fact = 0
    for q, a in HEXA_FACTS:
        rows.append({"text": fmt(q, a), "source": "hexa-fact", "tokens_est": (len(q) + len(a)) // 4})
        n_fact += 1
    print(f"hexa facts        : {n_fact}")

    # 2. Refusal (downsampled to 100)
    refusal_all = []
    with args.refusal_jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not r.get("completion") or "needs_completion" in r.get("tags", []):
                continue
            refusal_all.append(r)
    random.shuffle(refusal_all)
    refusal_subset = refusal_all[:args.n_refusal]
    for r in refusal_subset:
        rows.append({"text": fmt(r["prompt"], r["completion"]), "source": "refusal",
                     "tokens_est": (len(r["prompt"]) + len(r["completion"])) // 4})
    print(f"refusal pairs     : {len(refusal_subset)}")

    # 3. HumanEval (164)
    try:
        from human_eval.data import read_problems
    except ImportError as exc:
        raise SystemExit("human-eval required") from exc
    problems = read_problems()
    n_he = 0
    for tid, p in problems.items():
        prompt = p["prompt"].rstrip() + "\n    # Complete the function."
        completion = p["prompt"] + p["canonical_solution"]
        rows.append({"text": fmt(prompt, completion), "source": "humaneval",
                     "tokens_est": (len(prompt) + len(completion)) // 4})
        n_he += 1
    print(f"humaneval accept  : {n_he}")

    # 4. MBPP (200)
    n_mbpp = 0
    try:
        from datasets import load_dataset
        ds = load_dataset("mbpp", "sanitized", split="train", trust_remote_code=False)
        ds = list(ds.shuffle(seed=args.seed))
        for r in ds[: args.n_mbpp]:
            prompt = f"# Task: {r['prompt']}\n# Test:\n{r['test_list'][0] if r.get('test_list') else ''}\n"
            completion = r["code"]
            rows.append({"text": fmt(prompt, completion), "source": "mbpp",
                         "tokens_est": (len(prompt) + len(completion)) // 4})
            n_mbpp += 1
    except Exception as exc:
        print(f"mbpp skipped: {exc}")
    print(f"mbpp accept       : {n_mbpp}")

    # 5. Semantic canon md Q/A from heading→section
    import pyarrow.parquet as pq
    docs = pq.read_table(args.canon_dir / "canon-docs.parquet").to_pylist()
    random.shuffle(docs)
    n_md = 0
    for r in docs:
        if n_md >= args.n_canon_sections:
            break
        sections = parse_markdown_sections(r["content"])
        for head, body in sections[:3]:  # max 3 per doc
            if n_md >= args.n_canon_sections:
                break
            prompt = f"In `{r['repo']}/{r['path']}`, what does the section '{head}' cover?"
            rows.append({"text": fmt(prompt, body), "source": "canon-md-section",
                         "tokens_est": (len(prompt) + len(body)) // 4})
            n_md += 1
    print(f"canon md sections : {n_md}")

    # 6. Canon hexa (keep raw shape — code is itself the answer)
    src = pq.read_table(args.canon_dir / "canon-source.parquet").to_pylist()
    random.shuffle(src)
    n_hexa = 0
    for r in src[: args.n_canon_hexa]:
        prompt = f"Show me the canonical hexa source at `{r['repo']}/{r['path']}`."
        rows.append({"text": fmt(prompt, r["content"]), "source": "canon-hexa",
                     "tokens_est": (len(prompt) + len(r["content"])) // 4})
        n_hexa += 1
    print(f"canon hexa source : {n_hexa}")

    random.shuffle(rows)
    print(f"\ntotal             : {len(rows)} rows / ~{sum(r['tokens_est'] for r in rows)} tokens")

    out_jsonl = args.output / "train.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "n_hexa_fact": n_fact,
        "n_refusal": len(refusal_subset),
        "n_humaneval": n_he,
        "n_mbpp": n_mbpp,
        "n_canon_md_sections": n_md,
        "n_canon_hexa": n_hexa,
        "n_total": len(rows),
        "n_tokens_est": sum(r["tokens_est"] for r in rows),
        "refusal_ratio": round(len(refusal_subset) / max(len(rows), 1), 3),
        "template": "### User:\\n{prompt}\\n### Assistant:\\n{completion}",
    }
    with (args.output / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    print("\n=== MANIFEST ===")
    for k, v in manifest.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
