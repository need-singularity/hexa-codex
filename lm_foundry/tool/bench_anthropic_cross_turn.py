#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""bench_anthropic_cross_turn.py — production-telemetry ROI (r64 v2).

ORCHESTRATION.md §15 honesty caveat: r62's cross-turn `cache_control`
"shipped per SDK docs but NOT YET MEASURED". r64 measures it.

r64-v1 LESSON (kept in this docstring for the record): the first
attempt routed prompts through the full `run_turn → classifier →
tier_selector` chain, which bounced turns across opus / sonnet (
ml-comparison demotion fired on turn 3 due to "trade-offs vs").
Anthropic prompt-cache is per-model namespace, so cross-turn caching
did not engage. Plus we only captured `cache_read_input_tokens`,
hiding `cache_creation_input_tokens` entirely.

r64-v2 (this) FIXES both:
1. Bypasses the classifier+selector by calling `_anthropic_call`
   directly with a forced model. This makes the model-namespace
   uniform across turns.
2. Calls `_anthropic_call` BOTH with and without the cache marker
   (we mark the messages explicitly in this script using
   `_anthropic_cache_mark`), capturing `cache_read_input_tokens`
   AND `cache_creation_input_tokens` separately.

The 4-turn conversation is identical across A/B; the only
difference is whether the marker is applied.

NUMBERS REPORTED PER TURN
- input_tokens (fresh, never-seen-before tokens billed at full rate)
- cache_create_tokens (first-write premium; billed at 1.25× input rate)
- cache_read_tokens (subsequent-read savings; billed at 0.10× input rate)
- output_tokens (model response, billed at output rate)
- cost_usd (computed from r47 pricing table)

USAGE
    # Real run on sonnet (recommended — 1024 tok minimum cache size)
    python3 tool/bench_anthropic_cross_turn.py

    # Test on haiku (cheaper; 2048 tok minimum may not engage cache)
    python3 tool/bench_anthropic_cross_turn.py --model claude-haiku-4-5-20251001

    # Dry-run
    python3 tool/bench_anthropic_cross_turn.py --dry-run
"""
from __future__ import annotations

# Scrub tool/ from sys.path BEFORE stdlib imports
import os as _os  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_THIS_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _THIS_DIR]

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass  # noqa: E402

sys.path.insert(0, str(_THIS_DIR))

from forge_runtime import (  # type: ignore  # noqa: E402
    ForgeRuntimeConfig, _anthropic_call, _anthropic_cache_mark,
)


# 4-turn conversation designed for cache-hit testability:
#   - Turn 1 establishes a long context (Claude returns a long answer)
#   - Turns 2-4 ride on that prefix, each adding a short follow-up
# The prior turns + assistant answers compound, growing the cacheable
# prefix monotonically. We want the prefix to exceed sonnet's 1024-
# token minimum cache size by turn 2 ideally.
CONVERSATION = [
    "Explain rotary positional embedding (RoPE) in detail: motivation, "
    "the rotation matrix construction, how it encodes relative position "
    "through dot product invariance, and why it generalizes to lengths "
    "unseen at training time. Include the key equations.",
    "How does it compare to ALiBi attention for length extrapolation?",
    "And what about for very long contexts above 200K tokens — does the "
    "frequency scaling matter?",
    "Summarize the three most important takeaways in one paragraph.",
]


@dataclass
class TurnMeasurement:
    turn_idx: int
    config_label: str
    user_prompt_preview: str
    text_preview: str
    ok: bool
    input_tokens: int            # fresh / never-cached
    cache_create_tokens: int      # first-write premium
    cache_read_tokens: int        # subsequent-read savings
    output_tokens: int
    cost_usd: float
    latency_ms: int


def run_one_conversation(model: str, cfg: ForgeRuntimeConfig,
                          conv_prompts: list[str], use_cache_marker: bool,
                          config_label: str, pause_seconds: float
                          ) -> list[TurnMeasurement]:
    """Run conv through `_anthropic_call` directly; build messages list
    cumulatively in this script (bypass run_turn's classifier path).
    """
    messages: list[dict] = []
    out: list[TurnMeasurement] = []
    for i, user_prompt in enumerate(conv_prompts):
        # Append the new user turn to history
        messages.append({"role": "user", "content": user_prompt})

        # Optionally apply the cache marker on the second-to-last msg.
        # `_anthropic_cache_mark` returns a fresh list, doesn't mutate.
        msgs_to_send = _anthropic_cache_mark(messages) if (use_cache_marker and len(messages) >= 2) else messages

        t0 = time.time()
        ok, text, usage, err = _anthropic_call(
            model=model, prompt="", max_tokens=512, cfg=cfg, messages=msgs_to_send,
        )
        latency_ms = int((time.time() - t0) * 1000)

        if not ok:
            print(f"  WARN: turn {i+1} failed ({err}); skipping")
            out.append(TurnMeasurement(
                turn_idx=i+1, config_label=config_label,
                user_prompt_preview=user_prompt[:60], text_preview="(failed)",
                ok=False, input_tokens=0, cache_create_tokens=0,
                cache_read_tokens=0, output_tokens=0, cost_usd=0.0,
                latency_ms=latency_ms,
            ))
            # We can't append to history without an assistant turn.
            messages.pop()  # remove the un-answered user turn
            continue

        # Append the assistant response to history for next turn
        messages.append({"role": "assistant", "content": text})

        in_fresh   = int(usage.get("input_tokens", 0))
        cache_cr   = int(usage.get("cache_create_tokens", 0))
        cache_rd   = int(usage.get("cached_tokens", 0))
        # input_tokens in our usage dict is FRESH + cache_create + cache_read; back it out
        in_only = in_fresh - cache_cr - cache_rd
        out.append(TurnMeasurement(
            turn_idx=i+1, config_label=config_label,
            user_prompt_preview=user_prompt[:60],
            text_preview=text[:60].replace("\n", " "),
            ok=True,
            input_tokens=in_only,
            cache_create_tokens=cache_cr,
            cache_read_tokens=cache_rd,
            output_tokens=int(usage.get("output_tokens", 0)),
            cost_usd=float(usage.get("cost_usd", 0.0)),
            latency_ms=latency_ms,
        ))
        print(f"  ✓ turn {i+1}: fresh={in_only} cache_create={cache_cr} cache_read={cache_rd} "
              f"out={usage['output_tokens']} cost=${usage['cost_usd']:.6f} {latency_ms}ms")
        if i < len(conv_prompts) - 1:
            time.sleep(pause_seconds)
    return out


def render_summary(ma: list[TurnMeasurement], mb: list[TurnMeasurement],
                    model: str) -> str:
    lines: list[str] = []
    lines.append("=" * 96)
    lines.append(f"ANTHROPIC CROSS-TURN PROMPT-CACHE ROI (r64 v2) — model: {model}")
    lines.append("=" * 96)
    lines.append("Config A = cache marker ON  (anthropic_cross_turn_cache_enabled=True, r62 default)")
    lines.append("Config B = cache marker OFF (anthropic_cross_turn_cache_enabled=False)")
    lines.append("Direct `_anthropic_call` (bypass classifier+selector) ensures uniform model namespace.")
    lines.append("")
    lines.append(f"{'turn':<5} {'cfg':<5} {'fresh':>6} {'cr+':>6} {'rd+':>6} {'out':>5} "
                 f"{'cost USD':>11} {'lat ms':>7}")
    lines.append("-" * 96)
    n = max(len(ma), len(mb))
    for i in range(n):
        for measurements, label in ((ma, "A"), (mb, "B")):
            if i < len(measurements):
                m = measurements[i]
                lines.append(
                    f"{m.turn_idx:<5} {m.config_label:<5} "
                    f"{m.input_tokens:>6} {m.cache_create_tokens:>6} {m.cache_read_tokens:>6} "
                    f"{m.output_tokens:>5} {m.cost_usd:>11.6f} {m.latency_ms:>7}"
                )
        if i < n - 1:
            lines.append("")
    lines.append("=" * 96)
    lines.append("AGGREGATES")
    lines.append("=" * 96)
    def total(ms: list[TurnMeasurement], attr: str) -> int | float:
        return sum(getattr(m, attr) for m in ms)
    fields = [
        ("input_tokens",        "fresh input tokens"),
        ("cache_create_tokens", "cache CREATE tokens (first write premium)"),
        ("cache_read_tokens",   "cache READ tokens (savings)"),
        ("output_tokens",       "output tokens"),
        ("cost_usd",            "total cost USD"),
    ]
    lines.append(f"{'metric':<42} {'config A':>15} {'config B':>15} {'delta':>14} {'A vs B':>10}")
    lines.append("-" * 96)
    for attr, label in fields:
        a = total(ma, attr)
        b = total(mb, attr)
        delta = a - b
        if isinstance(a, float):
            a_s, b_s, d_s = f"${a:.6f}", f"${b:.6f}", f"${delta:+.6f}"
        else:
            a_s, b_s, d_s = f"{a}", f"{b}", f"{delta:+}"
        if b != 0 and b != 0.0:
            pct = f"{(a - b) / b * 100:+.1f}%"
        else:
            pct = "(B=0)"
        lines.append(f"{label:<42} {a_s:>15} {b_s:>15} {d_s:>14} {pct:>10}")

    # Verdict
    lines.append("")
    cost_a = total(ma, "cost_usd")
    cost_b = total(mb, "cost_usd")
    cache_rd_a = total(ma, "cache_read_tokens")
    cache_cr_a = total(ma, "cache_create_tokens")
    if cache_rd_a > 0 and cost_a < cost_b:
        savings_pct = (cost_b - cost_a) / cost_b * 100
        lines.append(
            f"VERDICT: Cross-turn cache_control SAVES ${cost_b - cost_a:.6f} "
            f"({savings_pct:.1f}% reduction) over {len(ma)} turns."
        )
        lines.append(
            f"         {cache_rd_a:,} tokens served from cache (read at 10% input rate); "
            f"{cache_cr_a:,} tokens cached (write at 125% input rate)."
        )
    elif cache_cr_a > 0 and cache_rd_a == 0:
        lines.append(
            f"VERDICT: Config A only CREATED cache ({cache_cr_a:,} tokens) but never "
            f"READ from it (likely too short a conversation; cache hits on "
            f"subsequent turns of THIS conv but not the first turn that wrote)."
        )
        lines.append(
            f"         For longer convs (≥5-6 turns) ROI compounds; r64 demonstrates "
            f"the mechanism, not steady-state savings."
        )
    elif cache_rd_a == 0 and cache_cr_a == 0:
        lines.append(
            "VERDICT: No cache activity in Config A. Likely cause:"
        )
        lines.append(
            f"         - Prefix below model's minimum cache size "
            f"(1024 sonnet/opus, 2048 haiku)"
        )
        lines.append(
            f"         - Pause between turns exceeded 5-min TTL (unlikely with current pause)"
        )
    else:
        lines.append(
            f"VERDICT: Mixed — Config A cost (${cost_a:.6f}) vs Config B (${cost_b:.6f}). "
            f"Cache_create premium not yet recovered by cache_read savings."
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="claude-sonnet-4-6",
                    help="Anthropic model id (default sonnet; min cache 1024)")
    ap.add_argument("--pause", type=float, default=1.0,
                    help="Pause between turns in seconds (rate-limit + TTL window)")
    ap.add_argument("--output", type=Path,
                    default=Path("bench/score-anthropic-xt-r64"),
                    help="Output directory for artifacts")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print plan, no API calls")
    args = ap.parse_args()

    prompts = CONVERSATION

    print("=" * 80)
    print(f"r64 anthropic cross-turn cache ROI measurement (v2 — direct _anthropic_call)")
    print(f"  model: {args.model}  (min cache size: "
          f"{'1024 tok' if 'sonnet' in args.model or 'opus' in args.model else '2048 tok'})")
    print(f"  turns: {len(prompts)}")
    print(f"  pause: {args.pause}s between turns")
    print("=" * 80)
    print("Conversation prompts:")
    for i, p in enumerate(prompts):
        print(f"  [{i+1}] {p[:90]}{'...' if len(p) > 90 else ''}")
    print()
    if args.dry_run:
        print("DRY-RUN — no API calls.")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)

    # Load keys via from_env; uses the same secret-CLI lookup as production
    cfg = ForgeRuntimeConfig.from_env()
    if not cfg.anthropic_api_key:
        print("ERROR: anthropic_api_key not set; ABORT.", file=sys.stderr)
        return 1

    # ─── Config A: cache marker ON ───
    print("─" * 80)
    print("Config A: cache marker ON  (anthropic_cross_turn_cache_enabled=True)")
    print("─" * 80)
    ma = run_one_conversation(
        args.model, cfg, prompts, use_cache_marker=True,
        config_label="A", pause_seconds=args.pause,
    )

    print()
    # ─── Config B: cache marker OFF ───
    print("─" * 80)
    print("Config B: cache marker OFF (anthropic_cross_turn_cache_enabled=False)")
    print("─" * 80)
    mb = run_one_conversation(
        args.model, cfg, prompts, use_cache_marker=False,
        config_label="B", pause_seconds=args.pause,
    )

    print()
    summary = render_summary(ma, mb, args.model)
    print(summary)

    # Persist artifacts
    (args.output / "per_turn_a.jsonl").write_text(
        "\n".join(json.dumps(m.__dict__, ensure_ascii=False) for m in ma)
    )
    (args.output / "per_turn_b.jsonl").write_text(
        "\n".join(json.dumps(m.__dict__, ensure_ascii=False) for m in mb)
    )
    (args.output / "summary.txt").write_text(summary)
    print(f"wrote: {args.output / 'per_turn_a.jsonl'}")
    print(f"wrote: {args.output / 'per_turn_b.jsonl'}")
    print(f"wrote: {args.output / 'summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
