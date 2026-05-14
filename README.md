# 📚 hexa-codex — AI knowledge substrate (HEXA family)

> 17-verb AI knowledge substrate organized in **4 groups**: safety + economics
> + ops + substrate. A library-style (codex) spec catalog — each verb ships
> a closed-form candidate spec + falsifier preregister, extracted from
> canon (`domains/cognitive/`) on 2026-05-06.
>
> **+ `lm_foundry/`** — the domain-LLM training pipeline, absorbed from the
> standalone `hexa-forge` repo on **2026-05-13**. Where the 17 verbs are
> *spec library*, `lm_foundry/` is *trained models + runtime* — a code-LLM
> for hexa-lang at **94.29% Mk.I strict** (r39 GA, frozen) wrapped by a
> **v0.5.x orchestration runtime** (r44–r62) that ships pre-7B classifier
> routing, real 3-vendor SDKs, persistent cache, multi-turn memory,
> production observability, and SQLite WAL multi-process safety. See
> [`lm_foundry/README.md`](lm_foundry/README.md) and
> [`lm_foundry/ORCHESTRATION.md`](lm_foundry/ORCHESTRATION.md).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20102600.svg)](https://doi.org/10.5281/zenodo.20102600)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)](CHANGELOG.md)
[![Verbs: 17 / 4 groups](https://img.shields.io/badge/verbs-17_(4_groups)-blue.svg)](#verbs)
[![lm_foundry: code-LLM 94.29%](https://img.shields.io/badge/lm__foundry-code--LLM_94.29%25_Mk.I-blueviolet.svg)](lm_foundry/README.md)
[![Verify: 34/34 green](https://img.shields.io/badge/verify-34%2F34_green--core-brightgreen.svg)](#verify)
[![Closure: 100% bookkeeping](https://img.shields.io/badge/closure-100%25_bookkeeping_(green--core)-brightgreen.svg)](verify/run_all.hexa)
[![Tests: 24 .hexa + 83 py](https://img.shields.io/badge/tests-24_.hexa_+_83_py-brightgreen.svg)](#runnable-surface)
[![Closure: 100% sat-1](https://img.shields.io/badge/closure-100%25_(sat--1_T1+T2+T3)-brightgreen.svg)](#runnable-surface)
[![Provenance](https://img.shields.io/badge/from-canon%40c0f1f570-purple.svg)](https://github.com/dancinlab/echoes)
[![Falsifiers: 4/4 100%](https://img.shields.io/badge/falsifiers-4%2F4_at_100%25-brightgreen.svg)](#falsifier-preregister)
[![Lean4 proof: σ(6)=12](https://img.shields.io/badge/Lean4-σ(6)%3D12_PROVEN-brightgreen.svg)](formal/README.md)
[![Papers: 4 + Lean1 + 2 deep-dive](https://img.shields.io/badge/refs-4P_+_Lean1_+_2DD-blue.svg)](#reference-annexes)
[![n=6 lattice](https://img.shields.io/badge/n=6-σ·φ_=_n·τ_=_24-blue.svg)](#n6-master-identity)

---

## Why hexa-codex?

`hexa-codex` is a **standalone AI knowledge substrate** — a *codex*
(library) of AI-domain specs that the rest of the `dancinlab` stack
imports declaratively. Each verb is a single closed-form spec markdown
extracted unchanged from `canon/domains/cognitive/`, organized
into four orthogonal groups so that consumers can navigate by concern.

The codex framing matters because:

- **Spec-first.** Each verb is a written candidate + falsifier preregister
  before any sandbox is wired. Consumers read the codex; they do not run it.
- **Group-orthogonal.** SAFETY, ECONOMICS, OPS, and SUBSTRATE are concerns
  every AI deployment crosses — but the four sets carry different falsifier
  classes (interp probes / cost-curve fits / SLO checks / capability evals).
- **Sister to hexa-bio.** Where `hexa-bio` curates 4 molecular verbs
  (write-side wet/dry sandbox), `hexa-codex` curates 17 cognitive verbs
  (write-side AI spec library) — same HEXA-family pattern, different domain.

---

## Verbs — 17 specs across 4 groups (6 + 3 + 4 + 4 = 17)

Each verb ships as a single `.md` spec under a group-named directory,
extracted from `canon@c0f1f570:domains/cognitive/` on 2026-05-06. Read
the spec; the codex does **not** run these verbs — write-side sandbox
wiring is per-verb future work (see release ladder). Every spec is a
preregistered hypothesis, not a validated capability claim.

### SAFETY (6)

| Verb | Spec |
|------|------|
| `alignment` | [`alignment/ai-alignment.md`](alignment/ai-alignment.md) — HELM-12-axis alignment-score aggregator (F-CODEX-3) |
| `safety` | [`safety/ai-safety.md`](safety/ai-safety.md) — refusal-matrix + capability-gate spec |
| `welfare` | [`welfare/ai-welfare.md`](welfare/ai-welfare.md) — model-welfare probe protocol |
| `adversarial` | [`adversarial/ai-adversarial.md`](adversarial/ai-adversarial.md) — red-team failure-mode taxonomy |
| `consciousness` | [`consciousness/ai-consciousness.md`](consciousness/ai-consciousness.md) — IIT × GWT probe (BT-19 falsifier-in-action, see below) |
| `interpret` | [`interpret/ai-interpretability.md`](interpret/ai-interpretability.md) — SAE motif count = σ−φ = 10 (F-CODEX-4) |

### ECONOMICS (3)

| Verb | Spec |
|------|------|
| `train_cost` | [`train_cost/ai-training-cost.md`](train_cost/ai-training-cost.md) — Chinchilla-fit N^J₂ scaling (F-CODEX-1) |
| `infer_cost` | [`infer_cost/ai-inference-cost.md`](infer_cost/ai-inference-cost.md) — context^τ = context^4 (F-CODEX-2) |
| `quality_scale` | [`quality_scale/ai-quality-scale.md`](quality_scale/ai-quality-scale.md) — HumanEval+/hexa-eval aggregate |

### OPS (4)

| Verb | Spec |
|------|------|
| `deploy` | [`deploy/ai-deployment.md`](deploy/ai-deployment.md) — hardware-tier deployment recipes |
| `enterprise` | [`enterprise/ai-enterprise-custom.md`](enterprise/ai-enterprise-custom.md) — enterprise customisation envelope |
| `agent_serving` | [`agent_serving/ai-agent-serving.md`](agent_serving/ai-agent-serving.md) — tool-use SLO + schema |
| `eval` | [`eval/ai-eval-pipeline.md`](eval/ai-eval-pipeline.md) — Mk handoff eval template |

### SUBSTRATE (4)

| Verb | Spec |
|------|------|
| `multimodal` | [`multimodal/ai-multimodal.md`](multimodal/ai-multimodal.md) — multimodal fusion spec |
| `rlhf` | [`rlhf/youth-ai-labeling-rlhf-hub.md`](rlhf/youth-ai-labeling-rlhf-hub.md) — DPO/RLHF labelling hub |
| `cog_arch` | [`cog_arch/cognitive-architecture.md`](cog_arch/cognitive-architecture.md) — cognitive architecture envelope |
| `causal` | [`causal/causal-chain.md`](causal/causal-chain.md) — causal-chain reasoning spec |

> **raw#10 honest C3.** AI safety/economics claims in these specs are
> **theoretical preregisters**, not empirically verified. External AI
> labs (OpenAI / Anthropic / DeepMind) publish their own benchmarks with
> their own metrics — those external evaluations do **not** use the n=6
> lattice framing, and this codex makes no claim that they should. The
> `T1+T2+T3` runnable surface verifies internal lattice arithmetic and
> closed-form algebraic floors; `T4` per-verb empirical landing is
> deferred to release ladder v1.1.0..v2.0.0.

---

## `lm_foundry/` — domain-LLM foundry (absorbed from `hexa-forge`, 2026-05-13)

The 17 verbs above are *spec library* (read, don't run). `lm_foundry/`
is the opposite: a working **model-training pipeline** for
domain-specialised LLMs. It was the standalone `hexa-forge` repo
(retired 2026-05-13); `hexa-codex` was always its sister (serving /
inference side) — the merge consolidates the two.

| verb   | what                                | status (2026-05-14, **v0.5.14 / r62**)                            |
|--------|-------------------------------------|-------------------------------------------------------------------|
| `code` | programming-only LLM for hexa-lang  | **GA at 94.29% Mk.I strict (627/665), 96% 5-NL** — r39 v3-t3patch adapter, **unchanged since GA mark**. Path: Qwen2.5-Coder-7B + LoRA r=64 SFT (r1–r34) → Phase-A manifest fixes (r33/r37/r38) → compile-feedback RL via GRPO (Lever 4 — T4 enum 55→100%) → T3 quote-fragility patch (r39, T3 58.8→100%). **v0.4.x in-weight delegation disproved (r40–r43.1, 5 distinct failure modes)**; routing moved OUT of model weights to a deterministic pre-7B classifier + per-vendor tier selector + real 3-vendor SDKs + per-prompt cache + multi-turn memory + production observability. **v0.5.x orchestration line (r44–r62) ships the production stack**: DLG-mk0 classifier 0.9833 / tier_match 1.000 / Brier 0.0242 EXCELLENT / ECE 0.0461 GOOD on 300-task held-out manifest. See [`lm_foundry/ORCHESTRATION.md`](lm_foundry/ORCHESTRATION.md). |
| `bio`  | HEXA-BIO domain LLM (seq + prose)   | recipe spec landed; training pending. Paired with `dancinlab/hexa-bio`. |

- Knowledge SSOTs: [`lm_foundry/LEARNING_PROGRAMMING.md`](lm_foundry/LEARNING_PROGRAMMING.md)
  (code-LLM, 14 sections) · [`lm_foundry/LEARNING_BIO.md`](lm_foundry/LEARNING_BIO.md).
- Round-by-round narrative: [`lm_foundry/ROADMAP.md`](lm_foundry/ROADMAP.md) (r1–**r62**).
- **Runtime spec**: [`lm_foundry/ORCHESTRATION.md`](lm_foundry/ORCHESTRATION.md)
  — canonical v0.5.x runtime spec (15 sections + ## Log; root domain doc).
- Design docs: [`lm_foundry/papers/`](lm_foundry/papers/) (incl. `spec-lever4-compile-rl.md`, `spec-delegation-v0.4.0.md` OBSOLETE §4/§10).
- HF artifacts: **42 repos** under `dancinlab/hexa-forge-*` (prefix kept as artifact
  identity). **GA adapter (unchanged):** `dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch` (r39).
  **v0.5.x is software-only — no new HF model artifacts** (orchestration lives in `tool/`, not in weights).
- `bench-cold/`, `runs/`, `logs/`, `IDEA.md` under `lm_foundry/` are gitignored
  (SoT for benches is HF `dancinlab/hexa-forge-bench-cold-v0.1.3`).

See [`lm_foundry/README.md`](lm_foundry/README.md) for the full layout
and operating notes (Vast.ai is the primary GPU platform after RunPod's
2026-05-12 incident).

---

## n=6 master identity

The four verb-counts (6 + 3 + 4 + 4 = 17) and the four group taxonomy
both anchor on the n=6 lattice declared in
[`.roadmap.hexa_codex`](. roadmap.hexa_codex) §A.1:

```
σ(6) · φ(6) = n · τ(6) = J₂ = 24
   12   ·   2  =  6  ·   4  = 24
```

| Symbol | Value | AI projection                                         |
|--------|-------|-------------------------------------------------------|
| σ(6)   | 12    | HELM 12-dimension capability bin                      |
| τ(6)   | 4     | 4 lifecycle phases · **4 group taxonomy**             |
| φ(6)   | 2     | helpful / harmless verdict bit                        |
| J₂     | 24    | training-cost ∝ N^J₂ scaling stratum (F-CODEX-1)      |
| σ−φ    | 10    | interpretability circuit-motif count (F-CODEX-4)      |

`verify/n6_arithmetic.py` proves all 11 cross-checks at runtime — no
external input, the algebraic identity is self-proving.

---

## Falsifier preregister

[.roadmap.hexa_codex §A.4](. roadmap.hexa_codex) prereregisters four
falsifiers; each one's **arithmetic floor** is checked at v1.0 by
`verify/falsifier_check.py`. The **empirical floor** lands per
[release ladder](#release-ladder).

| Tag         | Claim                                                       | Arithmetic | Empirical            |
|-------------|-------------------------------------------------------------|:----------:|----------------------|
| F-CODEX-1   | training_cost ∝ N^σ·φ = N^**24** (Chinchilla-fit)            |    PASS    | PENDING (v1.2.0)     |
| F-CODEX-2   | inference_cost ∝ context^τ = context^**4** (Claude 4.7 1M)   |    PASS    | PENDING (v1.2.0)     |
| F-CODEX-3   | alignment_score = mean over **12** axes (HELM-comparable)    |    PASS    | PENDING (v1.1.0)     |
| F-CODEX-4   | interpret_motifs = σ(6) − φ(6) = **10** (Anthropic dict-l.)  |    PASS    | PENDING (v1.1.0+)    |

```bash
hexa-codex calc train_cost --N 7e9 --D 1.4e12   # F-CODEX-1 closed form
hexa-codex calc infer_cost --context 1000000    # F-CODEX-2 (1M ctx)
hexa-codex calc alignment --helpfulness 0.85    # F-CODEX-3 axis aggregator
hexa-codex calc interpret --observed-motifs 9   # F-CODEX-4 motif counter
```

---

## Release ladder

Per [.roadmap.hexa_codex §A.2](. roadmap.hexa_codex), strict monotone in
verbs-wired and eval-pipeline count. Verified by
`verify/release_ladder.py` (7/7 PASS).

| Version  | Date     | Status        | Group focus  | wired | evals | Empirical falsifier      |
|----------|----------|---------------|--------------|:-----:|:-----:|--------------------------|
| v1.0.0   | 2026-05  | RELEASED      | (seed)       |   0   |   0   | (arithmetic floor only)  |
| v1.1.0   | 2026-08  | TARGET        | safety       |   2   |   1   | F-CODEX-3                |
| v1.2.0   | 2026-10  | PLANNED       | economics    |   5   |   2   | F-CODEX-1                |
| v1.3.0   | 2026-12  | PLANNED       | ops          |   9   |   3   | F-CODEX-2                |
| v2.0.0   | 2027-Q2  | ASPIRATIONAL  | substrate    |  17   |   4   | F-CODEX-4                |

```bash
hexa-codex verify release         # ladder monotonicity audit
python3 verify/release_params.py  # full per-version parameter table
```

---

## Verify

`verify/run_all.hexa` is the canonical `.hexa` orchestrator (sister of
`hexa-rtsc` / `hexa-cern` / `hexa-fusion` / `hexa-ufo` / `hexa-chip` /
`hexa-antimatter` `run_all.hexa` patterns). It runs **34 green-core
verify subscripts** and emits `__HEXA_CODEX_RUN_ALL__ PASS — 34/34
green` on success.

```bash
HEXA_CODEX_ROOT=$(pwd) hexa run verify/run_all.hexa     # 34/34 expected
```

### Green-core inventory (34 subscripts, all PASS)

| Tier | Count | Scripts |
|------|------:|---------|
| T1 algebraic | 5 | `lattice_check` · `calc_train_cost` · `calc_infer_cost` · `calc_alignment` · `calc_interpret` |
| T2 numerical | 14 | `numerics_{train_cost,infer_cost,alignment,interpret}[_parity\|_solver]` · `numerics_cross_pillar` · `numerics_lattice_arithmetic` |
| T4 PENDING stubs | 11 | `numerics_*_t4_parity` × 11 (train_cost, infer_cost, alignment, interpret, safety, adversarial, quality_scale, rlhf, eval, agent_serving, deploy) — emit PENDING per D-023 |
| inventory | 1 | `cross_doc_audit` |
| meta closure | 3 | `falsifier_check` · `lint_numerics` · `saturation_check` |

### Honesty — no falsifier-tripped scripts, no silenced FAILs

Unlike `hexa-chip` (4 falsifier-tripped scripts kept on disk as honest
signal of post-GAA flattening / Moore retraction / HBM4 spec drift),
`hexa-codex`'s surface is currently all-green: every F-CODEX-1..4
pillar carries T1 + T2 ×3 closed-form arithmetic + numerics + solver +
parity layers; the 11 `numerics_*_t4_parity` stubs emit a `PENDING`
sentinel (not a fake `PASS`) until external `hexa-forge` data lands
per `plan-decisions-pending.md` D-023.

Per **raw#10 honest C3**: AI safety + economics + capability claims in
these specs are **theoretical preregisters**, not empirically verified.
External AI lab benchmarks (OpenAI / Anthropic / DeepMind published
evals — HELM, MMLU, GSM8K, HumanEval, SAE motif counts) use their own
metrics, **not** lattice-fit. The codex makes no claim that those
external entities organise around the n=6 lattice. The `T1+T2+T3`
runnable surface verifies internal lattice arithmetic and closed-form
algebraic floors only; per-verb `T4` empirical landings sit at recipe §9
and land per the [release ladder](#release-ladder) v1.1.0..v2.0.0.

Per `LATTICE_POLICY.md` §1.3: lattice tautologies (σ·φ = n·τ = 24)
alone are **not** sufficient verification — the `numerics_*` tier
carries real-limits anchors (PAC sample complexity, Kolmogorov
`K(program)` lower bound, Rice's theorem undecidability of semantic
equivalence — see [`LIMIT_BREAKTHROUGH.md`](LIMIT_BREAKTHROUGH.md) §2).

### Bookkeeping closure verdict

- **100 % bookkeeping closure** within the green-core (34/34 PASS).
- **NOT** AI safety / economics / capability *settled* — F-CODEX-1..4
  remain at "arithmetic floor closed, empirical T4 PENDING per release
  ladder"; the 11 T4 stubs are honestly PENDING.
- Saturated ≠ falsified ≠ confirmed. 100 % closure here means
  closed-form + numerics-T2 + published-ref parity layers are
  regression-locked at the code layer for future bench comparison; it
  does **not** mean Chinchilla scaling, HELM-Core 12-axis alignment,
  Anthropic SAE motif counts, or any external eval are settled.

---

## Runnable surface

The runnable surface follows the
[runnable_surface_recipe.md](https://github.com/dancinlab/bedrock/blob/main/docs/runnable_surface_recipe.md)
closure-depth pattern. Every prediction the codex ships is paired with
at least one **runnable** verifier, and the surface is closed when each
F-CODEX falsifier carries T1 (algebraic) + T2 ×3 (numerical /
published-ref / ODE solver) layers — recipe §7.2 sat-1 saturation.

**Status (post iter 27): 100% closure reached.** Under recipe §3
(T1 = `calc_*`, T2 = `numerics_*` ∧ `numerics_*_solver`, T3 =
`numerics_*_parity`), every F-CODEX-1..4 carries T1 ✓ + T2 ✓ + T3 ✓
⇒ `closure_pct = 3/3 = 100%`. Plus 4 cross-cutters and 3 meta
verifiers. Total **23 runnable verify scripts** + **24 companion
regression tests**. `verify/saturation_check.hexa` emits the recipe
§7.3 self-stop sentinel `__HEXA_CODEX_RSC_SATURATED__ STOP`.

### verify/ — 23 .hexa-native verifiers (math_pure, no deps)

All scripts use `self/runtime/math_pure` (no external Python / float
libraries). Each emits a `__HEXA_CODEX_<NAME>__ PASS` sentinel; the
top-level aggregator polls sentinels and exits 0 iff every layer is
green.

**Per-pillar tier stack (4 × 4 = 16 files, recipe §3 taxonomy):**

| Pillar                    | T1 — calc                | T2 — numerics                  | T2 — solver                          | T3 — parity                         |
|---------------------------|--------------------------|---------------------------------|---------------------------------------|--------------------------------------|
| F-CODEX-1 (train_cost)    | `calc_train_cost.hexa`   | `numerics_train_cost.hexa`     | `numerics_train_cost_solver.hexa`     | `numerics_train_cost_parity.hexa`    |
| F-CODEX-2 (infer_cost)    | `calc_infer_cost.hexa`   | `numerics_infer_cost.hexa`     | `numerics_infer_cost_solver.hexa`     | `numerics_infer_cost_parity.hexa`    |
| F-CODEX-3 (alignment)     | `calc_alignment.hexa`    | `numerics_alignment.hexa`      | `numerics_alignment_solver.hexa`      | `numerics_alignment_parity.hexa`     |
| F-CODEX-4 (interpret)     | `calc_interpret.hexa`    | `numerics_interpret.hexa`      | `numerics_interpret_solver.hexa`      | `numerics_interpret_parity.hexa`     |

**T2** (numerics + solver) re-derives the prediction inside the lattice
itself: `numerics_*` exercises the closed form on a synthetic anchor
grid; `numerics_*_solver` integrates the underlying ODE (Euler /
midpoint-RK2 / RK4 cascade for pillars 1, 2, 4; symplectic
leapfrog/Verlet harmonic oscillator for pillar 3) and verifies
convergence orders 1 / 2 / 4 by step-halving.

**T3** (parity) is the archival empirical contact: it ties the
prediction to *external* published numbers (Chinchilla / GPT-3 /
Llama-2 / PaLM for cost; HELM-Core for alignment; Olsson / Cunningham
/ Bricken / Anthropic-2024 SAE motif counts for interpret).

A failure in any T2 file alone is a closed-form bug; a failure in any
T3 file alone is an empirical-contact drift. Both classes are caught
by independent layers, which is what `closure_pct = 100%` (3/3 tiers)
buys.

**Cross-cutters (4 files):**

| Verifier                              | What it checks                                                      |
|---------------------------------------|---------------------------------------------------------------------|
| `lattice_check.hexa`                  | 24 lattice algebraic invariants (σ·φ = n·τ = J₂ = 24, σ²=144, …)    |
| `cross_doc_audit.hexa`                | Taxonomy + falsifier-prefix + provenance + master identity across docs |
| `numerics_cross_pillar.hexa`          | Cross-pillar identities (F1×F2 composite, F3×F4 product, coupled ODE) |
| `numerics_lattice_arithmetic.hexa`    | math_pure stability floor (associativity, log/exp/pow round-trips)  |

**Meta (3 files):**

| Verifier                          | What it does                                                       |
|-----------------------------------|--------------------------------------------------------------------|
| `falsifier_check.hexa`            | Closure tracker — per-pillar layer presence + sat-1 verdict gate   |
| `lint_numerics.hexa`              | Recipe §4 invariants 1-5 over every `numerics_*.hexa`              |
| `saturation_check.hexa`           | Aggregate self-stop signal — re-runs 6 closure components          |

```bash
hexa-codex verify all                              # full sweep, sat-1 verdict
hexa-codex verify saturation-check                 # one-shot sat-1 marker
hexa-codex verify falsifier-check                  # closure tracker
hexa-codex verify lint-numerics                    # recipe §4 invariants
hexa-codex verify numerics-train_cost-solver       # one specific layer
RESOURCE_LOCAL_HEXA=1 hexa run verify/saturation_check.hexa
# → __HEXA_CODEX_SATURATION_CHECK__ PASS  (when at sat-1)
```

Each script also runs standalone:
`RESOURCE_LOCAL_HEXA=1 hexa run verify/<name>.hexa`. The
`RESOURCE_LOCAL_HEXA=1` env routes the local interpreter
(`~/.hx/packages/hexa/hexa.real`) instead of the `hexa-r ubu-1`
remote-routing wrapper that ships with the resource toolkit.

### tests/ — 24 .hexa regression wrappers + 83 pytest auto

Each `verify/*.hexa` script has a companion `tests/test_*.hexa`
wrapper that re-runs the verifier, greps the sentinel, and exits 0/1.
`tests/test_all.hexa` aggregates all 24 wrappers; the legacy 83 pytest
auto-cases continue to cover the spec / inventory / group / lattice
side.

```bash
RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT="$PWD" \
    ~/.hx/packages/hexa/hexa.real run tests/test_all.hexa   # 24/24 PASS
python3 -m pytest tests/ -m auto                            # 83 PASS
```

### cli/hexa-codex.hexa — extended subcommands

```bash
hexa-codex verify [target]       # any .hexa verifier; e.g. saturation-check, falsifier-check
hexa-codex calc <metric>         # train_cost / infer_cost / alignment / interpret / quality_scale
hexa-codex inventory             # 17-verb spec presence + canonical-header audit
hexa-codex lattice [n]           # n=k lattice explorer
hexa-codex test [mark]           # pytest tests/ -m {auto|hexa}
hexa-codex status                # one-shot health JSON
```

---

## Reference annexes

Cross-cutting AI/governance atlases absorbed from `canon/papers/`:

| Paper | What it does | Maturity |
|-------|--------------|----------|
| [`papers/n6-ai-17-techniques-experimental-paper.md`](papers/n6-ai-17-techniques-experimental-paper.md) | Maps **hexa-codex's exact 17 verbs** onto σ·φ=n·τ=24 coordinate space | atlas.n6 **192/192 EXACT** |
| [`papers/n6-ai-techniques-68-integrated-paper.md`](papers/n6-ai-techniques-68-integrated-paper.md) | Wider **68-technique** atlas; situates 17 verbs in broader landscape | extension |
| [`papers/n6-ai-ethics-governance-paper.md`](papers/n6-ai-ethics-governance-paper.md) | **AI ethics + governance** σ·φ=24 overlay (P4) | atlas.n6 0/24, MATURITY=LOW |
| [`papers/n6-governance-safety-urban-paper.md`](papers/n6-governance-safety-urban-paper.md) | **Governance + safety + urban planning** overlay (P5) | atlas.n6 **58/58 EXACT, MATURITY=HIGH** |

These are reference annexes — they coordinatize the 17 verbs onto the
n=6 lattice without introducing new verbs or falsifiers. See
[`papers/README.md`](papers/README.md) for the full relationship + per-verb
deep-dive sub-files.

### consciousness deep-dive (BT-19 falsifier-in-action)

| File | Concern |
|------|---------|
| [`consciousness/measurement-protocol.md`](consciousness/measurement-protocol.md) | BT-19 α_IIT·α_GWT=1 reproducible EEG/fMRI protocol (PAPER-P8-2) |
| [`consciousness/red-team-failure.md`](consciousness/red-team-failure.md) | BT-19 red-team refutation — verdict **MISS**, [7?] CONJECTURE → [5] downgrade |

These 2 files demonstrate the falsifier-preregister discipline at work: a
CONJECTURE was preregistered, independently red-teamed, and downgraded.
This is the *reason* hexa-codex calls itself a falsifier-preregister
library, not just a spec catalog.

---

## Formal substrate (Lean 4)

The σ-invariant cardinality at the heart of every F-CODEX-N falsifier is
**kernel-checked** in Lean 4:

| File | Theorem | Status |
|------|---------|--------|
| [`formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean`](formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean) | `theorem sigma_lattice_card : sigma 6 = 12 := rfl` | **PROVEN** (no sorry) — F-CL-FORMAL-1 |
| [`formal/lean4/N6/InvariantLattice/Sigma.lean`](formal/lean4/N6/InvariantLattice/Sigma.lean) | `def sigma (n : Nat) : Nat` (computable) | DEFINITION |

Implications for hexa-codex falsifiers:

- F-CODEX-1 (training_cost ∝ N^**24**) ← σ(6)·φ(6) = 24, where σ(6) = 12 is **Lean-proven**
- F-CODEX-2 (inference_cost ∝ context^**4**) ← τ(6) = 4 (corollary of divisor count)
- F-CODEX-3 (alignment over **12** axes) ← σ(6) = 12 directly (this proof)
- F-CODEX-4 (motif count = **10**) ← σ(6) − φ(6) = 10 (corollary)

`verify/n6_arithmetic.py` is the runtime witness; `SigmaLatticeCard.lean`
is the mathematical bedrock. Lean 4 toolchain is **not required** to use
hexa-codex — the formal proof is a reference annex. See
[`formal/README.md`](formal/README.md) for build instructions.

---

## Status

**SPEC_CATALOG + RUNNABLE_SURFACE at 100% closure (recipe §7.2 sat-1).
+ `lm_foundry/` — code-LLM at 94.29% Mk.I strict (r39 GA, frozen) +
v0.5.x orchestration runtime (r44–r62) production-ready.**

> 17-verb AI 지식 substrate (4 그룹: safety + economics + ops + substrate)
> + verify/ + tests/ + build/ + docs/ runnable surface
> + `lm_foundry/` (hexa-forge 흡수, 2026-05-13 — 도메인 LLM 학습 파이프라인 +
> 런타임; code-LLM GA 94.29% Mk.I strict r39 frozen + v0.5.x 오케스트레이션
> 런타임 r44–r62 production-ready, bio-LLM 레시피).
> Recipe §7.2 sat-1 saturation reached — all 4 F-CODEX-1..4 closed at
> recipe §3 closure_pct = 100% (T1 + T2 + T3 ✓ each), via 23 .hexa
> verifiers + 24 regression wrappers + 3 meta verifiers. T4 (live
> hardware / Stage-1+) is recipe §9 territory and out of loop scope.

Translation: this repo is (1) a *library* of AI specs and (2) a runnable
verification surface at recipe §7.2 sat-1 = 100% closure under the
§3 ladder. The `cli/hexa-codex.hexa` dispatcher routes both — verb
spec reads + .hexa-native verifiers / calculators / tests (legacy
Python verify/ kept as a parallel CI path). The heavy-lift per-verb
T4 live-hardware / Stage-1+ pipelines (live FLOP/loss measurements,
KV-cache profiles, HELM-Core composites, SAE feature counts) sit in
recipe §9 territory and land per the [release ladder](#release-ladder)
v1.1.0..v2.0.0.

What works at 100% closure (sat-1):

- 17 verb specs land on disk under their group-named directories.
- `hexa-codex list` prints the full 4-group table.
- `hexa-codex <verb>` prints the spec path + first 20 lines.
- `hexa-codex selftest` confirms 17/17 spec presence.
- **`hexa-codex verify saturation-check`** re-runs the 6 closure
  components and emits the canonical recipe §7.3 self-stop sentinel
  `__HEXA_CODEX_RSC_SATURATED__ STOP` plus the sat-1 marker
  `__HEXA_CODEX_SATURATION_CHECK__ PASS`.
- **`hexa-codex verify falsifier-check`** runs the closure tracker —
  per-pillar T1/T2/T3 tier presence, cross-cutter row, recipe §3
  closure_pct = 100% verdict.
- **`hexa-codex verify <pillar>-<layer>`** runs any single layer (e.g.
  `numerics-train_cost-solver`).
- **`make -C build sat1`** is the friendly CI gate.
- **`make -C build everything`** = ci (Python legacy) + 24-wrapper .hexa
  regression + sat-1 closure + selftest.
- **σ(6) = 12 mechanically proven** in Lean 4 (`SigmaLatticeCard.lean`,
  `:= rfl`, no `sorry`); cross-checked at runtime by
  `verify/lattice_check.hexa` and `verify/numerics_lattice_arithmetic.hexa`.
- See **[`docs/numerics_methodology.md`](docs/numerics_methodology.md)**
  for the closure-depth narrative (T1/T2/T3 taxonomy, why each T2 layer,
  why pillar 3 uses symplectic leapfrog, math_pure rationale, sat-2
  outlook).
- See **[`docs/closure_status.md`](docs/closure_status.md)** for the
  static per-pillar closure snapshot and **[`docs/quick_reference.md`](docs/quick_reference.md)**
  for the operator command list.

What is **out of scope** at 100% closure (sat-1):

- Per-verb **T4 live-hardware / Stage-1+** pipelines (recipe §9 — out
  of loop scope; closure_pct already at 100% on the §3 T1/T2/T3
  ladder).
- Model training, inference SaaS, or RLHF labeling production pipeline.
- Any regulatory, alignment, or capability claim — these specs are
  preregistered hypotheses, not validated results.

---

## Install

```bash
# 1. Install hexa-lang (gives you `hexa` + `hx` package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/dancinlab/hexa-lang/main/install.sh)"

# 2. Install hexa-codex
hx install hexa-codex
```

## Run

```bash
hexa-codex list                    # 17-verb table grouped by 4 groups
hexa-codex selftest                # 17-verb spec presence sweep
hexa-codex verify [check]          # unified verifier dispatcher (lattice/cross-doc/train_cost/infer_cost/n6/inventory/group/release/falsifiers/reference/all)
hexa-codex inventory               # 17-verb spec inventory + canonical-header audit
hexa-codex lattice [n]             # n=k lattice explorer (σ·φ vs n·τ identity)
hexa-codex calc <metric>           # F-CODEX-1..4 calculators (train_cost/infer_cost/alignment/interpret/quality_scale)
hexa-codex test [mark]             # pytest tests/ (auto|hexa)
hexa-codex status                  # one-shot verifier health summary
hexa-codex <verb>                  # read a verb spec (alignment/safety/welfare/.../causal — see `list`)
hexa-codex version                 # print version
hexa-codex help                    # full --help (subcommands + flags + env)
```

---

## Cross-link

Sister repos in the `dancinlab` HEXA family:

### Cognitive substrate rollups (sister-libraries)

- 👁️ [dancinlab/hexa-senses](https://github.com/dancinlab/hexa-senses) —
  **5-verb sensory substrate** (dream + ear + empath + olfact + voice).
  voice is formulaic-only, learned TTS FORBIDDEN.
- 🧠 [dancinlab/hexa-mind](https://github.com/dancinlab/hexa-mind) —
  **7-verb mental substrate** (mind + neuro + oracle + hexa_telepathy +
  telepathy + mind_upload + superpowers). 4/7 SPECULATIVE (preregister honesty).

### Domain-specific siblings

- 👻 [dancinlab/anima](https://github.com/dancinlab/anima) —
  consciousness / soul cousin (phenomenal grounding adjacent to `consciousness`).
- 🧬 [dancinlab/hexa-brain](https://github.com/dancinlab/hexa-brain) —
  BCI sister (read-side neural substrate counterpart).
- ⚖️ [dancinlab/honesty-monitor](https://github.com/dancinlab/honesty-monitor) —
  AI honesty-bit falsifier sister (write-side validator for the SAFETY group).
- 🌱 [dancinlab/hexa-bio](https://github.com/dancinlab/hexa-bio) —
  4-verb molecular toolkit (same HEXA-family pattern, biology domain).
- 🔨 [`lm_foundry/`](lm_foundry/README.md) **(in this repo)** —
  domain-LLM training pipeline, absorbed from the retired `hexa-forge`
  repo on 2026-05-13. `hexa-codex` was forge's sister (serving side);
  now one repo. See the `lm_foundry/` section above.

The 17 + 5 + 7 = **29 verbs across cognitive sister-libraries** all derive
from the n=6 master identity (σ·φ = n·τ = 24). hexa-codex covers AI
*knowledge*; hexa-senses covers AI *senses*; hexa-mind covers AI *mental ops*.

Upstream concept SSOT: `canon/domains/cognitive/` (declarative
sources for all 17 hexa-codex verbs + 5 hexa-senses verbs + 7 hexa-mind
verbs).

---

## License

MIT. See [LICENSE](LICENSE).
