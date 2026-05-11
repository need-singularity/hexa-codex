# plan — execution roadmap (v1.0.0 → v2.0.0)

> **Release-ladder anchored sequencing.** Every release maps to one of
> the 4 verb groups (per `.roadmap.hexa_codex §A.2`); progression is
> strict-monotone in `wired_verbs` and `eval_pipelines` count. Mirrors
> hexa-forge's `plan-execution-roadmap.md` shape.

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| status        | `LIVE`                                                             |
| current phase | **v1.0.0 RELEASED** → preparing v1.1.0 (safety)                   |
| closure       | recipe §7.2 sat-1 = 100% (T1 + T2 + T3 for all 4 F-CODEX)         |
| out-of-scope  | T4 live-hardware (recipe §9) — per-release one-verb gate (D-013)  |
| last updated  | 2026-05-11                                                         |

---

## §0 Status snapshot

| Aspect                        | State                                                |
| ----------------------------- | ---------------------------------------------------- |
| verb specs landed             | 17 / 17 (cp -R from canon@c0f1f570)                  |
| verbs wired (.hexa eval)      | 0 / 17                                               |
| F-CODEX-N closure (T1+T2+T3)  | 4 / 4 at 100% (sat-1 reached)                        |
| F-CODEX-N T4 empirical floor  | 0 / 4 (recipe §9 — gated per release)                |
| .hexa verifiers               | 23 (16 per-pillar + 4 cross-cutter + 3 meta)         |
| regression tests              | 24 .hexa wrappers + 83 pytest auto                   |
| Lean 4 proofs                 | 1 (`σ(6)=12 := rfl`, no `sorry`)                     |
| reference annex papers        | 4 (P1=192/192 EXACT, P2 extension, P3 LOW, P4 HIGH)  |
| ladder verifier               | `verify/release_ladder.py` 7/7 PASS                  |

---

## §1 Release-ladder gates

```
v1.0.0 (2026-05-06, RELEASED) — 17/17 specs, sat-1 closure
   ↓
v1.1.0 (2026-08, TARGET)   — safety group   — 2 wired, 1 eval pipeline, F-CODEX-3 empirical
   ↓
v1.2.0 (2026-10, PLANNED)  — economics      — 5 wired, 2 evals, F-CODEX-1 + F-CODEX-2 empirical
   ↓
v1.3.0 (2026-12, PLANNED)  — ops            — 9 wired, 3 evals
   ↓
v2.0.0 (2027-Q2, ASPIRAT.) — substrate      — 17 wired, 4 evals, F-CODEX-4 empirical
```

Verifier: `verify/release_ladder.py` enforces strict-monotone in
`wired_verbs` and `eval_pipelines` per `.roadmap.hexa_codex §A.2`.

---

## §2 v1.1.0 — safety group (TARGET 2026-08)

> Group focus: **alignment + interpret** wiring (per DoD #1).
> Single eval pipeline canon, F-CODEX-3 T4 empirical floor.

### Tasks

1. **Wire `alignment` verb** — Mk.0 → Mk.I:
   - audit HELM-Core 12-axis bench → contamination check
   - LLM-as-judge baseline + human calibration ratio (D-015)
   - F-CODEX-3 T4 parity vs HELM-Core 4-model composite (D-006)
2. **Wire `interpret` verb** — Mk.0 → Mk.I:
   - audit SAE motif counters (Olsson / Cunningham / Bricken / Anthropic 2024)
   - 10-motif arithmetic floor → empirical floor candidate at Mk.II
3. **Eval pipeline scaffold** — `.hexa` template that other verbs reuse:
   - shared `numerics_*_pipeline.hexa` shape
   - LLM-judge wrapper API
   - human-eval calibration recorder
   - contamination detector skeleton
4. **D-008 close** — confirm alignment + interpret as the v1.1.0 pair.
5. **D-014 close** — single .hexa file per verb; Python verify retained
   in parallel until Mk.IV.
6. **D-015 close** — 80% LLM-judge / 20% human at Mk.III.
7. **Cross-link D-021** — emit handoff signal to `hexa-forge` (forge
   consumes `alignment`, `interpret` specs in its `code` verb refusal
   contract + style audit).

### Exit bar

- [ ] `hexa-codex verify falsifier-check` reports F-CODEX-3 at T4 PASS
      (HELM parity)
- [ ] `alignment/` + `interpret/` have `.hexa` eval pipelines (Mk.I
      completion)
- [ ] release ladder advances to `wired=2, evals=1`
- [ ] `hexa-forge/docs/code-llm.md` Cross-link policy points at the
      wired specs (no breakage)
- [ ] CHANGELOG `[v1.1.0]` entry lands

### Out of scope

economics wiring · ops wiring · substrate wiring · F-CODEX-1/2/4
empirical (deferred)

### Estimate

~3 months effort. Compute: 1× H100 sufficient for HELM-Core 4-model
composite run; SAE motif count uses pretrained model artifacts.

---

## §3 v1.2.0 — economics group (PLANNED 2026-10)

> Group focus: **train_cost + infer_cost + quality_scale** wiring.
> F-CODEX-1 + F-CODEX-2 T4 empirical floors.

### Tasks

1. **Wire `train_cost`** — Mk.0 → Mk.I:
   - Chinchilla 70B / GPT-3 175B / Llama-2 70B / PaLM 540B fit
   - closed-form regression with confidence bands (D-010)
2. **Wire `infer_cost`** — Mk.0 → Mk.I:
   - Claude 4.7 1M ctx live latency curve (when measurement window opens)
   - F-CODEX-2 parity vs GPT-3.5 16k / Claude 2 100k / Gemini 1.5 1M
3. **Wire `quality_scale`** — composite verb tying F-CODEX-1×F-CODEX-2:
   - cross-pillar verifier (already exists: `numerics_cross_pillar.hexa`)
   - Mk.I bench: scaling-law fit + isoperformance contour
4. **D-009 close** — confirm Chinchilla + GPT-3 + Llama-2 + PaLM as the
   parity numbers source.
5. **D-010 close** — closed-form regression with confidence bands; NO
   LLM-judge for cost-fit.
6. **D-004 close** — F-CODEX-1 T4 empirical lands.
7. **D-005 close** — F-CODEX-2 T4 empirical lands.
8. **D-018 (formal)** — prove φ(6)=2 and τ(6)=4 as theorems alongside
   the cost-curve formalisation.
9. **Cross-link** — hexa-forge consumes cost canon for `code` verb
   sizing decisions (M4 Mini 16GB → 7B Q5/Q6 etc., already linked).

### Exit bar

- [ ] `hexa-codex verify falsifier-check` F-CODEX-1 + F-CODEX-2 at T4 PASS
- [ ] economics verbs have `.hexa` eval pipelines
- [ ] release ladder advances to `wired=5, evals=2`
- [ ] Lean 4 has φ(6)=2 + τ(6)=4 theorems

### Out of scope

substrate wiring · F-CODEX-4 empirical (deferred to v2.0.0)

### Estimate

~2 months effort. Compute: minimal (closed-form regression);
measurement-window dependency on Claude 4.7 1M live access.

---

## §4 v1.3.0 — ops group (PLANNED 2026-12)

> Group focus: **deploy + enterprise + agent_serving + eval** wiring.
> No F-CODEX T4 floor specific to this release.

### Tasks

1. **Wire `deploy`** — operational SLO audit; deploy patterns Mk.0 → Mk.I.
2. **Wire `enterprise`** — data-residency carve-outs, on-prem ladder.
3. **Wire `agent_serving`** — Mk.0 → Mk.I:
   - tool-use schema canon
   - **handoff to `hexa-forge`** for the `code` verb input contract
     (see hexa-forge `docs/code-llm.md §VERIFY agent_serving link`)
4. **Wire `eval`** — meta-verb that wraps F-CODEX-1..4:
   - `eval/ai-eval-pipeline.md §S6 Mk.I → Mk.II`
   - reuse v1.1.0 eval pipeline scaffold from §2
5. **D-011 close** — confirm shared eval scaffold form across the 4
   ops verbs.
6. **D-016 close** — adversarial vs eval boundary (generator vs harness;
   cross-link no merge).

### Exit bar

- [ ] all 4 ops verbs have `.hexa` eval pipelines
- [ ] release ladder advances to `wired=9, evals=3`
- [ ] tool-use schema documented; hexa-forge `code` verb consumes
- [ ] CHANGELOG `[v1.3.0]` entry lands

### Out of scope

substrate wiring · F-CODEX-4 empirical

### Estimate

~2 months effort. Compute: operational integration tests, no training.

---

## §5 v2.0.0 — substrate group (ASPIRATIONAL 2027-Q2)

> Group focus: **multimodal + cog_arch + causal + rlhf** wiring.
> F-CODEX-4 T4 empirical floor (SAE motif live count).

### Tasks

1. **Wire `multimodal`** — image / audio / video eval modality.
2. **Wire `cog_arch`** — substrate hub; absorb `ai-honesty` (D-003)
   if honesty-monitor handoff completes.
3. **Wire `causal`** — substrate hub for causal-chain reasoning.
4. **Wire `rlhf`** — preference-data substrate; **handoff to
   `hexa-forge` DPO stage** (`code` verb consumes the canon).
5. **Wire remaining safety: `safety`, `welfare`, `adversarial`,
   `consciousness`** — close D-001 (safety vs welfare), D-002 (anima
   cross-link).
6. **D-007 close** — F-CODEX-4 T4 empirical (Olsson 2022 / Cunningham
   2023 / Bricken 2023 / Anthropic 2024 SAE parity).
7. **D-012 close** — substrate integration form (mirrors n=6 lattice
   n·τ=24 partition).
8. **D-017 promote** — Lean 4 required for `make verify all`.
9. **D-019 close** — bidirectional cross-link to hexa-senses + hexa-mind.

### Exit bar

- [ ] all 17 verbs have `.hexa` eval pipelines (release ladder `wired=17, evals=4`)
- [ ] F-CODEX-4 at T4 PASS
- [ ] Lean 4 verification required gate
- [ ] full bidirectional sister cross-links live
- [ ] CHANGELOG `[v2.0.0]` entry lands; standalone book candidate

### Out of scope (deferred forever)

18th verb (D-022 — violates partition) ·
forge runtime · weights training (delegated to hexa-forge + hexa-chip) ·
honesty-bit production validator (delegated to honesty-monitor)

### Estimate

~5-6 months. Compute: multimodal eval needs vision/audio/video models;
SAE motif live count needs SAE-trained model access.

---

## §6 Critical path

```
v1.0.0 (DONE — sat-1 closure)
   ↓
v1.1.0 safety (alignment + interpret + F-CODEX-3 T4 + scaffold template)
   ↓ (single-eval-pipeline canon reusable downstream)
v1.2.0 economics (train_cost + infer_cost + quality_scale + F-CODEX-1/2 T4 + Lean φ/τ theorems)
   ↓ (cost canon consumed by hexa-forge sizing)
v1.3.0 ops (deploy + enterprise + agent_serving + eval; tool-use schema for hexa-forge)
   ↓
v2.0.0 substrate (multimodal + cog_arch + causal + rlhf + remaining safety + F-CODEX-4 T4)
```

**Single biggest dependency:** v1.1.0's eval pipeline scaffold (§2 step 3)
is the **template every later release reuses**. Getting the .hexa eval
pipeline shape right at v1.1.0 saves rework at v1.2.0/v1.3.0/v2.0.0.

---

## §7 Hard-coded sequencing rules

| Rule                                                                | Source                            |
| ------------------------------------------------------------------- | --------------------------------- |
| `wired_verbs` and `eval_pipelines` strict-monotone across releases  | `.roadmap.hexa_codex §A.2`        |
| 17-verb partition (6+3+4+4) immutable                               | n=6 lattice σ-φ partition         |
| Lean 4 σ(6)=12 proof never regresses                                | `SigmaLatticeCard.lean := rfl`    |
| Recipe §7.2 sat-1 closure never regresses                           | `verify/saturation_check.hexa`    |
| Falsifier preregister (4) immutable in number                       | n=6 lattice (4 = τ(6))            |
| T4 empirical = recipe §9 out-of-loop                                | recipe §9 definition              |
| English-only diagnostics rule (mirrors hexa-lang SPEC §7)           | sister-canon alignment            |

---

## §8 What's deliberately out of scope (forever)

| item                                       | why                                                              |
| ------------------------------------------ | ---------------------------------------------------------------- |
| 18th verb                                  | violates 6+3+4+4=17 partition (D-022)                            |
| Inference serving runtime                  | belongs to `hexa-codex serve` planned CLI, not spec catalog      |
| Model training / SFT / RLHF runtime        | belongs to `hexa-forge`                                          |
| Honesty-bit production validator           | belongs to `honesty-monitor` standalone                          |
| Consciousness primary substrate            | belongs to `anima` standalone                                    |
| Per-modality novel falsifiers (5+ F-CODEX) | violates τ(6)=4 falsifier count                                  |
| Custom LLM-judge synthesis at scale        | model-collapse risk (Shumailov 2024 — mirrors hexa-forge stance) |

---

## Cross-link

- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
- Coverage matrix: [`plan-coverage-matrix.md`](plan-coverage-matrix.md)
- Repo roadmap: [`../.roadmap.hexa_codex`](../.roadmap.hexa_codex)
- README §Release ladder: [`../README.md#release-ladder`](../README.md#release-ladder)
- README §Falsifier preregister: [`../README.md#falsifier-preregister`](../README.md#falsifier-preregister)
- README §Runnable surface: [`../README.md#runnable-surface`](../README.md#runnable-surface)
- CHANGELOG: [`../CHANGELOG.md`](../CHANGELOG.md)
- Sister downstream: [`~/core/hexa-forge/docs/code-llm.md`](../../hexa-forge/docs/code-llm.md)
  (hexa-forge `code` verb consumes 11 of 17 verbs via link-only Cross-link policy)
- Sister planning: [`~/core/hexa-forge/papers/plan-execution-roadmap.md`](../../hexa-forge/papers/plan-execution-roadmap.md)
