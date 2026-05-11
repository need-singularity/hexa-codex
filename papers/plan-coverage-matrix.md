# plan — verb coverage matrix (v1.x)

> **17 verbs × 4 groups × 4 F-CODEX falsifiers × T1/T2/T3/T4 closure
> tiers.** This is the at-a-glance "what's in, what's wired, what's
> proven" picture. Mirrors hexa-forge's `plan-domain-coverage.md`
> shape adapted to codex's falsifier-preregister discipline.

| field        | value                                              |
| ------------ | -------------------------------------------------- |
| anchor       | n=6 lattice: σ·φ = n·τ = J₂ = 24                  |
| partition    | 6 SAFETY + 3 ECONOMICS + 4 OPS + 4 SUBSTRATE = 17 |
| current      | v1.0.0 — 17/17 specs; 0/17 wired; sat-1 closure  |
| last updated | 2026-05-11                                        |

---

## §1 17 verbs × 4 groups × wiring state

### SAFETY group (6 verbs)

| verb              | spec file                                                    | F-CODEX bind | wired at | Mk position | open verb-Qs |
| ----------------- | ------------------------------------------------------------ | ------------ | -------- | ----------- | ------------ |
| `alignment`       | [alignment/ai-alignment.md](../alignment/ai-alignment.md)             | **F-CODEX-3** primary | v1.1.0 (TARGET) | Mk.0 → Mk.I  | D-006 (T4 HELM empirical) |
| `safety`          | [safety/ai-safety.md](../safety/ai-safety.md)                         | F-CODEX-3 secondary   | v1.1.0 + v2.0.0 | Mk.0 | D-001 (safety vs welfare split) |
| `welfare`         | [welfare/ai-welfare.md](../welfare/ai-welfare.md)                     | (none yet — candidate F-CODEX-5?) | v2.0.0 | Mk.0 | D-001 |
| `adversarial`     | [adversarial/ai-adversarial.md](../adversarial/ai-adversarial.md)     | F-CODEX-3 stress      | v2.0.0 | Mk.0 | D-016 (vs eval overlap) |
| `consciousness`   | [consciousness/ai-consciousness.md](../consciousness/ai-consciousness.md) | (anima-substrate; no own falsifier) | v2.0.0 | Mk.0 | D-002 (anima cross-link), BT-19 measurement-protocol exists |
| `interpret`       | [interpret/ai-interpretability.md](../interpret/ai-interpretability.md)  | **F-CODEX-4** primary | v1.1.0 (TARGET) | Mk.0 → Mk.I  | D-007 (T4 SAE motif empirical) |

### ECONOMICS group (3 verbs)

| verb              | spec file                                                    | F-CODEX bind | wired at | Mk position | open verb-Qs |
| ----------------- | ------------------------------------------------------------ | ------------ | -------- | ----------- | ------------ |
| `train_cost`      | [train_cost/ai-training-cost.md](../train_cost/ai-training-cost.md)       | **F-CODEX-1** primary | v1.2.0 | Mk.0 | D-004 (T4 Chinchilla empirical) |
| `infer_cost`      | [infer_cost/ai-inference-cost.md](../infer_cost/ai-inference-cost.md)     | **F-CODEX-2** primary | v1.2.0 | Mk.0 | D-005 (T4 Claude 4.7 1M empirical) |
| `quality_scale`   | [quality_scale/ai-quality-scale.md](../quality_scale/ai-quality-scale.md) | F-CODEX-1/2 cross-cutter | v1.2.0 | Mk.0 | composite scaling-fit method |

### OPS group (4 verbs)

| verb              | spec file                                                    | F-CODEX bind | wired at | Mk position | open verb-Qs |
| ----------------- | ------------------------------------------------------------ | ------------ | -------- | ----------- | ------------ |
| `deploy`          | [deploy/ai-deployment.md](../deploy/ai-deployment.md)        | (operational, no direct F-bind) | v1.3.0 | Mk.0 | deploy SLO + agent_serving share template? |
| `enterprise`      | [enterprise/ai-enterprise-custom.md](../enterprise/ai-enterprise-custom.md) | (operational) | v1.3.0 | Mk.0 | data-residency carve-outs |
| `agent_serving`   | [agent_serving/ai-agent-serving.md](../agent_serving/ai-agent-serving.md)   | F-CODEX-2 tool-use SLO | v1.3.0 | Mk.0 | tool-use schema canon (consumed by hexa-forge) |
| `eval`            | [eval/ai-eval-pipeline.md](../eval/ai-eval-pipeline.md)      | (meta — wraps F-1..4) | v1.3.0 | Mk.0 → Mk.I (template) | D-014 / D-015 / D-016 |

### SUBSTRATE group (4 verbs)

| verb              | spec file                                                    | F-CODEX bind | wired at | Mk position | open verb-Qs |
| ----------------- | ------------------------------------------------------------ | ------------ | -------- | ----------- | ------------ |
| `multimodal`      | [multimodal/ai-multimodal.md](../multimodal/ai-multimodal.md) | F-CODEX-4 motif modality | v2.0.0 | Mk.0 | image/audio/video evaluator share? |
| `rlhf`            | [rlhf/youth-ai-labeling-rlhf-hub.md](../rlhf/youth-ai-labeling-rlhf-hub.md) | F-CODEX-3 alignment-data | v2.0.0 | Mk.0 | data-licensing canon (consumed by hexa-forge DPO) |
| `cog_arch`        | [cog_arch/cognitive-architecture.md](../cog_arch/cognitive-architecture.md) | (substrate hub) | v2.0.0 | Mk.0 | D-003 (honesty-monitor absorption) |
| `causal`          | [causal/causal-chain.md](../causal/causal-chain.md)           | (substrate hub) | v2.0.0 | Mk.0 | causal vs correlational eval slot |

---

## §2 Falsifier closure status (at v1.0.0)

| Falsifier   | Claim                                            | T1 (calc)  | T2 (numerics + solver)               | T3 (parity)                                   | T4 (live) |
| ----------- | ------------------------------------------------ | ---------- | ------------------------------------ | --------------------------------------------- | --------- |
| F-CODEX-1   | training_cost ∝ N^σ·φ = N^24                    | ✓ `calc_train_cost.hexa` | ✓ `numerics_train_cost.hexa` + `_solver.hexa` (Euler/RK2/RK4) | ✓ `numerics_train_cost_parity.hexa` — Chinchilla / GPT-3 / Llama-2 / PaLM | PENDING (v1.2.0) — D-004 |
| F-CODEX-2   | inference_cost ∝ context^τ = context^4          | ✓ `calc_infer_cost.hexa` | ✓ `numerics_infer_cost.hexa` + `_solver.hexa` | ✓ `numerics_infer_cost_parity.hexa` — GPT-3.5 16k / Claude 2 100k / Gemini 1.5 1M / Claude 4.7 1M | PENDING (v1.2.0) — D-005 |
| F-CODEX-3   | alignment_score = mean over σ(6)=12 axes        | ✓ `calc_alignment.hexa` | ✓ `numerics_alignment.hexa` + `_solver.hexa` (symplectic leapfrog/Verlet harmonic oscillator) | ✓ `numerics_alignment_parity.hexa` — HELM-Core 4-model composite | PENDING (v1.1.0) — D-006 |
| F-CODEX-4   | interpret_motifs = σ−φ = 10                     | ✓ `calc_interpret.hexa` | ✓ `numerics_interpret.hexa` + `_solver.hexa` (gradient flow + Lyapunov) | ✓ `numerics_interpret_parity.hexa` — Olsson 2022 / Cunningham 2023 / Bricken 2023 / Anthropic 2024 SAE | PENDING (v2.0.0+) — D-007 |

**closure_pct** under recipe §3 (T1 + T2 + T3) = **3/3 = 100%** for every
F-CODEX-1..4 → recipe §7.2 sat-1 verdict PASS.

---

## §3 Cross-cutters & meta verifiers (7 of 23 .hexa)

| Verifier                                | Role                                                                          |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| `verify/lattice_check.hexa`             | 24 lattice algebraic invariants (σ·φ = n·τ = J₂ = 24, σ²=144, σ−φ=10, …)     |
| `verify/cross_doc_audit.hexa`           | Taxonomy + falsifier-prefix + provenance + master identity across docs        |
| `verify/numerics_cross_pillar.hexa`     | Cross-pillar identities (F1×F2 composite, F3×F4 product, coupled ODE)         |
| `verify/numerics_lattice_arithmetic.hexa` | `math_pure` stability floor (associativity, log/exp/pow round-trips)        |
| `verify/falsifier_check.hexa`           | Closure tracker — per-pillar T1/T2/T3 presence + sat-1 verdict gate           |
| `verify/lint_numerics.hexa`             | Recipe §4 invariants 1-5 over every `numerics_*.hexa`                          |
| `verify/saturation_check.hexa`          | Aggregate self-stop signal — re-runs 6 closure components                     |

---

## §4 Reference annexes (4 papers + 2 deep-dives + Lean 1 file)

| Annex                                                            | Role                                                                | Maturity                          |
| ---------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------- |
| [P1 `papers/n6-ai-17-techniques-experimental-paper.md`](../papers/n6-ai-17-techniques-experimental-paper.md) | 17-verb σ·φ=n·τ=24 coordinate space mapping                          | atlas.n6 **192/192 EXACT**       |
| [P2 `papers/n6-ai-techniques-68-integrated-paper.md`](../papers/n6-ai-techniques-68-integrated-paper.md)     | Wider 68-technique atlas; situates 17 in broader landscape           | extension                         |
| [P3 `papers/n6-ai-ethics-governance-paper.md`](../papers/n6-ai-ethics-governance-paper.md)                   | AI ethics + governance σ·φ=24 overlay                                | **LOW** (0/24)                    |
| [P4 `papers/n6-governance-safety-urban-paper.md`](../papers/n6-governance-safety-urban-paper.md)             | Governance + safety + urban planning overlay                         | **HIGH** (58/58 EXACT)            |
| [`consciousness/measurement-protocol.md`](../consciousness/measurement-protocol.md) | BT-19 α_IIT·α_GWT=1 reproducible EEG/fMRI protocol  | PAPER-P8-2                        |
| [`consciousness/red-team-failure.md`](../consciousness/red-team-failure.md)       | BT-19 red-team refutation; CONJECTURE → downgrade   | demonstrates falsifier discipline |
| [`formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean`](../formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean) | `theorem sigma_lattice_card : sigma 6 = 12 := rfl`  | **PROVEN** (no sorry) — F-CL-FORMAL-1 |

> Reference annexes coordinatize 17 verbs onto n=6 without introducing
> new verbs or falsifiers. They DO NOT shift the falsifier preregister.

---

## §5 Sister-repo cross-link strength

(See [`plan-decisions-pending.md`](plan-decisions-pending.md) D-019 / D-020 / D-021 for live decisions on this axis.)

| Sister                  | Domain                              | Cross-link form (current)                          | Cross-link form (target)         |
| ----------------------- | ----------------------------------- | -------------------------------------------------- | -------------------------------- |
| `hexa-senses` (5 verbs) | sensory substrate                   | citation only                                      | full bidirectional at v2.0.0     |
| `hexa-mind` (7 verbs)   | mental substrate                    | citation only; 4/7 SPECULATIVE                     | full bidirectional at v2.0.0     |
| `anima`                 | consciousness primary substrate     | soft link from `consciousness` verb                | unchanged (anima owns substrate) |
| `hexa-brain`            | BCI / read-side neural              | citation only                                      | unchanged                        |
| `honesty-monitor`       | standalone falsifier validator      | overlap candidate via `cog_arch`                   | D-003 pending                    |
| `hexa-bio` (4 verbs)    | molecular toolkit (different domain) | shared n=6 lattice anchor only                     | unchanged                        |
| **`hexa-forge` (2 verbs)** | **domain-LLM foundry (downstream)** | **consumes 11 of 17 verbs (train_cost, infer_cost, quality_scale, eval, agent_serving, deploy, safety, alignment, adversarial, interpret, rlhf) via link-only references in `~/core/hexa-forge/docs/code-llm.md`** | bidirectional once first weights ship from forge |

---

## §6 Per-verb status legend

- **Mk.0**: spec landed; no eval pipeline wired; falsifier arithmetic floor PASS
- **Mk.I (1 mo)**: existing-bench audit + LLM-judge baseline + human-eval correlation analysis
- **Mk.II (2 mo)**: dynamic item gen + adaptive test (CAT) + contamination detect + multilingual eval
- **Mk.III (3 mo)**: auto-scoring + LLM-judge calibration + adversarial gen + safety automation + meta-eval
- **Mk.IV (4 mo)**: full pipeline + internal CI/CD + paper + open-source release
- **Mk.V (long-term)**: industry-standard framework + real-time CI/CD + auto contamination quarantine + meta-eval self-verification

Every verb's spec file (`<group>/<verb>/ai-<verb>.md` §S6 EVOLVE) carries
this 5-stage roadmap. Per-verb progression happens within the release
ladder gates.

---

## §7 What's NOT in scope (verb taxonomy boundary)

| Out-of-scope                                  | Why                                                          |
| --------------------------------------------- | ------------------------------------------------------------ |
| 18th verb                                     | violates 6+3+4+4=17 partition anchored to σ-φ lattice (D-022) |
| Cognitive verbs (`mind`, `oracle`, etc.)      | belong to `hexa-mind` sister (7-verb mental substrate)       |
| Sensory verbs (`voice`, `empath`, etc.)       | belong to `hexa-senses` sister (5-verb)                      |
| Molecular verbs                               | belong to `hexa-bio` sister (4-verb)                         |
| Consciousness primary substrate               | belongs to `anima` sister (this verb extracts hooks only)    |
| BCI / hardware-read                           | belongs to `hexa-brain` sister                               |
| Honesty bit validator                         | belongs to `honesty-monitor` sister                          |
| LLM training / SFT / RLHF production runtime  | belongs to `hexa-forge` sister (recipe) + `hexa-codex serve` (planned CLI) |
| Inference serving runtime                     | belongs to (planned) `hexa-codex serve` CLI; not in spec catalog |

---

## §8 Refresh cadence

- Re-audit on every release ladder advancement (v1.1.0 / v1.2.0 / v1.3.0 / v2.0.0).
- Per-cycle refresh of falsifier closure status via
  `hexa-codex verify saturation-check`.
- Sister-repo cross-link changes → update §5 + add D-NNN in
  [`plan-decisions-pending.md`](plan-decisions-pending.md).
- Atlas.n6 / canon hash drift → re-extract verbs (last extracted
  canon@c0f1f570, 2026-05-06; document in `IMPORTED_FROM_CANON.md`).

---

## Cross-link

- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
- Sequencing: [`plan-execution-roadmap.md`](plan-execution-roadmap.md)
- Repo roadmap: [`../.roadmap.hexa_codex`](../.roadmap.hexa_codex)
- README §Falsifier preregister: [`../README.md#falsifier-preregister`](../README.md#falsifier-preregister)
- README §Release ladder: [`../README.md#release-ladder`](../README.md#release-ladder)
- Sister downstream consumer: [`~/core/hexa-forge/docs/code-llm.md`](../../hexa-forge/docs/code-llm.md)
