# Self-aware delegation protocol — v0.4.0 architecture line

**Status:** SPEC · draft 1 · 2026-05-13 · prerequisite Lever 4 (CLOSED, r38).
**v0.4.0 + v0.4.1 SFT implementations EXECUTED in rounds 40+41 — both
labeled experiments, NOT GA.** ROADMAP r40 (25% delegation, LR 5e-5, 1 ep):
Mk.I 82.71% / 5-NL 60% / DLG-mk0 0.7652 — all gates missed; T4 100→77%
(Lever-4 RL erased by shared-LoRA SFT). ROADMAP r41 (9% delegation, LR 2e-5,
2 ep, 4 new blocks): Mk.I 83.01% / 5-NL 52% / DLG-mk0 0.7760 — basically
flat vs r40. **Five hard lessons confirm: SFT-only delegation training
cannot escape the specialist↔routing tradeoff in 7B+LoRA.** **v0.4.2 plan
is routing-RL** (GRPO with binary route-correctness reward on a held-out
200-prompt training set, KL-anchored to r39 v3-t3patch, ~\$2-3/3h). The
token grammar (§2), runtime contract (§3), redaction (§6), streaming UX
(§7), confidence-band calibration (§8), routing-eval protocol (§9), and
SFT block schema (§10) below are all **correct and reusable** — the
bottleneck was training mechanism (SFT-on-shared-LoRA) not spec design.

**Owner:** code-LLM line. Implementer: `tool/forge_runtime.py`, `tool/build_sft_dataset_v18.py`.

**One-line thesis.** Teach the 7B to **recognise its competence boundary** and emit
a structured `<|delegate|>{…}<|/delegate|>` JSON token; a runtime parses it and
dispatches to Claude/OpenAI/Gemini/Wilson, injects the response back as
`<|delegate-result|>{…}<|/delegate-result|>`, and the 7B writes the user-facing
wrap-up. Routing-as-a-skill, learned via SFT — no MoE, no retrieval, no new
vocab tokens.

> Design rationale and the full why-not alternatives are in
> `LEARNING_PROGRAMMING.md` §12 (delegation) + §13 (OpenAI / Gemini surfaces) +
> §14 (Wilson). This spec is the **formal contract** — token grammar, runtime
> obligations, failure modes, eval protocol, SFT block shape.

---

## 1. Goal + non-goals

**Goal.** Ship a v0.4.0 adapter whose ON-EVAL behaviour:
1. Hexa-canon prompts → answer directly (preserve r38 v3 score: Mk.I ≥ 88%,
   T4 ≥ 95%, 5-NL ≥ 95% — i.e., within ±3pp of v3 on every gate).
2. Out-of-domain prompts (Rust async, ML internals, math derivations) →
   emit a well-formed `<|delegate|>` token whose `tool`/`model`/`prompt`/`reason`
   fields pass schema validation **≥ 95% of the time**.
3. Mid-confidence prompts (Swift snippet, common Python recipe) →
   prepend `<|confidence:medium|>` band before answering.
4. Security-sensitive prompts (exfil, harmful, illegal) → refuse directly,
   **never delegate** (don't shift liability — see §6).
5. Receiving a `<|delegate-result|>{…}` in context → fold its content into a
   clean user-facing wrap-up (no raw JSON leakage).

**Non-goals (v0.4.0).**
- No tool primitives beyond `claude-api` / `openai-api` / `gemini-api`.
  `web-search`, `code-execution`, `wilson-rpc` are v0.5.0+.
- No multi-turn delegation memory ("I delegated this in turn 1, skip re-delegation
  in turn 3") — deferred.
- No automatic confidence-band calibration (the SFT teaches a *target* band; the
  Brier-score scaffolding lands in v0.5.0 — see §8.B).
- No fine-tuned response caching (per-prompt cache of delegated answers) — v0.5.0.
- No offline-graceful 1.5B fallback — judged not worth the complexity (§12.G).

---

## 2. Token grammar (the wire format)

The 7B emits **two delimiter pairs** (no new vocab tokens — they're stock Qwen
ASCII sequences with `<|...|>` shape that survive existing tokenisation):

```
delegation         ::= "<|delegate|>" json_object "<|/delegate|>"
delegate_result    ::= "<|delegate-result|>" json_object "<|/delegate-result|>"
confidence_band    ::= "<|confidence:" band "|>"
band               ::= "high" | "medium" | "low"
```

Both delimiter pairs are case-sensitive. Whitespace inside `json_object` is
allowed; the runtime parses with `json.loads`. The parser is **non-greedy** on
the closing tag — it matches the first `<|/delegate|>` after the opener (so a
delegation can't contain itself in `prompt` text — that's by design, see §6).

### 2.A `<|delegate|>` schema (model emits → runtime consumes)

```json
{
  "tool": "claude-api" | "openai-api" | "gemini-api",
  "model": "<vendor-specific id>",
  "prompt": "<verbatim user prompt + any hexa context the 7B wants to forward>",
  "max_tokens": <int, 64..8192>,
  "reason": "<one-line, ≤ 80 chars>"
}
```

Required fields: all five. Validation order: `tool` ∈ enum → `model` ∈ vendor
allowlist → `prompt` non-empty + ≤ 16384 chars → `max_tokens` in range →
`reason` non-empty + ≤ 80 chars. Any failure → see §5 failure modes.

**Vendor model allowlists** (v0.4.0 frozen; runtime rejects others):
- `claude-api`: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- `openai-api`: `gpt-5`, `gpt-5-mini`, `o4-mini`, `gpt-4o-mini`
- `gemini-api`: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`

Default choices the 7B is SFT'd toward (see `LEARNING_PROGRAMMING.md` §13.D):
- General out-of-domain → `claude-api / claude-sonnet-4-6`
- Hard reasoning / math derivation → `claude-api / claude-opus-4-7` or `openai-api / o4-mini`
- Long-context code analysis (> 200 K tokens) → `gemini-api / gemini-2.5-pro` (2M ctx)
- Cheap general knowledge / structured output → `openai-api / gpt-5-mini`

### 2.B `<|delegate-result|>` schema (runtime emits → model consumes)

```json
{
  "ok": true,
  "text": "<vendor response text, post-cleanup>",
  "usage": {"input_tokens": <int>, "output_tokens": <int>, "cached_tokens": <int>, "cost_usd": <float>}
}
```
on success, or

```json
{
  "ok": false,
  "error": "upstream_timeout" | "upstream_5xx" | "auth_fail" |
           "budget_exhausted" | "max_delegations" | "offline" |
           "schema_violation" | "vendor_refusal" | "redaction_block",
  "detail": "<short human-readable explanation>"
}
```

The model **must** handle both shapes (see §5 + the SFT block §7.D).

### 2.C `<|confidence:band|>` (optional prefix on direct answers)

When present, must be the **first non-whitespace token** of the assistant
turn, before any other content. Three values: `high` / `medium` / `low`.
`low` triggers an immediate fall-through to delegation (the SFT teaches the
model to NOT emit `<|confidence:low|>` at all — it emits `<|delegate|>`
instead). The runtime **strips** the confidence prefix from the user-facing
output; it surfaces in telemetry (and optionally as a UI badge — runtime UX
choice, not a protocol mandate).

---

## 3. Runtime contract (`tool/forge_runtime.py`)

The runtime owns the safety boundary. **The model never sees:** vendor API
keys, budget state, network state, conversation-level rate limits. Steps
per turn:

1. **Generate.** Call the 7B with the user's prompt + system prefix. The
   system prefix MUST include: "You answer hexa-canon questions directly.
   For out-of-domain or hard-reasoning prompts, emit
   `<|delegate|>{…}<|/delegate|>`. For mid-confidence answers, prefix
   `<|confidence:medium|>`. NEVER emit confidence:low — delegate instead.
   NEVER delegate harmful / illegal / exfil prompts — refuse them directly."
2. **Detect.** Scan the generation for `<|delegate|>…<|/delegate|>` (regex,
   non-greedy). If absent → pass the answer through (after stripping any
   `<|confidence:...|>` prefix into telemetry).
3. **Parse + validate.** `json.loads` the body; check the §2.A schema.
   Failure → §5 schema_violation handling.
4. **Redact** (NEW v0.4.0 requirement, §6). Scan `prompt` for redaction
   patterns; replace matches with `[REDACTED:<class>]`. If a high-confidence
   secret detector fires → §5 redaction_block.
5. **Authorize.** The runtime owns `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` /
   `GEMINI_API_KEY` (from `secret get` CLI). Vendor + auth fail → §5 auth_fail.
6. **Budget check.** Per-conversation cap (default $0.50) + per-day cap
   (default $20). Reject + §5 budget_exhausted if exceeded. Caps are runtime
   config, not in the protocol — but the model is SFT'd to handle the error
   gracefully.
7. **Call vendor.** With prompt caching enabled (Anthropic `cache_control` /
   OpenAI auto-cache ≥ 1024-token prefix / Gemini explicit context caching).
   Surface caching savings in `usage.cached_tokens` of the delegate-result.
8. **Stream → buffer.** For real-time UX, the runtime emits *filler tokens*
   to the user channel while the vendor stream is in-flight (see §7 streaming).
9. **Inject result.** Re-enter the model with the original conversation +
   the assistant message ending right before `<|delegate|>` + a synthetic
   user-role turn containing `<|delegate-result|>{…}<|/delegate-result|>`.
   The model then produces the user-facing wrap-up.
10. **Cap iterations.** Hard limit `max_delegations_per_turn = 3`. Hitting
    the cap → §5 max_delegations.
11. **Telemetry.** Append one row to `state/delegation_log.jsonl`:
    `{ts, conv_id, turn_id, tool, model, tokens_in, tokens_out, cached_tokens,
    cost_usd, reason, error?, redaction_classes?, latency_ms}`. Used for cost
    attribution + the §9 routing-eval scoring.

---

## 4. Sequence diagram (one delegated turn)

```
user ─prompt─▶  runtime ─▶ 7B
                                7B emits: "<|delegate|>{...}<|/delegate|>"
runtime ◀─emission─ 7B
runtime: detect → parse → REDACT → authorize → budget-check
runtime ─filler─▶ user        ("Looking into that for you…")
runtime ─claude API─▶ vendor
runtime ◀─stream─ vendor
runtime ─delegate-result─▶ 7B (resume from pre-delegate position)
                                7B emits wrap-up + (optionally) more text
runtime ◀─wrap-up─ 7B
runtime ─sanitised output─▶ user
runtime ─log row─▶ state/delegation_log.jsonl
```

The **filler** (step "filler" in the diagram) is the §7 streaming-UX
intervention: without it, the user sees ~2-5 seconds of dead air between the
7B's emission and the vendor's first stream chunk.

---

## 5. Failure modes

| code | source | runtime injects | 7B SFT'd response |
|---|---|---|---|
| `upstream_timeout` | vendor 504 / network hang > 30s | `{"ok":false,"error":"upstream_timeout"}` | "Delegation upstream is unreachable; best I can offer locally: [partial / unknown]." |
| `upstream_5xx` | vendor 5xx | same shape with `upstream_5xx` | "The frontier model is having issues; for hexa questions I can answer directly, but for this off-domain query you'll want to retry shortly." |
| `auth_fail` | runtime API key missing or 401 | `auth_fail` | "Delegation auth is not configured on this instance. I can only answer hexa-canon questions locally." |
| `budget_exhausted` | per-conv / per-day cap hit | `budget_exhausted` | "Delegation budget for this conversation is spent. Please rephrase as a hexa question or retry later." |
| `max_delegations` | 3rd `<|delegate|>` in one turn | `max_delegations` | "Delegation limit reached for this turn — final answer from what I have: […]". |
| `offline` | runtime detects no network | `offline` | "Running offline; hexa-canon answered directly. Non-hexa queries unavailable until network is up." |
| `schema_violation` | model emitted malformed JSON | runtime returns hard error to user (NOT to model — never-event); telemetry flags the bug for SFT iteration | n/a — this is a model bug; SFT data must have ≥ 99% valid JSON emit rate. |
| `vendor_refusal` | vendor returned a refusal | `vendor_refusal` with `text` field carrying the refusal | Echo the refusal honestly. Don't try to re-delegate. |
| `redaction_block` | high-confidence secret detector fired (§6) | `redaction_block` with redaction class | "I detected what looks like a secret in this prompt and won't forward it externally. If you intended to ask without the secret, please rephrase." |

`schema_violation` is the only error the 7B should never produce — every other
row above must appear in the SFT block (≥ 5 examples each).

---

## 6. Privacy + redaction (IDEA #1 — NEW v0.4.0 requirement)

Forwarding a user prompt to a third-party vendor is a data-egress event. The
runtime owns the redaction pass; the model does not.

**Default redaction classes (regex-based; runtime config):**

| class | pattern (illustrative) | replacement |
|---|---|---|
| API keys | `sk-[A-Za-z0-9]{32,}` / `hf_[A-Za-z0-9]{32,}` / `xoxb-…` / etc. | `[REDACTED:api-key]` |
| JWTs | `eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}` | `[REDACTED:jwt]` |
| Email-like | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | `[REDACTED:email]` |
| Phone-like | `\+?[0-9][0-9 .()-]{8,}` (after a label like "phone" / "tel") | `[REDACTED:phone]` |
| Private SSH | `-----BEGIN (OPENSSH|RSA|DSA|EC|PGP) PRIVATE KEY-----` | hard-block (return `redaction_block`) |
| Local paths with usernames | `/Users/<W>+/` or `/home/<W>+/` | `/Users/<USER>/` etc. |
| IP addresses | RFC 5321 — IPv4 + IPv6 | `[REDACTED:ip]` |

**Two-band action:**
- **Soft redact** (replace with `[REDACTED:class]`) — for email/phone/path/IP.
  Continue with delegation, prompt now sanitised.
- **Hard block** (return `redaction_block` to the model, no vendor call) — for
  API keys, JWTs, private keys. The user must remove the secret and retry.

**Telemetry.** Every redaction logged with class + count (not value). Same
log row as §3.11 — adds `redaction_classes: ["api-key", "email"]`.

**Limitations.** Regex misses semantic secrets (an unstructured password
sentence "my password is hunter2"). The v0.4.0 redactor is **shallow by design**;
v0.5.0+ may add an LLM-driven redactor for prompts > a threshold. Document
this limit in the runtime config + the user-facing system prefix.

**Cross-link.** [[reference-secret-cli]] — the in-repo secret store the
runtime reads keys from. Never log raw key values; redaction telemetry
records classes only.

---

## 7. Streaming UX during delegate (IDEA #2 — NEW v0.4.0 requirement)

A vendor call typically takes 2-5 seconds before the first stream chunk
arrives (longer for Opus / o3). Without intervention the user sees dead air.
The runtime emits **filler tokens** in the user channel during this window.

**Strategy.** Three layers:

1. **Pre-call filler** (always, immediate). When the runtime detects
   `<|delegate|>` and starts the vendor call, emit a one-line filler to the
   user channel chosen by `reason`:
   - "Looking up the larger model on this one — back in a moment…"  (general)
   - "Working through the math — give me a few seconds…"  (reason mentions math/derivation)
   - "Pulling in long-context analysis — this can take 5-10 s…"  (gemini-2.5-pro / > 500K ctx prompt)
   - "Asking the reasoning model — this takes longer than chat…"  (o4-mini / opus-4-7)
   
   The model is SFT'd to write reasons that map to these (`LEARNING_PROGRAMMING.md` §13.D).

2. **Stream the vendor response** as it arrives — pass-through tokens to the
   user channel. The model's wrap-up (step 9) runs **after** the vendor stream
   ends; the user sees vendor text in real time, then a wrap-up paragraph.

3. **Cancellation handling.** If the user disconnects mid-stream, the runtime
   cancels the vendor request (HTTP abort). Partial costs still log to
   telemetry (vendor charges for emitted tokens).

**Why not have the 7B emit fillers?** Two reasons. (a) Latency — the 7B
finishes its emission *before* the runtime knows to delegate; you'd need a
"pre-delegate filler" trained into the SFT, doubling generation time. (b)
Honesty — runtime-emitted fillers can be tagged as "non-model output" in
the UI (italics, dimmer color); model-emitted ones can't.

**Telemetry.** Log `filler_emitted: true/false` + `time_to_first_vendor_chunk_ms`.
Used in the §9 routing-eval to score "user-perceived latency", not just
total latency.

---

## 8. Confidence-band calibration (IDEA #3 — partial v0.4.0)

`<|confidence:high|medium|>` is the model's self-rated answer reliability. The
SFT block teaches *targeted* bands (high for hexa-canon, medium for Swift /
common-Python idioms). The **calibration validation** — does the band's
predicted accuracy match the actual accuracy? — needs eval scaffolding.

### 8.A v0.4.0 — band-emission discipline (SFT-level)

Every direct answer in the SFT block prefixes a band:
- ~250 in-domain pairs → `<|confidence:high|>`
- ~100 mid-confidence pairs (Swift / common Python / common JS idioms) →
  `<|confidence:medium|>`
- 0 low-confidence pairs in direct-answer form — `low` always converts to
  `<|delegate|>` in the SFT.

Eval shape: on the existing Mk.I 665 + a small held-out OOD set
(`eval/delegation-mk0/`), measure (a) band-emission rate (≥ 98% on direct
answers) and (b) band-distribution (high ≥ 80% on Mk.I, medium dominates
in OOD set with no delegate token).

### 8.B v0.5.0 — Brier-score calibration eval (deferred)

For the medium band specifically, the predicted "I'm not sure" rate should
track actual accuracy in that band. Tooling:
- `eval/calibration-mk0/` — held-out questions across in-domain, mid, OOD;
  each annotated with the human-graded correct answer.
- `tool/score_calibration.py` — Brier score = mean( (p_high - I[correct])²)
  where `p_high = 1 if band=high else 0.5 if medium else 0`.
- Target: Brier ≤ 0.15 on the held-out set (calibrated within ±15pp).

v0.4.0 documents the eval design; v0.5.0 builds + runs it. The v0.4.0 SFT
shapes the band rates **plausibly** but doesn't yet *prove* calibration.

---

## 9. Routing-eval protocol (IDEA #5 — NEW v0.4.0 deliverable)

A delegation that *answers right* but *routes wrong* (e.g., uses gpt-4o-mini
when the prompt deserved Opus) is a silent failure. We need an eval that scores
**routing decisions** independent of answer quality.

### 9.A `eval/delegation-mk0/manifest.jsonl` (200 tasks)

Each task:
```json
{
  "task_id": "DLG-NNN",
  "prompt": "<user prompt>",
  "ideal_route": {
    "must_delegate": true | false,
    "must_refuse": true | false,
    "min_band": "high" | "medium" | "low",
    "preferred_tool": "claude-api" | "openai-api" | "gemini-api" | "any" | null,
    "preferred_model_tier": "haiku" | "sonnet" | "opus" | "nano" | "mini" | "flagship" | "any",
    "rationale": "<one-line why>"
  },
  "tags": ["in-domain", "rust", "ml-internals", "math-reasoning", "long-context", "security-refuse", "ambiguous", ...]
}
```

Distribution target (matches v0.4.0 SFT block §10):
- 80 in-domain (must_delegate=false, min_band=high)
- 60 out-of-domain delegate (must_delegate=true; varied preferred_tool/tier)
- 25 mid-confidence (must_delegate=false, min_band=medium)
- 15 security-refuse (must_refuse=true)
- 10 ambiguous (must_delegate=true, prompt rephrased in `prompt` field)
- 10 long-context (must_delegate=true, preferred_tool=gemini-api)

### 9.B Scorer (`tool/score_delegation_mk0.py`)

Five sub-scores, each 0-1, weighted-mean to overall:
1. **Route correctness** (w=0.40): did the model delegate ↔ `must_delegate`?
   Refuse ↔ `must_refuse`?
2. **Band correctness** (w=0.20): emitted band ≥ `min_band` on direct answers?
3. **Tool match** (w=0.15): if `preferred_tool` set, did the model pick it?
   (`any` = full credit.)
4. **Model-tier match** (w=0.15): did the chosen model match the preferred tier?
5. **Schema validity** (w=0.10): did the `<|delegate|>` JSON parse cleanly?
   (Hard gate — failure here zeros the other 4 for that task.)

### 9.C Acceptance bar (v0.4.0)

- **Hard gate:** Route correctness ≥ 0.90, Schema validity ≥ 0.98.
- **Soft gate:** Overall ≥ 0.85.
- Mk.I 665 (held-in-domain) regression bar: ≥ 88% strict (within 3pp of
  v3 GA 90.98%).

---

## 10. SFT block shape (`tool/build_sft_dataset_v18.py`)

Target ~700-900 pairs (matching `LEARNING_PROGRAMMING.md` §12.F est.):

| block | count | shape | notes |
|---|---|---|---|
| `in-domain-high-confidence` | 200 | `<|confidence:high|>` + canon answer | Sample across T1-T8 + 5-NL; reuse v17 base prompts. |
| `out-of-domain-delegate` | 220 | `<|delegate|>{...}<|/delegate|>` | Spread vendors: 120 claude-api, 60 openai-api, 40 gemini-api. Mix tiers per §13.D heuristics. |
| `medium-confidence-direct` | 100 | `<|confidence:medium|>` + short caveat + answer | Swift idioms, common Python recipes, basic Go patterns. |
| `ambiguous-clarify-delegate` | 80 | `<|delegate|>` with `prompt` containing a clarifying re-formulation | Under-specified prompts; model rephrases inside the delegation. |
| `delegate-result-integration` | 80 | input includes a synthesised `<|delegate-result|>{...}`; output is the wrap-up | Teaches §3.9 — folding vendor responses into clean prose. |
| `failure-mode-handling` | 70 | input includes a synthesised `<|delegate-result|>{"ok":false,"error":...}`; output is the graceful fallback | 10 each of the 7 error codes in §5 (excluding schema_violation — that's a never-event). |
| `security-refuse-direct` | 50 | refusal (no delegate, no confidence band) | Exfil prompts, harmful content, illegal — the 7B refuses without external escalation. |
| `no-delegation-override` | 40 | system prefix includes "answer locally only"; out-of-domain prompts produce refusal instead of delegate | Teaches the runtime-suppression case. |

Total ~840 pairs. Built on top of the existing v11 base dataset (3140 rows
post-v17), so v18 total = ~3980 rows.

**Holdout discipline.** None of these 840 pairs share an exact prompt with
the held-out `eval/delegation-mk0/manifest.jsonl` (§9.A). The generators
randomise function names / code / dates / domain references so the eval
truly measures generalisation. Same holdout principle as the build_rl_t4
splits (§spec-lever4 §4 + §14 r38 §11).

---

## 11. Training recipe (v0.4.0 round target)

| param | value | rationale |
|---|---|---|
| base | `Qwen/Qwen2.5-Coder-7B` | unchanged from v0.3.0 / v0.4.0 line |
| starting policy | r38 v3-t3patch adapter (post-r39) | preserve all r38/r39 gains |
| LoRA r / α | 64 / 128 | matches the v3 adapter shape (continue) |
| dataset | v18 (~3980 rows incl. delegation block) | v17 base + §10 |
| epochs | 1 | the delegation pairs are NEW signal; one epoch is enough to install the pattern. Don't over-train (regresses v3 Mk.I). |
| LR | 5e-5 | half the normal SFT LR — minimal-perturbation continue-train, same rationale as r39 T3 patch |
| batch × accum | 1 × 8 = 8 | same as r34 SFT recipe |
| max-seq | 1024 | delegation pairs include longer prompts than v17 — bump from 512 |
| compute | 1 × A100 SXM4 40GB | r38 confirmed 40GB is enough for 7B SFT + LoRA |
| cost | ~$2-3, ~2-3h | dataset is 25% bigger than v17; one epoch ~ 30-45 min train + 35 min Mk.I score + 30 min DLG eval + 3 min push |

**Acceptance gates:**
- ✅ Mk.I 665 ≥ 88% strict (within 3pp of v3 GA)
- ✅ 5-NL ≥ 95% (within 5pp of v3 GA's 100%)
- ✅ DLG-mk0 route correctness ≥ 0.90, schema validity ≥ 0.98, overall ≥ 0.85
- ✅ T4 ≥ 95% (Lever 4 win not destroyed by SFT)

If any fails: abort, ship v3-t3patch as GA, re-tune dataset balance.

---

## 12. v0.4.0 deliverables checklist

- [ ] `papers/spec-delegation-v0.4.0.md` — this file.
- [ ] `tool/build_sft_dataset_v18.py` — v17 base + §10 delegation block.
- [ ] `tool/forge_runtime.py` — runtime contract §3 implementation.
- [ ] `tool/score_delegation_mk0.py` — DLG-mk0 scorer §9.B.
- [ ] `eval/delegation-mk0/manifest.jsonl` — 200-task DLG eval §9.A.
- [ ] `state/delegation_log.jsonl` — telemetry sink (gitignored).
- [ ] One Vast A100 round: train + score Mk.I + score 5-NL + score DLG-mk0 +
  HF push as `dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-delegate`.
- [ ] `ROADMAP.md` round entry; `LEARNING_PROGRAMMING.md` §8 row.

Estimated wall-clock: **2-3 days of build/spec/dataset work + one ~3-hour pod round**.

---

## 13. What this enables

- Forge code-LLM stops pretending to know things it doesn't (the "Rust async
  with tokio" prompts r10/r24 mis-answered now route to Claude/GPT-5).
- The 7B's specialist value is preserved (hexa-canon ≥ 88%) — the delegation
  is **additive**, not a replacement.
- A clean line opens to v0.5.0+ work: caching delegated answers, multi-turn
  delegation memory, Brier-calibrated confidence bands, web-search /
  code-execution tool primitives, the Wilson agent target.

---

## 14. Bookmarks

- `LEARNING_PROGRAMMING.md` §12 — design rationale + competence-boundary table
- `LEARNING_PROGRAMMING.md` §13 — OpenAI + Gemini API surfaces (the §2.A
  `tool`/`model` enums come from here)
- `LEARNING_PROGRAMMING.md` §14 — Wilson agent target (v0.5.0+ `wilson-rpc` tool)
- `papers/spec-lever4-compile-rl.md` — Lever 4 (CLOSED, r38, prerequisite)
- `IDEA.md` (gitignored) §A1 (calibration), §B3 (streaming UX), §C1 (cost
  routing), §E3 (prompt injection — relevant to §6 redaction)
- [[reference-trl-grpo-stack-pin]] — TRL 0.17.0 pip recipe (reusable for v0.4.0 SFT)
- [[reference-vastai-cli]] — pod provisioning + 40GB-is-enough lesson
- [[feedback-pod-quoting]] — self-contained run_pod.sh pattern (mandatory)
- [[t3-quote-fragility]] — minimal-perturbation SFT design lesson (r39 informs v18 epoch=1 / LR=5e-5)
