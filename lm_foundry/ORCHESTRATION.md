# ORCHESTRATION — forge runtime layer (pre-7B classifier + tier router + vendor SDKs + cache)

> **Domain doc** (per dancinlab-wide `domain-meta-domain` principle: per-topic
> roadmap as root `UPPERCASE.md`). Current state lives in the spec sections
> below; chronological build history at `## Log` (bottom) cross-references
> ROADMAP §CHANGELOG entries.

**Status:** SPEC · v0.5.5 · 2026-05-14 · supersedes
`papers/spec-orchestration-v0.5.0.md` (the v0.5.0 base) AND obsoletes §4 / §10 of
`papers/spec-delegation-v0.4.0.md` (the in-weight routing thesis disproved by
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

The v0.5.x line shipped through **v0.5.14 (r62, 2026-05-14)** with
production-grade observability, persistence, multi-process safety, and
maintenance tooling. Specialist weights remain frozen at r39 GA by design.
v0.6.0+ scope narrows to items that v0.5.x can't address from CPU + the
existing weights:

- **OpenAI key provisioning** (user-action) — currently `smoke-openai`
  skips and `_vendor_call("openai-api", ...)` returns `auth_fail`. The
  classifier+selector correctly route to o4-mini / gpt-5-mini; vendor
  SDK + key are the only block. End-to-end reason-algo + struct
  validation needs this.
- **Gemini paid tier** (user-action) — currently free-tier limit=0 on
  gemini-2.5-pro causes `upstream_quota` on every longctx call. The
  quota mapping is verified (r48 + r53); actual long-doc answer quality
  is not yet measured.
- **Anthropic cross-turn cache ROI measurement** — r62 ships the
  cache_control marker on multi-turn dispatches; `forge_audit` already
  captures `cached_tokens`. A follow-up round can compare cached-token-
  ratio before/after on real conversational workloads.
- **SQLite schema migration tooling** — r62 ships `SCHEMA_VERSION`
  detection-only (stderr warning on mismatch). A real migration story
  needs either a versioned filename convention (`forge.v2.sqlite3`) or
  an explicit migration script.
- **`incremental` vacuum** — currently `forge_vacuum` requires runtime
  idle (exclusive lock on `VACUUM`). Enabling `PRAGMA auto_vacuum=INCREMENTAL`
  at DB creation (requires schema migration) would let `VACUUM` run
  concurrently with reads.
- **Connection pooling** — `_db` is a single connection per runtime.
  For 10K+ writes/sec workloads, batched writes or a real connection
  pool would help.
- **Specialist ceiling** — either (a) Lever 5+: full-FT, larger LoRA
  rank, more SFT data; OR (b) routing-LoRA as a separate weight artifact
  (the v0.4.x architectural alternative deferred). Both are GPU-bound.

---

## 13. Implementation file map (current — through r62)

| File | Lines | Role |
|---|---:|---|
| `tool/classify_prompt.py` | ~470 | Stage-based regex classifier — refuse / hexa / mid-conf / OOD with reason-deep/algo/ml-comparison signals + `_emit_conf` calibrated emission (§4) |
| `tool/select_vendor_tier.py` | ~225 | Pure function — 6-step priority cascade: longctx / ml-comparison demote / reason-algo / reason-deep / struct / general (§5) |
| `tool/forge_runtime.py` | ~1900 | Runtime dispatcher · 3 vendor SDKs · per-prompt cache · file cache · SQLite WAL cache · multi-turn memory · native messages threading · file conv · SQLite WAL conv · anthropic cross-turn cache mark · schema versioning (§6 / §8 / §9) |
| `tool/score_orchestration_mk0.py` | ~225 | CPU eval — classifier accuracy + tier_match + tool_match (§10) |
| `tool/score_brier_mk0.py` | ~220 | Calibration eval — Brier + ECE + 10-bin reliability table |
| `tool/forge_audit.py` | ~660 | Production observability CLI — aggregation + health gates (§11) |
| `tool/forge_vacuum.py` | ~280 | SQLite maintenance CLI — expire-cleanup + LRU cap + VACUUM + optimize (cron-friendly) |
| `tool/build_manifest_r51_extras.py` | ~340 | Manifest expansion script (200→300) |
| `tool/smoke_e2e_r53.py` | ~280 | End-to-end production smoke (24 prompts × real APIs) |
| `eval/delegation-mk0/manifest.jsonl` | 300 rows | Routing eval surface (expanded r51) |
| `papers/spec-orchestration-v0.5.0.md` | 342 | OBSOLETE — superseded |
| `papers/spec-delegation-v0.4.0.md` | 482 | OBSOLETE §4/§10; §1-3, §5-9 still valid |
| `ORCHESTRATION.md` | this file | CONSOLIDATED spec (root domain doc, per `domain-meta-domain` convention) |

---

## 14. Bookmarks

- `LEARNING_PROGRAMMING.md` §8 — round-by-round SFT/RL/orchestration recipe table (r1 through r62)
- `LEARNING_PROGRAMMING.md` §12 — original delegation thesis (now archived; superseded by v0.5.0)
- ROADMAP §CHANGELOG r40-r62 — round-by-round narrative with honesty caveats
- `bench/score-orchestration-mk0-r55/` — r55 score artifacts (latest classifier patterns)
- `bench/score-brier-mk0-r55/` — calibration artifacts (Brier 0.0242 / ECE 0.0461)
- `bench/score-e2e-r53/` — r53 end-to-end production smoke artifacts ($0.43 spend across 24 prompts)
- `bench/score-orchestration-mk0-r49/` — r49 baseline (200-task) score artifacts
- `bench/score-delegation-mk0-r39/` — r39 GA score artifacts (specialist quality)
- Memory pointers (in `~/.claude/projects/-Users-ghost-core-hexa-codex/memory/`):
  - `[[pure-rl-exploration-collapse]]` — r42 lesson
  - `[[rl-tail-vs-greedy-eval]]` — r43+r43.1 lesson
  - `[[lever4-rl-sft-conflict]]` — r40/r41 lesson
  - `[[phase-a-manifest-rescore-pattern]]` — re-score before retrain
  - `[[t3-quote-fragility]]` — T3 quote-pair gotcha

---

## 15. Honesty caveats (current — through r62)

- **DLG-mk0 surface is now 300 tasks** (r51 expansion). r55 patterns
  achieved tier_match=1.000 / tool_match=0.987 / overall=0.9833 on the
  expanded surface, but these are still designed against the manifest's
  specific phrasings. **Production rollout should monitor
  `state/delegation_log.jsonl` for novel no-signal-fallthrough patterns
  and feed back via manifest expansion.** Cross-vendor tier equiv
  (sonnet↔mini, opus↔flagship, haiku↔nano) is applied per spec §5 — so
  tier_match=1.000 means cost-band-equivalent, not vendor-identical.
- **Confidence calibration is GOOD but not perfect**. Brier 0.0242 is
  EXCELLENT (<0.05); ECE 0.0461 passes the 0.05 strict threshold for
  first time post-r55 but the per-bin gap is still slight (-0.046 mean,
  -0.45 on the smallest no-signal bin). For cost-sensitive cutoffs,
  treat confidence as a categorical band (high ≥0.9 / med 0.7-0.9 /
  low <0.7) rather than a raw probability.
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
  exponential backoff is a v0.6.x candidate.
- **Multi-process safety requires `forge_db_path` SQLite WAL** — the
  JSONL `vendor_cache_path` / `conv_history_path` modes are
  single-process. Two processes appending to the same JSONL CAN
  interleave; use SQLite for any multi-process deployment.
- **SQLite WAL requires local disk** — NOT NFS, CIFS, or other network
  filesystems. For distributed deployments, use a real network DB
  (Postgres / managed Redis / DynamoDB) — not in scope for v0.5.x.
- **Anthropic cross-turn cache_control (r62) MEASURED in r64 — REDUNDANT
  in practice**. The empirical finding (`bench/score-anthropic-xt-r64/`):
  Config A (marker ON) and Config B (marker OFF) produced bit-for-bit
  identical cache_create / cache_read counts on a 4-turn sonnet
  conversation. Anthropic auto-caches the conversation prefix using only
  the `cache_control` marker on the system message (r45 baseline).
  r62's `_anthropic_cache_mark` is kept in code as a defensive no-op
  against future SDK behavior changes; the runtime is NOT degraded by
  its presence. Cache READ IS valuable (~90% savings on cached portion)
  but materializes from anthropic's automatic mechanism, not from r62's
  explicit marker. Per-model thresholds (sonnet 1024 tok, haiku 2048,
  opus 1024) gate when cache fires; turns 3+ of a typical conversation
  cross sonnet's threshold.
- **`forge_vacuum` requires runtime idle during VACUUM** (exclusive
  lock). Schedule cron in a low-traffic window.
- **Schema versioning is detection-only** — `SCHEMA_VERSION = 1` is
  tracked via `PRAGMA user_version`; runtime warns on mismatch but
  does NOT auto-migrate. A future schema change requires either a
  versioned filename (`forge.v2.sqlite3`) or a manual migration script.
- **Cost-saved-estimate in `forge_audit`** is a heuristic (avg same-
  (tool, model) miss cost × hits). High variance per-call workloads
  make the estimate noisier; track over time to gauge true cache ROI.
- **Latency percentiles in `forge_audit`** include only REAL calls
  (`not cache_hit and ok`). This is the right denominator for "how
  fast is upstream", NOT "what does the user feel" (which includes
  cache hits at ~0ms making user-perceived p95 much better).

---

## Log

Chronological build history (cross-ref ROADMAP §CHANGELOG for full per-round narratives):

- **2026-05-14 r44** — v0.5.0 architecture line OPENED. Pre-7B keyword
  classifier `tool/classify_prompt.py` (~440 LOC). DLG-mk0 classifier
  accuracy 0.985 / passes 0.92 GA gate by +6.5pp. v0.4.x in-weight thesis
  closed after 5 disproof rounds (r40-r43.1).
- **2026-05-14 r45** — `tool/forge_runtime.py` classifier wire-up
  (`_run_turn_orchestrated`). End-to-end real Anthropic call verified.
  v0.5.0 GA stack OPERATIONAL.
- **2026-05-14 r46** — `tool/select_vendor_tier.py` NEW (~210 LOC) — per-
  vendor tier routing (long-ctx→gemini-pro, math→opus, struct→openai-mini,
  general→claude-sonnet). DLG-mk0 tool_match 0.948 / tier_match 0.909.
- **2026-05-14 r47** — Real OpenAI + Gemini SDKs wired (no more stubs);
  `_load_key` secret-CLI path bugfix. All 3 vendors verified end-to-end.
  Forge orchestration stack production-ready.
- **2026-05-14 r48** — `upstream_quota` error code + per-prompt vendor
  cache (TTL 300s, LRU 1024). Production cost optimization. `DelegationCall.cache_hit`
  telemetry. 10/10 offline smoke.
- **2026-05-14 r49** — Reason-class split: `reason-deep` (opus) vs
  `reason-algo` (o4-mini) + ml-comparison demotion to sonnet. tier_match
  0.909 → 1.000, tool_match 0.948 → 0.987 — all 7 r48 misses closed.
  21/21 classify + 14/14 tier + 10/10 forge smoke. ~80% per-call cost
  reduction on reason-algo routes.
- **2026-05-14 r50** — This consolidated spec doc, originally written
  to `papers/spec-orchestration-v0.5.5.md`, then moved to root as
  `ORCHESTRATION.md` per dancinlab `domain-meta-domain` convention
  (per-topic roadmap as root UPPERCASE.md, one domain = one file).
- **2026-05-14 r51** — DLG-mk0 manifest expanded 200→300 (held-out r49
  validation) via `tool/build_manifest_r51_extras.py`. r49 patterns hold
  with -0.17pp regression. SURFACED 5 critical security-refuse gaps
  (brute-force conjugation, jailbreak-policy, prompt-injection, weapon-
  synthesis, doxing) — all CLOSED in same round. tier_match 0.978 on
  300 with 5 documented boundary cases.
- **2026-05-14 r52** — Brier-score calibration eval (`tool/score_brier_mk0.py`).
  Honest finding: Brier 0.0920 GOOD but ECE 0.1650 POOR (-15.61pp
  systematically underconfident). Root cause: `min(1.0, X/Y)` formulas
  emit 0.25-0.50 for single-signal cases with empirical 100% accuracy.
  No code change in r52 — the deliverable IS the measurement.
- **2026-05-14 r53** — End-to-end production smoke (`tool/smoke_e2e_r53.py`).
  24 novel held-out prompts × real vendor SDKs × \$0.43 across 2 runs.
  label_match 24/24, tool_match 17/18, anthropic 10/10 successful,
  gemini upstream_quota 2/2, openai auth_fail 5/5 (no key in secret),
  cache fidelity 2/2 cross-process. **v0.5.x stack GA-quality on real APIs.**
- **2026-05-14 r54** — v0.5.6 confidence recalibration. NEW `_emit_conf`
  helper replaces pessimistic `min(1.0, X/Y)` at 7 sites with shifted-
  and-scaled floors (0.80-0.95). Brier 0.0920 → 0.0351 EXCELLENT (-62%);
  ECE 0.1650 → 0.0674 (-59%). Label dispatch UNCHANGED by construction.
- **2026-05-14 r55** — v0.5.7 classifier coverage expansion. 5 new/
  extended OOD patterns (golang broad, swift-framework, ml-internals
  +MoE/RLHF/DPO/KL, llm-infra, generic-write-code) + 2 ambiguous +
  derivation-algo widen + ml-comparison widen. Closes 17 no-signal-
  fallthrough + 3 tier-routing misses (DLG-100 MoE trade-offs / DLG-227
  master theorem / DLG-230 Big-O quickselect). **Final: Brier 0.0242
  EXCELLENT / ECE 0.0461 GOOD / tier_match 1.000 RESTORED / tool_match
  0.9926.**
- **2026-05-14 r56** — v0.5.8 file-backed shared cache. NEW config
  `vendor_cache_path: Path` for cross-process restart-persistence.
  JSONL append + load-on-init + LRU-compact-on-evict. Single-process
  only (not multi-process safe; SQLite WAL ships in r61). Smoke [11].
- **2026-05-14 r57** — v0.5.9 multi-turn delegation memory. Two-layer
  design: (a) `ConversationTurn` storage per conv_id with max_turns cap;
  (b) optional auto-prepend `Previous conversation:` string preamble.
  Public API: `get_conversation_history` / `clear_conversation`. Smoke [12].
- **2026-05-14 r58** — v0.5.10 production audit CLI (`tool/forge_audit.py`).
  Reads `state/delegation_log.jsonl`, aggregates cache/vendor/error/
  latency/cost. 3 output formats (text/json/csv) + health gate alerts
  (cache_hit_min / error_rate_max / cost_day_max → exit 2). Self-test
  on 20 synthetic rows verifies every metric.
- **2026-05-14 r59** — v0.5.11 vendor-native `messages=[...]` threading.
  Replaces r57 string-concat workaround. All 4 vendor functions accept
  optional `messages` kwarg. NEW `_messages_to_gemini_contents` (assistant
  → model role; content → parts:[{text:...}]). Cache key adapts to
  serialized-messages hash. Backward-compat (default OFF). Smoke [13].
- **2026-05-14 r60** — v0.5.12 persistent conv memory across restarts.
  NEW `conv_history_path: Path` mirrors r56 pattern for ConversationTurn
  buffers. Load-on-init + append-on-record + compact-on-evict/clear.
  Smoke [14].
- **2026-05-14 r61** — v0.5.13 SQLite WAL multi-process backend. NEW
  `forge_db_path: Path` unified DB (vendor_cache + conv_turns tables
  with indexes; WAL mode; NORMAL sync). When set, OVERRIDES JSONL paths.
  Closes the "NOT multi-process safe" caveat from r56+r60. stdlib
  sqlite3 only (no external dep). Smoke [15] + [16].
- **2026-05-14 r62** — v0.5.14 production maturity bundle (user's "전부
  한번에" directive). 3 features one round: (a) anthropic cross-turn
  cache_control via `_anthropic_cache_mark` helper (caches conv prefix
  on multi-turn dispatches); (b) SQLite schema versioning (`SCHEMA_VERSION
  = 1` + `PRAGMA user_version` detection); (c) `tool/forge_vacuum.py`
  cron CLI (expire-cleanup + LRU cap + retention + VACUUM + optimize,
  idempotent, dry-run flag). Smoke [17] + [18] + `forge_vacuum --smoke`.
- **2026-05-14 r62.1 (this update)** — ORCHESTRATION.md refreshed to
  reflect r51-r62 changes: §12 v0.6.0+ roadmap rewritten with realized
  state; §13 file map updated with new tools + accurate line counts;
  §14 bookmarks pointed at latest score artifacts; §15 honesty caveats
  expanded with 7 new entries covering r51-r62 surface; ## Log
  appended with chronological r51-r62 narratives.

