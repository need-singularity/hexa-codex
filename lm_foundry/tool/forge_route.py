#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge_route.py — decision-trace CLI for the v0.6.x runtime (r70).

Given a prompt, walks the classify → tier-select → vendor → cost-
estimate pipeline OFFLINE (no real API call). Useful for:

- "What would the runtime do with THIS prompt?" — operator debugging
- Pre-deploy prompt review (will it route hexa / ood / refuse?)
- Cost projection for known prompt templates
- Classifier signal exploration

USAGE
    # Single prompt via argv
    python3 tool/forge_route.py "Write a Rust async server"

    # Via stdin (handles multi-line, hides secrets)
    echo "Walk through the proof of Euclid's lemma" | python3 tool/forge_route.py

    # JSON output (machine-readable; pipes well to jq)
    python3 tool/forge_route.py --output json "What's RoPE?"

    # CSV row-per-prompt (batch mode; reads JSONL of {prompt: "..."} from stdin)
    cat prompts.jsonl | python3 tool/forge_route.py --batch --output csv

    # --estimate-tokens: rough heuristic char_count / 4 ≈ tokens, multiplied
    # by tier pricing table for $/turn projection. Heuristic, NOT exact.
    python3 tool/forge_route.py --estimate-tokens \\
        --expected-output-tokens 500 "Derive complexity of binary search"

OUTPUT (default text mode)
    Classifier label · matched signals · confidence
    Tier selection (if ood): tool / model / max_tokens / reason
    Cost estimate (if --estimate-tokens): est in / out tokens × tier price
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

sys.path.insert(0, str(_THIS_DIR))

from classify_prompt import classify_prompt  # type: ignore  # noqa: E402
sys.path.insert(0, str(_THIS_DIR))
from select_vendor_tier import select_vendor_tier  # type: ignore  # noqa: E402


# Cheap token-count heuristic (NOT exact; for projection only).
# Anthropic + OpenAI tokenizers average ~4 chars/token on English code/text.
# This is good to ±25% for cost projections; precision tokenization would
# require shipping the actual tokenizer (tiktoken / anthropic SDK is overkill
# for this purpose).
_CHARS_PER_TOKEN = 4.0


# Tier pricing table (USD per 1M tokens; mirrors forge_runtime.py).
# (input, cache_create, cache_read, output)
_PRICING_USD_PER_MTOK = {
    # claude
    "claude-opus-4-7":            (15.00, 18.75,  1.50,  75.00),
    "claude-sonnet-4-6":          ( 3.00,  3.75,  0.30,  15.00),
    "claude-haiku-4-5-20251001":  ( 0.80,  1.00,  0.08,   4.00),
    # openai
    "gpt-5":                       ( 5.00,  6.25,  0.50,  20.00),
    "gpt-5-mini":                  ( 0.25,  0.31,  0.025,  1.00),
    "gpt-5-nano":                  ( 0.05,  0.06,  0.005,  0.40),
    "o4-mini":                     ( 1.20,  1.50,  0.12,   4.80),
    "gpt-4o-mini":                 ( 0.15,  0.19,  0.015,  0.60),
    # gemini
    "gemini-2.5-pro":              ( 1.25,  1.56,  0.31,  10.00),
    "gemini-2.5-flash":            ( 0.30,  0.38,  0.075,  2.50),
    "gemini-2.5-flash-lite":       ( 0.10,  0.13,  0.025,  0.40),
}


def estimate_cost(model: str, in_chars: int, out_tokens_expected: int
                   ) -> tuple[int, float] | None:
    """Heuristic cost projection. Returns (est_in_tokens, est_cost_usd) or None
    if model unknown."""
    prc = _PRICING_USD_PER_MTOK.get(model)
    if prc is None:
        return None
    in_tok = max(1, int(in_chars / _CHARS_PER_TOKEN))
    cost = (in_tok * prc[0] + out_tokens_expected * prc[3]) / 1_000_000.0
    return in_tok, cost


def trace_one(prompt: str, estimate_tokens: bool,
               expected_output_tokens: int) -> dict:
    """Run the prompt through the pipeline, return a structured trace."""
    d = classify_prompt(prompt)
    trace = {
        "prompt_preview": prompt[:120] + ("…" if len(prompt) > 120 else ""),
        "prompt_chars": len(prompt),
        "classifier": {
            "label": d.label,
            "confidence": d.confidence,
            "reason": d.reason,
            "matched_signals": list(d.matched_signals),
        },
        "tier_selection": None,
        "cost_estimate": None,
    }
    if d.label != "ood":
        # hexa goes to 7B local; refuse short-circuits — no tier selection
        return trace

    tool, model, max_tokens, sel_reason = select_vendor_tier(d, prompt)
    trace["tier_selection"] = {
        "tool": tool,
        "model": model,
        "max_tokens": max_tokens,
        "reason": sel_reason,
    }
    if estimate_tokens:
        est = estimate_cost(model, len(prompt), expected_output_tokens)
        if est:
            in_tok, cost = est
            trace["cost_estimate"] = {
                "est_input_tokens":  in_tok,
                "expected_output_tokens": expected_output_tokens,
                "model":             model,
                "est_cost_usd":      round(cost, 6),
                "heuristic":         "chars / 4 → tokens; cost = in × input_rate + out × output_rate (vendor cache discount NOT applied; treat as upper bound)",
            }
    return trace


def render_text(trace: dict) -> str:
    """Pretty-print the trace for human reading."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("forge_route — decision trace (offline; no API call)")
    lines.append("=" * 78)
    lines.append(f"prompt:           {trace['prompt_preview']}")
    lines.append(f"prompt_chars:     {trace['prompt_chars']}")
    lines.append("")
    c = trace["classifier"]
    lines.append(f"CLASSIFIER")
    lines.append(f"  label:          {c['label']}")
    lines.append(f"  confidence:     {c['confidence']:.3f}")
    lines.append(f"  reason:         {c['reason']}")
    lines.append(f"  matched signals: {c['matched_signals']}")
    if c["label"] == "hexa":
        lines.append("")
        lines.append("DISPATCH:        hexa-canon → local 7B (no external delegation)")
    elif c["label"] == "refuse":
        lines.append("")
        lines.append("DISPATCH:        refuse → canonical refusal text (no 7B, no vendor)")
    else:
        ts = trace.get("tier_selection")
        if ts:
            lines.append("")
            lines.append("TIER SELECTION")
            lines.append(f"  tool:           {ts['tool']}")
            lines.append(f"  model:          {ts['model']}")
            lines.append(f"  max_tokens:     {ts['max_tokens']}")
            lines.append(f"  reason:         {ts['reason']}")
        ce = trace.get("cost_estimate")
        if ce:
            lines.append("")
            lines.append("COST ESTIMATE (heuristic)")
            lines.append(f"  est input:      {ce['est_input_tokens']} tokens (~chars/4)")
            lines.append(f"  expected output:{ce['expected_output_tokens']} tokens")
            lines.append(f"  est cost:       ${ce['est_cost_usd']:.6f} USD")
            lines.append(f"  (cache discount NOT applied; upper bound)")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_csv_header() -> str:
    return ("prompt_preview,prompt_chars,label,confidence,reason,"
            "matched_signals,tool,model,max_tokens,tier_reason,"
            "est_input_tokens,expected_output_tokens,est_cost_usd\n")


def render_csv_row(trace: dict) -> str:
    c = trace["classifier"]
    ts = trace.get("tier_selection") or {}
    ce = trace.get("cost_estimate") or {}
    def _esc(s: str) -> str:
        s = str(s).replace('"', '""')
        if "," in s or "\n" in s or '"' in s:
            return f'"{s}"'
        return s
    fields = [
        _esc(trace["prompt_preview"]),
        str(trace["prompt_chars"]),
        c["label"],
        f"{c['confidence']:.3f}",
        _esc(c["reason"]),
        _esc("|".join(c["matched_signals"])),
        ts.get("tool", ""),
        ts.get("model", ""),
        str(ts.get("max_tokens", "")),
        _esc(ts.get("reason", "")),
        str(ce.get("est_input_tokens", "")),
        str(ce.get("expected_output_tokens", "")),
        str(ce.get("est_cost_usd", "")),
    ]
    return ",".join(fields) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", default=None,
                    help="Prompt to trace (or read from stdin if omitted)")
    ap.add_argument("--batch", action="store_true",
                    help="Batch mode: read JSONL of {prompt: '...'} from stdin, "
                         "one row per line; output one trace per row")
    ap.add_argument("--output", choices=["text", "json", "csv"], default="text")
    ap.add_argument("--estimate-tokens", action="store_true",
                    help="Estimate input tokens (heuristic chars/4) + cost projection")
    ap.add_argument("--expected-output-tokens", type=int, default=500,
                    help="Expected output tokens for cost estimate (default 500)")
    args = ap.parse_args()

    # Resolve prompt source
    prompts: list[str] = []
    if args.batch:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                prompts.append(rec.get("prompt", ""))
            except json.JSONDecodeError:
                # Plain-text line is also acceptable
                prompts.append(line)
    elif args.prompt is not None:
        prompts.append(args.prompt)
    else:
        # stdin (single prompt, possibly multi-line)
        content = sys.stdin.read().strip()
        if not content:
            print("ERROR: no prompt provided (argv, stdin, or --batch JSONL)",
                  file=sys.stderr)
            return 1
        prompts.append(content)

    if not prompts:
        return 1

    if args.output == "csv":
        sys.stdout.write(render_csv_header())

    for prompt in prompts:
        trace = trace_one(
            prompt,
            estimate_tokens=args.estimate_tokens,
            expected_output_tokens=args.expected_output_tokens,
        )
        if args.output == "json":
            print(json.dumps(trace, ensure_ascii=False))
        elif args.output == "csv":
            sys.stdout.write(render_csv_row(trace))
        else:
            sys.stdout.write(render_text(trace))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
