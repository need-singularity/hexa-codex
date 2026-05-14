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
import sqlite3  # v0.5.13 (r61): unified WAL-backed cache + conv memory
import random  # v0.6.2 (r69): retry jitter
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
    # v0.5.8 (r56): optional file-backed cache for cross-process persistence.
    # Default None = in-memory only (process-local). When set, loads existing
    # unexpired entries on __init__ and appends new entries on `_vendor_cache_put`.
    # Compaction on eviction. File format = JSONL with one record per put:
    #   {"key": [tool, model, max_tokens, sha256], "text": "...", "usage": {...}, "expires": 12345.67}
    # CAVEAT: NOT multi-process-safe (no locking) — single-process restart-
    # persistence only. Multi-process shared cache (Redis / SQLite WAL) is v0.6.0+.
    vendor_cache_path:         Path | None = None

    # v0.5.9 (r57): multi-turn delegation memory.
    # When `multi_turn_memory_enabled=True`, runtime stores a per-conv_id
    # buffer of `ConversationTurn` records. Calling code can query via
    # `get_conversation_history(conv_id)` to render UX context.
    # When `multi_turn_memory_auto_prepend=True` (REQUIRES enabled=True),
    # the OOD path automatically prepends recent turns to the prompt as a
    # `Previous conversation:` preamble before redaction + dispatch.
    # CAVEAT: auto-prepend changes the per-prompt-cache key on every turn
    # (different SHA256 hash each time as context grows), so caching is
    # effectively single-turn. Use selectively for conversational flows.
    multi_turn_memory_enabled:      bool = False
    multi_turn_memory_max_turns:    int  = 5
    multi_turn_memory_max_chars:    int  = 8000
    multi_turn_memory_auto_prepend: bool = False
    # v0.5.13 (r61): unified SQLite WAL backend for cross-process safety.
    # When set, OVERRIDES `vendor_cache_path` and `conv_history_path` —
    # both vendor cache and conv memory live in one SQLite file using
    # `vendor_cache` and `conv_turns` tables. WAL mode supports concurrent
    # reads + serialized writes from multiple processes. stdlib `sqlite3`
    # only, no external deps. When None: fall back to JSONL paths (r56+r60
    # behavior, single-process-only).
    forge_db_path:                  Path | None = None
    # v0.6.0 (r64): toggle for anthropic cross-turn prompt-cache marker
    # (`_anthropic_cache_mark`). r62 introduced the marker as always-on
    # when multi-turn native messages are dispatched. r64 adds the toggle
    # so the marker can be A/B tested. Default True preserves r62 behavior.
    # Effect when False: `_anthropic_call` skips the cache_control marker
    # on the second-to-last message; only the system prefix is cached.
    anthropic_cross_turn_cache_enabled: bool = True
    # v0.6.2 (r69): auto-retry with exponential backoff for transient
    # vendor errors. Closes the V0_6_0_GA.md §6 v0.7 candidate.
    #
    # RETRYABLE (whitelist):
    #   - upstream_timeout (request exceeded SDK timeout)
    #   - upstream_5xx    (vendor returned 5xx server error)
    #
    # NOT RETRYABLE (deterministic / wait-needed failures):
    #   - upstream_quota  (rate-limit; immediate retry would just re-hit;
    #                      caller should wait or upgrade tier)
    #   - auth_fail       (deterministic; retry won't help)
    #   - schema_violation (config error; retry won't help)
    #   - redaction_block  (the prompt has secrets; user must rephrase)
    #
    # Default OFF (`retry_on_transient=False`) preserves r48 behavior:
    # error code surfaces directly to user-facing text and calling code
    # implements its own retry loop. When True, the runtime retries up
    # to `retry_max_attempts` times with exponential backoff
    # (`retry_base_delay_s * 2^attempt`) plus ±`retry_jitter_pct` jitter
    # to avoid thundering herd on coordinated retries from multiple processes.
    retry_on_transient:   bool   = False
    retry_max_attempts:   int    = 3
    retry_base_delay_s:   float  = 1.0
    retry_jitter_pct:     float  = 0.25

    # v0.6.4 (r71): built-in size-based rotation of `telemetry_path`.
    # No external logrotate dependency. Default OFF (0 = disabled) preserves
    # r48-r69 behavior where operators relied on `/etc/logrotate.d/forge`
    # (documented in OPERATIONS.md §2).
    #
    # When enabled (`telemetry_max_size_bytes > 0`):
    #   On each `_append_telemetry`, if the resulting file size exceeds
    #   the threshold, rotate: rename `delegation_log.jsonl` →
    #   `delegation_log.jsonl.1`, shift `.1`→`.2`, ..., delete oldest
    #   beyond `telemetry_keep_rotations`. The new write goes to a fresh
    #   empty file.
    telemetry_max_size_bytes: int = 0
    telemetry_keep_rotations: int = 5
    # v0.5.12 (r60): optional file-backed conversation memory for
    # cross-process restart-persistence. Default None = in-memory only
    # (process-local, matches r57 behavior). When set, loads existing
    # turns on __init__ and appends new turns on `_record_conversation_turn`.
    # JSONL format, one record per turn:
    #   {"conv_id": str, "turn": {turn_id, timestamp_utc, user_prompt,
    #     assistant_text, classifier_label, tool, model}}
    # CAVEAT: NOT multi-process-safe (no locking). Single-process restart-
    # persistence only. Same safety boundary as r56 vendor_cache_path.
    conv_history_path:              Path | None = None
    # v0.5.11 (r59): vendor-native message-list threading.
    # When True (requires auto_prepend=True), instead of building a
    # `Previous conversation:` string preamble, the runtime constructs a
    # proper `messages=[{role: 'user'|'assistant', content: ...}]` list
    # and sends it via the new `messages=` parameter to `_vendor_call`.
    # Benefits: anthropic/openai/gemini all consume this natively (no
    # string parsing), upstream prompt-cache aligns better with stable
    # system+early-turn prefixes, and the conversation structure is
    # legible to the vendor. CAVEAT: cache key shifts to messages-hash;
    # different conversation states produce different keys (as expected).
    multi_turn_memory_native_messages: bool = False

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
    # v0.6.2 (r69): number of upstream attempts spent on this turn.
    # 1 = first attempt succeeded OR retries disabled. >1 = retry fired.
    # latency_ms includes time spent in retry backoff.
    retry_attempts: int = 1
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class ConversationTurn:
    """v0.5.9 (r57) multi-turn delegation memory — one stored turn per conv_id.

    Recorded after run_turn completes. The buffer is per `conv_id` and capped
    by `multi_turn_memory_max_turns`. Used either (a) by calling code that
    queries `get_conversation_history()` to render UX context, OR (b) by the
    runtime's optional auto-prepend mode which feeds the previous turns into
    the next OOD prompt as a `Previous conversation:` preamble.
    """
    turn_id: str
    timestamp_utc: str
    user_prompt: str          # post-redaction, what the runtime actually saw
    assistant_text: str        # what was returned to the user
    classifier_label: str      # "hexa" | "ood" | "refuse"
    tool: str | None           # vendor tool if ood, else None
    model: str | None          # vendor model id if ood, else None


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


def _anthropic_cache_mark(msgs: list[dict]) -> list[dict]:
    """r62 (v0.5.14): anthropic cross-turn prompt-cache helper.

    Anthropic supports `cache_control: {type: 'ephemeral'}` on content
    blocks to mark a cache breakpoint. The model caches everything UP TO
    AND INCLUDING that block, with a 5-min TTL. Putting the marker on
    the LAST prior assistant message (before the current user turn)
    causes the model to cache `system + turn1.user + turn1.assistant +
    ... + turnN-1.assistant` so the next turn in the same conversation
    pays input tokens only for the newest user message.

    Input: `[{role: 'user'|'assistant', content: str}, ...]`
    Output: same list but with the second-to-last message's content
    re-wrapped as `[{type: 'text', text: ..., cache_control: ...}]`
    (a content-block list, not a bare string — anthropic accepts either).

    Returns a new list (does not mutate the input).
    """
    if len(msgs) < 2:
        return list(msgs)
    # Mark the message immediately before the last (which is the current user
    # turn). For a 3-message conversation [u, a, u], we mark the assistant.
    out = list(msgs)
    mark_idx = len(out) - 2
    target = dict(out[mark_idx])  # copy
    raw = target.get("content", "")
    if isinstance(raw, str):
        target["content"] = [{
            "type": "text",
            "text": raw,
            "cache_control": {"type": "ephemeral"},
        }]
    elif isinstance(raw, list):
        # Already content-block form; mark the LAST block.
        new_blocks = [dict(b) for b in raw]
        if new_blocks:
            last = new_blocks[-1]
            if last.get("type") == "text":
                last["cache_control"] = {"type": "ephemeral"}
        target["content"] = new_blocks
    out[mark_idx] = target
    return out


def _anthropic_call(model: str, prompt: str, max_tokens: int,
                    cfg: ForgeRuntimeConfig, *,
                    messages: list[dict] | None = None) -> tuple[bool, str, dict, str | None]:
    """Real Anthropic API call via the `anthropic` SDK.

    System prefix is short and stable — marked with `cache_control` so
    repeated calls in the same 5-minute TTL window hit the cache. Returns
    (ok, text, usage_dict, error|None) per the _vendor_call contract.

    r59 (v0.5.11): optional `messages` parameter for native message-list
    threading. When provided, it's sent directly (bypass single-prompt
    wrapping). Standard format: `[{role: 'user'|'assistant', content: str}, ...]`.
    The anthropic SDK consumes this format directly. When None, falls
    back to wrapping `prompt` as a single user turn (legacy behavior).

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
        # r59: use native messages list if provided; otherwise wrap prompt.
        msgs = messages if messages is not None else [{"role": "user", "content": prompt}]
        # r62 (v0.5.14): cross-turn upstream prompt-cache. When `messages` is
        # set AND has ≥2 turns AND cfg.anthropic_cross_turn_cache_enabled,
        # mark the boundary BEFORE the latest user message with `cache_control`
        # so anthropic caches the conversation prefix (system + earlier turns).
        # Next turn in same conv within 5-min TTL hits anthropic cache, saving
        # input tokens. Single-turn calls keep legacy behavior (only system cached).
        # r64 added the toggle so the marker can be A/B tested.
        if (messages is not None
                and len(msgs) >= 2
                and getattr(cfg, "anthropic_cross_turn_cache_enabled", True)):
            msgs = _anthropic_cache_mark(msgs)
        resp = client.messages.create(
            model=model,
            max_tokens=int(max_tokens),
            system=[{"type": "text", "text": system_prefix,
                     "cache_control": {"type": "ephemeral"}}],
            messages=msgs,
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
    # r64 fix: surface cache_create separately from cache_read. r62's
    # `cached_tokens` only captured cache_read (savings on subsequent
    # calls) but cache_create (premium paid on first writes) was hidden
    # from telemetry. Both matter for honest cross-turn cache ROI accounting.
    usage = {
        "input_tokens":  in_tok + cache_create + cache_read,
        "output_tokens": out_tok,
        "cached_tokens": cache_read,
        "cache_create_tokens": cache_create,
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
                 cfg: ForgeRuntimeConfig, *,
                 messages: list[dict] | None = None) -> tuple[bool, str, dict, str | None]:
    """Real OpenAI API call via the `openai` SDK. Uses chat.completions for
    broad compatibility (Responses API is preferred for new builds but
    chat.completions is universally supported). Auto-cache fires when the
    prompt prefix is ≥ 1024 tokens — surfaces in `usage.prompt_tokens_details.cached_tokens`.

    r59 (v0.5.11): optional `messages` parameter for native conversation
    threading. The system prefix is always prepended; if `messages` is
    supplied, user/assistant turns from the list follow it. Standard
    format `[{role: 'user'|'assistant', content: str}, ...]` works directly.

    Refusal handling: like Claude, OpenAI returns refusal text as normal
    `message.content`. Returns ok=True with refusal text; 7B echoes honestly.
    """
    try:
        import openai
    except ImportError:
        return False, "", {}, "auth_fail"  # SDK missing == effectively unauthed

    try:
        client = openai.OpenAI(api_key=cfg.openai_api_key, timeout=30.0)
        system_msg = {"role": "system", "content": (
            "You are answering a question for a small hexa-canon code-LLM "
            "that delegated this. Be concise; return code in hexa idiom if applicable.")}
        # r59: native messages or wrap prompt.
        user_msgs = messages if messages is not None else [{"role": "user", "content": prompt}]
        resp = client.chat.completions.create(
            model=model,
            max_tokens=int(max_tokens),
            messages=[system_msg, *user_msgs],
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


def _messages_to_gemini_contents(messages: list[dict]) -> list[dict]:
    """r59: translate standard `[{role: user|assistant, content: str}, ...]`
    to Gemini's contents format. Gemini uses `model` role for assistant
    turns and wraps text in a `parts` list of `{text: str}` entries."""
    out: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        # OpenAI/Anthropic-style "assistant" → Gemini "model"
        if role == "assistant":
            role = "model"
        content = m.get("content", "")
        if isinstance(content, str):
            parts = [{"text": content}]
        elif isinstance(content, list):
            # Already a parts-like structure; pass through verbatim
            parts = content
        else:
            parts = [{"text": str(content)}]
        out.append({"role": role, "parts": parts})
    return out


def _gemini_call(model: str, prompt: str, max_tokens: int,
                 cfg: ForgeRuntimeConfig, *,
                 messages: list[dict] | None = None) -> tuple[bool, str, dict, str | None]:
    """Real Gemini API call via `google.genai`. Long-context (2M tokens on
    gemini-2.5-pro) is the value-add tier; the runtime sends the full prompt
    in a single request. v0.5.3 base ships without explicit context caching;
    v0.6+ can add `cached_content` for repeated long-doc prompts.

    r59 (v0.5.11): optional `messages` parameter. When provided, translated
    to Gemini's `contents=[{role: user|model, parts: [{text: ...}]}, ...]`
    format via `_messages_to_gemini_contents`. When None, falls back to
    single-prompt mode (legacy behavior).
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
        # r59: native messages → translate to Gemini contents; else single prompt.
        contents_arg = (_messages_to_gemini_contents(messages)
                        if messages is not None else prompt)
        resp = client.models.generate_content(
            model=model,
            contents=contents_arg,
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
                 cfg: ForgeRuntimeConfig, *,
                 messages: list[dict] | None = None) -> tuple[bool, str, dict, str | None]:
    """Dispatch a vendor call. Returns (ok, text, usage_dict, error|None).

    v0.5.3 status (all three vendors REAL):
      - claude-api  → `anthropic` SDK with prompt-cache `cache_control`.
      - openai-api  → `openai` SDK (chat.completions; auto-cache ≥1024-tok prefix).
      - gemini-api  → `google.genai` SDK (`generate_content`).

    SDK presence is gated: if the package isn't installed OR no API key is
    configured, the call returns `auth_fail` cleanly. Stubs are removed —
    the runtime degrades to auth_fail instead of returning fake success.

    r59 (v0.5.11): optional `messages` parameter threads a native message
    list down to the adapter. When None, `prompt` is wrapped as a single
    user turn (legacy behavior). The two paths produce IDENTICAL output
    when `messages=[{role:'user', content: prompt}]` — the new param is
    additive, not a replacement.

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
        return _anthropic_call(model, prompt, max_tokens, cfg, messages=messages)
    if tool == "openai-api":
        return _openai_call(model, prompt, max_tokens, cfg, messages=messages)
    if tool == "gemini-api":
        return _gemini_call(model, prompt, max_tokens, cfg, messages=messages)

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


# v0.6.2 (r69): retryable error code whitelist. These represent transient
# failures where an immediate-with-backoff retry has a reasonable chance
# of succeeding (vendor server-side error or timeout). Quota / auth /
# schema / redaction are NOT retryable — see config docstring.
_RETRYABLE_ERRORS: frozenset[str] = frozenset({"upstream_5xx", "upstream_timeout"})


def _vendor_call_with_retry(tool: str, model: str, prompt: str, max_tokens: int,
                              cfg: ForgeRuntimeConfig, *,
                              messages: list[dict] | None = None
                              ) -> tuple[bool, str, dict, str | None, int]:
    """r69 auto-retry wrapper around `_vendor_call`.

    Returns `(ok, text, usage, error, attempts)` — same as `_vendor_call`
    plus the attempt count (1 if no retry, >1 if retried).

    Behavior:
      - If `cfg.retry_on_transient=False` → single call, attempts=1 always.
      - If True → up to `cfg.retry_max_attempts` calls total, retrying
        only on error codes in `_RETRYABLE_ERRORS`.
      - Backoff: `cfg.retry_base_delay_s * 2^attempt_idx`, plus
        ±`cfg.retry_jitter_pct` jitter (e.g. ±25% randomization to
        prevent thundering herd from coordinated multi-process retries).
      - On final-attempt failure, the LAST error is returned (whether
        transient or not).
    """
    if not getattr(cfg, "retry_on_transient", False):
        ok, text, usage, err = _vendor_call(tool, model, prompt, max_tokens,
                                              cfg, messages=messages)
        return ok, text, usage, err, 1

    max_attempts = max(1, int(getattr(cfg, "retry_max_attempts", 3)))
    base_delay   = max(0.0, float(getattr(cfg, "retry_base_delay_s", 1.0)))
    jitter_pct   = max(0.0, min(1.0, float(getattr(cfg, "retry_jitter_pct", 0.25))))

    last_ok, last_text, last_usage, last_err = False, "", {}, "no_attempt"
    for attempt_idx in range(max_attempts):
        last_ok, last_text, last_usage, last_err = _vendor_call(
            tool, model, prompt, max_tokens, cfg, messages=messages,
        )
        if last_ok:
            return last_ok, last_text, last_usage, last_err, attempt_idx + 1
        if last_err not in _RETRYABLE_ERRORS:
            return last_ok, last_text, last_usage, last_err, attempt_idx + 1
        if attempt_idx == max_attempts - 1:
            # Exhausted retries — return last result
            return last_ok, last_text, last_usage, last_err, attempt_idx + 1
        # Exponential backoff with jitter
        delay = base_delay * (2 ** attempt_idx)
        if jitter_pct > 0:
            delay *= (1.0 + random.uniform(-jitter_pct, jitter_pct))
        time.sleep(delay)
    return last_ok, last_text, last_usage, last_err, max_attempts


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
        self._vendor_cache_stats = {"hits": 0, "misses": 0, "evictions": 0,
                                     "file_loads": 0, "file_writes": 0,
                                     "db_loads": 0, "db_writes": 0}
        # v0.5.9 (r57): multi-turn conversation memory.
        self._conv_history: dict[str, list[ConversationTurn]] = {}
        # v0.5.12 (r60): conversation memory stats counter (mirrors cache stats).
        self._conv_history_stats = {"file_loads": 0, "file_writes": 0,
                                     "db_loads": 0, "db_writes": 0}
        # v0.5.13 (r61): unified SQLite WAL backend. When set, OVERRIDES
        # both `vendor_cache_path` and `conv_history_path`. Opens one
        # connection per runtime instance; WAL mode supports concurrent
        # reads + serialized writes from multiple processes.
        self._db: sqlite3.Connection | None = None
        if cfg.forge_db_path is not None:
            self._db_open()
            if cfg.vendor_cache_enabled:
                self._vendor_cache_load_from_db()
            if cfg.multi_turn_memory_enabled:
                self._conv_history_load_from_db()
        else:
            # Legacy JSONL fall-backs (r56 + r60). Mutually exclusive with DB.
            if cfg.vendor_cache_enabled and cfg.vendor_cache_path is not None:
                self._vendor_cache_load_from_file()
            if (cfg.multi_turn_memory_enabled
                    and cfg.conv_history_path is not None):
                self._conv_history_load_from_file()

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

        # v0.5.9 (r57) + v0.5.11 (r59): multi-turn memory auto-prepend.
        # Two modes when `auto_prepend=True` and history exists:
        #   (a) string-concat preamble (r57 default; native_messages=False)
        #   (b) vendor-native messages list (r59; native_messages=True)
        # The classifier still runs on the original `user_prompt` either
        # way — only the dispatch surface to the vendor changes.
        effective_prompt = user_prompt
        messages_for_vendor: list[dict] | None = None
        if (self.cfg.multi_turn_memory_enabled
                and self.cfg.multi_turn_memory_auto_prepend
                and self._conv_history.get(conv_id)):
            if self.cfg.multi_turn_memory_native_messages:
                # r59: build messages list; classifier still sees plain user_prompt
                messages_for_vendor = self._build_messages_with_history(conv_id, user_prompt)
            else:
                # r57 legacy: string preamble; classifier sees the assembled string
                effective_prompt = self._build_prompt_with_history(conv_id, user_prompt)

        # v0.5.0 orchestration: classify BEFORE the 7B sees anything.
        if self.cfg.use_orchestration and _HAS_CLASSIFIER:
            result = self._run_turn_orchestrated(effective_prompt, gen_fn,
                                                  conv_id=conv_id, turn_id=turn_id,
                                                  emit_filler_fn=emit_filler_fn,
                                                  messages=messages_for_vendor)
            # r57: record this turn for future context (use ORIGINAL prompt,
            # NOT the auto-prepended one, so the buffer stays clean).
            if self.cfg.multi_turn_memory_enabled:
                self._record_conversation_turn(conv_id, turn_id, user_prompt, result)
            return result

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
                                 emit_filler_fn: Callable[[str], None] | None,
                                 messages: list[dict] | None = None) -> TurnResult:
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

        # v0.5.4 + r59: per-prompt vendor cache lookup. When `messages` is
        # provided (r59 native multi-turn), the cache key is keyed on the
        # JSON-serialized messages list so different conversation states
        # produce different keys. Otherwise it's keyed on the redacted prompt.
        if messages is not None:
            cache_key = self._vendor_cache_key_for_messages(tool, model, max_tokens, messages)
        else:
            cache_key = self._vendor_cache_key(tool, model, max_tokens, redacted_prompt)
        cache_hit = False
        cached = self._vendor_cache_get(cache_key) if self.cfg.vendor_cache_enabled else None
        retry_attempts = 1  # r69: track # of upstream attempts for telemetry
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
            # r59: pass `messages` if native threading was requested; else
            # the legacy single-prompt path is used (identical results).
            # r69: wrap with retry-on-transient when enabled.
            ok, text, usage, err, retry_attempts = _vendor_call_with_retry(
                tool, model, redacted_prompt, max_tokens, self.cfg,
                messages=messages,
            )
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
            retry_attempts=retry_attempts,  # r69
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
        path = self.cfg.telemetry_path
        with path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        # r71: post-write size check + rotation. Cheap (one stat syscall);
        # skipped entirely when feature is disabled.
        if self.cfg.telemetry_max_size_bytes > 0:
            try:
                if path.stat().st_size > self.cfg.telemetry_max_size_bytes:
                    self._rotate_telemetry()
            except OSError:
                pass  # stat failed; degrade silently

    def _rotate_telemetry(self) -> None:
        """r71: rotate telemetry file when size exceeds
        `telemetry_max_size_bytes`. Renames:
          delegation_log.jsonl   → delegation_log.jsonl.1
          delegation_log.jsonl.1 → delegation_log.jsonl.2
          ...
          delegation_log.jsonl.{N-1} → delegation_log.jsonl.{N}
          delegation_log.jsonl.{N+1} → (deleted)
        where N = `telemetry_keep_rotations`. New writes start at an empty
        delegation_log.jsonl.
        """
        path = self.cfg.telemetry_path
        keep = max(1, int(self.cfg.telemetry_keep_rotations))
        # Delete the oldest if it exists
        oldest = path.with_suffix(path.suffix + f".{keep}")
        if oldest.exists():
            try:
                oldest.unlink()
            except OSError as e:
                print(f"[forge_runtime] log rotate: failed to drop oldest {oldest}: {e!r}",
                      file=_sys.stderr)
        # Shift .{N-1} → .{N}, ..., .1 → .2
        for i in range(keep - 1, 0, -1):
            src = path.with_suffix(path.suffix + f".{i}")
            dst = path.with_suffix(path.suffix + f".{i + 1}")
            if src.exists():
                try:
                    src.rename(dst)
                except OSError as e:
                    print(f"[forge_runtime] log rotate: failed shift {src}→{dst}: {e!r}",
                          file=_sys.stderr)
                    return
        # Move current → .1
        target = path.with_suffix(path.suffix + ".1")
        try:
            path.rename(target)
        except OSError as e:
            print(f"[forge_runtime] log rotate: failed primary rename: {e!r}",
                  file=_sys.stderr)

    # ---- v0.5.4 per-prompt vendor cache ----

    @staticmethod
    def _vendor_cache_key(tool: str, model: str, max_tokens: int, prompt: str) -> tuple:
        """SHA256 the prompt + include (tool, model, max_tokens) so a different
        target or generation cap doesn't serve a stale entry."""
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return (tool, model, int(max_tokens), h)

    @staticmethod
    def _vendor_cache_key_for_messages(tool: str, model: str, max_tokens: int,
                                        messages: list[dict]) -> tuple:
        """r59: cache key for vendor-native messages path. JSON-serialize the
        messages with sort_keys for deterministic hashing — different
        conversation states (different prior turns, different ordering)
        produce different keys, as expected."""
        h = hashlib.sha256(
            json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
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
        """Insert a cache entry; evict the oldest 25% if over cap; optionally
        persist (r56 file or r61 SQLite WAL) for cross-process persistence."""
        # Cap enforcement via LRU eviction.
        evicted_this_call = False
        if len(self._vendor_cache) >= self.cfg.vendor_cache_max_entries:
            n_evict = max(1, self.cfg.vendor_cache_max_entries // 4)
            for k in list(self._vendor_cache.keys())[:n_evict]:
                self._vendor_cache.pop(k, None)
            self._vendor_cache_stats["evictions"] += n_evict
            evicted_this_call = True
        expires = time.time() + self.cfg.vendor_cache_ttl_s
        self._vendor_cache[key] = (text, dict(usage), expires)
        # r61 SQLite WAL takes precedence over r56 JSONL when configured.
        if self._db is not None:
            # UPSERT; eviction handled by periodic expiry cleanup on next load.
            # (We don't aggressively delete evicted rows from the DB to avoid
            # write amplification; the next runtime load picks up most-recent.)
            self._vendor_cache_put_to_db(key, text, usage, expires)
        elif self.cfg.vendor_cache_path is not None:
            # r56 JSONL fallback.
            if evicted_this_call:
                self._vendor_cache_compact_file()
            else:
                self._vendor_cache_append_to_file(key, text, usage, expires)

    # ---- v0.5.8 (r56) file-backed cache helpers ----

    def _vendor_cache_load_from_file(self) -> None:
        """Load JSONL cache entries from `cfg.vendor_cache_path`. Skip
        expired records. Cap at max_entries (most-recent kept). Best-effort:
        a malformed line is skipped with a stderr note, NOT raised, so a
        truncated/corrupt cache file doesn't break runtime startup."""
        path = self.cfg.vendor_cache_path
        if path is None or not path.exists():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            print(f"[forge_runtime] cache file unreadable, skipping load: {e!r}", file=_sys.stderr)
            return
        now = time.time()
        loaded = 0
        skipped_expired = 0
        skipped_malformed = 0
        # Process newest-first by iterating reversed; keep first `max_entries`.
        for line in reversed(lines):
            if loaded >= self.cfg.vendor_cache_max_entries:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key_list = rec["key"]
                key = (str(key_list[0]), str(key_list[1]), int(key_list[2]), str(key_list[3]))
                text = rec["text"]
                usage = dict(rec.get("usage", {}))
                expires = float(rec["expires"])
            except (json.JSONDecodeError, KeyError, ValueError, TypeError, IndexError):
                skipped_malformed += 1
                continue
            if expires <= now:
                skipped_expired += 1
                continue
            if key in self._vendor_cache:
                # Newer entry already loaded (we're iterating newest-first).
                continue
            self._vendor_cache[key] = (text, usage, expires)
            loaded += 1
        # Re-insert in newest-last order so LRU eviction works correctly on
        # the next put (Python dict preserves insertion order).
        self._vendor_cache = dict(reversed(list(self._vendor_cache.items())))
        self._vendor_cache_stats["file_loads"] += loaded
        if skipped_malformed:
            print(f"[forge_runtime] cache load: skipped {skipped_malformed} malformed lines",
                  file=_sys.stderr)

    def _vendor_cache_append_to_file(self, key: tuple, text: str,
                                      usage: dict, expires: float) -> None:
        """Append one JSONL record to the cache file. Atomic-enough for
        single-process use (Python's text-mode line write is atomic at the
        OS level for sizes under PIPE_BUF on POSIX; we're well under that)."""
        path = self.cfg.vendor_cache_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "key":     [key[0], key[1], key[2], key[3]],
            "text":    text,
            "usage":   dict(usage),
            "expires": float(expires),
        }
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._vendor_cache_stats["file_writes"] += 1
        except OSError as e:
            # File write failures should NOT break the runtime — log and continue.
            # The in-memory cache still has the entry; persistence is best-effort.
            print(f"[forge_runtime] cache append failed (in-memory only): {e!r}",
                  file=_sys.stderr)

    # ---- v0.5.9 (r57) multi-turn delegation memory ----

    def get_conversation_history(self, conv_id: str) -> list[ConversationTurn]:
        """Return the recorded turn buffer for `conv_id` (oldest first).
        Returns empty list if no history exists. The buffer is a live
        reference — callers should not mutate it; use `clear_conversation()`."""
        return list(self._conv_history.get(conv_id, []))

    def clear_conversation(self, conv_id: str) -> None:
        """Drop the conversation buffer for `conv_id`. Useful when a session
        ends, when the user explicitly resets, or to bound long-running
        conv memory. r60/r61: if file-backed (JSONL) or DB-backed (SQLite),
        also delete the cleared conversation's persisted turns."""
        existed = conv_id in self._conv_history
        self._conv_history.pop(conv_id, None)
        if existed:
            if self._db is not None:
                self._conv_history_clear_db(conv_id)
            elif self.cfg.conv_history_path is not None:
                self._conv_history_compact_file()

    def _conv_history_load_from_file(self) -> None:
        """r60: load conversation buffers from `cfg.conv_history_path` on
        __init__. Best-effort: a malformed line is skipped with a stderr
        note. Respects `multi_turn_memory_max_turns` per conv_id (oldest
        dropped on overflow during reconstruction)."""
        path = self.cfg.conv_history_path
        if path is None or not path.exists():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            print(f"[forge_runtime] conv-history file unreadable, skipping load: {e!r}",
                  file=_sys.stderr)
            return
        n_loaded = 0
        n_malformed = 0
        max_n = self.cfg.multi_turn_memory_max_turns
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                conv_id = str(rec["conv_id"])
                t = rec["turn"]
                turn = ConversationTurn(
                    turn_id=str(t["turn_id"]),
                    timestamp_utc=str(t["timestamp_utc"]),
                    user_prompt=str(t["user_prompt"]),
                    assistant_text=str(t["assistant_text"]),
                    classifier_label=str(t["classifier_label"]),
                    tool=t.get("tool"),
                    model=t.get("model"),
                )
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                n_malformed += 1
                continue
            buf = self._conv_history.setdefault(conv_id, [])
            buf.append(turn)
            if len(buf) > max_n:
                del buf[: len(buf) - max_n]
            n_loaded += 1
        self._conv_history_stats["file_loads"] += n_loaded
        if n_malformed:
            print(f"[forge_runtime] conv-history load: skipped {n_malformed} malformed lines",
                  file=_sys.stderr)

    def _conv_history_append_to_file(self, conv_id: str, turn: "ConversationTurn") -> None:
        """r60: append one JSONL record on each successful `_record_conversation_turn`."""
        path = self.cfg.conv_history_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "conv_id": conv_id,
            "turn": {
                "turn_id":          turn.turn_id,
                "timestamp_utc":    turn.timestamp_utc,
                "user_prompt":      turn.user_prompt,
                "assistant_text":   turn.assistant_text,
                "classifier_label": turn.classifier_label,
                "tool":             turn.tool,
                "model":            turn.model,
            },
        }
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._conv_history_stats["file_writes"] += 1
        except OSError as e:
            print(f"[forge_runtime] conv-history append failed (in-memory only): {e!r}",
                  file=_sys.stderr)

    def _conv_history_compact_file(self) -> None:
        """r60: rewrite conv-history file from current in-memory state.
        Called after `clear_conversation` so dropped convs don't persist
        in the file. tmp+rename for atomicity."""
        path = self.cfg.conv_history_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        records: list[str] = []
        for conv_id, buf in self._conv_history.items():
            for turn in buf:
                rec = {
                    "conv_id": conv_id,
                    "turn": {
                        "turn_id":          turn.turn_id,
                        "timestamp_utc":    turn.timestamp_utc,
                        "user_prompt":      turn.user_prompt,
                        "assistant_text":   turn.assistant_text,
                        "classifier_label": turn.classifier_label,
                        "tool":             turn.tool,
                        "model":            turn.model,
                    },
                }
                records.append(json.dumps(rec, ensure_ascii=False))
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_text("\n".join(records) + ("\n" if records else ""),
                                encoding="utf-8")
            tmp_path.replace(path)
        except OSError as e:
            print(f"[forge_runtime] conv-history compact failed: {e!r}", file=_sys.stderr)

    def _record_conversation_turn(self, conv_id: str, turn_id: str,
                                    user_prompt: str, result: "TurnResult") -> None:
        """Append a `ConversationTurn` to the per-conv buffer. Capped at
        `multi_turn_memory_max_turns` (oldest dropped on overflow). Records
        the ORIGINAL user_prompt (not auto-prepended) and the user-facing
        text from `result`."""
        if not self.cfg.multi_turn_memory_enabled:
            return
        # Only record successful turns — errors leave the buffer unchanged so
        # users can retry without polluting context.
        if result.final_error is not None:
            return
        # The classifier_label is set by orchestration path; for legacy path
        # it's None — skip recording (multi-turn is v0.5.x+ feature).
        if result.classifier_label is None:
            return
        delegation = result.delegations[0] if result.delegations else None
        turn = ConversationTurn(
            turn_id=turn_id,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            user_prompt=user_prompt,
            assistant_text=result.user_facing_text,
            classifier_label=result.classifier_label,
            tool=delegation.tool if delegation else None,
            model=delegation.model if delegation else None,
        )
        buf = self._conv_history.setdefault(conv_id, [])
        buf.append(turn)
        # Cap to max_turns — drop oldest.
        max_n = self.cfg.multi_turn_memory_max_turns
        evicted = False
        if len(buf) > max_n:
            del buf[: len(buf) - max_n]
            evicted = True
        # r61 SQLite WAL takes precedence over r60 JSONL.
        if self._db is not None:
            self._conv_history_append_to_db(conv_id, turn)
            if evicted:
                # Mirror in-memory eviction in DB so rows don't accumulate.
                self._conv_history_evict_excess_db(conv_id)
        elif self.cfg.conv_history_path is not None:
            # r60 JSONL fallback.
            if evicted:
                self._conv_history_compact_file()
            else:
                self._conv_history_append_to_file(conv_id, turn)

    def _build_prompt_with_history(self, conv_id: str, user_prompt: str) -> str:
        """Construct an auto-prepended prompt: prior turns rendered as a
        'Previous conversation:' preamble + the current question. Trimmed
        from oldest if total chars exceed `multi_turn_memory_max_chars`."""
        history = self._conv_history.get(conv_id, [])
        if not history:
            return user_prompt
        max_chars = self.cfg.multi_turn_memory_max_chars
        # Build preamble newest-first then reverse so oldest comes first in
        # the final string (chronological reading order for the vendor).
        rendered: list[str] = []
        char_budget = max_chars
        for turn in reversed(history):
            block = f"User: {turn.user_prompt}\nAssistant: {turn.assistant_text}"
            if char_budget - len(block) - 2 < 0:
                break
            rendered.append(block)
            char_budget -= len(block) + 2  # +2 for the joining \n\n
        if not rendered:
            return user_prompt
        preamble = "\n\n".join(reversed(rendered))
        return (f"Previous conversation:\n{preamble}\n\n"
                f"Current question:\n{user_prompt}")

    def _build_messages_with_history(self, conv_id: str, user_prompt: str) -> list[dict]:
        """r59 (v0.5.11): construct a vendor-native messages list from prior
        turns + current user prompt. Returns `[{role:'user', content:...},
        {role:'assistant', content:...}, ..., {role:'user', content: <current>}]`.
        Trimmed from OLDEST if total content chars exceed
        `multi_turn_memory_max_chars`. The current turn is always included.
        """
        history = self._conv_history.get(conv_id, [])
        # Always include current user message; budget tracks prior turns.
        current = {"role": "user", "content": user_prompt}
        if not history:
            return [current]
        # Walk newest-first, accumulating until budget hits zero.
        max_chars = self.cfg.multi_turn_memory_max_chars
        budget = max_chars - len(user_prompt)
        msgs: list[dict] = []
        for turn in reversed(history):
            up_len = len(turn.user_prompt)
            ap_len = len(turn.assistant_text)
            if budget - up_len - ap_len < 0:
                break
            # Insert at front so chronological order is preserved (oldest first).
            msgs.insert(0, {"role": "assistant", "content": turn.assistant_text})
            msgs.insert(0, {"role": "user",      "content": turn.user_prompt})
            budget -= up_len + ap_len
        msgs.append(current)
        return msgs

    # ---- v0.5.13 (r61) unified SQLite WAL backend ----

    # r62 (v0.5.14): schema version. Bumped only on incompatible changes
    # (column drops/renames, type changes). Adding nullable columns is
    # backward-compatible via `CREATE TABLE IF NOT EXISTS` and doesn't
    # require a bump. SQLite's `user_version` pragma stores this per-DB.
    SCHEMA_VERSION = 1

    def _db_open(self) -> None:
        """Open the SQLite connection (WAL mode) and create tables if needed.
        Idempotent — calling twice is a no-op after the first.

        r62: also checks the DB's `user_version` pragma against
        `SCHEMA_VERSION`. If the DB version is NEWER than the runtime
        knows about, logs a stderr warning (forward-compat: runtime
        proceeds, but newer-version fields may be ignored). If OLDER,
        logs a different warning (calling code should run a migration —
        no auto-migration in v0.5.x). On a brand-new DB, sets user_version
        to current.
        """
        if self._db is not None:
            return
        path = self.cfg.forge_db_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None → autocommit; we explicitly use transactions
        # for multi-row operations to keep SQLite happy under WAL.
        self._db = sqlite3.connect(str(path), isolation_level=None,
                                     check_same_thread=False, timeout=10.0)
        # WAL = concurrent reads + serialized writes; durable enough for
        # cache + conv-memory use case. NORMAL sync = good perf/safety trade.
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        # r62: schema versioning. user_version starts at 0 on a fresh DB.
        cur_ver = self._db.execute("PRAGMA user_version").fetchone()[0]
        if cur_ver == 0:
            self._db.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
        elif cur_ver > self.SCHEMA_VERSION:
            print(
                f"[forge_runtime] SQLite db has user_version={cur_ver} but "
                f"runtime SCHEMA_VERSION={self.SCHEMA_VERSION}. Newer schema "
                f"detected — runtime proceeds in best-effort backward-read "
                f"mode; columns added in later versions will be ignored.",
                file=_sys.stderr,
            )
        elif cur_ver < self.SCHEMA_VERSION:
            print(
                f"[forge_runtime] SQLite db has user_version={cur_ver} but "
                f"runtime SCHEMA_VERSION={self.SCHEMA_VERSION}. Older schema "
                f"detected — no auto-migration in v0.5.x; calling code should "
                f"run a migration script or use a fresh DB path.",
                file=_sys.stderr,
            )
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS vendor_cache (
                cache_key   TEXT PRIMARY KEY,
                tool        TEXT NOT NULL,
                model       TEXT NOT NULL,
                max_tokens  INTEGER NOT NULL,
                text        TEXT NOT NULL,
                usage_json  TEXT NOT NULL,
                expires     REAL NOT NULL,
                inserted_at REAL NOT NULL
            )
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_vendor_cache_expires
                ON vendor_cache(expires)
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS conv_turns (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id          TEXT NOT NULL,
                turn_id          TEXT NOT NULL,
                timestamp_utc    TEXT NOT NULL,
                user_prompt      TEXT NOT NULL,
                assistant_text   TEXT NOT NULL,
                classifier_label TEXT NOT NULL,
                tool             TEXT,
                model            TEXT,
                recorded_at      REAL NOT NULL
            )
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_turns_conv_id
                ON conv_turns(conv_id, seq)
        """)

    def close(self) -> None:
        """Close the SQLite connection cleanly. Safe to call multiple times.
        Optional — OS reclaims FDs on process exit; SQLite WAL handles
        unclean shutdowns. Useful in tests for tempfile cleanup."""
        if self._db is not None:
            try:
                self._db.close()
            except sqlite3.Error:
                pass
            self._db = None

    # ---- SQLite vendor cache ----

    def _vendor_cache_load_from_db(self) -> None:
        """Load unexpired cache entries from SQLite into in-memory dict.
        Capped at `vendor_cache_max_entries` (most-recent kept by `inserted_at`).
        Drops expired entries via a single DELETE pass first."""
        if self._db is None:
            return
        now = time.time()
        # Lazy expiry cleanup — drops anything stale before loading.
        try:
            self._db.execute("DELETE FROM vendor_cache WHERE expires <= ?", (now,))
        except sqlite3.Error as e:
            print(f"[forge_runtime] db cache expire-cleanup failed: {e!r}", file=_sys.stderr)
        # Load most-recent up to cap.
        max_n = self.cfg.vendor_cache_max_entries
        try:
            cur = self._db.execute(
                "SELECT cache_key, tool, model, max_tokens, text, usage_json, expires "
                "FROM vendor_cache "
                "ORDER BY inserted_at DESC LIMIT ?", (max_n,)
            )
            rows = list(cur.fetchall())
        except sqlite3.Error as e:
            print(f"[forge_runtime] db cache load failed: {e!r}", file=_sys.stderr)
            return
        # Insert in oldest-first order so LRU eviction works correctly.
        for cache_key, tool, model, max_tokens, text, usage_json, expires in reversed(rows):
            # cache_key is a stored hex string; we need the tuple form back.
            # The original key format is (tool, model, max_tokens, sha256_hex).
            # We stored the sha256 portion in cache_key (the join of all 4
            # makes the row PRIMARY KEY uniquely). Reconstruct:
            key = (tool, model, int(max_tokens), cache_key)
            try:
                usage = dict(json.loads(usage_json))
            except (json.JSONDecodeError, TypeError):
                usage = {}
            self._vendor_cache[key] = (text, usage, float(expires))
        self._vendor_cache_stats["db_loads"] += len(rows)

    @staticmethod
    def _cache_key_to_sha(key: tuple) -> str:
        """Extract the sha256-hex portion of a cache key tuple for DB storage.
        Cache key format is (tool, model, max_tokens, sha256_hex)."""
        return str(key[3])

    def _vendor_cache_put_to_db(self, key: tuple, text: str,
                                  usage: dict, expires: float) -> None:
        """Insert or replace a cache row. UPSERT semantics via REPLACE."""
        if self._db is None:
            return
        tool, model, max_tokens, sha_hex = key[0], key[1], int(key[2]), str(key[3])
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO vendor_cache "
                "(cache_key, tool, model, max_tokens, text, usage_json, expires, inserted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sha_hex, tool, model, max_tokens, text,
                 json.dumps(dict(usage), ensure_ascii=False),
                 float(expires), time.time()),
            )
            self._vendor_cache_stats["db_writes"] += 1
        except sqlite3.Error as e:
            print(f"[forge_runtime] db cache put failed (in-memory only): {e!r}",
                  file=_sys.stderr)

    # ---- SQLite conv history ----

    def _conv_history_load_from_db(self) -> None:
        """Load all conv turns from DB grouped by conv_id, ordered by seq.
        Respects max_turns per conv (oldest dropped if a conv has more
        than max_turns rows — keeps the most-recent N)."""
        if self._db is None:
            return
        max_n = self.cfg.multi_turn_memory_max_turns
        try:
            cur = self._db.execute(
                "SELECT seq, conv_id, turn_id, timestamp_utc, user_prompt, "
                "       assistant_text, classifier_label, tool, model "
                "FROM conv_turns ORDER BY conv_id, seq ASC"
            )
            rows = list(cur.fetchall())
        except sqlite3.Error as e:
            print(f"[forge_runtime] db conv load failed: {e!r}", file=_sys.stderr)
            return
        for _seq, conv_id, turn_id, ts, up, at, label, tool, model in rows:
            turn = ConversationTurn(
                turn_id=str(turn_id), timestamp_utc=str(ts),
                user_prompt=str(up), assistant_text=str(at),
                classifier_label=str(label),
                tool=tool, model=model,
            )
            buf = self._conv_history.setdefault(str(conv_id), [])
            buf.append(turn)
            if len(buf) > max_n:
                del buf[: len(buf) - max_n]
        self._conv_history_stats["db_loads"] += len(rows)

    def _conv_history_append_to_db(self, conv_id: str,
                                      turn: "ConversationTurn") -> None:
        """Append a single conv-turn row to the DB."""
        if self._db is None:
            return
        try:
            self._db.execute(
                "INSERT INTO conv_turns "
                "(conv_id, turn_id, timestamp_utc, user_prompt, assistant_text, "
                " classifier_label, tool, model, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, turn.turn_id, turn.timestamp_utc, turn.user_prompt,
                 turn.assistant_text, turn.classifier_label, turn.tool,
                 turn.model, time.time()),
            )
            self._conv_history_stats["db_writes"] += 1
        except sqlite3.Error as e:
            print(f"[forge_runtime] db conv append failed (in-memory only): {e!r}",
                  file=_sys.stderr)

    def _conv_history_evict_excess_db(self, conv_id: str) -> None:
        """When in-memory buffer was capped (oldest dropped), mirror the
        eviction in the DB so file rows don't accumulate without bound.
        Keep only the most-recent `max_turns` rows for this conv_id."""
        if self._db is None:
            return
        max_n = self.cfg.multi_turn_memory_max_turns
        try:
            # Get seqs ordered newest-first; everything beyond max_n is excess.
            cur = self._db.execute(
                "SELECT seq FROM conv_turns WHERE conv_id = ? "
                "ORDER BY seq DESC LIMIT -1 OFFSET ?",
                (conv_id, max_n),
            )
            stale_seqs = [r[0] for r in cur.fetchall()]
            if stale_seqs:
                placeholders = ",".join("?" * len(stale_seqs))
                self._db.execute(
                    f"DELETE FROM conv_turns WHERE seq IN ({placeholders})",
                    stale_seqs,
                )
        except sqlite3.Error as e:
            print(f"[forge_runtime] db conv evict failed: {e!r}", file=_sys.stderr)

    def _conv_history_clear_db(self, conv_id: str) -> None:
        """Delete all rows for a conv_id (mirror of `clear_conversation`)."""
        if self._db is None:
            return
        try:
            self._db.execute("DELETE FROM conv_turns WHERE conv_id = ?", (conv_id,))
        except sqlite3.Error as e:
            print(f"[forge_runtime] db conv clear failed: {e!r}", file=_sys.stderr)

    def _vendor_cache_compact_file(self) -> None:
        """Rewrite the cache file from current in-memory state. Called after
        an LRU eviction so the file doesn't grow with stale records."""
        path = self.cfg.vendor_cache_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        records: list[str] = []
        for key, (text, usage, expires) in self._vendor_cache.items():
            rec = {
                "key":     [key[0], key[1], key[2], key[3]],
                "text":    text,
                "usage":   dict(usage),
                "expires": float(expires),
            }
            records.append(json.dumps(rec, ensure_ascii=False))
        # Write to a tmp file then rename for atomicity.
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_text("\n".join(records) + ("\n" if records else ""),
                                encoding="utf-8")
            tmp_path.replace(path)
        except OSError as e:
            print(f"[forge_runtime] cache compact failed: {e!r}", file=_sys.stderr)


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
        def _fake_call(tool, model, prompt, max_tokens, cfg, *, messages=None):
            # r59: accept optional `messages` kwarg (ignored by stub — both
            # prompt and messages produce the same fake response).
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

        # Case 11: v0.5.8 (r56) file-backed cache cross-process persistence.
        # Same monkey-patch trick. Two runtime instances share a JSONL cache
        # file; instance A writes, instance B (created after) reads on init.
        _self_mod._vendor_call = _fake_call
        _call_count[0] = 0  # reset
        cache_file = Path("/tmp/forge_runtime_smoke_cache_file.jsonl")
        if cache_file.exists():
            cache_file.unlink()  # clean start
        try:
            cfg_file_a = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_file_a.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                vendor_cache_ttl_s=300,
                vendor_cache_path=cache_file,
            )
            rt_a = ForgeRuntime(cfg_file_a)
            test_prompt = "Write a Python decorator that caches function results."
            # Instance A: real upstream call → cache miss + file write
            def gen_assert(_): raise AssertionError("not called")
            r_a = rt_a.run_turn(test_prompt, gen_assert)
            assert r_a.delegations[0].ok is True
            assert r_a.delegations[0].cache_hit is False
            assert _call_count[0] == 1
            assert cache_file.exists(), "cache file should be created on first put"
            file_lines_after_put = len(cache_file.read_text().strip().splitlines())
            assert file_lines_after_put == 1, f"expected 1 JSONL record, got {file_lines_after_put}"

            # Instance B: brand-new runtime, same cache file. Should load on init.
            cfg_file_b = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_file_b.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                vendor_cache_ttl_s=300,
                vendor_cache_path=cache_file,
            )
            rt_b = ForgeRuntime(cfg_file_b)
            # Instance B should have loaded 1 entry from file
            assert rt_b._vendor_cache_stats["file_loads"] == 1, (
                f"expected file_loads=1, got {rt_b._vendor_cache_stats}"
            )
            # Same prompt through instance B → cache hit, NO new upstream call
            r_b = rt_b.run_turn(test_prompt, gen_assert)
            assert r_b.delegations[0].ok is True
            assert r_b.delegations[0].cache_hit is True, "instance B should hit cache loaded from file"
            assert _call_count[0] == 1, f"instance B should NOT call upstream; got {_call_count[0]}"
            assert r_b.delegations[0].cost_usd == 0.0
            print(f"[11] ORCH file-backed cache: rt_b loaded {rt_b._vendor_cache_stats['file_loads']} "
                  f"entry from file, served {rt_b._vendor_cache_stats['hits']} hit(s) cross-process")
        finally:
            _self_mod._vendor_call = _orig_vendor_call
            if cache_file.exists():
                cache_file.unlink()

        # Case 12: v0.5.9 (r57) multi-turn delegation memory.
        # Verifies (a) ConversationTurn buffer per conv_id with cap; (b)
        # public API get/clear; (c) auto-prepend mode constructs prompt with
        # `Previous conversation:` preamble.
        _self_mod._vendor_call = _fake_call
        _call_count[0] = 0  # reset
        captured_prompts: list[str] = []  # what the (fake) vendor saw
        def _fake_call_capture(tool, model, prompt, max_tokens, cfg, *, messages=None):
            # r59: capture both prompt + messages. When `messages` is set
            # (native path), record it; otherwise record the wrapped prompt.
            captured_prompts.append(messages if messages is not None else prompt)
            _call_count[0] += 1
            return True, f"answer-{_call_count[0]}", {
                "input_tokens": 100, "output_tokens": 50,
                "cached_tokens": 0, "cost_usd": 0.001,
            }, None
        _self_mod._vendor_call = _fake_call_capture
        try:
            cfg_mem = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_mem.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,    # disable cache so each call hits vendor
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=3,
                multi_turn_memory_auto_prepend=True,
                multi_turn_memory_max_chars=2000,
            )
            rt_mem = ForgeRuntime(cfg_mem)
            conv_id = "smoke-conv-12"
            # Turn 1 — empty history; effective_prompt == user_prompt
            r1 = rt_mem.run_turn(
                "Write a Python decorator that retries on failure.",
                gen_fn=lambda _: "",  # unused for ood path
                conv_id=conv_id,
            )
            assert r1.delegations[0].ok is True
            assert r1.classifier_label == "ood"
            hist1 = rt_mem.get_conversation_history(conv_id)
            assert len(hist1) == 1, f"expected 1 stored turn, got {len(hist1)}"
            assert hist1[0].user_prompt == "Write a Python decorator that retries on failure."
            assert hist1[0].assistant_text == "answer-1"
            assert hist1[0].tool == "claude-api"

            # Turn 2 — should auto-prepend turn 1
            r2 = rt_mem.run_turn(
                "Now show the same thing in TypeScript.",
                gen_fn=lambda _: "",
                conv_id=conv_id,
            )
            assert r2.delegations[0].ok is True
            # Check captured upstream prompt for turn 2 contains turn-1 context
            assert "Previous conversation:" in captured_prompts[1], (
                f"turn 2 should have preamble; got:\n{captured_prompts[1][:300]}"
            )
            assert "Python decorator" in captured_prompts[1], (
                "turn 2 preamble should include turn-1 user prompt"
            )
            assert "answer-1" in captured_prompts[1], (
                "turn 2 preamble should include turn-1 assistant text"
            )
            # Verify storage records the ORIGINAL prompt (not the auto-prepended one)
            hist2 = rt_mem.get_conversation_history(conv_id)
            assert len(hist2) == 2
            assert hist2[1].user_prompt == "Now show the same thing in TypeScript."

            # Turns 3 + 4 — verify cap (max_turns=3 → only keep last 3)
            rt_mem.run_turn("Now in Rust.", gen_fn=lambda _: "", conv_id=conv_id)
            rt_mem.run_turn("Now in Go.", gen_fn=lambda _: "", conv_id=conv_id)
            hist4 = rt_mem.get_conversation_history(conv_id)
            assert len(hist4) == 3, f"buffer cap is 3, got {len(hist4)}"
            # Oldest (Python) should have been dropped
            user_prompts = [t.user_prompt for t in hist4]
            assert "Python" not in " ".join(user_prompts), (
                f"oldest turn should be evicted; buffer={user_prompts}"
            )

            # clear_conversation drops the buffer
            rt_mem.clear_conversation(conv_id)
            assert rt_mem.get_conversation_history(conv_id) == []
            print(f"[12] ORCH multi-turn memory: stored {len(hist4)} turns (cap 3); "
                  f"auto-prepend verified in turn 2 prompt")
        finally:
            _self_mod._vendor_call = _orig_vendor_call

        # Case 13: v0.5.11 (r59) vendor-native message-list threading.
        # Multi-turn auto-prepend with native_messages=True should produce a
        # proper `[{role:'user', content:...}, {role:'assistant', ...},
        # {role:'user', content: <current>}]` list passed via the new
        # `messages` kwarg — NOT a `Previous conversation:` string preamble.
        _self_mod._vendor_call = _fake_call_capture
        _call_count[0] = 0
        captured_prompts.clear()
        try:
            cfg_nm = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_nm.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=5,
                multi_turn_memory_auto_prepend=True,
                multi_turn_memory_native_messages=True,  # r59 ON
                multi_turn_memory_max_chars=4000,
            )
            rt_nm = ForgeRuntime(cfg_nm)
            conv_id = "smoke-conv-13"

            # Turn 1 — no history; messages-mode still kicks in but only with current turn
            r1 = rt_nm.run_turn(
                "Write a Python decorator that retries on failure.",
                gen_fn=lambda _: "", conv_id=conv_id,
            )
            assert r1.delegations[0].ok is True
            # Turn 1 has NO history → run_turn doesn't trigger native messages
            # path (history is empty), so captured_prompts[0] is the STRING.
            assert isinstance(captured_prompts[0], str), \
                f"turn 1 should be string (no history); got {type(captured_prompts[0])}"

            # Turn 2 — history exists → native messages path fires
            r2 = rt_nm.run_turn(
                "Now show the same thing in TypeScript.",
                gen_fn=lambda _: "", conv_id=conv_id,
            )
            assert r2.delegations[0].ok is True
            # captured_prompts[1] should now be a LIST (messages format)
            assert isinstance(captured_prompts[1], list), \
                f"turn 2 should be messages list (native_messages=True); got {type(captured_prompts[1])}"
            msgs = captured_prompts[1]
            # Expected: [{u:t1}, {a:answer-1}, {u:t2-current}]
            assert len(msgs) == 3, f"expected 3 messages, got {len(msgs)}: {msgs}"
            assert msgs[0]["role"] == "user"
            assert "Python decorator" in msgs[0]["content"]
            assert msgs[1]["role"] == "assistant"
            assert "answer-1" in msgs[1]["content"]
            assert msgs[2]["role"] == "user"
            assert "TypeScript" in msgs[2]["content"]
            # CRITICAL: turn 2's content must NOT contain a string preamble —
            # the native path bypasses _build_prompt_with_history entirely.
            assert "Previous conversation:" not in msgs[2]["content"], (
                "native_messages mode must NOT use string preamble"
            )

            # Turn 3 — full 3-turn history threaded
            r3 = rt_nm.run_turn(
                "And in Rust now.",
                gen_fn=lambda _: "", conv_id=conv_id,
            )
            assert isinstance(captured_prompts[2], list)
            msgs3 = captured_prompts[2]
            # Expected: [u:t1, a:1, u:t2, a:2, u:t3-current]
            assert len(msgs3) == 5
            assert msgs3[-1]["content"] == "And in Rust now."
            assert msgs3[-1]["role"] == "user"

            # Verify gemini contents translation
            gemini_contents = _messages_to_gemini_contents(msgs3)
            assert all("role" in c and "parts" in c for c in gemini_contents)
            assert gemini_contents[1]["role"] == "model"  # assistant → model
            assert gemini_contents[1]["parts"][0]["text"] == "answer-1"

            print(f"[13] ORCH native messages (r59): turn 2 sent {len(msgs)} msgs; "
                  f"turn 3 sent {len(msgs3)} msgs; gemini-translate ✓")
        finally:
            _self_mod._vendor_call = _orig_vendor_call

        # Case 14: v0.5.12 (r60) persistent conv memory cross-process.
        # Mirrors case [11] file-backed cache pattern. Runtime A records
        # turns to a JSONL conv-history file; runtime B (independent
        # instance) loads them on init and queries via get_conversation_history.
        _self_mod._vendor_call = _fake_call
        _call_count[0] = 0
        conv_file = Path("/tmp/forge_runtime_smoke_conv_history.jsonl")
        if conv_file.exists():
            conv_file.unlink()
        try:
            cfg_conv_a = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_conv_a.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=5,
                multi_turn_memory_auto_prepend=False,  # disable to keep test focused on storage
                conv_history_path=conv_file,
            )
            rt_ca = ForgeRuntime(cfg_conv_a)
            conv_id = "smoke-conv-14"
            # Runtime A: record 3 turns
            for q in ["Question 1.", "Question 2.", "Question 3."]:
                rt_ca.run_turn(q, gen_fn=lambda _: "", conv_id=conv_id)
            assert conv_file.exists(), "conv-history file should exist after first record"
            file_lines = len(conv_file.read_text().strip().splitlines())
            assert file_lines == 3, f"expected 3 records, got {file_lines}"
            hist_a = rt_ca.get_conversation_history(conv_id)
            assert len(hist_a) == 3

            # Runtime B: brand-new instance, same conv_history_path
            cfg_conv_b = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_conv_b.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=5,
                conv_history_path=conv_file,
            )
            rt_cb = ForgeRuntime(cfg_conv_b)
            assert rt_cb._conv_history_stats["file_loads"] == 3, (
                f"expected 3 loaded, got {rt_cb._conv_history_stats}"
            )
            hist_b = rt_cb.get_conversation_history(conv_id)
            assert len(hist_b) == 3, f"runtime B should have 3 loaded turns, got {len(hist_b)}"
            assert hist_b[0].user_prompt == "Question 1."
            assert hist_b[2].user_prompt == "Question 3."

            # Append one more turn through runtime B → file grows to 4 lines
            rt_cb.run_turn("Question 4.", gen_fn=lambda _: "", conv_id=conv_id)
            file_lines_after = len(conv_file.read_text().strip().splitlines())
            assert file_lines_after == 4, f"expected 4 records after append, got {file_lines_after}"
            hist_b2 = rt_cb.get_conversation_history(conv_id)
            assert len(hist_b2) == 4

            # clear_conversation through runtime B → file compacted (0 records)
            rt_cb.clear_conversation(conv_id)
            assert rt_cb.get_conversation_history(conv_id) == []
            file_lines_after_clear = len(conv_file.read_text().strip().splitlines())
            assert file_lines_after_clear == 0, (
                f"expected 0 records after clear, got {file_lines_after_clear}"
            )
            print(f"[14] ORCH file-backed conv memory: rt_b loaded {rt_cb._conv_history_stats['file_loads']} "
                  f"turns; append→4 records; clear→0 records (compacted)")
        finally:
            _self_mod._vendor_call = _orig_vendor_call
            if conv_file.exists():
                conv_file.unlink()

        # Case 15: v0.5.13 (r61) SQLite WAL backend — vendor cache.
        # Mirrors case [11] but uses forge_db_path (SQLite) instead of
        # vendor_cache_path (JSONL). Runtime A writes, runtime B reads.
        _self_mod._vendor_call = _fake_call
        _call_count[0] = 0
        db_file = Path("/tmp/forge_runtime_smoke_db.sqlite3")
        for p in (db_file, db_file.with_suffix(".sqlite3-wal"),
                  db_file.with_suffix(".sqlite3-shm")):
            if p.exists():
                p.unlink()
        try:
            cfg_db_a = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_db_a.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                vendor_cache_ttl_s=300,
                forge_db_path=db_file,
            )
            rt_da = ForgeRuntime(cfg_db_a)
            test_prompt = "Write a Rust function that splits a string on commas."
            r_a = rt_da.run_turn(test_prompt, gen_fn=lambda _: "")
            assert r_a.delegations[0].ok is True
            assert r_a.delegations[0].cache_hit is False
            assert _call_count[0] == 1
            assert rt_da._vendor_cache_stats["db_writes"] >= 1, (
                f"expected db_writes >=1, got {rt_da._vendor_cache_stats}"
            )
            assert db_file.exists(), "SQLite db file should exist after first put"
            rt_da.close()

            # Runtime B: brand-new instance, same forge_db_path → should load
            cfg_db_b = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_db_b.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                vendor_cache_ttl_s=300,
                forge_db_path=db_file,
            )
            rt_db = ForgeRuntime(cfg_db_b)
            assert rt_db._vendor_cache_stats["db_loads"] == 1, (
                f"expected db_loads=1, got {rt_db._vendor_cache_stats}"
            )
            # Same prompt → cache hit, no upstream call
            r_b = rt_db.run_turn(test_prompt, gen_fn=lambda _: "")
            assert r_b.delegations[0].ok is True
            assert r_b.delegations[0].cache_hit is True, "instance B should hit cache loaded from DB"
            assert _call_count[0] == 1, f"instance B should NOT call upstream; got {_call_count[0]}"
            assert r_b.delegations[0].cost_usd == 0.0
            print(f"[15] ORCH SQLite cache (r61): rt_b loaded {rt_db._vendor_cache_stats['db_loads']} "
                  f"entry from DB, served {rt_db._vendor_cache_stats['hits']} hit(s) cross-process")
            rt_db.close()
        finally:
            _self_mod._vendor_call = _orig_vendor_call
            for p in (db_file, db_file.with_suffix(".sqlite3-wal"),
                      db_file.with_suffix(".sqlite3-shm")):
                if p.exists():
                    p.unlink()

        # Case 16: v0.5.13 (r61) SQLite WAL backend — conv memory.
        # Mirrors case [14] but uses forge_db_path. Tests append + load +
        # clear (DB row delete on conv reset).
        _self_mod._vendor_call = _fake_call
        _call_count[0] = 0
        db_file = Path("/tmp/forge_runtime_smoke_db_conv.sqlite3")
        for p in (db_file, db_file.with_suffix(".sqlite3-wal"),
                  db_file.with_suffix(".sqlite3-shm")):
            if p.exists():
                p.unlink()
        try:
            cfg_dbc_a = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_dbc_a.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=5,
                forge_db_path=db_file,
            )
            rt_dca = ForgeRuntime(cfg_dbc_a)
            conv_id = "smoke-conv-16"
            for q in ["DB Q1.", "DB Q2.", "DB Q3."]:
                rt_dca.run_turn(q, gen_fn=lambda _: "", conv_id=conv_id)
            assert rt_dca._conv_history_stats["db_writes"] == 3, (
                f"expected 3 db_writes, got {rt_dca._conv_history_stats}"
            )
            rt_dca.close()

            # Runtime B: load from same DB
            cfg_dbc_b = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_dbc_b.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=False,
                multi_turn_memory_enabled=True,
                multi_turn_memory_max_turns=5,
                forge_db_path=db_file,
            )
            rt_dcb = ForgeRuntime(cfg_dbc_b)
            assert rt_dcb._conv_history_stats["db_loads"] == 3, (
                f"expected db_loads=3, got {rt_dcb._conv_history_stats}"
            )
            hist = rt_dcb.get_conversation_history(conv_id)
            assert len(hist) == 3
            assert hist[0].user_prompt == "DB Q1."
            assert hist[2].user_prompt == "DB Q3."

            # Append through B
            rt_dcb.run_turn("DB Q4.", gen_fn=lambda _: "", conv_id=conv_id)
            assert rt_dcb._conv_history_stats["db_writes"] == 1
            hist2 = rt_dcb.get_conversation_history(conv_id)
            assert len(hist2) == 4

            # Clear → DB rows for this conv_id deleted
            rt_dcb.clear_conversation(conv_id)
            assert rt_dcb.get_conversation_history(conv_id) == []
            # Verify DB shows 0 rows for the conv
            n_rows = rt_dcb._db.execute(
                "SELECT COUNT(*) FROM conv_turns WHERE conv_id = ?", (conv_id,)
            ).fetchone()[0]
            assert n_rows == 0, f"expected 0 rows after clear, got {n_rows}"
            print(f"[16] ORCH SQLite conv (r61): rt_b loaded {rt_dcb._conv_history_stats['db_loads']} "
                  f"turns; appended 1; clear→0 rows in DB")
            rt_dcb.close()
        finally:
            _self_mod._vendor_call = _orig_vendor_call
            for p in (db_file, db_file.with_suffix(".sqlite3-wal"),
                      db_file.with_suffix(".sqlite3-shm")):
                if p.exists():
                    p.unlink()

        # Case 17: r62 (v0.5.14) anthropic cache_mark helper unit test.
        # Verifies cross-turn cache_control insertion on the second-to-last
        # message of a conversation. The runtime helper transforms a plain
        # messages list into anthropic content-block form with cache_control.
        msgs_in = [
            {"role": "user", "content": "First question."},
            {"role": "assistant", "content": "First answer."},
            {"role": "user", "content": "Follow-up."},
        ]
        msgs_marked = _anthropic_cache_mark(msgs_in)
        assert len(msgs_marked) == 3
        # First user msg unchanged (still string content)
        assert msgs_marked[0]["content"] == "First question."
        # Assistant msg (index 1, second-to-last) should be content-block form
        assistant = msgs_marked[1]
        assert isinstance(assistant["content"], list), (
            f"assistant content should be list, got {type(assistant['content'])}"
        )
        assert assistant["content"][0]["type"] == "text"
        assert assistant["content"][0]["text"] == "First answer."
        assert assistant["content"][0]["cache_control"] == {"type": "ephemeral"}, (
            f"expected cache_control marker, got {assistant['content'][0]}"
        )
        # Last user msg unchanged (current turn isn't cached — it's the new data)
        assert msgs_marked[2]["content"] == "Follow-up."
        # Original input not mutated
        assert msgs_in[1]["content"] == "First answer.", "input list should not be mutated"
        # Single-turn → no marking
        single = [{"role": "user", "content": "Solo."}]
        marked_single = _anthropic_cache_mark(single)
        assert len(marked_single) == 1
        assert marked_single[0]["content"] == "Solo."  # unchanged
        print(f"[17] anthropic cache_mark (r62): cross-turn cache_control on "
              f"second-to-last msg; single-turn unchanged; input not mutated")

        # Case 18: r62 SQLite schema_version PRAGMA. Open a fresh DB,
        # verify user_version is set to SCHEMA_VERSION (1).
        db_ver_file = Path("/tmp/forge_runtime_smoke_db_ver.sqlite3")
        for p in (db_ver_file, db_ver_file.with_suffix(".sqlite3-wal"),
                  db_ver_file.with_suffix(".sqlite3-shm")):
            if p.exists():
                p.unlink()
        try:
            cfg_ver = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_runtime_smoke_db_ver.jsonl"),
                use_orchestration=True,
                vendor_cache_enabled=True,
                forge_db_path=db_ver_file,
            )
            rt_ver = ForgeRuntime(cfg_ver)
            user_ver = rt_ver._db.execute("PRAGMA user_version").fetchone()[0]
            assert user_ver == ForgeRuntime.SCHEMA_VERSION, (
                f"expected user_version={ForgeRuntime.SCHEMA_VERSION}, got {user_ver}"
            )
            print(f"[18] schema versioning (r62): user_version={user_ver} matches "
                  f"SCHEMA_VERSION={ForgeRuntime.SCHEMA_VERSION}")
            rt_ver.close()
        finally:
            for p in (db_ver_file, db_ver_file.with_suffix(".sqlite3-wal"),
                      db_ver_file.with_suffix(".sqlite3-shm")):
                if p.exists():
                    p.unlink()

        # Case 19: r69 auto-retry with exponential backoff.
        # Three scenarios:
        #  (a) retry_on_transient=False → single attempt, retry_attempts=1
        #  (b) retry_on_transient=True + transient error first 2 calls,
        #      then success on 3rd → retry_attempts=3
        #  (c) retry_on_transient=True + permanent error → no retry,
        #      retry_attempts=1
        _self_mod._vendor_call = _orig_vendor_call  # reset before patching
        call_count = [0]
        next_responses: list[tuple] = []

        def _seq_call(tool, model, prompt, max_tokens, cfg, *, messages=None):
            call_count[0] += 1
            if next_responses:
                return next_responses.pop(0)
            return True, "default-ok", {"input_tokens": 1, "output_tokens": 1,
                                          "cached_tokens": 0, "cost_usd": 0.0}, None

        _self_mod._vendor_call = _seq_call
        try:
            # Scenario (a): retry OFF, immediate success
            cfg_no_retry = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_smoke_retry_a.jsonl"),
                use_orchestration=True, vendor_cache_enabled=False,
                retry_on_transient=False,
            )
            rt_a = ForgeRuntime(cfg_no_retry)
            call_count[0] = 0
            next_responses.clear()
            r = rt_a.run_turn(
                "Write a Rust async server using tokio that listens on TCP 8080.",
                gen_fn=lambda _: "",
            )
            assert r.delegations[0].ok is True
            assert r.delegations[0].retry_attempts == 1, (
                f"retry OFF should attempt once; got {r.delegations[0].retry_attempts}"
            )
            assert call_count[0] == 1

            # Scenario (b): retry ON, 2 transient failures then success
            cfg_retry = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=Path("/tmp/forge_smoke_retry_b.jsonl"),
                use_orchestration=True, vendor_cache_enabled=False,
                retry_on_transient=True,
                retry_max_attempts=3,
                retry_base_delay_s=0.01,  # fast for test
                retry_jitter_pct=0.0,
            )
            rt_b = ForgeRuntime(cfg_retry)
            call_count[0] = 0
            next_responses.clear()
            next_responses.append((False, "", {}, "upstream_5xx"))
            next_responses.append((False, "", {}, "upstream_timeout"))
            next_responses.append((True, "recovered", {
                "input_tokens": 1, "output_tokens": 1,
                "cached_tokens": 0, "cost_usd": 0.0001,
            }, None))
            r = rt_b.run_turn(
                "Write a Rust async server using tokio that listens on TCP 8080.",
                gen_fn=lambda _: "",
            )
            assert r.delegations[0].ok is True
            assert r.delegations[0].retry_attempts == 3, (
                f"expected 3 attempts, got {r.delegations[0].retry_attempts}"
            )
            assert call_count[0] == 3
            assert r.delegations[0].text.startswith("recovered")

            # Scenario (c): retry ON, but auth_fail (non-retryable) — no retry
            rt_c = ForgeRuntime(cfg_retry)
            call_count[0] = 0
            next_responses.clear()
            next_responses.append((False, "", {}, "auth_fail"))
            r = rt_c.run_turn(
                "Write a Rust async server using tokio that listens on TCP 8080.",
                gen_fn=lambda _: "",
            )
            assert r.delegations[0].ok is False
            assert r.delegations[0].error == "auth_fail"
            assert r.delegations[0].retry_attempts == 1, (
                f"non-retryable error should not retry; got {r.delegations[0].retry_attempts}"
            )
            assert call_count[0] == 1
            print(f"[19] r69 auto-retry: OFF=1 attempt, ON+transient×2+ok=3 attempts, "
                  f"ON+auth_fail=1 attempt (non-retryable)")
        finally:
            _self_mod._vendor_call = _orig_vendor_call

        # Case 20: r71 built-in telemetry log rotation.
        _self_mod._vendor_call = _seq_call
        try:
            tel_path = Path("/tmp/forge_smoke_rotate.jsonl")
            for p in [tel_path] + [tel_path.with_suffix(f".jsonl.{i}") for i in range(1, 6)]:
                if p.exists():
                    p.unlink()
            # Each delegation_log row ≈ 527 bytes (measured). Set threshold
            # = 800 so ~2 records fit per file before rotation triggers.
            cfg_rot = ForgeRuntimeConfig(
                anthropic_api_key="stub", openai_api_key="stub", gemini_api_key="stub",
                telemetry_path=tel_path,
                use_orchestration=True, vendor_cache_enabled=False,
                telemetry_max_size_bytes=800,  # ~1.5 records per file
                telemetry_keep_rotations=3,
            )
            rt_rot = ForgeRuntime(cfg_rot)
            # 12 turns × 527 bytes per row, threshold 800 → rotate every 2
            # records → 6 rotation events, but cap at keep_rotations=3.
            # End-state: current file (1 record, ~527 bytes; under threshold)
            # + .1 + .2 + .3 (each ~1054 bytes from 2-record cohort).
            for _ in range(12):
                rt_rot.run_turn(
                    "Write a Rust async server using tokio that listens on TCP 8080.",
                    gen_fn=lambda _: "",
                )
            # Expect: 3 rotation files .1 .2 .3 exist, .4/.5 dropped.
            # Current jsonl existence is timing-dependent (may be present or
            # missing depending on whether the last turn just rotated); not
            # part of the assertion (functionality-only test).
            assert tel_path.with_suffix(".jsonl.1").exists(), "rotation .1 should exist"
            assert tel_path.with_suffix(".jsonl.2").exists(), "rotation .2 should exist"
            assert tel_path.with_suffix(".jsonl.3").exists(), "rotation .3 should exist"
            assert not tel_path.with_suffix(".jsonl.4").exists(), (
                "rotation .4 should NOT exist (keep_rotations=3)"
            )
            assert not tel_path.with_suffix(".jsonl.5").exists()
            # Add one extra turn to guarantee current file exists for size check
            rt_rot.run_turn(
                "Write a Rust async server using tokio that listens on TCP 8080.",
                gen_fn=lambda _: "",
            )
            assert tel_path.exists(), "current telemetry file should exist after final append"
            sz = tel_path.stat().st_size
            assert sz <= 800, f"current file should be under threshold; got {sz}"
            print(f"[20] r71 log rotation: 12 rotations + 1 final → current {sz}b + .1/.2/.3 "
                  f"(keep_rotations=3 enforced; .4/.5 dropped)")
        finally:
            _self_mod._vendor_call = _orig_vendor_call
            for p in [tel_path] + [tel_path.with_suffix(f".jsonl.{i}") for i in range(1, 6)]:
                if p.exists():
                    p.unlink()

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
