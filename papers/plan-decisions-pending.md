# plan — decisions ledger (v1.x)

> **Single source of truth for "what's still open" in hexa-codex.**
> Resolved decisions retire to §4 with date stamp. Mirrors the layout
> used in sister `hexa-forge` planning.

| field        | value                                                |
| ------------ | ---------------------------------------------------- |
| status       | `LIVE`                                               |
| current      | v1.0.0 RELEASED (recipe §7.2 sat-1 = 100% closure)  |
| next target  | v1.1.0 ~2026-08 (safety group wiring)               |
| convention   | `D-NNN` = decision, `M-NNN` = meta/batch            |
| last updated | 2026-05-11                                          |

---

## §1 How this ledger works

- Each pending design question is a `D-NNN` row with a **proposed
  default** in italics so work can proceed if no one objects.
- A row in §3 is **active**: it is gating a release target or a verb
  wiring step. The `blocks` column names what's stuck.
- When resolved: move to §4 with date + 1-line rationale. Do NOT
  delete — audit trail.
- Source of inheritance: `~/core/hexa-codex/.roadmap.hexa_codex §A.5`
  (pre-existing pending) + per-falsifier T4 empirical floors + per-group
  wiring gates.

---

## §2 Critical path at a glance

```
Paper-resolvable decisions resolved at 2026-05-11 (D-013..D-022 closed).
Remaining 11 are split into 4 streams:

[Release-prep triggers] — lifted when each release prep begins:
   D-008 (v1.1.0 verbs = alignment + interpret) ─ unblocks v1.1.0 release
   D-009 (v1.2.0 cost-fit data) + D-010 (fit method) ─ unblocks v1.2.0
   D-011 (v1.3.0 ops eval form) ─ unblocks v1.3.0
   D-012 (v2.0.0 substrate scope) ─ unblocks v2.0.0

[F-CODEX T4 empirical floors] — gated on real measurements:
   D-006 (F-CODEX-3 T4 — HELM-Core)  ← v1.1.0 + forge refusal matrix (D-023)
   D-004 (F-CODEX-1 T4 — Chinchilla) ← v1.2.0 + forge SFT curve (D-023)
   D-005 (F-CODEX-2 T4 — Claude 1M)  ← v1.2.0 + forge latency profile (D-023)
   D-007 (F-CODEX-4 T4 — SAE motif)  ← v2.0.0 + forge weight introspection

[Canon debates] — slow-burn, NOT blocking any single release:
   D-001 / D-002 / D-003 — verb taxonomy stability over time

[Forge intake] — operational protocol:
   D-023 (forge T4 PR template + SLA) ← lifts when forge v0.1.3 reaches SFT
```

**Single biggest dependency:** forge v0.1.3 SFT triggers D-023 lift +
unblocks D-004/D-005 (and likely D-006). Until forge enters compute,
hexa-codex's release ladder progresses on paper specs + arithmetic
floor only.

---

## §3 Active ledger

### Pre-existing (from .roadmap §A.5)

| ID    | Status | Decision                                                   | Proposed                                                | Blocks                | Blocked by |
| ----- | ------ | ---------------------------------------------------------- | ------------------------------------------------------- | --------------------- | ---------- |
| D-001 | OPEN   | AI safety vs welfare verb separation strength             | *keep 2 verbs (different falsifier classes); cross-cite* | verb taxonomy stability | canon-side review |
| D-002 | OPEN   | anima (consciousness) cross-link strength                 | *soft link; anima retains own substrate, this verb extracts only the falsifier hooks* | consciousness verb scope | anima-side handoff |
| D-003 | OPEN   | honesty-monitor verb overlap (cog-arch absorbs ai-honesty) | *cog-arch absorbs; honesty-monitor stays standalone falsifier validator* | cog-arch substrate scope | honesty-monitor handoff |

### F-CODEX empirical floors (T4 — recipe §9 territory)

| ID    | Status | Decision                                              | Proposed                                                | Blocks                | Blocked by |
| ----- | ------ | ----------------------------------------------------- | ------------------------------------------------------- | --------------------- | ---------- |
| D-004 | OPEN   | F-CODEX-1 T4 empirical floor (training cost N^24)    | *Chinchilla 70B / GPT-3 175B / Llama-2 70B / PaLM 540B fit, v1.2.0 target* | v1.2.0 release | D-009 (cost-fit data) |
| D-005 | OPEN   | F-CODEX-2 T4 empirical floor (inference cost ctx^4)  | *Claude 4.7 1M live latency curve, v1.2.0 target*       | v1.2.0 release | live measurement window |
| D-006 | OPEN   | F-CODEX-3 T4 empirical floor (alignment 12-axis)     | *HELM-Core 4-model composite, v1.1.0 target*           | v1.1.0 release | D-008 (verb wiring) |
| D-007 | OPEN   | F-CODEX-4 T4 empirical floor (motif count 10)        | *Olsson 2022 + Cunningham 2023 + Bricken 2023 + Anthropic 2024 SAE parity, v2.0.0+ target* | v2.0.0 release | D-012 (substrate scope) |

### Release wiring (block release ladder progression)

*(D-013 resolved 2026-05-11 — see §4. D-008..D-012 stay open as **release-prep
triggers** — lifted when each release prep begins, not paper-blocking.)*

| ID    | Status | Decision                                              | Proposed                                                | Blocks                | Blocked by |
| ----- | ------ | ----------------------------------------------------- | ------------------------------------------------------- | --------------------- | ---------- |
| D-008 | OPEN   | v1.1.0 safety group verb selection                   | *alignment + interpret (per .roadmap §0 DoD #1)*       | v1.1.0 release | — |
| D-009 | OPEN   | v1.2.0 economics scaling fit data source             | *Chinchilla published numbers + GPT-3 / Llama-2 / PaLM*  | D-004                 | — |
| D-010 | OPEN   | v1.2.0 cost-curve fit method                         | *closed-form regression with confidence bands; no LLM-judge* | v1.2.0 release | D-009 |
| D-011 | OPEN   | v1.3.0 ops .hexa eval pipeline form                  | *deploy + agent_serving sharing a single eval scaffold; cross-link to enterprise + eval verbs* | v1.3.0 release | D-008 (template) |
| D-012 | OPEN   | v2.0.0 substrate integration scope                   | *multimodal + cog_arch + causal + rlhf as 4-pillar integrated test (mirrors n=6 lattice n·τ=24 partition)* | v2.0.0 release | — |

### Per-verb Mk.I → Mk.V cycle

*(D-014, D-015, D-016 resolved 2026-05-11 — see §4.)*

### Formal substrate (Lean 4)

*(D-017, D-018 resolved 2026-05-11 — see §4.)*

### Cross-link strength to sisters

*(D-019, D-020, D-021 resolved 2026-05-11 — see §4. D-021 upgraded to **bidirectional** matching hexa-forge D-031.)*

### New verb proposals

*(D-022 resolved 2026-05-11 — 17 verbs are anchored to σ-φ partition; 18th verb permanently rejected.)*

### Intake from hexa-forge (block forge → codex feedback loop)

| ID    | Status | Decision                                              | Proposed                                                | Blocks                | Blocked by |
| ----- | ------ | ----------------------------------------------------- | ------------------------------------------------------- | --------------------- | ---------- |
| D-023 | OPEN   | forge feedback intake protocol                        | *accept PRs per [`~/core/hexa-forge/papers/plan-feedback-channel-ops.md`](../../hexa-forge/papers/plan-feedback-channel-ops.md) template — `t4-empirical/forge-<run_id>.json` + parity row in `numerics_<verb>_t4_parity.hexa`; SLA ≤ 2 weeks per T4 PR; do NOT auto-tombstone arithmetic floor on T4 anomaly — open a paired `D-NNN` in this ledger* | forge → codex feedback loop closure | forge v0.1.3 enters SFT |

### Meta / batch actions

| ID    | Status | Action                                                | Inputs                                                  | Output                |
| ----- | ------ | ----------------------------------------------------- | ------------------------------------------------------- | --------------------- |
| M-001 | OPEN   | v1.1.0 release prep                                   | D-008 / D-014 / D-006                                   | safety group wired; .hexa eval pipeline for alignment + interpret |
| M-002 | OPEN   | v1.2.0 release prep                                   | D-009 / D-010 / D-004 / D-005                           | economics group wired; cost-fit T4 empirical |
| M-003 | OPEN   | v1.3.0 release prep                                   | D-011                                                   | ops group wired |
| M-004 | OPEN   | v2.0.0 release prep                                   | D-012 / D-007                                           | substrate group wired; F-CODEX-4 T4 empirical |
| M-005 | OPEN   | Canon split debate consolidation                      | D-001 / D-002 / D-003                                   | verb taxonomy stability statement |

---

## §4 Resolved (audit trail)

| ID    | Decision                                              | Resolved                                                | Date       |
| ----- | ----------------------------------------------------- | ------------------------------------------------------- | ---------- |
| ✓ v1.0.0 release             | 17 verb spec seeds extracted from canon@c0f1f570; 4-group table | shipped | 2026-05-06 |
| ✓ Recipe §7.2 sat-1          | T1 + T2 + T3 closure_pct = 100% for all 4 F-CODEX-N    | reached at iter 27 | 2026-05-08 |
| ✓ Lean 4 σ(6)=12 proof       | `theorem sigma_lattice_card : sigma 6 = 12 := rfl`     | proven (no sorry) | 2026-05-08 |
| ✓ 23+24+3 verifier surface   | 23 .hexa verifiers + 24 regression wrappers + 3 meta   | landed | 2026-05-08 |
| D-013 | T1+T2+T3 → T4 promotion gate                         | **T4 = live compute; only run on ≥1 verb per release; not parallel.** Per release ladder pacing. | 2026-05-11 |
| D-014 | Mk.I → Mk.II handoff template                         | **single .hexa file per verb**; Python verify retained in parallel until Mk.IV. Default confirmed. | 2026-05-11 |
| D-015 | LLM-as-judge vs human-eval calibration ratio           | **80% LLM-judge / 20% human at Mk.III**; revisit at Mk.IV when calibration data accumulates. | 2026-05-11 |
| D-016 | Adversarial vs eval verb boundary                     | **adversarial = generator side; eval = harness side**; cross-link, no merge. Matches `eval/ai-eval-pipeline.md §S4 STRUCT` 3-axis (gen / execute / meta) decomposition. | 2026-05-11 |
| D-017 | Lean 4 build requirement                              | **KEEP optional / reference annex through v1.x**; promote to "required for `make verify all`" at v2.0.0. Matches reference-annex tier in README. | 2026-05-11 |
| D-018 | More Lean theorems beyond σ(6)=12                     | **Defer to v1.2.0** alongside the cost-curve formalisation work. Targets: φ(6)=2, τ(6)=4 as theorems (currently `:= rfl` reflexive but unproven). | 2026-05-11 |
| D-019 | hexa-senses / hexa-mind sister cross-link             | **Citation-only at v1.1.0**; full bidirectional eval at v2.0.0. Mirrors sister-roadmap stability. | 2026-05-11 |
| D-020 | hexa-bio sister falsifier sharing                     | **No shared falsifiers** (different domain); shared n=6 lattice anchor only. | 2026-05-11 |
| D-021 | hexa-forge `code` verb cross-link                     | **BIDIRECTIONAL** (upgraded). hexa-codex provides spec canon to forge; **forge contributes T4 empirical data back** via PR per [`~/core/hexa-forge/papers/plan-feedback-channel-ops.md`](../../hexa-forge/papers/plan-feedback-channel-ops.md). Forge v1.0.0 gate requires ≥ 5 PRs landed in hexa-codex (covers F-CODEX-1 + F-CODEX-2 T4 by default). | 2026-05-11 |
| D-022 | 18th verb candidate?                                   | **NEVER** — 17 = 6+3+4+4 anchored to σ-φ partition (`lattice_check.hexa`'s `verb_partition` invariant). Adding requires lattice rebase, which would invalidate all 4 F-CODEX-N falsifiers. | 2026-05-11 |

---

## §5 Adding a new decision (template)

```
| D-NNN | OPEN   | <one-line decision name>          | *<proposed default>*                     | <what's blocked>      | <what blocks this> |
```

Rules:
- Italic `Proposed` = act-by-default unless objection in the session.
- Rows OPEN for >2 sessions → mark `STALE` + escalate to release-prep meta.

---

## Cross-link

- Execution sequencing: [`plan-execution-roadmap.md`](plan-execution-roadmap.md)
- Coverage matrix: [`plan-coverage-matrix.md`](plan-coverage-matrix.md)
- Repo roadmap: [`../.roadmap.hexa_codex`](../.roadmap.hexa_codex)
- Release ladder: [`../README.md` §Release ladder](../README.md#release-ladder)
- Falsifier preregister: [`../README.md` §Falsifier preregister](../README.md#falsifier-preregister)
- Per-verb specs: 17 specs under `<group>/<verb>/ai-<verb>.md`
- Sister downstream: [`~/core/hexa-forge/docs/code-llm.md`](../../hexa-forge/docs/code-llm.md) (consumes the codex)
