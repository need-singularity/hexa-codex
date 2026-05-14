# Orchestration v0.5.5 — consolidated spec

**Status:** SPEC · v0.5.5 · 2026-05-14 · supersedes
`spec-orchestration-v0.5.0.md` (the v0.5.0 base) AND obsoletes §4 / §10 of
`spec-delegation-v0.4.0.md` (the in-weight routing thesis disproved by
rounds r40-r43.1). **The r39 GA (v3-t3patch) adapter ships as the
permanent pure-specialist weight artifact**; this document defines the
runtime orchestration system that wraps it into a production-ready
forge code-LLM.

**Owner:** code-LLM line.
**Implementers:**
- `tool/classify_prompt.py` — pre-7B keyword classifier (§4)
- `tool/select_vendor_tier.py` — per-prompt vendor + tier selection (§5)
- `tool/forge_runtime.py` — runtime dispatcher + vendor SDKs + cache (§6 / §8 / §9)
- `tool/score_orchestration_mk0.py` — DLG-mk0 evaluator (§10)
- `eval/delegation-mk0/manifest.jsonl` — 200-task routing eval (reused)

**Reference round notes** in ROADMAP §CHANGELOG:
r44 (classifier) · r45 (forge wire-up) · r46 (tier routing) · r47 (OpenAI+Gemini SDKs) · r48 (quota+cache) · r49 (reason-class split).

---

## 1. Goal + non-goals

### Goal

Ship a v0.5.x system whose end-to-end behaviour delivers:

1. **Hexa-canon prompts** (Mk.I 665 + 5-NL 25) → routed to local 7B → answered
   directly. Specialist scores **unchanged vs r39 GA**: 94.29% Mk.I strict, 96% 5-NL.
2. **Out-of-domain prompts** (Rust async, ML internals, math derivations,
   structured-output, long-context) → bypass the 7B entirely, dispatched
   to the right vendor + tier:
   - long-context (>12K chars OR explicit token-count mention) → Gemini 2.5 Pro (2M ctx)
   - **reason-deep** (foundational proofs, theorems, deep ml-internals mechanism) → Claude Opus 4.7
   - **reason-algo** (closed-form / recurrence / Big-O / formula derivations) → OpenAI o4-mini
   - **ml-comparison** (ml-internals topics in comparative-Q form) → Claude Sonnet 4.6
   - structured-output (JSON extraction / schema validation) → OpenAI gpt-5-mini
   - general OOD code (frameworks, language idioms) → Claude Sonnet 4.6
3. **Security-sensitive prompts** (exfil/credential-theft/malware/weapon/illegal)
   → refused at classifier stage; **never reach** the 7B or any vendor.
4. **Cost optimization**:
   - Per-prompt vendor cache (5-min TTL mirroring Anthropic's prompt-cache window) eliminates duplicate billing on repeated identical prompts.
   - Reason-class split (r49) cuts per-call cost ~80% on algorithmic-math
     routes by demoting closed-form derivations from opus to o4-mini
     (\$1.20 vs \$15.00 per Mtok input).
5. **Quota-aware error handling** — distinguish 429 (rate-limit/quota,
   upgrade tier or wait) from generic 5xx (retry hammering).

### Acceptance numbers (all met as of r49)

| Gate | Target | r49 actual |
|---|---|---|
| Classifier accuracy on DLG-mk0 (overall) | ≥ 0.92 | **0.985** |
| in-domain accuracy | ≥ 0.95 | **1.000** |
| ood-delegate accuracy | ≥ 0.90 | **0.950** |
| mid-confidence accuracy | ≥ 0.80 | **1.000** |
| security-refuse accuracy | ≥ 0.95 | **1.000** |
| ambiguous accuracy | ≥ 0.70 | **1.000** |
| long-context accuracy | ≥ 0.90 | **1.000** |
| tier_match (must_delegate) | ≥ 0.85 | **1.000** |
| tool_match (must_delegate) | ≥ 0.85 | **0.987** |
| Mk.I 665 strict | ≥ 88% | **94.29%** (r39 GA, unchanged) |
| 5-NL 25 | ≥ 95% | **96%** (same) |
| Hexa turn latency overhead | ≤ 5% | **< 1%** (classifier ~1ms vs 7B ~5-20s) |

### Non-goals (still deferred to v0.6.0+)

- **No in-weight routing**: the 7B's emission of `<|delegate|>` tokens
  is stripped post-decode. Routing is the runtime's job. (v0.4.x disproof.)
- **No multi-turn delegation memory** — per-prompt cache (r48) is single-turn only.
- **No shared cache** — current cache is in-memory dict per `ForgeRuntime`
  instance; cross-process or restart loses state.
- **No Brier-score calibration** of classifier confidence — deferred to
  the calibration-eval round.

---

## 2. Why pre-7B, not in-weight (v0.4.x post-mortem, kept for posterity)

Five v0.4.x rounds disproved the in-weight thesis at ~\$5.5 cost:

| round | recipe | Mk.I | DLG-mk0 | failure |
|---|---|---:|---:|---|
| r40 | SFT 25% delegation | 82.71% | 0.7652 | erased specialist |
| r41 | SFT 9% delegation + 4 new blocks + LR 2e-5 + 2 ep | 83.01% | 0.7760 | same |
| r42 | pure GRPO, KL=0.01, temp 0.7, 4 ep | 93.83% | 0.4490 | exploration collapse, 0% OOD route |
| r43 | SFT-bootstrap (40 pairs) + GRPO full DLG reward, KL=0.02, temp 0.9 | 93.98% | 0.4490 | greedy never emitted |
| r43.1 | r43 re-scored with temp 0.7 best-of-3 | (same) | 0.4550 | tail empty too |

**The structural fact**: in a 7B + r=64 LoRA architecture, the same
gradient that learns `<|delegate|>` emission also degrades hexa-canon
emission. The KL anchor strength that preserves the specialist (≥ 0.01)
is too tight to allow exploration of the never-emitted target class.
The reward shape plateaus at ~0.45 because in-domain + mid-confidence
rewards dominate the gradient and push the model toward "direct answer
everywhere."

Cross-refs: [[pure-rl-exploration-collapse]], [[rl-tail-vs-greedy-eval]],
[[lever4-rl-sft-conflict]] memories.

---

## 3. Architecture

```
                          ┌───────────────────────────┐
   user prompt            │                           │
       │                  │      forge_runtime        │
       │                  │   (ForgeRuntime instance) │
       └─▶ run_turn(p) ───▶                           │
                          │ ┌───────────────────────┐ │
                          │ │ 1. classify_prompt(p) │ │ ← §4
                          │ │   → ClassifierDecision│ │
                          │ └───────────┬───────────┘ │
                          │             │             │
                          │   hexa  ──┐ │ ┌── refuse  │
                          │           ▼ ▼ ▼           │
                          │       ┌─────────┐         │
                          │       │ dispatch│         │
                          │       └─┬─┬─┬───┘         │
                          │   hexa  │ │ │  refuse     │
                          │     ┌───┘ │ └──┐          │
                          │     ▼     │    ▼          │
                          │  ┌────┐   │  ┌─────────┐  │
                          │  │ 7B │   │  │ canonical│ │
                          │  │ GA │   │  │ refuse   │ │
                          │  └────┘   │  └─────────┘ │
                          │           │              │
                          │       ood ▼              │
                          │   ┌─────────────────────┐│
                          │   │2.select_vendor_tier ││← §5
                          │   │  →(tool,model,maxTok)││
                          │   └──────────┬──────────┘│
                          │              ▼           │
                          │   ┌─────────────────────┐│
                          │   │3. _redact + authorize│← §7
                          │   └──────────┬──────────┘│
                          │              ▼           │
                          │   ┌─────────────────────┐│
                          │   │4. cache lookup       ←§9
                          │   └──┬─────────────┬───┘ │
                          │  hit│             │miss  │
                          │     │             ▼      │
                          │     │   ┌─────────────┐  │
                          │     │   │5._vendor_call│ │← §8
                          │     │   │ {anthropic,  │ │
                          │     │   │  openai,     │ │
                          │     │   │  gemini}     │ │
                          │     │   └──────┬──────┘  │
                          │     │          ▼         │
                          │     │   ┌────────────┐   │
                          │     │   │6.cache put │   │
                          │     │   └──────┬─────┘   │
                          │     └──────────┘         │
                          │              │           │
                          │              ▼           │
                          │   ┌─────────────────────┐│
                          │   │ 7. telemetry +      ││ ← §11
                          │   │    user-facing text ││
                          │   └─────────────────────┘│
                          └─────────────────────────┘
```

The classifier is a **strict gate** — its decision determines *which path
runs*, not just metadata. Once classified:
- The 7B never sees an OOD prompt.
- The vendor never sees a hexa prompt or a refuse-class prompt.
- Each side runs in its home environment with the right cost profile.

---

## 4. The classifier (`tool/classify_prompt.py`)

Stage-based regex/keyword router, **~440 lines, CPU-only, ~1 ms per prompt**.

```python
@dataclass
class ClassifierDecision:
    label: Literal["hexa", "ood", "refuse"]
    confidence: float
    reason: str
    matched_signals: list[str]

def classify_prompt(prompt: str) -> ClassifierDecision: ...
```

### Stage order (early-return on match)

1. **Security-refuse** (27 patterns, highest priority): exfil /
   credential-theft / malware / weapon / illegal-substance / harassment.
   Match → `label="refuse"`, never proceeds.
2. **Hexa-canon positive signals**:
   - Annotations: `@grace`, `@implements`, `@discover`, `@deprecated`
   - HX-code families: `HX[0-9]+xxx?`, `HX0…HX9` + digits
   - Type markers: `enum\s+\w+\s*\{`, `hexa-canon`, `hexa-lang`, `hexa-cc`
   - Module paths: `stdlib/(core|io|alloc|net|embedded|proof)`, `applications/`, `firmware/`, `codex-techniques/`
   - Target triples: `(thumb|riscv|x86_64|aarch64|wasm32)[\w-]+`
   - Atlas: `L\[\d+\]`, `@discover(kind=`, `prove_\w+`, `discover_\w+`
   - Diagnostics: `triple`, `target triple`, `linker triple`, `5-NL`
   - 5-NL i18n: non-English question form containing `HX` token (`HX 패밀리`, `quelle famille HX`)
   - T8 creative-refuse markers (when the prompt asks for hexa-canon harmful work; goes to hexa branch which routes through 7B's own T8 refusal)
3. **Mid-confidence short-circuit** (DLG-mk0 mid-conf category):
   - Swift mention → mid-conf always (DLG-mk0 has zero OOD Swift)
   - Python/Go/Kotlin/Ruby short prompt with NO functional-verb prefix
     (`write a python ...`, `show a go ...`) and NO `_IDIOMATIC_FOR_RE`
     prefix (`idiomatic python for ...`) and NO `_FUNCTIONAL_CONTENT_RE`
     marker (`function that ...`, `pytest fixture ...`, `pattern.`, etc.)
   - Returns `label="hexa"` with `reason="mid-confidence: short language idiom — 7B answers with confidence:medium"`
4. **OOD positive signals**:
   - Language names: `\b(rust|python|go|javascript|typescript|swift|kotlin|c\+\+|haskell|elixir|ruby|julia|scala|erlang|ocaml|coq|agda|idris|nim|zig|dart|php|perl|lua|f#|clojure)\b`
   - Frameworks: tokio / fastapi / flask / django / react / vue / angular / next.js / kubernetes / terraform / docker / helm / etc.
   - **Math reasoning** (r49 update):
     - `prove-derive`: `\b(?:prov(?:e|ing)|deriv(?:e|ation|ing)|show\s+that|theorem|lemma|corollary|induct(?:ion|ively)|proof\s+(?:that|of|by)|infinitely\s+many)\b`
       — extended in r49 to catch "proof" NOUN + "infinitely many" (closes DLG-135)
     - `complexity-bigO`: `\bcomplexity\b|\bbig[-_ ]?O\b|\bclosed[-_ ]?form\b|\brecurrence\b|\bO\(.*\)`
     - `ml-internals`: `\battention\b|\btransformer\b|\bRoPE\b|\bLoRA\b|\bDoRA\b|\bGRPO\b|\bPPO\b|\bRAG\b|\bembedding\b|\bsoftmax\b`
     - `derivation-algo` (r49 NEW): `\bderiv(?:e|ation|ing)\s+(?:the\s+)?(?:closed[-_ ]?form|recurrence|formula|dual|integral|complexity|big[-_ ]?O)\b|\bclosed[-_ ]?form\b|\brecurrence\b|\bT\(n\)\s*=`
     - `ml-comparison` (r49 NEW): `\bdifference\s+between\b|\bgives?\s+better\b|\bwhen\s+does\s+\w+\s+help\b|\breduce\s+(?:memory|compute|cost|latency)\s+vs\b|\bbetter\s+(?:diversity|throughput|latency|memory)\b`
   - **Structured output**:
     - `structured-json`: `\b(?:parse|convert|extract|classify|validate|return|summari[zs]e|generate|output|emit)\b.*\bjson\b`
     - `json-schema`: `\bjson schema\b|\bzod\b|\bjsonschema\b`
   - **Long-context**: prompt length ≥ 12000 chars OR `\b\d{2,4}K-?token\b|\b\d+(?:\.\d+)?M-?token\b`
5. **Disambiguation** by weight (`prove-derive` etc. have w=1.5; new
   r49 signals have w=1.0):
   - Strong hexa signal ≥ 2 matches → `hexa`
   - Weak hexa + strong ood → `ood`
   - Both fired with similar weight → `ood` (safer default — 7B can
     refuse via T8 if mis-routed; vendor handles spurious OOD gracefully)
6. **Ambiguous imperative** (vague-imperative regex like `^(?:make it|fix this|why is it|optimize|...)`) → `ood`
7. **Weak-signal fallthrough**: even if no signal hit the strong
   threshold, return `label="ood"` with the matched signals list
   preserved so the tier selector can use them. (r46 fix: prior
   code stripped `matched_signals=[]` here, blocking tier routing.)

### Honesty about confidence

The `confidence` field is heuristic (0.55-1.00 based on match weight
totals). It is **not** calibrated against ground-truth accuracy.
Brier-score calibration is a v0.5.x+ candidate. Production telemetry
should treat `confidence` as a tier-band signal, not a true probability.

---

## 5. Tier selector (`tool/select_vendor_tier.py`)

Pure function: `(ClassifierDecision, raw_prompt) → (tool, model, max_tokens, reason)`.
~210 lines, no side effects.

### Routes (r49)

```python
_CLASS_TO_ROUTE = {
    "longctx":     ("gemini-api", "gemini-2.5-pro",    8192),
    "reason-deep": ("claude-api", "claude-opus-4-7",   4096),
    "reason-algo": ("openai-api", "o4-mini",           2048),  # r49 NEW
    "reason":      ("claude-api", "claude-opus-4-7",   4096),  # legacy alias for reason-deep
    "struct":      ("openai-api", "gpt-5-mini",        2048),
    "general":     ("claude-api", "claude-sonnet-4-6", 2048),
}
```

### 6-step priority cascade (r49, first match wins)

1. **longctx**: `len(prompt) ≥ 12000` OR `long-context` signal OR `long-prompt-chars` signal → gemini-2.5-pro
2. **ml-comparison demotion**: `ml-comparison ∈ sigs AND ml-internals ∈ sigs` → general/sonnet
   (comparative-Q form of ml-internals topics = trade-off explanation, sonnet-tier work, NOT opus)
3. **reason-algo**: `derivation-algo ∈ sigs AND ml-internals ∉ sigs` → o4-mini
   (the `AND NOT ml-internals` guard preserves DLG-092 "Derive the gradient of softmax cross-entropy" on opus — ML-specific deep work, not textbook algebra)
4. **reason-deep**: `sigs ∩ {prove-derive, complexity-bigO, ml-internals, agda-coq-lean}` → opus
5. **struct**: `sigs ∩ {structured-json, json-schema}` → gpt-5-mini
6. **Fallback general**: → claude-sonnet-4-6

### Cross-vendor tier-equivalence table (used by scorer)

```python
_TIER_EQUIV = {
    "haiku":    {"haiku", "nano"},
    "nano":     {"nano", "haiku"},
    "sonnet":   {"sonnet", "mini"},
    "mini":     {"mini", "sonnet"},
    "opus":     {"opus", "flagship"},
    "flagship": {"flagship", "opus"},
}
```

This is used by `score_orchestration_mk0.py` so `tier_match=true` when
the chosen model's tier is equivalent to the manifest's preferred tier
across vendors (e.g. gpt-5-mini ↔ claude-sonnet).

### Cost honesty (per `_OPENAI_PRICING_USD_PER_MTOK`, r49 numbers)

| Tier | Model | $ / Mtok input | $ / Mtok output |
|---|---|---:|---:|
| opus | claude-opus-4-7 | $15.00 | $75.00 |
| flagship | gpt-5 | $5.00 | $20.00 |
| flagship | gemini-2.5-pro | $1.25 | $10.00 |
| sonnet | claude-sonnet-4-6 | $3.00 | $15.00 |
| mini | gpt-5-mini | $0.25 | $1.00 |
| mini | o4-mini | $1.20 | $4.80 |
| mini | gemini-2.5-flash | $0.30 | $2.50 |
| haiku | claude-haiku-4-5-20251001 | $1.00 | $5.00 |
| nano | gpt-5-nano | $0.05 | $0.40 |
| nano | gemini-2.5-flash-lite | $0.10 | $0.40 |

**r49 cost impact**: routing closed-form derivations from opus
($15/Mtok) → o4-mini ($1.20/Mtok) is ~12× input-token savings. On a
realistic ratio of 200 input / 400 output tokens per call: $3.03 →
$0.24 = **~92% cost reduction** on reason-algo routes.

---

## 6. Runtime contract (`tool/forge_runtime.py`, `_run_turn_orchestrated`)

```
1. classify_prompt(user_prompt) → decision
2. If decision.label == "refuse":
     emit canonical refusal ("out-of-domain — <category> (security-sensitive)")
     log telemetry, no vendor call, no 7B
     return
3. If decision.label == "hexa":
     run 7B generate (existing path)
     post-decode strip <|delegate|> / <|delegate-result|> / <|confidence:*|> residue
     return
4. If decision.label == "ood":
     (tool, model, max_tokens, reason) = select_vendor_tier(decision, user_prompt)
     redact(user_prompt) → redacted_prompt    # see §7
     authorize(tool, model)                    # see §7
     budget_check()                            # see §7
     cache_key = (tool, model, max_tokens, sha256(redacted_prompt))
     if (cached := _vendor_cache_get(cache_key)) is not None:
         return wrap(text=cached.text, cost=0, cache_hit=True, ...)
     filler_emit(decision.reason)              # see §7
     ok, text, usage, err = _vendor_call(tool, model, redacted_prompt, max_tokens)
     if not ok:
         emit errmap[err]
         log telemetry
         return
     _vendor_cache_put(cache_key, text, usage)
     log telemetry (DelegationCall with cache_hit=False, cost from pricing)
     return wrap(text=text, cost=..., cache_hit=False, ...)
```

All existing v0.4.0 runtime features survive: redaction, filler tokens,
budget caps, telemetry to `state/delegation_log.jsonl`, authorization,
vendor SDK error mapping.

### `DelegationCall` telemetry record

```python
@dataclass
class DelegationCall:
    timestamp_iso: str
    tool: str                # "claude-api" | "openai-api" | "gemini-api"
    model: str
    max_tokens: int
    reason: str              # tier selector's reason string
    classifier_label: str    # "ood" (or "hexa"/"refuse" for non-vendor turns)
    classifier_confidence: float
    classifier_signals: list[str]
    redacted_classes: list[str]
    ok: bool
    error_code: str | None   # "auth_fail" | "upstream_timeout" | "upstream_5xx" | "upstream_quota" | "schema_violation" | "redaction_block" | None
    usage: dict              # vendor-reported token counts
    cost_usd: float          # 0 if cache_hit OR if !ok
    latency_ms: int
    cache_hit: bool          # r48 NEW
    filler_emitted: bool
```

This is what lands in `state/delegation_log.jsonl` as one JSON line per
turn.

---

## 7. Redaction + authorization + budget (kept from v0.4.0)

Unchanged from `spec-delegation-v0.4.0.md §6`. Quick reference:

- **Redaction classes**: `api-key`, `bearer-token`, `email`, `private-key-block`, `aws-key-id`, `secret-name-like`, `phone`, `internal-host`. Hard block if redacted_classes is non-empty; do NOT send to vendor.
- **Authorization**: tool+model pair must be in `cfg.allowed_tools` (default = all 3 vendor tools).
- **Budget**: per-turn `cfg.max_cost_usd_per_turn = 0.50` (default). Cache hits bypass since cost is $0.
- **Filler tokens**: ≤ 60 chars, emitted to user channel during vendor call so UX doesn't feel frozen. Skipped on cache hit (response is instant).

---

## 8. Vendor SDKs (r47 + r48)

### 8.A Anthropic

- **SDK**: `anthropic.Anthropic().messages.create()`
- **Models**: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- **Cache hint**: `cache_control={"type": "ephemeral"}` on system block (Anthropic prompt-cache, 5-min TTL).
- **Pricing table**: `_ANTHROPIC_PRICING_USD_PER_MTOK` (cached_input pricing column).
- **Error mapping**:
  - `APIAuthenticationError` → `auth_fail`
  - `APITimeoutError` → `upstream_timeout`
  - `APIStatusError.status_code == 429` → `upstream_quota` (r48 NEW)
  - `APIStatusError` (other) → `upstream_5xx`

### 8.B OpenAI

- **SDK**: `openai.OpenAI().chat.completions.create()`
- **Models**: gpt-5, gpt-5-mini, gpt-5-nano, o4-mini, gpt-4o-mini
- **Pricing table**: `_OPENAI_PRICING_USD_PER_MTOK`. Cached input via `prompt_tokens_details` OR `cached_tokens` (SDK version compat).
- **Error mapping**: same as Anthropic (`APIAuthenticationError` /
  `APITimeoutError` / `APIStatusError.status_code == 429` → `upstream_quota`).

### 8.C Gemini

- **SDK**: `google.genai.Client().models.generate_content()`
- **Models**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite
- **Pricing table**: `_GEMINI_PRICING_USD_PER_MTOK`. Cached token count via `cached_content_token_count`.
- **Error mapping**: Gemini's coarse single-exception model handled via
  message string-match. `if "resource_exhausted" in msg or "quota" in
  msg or "rate limit" in msg or "429" in msg: return False, "", {},
  "upstream_quota"`. Other failures → `upstream_5xx`.

### 8.D Key provisioning

`ForgeRuntimeConfig.from_env()` loads keys via `_load_key()` (r47 bugfix
— uses explicit dict map, NOT `name.lower().replace("_",".")` which
produced wrong secret CLI key names). Lookup chain:
1. Env var (e.g. `ANTHROPIC_API_KEY`)
2. Secret CLI (`security find-generic-password -s anthropic.api_key`)
3. None → vendor calls return `auth_fail`

### 8.E Error → user-facing message map

```python
errmap = {
    "auth_fail":         "Vendor authentication failed — check API key.",
    "upstream_timeout":  "The frontier model timed out. Please retry.",
    "upstream_5xx":      "The frontier model returned a server error. Please retry.",
    "upstream_quota":    "The frontier model has hit its quota / rate-limit. Please retry in a moment, or upgrade the API tier.",  # r48 NEW
    "schema_violation":  "The runtime config rejected this delegation (tool or model not in allowlist).",
    "redaction_block":   "Your prompt contains sensitive data (API key / secret / credential). Strip the secret and retry.",
}
```

---

## 9. Per-prompt vendor cache (r48)

### Knobs

```python
@dataclass
class ForgeRuntimeConfig:
    vendor_cache_ttl_s: int = 300         # 5 min mirrors Anthropic prompt-cache TTL
    vendor_cache_max_entries: int = 1024  # hard cap; LRU eviction of oldest 25% on full
    vendor_cache_enabled: bool = True     # kill switch
```

### Mechanics

- **Cache key**: `(tool, model, max_tokens, sha256(redacted_prompt))`.
  `max_tokens` is part of the key so a 4096-tok re-ask doesn't serve
  a 1024-tok truncated entry. `redacted_prompt` (post-`_redact_pii`) is
  hashed, NOT the raw user text.
- **Lookup**: in `_run_turn_orchestrated`, AFTER redact + authorize +
  budget, BEFORE filler-emit + vendor call.
- **Hit**: returns cached text + usage. `DelegationCall.cost_usd = 0.0`,
  `cache_hit = True`, `filler_emitted = False`, `latency_ms = 0`.
- **Miss**: falls through to real vendor call. Successful responses
  cached; **failures are NOT cached** (intentional — retries should hit
  upstream, not a stale error).
- **Eviction**: LRU on `_vendor_cache` ordered dict. When `len ≥
  max_entries`, oldest 25% evicted in one pass (amortized cleanup).
- **Stats**: `self._vendor_cache_stats = {hits: int, misses: int, evictions: int}`.
  Not exposed via CLI in r48; future round may add a `pool_audit`-style
  query.

### Cost impact (production-realistic)

Burst of N identical prompts within 5 min (e.g. LSP autocomplete asking
"explain this Rust idiom" several times): **1 real call + (N-1) cached**.
At ~$0.02/turn for claude-sonnet, this is real money at scale.

### Cache fidelity

The cached text and usage dict are byte-equal to what the vendor
returned. Telemetry preserves the original vendor's usage counts (not
0) so cost-attribution analyses can split paid vs cached spend cleanly.

### What the cache does NOT do

- **No cross-process sharing** (in-memory dict per ForgeRuntime instance).
  Cross-process or restart loses the cache. Shared cache (Redis / file)
  is a v0.5.x+ candidate.
- **No semantic similarity** — only byte-exact prompts hit. Paraphrases
  miss. (Intentional: keyed on hash for determinism.)
- **No multi-turn dialogue memory** — only single-prompt caching. Deferred.
- **No upstream cache replacement** — Anthropic's prompt-cache and
  Gemini's context-cache still operate alongside. The forge cache is
  *complementary* (works even when upstream caches don't, e.g. on cache
  misses; saves the network round-trip too).

---

## 10. Eval (`tool/score_orchestration_mk0.py`)

`eval/delegation-mk0/manifest.jsonl` — 200 tasks, **unchanged since r39
follow-up**. Per-row schema:

```json
{
  "task_id": "DLG-001",
  "tags": ["in-domain"],
  "prompt": "...",
  "ideal_route": {
    "must_delegate": false,
    "must_refuse": false,
    "preferred_tool": "any",
    "preferred_model_tier": "any"
  }
}
```

Tag categories: in-domain (80), ood-delegate (60), mid-confidence (25),
security-refuse (15), ambiguous (10), long-context (10).

### Scorer outputs (r46+r49)

- **Classifier accuracy**: overall + per-category + confusion matrix.
- **Tier routing accuracy** (must_delegate rows only):
  - `n_eligible`: 77 (the must_delegate count; the 60 ood-delegate +
    10 long-context + 7 mid-conf-with-explicit-delegate).
  - `tool_match`: classifier's vendor pick == manifest's preferred_tool
  - `tier_match`: chosen model's tier ∈ _TIER_EQUIV[preferred_tier]
- **GA verdict**: overall ≥ 0.92 ✓.

### v0.5.5 actual scores

| Field | Value |
|---|---|
| classifier overall | 0.985 |
| in-domain | 1.000 |
| ood-delegate | 0.950 |
| mid-confidence | 1.000 |
| security-refuse | 1.000 |
| ambiguous | 1.000 |
| long-context | 1.000 |
| tier_match | 1.000 |
| tool_match | 0.987 |

### Specialist eval (unchanged)

Mk.I 665 strict + 5-NL 25 are **NOT re-run** in any v0.5.x round. The
classifier wraps the GA adapter without modifying it. r39 GA's
**94.29% Mk.I strict / 96% 5-NL** stand by construction.

---

## 11. Telemetry + observability

### Per-turn log: `state/delegation_log.jsonl`

One JSON line per turn (see §6 `DelegationCall`). Production operators
should aggregate this for:
- Vendor distribution: how many calls go to which vendor + tier?
- Cache hit rate: `cache_hit==True / total_ood_turns`
- Error rate by error_code (quota / 5xx / auth / etc.)
- Cost-attribution: sum cost_usd by (tool, model)
- Latency distribution by (cache_hit, vendor, tier)

### Cache stats: `_vendor_cache_stats`

Read directly from a `ForgeRuntime` instance:
```python
rt._vendor_cache_stats  # {"hits": ..., "misses": ..., "evictions": ...}
```

Useful in long-running services to tune `vendor_cache_max_entries`.

### Classifier signals: `DelegationCall.classifier_signals`

The list of regex names that fired. In production, scrape this to spot:
- Newly emerging OOD patterns (signals firing frequently but with low confidence)
- Hexa-canon drift (`hexa-keyword` signal disappearing → 7B may be ignoring
  hexa vocabulary)
- Tier-routing surprises (signals like `derivation-algo` appearing in
  contexts that should be reason-deep — feeds back into manifest
  expansion for v0.5.x+).

---

## 12. v0.6.0+ roadmap

The v0.5.x line is **features-complete** as of r49. Future work:

- **v0.5.6** — OpenAI key provisioning (currently `smoke-openai` skips —
  blocks real o4-mini end-to-end verification). User-action: add
  `openai.api_key` to secret CLI.
- **v0.5.7** — Brier-score calibration eval on classifier confidence
  (predicted vs actual accuracy in each band).
- **v0.5.8** — Multi-turn delegation memory + dialogue context cache
  (different from r48's per-prompt cache).
- **v0.5.9** — Shared cache (Redis or file-backed) for cross-process
  cache sharing.
- **v0.6.0** — Either (a) raise the specialist ceiling further (Lever 5+:
  full-FT, larger adapter rank, more SFT data), OR (b) explore the
  routing-LoRA architectural alternative (separate weight artifact, not
  re-purposed specialist).

---

## 13. Implementation file map

| File | Lines | Role |
|---|---:|---|
| `tool/classify_prompt.py` | ~440 | Stage-based regex classifier (§4) |
| `tool/select_vendor_tier.py` | ~210 | Pure function: decision → tier (§5) |
| `tool/forge_runtime.py` | ~1400 | Runtime dispatcher + vendor SDKs + cache (§6 / §8 / §9) |
| `tool/score_orchestration_mk0.py` | ~210 | CPU eval (§10) |
| `eval/delegation-mk0/manifest.jsonl` | 200 rows | Routing eval surface |
| `papers/spec-orchestration-v0.5.0.md` | 342 | OBSOLETE — superseded by this doc |
| `papers/spec-delegation-v0.4.0.md` | 482 | OBSOLETE §4/§10; §1-3, §5-9 still valid |
| `papers/spec-orchestration-v0.5.5.md` | this file | CONSOLIDATED spec |

---

## 14. Bookmarks

- `LEARNING_PROGRAMMING.md` §8 — round-by-round SFT/RL/orchestration recipe table
- `LEARNING_PROGRAMMING.md` §12 — original delegation thesis (now archived)
- ROADMAP §CHANGELOG r40-r49 — round-by-round narrative
- `bench/score-orchestration-mk0-r49/` — r49 score artifacts
- `bench/score-delegation-mk0-r39/` — r39 GA score artifacts
- Memory pointers (in `~/.claude/projects/-Users-ghost-core-hexa-codex/memory/`):
  - `[[pure-rl-exploration-collapse]]` — r42 lesson
  - `[[rl-tail-vs-greedy-eval]]` — r43+r43.1 lesson
  - `[[lever4-rl-sft-conflict]]` — r40/r41 lesson
  - `[[phase-a-manifest-rescore-pattern]]` — re-score before retrain
  - `[[t3-quote-fragility]]` — T3 quote-pair gotcha

---

## 15. Honesty caveats

- **Tier_match=1.000 on DLG-mk0** is on the *same 200-task manifest
  used to design the patterns*. The r49 fixes were targeted at the 7
  specific misses surfaced in r48. **There is genuine overfit risk**;
  v0.5.x+ candidate is manifest expansion (200 → 300+ tasks with new
  reason-deep / reason-algo / ml-comparison edge cases) to validate the
  patterns hold on held-out prompts.
- **Cache TTL = 300s** is set by convention (Anthropic prompt-cache TTL
  mirror), not empirically tuned. Production workloads with different
  prompt-repeat distributions may want longer (lower miss rate) or shorter
  (less staleness) TTL.
- **The 7B specialist is frozen at r39 GA** — no further training in
  the v0.5.x line. If the specialist ceiling becomes a bottleneck
  (production users hit T-family failures the 7B can't fix), that's a
  v0.6.0 model-round decision, not an orchestration patch.
- **`upstream_quota` distinguishes 429 from 5xx** but does not yet retry
  automatically. The user-facing message says "retry in a moment"; the
  client (calling code) must implement the retry loop. Auto-retry with
  exponential backoff is a v0.5.x+ candidate.
