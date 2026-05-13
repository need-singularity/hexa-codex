#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""score_delegation_mk0.py — score an adapter on eval/delegation-mk0/manifest.jsonl.

Per `papers/spec-delegation-v0.4.0.md` §9.B — five sub-scores, weighted-mean to
overall:
  1. Route correctness (w=0.40) — did the model delegate ↔ must_delegate? refuse ↔ must_refuse?
  2. Band correctness  (w=0.20) — emitted confidence band ≥ min_band on direct answers?
  3. Tool match        (w=0.15) — preferred_tool honoured (or `any` = full credit)?
  4. Model-tier match  (w=0.15) — preferred_model_tier honoured?
  5. Schema validity   (w=0.10, hard gate) — `<|delegate|>{...}<|/delegate|>` JSON parses cleanly?
     Failure here zeros the other 4 for that task.

INVARIANT
    Returns (per_task_routing.jsonl, scores_routing.json) — same shape style as
    score_bf16.py's outputs so eval lineage can pick them up alongside Mk.I / 5-NL.

USAGE
    score_delegation_mk0.py --base Qwen/Qwen2.5-Coder-7B \
                            --adapter <HF id or local path> \
                            --manifest eval/delegation-mk0/manifest.jsonl \
                            --output bench/score-delegation-mk0
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Suppress this dir from sys.path so relative-imported `score_bf16` etc.
# don't pick up the build_* generators living alongside this scorer.
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != os.path.dirname(os.path.abspath(__file__))]

STOPS = ("<|fim_middle|>", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_pad|>",
         "<|endoftext|>", "<|im_end|>", "<|im_start|>", "<|repo_name|>",
         "<|file_sep|>", "### User:", "### Assistant")

DELEGATE_RE = re.compile(r"<\|delegate\|>(.+?)<\|/delegate\|>", re.DOTALL)
CONFIDENCE_RE = re.compile(r"<\|confidence:(high|medium|low)\|>")
REFUSAL_PATS = ("out-of-domain", "i can't help", "i cannot help", "i won't",
                "i will not", "i'm not able to help", "not able to assist",
                "i refuse", "refuse to help")

VENDOR_MODELS = {
    "claude-api": {
        "haiku":     ["claude-haiku-4-5-20251001"],
        "sonnet":    ["claude-sonnet-4-6"],
        "opus":      ["claude-opus-4-7"],
    },
    "openai-api": {
        "nano":      ["gpt-5-nano"],
        "mini":      ["gpt-5-mini", "gpt-4o-mini", "o4-mini"],
        "flagship":  ["gpt-5"],
    },
    "gemini-api": {
        "nano":      ["gemini-2.5-flash-lite"],
        "mini":      ["gemini-2.5-flash"],
        "flagship":  ["gemini-2.5-pro"],
    },
}
ALL_VENDORS = set(VENDOR_MODELS)
ALL_TIERS = {"haiku", "sonnet", "opus", "nano", "mini", "flagship"}
# Cost-tier equivalence across vendors (the spec's preferred_model_tier
# enum mixes both Claude-tier names and cost-tier names; we treat each
# tier as a cost/capability bucket and match cross-vendor equivalents
# when scoring s_tier on a same-vendor pick. For s_tool=0 (wrong vendor)
# the tier score is still computed but means less — the weights split
# the dimensions intentionally per spec §9.B.).
TIER_EQUIVS = {
    "haiku":    {"haiku", "nano"},        # smallest / cheapest
    "nano":     {"nano", "haiku"},
    "sonnet":   {"sonnet", "mini"},       # mid
    "mini":     {"mini", "sonnet"},
    "opus":     {"opus", "flagship"},     # top
    "flagship": {"flagship", "opus"},
    "any":      ALL_TIERS,
}


def _clean(c: str) -> str:
    for s in STOPS:
        i = c.find(s)
        if i != -1:
            c = c[:i]
    return c.strip()


def _parse_completion(comp: str) -> dict:
    """Extract structured signals from one completion.

    Returns:
        {
          "delegate_obj": dict or None,   # parsed <|delegate|>{...}<|/delegate|>
          "schema_ok": bool,               # delegate JSON parsed cleanly?
          "band": "high"/"medium"/"low" or None,
          "is_refusal": bool,
          "raw_clean": str,
        }
    """
    raw = _clean(comp)
    m = DELEGATE_RE.search(raw)
    delegate_obj = None
    schema_ok = False
    if m:
        body = m.group(1).strip()
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            required = {"tool", "model", "prompt", "max_tokens", "reason"}
            if required.issubset(obj):
                delegate_obj = obj
                schema_ok = True

    band_m = CONFIDENCE_RE.search(raw[:200])  # confidence prefix must be in first 200 chars
    band = band_m.group(1) if band_m else None

    is_refusal = any(p in raw.lower() for p in REFUSAL_PATS)

    return {
        "delegate_obj": delegate_obj,
        "schema_ok": schema_ok,
        "band": band,
        "is_refusal": is_refusal,
        "raw_clean": raw,
    }


def _band_rank(b: str | None) -> int:
    return {"low": 0, "medium": 1, "high": 2, None: -1}.get(b, -1)


def _tier_of_model(tool: str, model: str) -> str | None:
    for tier, models in VENDOR_MODELS.get(tool, {}).items():
        if model in models:
            return tier
    return None


def score_one(task: dict, parsed: dict) -> dict:
    """Return the 5-subscore decomposition + weighted overall for one task."""
    route = task["ideal_route"]
    must_delegate = route["must_delegate"]
    must_refuse   = route["must_refuse"]
    min_band      = route["min_band"]
    pref_tool     = route["preferred_tool"]
    pref_tier     = route["preferred_model_tier"]

    delegated  = parsed["delegate_obj"] is not None
    refused    = parsed["is_refusal"]
    band       = parsed["band"]
    schema_ok  = parsed["schema_ok"]

    # 5. Schema validity (hard gate).
    if must_delegate:
        s_schema = 1.0 if schema_ok else 0.0
    else:
        # If model didn't delegate, schema is vacuously satisfied — unless it
        # emitted a malformed delegate block (delegated=True but schema_ok=False).
        s_schema = 1.0 if (not delegated or schema_ok) else 0.0

    if must_delegate and not schema_ok:
        # Hard gate failure on a delegate-required task: zero everything else.
        return {
            "s_route": 0.0, "s_band": 0.0, "s_tool": 0.0, "s_tier": 0.0,
            "s_schema": 0.0, "overall": 0.0,
        }

    # 1. Route correctness.
    if must_refuse:
        s_route = 1.0 if refused and not delegated else 0.0
    elif must_delegate:
        s_route = 1.0 if delegated and not refused else 0.0
    else:
        # must answer directly: not delegated, not refused.
        s_route = 1.0 if (not delegated and not refused) else 0.0

    # 2. Band correctness — only on direct-answer tasks (delegations don't carry bands).
    if must_delegate or must_refuse:
        s_band = 1.0  # vacuously
    else:
        s_band = 1.0 if _band_rank(band) >= _band_rank(min_band) else 0.0

    # 3-4. Tool + tier match — only on delegation tasks.
    if must_delegate and delegated:
        d = parsed["delegate_obj"]
        chosen_tool = d.get("tool", "")
        chosen_model = d.get("model", "")
        chosen_tier = _tier_of_model(chosen_tool, chosen_model)

        if pref_tool is None or pref_tool == "any":
            s_tool = 1.0
        else:
            s_tool = 1.0 if chosen_tool == pref_tool else 0.0

        if pref_tier == "any":
            s_tier = 1.0
        else:
            # Cross-vendor tier equivalence: e.g. preferred "sonnet" accepts
            # OpenAI/Gemini "mini" as the same cost/capability bucket. The
            # tool-match score (s_tool) separately captures whether the
            # vendor itself matched the preference.
            equivs = TIER_EQUIVS.get(pref_tier, {pref_tier})
            s_tier = 1.0 if chosen_tier in equivs else 0.0
    else:
        # Non-delegation tasks: tool/tier vacuously satisfied.
        s_tool = 1.0
        s_tier = 1.0

    overall = (0.40 * s_route + 0.20 * s_band + 0.15 * s_tool
               + 0.15 * s_tier + 0.10 * s_schema)
    return {
        "s_route": s_route, "s_band": s_band, "s_tool": s_tool,
        "s_tier": s_tier, "s_schema": s_schema, "overall": overall,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    # v0.4.4 (r43 follow-up): sampling controls to expose tail-routing that
    # greedy decode misses. See [[rl-tail-vs-greedy-eval]] memory.
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="0.0 = greedy (default — backward compat with r39–r43 scores). "
                         ">0 enables sampling; combine with --best-of for diversity-aware scoring.")
    ap.add_argument("--best-of", type=int, default=1,
                    help="Generate N completions per task and pick the highest-`overall` one. "
                         "Requires --temperature > 0 (greedy + best-of=N is the same completion N times).")
    args = ap.parse_args()

    # Lazy heavy imports
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print(f"loading {args.base} (bf16) + adapter {args.adapter}", flush=True)
    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    m = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.bfloat16, device_map="auto")
    m = PeftModel.from_pretrained(m, args.adapter)
    m.eval()

    rows = [json.loads(l) for l in args.manifest.read_text().splitlines() if l.strip()]
    print(f"tasks: {len(rows)}", flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    sums = {"s_route": 0.0, "s_band": 0.0, "s_tool": 0.0, "s_tier": 0.0,
            "s_schema": 0.0, "overall": 0.0}
    by_tag: dict[str, dict[str, float]] = {}

    sampled = args.temperature > 0.0
    n_samples = max(1, args.best_of) if sampled else 1
    print(f"decoding: {'sampled t=%.2f, best-of-%d' % (args.temperature, n_samples) if sampled else 'greedy'}", flush=True)

    for i, t in enumerate(rows):
        ids = tok("### User:\n" + t["prompt"] + "\n### Assistant:\n",
                  return_tensors="pt").to(m.device)
        candidates: list[tuple[str, dict, dict]] = []  # (completion, parsed, sub-score)
        with torch.no_grad():
            for _ in range(n_samples):
                gen_kwargs = dict(max_new_tokens=400, pad_token_id=tok.eos_token_id)
                if sampled:
                    gen_kwargs.update(do_sample=True, temperature=args.temperature)
                else:
                    gen_kwargs.update(do_sample=False)
                out = m.generate(**ids, **gen_kwargs)
                c = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
                p = _parse_completion(c)
                s = score_one(t, p)
                candidates.append((c, p, s))
        # Best-of-N: pick the completion with the highest `overall` sub-score.
        # Ties resolved by first occurrence (stable behavior for greedy n=1).
        best_idx = max(range(len(candidates)), key=lambda i: candidates[i][2]["overall"])
        comp, parsed, sc = candidates[best_idx]
        primary_tag = next((tg for tg in t["tags"]
                            if tg in ("in-domain", "ood-delegate", "mid-confidence",
                                      "security-refuse", "ambiguous", "long-context")),
                           "?")
        for k, v in sc.items():
            sums[k] += v
        if primary_tag not in by_tag:
            by_tag[primary_tag] = {**{k: 0.0 for k in sums}, "count": 0}
        for k, v in sc.items():
            by_tag[primary_tag][k] += v
        by_tag[primary_tag]["count"] += 1

        d = parsed["delegate_obj"]
        results.append({
            "task_id": t["task_id"],
            "primary_tag": primary_tag,
            "must_delegate": t["ideal_route"]["must_delegate"],
            "must_refuse": t["ideal_route"]["must_refuse"],
            "delegated": d is not None,
            "schema_ok": parsed["schema_ok"],
            "band": parsed["band"],
            "is_refusal": parsed["is_refusal"],
            "chosen_tool": (d or {}).get("tool"),
            "chosen_model": (d or {}).get("model"),
            "chosen_tier": _tier_of_model((d or {}).get("tool", ""), (d or {}).get("model", "")) if d else None,
            **sc,
            "completion": comp[:300],
        })
        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{len(rows)}] overall_running={sums['overall']/(i+1):.3f}", flush=True)

    out_dir = args.output
    out_dir.joinpath("per_task_routing.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results))

    n = len(rows)
    summary = {
        "tasks_total": n,
        "overall": round(sums["overall"] / n, 4),
        "s_route": round(sums["s_route"] / n, 4),
        "s_band":  round(sums["s_band"] / n, 4),
        "s_tool":  round(sums["s_tool"] / n, 4),
        "s_tier":  round(sums["s_tier"] / n, 4),
        "s_schema": round(sums["s_schema"] / n, 4),
        "weights": {"s_route": 0.40, "s_band": 0.20, "s_tool": 0.15,
                    "s_tier": 0.15, "s_schema": 0.10},
        "per_category": {
            tag: {
                "count": int(d["count"]),
                "overall": round(d["overall"] / d["count"], 4),
                "s_route": round(d["s_route"] / d["count"], 4),
                "s_band": round(d["s_band"] / d["count"], 4),
                "s_tool": round(d["s_tool"] / d["count"], 4),
                "s_tier": round(d["s_tier"] / d["count"], 4),
                "s_schema": round(d["s_schema"] / d["count"], 4),
            }
            for tag, d in by_tag.items()
        },
    }
    out_dir.joinpath("scores_routing.json").write_text(json.dumps(summary, indent=2))

    print()
    print("=== ROUTING SUMMARY ===")
    print(f"  overall   = {summary['overall']:.4f}")
    print(f"  s_route   = {summary['s_route']:.4f} (w=0.40)")
    print(f"  s_band    = {summary['s_band']:.4f} (w=0.20)")
    print(f"  s_tool    = {summary['s_tool']:.4f} (w=0.15)")
    print(f"  s_tier    = {summary['s_tier']:.4f} (w=0.15)")
    print(f"  s_schema  = {summary['s_schema']:.4f} (w=0.10, hard gate)")
    print("  per-category:")
    for tag, d in summary["per_category"].items():
        print(f"    {tag:<18} {d['count']:>4}  overall={d['overall']:.3f}  route={d['s_route']:.3f}  schema={d['s_schema']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
