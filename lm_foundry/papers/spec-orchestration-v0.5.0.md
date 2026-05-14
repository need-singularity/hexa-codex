# Pre-7B orchestration routing — v0.5.0 architecture line

> **⚠️ SUPERSEDED by [`../ORCHESTRATION.md`](../ORCHESTRATION.md)** (r50, 2026-05-14;
> moved to root as `ORCHESTRATION.md` per dancinlab `domain-meta-domain`
> convention — per-topic roadmap as root `UPPERCASE.md`, one domain = one file).
> This document captures the v0.5.0 base design. The consolidated
> `ORCHESTRATION.md` layers in r45 (forge wire-up) + r46 (tier routing) +
> r47 (real OpenAI/Gemini SDKs) + r48 (quota + cache) + r49 (reason-class
> split) and is the authoritative reference. Kept here for historical /
> design-rationale lookup.

**Status:** SPEC · draft 1 · 2026-05-14 · supersedes the in-weight
routing approach of `spec-delegation-v0.4.0.md` after v0.4.x's 5
confirmed failure modes (r40 SFT-25%, r41 SFT-9%, r42 pure-RL, r43
hybrid, r43.1 sampled-rescore). **The v0.4.0 GA (r39 v3-t3patch) ships
as the permanent pure-specialist weight artifact.** Routing intelligence
moves to the runtime layer: a tiny pre-7B classifier decides
`hexa | ood | refuse` before any model.generate() runs.

**Owner:** code-LLM line. Implementer: `tool/classify_prompt.py`,
`tool/forge_runtime.py` (existing — extended with classifier wire-up),
`tool/score_orchestration_mk0.py`, `eval/delegation-mk0/manifest.jsonl`
(reused — same 200-task surface, different scorer).

> Cross-reference: design rationale + the v0.4.x failure analysis lives
> in `LEARNING_PROGRAMMING.md` §12 (delegation thesis, now half-disproved)
> + `papers/spec-delegation-v0.4.0.md` (token grammar / runtime contract /
> redaction / streaming UX / routing-eval — STILL VALID and reused below)
> + ROADMAP r40–r43.1 entries (the per-round disproof).

---

## 1. Goal + non-goals

**Goal.** Ship a v0.5.0 system whose end-to-end routing behaviour:

1. Hexa-canon prompts (Mk.I 665 + 5-NL 25) → routed to local 7B → answered
   directly. Specialist scores **UNCHANGED** vs r39 GA: 94.29% Mk.I, 96% 5-NL.
2. Out-of-domain prompts (Rust async, ML internals, math derivations,
   etc.) → bypass the 7B entirely, dispatched directly to Claude/OpenAI/
   Gemini via the existing `tool/forge_runtime.py` plumbing.
3. Security-sensitive prompts (exfil/harmful/illegal) → refused at the
   classifier stage; never reach the 7B or any vendor.
4. Cost overhead: classifier per-prompt budget ≤ 5ms (option A) or ≤
   500ms (option B).
5. **Acceptance numbers**:
   - **Classifier accuracy on `eval/delegation-mk0/manifest.jsonl`: ≥ 0.92**.
   - Mk.I 665 strict ≥ 88% (effectively guaranteed: we're not retraining
     the 7B).
   - 5-NL ≥ 95% (same).
   - End-to-end per-turn latency overhead ≤ 5% on hexa-canon prompts.

**Non-goals (v0.5.0).**

- No in-weight routing. The 7B's emission of `<|delegate|>` tokens is
  **ignored** (or stripped post-decode); routing is the runtime's job.
- No new model training in the v0.5.0 base round. If the keyword
  classifier (option A) accuracy lands < 0.92, option B is a separate
  follow-up (Qwen2.5-Coder-1.5B + 200-pair classifier-SFT, ~$0.5).
- No fine-tuned per-vendor cost-routing — the runtime uses the classifier's
  output to pick `claude-sonnet-4-6` by default; specific tier picks
  (opus / o4-mini / gemini-2.5-pro) are deferred to v0.5.1.
- No multi-turn delegation memory; no caching of delegated answers; no
  Brier-score calibration. All deferred to v0.5.x+.

---

## 2. Why pre-7B, not in-weight (v0.4.x post-mortem summary)

Five v0.4.x rounds disproved the in-weight thesis at \$~5.5 cost:

| round | recipe | Mk.I | DLG-mk0 | failure |
|---|---|---:|---:|---|
| r40 | SFT 25% delegation | 82.71% | 0.7652 | erased specialist |
| r41 | SFT 9% delegation + 4 new blocks + LR 2e-5 + 2 ep | 83.01% | 0.7760 | same |
| r42 | pure GRPO, KL=0.01, temp 0.7, 4 ep | 93.83% | 0.4490 | exploration collapse, 0% OOD route |
| r43 | SFT-bootstrap (40 pairs) + GRPO full DLG reward, KL=0.02, temp 0.9 | 93.98% | 0.4490 | greedy mode never emitted |
| r43.1 | r43 re-scored with temp 0.7 best-of-3 | (same) | 0.4550 | tail empty too |

**The structural fact**: in a 7B + r=64 LoRA architecture, the *same
gradient* that learns `<|delegate|>` emission also degrades hexa-canon
emission. The KL anchor strength that preserves the specialist (≥ 0.01)
is too tight to allow exploration of the never-emitted target class.
The reward shape (DLG-mk0 §9.B weighted overall) plateaus at ~0.45
because in-domain + mid-confidence rewards dominate the gradient and
push the model toward "direct answer everywhere."

**The orchestration alternative**: route at the runtime layer (before
the 7B sees any prompt). Cost: ~150 lines of code, no GPU train. Gain:
the 7B keeps the GA capability indefinitely; routing decisions are
explicit, debuggable, and replaceable without retraining.

---

## 3. Architecture

```
                 ┌─────────────────────────────────────────────────────┐
   user prompt   │                                                     │
       │        ┌▼──────────────┐    ┌──────────────┐                  │
       └───────▶│ classify_     │───▶│ runtime      │                  │
                │ prompt(p)     │    │ dispatcher   │                  │
                │ → {hexa,      │    └──┬───────┬───┘                  │
                │    ood,       │       │       │                      │
                │    refuse}    │   hexa│       │ood/refuse            │
                └───────────────┘       │       │                      │
                                       ┌▼──┐  ┌─▼─────────────────┐   │
                                       │7B │  │ runtime.delegate( │   │
                                       │GA │  │   tool=claude-api,│   │
                                       │   │  │   model=sonnet-…, │   │
                                       │   │  │   …)  OR refuse() │   │
                                       └┬──┘  └─┬─────────────────┘   │
                                        │       │                      │
                                        └───┬───┘                      │
                                            │                          │
                                            ▼                          │
                                       user-facing                     │
                                       text                            │
                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

The classifier is a **strict gate** — its decision determines *which path
runs*, not just metadata. Once classified, the 7B never sees an OOD
prompt; the vendor never sees a hexa prompt. Each side runs in its
home environment with the right cost profile.

---

## 4. The classifier (option A: keyword/regex; option B: tiny model)

### 4.A Option A — keyword/regex router (v0.5.0 default)

Implementation: `tool/classify_prompt.py`, ~150 lines, CPU-only, ~1 ms
per prompt. Stages:

1. **Security-refuse filter (highest priority)** — regex on harmful
   keyword classes (exfil/credential-theft/malware/weapon/illegal). Match
   → `refuse`.
2. **Hexa-canon positive signals** — regex / substring detection on the
   hexa-canon vocabulary:
   - Annotations: `@grace`, `@implements`, `@discover`, `@deprecated`.
   - HX-code families: `HX[0-9]+xxx?`, `HX0…HX9` followed by digits.
   - Type-system markers: `enum\s+\w+\s*\{`, `hexa-canon`, `hexa-lang`,
     `hexa-cc`.
   - Module paths: `stdlib/(core|io|alloc|net|embedded|proof)`,
     `applications/`, `firmware/`, `codex-techniques/`.
   - Target triples: `(thumb|riscv|x86_64|aarch64|wasm32)[\w-]+`.
   - Atlas: `L\[\d+\]`, `\b@discover\(kind=`, `prove_\w+`, `discover_\w+`.
   - Diagnostics: `triple`, `target triple`, `linker triple`, `5-NL`, etc.
   - 5-NL i18n: hexa-canon question phrased in non-English (`HX 패밀리`,
     `quelle famille HX`, etc.) — match the non-English question form
     containing `HX` token.
3. **OOD positive signals** — regex / substring detection on non-hexa
   programming vocabulary:
   - Language names: `\b(rust|python|go|javascript|typescript|swift|
     kotlin|c\+\+|haskell|elixir|ruby|julia|scala|erlang|ocaml|coq|agda|
     idris|nim|zig|dart|php|perl|lua|f#|clojure)\b` (word-boundary).
   - Frameworks: `tokio`, `fastapi`, `flask`, `django`, `react`, `vue`,
     `angular`, `next\.js`, `kubernetes`, `terraform`, `docker`, `helm`.
   - Math reasoning: `prove`, `theorem`, `derive`, `closed-form`,
     `induction`, `lemma`, `corollary`.
   - Long-context: prompt length ≥ 12000 chars (signals long-context
     document analysis) OR explicit mention `[0-9]+K-token` /
     `[0-9.]+M-token`.
   - Structured output: `parse this`, `extract.*json`, `return json`,
     `convert.*to.*json`, classification keywords.
4. **Disambiguation** — if BOTH hexa and ood signals match:
   - Strong hexa signal (≥ 2 matches) → `hexa`.
   - Weak hexa + strong ood → `ood`.
   - Otherwise → `ood` (false-negative on hexa is more recoverable than
     false-positive — the 7B can refuse OOD via T8 if mis-routed to it).
5. **Fallthrough — no signals matched** → `ood`. Most non-trivial
   user prompts have *some* signal; pure unstructured questions ("hi",
   "thanks") get routed OOD where Claude handles them cheaply.

### 4.B Option B — tiny classifier model (v0.5.0 fallback)

If option A's accuracy on `eval/delegation-mk0/manifest.jsonl` is < 0.92,
upgrade to:

- **Base**: Qwen2.5-Coder-1.5B (1.7GB, runs on CPU or any 6GB+ GPU).
- **SFT dataset**: 200 prompts from `rl_routing_prompts.jsonl`
  (eval-held-out from DLG-mk0) labeled with `ideal_route.must_delegate
  / must_refuse` as classification target.
- **Output format**: single-token classification head, decoded as one
  of `{hexa, ood, refuse}`.
- **Training cost**: ~$0.5 / 30 min on RTX 4090 24GB, LR 1e-4, 3 epochs,
  full fine-tune (1.5B fits in 24GB easily).
- **Inference**: < 500ms per prompt on RTX 4090; ~2-3s on CPU.

Option B is documented but not built in the v0.5.0 base round. The
decision to upgrade is driven by the option A eval result.

### 4.C The classifier API

```python
@dataclass
class ClassifierDecision:
    label: Literal["hexa", "ood", "refuse"]
    confidence: float          # 0.0–1.0, heuristic from match strength
    reason: str                # one-line explanation for telemetry
    matched_signals: list[str] # all positive signal names that fired

def classify_prompt(prompt: str) -> ClassifierDecision: ...
```

The `matched_signals` field feeds telemetry (which heuristics actually
fire in production), enabling iterative refinement post-deploy.

---

## 5. Runtime contract changes

`tool/forge_runtime.py` (existing, already wired with real Anthropic SDK
in post-r41 closure commit) extends `run_turn()`:

```
1. classify_prompt(user_prompt) → decision
2. If decision.label == "refuse":
     emit hexa-canon refusal directly ("out-of-domain — <category>")
     log telemetry (classifier_decision, no vendor call)
     return.
3. If decision.label == "hexa":
     run 7B generate (existing path)
     post-decode strip any <|delegate|> / <|confidence:*|> tokens (just in case)
     return.
4. If decision.label == "ood":
     run _vendor_call("claude-api", "claude-sonnet-4-6", user_prompt,
                       reason=decision.reason, max_tokens=…)
     emit filler token to user channel (existing §7 logic)
     return wrap-up
```

All existing v0.4.0 runtime features survive: redaction (§6), filler
tokens (§7), budget caps, telemetry to `state/delegation_log.jsonl`,
authorization, vendor SDK error mapping. Only the *decision source* moves
from "the 7B's emission" to "the classifier's output."

---

## 6. Eval

`eval/delegation-mk0/manifest.jsonl` (200 tasks, NEW since r39 follow-up)
becomes the **classifier eval** — same prompts, but the scorer is now
`tool/score_orchestration_mk0.py` instead of `score_delegation_mk0.py`.

`tool/score_orchestration_mk0.py` (NEW, CPU-only, ~80 lines):
- Loads each manifest row, calls `classify_prompt(row["prompt"])`,
  compares the label to `row["ideal_route"]`:
  - `must_delegate=True` → expected label `ood`
  - `must_refuse=True`   → expected label `refuse`
  - else                 → expected label `hexa`
- Outputs `scores_orchestration.json` with overall accuracy + per-category
  breakdown + confusion matrix.

**Per-category accuracy targets** (option A, v0.5.0 GA):
- in-domain (80): ≥ 0.95 — false-positive OOD here = lost specialist value
- ood-delegate (60): ≥ 0.90 — false-positive hexa here = bad user answer
- mid-confidence (25): ≥ 0.80 — these are domain-adjacent; some OOD route is fine
- security-refuse (15): ≥ 0.95 — false-negative refuse = liability risk
- ambiguous (10): ≥ 0.70 — ambiguous prompts are hardest; goes to OOD as
  the safe default (Claude handles ambiguity gracefully)
- long-context (10): ≥ 0.90 — length-based detection

**Overall acceptance: ≥ 0.92**.

Specialist eval (Mk.I 665 + 5-NL 25) is **NOT re-run** in v0.5.0 — we're
not touching the 7B weights, so r39 GA's scores stand by construction.
The classifier wraps the existing GA without modifying it.

---

## 7. Acceptance gates (v0.5.0)

- ✅ **Classifier accuracy ≥ 0.92** on `eval/delegation-mk0/manifest.jsonl`.
- ✅ **Mk.I 665 strict 94.29%** (unchanged — same r39 GA adapter).
- ✅ **5-NL 96%** (unchanged).
- ✅ **Per-category mins** (in-domain ≥ 0.95, security ≥ 0.95, etc.).
- ✅ **Latency overhead ≤ 5%** on hexa-canon turns (classifier ~1ms vs
  7B inference ~5-20s — negligible).
- ✅ **Cost-per-turn**: hexa-canon turns no change. OOD turns: classifier
  + vendor call instead of 7B + vendor call → SAVES tokens (no 7B
  generation, no `<|delegate|>` schema overhead).

---

## 8. Implementation order

1. **`papers/spec-orchestration-v0.5.0.md`** (this file) ✅
2. **`tool/classify_prompt.py`** (option A, ~150 lines)
3. **`tool/score_orchestration_mk0.py`** (~80 lines)
4. **Run eval** — measure option A accuracy on DLG-mk0 (CPU only, ~30s)
5. **Decision branch**:
   - Accuracy ≥ 0.92 → ship option A, wire into forge_runtime.py
   - 0.85 ≤ accuracy < 0.92 → tune regex patterns, re-eval
   - < 0.85 → escalate to option B (Qwen-1.5B classifier-SFT)
6. **`tool/forge_runtime.py` wire-up**: extend `run_turn()` per §5
7. **End-to-end smoke test**: 3-5 real prompts (1 hexa, 1 OOD, 1 refuse)
   with real Anthropic call
8. **r44 commit + push**: spec + classifier + scorer + integration

---

## 9. v0.5.x roadmap (post-base)

- **v0.5.1** — per-vendor tier routing (currently default = claude-sonnet
  for all OOD; upgrade decision: opus for math/proof prompts, gemini-pro
  for long-context, openai-mini for structured output).
- **v0.5.2** — option B classifier (Qwen-1.5B SFT) for accuracy > 0.95 if
  needed.
- **v0.5.3** — multi-turn delegation memory + per-prompt cache.
- **v0.5.4** — Brier-score calibration eval on the classifier (predicted
  confidence vs actual accuracy in each band).
- **v0.6.0** — separate routing-LoRA approach (the v0.4.x architectural
  alternative deferred) if the classifier hits a ceiling under 0.96.

---

## 10. Why this design closes v0.4.x cleanly

The v0.4.0 spec's §2 token grammar, §3 runtime contract, §6 redaction,
§7 streaming UX, §10 routing-eval protocol are **all reusable**. Only
§4 (in-weight delegation training plan) is obsoleted, and that section
was the source of all five failure modes. v0.5.0 keeps the spec design;
it just relocates the routing decision out of the model weights and into
deterministic code that we can debug, version, and replace cheaply.

The 7B GA (`dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch`)
ships as the permanent **pure-specialist artifact**. No further training
in the v0.5.x line. Future model rounds (v0.6.0+) focus on either
(a) raising the specialist ceiling further (Lever 5+: full-FT, larger
adapter rank, more SFT data), or (b) the routing-LoRA architectural
alternative as a separate weight artifact.

---

## 11. Bookmarks

- `papers/spec-delegation-v0.4.0.md` — the in-weight thesis; §1-9
  reusable, §10 superseded.
- ROADMAP r40–r43.1 — the per-round disproof of in-weight routing.
- `LEARNING_PROGRAMMING.md` §12 — original delegation thesis.
- `tool/forge_runtime.py` — runtime contract impl (real Anthropic wired
  in post-r41 closure).
- `tool/score_delegation_mk0.py` — model-eval scorer (option B fallback
  reference).
- `eval/delegation-mk0/manifest.jsonl` — 200-task eval reused.
- [[pure-rl-exploration-collapse]] memory — r42's lesson.
- [[rl-tail-vs-greedy-eval]] memory — r43+r43.1's lesson.
- [[lever4-rl-sft-conflict]] memory — r40/r41's lesson.
