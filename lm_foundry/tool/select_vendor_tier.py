#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""select_vendor_tier.py — per-prompt vendor + model selection for v0.5.2.

When `classify_prompt()` returns label="ood", we still have to pick WHICH
vendor + WHICH tier. Different out-of-domain prompts have different right
answers per `papers/spec-delegation-v0.4.0.md` §13.D heuristics:

  * long-context (>200K tokens) → gemini-2.5-pro (2M context window)
  * hard math / proof / reasoning → claude-opus-4-7 OR openai o4-mini
  * structured-output (JSON extraction / schema validation) → openai gpt-5-mini
                                                              (Structured Outputs)
  * general OOD code (Rust, Python, Go, frameworks) → claude-sonnet-4-6 (default)
  * ambiguous → claude-sonnet-4-6 (good at clarification)

The selector reads `ClassifierDecision.matched_signals` + raw prompt features
(length, explicit token-count mentions) and returns the route. Pure function —
no side effects, no API calls. Selection rules are deterministic for
reproducibility + telemetry.

USAGE
    from select_vendor_tier import select_vendor_tier
    decision = classify_prompt(prompt)
    if decision.label == "ood":
        tool, model, max_tokens, reason = select_vendor_tier(decision, prompt)
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

from typing import Iterable


# Signal → (tier-class, vendor-preference) routing table.
# Tier classes (per spec-delegation §13.D):
#   "longctx"  — long-context document analysis (>200K tokens)
#   "reason"   — math / proof / hard-reasoning / ml-internals
#   "struct"   — structured-output / JSON extraction / classification
#   "general"  — everything else OOD (fallback to claude-sonnet)
_SIGNAL_TO_CLASS: dict[str, str] = {
    # Long-context
    "long-context":     "longctx",
    "long-prompt-chars": "longctx",
    # Math / hard reasoning
    "prove-derive":     "reason",
    "complexity-bigO":  "reason",
    "ml-internals":     "reason",
    "agda-coq-lean":    "reason",   # dependent types / proof assistants
    # Structured output / extraction
    "structured-json":  "struct",
    "json-schema":      "struct",
}


# Tier-class → (tool, model, max_tokens) route.
#   r49 split the legacy "reason" tier into two:
#     * "reason-deep"  — foundational proofs / theorem walkthroughs /
#                        deep ml-internals mechanism explanations (opus).
#     * "reason-algo"  — closed-form derivations / recurrence / Big-O
#                        analysis — textbook algorithmic math (o4-mini).
#   Legacy "reason" key kept as alias for "reason-deep" so older tests
#   that hand-pick `_CLASS_TO_ROUTE["reason"]` keep working.
_CLASS_TO_ROUTE: dict[str, tuple[str, str, int]] = {
    "longctx":     ("gemini-api", "gemini-2.5-pro",            8192),
    "reason-deep": ("claude-api", "claude-opus-4-7",           4096),
    "reason-algo": ("openai-api", "o4-mini",                   2048),
    "reason":      ("claude-api", "claude-opus-4-7",           4096),  # legacy alias
    "struct":      ("openai-api", "gpt-5-mini",                2048),
    "general":     ("claude-api", "claude-sonnet-4-6",         2048),
}


# Public — match `score_delegation_mk0.score_one()`'s ideal_route fields.
# preferred_model_tier strings used by DLG-mk0 manifest:
#   "haiku" | "sonnet" | "opus"  (Claude tier names)
#   "nano"  | "mini"   | "flagship" (OpenAI / Gemini cost-tier names)
#   "any"   (no preference)
_MODEL_TO_TIER_NAME: dict[str, str] = {
    "claude-haiku-4-5-20251001": "haiku",
    "claude-sonnet-4-6":         "sonnet",
    "claude-opus-4-7":           "opus",
    "gpt-5-nano":                "nano",
    "gpt-5-mini":                "mini",
    "gpt-4o-mini":               "mini",
    "o4-mini":                   "mini",
    "gpt-5":                     "flagship",
    "gemini-2.5-flash-lite":     "nano",
    "gemini-2.5-flash":          "mini",
    "gemini-2.5-pro":            "flagship",
}


def model_tier(model: str) -> str:
    """Return the tier-name string for a model id (per DLG-mk0 vocab)."""
    return _MODEL_TO_TIER_NAME.get(model, "any")


def select_vendor_tier(decision, prompt: str) -> tuple[str, str, int, str]:
    """Pick `(tool, model, max_tokens, reason)` for an OOD-routed prompt.

    Args:
        decision: a `ClassifierDecision` from `classify_prompt()`; must have
                   label=="ood" (caller's responsibility — we assert).
        prompt:   raw user prompt (used for length-based heuristics that
                   complement the classifier's signal list).

    Returns:
        (tool, model, max_tokens, reason_string).
        `reason_string` includes the tier-class for telemetry; it's used as
        the `reason` field in the `DelegationCall`.

    Selection priority (first match wins, r49 split):
        1. Long-context (≥12K chars OR long-context signal) → longctx (gemini-2.5-pro).
        2. ml-comparison + ml-internals (comparative-Q form) → general (sonnet).
           Demotion from naive ml-internals→opus path. Comparative
           trade-off questions are sonnet-tier work, not opus.
        3. derivation-algo AND NOT ml-internals → reason-algo (o4-mini).
           Textbook closed-form / recurrence / Big-O derivations are
           o4-mini's sweet spot. ML gradient derivations (which also
           fire derivation-algo) stay on opus via step 4 because
           ml-internals is also matched.
        4. Legacy reason set (prove-derive / complexity-bigO / ml-internals /
           agda-coq-lean) → reason-deep (opus). Foundational proofs +
           deep ml-internals mechanism explanations.
        5. struct-class signal → struct (gpt-5-mini).
        6. Fallback → general (claude-sonnet-4-6).
    """
    if getattr(decision, "label", None) != "ood":
        raise ValueError(f"select_vendor_tier requires label='ood', got {decision.label!r}")

    sigs: Iterable[str] = decision.matched_signals or ()
    sig_set = set(sigs)

    # 1. Long-context wins above all (gemini's 2M context is the value-add).
    if len(prompt) >= 12000 or "long-context" in sig_set or "long-prompt-chars" in sig_set:
        tool, model, max_tokens = _CLASS_TO_ROUTE["longctx"]
        return tool, model, max_tokens, f"longctx: {decision.reason}"

    # 2. ml-comparison demotion: ml-internals topic in comparative-Q form
    #    (difference between / give better / reduce X vs / when does Y help)
    #    is sonnet-tier (trade-off explanation), not opus.
    if "ml-comparison" in sig_set and "ml-internals" in sig_set:
        tool, model, max_tokens = _CLASS_TO_ROUTE["general"]
        return tool, model, max_tokens, f"general (ml-comparison): {decision.reason}"

    # 3. Algorithmic derivation: closed-form, recurrence, Big-O, formula
    #    derivation — textbook math, o4-mini is the right cost/quality tier.
    #    Excludes ML-gradient derivations (ml-internals fires → step 4 opus).
    if "derivation-algo" in sig_set and "ml-internals" not in sig_set:
        tool, model, max_tokens = _CLASS_TO_ROUTE["reason-algo"]
        return tool, model, max_tokens, f"reason-algo: {decision.reason}"

    # 4. Deep reasoning / math / proof / ml-internals mechanism.
    if sig_set & {"prove-derive", "complexity-bigO", "ml-internals", "agda-coq-lean"}:
        tool, model, max_tokens = _CLASS_TO_ROUTE["reason-deep"]
        return tool, model, max_tokens, f"reason-deep: {decision.reason}"

    # 5. Structured output / extraction / classification.
    if sig_set & {"structured-json", "json-schema"}:
        tool, model, max_tokens = _CLASS_TO_ROUTE["struct"]
        return tool, model, max_tokens, f"struct: {decision.reason}"

    # 6. Fallback: general OOD code / frameworks / language idioms.
    tool, model, max_tokens = _CLASS_TO_ROUTE["general"]
    return tool, model, max_tokens, f"general: {decision.reason}"


# ============================================================================
# Smoke test
# ============================================================================

def _smoke() -> int:
    """Run select_vendor_tier on a few representative prompts via classify_prompt."""
    _sys.path.insert(0, _THIS_DIR)
    from classify_prompt import classify_prompt  # type: ignore
    cases = [
        # (prompt, expected_tier_class)
        ("Write a Rust async server using tokio that listens on TCP port 8080.", "general"),
        ("Show a Python decorator that caches function results with a TTL.",     "general"),
        # r49 reason-deep: foundational proof / theorem walkthrough
        ("Prove that the sum of the first n odd integers equals n².",            "reason-deep"),
        ("Walk through the proof that there are infinitely many primes.",        "reason-deep"),
        ("Explain how multi-head attention's QKV projections work.",             "reason-deep"),  # deep ml-internals mechanism
        # r49 reason-algo: closed-form / recurrence / formula derivation
        ("Derive the closed-form of the recurrence T(n) = 2T(n/2) + n.",         "reason-algo"),
        ("Derive the formula for the variance of the sum of two RVs.",           "reason-algo"),
        # r49 ml-comparison: ml topic in comparative-Q form → sonnet
        ("What's the difference between LoRA and DoRA?",                         "general"),
        ("How does FlashAttention-2 reduce memory vs naive attention?",          "general"),
        ("Parse 'Alice, 32, alice@example.com' into JSON {name, age, email}.",  "struct"),
        ("Classify this support ticket as urgent|normal|low; return JSON.",       "struct"),
        ("Here is a 500K-token spec document. Summarise rate-limiting section.", "longctx"),
        ("Across this 1M-token transcript, find all speaker contradictions.",    "longctx"),
        ("Help me debug this.",                                                   "general"),  # ambiguous → general
    ]
    pass_n = 0
    for prompt, expected_class in cases:
        d = classify_prompt(prompt)
        if d.label != "ood":
            print(f"  SKIP (label={d.label!r}): {prompt[:60]!r}")
            continue
        tool, model, max_tokens, reason = select_vendor_tier(d, prompt)
        # Reverse-map tool+model → tier-class for verification.
        tc = next((k for k, (t, m, _mt) in _CLASS_TO_ROUTE.items()
                    if t == tool and m == model), "?")
        ok = tc == expected_class
        flag = "✓" if ok else "✗"
        if ok:
            pass_n += 1
        print(f"  {flag} {expected_class:<8} → tc={tc:<8} ({tool}/{model:<25}) {prompt[:70]!r}")
    print(f"\n=== {pass_n}/{len(cases)} smoke cases pass ({pass_n/len(cases)*100:.0f}%) ===")
    return 0 if pass_n == len(cases) else 1


if __name__ == "__main__":
    _sys.exit(_smoke())
