# lm_foundry — domain-LLM foundry

> Absorbed from the standalone `hexa-forge` repo on **2026-05-13**.
> The research + recipe + training substrate for **domain-specialised
> LLMs** in the dancinlab stack. Where the rest of `hexa-codex`
> serves and analyses, `lm_foundry/` *trains*.

## What this is

A narrow-and-deep approach to LLMs: a 7B–14B model that only knows
**code** (or only knows **biology**) beats a 70B generalist on its
home turf for less compute, less hallucination, and a smaller laptop.

Two seed verbs:

| verb   | what it is                          | knowledge doc                |
|--------|-------------------------------------|------------------------------|
| `code` | programming-only LLM for hexa-lang  | `LEARNING_PROGRAMMING.md`    |
| `bio`  | HEXA-BIO domain LLM (seq + prose)   | `LEARNING_BIO.md`            |

## Status (2026-05-14, v0.5.14 / r62)

- **`code` verb GA at 94.29% Mk.I strict** (627/665, 96% 5-NL) — r39
  v3-t3patch adapter, **unchanged since the GA mark**. Path: Qwen2.5-
  Coder-7B + LoRA r=64 SFT (r1–r34) → Phase-A manifest fixes (r33, r37,
  r38) → **compile-feedback RL (Lever 4, GRPO)** lifted T4 enum 55→100%
  → **T3 quote-fragility patch (r39) recovered T3 58.8→100%**.
- **v0.4.x in-weight delegation thesis disproved across r40–r43.1**
  (5 distinct failure modes documented; in-weight `<|delegate|>` SFT
  and RL all eroded the specialist or collapsed exploration).
- **v0.5.x orchestration line (r44–r62) shipped the production
  alternative**: routing moves OUT of model weights into a deterministic
  pre-7B keyword classifier + per-vendor tier selector + real 3-vendor
  SDK dispatch + per-prompt cache + multi-turn memory + production
  observability + SQLite WAL multi-process backend. **Specialist
  unchanged**; orchestration wraps the GA adapter.

### Current quality state (r62)

| Eval | Result |
|------|--------|
| Mk.I 665 strict (specialist quality) | **94.29%** (unchanged from r39 GA) |
| 5-NL 25 i18n | **96%** (unchanged) |
| DLG-mk0 classifier overall (300 tasks) | **0.9833** |
| DLG-mk0 tier_match | **1.000** (77/77 must_delegate) |
| DLG-mk0 tool_match | **0.9926** |
| Brier score (confidence calibration) | **0.0242 EXCELLENT** (<0.05) |
| ECE (10-bin) | **0.0461 GOOD** (passes <0.05 strict threshold) |
| Refuse-stage zero-bleed | **25/25 = 100%** (r51 NEW patterns verified end-to-end) |

Full per-round narrative through r62 in `ROADMAP.md §CHANGELOG`.

## Architecture (v0.5.x → ORCHESTRATION.md)

```
user prompt → classify_prompt(p) → {hexa, ood, refuse}
                  │
       hexa ─────┴────── ood ─── select_vendor_tier()
        │                │            │
        ▼                ▼            ▼
       7B GA       redact → auth → budget → cache
       (r39)              │              │
                       hit│              │miss
                          ▼              ▼
                    text from        _vendor_call(anthropic/openai/gemini)
                    cache,           with optional native messages list
                    cost=$0          │
                                     ▼
                                 telemetry → state/delegation_log.jsonl
                                            (forge_audit aggregates)
```

Routing intelligence lives in deterministic Python (`tool/classify_prompt.py`
+ `tool/select_vendor_tier.py` + `tool/forge_runtime.py`), not in
model weights — closing the v0.4.x architectural cul-de-sac. Three
storage modes compose: in-memory only / file-backed JSONL (r56+r60) /
SQLite WAL multi-process safe (r61). Production observability via
`tool/forge_audit.py` + maintenance via `tool/forge_vacuum.py`.

## Layout

| path | what |
|------|------|
| `LEARNING_PROGRAMMING.md` | the SSOT for "what the code-LLM must know" — 14 sections incl. hexa-canon, operator skills (Vast/HF/R2/Docker), Claude/OpenAI/Gemini API surfaces, Wilson |
| `LEARNING_BIO.md` | same, for the bio verb |
| `ROADMAP.md` | per-round narrative — r1 through **r62**; complete documented recipe with every failure mode preserved |
| **`ORCHESTRATION.md`** | **canonical spec for the v0.5.x runtime stack** (root domain doc per `domain-meta-domain` convention) — 15 sections + ## Log |
| `LATTICE_POLICY.md` | universal real-limits standard (dancinlab-wide) |
| `LIMIT_BREAKTHROUGH.md` | this project's real-limits audit per LATTICE_POLICY |
| `papers/` | design docs — `spec-lever4-compile-rl.md`, `plan-v0.3.0-structural.md`, `spec-delegation-v0.4.0.md` (OBSOLETE §4/§10), `spec-orchestration-v0.5.0.md` (SUPERSEDED), per-tier findings |
| `tool/` | builders + trainers + scorers + **the orchestration runtime** — see table below |
| `eval/` | `hexa-eval/manifest-mk1.jsonl` (665-task Mk.I) + `five-nl-eval/` (25-task 5-NL i18n) + `delegation-mk0/manifest.jsonl` (300-task routing eval r51) |
| `cli/` | the `hexa-forge` verb-table CLI (`status` / `selftest` / `code` / `bio`) |
| `docs/` | per-verb recipe docs (`code-llm.md`, `bio-llm.md`) |
| `bench/` | per-round score artifacts (orchestration / brier / e2e) |
| `bench-cold/` | local per-round bench pulls — **gitignored**; SoT is HF `dancinlab/hexa-forge-bench-cold-v0.1.3` |
| `datasets.toml` | dataset registry |
| `IDEA.md` | local idea memo on LLM-UX pain points — **gitignored** |

### `tool/` — orchestration runtime (v0.5.x)

| file | role |
|------|------|
| `forge_runtime.py` (~1900 LOC) | runtime dispatcher · 3 vendor SDKs · per-prompt + file + SQLite WAL cache · multi-turn memory (string-concat + native messages) · cross-turn anthropic cache · schema versioning |
| `classify_prompt.py` (~470 LOC) | stage-based regex classifier — refuse/hexa/mid-conf/OOD with reason-deep/algo/ml-comparison signals · calibrated `_emit_conf` |
| `select_vendor_tier.py` (~225 LOC) | pure function: 6-step priority cascade (longctx / ml-comp demote / reason-algo / reason-deep / struct / general) |
| `score_orchestration_mk0.py` | CPU eval — classifier accuracy + tier_match + tool_match (300-task) |
| `score_brier_mk0.py` | calibration eval — Brier + ECE + 10-bin reliability table |
| `forge_audit.py` (~660 LOC) | production observability CLI — aggregation + health gates + 3 output formats |
| `forge_vacuum.py` (~280 LOC) | SQLite maintenance CLI — expire-cleanup + LRU cap + VACUUM + optimize (cron) |
| `smoke_e2e_r53.py` | end-to-end production smoke (24 prompts × real APIs) |
| `build_manifest_r51_extras.py` | manifest expansion script (200→300) |

### `tool/` — specialist training (v0.1.x – v0.4.x, frozen at r39 GA)

| file | role |
|------|------|
| `build_sft_dataset_v*.py` | SFT dataset builders (r1–r34) |
| `train_sft_lora.py` | Qwen2.5-Coder-7B + LoRA r=64 SFT trainer |
| `build_rl_t4_prompts.py` | Lever 4 compile-feedback RL prompt set |
| `train_rl_grpo_t4.py` | GRPO trainer (TRL 0.17.0 stack) |
| `score_hexa_eval.py` | Mk.I 665 scorer |

## Configuration (v0.5.x runtime)

```python
from tool.forge_runtime import ForgeRuntime, ForgeRuntimeConfig
from pathlib import Path

# Single-process simple deployment (file-backed persistence)
cfg = ForgeRuntimeConfig.from_env(
    vendor_cache_path=Path("/var/lib/forge/cache.jsonl"),
    multi_turn_memory_enabled=True,
    conv_history_path=Path("/var/lib/forge/conv.jsonl"),
)

# Multi-process production deployment (SQLite WAL)
cfg = ForgeRuntimeConfig.from_env(
    vendor_cache_enabled=True,
    multi_turn_memory_enabled=True,
    multi_turn_memory_native_messages=True,
    multi_turn_memory_auto_prepend=True,
    forge_db_path=Path("/var/lib/forge/forge.sqlite3"),
)

rt = ForgeRuntime(cfg)
result = rt.run_turn(user_prompt, gen_fn=local_7b_generate, conv_id=session_id)
```

Production cron pattern (daily 03:00 maintenance):
```bash
0 3 * * * forge python3 /opt/forge/tool/forge_vacuum.py \
    --db /var/lib/forge/forge.sqlite3 \
    --keep-recent 4096 --conv-days 30
```

Production health-gate (daily check):
```bash
python3 /opt/forge/tool/forge_audit.py \
    --input /var/lib/forge/state/delegation_log.jsonl \
    --since-hours 24 \
    --alert-cache-hit-min 0.20 \
    --alert-error-rate-max 0.05 \
    --alert-cost-day-max 50.00 \
    || mail -s "forge degraded" oncall@example.com
```

## Hugging Face artifacts

**42 repos** under `dancinlab/hexa-forge-*` (adapters, GGUFs, the
bench-cold dataset). The `hexa-forge` prefix is retained as **artifact
identity** — renaming would break `from_pretrained` references in
published recipes.

**GA adapter (unchanged since r39):**
`dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch`
(94.29% Mk.I, 96% 5-NL — pure hexa-canon specialist).

Labeled experiments (NOT GA): `…-rl-t4-v3-t3patch` is preceded by the
Lever-4 line (`…-rl-t4`, `…-rl-t4-v2`, `…-rl-t4-v3`) and followed by
the v0.4.x SFT/RL line (`…-v0.4.0-delegate` r40, `…-v0.4.1-delegate` r41,
`…-v0.4.2-route-rl` r42, `…-v0.4.3-route-rl-hybrid` r43 — all disproved).
**v0.5.x is software-only** — no new HF model artifacts (orchestration
lives in `tool/`, not in weights).

## Cost ladder

Total cumulative spend through r62: **~\$18.27 USD** including the r43
zombie pod (~\$9.60 wasted). r54–r62 all \$0 GPU (CPU-only software
rounds). r53 was the only paid-API round in v0.5.x line (\$0.43 across
2 production smoke runs).

| segment | rounds | spend |
|---------|--------|-------|
| Specialist build (r1–r39) | training SFT + Lever 4 RL | ~\$5.0 |
| v0.4.x delegation experiments (r40–r43.1) | RL exploration disproof | ~\$5.5 + \$9.60 r43 zombie |
| v0.5.x orchestration (r44–r62) | 19 software-only + 1 real-API round | ~\$0.43 (r53 only) |

## Operating notes

- Cloud GPU: **Vast.ai is the primary platform** (A100 SXM4 80GB ≈
  \$0.87–1.07/hr, ~80 s ready) after RunPod's 2026-05-12 platform-wide
  stuck-pod incident. Onboarding + CLI surface in `LEARNING_PROGRAMMING.md §6`.
- Pod-side work ships a self-contained `run_pod.sh` via scp — never
  inline ssh heredocs (the "rm-disaster" rule).
- This component follows the dancinlab-wide `LATTICE_POLICY.md`
  (real-limits-first verification anchor).
- **For v0.5.x runtime work specifically**: no pod needed — the entire
  orchestration stack is CPU-runnable (smoke tests + scoring + audit +
  vacuum all complete in seconds on Mac M-chip).

## What's next (v0.6.0+ scope)

- **OpenAI key provisioning** (user-action) — currently auth_fail; blocks
  real o4-mini + gpt-5-mini end-to-end validation
- **Gemini paid tier** (user-action) — currently upstream_quota on
  gemini-2.5-pro free tier; blocks longctx answer quality measurement
- **Specialist ceiling** (GPU-bound) — either Lever 5+ (full-FT / larger
  LoRA / more SFT data) OR routing-LoRA architectural alternative
- **Anthropic cross-turn cache ROI measurement** (r62 shipped marker;
  needs production telemetry to confirm input-token savings)
- **SQLite incremental vacuum** — would let `VACUUM` run concurrently
  with reads (requires schema migration)
