#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_delegate_bootstrap.py — v0.4.3 SFT bootstrap for routing-RL.

40 ONLY-delegate pairs across the categories where r42 routing-RL hit
exploration collapse (s_route=0 on OOD/ambiguous/long-context). Just
enough explicit `<|delegate|>{...}<|/delegate|>` exemplars to seed the
schema shape, so r43's GRPO group-rollouts have positive-class signals
to amplify.

Per the [[pure-rl-exploration-collapse]] lesson: pure RL fails when
baseline rate on the target token class is ~0. Bootstrap is small
(40 pairs ≪ v18's 840) so it can't over-train and erase the specialist
the way r40/r41 did.

Distribution (matches DLG-mk0 §9.A on the must-delegate categories):
   20 OOD-delegate / claude-sonnet (general code, popular non-hexa langs)
    5 hard-reasoning / claude-opus  (math derivations, proofs)
    5 structured-output / openai-mini
    5 long-context / gemini-2.5-pro
    5 ambiguous / claude-sonnet (with clarifying re-formulation in prompt)

Eval holdout: NONE of these prompts appear in
`eval/delegation-mk0/manifest.jsonl` or `rl_routing_prompts.jsonl`.

USAGE
    build_sft_delegate_bootstrap.py --out <path>
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

random.seed(2026_05_13_43)


def _delegate_json(tool: str, model: str, prompt: str, reason: str,
                    max_tokens: int = 2048) -> str:
    """Construct a canonical <|delegate|>{...}<|/delegate|> emission."""
    obj = {
        "tool": tool, "model": model, "prompt": prompt,
        "max_tokens": max_tokens, "reason": reason,
    }
    return f"<|delegate|>{json.dumps(obj, ensure_ascii=False)}<|/delegate|>"


# ============================================================================
# 20 OOD claude-sonnet — general-purpose non-hexa code/explanation
# ============================================================================
OOD_SONNET: list[tuple[str, str]] = [
    ("Write a Rust async function that retries an HTTP call with exponential backoff.",
     "out-of-domain: Rust async"),
    ("Show a Python class implementing a thread-safe LRU cache.",
     "out-of-domain: Python concurrency"),
    ("Write a Go function for finding the longest common substring.",
     "out-of-domain: Go algorithms"),
    ("Explain how WebSocket frames are encoded at the byte level.",
     "out-of-domain: networking"),
    ("Show a TypeScript decorator for HTTP route registration.",
     "out-of-domain: TS decorator"),
    ("Write a Kotlin coroutine pattern for cancellation-safe IO.",
     "out-of-domain: Kotlin coroutines"),
    ("Implement a Bloom filter in C with a chosen hash family.",
     "out-of-domain: C data structures"),
    ("Write a Swift function for parsing a JSON Web Token without external libs.",
     "out-of-domain: Swift JWT"),
    ("Explain Java's `volatile` semantics with a memory-visibility example.",
     "out-of-domain: Java memory model"),
    ("Write a Ruby method that benchmarks a block with iteration count.",
     "out-of-domain: Ruby"),
    ("Show a Haskell function using `State` monad to thread a counter.",
     "out-of-domain: Haskell monad"),
    ("Write a Scala higher-order function for curry+compose chaining.",
     "out-of-domain: Scala FP"),
    ("Implement merge-sort in Erlang using pattern matching.",
     "out-of-domain: Erlang"),
    ("Show an Elixir GenServer that broadcasts events to subscribers.",
     "out-of-domain: Elixir GenServer"),
    ("Write a Bash script that monitors disk usage and alerts on threshold.",
     "out-of-domain: Bash"),
    ("Explain Docker's overlay filesystem and how layers compose.",
     "out-of-domain: Docker internals"),
    ("Write a SQL query (PostgreSQL) for the median value in a column.",
     "out-of-domain: SQL"),
    ("Implement Dijkstra's algorithm in Java with a priority queue.",
     "out-of-domain: Java algorithms"),
    ("Show a TypeScript Express middleware for request rate limiting.",
     "out-of-domain: TS Express"),
    ("Write a Python regex (with re.VERBOSE) for parsing semver strings.",
     "out-of-domain: Python regex"),
]
assert len(OOD_SONNET) == 20


# ============================================================================
# 5 hard-reasoning claude-opus
# ============================================================================
HARD_OPUS: list[tuple[str, str]] = [
    ("Derive the Cauchy-Schwarz inequality from the discriminant of a quadratic.",
     "hard reasoning: math derivation"),
    ("Prove that the determinant is multiplicative: det(AB) = det(A)·det(B).",
     "hard reasoning: linear algebra"),
    ("Show that the chromatic number of a planar graph is at most 4 (sketch).",
     "hard reasoning: graph theory"),
    ("Walk through the proof that every well-formed expression has a unique parse.",
     "hard reasoning: formal languages"),
    ("Prove the Bellman-Ford correctness on graphs with no negative cycle.",
     "hard reasoning: algorithm proof"),
]
assert len(HARD_OPUS) == 5


# ============================================================================
# 5 structured-output openai-mini
# ============================================================================
STRUCT_OAI: list[tuple[str, str]] = [
    ("Parse this address book entry into JSON {name, email, phone, address}: 'Bob Lee, bob@x.com, +1-555-0123, 100 Main St'.",
     "structured output: openai Structured Outputs"),
    ("Extract every URL from the following paragraph and return JSON array of {url, scheme, host}.",
     "structured output: openai"),
    ("Classify this product review as positive/neutral/negative and return JSON {sentiment, score, keywords}.",
     "structured output: openai"),
    ("Convert this Markdown nested list to a hierarchical JSON tree.",
     "structured conversion: openai"),
    ("Validate that a JSON object matches schema {order:{id:int, lines:[{sku,qty}]}} and return errors.",
     "structured validation: openai"),
]
assert len(STRUCT_OAI) == 5


# ============================================================================
# 5 long-context gemini-2.5-pro
# ============================================================================
LONGCTX_GEMINI: list[tuple[str, str]] = [
    ("Across this 600K-token archive of historical letters, extract every dated reference to a financial transaction.",
     "long-context: gemini 2M ctx"),
    ("Walk through this 900K-token codebase dump and emit a JSON dependency graph between modules.",
     "long-context: gemini 2M ctx"),
    ("Cross-reference 300K tokens of customer-support transcripts with 200K tokens of release notes; surface unaddressed complaints.",
     "long-context: gemini 2M ctx"),
    ("Summarise this 800K-token medical-guideline corpus organised by condition, in JSON.",
     "long-context: gemini 2M ctx"),
    ("From a 1.2M-token meeting transcript collection, extract action items grouped by participant.",
     "long-context: gemini 2M ctx"),
]
assert len(LONGCTX_GEMINI) == 5


# ============================================================================
# 5 ambiguous with clarifying re-formulation (claude-sonnet)
# ============================================================================
AMBIGUOUS_REFORM: list[tuple[str, str]] = [
    ("Help me debug this.",
     "User said 'help me debug this' without code or error. Please ask: which programming language, what error message or unexpected behaviour they observe, and a minimal repro snippet."),
    ("Make it cleaner.",
     "User said 'make it cleaner' without code in context. Please ask for the code + the target language + project style guide (if any) + which dimension to clean (readability / structure / naming)."),
    ("Speed this up.",
     "User said 'speed this up' without code or profile. Please ask for the code, the current measured runtime, the target runtime, and the input size that the timing is at."),
    ("Why won't it compile?",
     "User said 'why won't it compile' without the source or compiler output. Please ask for both: the failing code (or filename) and the exact compiler error message + version."),
    ("Add proper error handling.",
     "User said 'add proper error handling' without code in context. Please ask: which code, which error model the project uses (Result/Option/exceptions/error-return), and which dimensions to harden (network/disk/validation/cancellation)."),
]
assert len(AMBIGUOUS_REFORM) == 5


def gen_pairs() -> list[dict]:
    rows: list[dict] = []
    # OOD claude-sonnet
    for prompt, reason in OOD_SONNET:
        ans = _delegate_json("claude-api", "claude-sonnet-4-6", prompt, reason)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # Hard claude-opus
    for prompt, reason in HARD_OPUS:
        ans = _delegate_json("claude-api", "claude-opus-4-7", prompt, reason, max_tokens=4096)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # Structured openai-mini
    for prompt, reason in STRUCT_OAI:
        ans = _delegate_json("openai-api", "gpt-5-mini", prompt, reason)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # Long-context gemini-pro
    for prompt, reason in LONGCTX_GEMINI:
        ans = _delegate_json("gemini-api", "gemini-2.5-pro", prompt, reason, max_tokens=8192)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    # Ambiguous with clarifying re-formulation
    for prompt, reform in AMBIGUOUS_REFORM:
        ans = _delegate_json("claude-api", "claude-sonnet-4-6", reform,
                              "ambiguous prompt — needs clarification", max_tokens=1024)
        rows.append({"text": f"### User:\n{prompt}\n### Assistant:\n{ans}"})
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    rows = gen_pairs()
    random.shuffle(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {args.out}  ({len(rows)} pairs)")

    # Sanity: every row's assistant emits <|delegate|>...<|/delegate|>.
    n_delegate = sum(1 for r in rows if "<|delegate|>" in r["text"] and "<|/delegate|>" in r["text"])
    print(f"with <|delegate|>: {n_delegate}/{len(rows)} (must be {len(rows)})")
    assert n_delegate == len(rows)

    # Vendor distribution
    by_tool: dict[str, int] = {}
    for r in rows:
        for tool in ("claude-api", "openai-api", "gemini-api"):
            if f'"tool": "{tool}"' in r["text"] or f'"tool":"{tool}"' in r["text"]:
                by_tool[tool] = by_tool.get(tool, 0) + 1
                break
    print("tool distribution:")
    for k, v in sorted(by_tool.items()):
        print(f"  {k:<14} {v:>4}")

    # Eval-holdout sanity vs delegation-mk0 + rl_routing_prompts (if exist)
    here = Path(__file__).parent.parent
    for path in [here / "eval" / "delegation-mk0" / "manifest.jsonl",
                 here / ".." / "tmp" / "rl_routing_prompts.jsonl",  # unlikely co-located
                 Path("/tmp/rl_routing_prompts.jsonl")]:
        if path.exists():
            try:
                eval_prompts = {json.loads(l).get("prompt", "")
                                for l in path.read_text().splitlines() if l.strip()}
            except Exception:
                continue
            # Extract user prompts from our SFT rows
            sft_prompts = set()
            for r in rows:
                if "### User:\n" in r["text"]:
                    body = r["text"].split("### User:\n", 1)[1].split("\n### Assistant:\n", 1)[0]
                    sft_prompts.add(body)
            overlap = eval_prompts & sft_prompts
            print(f"holdout vs {path.name}: {len(overlap)} overlap (must be 0)")
            assert not overlap

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
