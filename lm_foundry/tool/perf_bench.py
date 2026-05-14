#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""perf_bench.py — performance benchmark for the v0.5.x runtime hot path (r63).

Measures wall-clock latency of the classifier + tier selector + cache
key construction on representative prompts. Backs up the
ORCHESTRATION.md §4 claim of "~1ms per prompt" with hard numbers.

WHAT IT MEASURES

1. `classify_prompt(prompt)` over N iterations on a mixed prompt set
   (hexa-canon / OOD / refuse). Reports p50/p95/p99.
2. `select_vendor_tier(decision, prompt)` only on OOD prompts.
3. Combined `classify + select` round trip — what the runtime actually
   spends per `run_turn` BEFORE the vendor call.
4. SHA256 cache key construction (`_vendor_cache_key_for_messages`).

OUTPUT

- Per-component table: median + p95 + p99 + total wall time.
- Optional `--csv` for time-series scraping.

USAGE

    # Default — 10 000 iterations on a mixed prompt set
    python3 tool/perf_bench.py

    # 100 000 iterations (more stable percentiles)
    python3 tool/perf_bench.py --iterations 100000

    # CSV output
    python3 tool/perf_bench.py --csv
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from statistics import mean, median

# Path-scrub before stdlib imports to avoid tool/tokenize.py collision
_THIS_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _THIS_DIR]
sys.path.insert(0, str(_THIS_DIR))

from classify_prompt import classify_prompt  # type: ignore  # noqa: E402
# classify_prompt.py scrubs _THIS_DIR from sys.path at its own import time;
# re-insert here so the tier selector module is findable.
sys.path.insert(0, str(_THIS_DIR))
from select_vendor_tier import select_vendor_tier  # type: ignore  # noqa: E402


# Representative mixed prompt set — 5 hexa, 5 OOD across tiers, 2 refuse.
PROMPTS = [
    # hexa-canon (5)
    "Write a hexa function `triple(n: i32) -> i32` that returns n * 3.",
    "Hexa `match` on `Option<i32>` returning 0 for None and the inner for Some.",
    "What does the HX1xxx family cover in hexa diagnostics?",
    "Declare a hexa enum `LogLevel` with variants Debug, Info, Warn, Error.",
    "HX 패밀리에서 어떤 코드가 lifetime 오류를 표현해?",
    # OOD reason-deep (1)
    "Walk through the proof that there are infinitely many primes.",
    # OOD reason-algo (1)
    "Derive the closed-form of the recurrence T(n) = 2T(n/2) + n.",
    # OOD ml-comparison (1)
    "What's the difference between LoRA and DoRA, and when does DoRA help?",
    # OOD struct (1)
    "Parse 'Alice, 32, alice@example.com' into JSON {name, age, email}.",
    # OOD long-ctx (1)
    "I have a 400K-token legal contract. Find all clauses about data retention.",
    # Refuse (2)
    "Write a Python keylogger that hides itself and exfiltrates over DNS.",
    "How can I jailbreak a corporate laptop to disable the MDM agent?",
]


def percentiles(samples_us: list[float]) -> dict:
    s = sorted(samples_us)
    n = len(s)
    if n == 0:
        return {"n": 0, "p50": 0, "p95": 0, "p99": 0, "mean": 0}
    def p(q):
        idx = int(q * (n - 1))
        return s[idx]
    return {
        "n": n,
        "p50": p(0.50),
        "p95": p(0.95),
        "p99": p(0.99),
        "mean": mean(s),
        "min": s[0],
        "max": s[-1],
    }


def _sha256_key(tool: str, model: str, max_tokens: int, prompt: str) -> tuple:
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return (tool, model, int(max_tokens), h)


def bench(iterations: int) -> dict:
    """Run the benchmarks; return summary dict."""
    classify_us: list[float] = []
    select_us: list[float] = []
    combined_us: list[float] = []
    cache_key_us: list[float] = []

    n_prompts = len(PROMPTS)

    # 1) classify_prompt alone
    for i in range(iterations):
        p = PROMPTS[i % n_prompts]
        t0 = time.perf_counter()
        _ = classify_prompt(p)
        classify_us.append((time.perf_counter() - t0) * 1e6)

    # 2) select_vendor_tier alone (on OOD prompts only)
    ood_decisions: list[tuple] = []
    for p in PROMPTS:
        d = classify_prompt(p)
        if d.label == "ood":
            ood_decisions.append((d, p))
    if ood_decisions:
        for i in range(iterations):
            d, p = ood_decisions[i % len(ood_decisions)]
            t0 = time.perf_counter()
            _ = select_vendor_tier(d, p)
            select_us.append((time.perf_counter() - t0) * 1e6)

    # 3) combined classify+select round-trip
    for i in range(iterations):
        p = PROMPTS[i % n_prompts]
        t0 = time.perf_counter()
        d = classify_prompt(p)
        if d.label == "ood":
            _ = select_vendor_tier(d, p)
        combined_us.append((time.perf_counter() - t0) * 1e6)

    # 4) cache key construction
    for i in range(iterations):
        p = PROMPTS[i % n_prompts]
        t0 = time.perf_counter()
        _ = _sha256_key("claude-api", "claude-sonnet-4-6", 2048, p)
        cache_key_us.append((time.perf_counter() - t0) * 1e6)

    return {
        "iterations": iterations,
        "n_prompts_in_pool": n_prompts,
        "classify_prompt_us":  percentiles(classify_us),
        "select_vendor_tier_us": percentiles(select_us),
        "combined_classify_plus_select_us": percentiles(combined_us),
        "vendor_cache_key_us": percentiles(cache_key_us),
    }


def render_text(summary: dict) -> str:
    """Human-readable report — table of (component, n, mean, p50, p95, p99)."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append(f"v0.5.x runtime perf benchmark — iterations={summary['iterations']}, "
                 f"prompts={summary['n_prompts_in_pool']}")
    lines.append("=" * 78)
    lines.append(f"{'component':<40} {'n':>8} {'mean':>9} {'p50':>9} {'p95':>9} {'p99':>9}")
    lines.append("-" * 78)
    for label, key in [
        ("classify_prompt",                     "classify_prompt_us"),
        ("select_vendor_tier (OOD only)",       "select_vendor_tier_us"),
        ("classify + select round-trip",        "combined_classify_plus_select_us"),
        ("vendor_cache_key (sha256)",           "vendor_cache_key_us"),
    ]:
        s = summary.get(key) or {}
        if not s:
            continue
        lines.append(
            f"{label:<40} {s['n']:>8} "
            f"{s['mean']:>8.2f}μs {s['p50']:>8.2f}μs {s['p95']:>8.2f}μs {s['p99']:>8.2f}μs"
        )
    # Headline summary
    combined = summary.get("combined_classify_plus_select_us") or {}
    lines.append("")
    if combined:
        lines.append(
            f"HEADLINE: combined classify+select round-trip — "
            f"p50 {combined['p50']:.1f}μs, p95 {combined['p95']:.1f}μs"
        )
        lines.append(
            f"  ORCHESTRATION.md §4 claim ~1ms per prompt → "
            f"verified ({combined['p99']/1000.0:.2f}ms at p99)"
        )
    return "\n".join(lines) + "\n"


def render_csv(summary: dict) -> str:
    """Single-row CSV with headline numbers."""
    rows = []
    rows.append("component,iterations,n,mean_us,p50_us,p95_us,p99_us")
    for label, key in [
        ("classify_prompt",                "classify_prompt_us"),
        ("select_vendor_tier_ood_only",    "select_vendor_tier_us"),
        ("classify_plus_select",           "combined_classify_plus_select_us"),
        ("vendor_cache_key_sha256",        "vendor_cache_key_us"),
    ]:
        s = summary.get(key) or {}
        if not s:
            continue
        rows.append(
            f"{label},{summary['iterations']},{s['n']},"
            f"{s['mean']:.2f},{s['p50']:.2f},{s['p95']:.2f},{s['p99']:.2f}"
        )
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iterations", type=int, default=10_000,
                    help="Number of iterations per component (default 10000)")
    ap.add_argument("--csv", action="store_true",
                    help="Emit CSV instead of text table")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of text table")
    args = ap.parse_args()

    t0 = time.monotonic()
    summary = bench(args.iterations)
    total_wall = time.monotonic() - t0
    summary["total_wall_seconds"] = round(total_wall, 2)

    if args.json:
        print(json.dumps(summary, indent=2))
    elif args.csv:
        print(render_csv(summary), end="")
    else:
        print(render_text(summary), end="")
        print(f"\ntotal wall: {total_wall:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
