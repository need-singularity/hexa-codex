#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge_runtime.py — runtime side of the §12 self-aware delegation protocol.

Reference implementation of the 11-step contract from
`papers/spec-delegation-v0.4.0.md` §3. The runtime owns the safety boundary —
**the model never sees vendor API keys, budget state, network state, or
conversation-level rate limits**. The model emits `<|delegate|>{...}<|/delegate|>`
tokens; this module detects them, parses + validates the JSON, redacts secrets,
authorises, budget-checks, calls the vendor, injects `<|delegate-result|>{...}`
back into the model's context, and logs telemetry.

v0.4.0 scope (per spec §1):
  - `tool` in {`claude-api`, `openai-api`, `gemini-api`} — vendor SDK calls
    are stubbed (TODO: wire up Anthropic/OpenAI/google-genai SDKs in the
    v0.4.0 implementation round).
  - `web-search`, `code-execution`, `wilson-rpc` are v0.5.0+.

USAGE
    from forge_runtime import ForgeRuntime, ForgeRuntimeConfig
    rt = ForgeRuntime(ForgeRuntimeConfig.from_env())
    result = rt.run_turn(user_prompt, gen_fn=my_7b_generate)
    # → result.user_facing_text, result.telemetry_rows
"""
from __future__ import annotations

import os as _os
import sys as _sys
# Strip this file's dir from sys.path so stdlib imports (e.g. `tokenize`) do
# not get shadowed by sibling tool/*.py modules of the same name.
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import hashlib
import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable
os = _os

# v0.5.0 orchestration: pre-7B classifier wired into run_turn(). Imported
# lazily so the runtime stays importable on hosts without the classifier
# (early-r45 transition only). After v0.5.1 settles, this becomes a hard import.
try:
    _sys.path.insert(0, _THIS_DIR)
    from classify_prompt import classify_prompt, ClassifierDecision  # type: ignore
    _HAS_CLASSIFIER = True
except ImportError:
    classify_prompt = None
    ClassifierDecision = None  # type: ignore
    _HAS_CLASSIFIER = False

# v0.5.2: per-vendor tier selector. Picks (tool, model, max_tokens) per
# classifier signals — long-context → gemini-pro, math/proof → claude-opus,
# structured-output → openai-mini, else claude-sonnet. Pure function; imported
# lazily for the same reason as classify_prompt.
# NOTE: classify_prompt.py (imported above) scrubs _THIS_DIR from sys.path at
# its own import time; re-insert here so the tier selector module is findable.
_sys.path.insert(0, _THIS_DIR)
try:
    from select_vendor_tier import select_vendor_tier  # type: ignore
    _HAS_TIER_SELECTOR = True
except ImportError:
    select_vendor_tier = None
    _HAS_TIER_SELECTOR = False

# ============================================================================
# Token grammar (spec §2)
# ============================================================================

_DELEGATE_RE        = re.compile(r"<\|delegate\|>(.+?)<\|/delegate\|>", re.DOTALL)
_DELEGATE_RESULT_RE = re.compile(r"<\|delegate-result\|>(.+?)<\|/delegate-result\|>", re.DOTALL)
_CONFIDENCE_RE      = re.compile(r"<\|confidence:(high|medium|low)\|>")

_REQUIRED_DELEGATE_FIELDS = {"tool", "model", "prompt", "max_tokens", "reason"}

_VENDOR_MODEL_ALLOWLIST = {
    "claude-api": {"claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"},
    "openai-api": {"gpt-5", "gpt-5-mini", "o4-mini", "gpt-4o-mini"},
    "gemini-api": {"gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"},
}

# ============================================================================
# Redaction (spec §6 — 8 classes; runtime-owned)
# ============================================================================

# (class, regex, action)  — action ∈ {"soft", "hard"}.
# Patterns are intentionally conservative to keep false-positives low; the
# v0.4.0 redactor is shallow by design (cf. spec §6 "Limitations").
_REDACTION_PATTERNS: list[tuple[str, re.Pattern[str], str, str]] = [
    ("api-key",      re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),                  "[REDACTED:api-key]", "hard"),
    ("api-key",      re.compile(r"\bhf_[A-Za-z0-9]{32,}\b"),                  "[REDACTED:api-key]", "hard"),
    ("api-key",      re.compile(r"\bxoxb-[A-Za-z0-9-]{20,}\b"),               "[REDACTED:api-key]", "hard"),
    ("jwt",          re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
                                                                              "[REDACTED:jwt]",      "hard"),
    ("private-key",  re.compile(r"-----BEGIN (OPENSSH|RSA|DSA|EC|PGP) PRIVATE KEY-----"),
                                                                              "[REDACTED:private-key]", "hard"),
    ("email",        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
                                                                              "[REDACTED:email]",    "soft"),
    ("ipv4",         re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),              "[REDACTED:ipv4]",     "soft"),
    ("local-path",   re.compile(r"/Users/[A-Za-z0-9_-]+/"),                   "/Users/<USER>/",      "soft"),
    ("local-path",   re.compile(r"/home/[A-Za-z0-9_-]+/"),                    "/home/<USER>/",       "soft"),
]


def redact(text: str) -> tuple[str, list[str], bool]:
    """Apply redaction patterns to `text`.

    Returns:
        (redacted_text, classes_hit, hard_block)
        - `classes_hit` is a deduped list of class labels for telemetry.
        - `hard_block=True` if any high-confidence-secret pattern matched →
          runtime aborts and returns `redaction_block` error per spec §5.
    """
    out = text
    hits: list[str] = []
    hard_block = False
    for cls, pat, repl, action in _REDACTION_PATTERNS:
        if pat.search(out):
            if cls not in hits:
                hits.append(cls)
            if action == "hard":
                hard_block = True
            out = pat.sub(repl, out)
    return out, hits, hard_block


# ============================================================================
# Configuration + telemetry
# ============================================================================

@dataclass
class ForgeRuntimeConfig:
    """All knobs the runtime needs. Keys come from `secret get`, never logged."""
    anthropic_api_key: str | None = None
    openai_api_key:    str | None = None
    gemini_api_key:    str | None = None

    # Budget caps (USD).
    per_conversation_usd: float = 0.50
    per_day_usd:          float = 20.00

    # Iteration cap (spec §3.10).
    max_delegations_per_turn: int = 3

    # Telemetry sink (gitignored). One JSONL row per delegation attempt.
    telemetry_path: Path = field(default_factory=lambda: Path("state/delegation_log.jsonl"))

    # Filler-token catalog (spec §7).
    filler_general: str   = "Looking up the larger model on this one — back in a moment…"
    filler_math:    str   = "Working through the math — give me a few seconds…"
    filler_longctx: str   = "Pulling in long-context analysis — this can take 5-10 s…"
    filler_reason:  str   = "Asking the reasoning model — this takes longer than chat…"

    # System prefix injected into every 7B turn (spec §3.1).
    system_prefix: str = (
        "You answer hexa-canon questions directly. For out-of-domain or "
        "hard-reasoning prompts, emit <|delegate|>{…}<|/delegate|>. For "
        "mid-confidence answers, prefix <|confidence:medium|>. NEVER emit "
        "<|confidence:low|> — delegate instead. NEVER delegate harmful / "
        "illegal / exfil prompts — refuse them directly."
    )

    # Where to look up secret-CLI for keys (lazy; called only when missing).
    secret_cli_path: str = os.path.expanduser("~/core/secret/bin/secret")

    # v0.5.0 orchestration mode. When True, run_turn() consults
    # `classify_prompt(user_prompt)` BEFORE generating with the 7B and uses
    # the classifier's label to route hexa → 7B, ood → vendor, refuse →
    # direct refusal. The 7B's own `<|delegate|>` token emissions are then
    # ignored (the classifier owns the routing decision). When False, the
    # v0.4.0 in-weight thesis is used (model emits <|delegate|>, runtime
    # dispatches) — kept for backward compatibility with old test harnesses
    # and the spec-delegation §3 flow. Default True since r44 disproved the
    # in-weight thesis across r40-r43.1.
    use_orchestration: bool = True

    # Default vendor for ood-routed prompts when orchestration is on.
    # The classifier's reason text + the prompt's character length informs
    # tier selection (e.g., long-context → gemini-pro), but v0.5.0 base
    # ships with a fixed default and defers per-vendor-tier routing to v0.5.1.
    default_ood_tool:  str = "claude-api"
    default_ood_model: str = "claude-sonnet-4-6"
    default_ood_max_tokens: int = 2048

    # v0.5.4: per-prompt vendor cache. Identical (tool, model, prompt) calls
    # within the TTL window return the cached response with cost=$0 and
    # `cache_hit=True` in telemetry. Default TTL 300s mirrors Anthropic's
    # prompt-cache TTL — within that window, the upstream vendor's own
    # prompt-cache would also be hot, so 300s is the natural pairing. Set
    # to 0 to disable caching entirely.
    vendor_cache_ttl_s:        int  = 300
    vendor_cache_max_entries:  int  = 1024   # hard cap to bound memory
    vendor_cache_enabled:      bool = True

    @classmethod
    def from_env(cls, **overrides) -> "ForgeRuntimeConfig":
        """Construct config; pull keys from secret-CLI lazily — see `_load_key`."""
        cfg = cls(**overrides)
        cfg.anthropic_api_key = cfg.anthropic_api_key or _load_key(cfg, "ANTHROPIC_API_KEY")
        cfg.openai_api_key    = cfg.openai_api_key    or _load_key(cfg, "OPENAI_API_KEY")
        cfg.gemini_api_key    = cfg.gemini_api_key    or _load_key(cfg, "GEMINI_API_KEY")
        cfg.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        return cfg


def _load_key(cfg: ForgeRuntimeConfig, name: str) -> str | None:
    """Load a secret via env var first, then fall back to the secret CLI.

    The secret CLI key convention is `<vendor>.api_key` (single underscore
    inside `api_key`, dot between vendor and the rest). Env-var convention
    is `<VENDOR>_API_KEY`. Map via the explicit table — naive replace("_",".")
    produced `anthropic.api.key` which the secret store doesn't have.
    """
    if (env := os.environ.get(name)):
        return env
    secret_key = {
        "ANTHROPIC_API_KEY": "anthropic.api_key",
        "OPENAI_API_KEY":    "openai.api_key",
        "GEMINI_API_KEY":    "gemini.api_key",
    }.get(name)
    if secret_key and os.path.exists(cfg.secret_cli_path):
        try:
            r = subprocess.run(
                [cfg.secret_cli_path, "get", secret_key],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            return None
    return None


# ============================================================================
# Result types
# ============================================================================

@dataclass
class DelegationCall:
    """One delegation event — parsed + acted on. Logged to telemetry."""
    conv_id: str
    turn_id: str
    iteration: int
    tool: str
    model: str
    prompt_chars: int
    prompt_redacted_classes: list[str]
    max_tokens: int
    reason: str
    ok: bool
    error: str | None = None
    text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    filler_emitted: bool = False
    # v0.5.4: True iff the response was served from the per-prompt vendor cache
    # (no upstream call made; cost_usd=0; latency_ms = local cache lookup time).
    cache_hit: bool = False
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class TurnResult:
    """The final outcome of a single user→model turn (possibly with delegations)."""
    conv_id: str
    turn_id: str
    user_facing_text: str
    confidence_band: str | None
    delegations: list[DelegationCall]
    final_error: str | None = None
    # v0.5.0 fields — populated when orchestration routing is on.
    classifier_label: str | None = None       # "hexa" | "ood" | "refuse" | None (legacy)
    classifier_reason: str | None = None      # one-line explanation for telemetry
    classifier_signals: list[str] = field(default_factory=list)


# ============================================================================
# Vendor dispatch (STUBS — wire up in v0.4.0 implementation round)
# ============================================================================

# Anthropic pricing per million tokens (claude-opus-4-7 / -sonnet-4-6 / -haiku-4-5-…).
# Used for cost telemetry; not authoritative — Anthropic publishes the canonical table.
# Cached input tokens cost ~10% of normal (5-min TTL); cache creation 1.25× normal.
_ANTHROPIC_PRICING_USD_PER_MTOK = {
    # model_id                       : (input_per_M, cache_create_per_M, cache_read_per_M, output_per_M)
    "claude-opus-4-7":                 (15.0, 18.75, 1.50, 75.0),
    "claude-sonnet-4-6":               ( 3.0,  3.75, 0.30, 15.0),
    "claude-haiku-4-5-20251001":       ( 0.80, 1.00, 0.08, 4.00),
}


def _anthropic_call(model: str, prompt: str, max_tokens: int,
                    cfg: ForgeRuntimeConfig) -> tuple[bool, str, dict, str | None]:
    """Real Anthropic API call via the `anthropic` SDK.

    System prefix is short and stable — marked with `cache_control` so
    repeated calls in the same 5-minute TTL window hit the cache. Returns
    (ok, text, usage_dict, error|None) per the _vendor_call contract.

    Refusal handling: a Claude refusal comes back as normal content (text
    starts with "I can't…" / "I won't…"). Per spec §5 we return `ok=True`
    with the refusal text; the 7B is SFT'd to echo it honestly.
    """
    try:
        import anthropic
    except ImportError:
        return False, "", {}, "auth_fail"  # SDK missing == effectively unauthed

    try:
        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key, timeout=30.0)
        system_prefix = (
            "You are answering a question for a small hexa-canon code-LLM that "
            "delegated this. Be concise; return code in hexa idiom if applicable."
        )
        resp = client.messages.create(
            model=model,
            max_tokens=int(max_tokens),
            system=[{"type": "text", "text": system_prefix,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        return False, "", {}, "auth_fail"
    except anthropic.APITimeoutError:
        return False, "", {}, "upstream_timeout"
    except anthropic.APIStatusError as e:
        sc = int(getattr(e, "status_code", 0) or 0)
        if sc == 429:
            return False, "", {}, "upstream_quota"
        if 500 <= sc < 600:
            return False, "", {}, "upstream_5xx"
        return False, "", {}, "upstream_5xx"  # treat other 4xx as upstream too
    except Exception:
        return False, "", {}, "upstream_5xx"

    # Concatenate text-content blocks (Anthropic returns a list; we ignore
    # tool_use / thinking blocks for v0.4.0).
    parts = []
    for blk in (resp.content or []):
        if getattr(blk, "type", None) == "text":
            parts.append(getattr(blk, "text", ""))
    text = "".join(parts)

    # Usage + cost. The Anthropic SDK surfaces `input_tokens`,
    # `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`.
    u = resp.usage
    in_tok      = int(getattr(u, "input_tokens", 0) or 0)
    out_tok     = int(getattr(u, "output_tokens", 0) or 0)
    cache_create = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
    cache_read   = int(getattr(u, "cache_read_input_tokens", 0) or 0)
    prc = _ANTHROPIC_PRICING_USD_PER_MTOK.get(model, (0, 0, 0, 0))
    cost_usd = (in_tok * prc[0] + cache_create * prc[1] + cache_read * prc[2]
                + out_tok * prc[3]) / 1_000_000.0
    usage = {
        "input_tokens":  in_tok + cache_create + cache_read,
        "output_tokens": out_tok,
        "cached_tokens": cache_read,
        "cost_usd":      round(cost_usd, 6),
    }
    return True, text, usage, None


# ============================================================================
# OpenAI pricing per million tokens (per LEARNING_PROGRAMMING.md §13.A).
# (input_per_M, cached_input_per_M, output_per_M). OpenAI's auto-cache discount
# is ~50% on the input side; we collapse it into cached_input_per_M.
# ============================================================================
_OPENAI_PRICING_USD_PER_MTOK = {
    "gpt-5":         (2.0, 1.0, 10.0),
    "gpt-5-mini":    (0.50, 0.25, 2.0),
    "gpt-5-nano":    (0.05, 0.025, 0.40),
    "o4-mini":       (3.0, 1.5, 12.0),
    "gpt-4o-mini":   (0.15, 0.075, 0.60),
}


def _openai_call(model: str, prompt: str, max_tokens: int,
                 cfg: ForgeRuntimeConfig) -> tuple[bool, str, dict, str | None]:
    """Real OpenAI API call via the `openai` SDK. Uses chat.completions for
    broad compatibility (Responses API is preferred for new builds but
    chat.completions is universally supported). Auto-cache fires when the
    prompt prefix is ≥ 1024 tokens — surfaces in `usage.prompt_tokens_details.cached_tokens`.

    Refusal handling: like Claude, OpenAI returns refusal text as normal
    `message.content`. Returns ok=True with refusal text; 7B echoes honestly.
    """
    try:
        import openai
    except ImportError:
        return False, "", {}, "auth_fail"  # SDK missing == effectively unauthed

    try:
        client = openai.OpenAI(api_key=cfg.openai_api_key, timeout=30.0)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=int(max_tokens),
            messages=[
                {"role": "system", "content": (
                    "You are answering a question for a small hexa-canon code-LLM "
                    "that delegated this. Be concise; return code in hexa idiom if applicable.")},
                {"role": "user", "content": prompt},
            ],
        )
    except openai.AuthenticationError:
        return False, "", {}, "auth_fail"
    except openai.APITimeoutError:
        return False, "", {}, "upstream_timeout"
    except openai.APIStatusError as e:
        sc = int(getattr(e, "status_code", 0) or 0)
        if sc == 429:
            return False, "", {}, "upstream_quota"
        return False, "", {}, "upstream_5xx"
    except Exception:
        return False, "", {}, "upstream_5xx"

    text = (resp.choices[0].message.content or "") if resp.choices else ""
    u = resp.usage
    in_tok  = int(getattr(u, "prompt_tokens", 0) or 0)
    out_tok = int(getattr(u, "completion_tokens", 0) or 0)
    # cached_tokens lives under prompt_tokens_details (newer SDK) or
    # cached_tokens (older) — try both.
    cached = 0
    details = getattr(u, "prompt_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    else:
        cached = int(getattr(u, "cached_tokens", 0) or 0)
    prc = _OPENAI_PRICING_USD_PER_MTOK.get(model, (0, 0, 0))
    fresh_in = max(0, in_tok - cached)
    cost_usd = (fresh_in * prc[0] + cached * prc[1] + out_tok * prc[2]) / 1_000_000.0
    usage = {
        "input_tokens":  in_tok,
        "output_tokens": out_tok,
        "cached_tokens": cached,
        "cost_usd":      round(cost_usd, 6),
    }
    return True, text, usage, None


# ============================================================================
# Gemini pricing per million tokens (LEARNING_PROGRAMMING.md §13.B).
# (input_per_M, cached_input_per_M, output_per_M). Gemini context caching is
# explicit (not auto); cached_input_per_M is the dominant savings tier.
# ============================================================================
_GEMINI_PRICING_USD_PER_MTOK = {
    "gemini-2.5-pro":         (1.25, 0.31, 10.0),
    "gemini-2.5-flash":       (0.30, 0.075, 2.5),
    "gemini-2.5-flash-lite":  (0.10, 0.025, 0.40),
}


def _gemini_call(model: str, prompt: str, max_tokens: int,
                 cfg: ForgeRuntimeConfig) -> tuple[bool, str, dict, str | None]:
    """Real Gemini API call via `google.genai`. Long-context (2M tokens on
    gemini-2.5-pro) is the value-add tier; the runtime sends the full prompt
    in a single request. v0.5.3 base ships without explicit context caching;
    v0.6+ can add `cached_content` for repeated long-doc prompts.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return False, "", {}, "auth_fail"  # SDK missing

    try:
        client = genai.Client(api_key=cfg.gemini_api_key)
        cfg_obj = genai_types.GenerateContentConfig(
            max_output_tokens=int(max_tokens),
            system_instruction=(
                "You are answering a question for a small hexa-canon code-LLM "
                "that delegated this. Be concise; return code in hexa idiom if applicable."),
        )
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg_obj,
        )
    except Exception as e:
        # google.genai errors are heterogeneous; coarse-classify by string.
        # ClientError(429) for quota-exceeded uses 'RESOURCE_EXHAUSTED' /
        # 'quota' phrasing — map to upstream_quota for finer-grained UX.
        msg = str(e).lower()
        if "authentication" in msg or "api key" in msg or "invalid api key" in msg or "permission" in msg:
            return False, "", {}, "auth_fail"
        if "timeout" in msg or "deadline" in msg:
            return False, "", {}, "upstream_timeout"
        if "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg or "429" in msg:
            return False, "", {}, "upstream_quota"
        return False, "", {}, "upstream_5xx"

    text = getattr(resp, "text", None) or ""
    u = getattr(resp, "usage_metadata", None)
    in_tok  = int(getattr(u, "prompt_token_count", 0) or 0) if u else 0
    out_tok = int(getattr(u, "candidates_token_count", 0) or 0) if u else 0
    cached  = int(getattr(u, "cached_content_token_count", 0) or 0) if u else 0
    prc = _GEMINI_PRICING_USD_PER_MTOK.get(model, (0, 0, 0))
    fresh_in = max(0, in_tok - cached)
    cost_usd = (fresh_in * prc[0] + cached * prc[1] + out_tok * prc[2]) / 1_000_000.0
    usage = {
        "input_tokens":  in_tok,
        "output_tokens": out_tok,
        "cached_tokens": cached,
        "cost_usd":      round(cost_usd, 6),
    }
    return True, text, usage, None


def _vendor_call(tool: str, model: str, prompt: str, max_tokens: int,
                 cfg: ForgeRuntimeConfig) -> tuple[bool, str, dict, str | None]:
    """Dispatch a vendor call. Returns (ok, text, usage_dict, error|None).

    v0.5.3 status (all three vendors REAL):
      - claude-api  → `anthropic` SDK with prompt-cache `cache_control`.
      - openai-api  → `openai` SDK (chat.completions; auto-cache ≥1024-tok prefix).
      - gemini-api  → `google.genai` SDK (`generate_content`).

    SDK presence is gated: if the package isn't installed OR no API key is
    configured, the call returns `auth_fail` cleanly. Stubs are removed —
    the runtime degrades to auth_fail instead of returning fake success.

    Failure modes per spec §5:
      - timeout / 5xx → "upstream_timeout" / "upstream_5xx"
      - auth fail (SDK missing OR 401 OR no key) → "auth_fail"
      - refusal       → (ok=True, text=<refusal>) — the 7B SFT echoes it.
    """
    key = {
        "claude-api": cfg.anthropic_api_key,
        "openai-api": cfg.openai_api_key,
        "gemini-api": cfg.gemini_api_key,
    }.get(tool)
    if not key:
        return False, "", {}, "auth_fail"

    if tool == "claude-api":
        return _anthropic_call(model, prompt, max_tokens, cfg)
    if tool == "openai-api":
        return _openai_call(model, prompt, max_tokens, cfg)
    if tool == "gemini-api":
        return _gemini_call(model, prompt, max_tokens, cfg)

    # Unknown tool (shouldn't happen — _validate_delegate_obj guards in legacy
    # path; tier selector only emits allowlisted tools in orchestration path).
    return False, "", {}, "auth_fail"


def _pick_filler(reason: str, cfg: ForgeRuntimeConfig) -> str:
    """Choose the pre-call filler from spec §7 by `reason` content."""
    r = reason.lower()
    if any(k in r for k in ("math", "deriv", "proof", "theorem")):
        return cfg.filler_math
    if any(k in r for k in ("long-context", "long context", "ctx", ">200", "500k", "1m token")):
        return cfg.filler_longctx
    if any(k in r for k in ("reason", "o3", "o4", "opus")):
        return cfg.filler_reason
    return cfg.filler_general


# ============================================================================
# Main runtime
# ============================================================================

class ForgeRuntime:
    """Owns the §3 11-step contract. One instance per process; thread-safe is
    not required for v0.4.0 (single-tenant inference)."""

    def __init__(self, cfg: ForgeRuntimeConfig):
        self.cfg = cfg
        # Per-conversation spent tracker (in-memory; v0.5.0 may persist).
        self._spent_per_conv: dict[str, float] = {}
        self._spent_today: float = 0.0
        self._today: str = time.strftime("%Y-%m-%d", time.gmtime())
        # v0.5.4 per-prompt vendor cache. Key: (tool, model, max_tokens,
        # sha256(prompt)) — max_tokens included so a high-cap re-ask doesn't
        # serve a truncated cached response. Value: (text, usage, expires_ts).
        # In-memory dict with hard cap + LRU eviction; cleared on process exit.
        self._vendor_cache: dict[tuple, tuple] = {}
        # Cache eviction order — simple FIFO insertion ordering; Python dict
        # preserves insertion order. On full, pop the oldest 25% to amortise
        # the cleanup cost.
        self._vendor_cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

    # ---- public entry point ----

    def run_turn(self, user_prompt: str, gen_fn: Callable[[str], str], *,
                 conv_id: str | None = None,
                 emit_filler_fn: Callable[[str], None] | None = None) -> TurnResult:
        """Execute one user→model turn, dispatching delegations as needed.

        Args:
            user_prompt: raw user input.
            gen_fn: a callable that takes a fully-formed model prompt (including
                the system prefix + any conversation context + any synthetic
                `<|delegate-result|>{...}` turn) and returns the model's
                generation text.
            conv_id: optional conversation id for per-conv budget tracking;
                a UUID is minted if not provided.
            emit_filler_fn: optional sink for streaming-UX fillers (spec §7).
                If None, fillers are dropped; the wrapping serving layer
                normally hooks the real user channel here.

        Returns:
            TurnResult.
        """
        conv_id = conv_id or str(uuid.uuid4())
        turn_id = str(uuid.uuid4())

        # v0.5.0 orchestration: classify BEFORE the 7B sees anything.
        if self.cfg.use_orchestration and _HAS_CLASSIFIER:
            return self._run_turn_orchestrated(user_prompt, gen_fn,
                                                 conv_id=conv_id, turn_id=turn_id,
                                                 emit_filler_fn=emit_filler_fn)

        # v0.4.0 legacy in-weight path — kept for backward compatibility.
        # Step 1: generate.
        full_prompt = f"### System:\n{self.cfg.system_prefix}\n### User:\n{user_prompt}\n### Assistant:\n"
        gen = gen_fn(full_prompt)
        delegations: list[DelegationCall] = []

        # Step 2-10: detect / parse / redact / authorize / budget / call /
        # inject; loop up to max_delegations_per_turn.
        for iteration in range(1, self.cfg.max_delegations_per_turn + 1):
            m = _DELEGATE_RE.search(gen)
            if not m:
                break  # no more delegate tokens → done

            # Parse + validate (steps 2-3).
            body = m.group(1).strip()
            try:
                obj = json.loads(body)
            except json.JSONDecodeError:
                # spec §5 schema_violation = never-event for the model; runtime
                # returns hard error to user (NOT injected back).
                return TurnResult(
                    conv_id, turn_id,
                    user_facing_text=(
                        "[runtime] model emitted malformed <|delegate|> JSON. "
                        "This is a model bug — please report. (No vendor call made.)"
                    ),
                    confidence_band=None, delegations=delegations,
                    final_error="schema_violation",
                )
            err = self._validate_delegate_obj(obj)
            if err:
                return TurnResult(
                    conv_id, turn_id,
                    user_facing_text=f"[runtime] delegation schema violation: {err}",
                    confidence_band=None, delegations=delegations,
                    final_error="schema_violation",
                )

            # Step 4: redact.
            redacted, hits, hard_block = redact(obj["prompt"])
            if hard_block:
                result_obj = {"ok": False, "error": "redaction_block",
                              "detail": "high-confidence secret detected; not forwarded"}
                gen = self._inject_result(gen, m, result_obj)
                delegations.append(DelegationCall(
                    conv_id=conv_id, turn_id=turn_id, iteration=iteration,
                    tool=obj["tool"], model=obj["model"],
                    prompt_chars=len(obj["prompt"]),
                    prompt_redacted_classes=hits, max_tokens=obj["max_tokens"],
                    reason=obj["reason"], ok=False, error="redaction_block",
                ))
                gen = gen_fn(self._resume_prompt(user_prompt, gen))
                continue
            obj_prompt = redacted

            # Step 5: authorize.
            if not self._has_key_for(obj["tool"]):
                result_obj = {"ok": False, "error": "auth_fail",
                              "detail": f"no API key configured for {obj['tool']}"}
                gen = self._inject_result(gen, m, result_obj)
                delegations.append(DelegationCall(
                    conv_id=conv_id, turn_id=turn_id, iteration=iteration,
                    tool=obj["tool"], model=obj["model"],
                    prompt_chars=len(obj["prompt"]),
                    prompt_redacted_classes=hits, max_tokens=obj["max_tokens"],
                    reason=obj["reason"], ok=False, error="auth_fail",
                ))
                gen = gen_fn(self._resume_prompt(user_prompt, gen))
                continue

            # Step 6: budget check.
            self._roll_day()
            spent_conv = self._spent_per_conv.get(conv_id, 0.0)
            if (spent_conv >= self.cfg.per_conversation_usd
                    or self._spent_today >= self.cfg.per_day_usd):
                result_obj = {"ok": False, "error": "budget_exhausted",
                              "detail": "per-conversation or per-day cap reached"}
                gen = self._inject_result(gen, m, result_obj)
                delegations.append(DelegationCall(
                    conv_id=conv_id, turn_id=turn_id, iteration=iteration,
                    tool=obj["tool"], model=obj["model"],
                    prompt_chars=len(obj["prompt"]),
                    prompt_redacted_classes=hits, max_tokens=obj["max_tokens"],
                    reason=obj["reason"], ok=False, error="budget_exhausted",
                ))
                gen = gen_fn(self._resume_prompt(user_prompt, gen))
                continue

            # Step 7-8: filler + vendor call.
            filler = _pick_filler(obj["reason"], self.cfg)
            if emit_filler_fn:
                emit_filler_fn(filler)
            t0 = time.monotonic()
            ok, text, usage, err = _vendor_call(
                obj["tool"], obj["model"], obj_prompt, obj["max_tokens"], self.cfg,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            # Budget accounting.
            cost = float(usage.get("cost_usd", 0.0))
            self._spent_per_conv[conv_id] = spent_conv + cost
            self._spent_today += cost

            call = DelegationCall(
                conv_id=conv_id, turn_id=turn_id, iteration=iteration,
                tool=obj["tool"], model=obj["model"],
                prompt_chars=len(obj["prompt"]),
                prompt_redacted_classes=hits, max_tokens=obj["max_tokens"],
                reason=obj["reason"], ok=ok, error=err, text=text[:2000],
                tokens_in=int(usage.get("input_tokens", 0)),
                tokens_out=int(usage.get("output_tokens", 0)),
                cached_tokens=int(usage.get("cached_tokens", 0)),
                cost_usd=cost, latency_ms=latency_ms,
                filler_emitted=emit_filler_fn is not None,
            )
            delegations.append(call)

            # Step 9: inject result + re-generate.
            if ok:
                result_obj = {"ok": True, "text": text, "usage": usage}
            else:
                result_obj = {"ok": False, "error": err or "upstream_5xx", "detail": ""}
            gen = self._inject_result(gen, m, result_obj)
            gen = gen_fn(self._resume_prompt(user_prompt, gen))
        else:
            # Step 10: max_delegations hit.
            # `for/else` runs when the loop did NOT break — i.e., we still have a
            # `<|delegate|>` lurking in `gen` after max iterations. Inject
            # `max_delegations` and have the model write a graceful close.
            m = _DELEGATE_RE.search(gen)
            if m:
                result_obj = {"ok": False, "error": "max_delegations",
                              "detail": f"hit {self.cfg.max_delegations_per_turn}-delegation cap"}
                gen = self._inject_result(gen, m, result_obj)
                gen = gen_fn(self._resume_prompt(user_prompt, gen))

        # Step 11: telemetry.
        for d in delegations:
            self._append_telemetry(d)

        # Strip the confidence band into a structured field; surface the
        # cleaned text to the user.
        band_m = _CONFIDENCE_RE.search(gen[:200])
        band = band_m.group(1) if band_m else None
        user_facing = _CONFIDENCE_RE.sub("", gen, count=1).lstrip()

        return TurnResult(conv_id, turn_id, user_facing, band, delegations)

    # ---- v0.5.0 orchestration path ----

    def _run_turn_orchestrated(self, user_prompt: str, gen_fn: Callable[[str], str], *,
                                 conv_id: str, turn_id: str,
                                 emit_filler_fn: Callable[[str], None] | None) -> TurnResult:
        """Pre-7B-classifier dispatch per spec-orchestration-v0.5.0.md §5.

        Decision flow:
          1. `classify_prompt(user_prompt)` → {hexa, ood, refuse}.
          2. label="refuse" → emit canonical refusal directly. No 7B, no vendor.
          3. label="hexa"   → call gen_fn(7B prompt). Strip any <|delegate|> /
                                <|delegate-result|> / <|confidence:*|> tokens
                                from the output (classifier owns routing, not
                                model). Surface the cleaned text + band.
          4. label="ood"    → bypass 7B entirely. Run the existing v0.4.0
                                redaction + budget + vendor-call pipeline using
                                the classifier's `reason` as the delegation
                                rationale. Emit filler before the vendor call.
        """
        d = classify_prompt(user_prompt)

        # --- refuse path ---
        if d.label == "refuse":
            text = (f"out-of-domain — this is a security-sensitive request "
                    f"({d.reason.split(':',1)[-1].strip() or 'classified by gate'}) "
                    "I won't help with.")
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=text, confidence_band="high",
                delegations=[], final_error=None,
                classifier_label="refuse", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

        # --- hexa path ---
        if d.label == "hexa":
            full_prompt = (f"### System:\n{self.cfg.system_prefix}\n"
                            f"### User:\n{user_prompt}\n### Assistant:\n")
            gen = gen_fn(full_prompt)
            # Strip delegation-protocol tokens — classifier owns routing.
            gen_clean = _DELEGATE_RE.sub("", gen)
            gen_clean = _DELEGATE_RESULT_RE.sub("", gen_clean)
            band_m = _CONFIDENCE_RE.search(gen_clean[:200])
            band = band_m.group(1) if band_m else None
            user_facing = _CONFIDENCE_RE.sub("", gen_clean, count=1).lstrip()
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=user_facing, confidence_band=band,
                delegations=[], final_error=None,
                classifier_label="hexa", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

        # --- ood path ---
        # v0.5.2: pick vendor + model + max_tokens by classifier signal class
        # (long-context → gemini-pro, math/proof → claude-opus, structured →
        # openai-mini, else claude-sonnet). Falls back to config defaults
        # when the selector isn't importable.
        if _HAS_TIER_SELECTOR:
            tool, model, max_tokens, reason = select_vendor_tier(d, user_prompt)
        else:
            tool = self.cfg.default_ood_tool
            model = self.cfg.default_ood_model
            max_tokens = self.cfg.default_ood_max_tokens
            reason = d.reason

        # Redaction (spec §6).
        redacted_prompt, redaction_hits, hard_block = redact(user_prompt)
        if hard_block:
            text = ("I detected what looks like a secret in this prompt and won't "
                    "forward it externally. If you intended to ask without the "
                    "secret, please rephrase.")
            call = DelegationCall(
                conv_id=conv_id, turn_id=turn_id, iteration=1,
                tool=tool, model=model,
                prompt_chars=len(user_prompt),
                prompt_redacted_classes=redaction_hits, max_tokens=max_tokens,
                reason=reason, ok=False, error="redaction_block",
            )
            self._append_telemetry(call)
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=text, confidence_band=None,
                delegations=[call], final_error="redaction_block",
                classifier_label="ood", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

        # Authorize.
        if not self._has_key_for(tool):
            text = f"Delegation auth is not configured for {tool}. (No vendor call made.)"
            call = DelegationCall(
                conv_id=conv_id, turn_id=turn_id, iteration=1,
                tool=tool, model=model,
                prompt_chars=len(user_prompt),
                prompt_redacted_classes=redaction_hits, max_tokens=max_tokens,
                reason=reason, ok=False, error="auth_fail",
            )
            self._append_telemetry(call)
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=text, confidence_band=None,
                delegations=[call], final_error="auth_fail",
                classifier_label="ood", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

        # Budget check.
        self._roll_day()
        spent_conv = self._spent_per_conv.get(conv_id, 0.0)
        if (spent_conv >= self.cfg.per_conversation_usd
                or self._spent_today >= self.cfg.per_day_usd):
            text = ("Delegation budget for this conversation is spent. Please "
                    "rephrase as a hexa-canon question or retry later.")
            call = DelegationCall(
                conv_id=conv_id, turn_id=turn_id, iteration=1,
                tool=tool, model=model,
                prompt_chars=len(user_prompt),
                prompt_redacted_classes=redaction_hits, max_tokens=max_tokens,
                reason=reason, ok=False, error="budget_exhausted",
            )
            self._append_telemetry(call)
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=text, confidence_band=None,
                delegations=[call], final_error="budget_exhausted",
                classifier_label="ood", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

        # v0.5.4: per-prompt vendor cache lookup. Identical (tool, model,
        # max_tokens, prompt) within TTL → return cached response, cost=$0.
        cache_key = self._vendor_cache_key(tool, model, max_tokens, redacted_prompt)
        cache_hit = False
        cached = self._vendor_cache_get(cache_key) if self.cfg.vendor_cache_enabled else None
        if cached is not None:
            text, usage, _expires = cached
            ok, err = True, None
            latency_ms = 0
            cache_hit = True
            self._vendor_cache_stats["hits"] += 1
        else:
            # Pre-call filler (spec §7) + real vendor call.
            if self.cfg.vendor_cache_enabled:
                self._vendor_cache_stats["misses"] += 1
            filler = _pick_filler(reason, self.cfg)
            if emit_filler_fn:
                emit_filler_fn(filler)
            t0 = time.monotonic()
            ok, text, usage, err = _vendor_call(tool, model, redacted_prompt,
                                                  max_tokens, self.cfg)
            latency_ms = int((time.monotonic() - t0) * 1000)
            # Cache successful responses only — failures should be retried.
            if ok and self.cfg.vendor_cache_enabled and self.cfg.vendor_cache_ttl_s > 0:
                self._vendor_cache_put(cache_key, text, usage)

        # Cost is zero on cache hit (no upstream tokens consumed).
        cost = 0.0 if cache_hit else float(usage.get("cost_usd", 0.0))
        self._spent_per_conv[conv_id] = spent_conv + cost
        self._spent_today += cost

        call = DelegationCall(
            conv_id=conv_id, turn_id=turn_id, iteration=1,
            tool=tool, model=model,
            prompt_chars=len(user_prompt),
            prompt_redacted_classes=redaction_hits, max_tokens=max_tokens,
            reason=reason, ok=ok, error=err, text=(text or "")[:2000],
            tokens_in=int(usage.get("input_tokens", 0)),
            tokens_out=int(usage.get("output_tokens", 0)),
            cached_tokens=int(usage.get("cached_tokens", 0)),
            cost_usd=cost, latency_ms=latency_ms,
            filler_emitted=(emit_filler_fn is not None) and not cache_hit,
            cache_hit=cache_hit,
        )
        self._append_telemetry(call)

        if ok:
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=text, confidence_band=None,
                delegations=[call], final_error=None,
                classifier_label="ood", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )
        else:
            # Graceful fallback message
            errmap = {
                "upstream_timeout": "The frontier model is unreachable right now. Please retry shortly.",
                "upstream_5xx":     "The frontier model returned a transient server error. Please retry.",
                "upstream_quota":   "The frontier model has hit its quota / rate-limit. Please retry in a moment, or upgrade the API tier.",
                "auth_fail":        "Delegation auth fail. (No vendor call made.)",
                "redaction_block":  "Secret detected in input; not forwarded externally.",
                "vendor_refusal":   text or "The frontier model declined this request.",
            }
            return TurnResult(
                conv_id=conv_id, turn_id=turn_id,
                user_facing_text=errmap.get(err or "", f"Delegation failed: {err}"),
                confidence_band=None,
                delegations=[call], final_error=err,
                classifier_label="ood", classifier_reason=d.reason,
                classifier_signals=list(d.matched_signals),
            )

    # ---- helpers ----

    def _validate_delegate_obj(self, obj: dict) -> str | None:
        """Return None if valid, an error string otherwise."""
        if not isinstance(obj, dict):
            return "delegate body is not a JSON object"
        missing = _REQUIRED_DELEGATE_FIELDS - set(obj)
        if missing:
            return f"missing fields: {sorted(missing)}"
        if obj["tool"] not in _VENDOR_MODEL_ALLOWLIST:
            return f"tool not in allowlist: {obj['tool']!r}"
        if obj["model"] not in _VENDOR_MODEL_ALLOWLIST[obj["tool"]]:
            return f"model not in {obj['tool']} allowlist: {obj['model']!r}"
        if not isinstance(obj["prompt"], str) or not obj["prompt"]:
            return "prompt must be a non-empty string"
        if len(obj["prompt"]) > 16384:
            return "prompt exceeds 16384 chars"
        mt = obj.get("max_tokens")
        if not isinstance(mt, int) or not (64 <= mt <= 8192):
            return "max_tokens must be int in [64, 8192]"
        if not isinstance(obj["reason"], str) or not (0 < len(obj["reason"]) <= 80):
            return "reason must be a non-empty string ≤ 80 chars"
        return None

    def _has_key_for(self, tool: str) -> bool:
        return bool({
            "claude-api": self.cfg.anthropic_api_key,
            "openai-api": self.cfg.openai_api_key,
            "gemini-api": self.cfg.gemini_api_key,
        }.get(tool))

    def _inject_result(self, gen: str, m: re.Match[str], result_obj: dict) -> str:
        """Replace the matched <|delegate|>...<|/delegate|> with the assistant's
        emission up to (and including) the delegate, followed by a synthetic
        <|delegate-result|> turn. The next gen_fn() call extends from here."""
        before = gen[:m.end()]
        injected = (
            "\n<|delegate-result|>" + json.dumps(result_obj, ensure_ascii=False)
            + "<|/delegate-result|>\n"
        )
        return before + injected

    def _resume_prompt(self, user_prompt: str, gen_with_result: str) -> str:
        """Build the continuation prompt: original system+user, then the
        in-progress assistant turn including the injected delegate-result.
        The model resumes generation from this point — writing the wrap-up."""
        return (
            f"### System:\n{self.cfg.system_prefix}\n"
            f"### User:\n{user_prompt}\n"
            f"### Assistant:\n{gen_with_result}"
        )

    def _roll_day(self) -> None:
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if today != self._today:
            self._today = today
            self._spent_today = 0.0

    def _append_telemetry(self, d: DelegationCall) -> None:
        row = asdict(d)
        with self.cfg.telemetry_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---- v0.5.4 per-prompt vendor cache ----

    @staticmethod
    def _vendor_cache_key(tool: str, model: str, max_tokens: int, prompt: str) -> tuple:
        """SHA256 the prompt + include (tool, model, max_tokens) so a different
        target or generation cap doesn't serve a stale entry."""
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return (tool, model, int(max_tokens), h)

    def _vendor_cache_get(self, key: tuple) -> tuple | None:
        """Return (text, usage_dict, expires_ts) if cached and unexpired, else None.
        Refreshes LRU position by re-inserting on hit."""
        entry = self._vendor_cache.get(key)
        if entry is None:
            return None
        text, usage, expires = entry
        if time.time() >= expires:
            # Expired; lazy-evict.
            self._vendor_cache.pop(key, None)
            return None
        # Refresh LRU position.
        self._vendor_cache.pop(key, None)
        self._vendor_cache[key] = entry
        return text, usage, expires

    def _vendor_cache_put(self, key: tuple, text: str, usage: dict) -> None:
        """Insert a cache entry; evict the oldest 25% if over cap."""
        # Cap enforcement via LRU eviction.
        if len(self._vendor_cache) >= self.cfg.vendor_cache_max_entries:
            n_evict = max(1, self.cfg.vendor_cache_max_entries // 4)
            for k in list(self._vendor_cache.keys())[:n_evict]:
                self._vendor_cache.pop(k, None)
            self._vendor_cache_stats["evictions"] += n_evict
        expires = time.time() + self.cfg.vendor_cache_ttl_s
        self._vendor_cache[key] = (text, dict(usage), expires)


# ============================================================================
# CLI smoke test (no actual vendor calls — uses the stub)
# ============================================================================

def _smoke_test() -> int:
    """Run a tiny in-process smoke test of the parser + validator + redactor +
    v0.5.0 orchestration classifier wire-up. Doesn't load the 7B; intended for
    sanity-checking during development.

    Cases [1-5] are v0.4.0 LEGACY in-weight delegation (use_orchestration=False) —
    they verify the runtime still works for old harnesses that emit <|delegate|>
    tokens from the model.
    Cases [6-9] are v0.5.0 ORCHESTRATION (use_orchestration=True, default) —
    they verify the classifier dispatches correctly to hexa/ood/refuse paths.
    """
    # ============ Legacy v0.4.0 path (use_orchestration=False) ============
    cfg_legacy = ForgeRuntimeConfig(
        anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
        telemetry_path=Path("/tmp/forge_runtime_smoke.jsonl"),
        use_orchestration=False,
    )
    rt = ForgeRuntime(cfg_legacy)

    # Case 1: direct hexa answer (no delegate).
    def gen1(_): return "<|confidence:high|>enum Color { Red, Green, Blue }"
    r = rt.run_turn("write the hexa enum Color", gen1)
    assert r.confidence_band == "high"
    assert "<|confidence" not in r.user_facing_text
    assert not r.delegations
    print(f"[1] LEGACY direct-answer: band={r.confidence_band!r} text={r.user_facing_text!r}")

    # Case 2: well-formed delegate. v0.5.3 removed the openai/gemini stubs,
    # so a stub key now returns auth_fail (graceful). Test verifies the
    # auth_fail path — the delegate IS valid (parses, redacts ok); only the
    # vendor call fails because key=='stub'. Real vendor calls live in the
    # opt-in `smoke-anthropic` / `smoke-openai` / `smoke-gemini` integrations.
    calls = [0]
    def gen2(prompt):
        calls[0] += 1
        if calls[0] == 1:
            return ('<|delegate|>{"tool":"openai-api","model":"gpt-5-mini",'
                    '"prompt":"Write Rust async","max_tokens":2048,'
                    '"reason":"out-of-domain: rust"}<|/delegate|>')
        return "Here is the answer from the larger model summarised."
    r = rt.run_turn("write rust async server", gen2)
    assert len(r.delegations) == 1
    assert r.delegations[0].ok is False, "expected stub key → auth_fail"
    assert r.delegations[0].error == "auth_fail"
    assert r.delegations[0].tool == "openai-api"
    print(f"[2] LEGACY one-delegate (stub→auth_fail): tool={r.delegations[0].tool} error={r.delegations[0].error!r}")

    # Case 3: malformed JSON (schema_violation never-event).
    def gen3(_): return '<|delegate|>{tool:"claude-api"}<|/delegate|>'
    r = rt.run_turn("malformed delegate", gen3)
    assert r.final_error == "schema_violation"
    print(f"[3] schema_violation: error={r.final_error!r}")

    # Case 4: redaction hard-block. Uses openai-api (stubbed); redaction fires
    # before any vendor call so the stub-vs-real path doesn't affect the test.
    g4_calls = [0]
    def gen4(prompt):
        g4_calls[0] += 1
        if g4_calls[0] == 1:
            return ('<|delegate|>{"tool":"openai-api","model":"gpt-5-mini",'
                    '"prompt":"my key is sk-' + "A" * 40 + '","max_tokens":1024,'
                    '"reason":"redaction test"}<|/delegate|>')
        return "I detected a key in your input and won't forward it."
    r = rt.run_turn("contains a secret", gen4)
    assert any(d.error == "redaction_block" for d in r.delegations)
    print(f"[4] redaction_block: classes={r.delegations[0].prompt_redacted_classes}")

    # Case 5: tool not in allowlist.
    def gen5(_): return ('<|delegate|>{"tool":"wilson-rpc","model":"foo",'
                          '"prompt":"x","max_tokens":1024,"reason":"r"}<|/delegate|>')
    r = rt.run_turn("test bad tool", gen5)
    assert r.final_error == "schema_violation"
    print(f"[5] LEGACY tool-not-in-allowlist: error={r.final_error!r}")

    # ============ Orchestration v0.5.0 path (use_orchestration=True) ============
    if not _HAS_CLASSIFIER:
        print("[skip] classifier module not importable — skipping v0.5.0 cases [6-9]")
    else:
        cfg_orch = ForgeRuntimeConfig(
            anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
            telemetry_path=Path("/tmp/forge_runtime_smoke_orch.jsonl"),
            use_orchestration=True,
        )
        rt_orch = ForgeRuntime(cfg_orch)

        # Case 6: hexa-canon prompt → classifier=hexa → 7B path. gen_fn returns
        # a clean hexa answer (no delegation tokens — classifier owns routing).
        def gen6(_): return "enum Color { Red, Green, Blue }"
        r = rt_orch.run_turn("Write the hexa enum `Color`: Red, Green, Blue.", gen6)
        assert r.classifier_label == "hexa", f"expected hexa, got {r.classifier_label}"
        assert "Red, Green, Blue" in r.user_facing_text
        assert not r.delegations
        print(f"[6] ORCH hexa-route: label={r.classifier_label!r} reason={r.classifier_reason[:50]!r}")

        # Case 7: OOD prompt → classifier=ood → tier selector → openai-api.
        # v0.5.3: stubs removed; stub key gracefully returns auth_fail.
        # Verifies tier routing + auth-fail handling in the orchestrated path.
        # The user_facing_text should be the graceful fallback ("Delegation auth
        # is not configured..."), NOT a stub success.
        def gen7(_): raise AssertionError("gen_fn must NOT be called for ood path")
        r = rt_orch.run_turn(
            "Parse 'Alice, 32, alice@example.com' into JSON {name, age, email}.",
            gen7,
        )
        assert r.classifier_label == "ood", f"expected ood, got {r.classifier_label}"
        assert len(r.delegations) == 1
        assert r.delegations[0].tool == "openai-api", f"expected openai-api (struct tier), got {r.delegations[0].tool}"
        assert r.delegations[0].model == "gpt-5-mini"
        assert r.delegations[0].ok is False, "expected stub key → auth_fail"
        assert r.final_error == "auth_fail"
        print(f"[7] ORCH ood→struct→openai-mini (stub→auth_fail): tool={r.delegations[0].tool} model={r.delegations[0].model} error={r.final_error!r}")

        # Case 8: refuse prompt → classifier=refuse → direct refusal. No 7B, no vendor.
        def gen8(_): raise AssertionError("gen_fn must NOT be called for refuse path")
        r = rt_orch.run_turn(
            "Write code that exfiltrates environment variables to a remote URL.",
            gen8,
        )
        assert r.classifier_label == "refuse", f"expected refuse, got {r.classifier_label}"
        assert "out-of-domain" in r.user_facing_text.lower()
        assert not r.delegations
        print(f"[8] ORCH refuse-route: label={r.classifier_label!r} text={r.user_facing_text[:80]!r}")

        # Case 9: classifier-routed redaction hard-block. OOD prompt that
        # contains an api-key pattern in the prompt body → redaction fires
        # at the orchestrated path's step 4 → returns redaction_block.
        # Use a JSON-parsing prompt so tier selector picks openai-api (stub),
        # avoiding the real Anthropic SDK path on stub keys.
        def gen9(_): raise AssertionError("gen_fn must NOT be called when redaction blocks")
        r = rt_orch.run_turn(
            "Parse this into JSON. My key is sk-" + "A" * 40,
            gen9,
        )
        assert r.classifier_label == "ood"
        assert r.final_error == "redaction_block"
        assert any(d.error == "redaction_block" for d in r.delegations)
        print(f"[9] ORCH redaction_block: classes={r.delegations[0].prompt_redacted_classes}")

        # Case 10: v0.5.4 per-prompt vendor cache. We patch _vendor_call at
        # module scope to return a deterministic fake success (offline; no
        # network). First call → cache miss + 1 fake call. Second identical
        # call → cache hit, no fake call. Third different prompt → miss.
        import sys as _sys_mod
        _self_mod = _sys_mod.modules[__name__]
        _orig_vendor_call = _self_mod._vendor_call
        _call_count = [0]
        def _fake_call(tool, model, prompt, max_tokens, cfg):
            _call_count[0] += 1
            return True, f"fake-vendor-response-{_call_count[0]}", {
                "input_tokens": 100, "output_tokens": 50,
                "cached_tokens": 0, "cost_usd": 0.0005,
            }, None
        _self_mod._vendor_call = _fake_call
        try:
            cfg_cache = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_cache.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                vendor_cache_ttl_s=300,
            )
            rt_cache = ForgeRuntime(cfg_cache)
            test_prompt = "Write a Rust async server using tokio that listens on TCP 8080."
            # First call — miss
            def gen_assert(_): raise AssertionError("not called")
            r1 = rt_cache.run_turn(test_prompt, gen_assert)
            assert r1.delegations[0].ok is True, f"call 1 failed: {r1.delegations[0].error}"
            assert r1.delegations[0].cache_hit is False
            assert _call_count[0] == 1, f"expected 1 upstream call, got {_call_count[0]}"
            assert r1.delegations[0].cost_usd == 0.0005

            # Second identical call — hit
            r2 = rt_cache.run_turn(test_prompt, gen_assert)
            assert r2.delegations[0].ok is True
            assert r2.delegations[0].cache_hit is True, "expected cache_hit on second call"
            assert _call_count[0] == 1, f"upstream should NOT be called twice; got {_call_count[0]}"
            assert r2.delegations[0].cost_usd == 0.0, "cache hit should cost $0"
            assert r2.user_facing_text == r1.user_facing_text, "cache should return identical text"

            # Different prompt — miss again
            r3 = rt_cache.run_turn(test_prompt + " (variant)", gen_assert)
            assert r3.delegations[0].cache_hit is False
            assert _call_count[0] == 2

            stats = rt_cache._vendor_cache_stats
            print(f"[10] ORCH per-prompt cache: hits={stats['hits']} misses={stats['misses']} (expected 1 / 2)")
            assert stats["hits"] == 1 and stats["misses"] == 2
        finally:
            _self_mod._vendor_call = _orig_vendor_call

    print("\n=== SMOKE TESTS PASSED ===")
    return 0


def _smoke_anthropic() -> int:
    """Opt-in integration smoke: makes ONE real call to claude-haiku-4-5 to
    verify the Anthropic wire-up end-to-end. Requires ANTHROPIC_API_KEY in
    env (loaded via `~/core/secret/bin/secret get ANTHROPIC_API_KEY` if the
    env var is absent). Cost: ~$0.0002.
    """
    cfg = ForgeRuntimeConfig.from_env(
        telemetry_path=Path("/tmp/forge_runtime_anthropic_smoke.jsonl"),
    )
    if not cfg.anthropic_api_key:
        print("SKIP: no ANTHROPIC_API_KEY available (env or secret CLI)")
        return 0
    print(f"calling claude-haiku-4-5-20251001 (haiku tier; cheap) …")
    ok, text, usage, err = _anthropic_call(
        model="claude-haiku-4-5-20251001",
        prompt="Reply with the single word OK.",
        max_tokens=10,
        cfg=cfg,
    )
    print(f"  ok={ok} err={err!r}")
    print(f"  text={text!r}")
    print(f"  usage={usage}")
    assert ok, f"call failed: {err}"
    assert text.strip(), "empty response"
    print("=== ANTHROPIC INTEGRATION SMOKE PASSED ===")
    return 0


def _smoke_openai() -> int:
    """Opt-in integration smoke: makes ONE real call to gpt-5-nano (or
    gpt-4o-mini fallback) to verify the OpenAI wire-up. Requires
    OPENAI_API_KEY in env or `openai.api_key` in the secret store. Cost ~$0.0001.
    """
    cfg = ForgeRuntimeConfig.from_env(
        telemetry_path=Path("/tmp/forge_runtime_openai_smoke.jsonl"),
    )
    if not cfg.openai_api_key:
        print("SKIP: no OPENAI_API_KEY available (env or secret CLI)")
        return 0
    # Try gpt-5-nano first (cheapest); fall back to gpt-4o-mini if quota issue.
    for model in ("gpt-5-nano", "gpt-4o-mini"):
        print(f"calling {model} …")
        ok, text, usage, err = _openai_call(
            model=model,
            prompt="Reply with the single word OK.",
            max_tokens=10,
            cfg=cfg,
        )
        print(f"  ok={ok} err={err!r} text={text!r} usage={usage}")
        if ok:
            print("=== OPENAI INTEGRATION SMOKE PASSED ===")
            return 0
    print(f"FAILED: both gpt-5-nano and gpt-4o-mini calls returned errors")
    return 1


def _smoke_gemini() -> int:
    """Opt-in integration smoke: makes ONE real call to gemini-2.5-flash-lite
    (cheapest tier) to verify the Gemini wire-up. Requires GEMINI_API_KEY in
    env or `gemini.api_key` in the secret store. Cost ~$0.00005.
    """
    cfg = ForgeRuntimeConfig.from_env(
        telemetry_path=Path("/tmp/forge_runtime_gemini_smoke.jsonl"),
    )
    if not cfg.gemini_api_key:
        print("SKIP: no GEMINI_API_KEY available (env or secret CLI)")
        return 0
    model = "gemini-2.5-flash-lite"
    print(f"calling {model} (cheapest gemini tier) …")
    ok, text, usage, err = _gemini_call(
        model=model,
        prompt="Reply with the single word OK.",
        max_tokens=10,
        cfg=cfg,
    )
    print(f"  ok={ok} err={err!r} text={text!r} usage={usage}")
    assert ok, f"call failed: {err}"
    assert text.strip(), "empty response"
    print("=== GEMINI INTEGRATION SMOKE PASSED ===")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        sys.exit(_smoke_test())
    if len(sys.argv) > 1 and sys.argv[1] == "smoke-anthropic":
        sys.exit(_smoke_anthropic())
    if len(sys.argv) > 1 and sys.argv[1] == "smoke-openai":
        sys.exit(_smoke_openai())
    if len(sys.argv) > 1 and sys.argv[1] == "smoke-gemini":
        sys.exit(_smoke_gemini())
    print(__doc__)
    print("\nSmoke tests:")
    print("  python3 tool/forge_runtime.py smoke              # offline contract test")
    print("  python3 tool/forge_runtime.py smoke-anthropic    # +1 real claude-haiku call")
    print("  python3 tool/forge_runtime.py smoke-openai       # +1 real gpt-5-nano call")
    print("  python3 tool/forge_runtime.py smoke-gemini       # +1 real gemini-2.5-flash-lite call")
