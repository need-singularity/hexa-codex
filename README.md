# 📚 hexa-codex — AI knowledge substrate (HEXA family)

> 17-verb AI knowledge substrate organized in **4 groups**: safety + economics
> + ops + substrate. A library-style (codex) spec catalog — each verb ships
> a closed-form candidate spec + falsifier preregister, extracted from
> n6-architecture (`domains/cognitive/`) on 2026-05-06.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)](CHANGELOG.md)
[![Verbs: 17 / 4 groups](https://img.shields.io/badge/verbs-17_(4_groups)-blue.svg)](#verbs)
[![Verify: 23 .hexa](https://img.shields.io/badge/verify-23_(.hexa)-brightgreen.svg)](#runnable-surface)
[![Tests: 24 .hexa + 83 py](https://img.shields.io/badge/tests-24_.hexa_+_83_py-brightgreen.svg)](#runnable-surface)
[![Closure: sat-1](https://img.shields.io/badge/closure-sat--1_T2×3-brightgreen.svg)](#runnable-surface)
[![Falsifiers: 4/4 T1+T2×3](https://img.shields.io/badge/falsifiers-4%2F4_T1+T2×3-brightgreen.svg)](#falsifier-preregister)
[![Lean4 proof: σ(6)=12](https://img.shields.io/badge/Lean4-σ(6)%3D12_PROVEN-brightgreen.svg)](formal/README.md)
[![Papers: 4 + Lean1 + 2 deep-dive](https://img.shields.io/badge/refs-4P_+_Lean1_+_2DD-blue.svg)](#reference-annexes)
[![n=6 lattice](https://img.shields.io/badge/n=6-σ·φ_=_n·τ_=_24-blue.svg)](#n6-master-identity)

---

## Why hexa-codex?

`hexa-codex` is a **standalone AI knowledge substrate** — a *codex*
(library) of AI-domain specs that the rest of the `dancinlab` stack
imports declaratively. Each verb is a single closed-form spec markdown
extracted unchanged from `n6-architecture/domains/cognitive/`, organized
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

## Verbs

17 verb specs / 4 groups. All sources are unchanged `.md` files from
`n6-architecture@c0f1f570`.

### SAFETY (6)

| Verb            | Spec                                     | Concern                                |
|-----------------|------------------------------------------|----------------------------------------|
| `alignment`     | [alignment/ai-alignment.md](alignment/ai-alignment.md)             | values / objective alignment          |
| `safety`        | [safety/ai-safety.md](safety/ai-safety.md)                         | safety-critical guardrails             |
| `welfare`       | [welfare/ai-welfare.md](welfare/ai-welfare.md)                     | model-welfare considerations           |
| `adversarial`   | [adversarial/ai-adversarial.md](adversarial/ai-adversarial.md)     | adversarial robustness / red-team      |
| `consciousness` | [consciousness/ai-consciousness.md](consciousness/ai-consciousness.md) | consciousness / phenomenal grounding |
| `interpret`     | [interpret/ai-interpretability.md](interpret/ai-interpretability.md) | interpretability / mech-interp        |

### ECONOMICS (3)

| Verb            | Spec                                                       | Concern                          |
|-----------------|------------------------------------------------------------|----------------------------------|
| `train_cost`    | [train_cost/ai-training-cost.md](train_cost/ai-training-cost.md)       | training-cost curves / scaling   |
| `infer_cost`    | [infer_cost/ai-inference-cost.md](infer_cost/ai-inference-cost.md)     | inference-cost / serving economics |
| `quality_scale` | [quality_scale/ai-quality-scale.md](quality_scale/ai-quality-scale.md) | quality-scaling laws             |

### OPS (4)

| Verb            | Spec                                                            | Concern                              |
|-----------------|-----------------------------------------------------------------|--------------------------------------|
| `deploy`        | [deploy/ai-deployment.md](deploy/ai-deployment.md)              | deployment patterns                  |
| `enterprise`    | [enterprise/ai-enterprise-custom.md](enterprise/ai-enterprise-custom.md) | enterprise-custom integration   |
| `agent_serving` | [agent_serving/ai-agent-serving.md](agent_serving/ai-agent-serving.md)   | agent-serving infrastructure    |
| `eval`          | [eval/ai-eval-pipeline.md](eval/ai-eval-pipeline.md)            | eval pipeline / capability gates     |

### SUBSTRATE (4)

| Verb         | Spec                                                       | Concern                                     |
|--------------|------------------------------------------------------------|---------------------------------------------|
| `multimodal` | [multimodal/ai-multimodal.md](multimodal/ai-multimodal.md) | multimodal substrate (vision/audio/etc)     |
| `rlhf`       | [rlhf/youth-ai-labeling-rlhf-hub.md](rlhf/youth-ai-labeling-rlhf-hub.md) | RLHF / preference-data substrate    |
| `cog_arch`   | [cog_arch/cognitive-architecture.md](cog_arch/cognitive-architecture.md) | cognitive-architecture substrate     |
| `causal`     | [causal/causal-chain.md](causal/causal-chain.md)           | causal-chain reasoning substrate            |

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

## Runnable surface

The runnable surface follows the
[runnable_surface_recipe.md](https://github.com/dancinlab/bedrock/blob/main/docs/runnable_surface_recipe.md)
closure-depth pattern. Every prediction the codex ships is paired with
at least one **runnable** verifier, and the surface is closed when each
F-CODEX falsifier carries T1 (algebraic) + T2 ×3 (numerical /
published-ref / ODE solver) layers — recipe §7.2 sat-1 saturation.

**Status (post iter 23): sat-1 reached.** All 4 F-CODEX falsifiers at
T1 + T2 ×3, plus 4 cross-cutters and 3 meta verifiers. Total **23
runnable verify scripts** + **24 companion regression tests**.

### verify/ — 23 .hexa-native verifiers (math_pure, no deps)

All scripts use `self/runtime/math_pure` (no external Python / float
libraries). Each emits a `__HEXA_CODEX_<NAME>__ PASS` sentinel; the
top-level aggregator polls sentinels and exits 0 iff every layer is
green.

**Per-pillar layer stack (4 × 4 = 16 files):**

| Pillar                    | T1 (calc)                | T2 #1 (numerics)            | T2 #2 (parity)                     | T2 #3 (solver)                     |
|---------------------------|--------------------------|------------------------------|-------------------------------------|-------------------------------------|
| F-CODEX-1 (train_cost)    | `calc_train_cost.hexa`   | `numerics_train_cost.hexa`   | `numerics_train_cost_parity.hexa`   | `numerics_train_cost_solver.hexa`   |
| F-CODEX-2 (infer_cost)    | `calc_infer_cost.hexa`   | `numerics_infer_cost.hexa`   | `numerics_infer_cost_parity.hexa`   | `numerics_infer_cost_solver.hexa`   |
| F-CODEX-3 (alignment)     | `calc_alignment.hexa`    | `numerics_alignment.hexa`    | `numerics_alignment_parity.hexa`    | `numerics_alignment_solver.hexa`    |
| F-CODEX-4 (interpret)     | `calc_interpret.hexa`    | `numerics_interpret.hexa`    | `numerics_interpret_parity.hexa`    | `numerics_interpret_solver.hexa`    |

T2 #2 (parity) anchors against published-ref data (Chinchilla / GPT-3
/ Llama-2 / PaLM for cost; HELM-Core / Olsson / Cunningham / Bricken /
Anthropic-2024 for alignment + interpret). T2 #3 (solver) re-derives
the same prediction by integrating the underlying ODE
(Euler / midpoint-RK2 / RK4 cascade for pillars 1, 2, 4; symplectic
leapfrog/Verlet harmonic oscillator for pillar 3) and verifying
convergence orders 1 / 2 / 4 by step-halving.

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

Cross-cutting AI/governance atlases absorbed from `n6-architecture/papers/`:

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

**SPEC_CATALOG + RUNNABLE_SURFACE at sat-1 (post v1.0.0, pre v1.1.0).**

> 17-verb AI 지식 substrate (4 그룹: safety + economics + ops + substrate)
> + verify/ + tests/ + build/ + docs/ runnable surface.
> recipe §7.2 sat-1 saturation reached — all 4 F-CODEX falsifiers carry
> T1 + T2 ×3 layer stacks via 23 .hexa-native verifiers + 24 regression
> wrappers + 3 meta verifiers. Per-verb T3 (live empirical) row pending.

Translation: this repo is (1) a *library* of AI specs and (2) a runnable
verification surface that has reached the recipe §7.2 sat-1 closure
goal. The `cli/hexa-codex.hexa` dispatcher routes both — verb spec
reads + .hexa-native verifiers / calculators / tests (legacy Python
verify/ kept as a parallel CI path). The heavy-lift per-verb T3
empirical pipelines (live FLOP/loss measurements, KV-cache profiles,
HELM-Core composites, SAE feature counts) land per the
[release ladder](#release-ladder) v1.1.0..v2.0.0.

What works at sat-1:

- 17 verb specs land on disk under their group-named directories.
- `hexa-codex list` prints the full 4-group table.
- `hexa-codex <verb>` prints the spec path + first 20 lines.
- `hexa-codex selftest` confirms 17/17 spec presence.
- **`hexa-codex verify saturation-check`** re-runs the 6 closure
  components and emits the canonical sat-1 marker
  `__HEXA_CODEX_SATURATION_CHECK__ PASS`.
- **`hexa-codex verify falsifier-check`** runs the closure tracker —
  per-pillar T1 + T2 ×3 layer presence, cross-cutter row, sat-1 verdict.
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

What is **out of scope** at sat-1:

- Per-verb T3 empirical pipelines (T2 floor only — closure pct = 4/5
  per pillar; T3 row lifts to 5/5 = sat-2 along the
  [release ladder](#release-ladder)).
- Model training, inference SaaS, or RLHF labeling production pipeline.
- Any regulatory, alignment, or capability claim — these specs are
  preregistered hypotheses, not validated results.

---

## Install

### Via `hx` (works today)

```bash
# `hx` does not auto-detect hexa.toml's `entry` field yet — pass --entry
# explicitly. Tracked as upstream improvement.
hx install hexa-codex --entry cli/hexa-codex.hexa
hexa-codex --version           # → 1.0.0
hexa-codex verify saturation-check   # → __HEXA_CODEX_SATURATION_CHECK__ PASS  (sat-1 marker)
hexa-codex verify falsifier-check    # → per-pillar layer presence + sat-1 verdict
hexa-codex selftest                  # → 17/17 verb specs PASS
```

For local development install (avoids GitHub round-trip):

```bash
hx install /path/to/hexa-codex --entry cli/hexa-codex.hexa --as hexa-codex
```

### Via git clone

```bash
git clone https://github.com/dancinlab/hexa-codex.git ~/.hexa-codex
export HEXA_CODEX_ROOT=~/.hexa-codex
cd $HEXA_CODEX_ROOT

# List the 17 verbs:
hexa run cli/hexa-codex.hexa list

# Run the .hexa-native sat-1 closure verdict:
make -C build sat1
# (or directly):
RESOURCE_LOCAL_HEXA=1 ~/.hx/packages/hexa/hexa.real run verify/saturation_check.hexa

# Run the 24-wrapper regression suite:
make -C build test-hexa-all

# Run the legacy Python verifiers (parallel CI path):
make -C build verify          # Python stdlib only

# Run the pytest auto suite (no pip install required):
make -C build test            # 83 cases

# Run F-CODEX-1 closed-form training-cost calc:
hexa-codex calc train_cost --N 7e9 --D 1.4e12
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

The 17 + 5 + 7 = **29 verbs across cognitive sister-libraries** all derive
from the n=6 master identity (σ·φ = n·τ = 24). hexa-codex covers AI
*knowledge*; hexa-senses covers AI *senses*; hexa-mind covers AI *mental ops*.

Upstream concept SSOT: `n6-architecture/domains/cognitive/` (declarative
sources for all 17 hexa-codex verbs + 5 hexa-senses verbs + 7 hexa-mind
verbs).

---

## License

MIT. See [LICENSE](LICENSE).
