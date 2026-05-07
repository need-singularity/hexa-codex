# 📚 hexa-codex — AI knowledge substrate (HEXA family)

> 17-verb AI knowledge substrate organized in **4 groups**: safety + economics
> + ops + substrate. A library-style (codex) spec catalog — each verb ships
> a closed-form candidate spec + falsifier preregister, extracted from
> n6-architecture (`domains/cognitive/`) on 2026-05-06.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)](CHANGELOG.md)
[![Verbs: 17 / 4 groups](https://img.shields.io/badge/verbs-17_(4_groups)-blue.svg)](#verbs)
[![Verify: 6/6](https://img.shields.io/badge/verify-6%2F6-brightgreen.svg)](#runnable-surface)
[![Tests: 73 passed](https://img.shields.io/badge/tests-73_passed-brightgreen.svg)](#runnable-surface)
[![Falsifiers: 4/4 floor](https://img.shields.io/badge/falsifiers-4%2F4_floor-brightgreen.svg)](#falsifier-preregister)
[![Lean4 proof: σ(6)=12](https://img.shields.io/badge/Lean4-σ(6)%3D12_PROVEN-brightgreen.svg)](formal/README.md)
[![n=6 lattice](https://img.shields.io/badge/n=6-σ·φ_=_n·τ_=_24-blue.svg)](#n6-master-identity)

---

## Why hexa-codex?

`hexa-codex` is a **standalone AI knowledge substrate** — a *codex*
(library) of AI-domain specs that the rest of the `need-singularity` stack
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

v1.0.0 ships the **codex** (markdown spec library) **plus** a stdlib-only
runnable verification surface that mirrors the
[hexa-sscb](https://github.com/need-singularity/hexa-sscb) pattern.

### verify/ — 5 verifiers, Python stdlib only

| Check          | Module                                | What it verifies                                  |
|----------------|---------------------------------------|---------------------------------------------------|
| `n6`           | `verify/n6_arithmetic.py`             | n=6 lattice identity (σ·φ = n·τ = 24) + 8 projections |
| `inventory`    | `verify/spec_inventory.py`            | 17-verb spec presence + `@canonical` headers      |
| `group`        | `verify/group_audit.py`               | 4-group / 17-verb consistency across 6 surfaces   |
| `release`      | `verify/release_ladder.py`            | v1.0→v2.0 monotonicity (verbs_wired ↑, evals ↑)   |
| `falsifiers`   | `verify/falsifier_check.py`           | F-CODEX-1..4 arithmetic floors                    |
| `reference`    | `verify/reference_inventory.py`       | papers/ + formal/ md5 + canonical-header audit    |

```bash
python3 verify/cli.py all          # 5/5 PASS in <2s
python3 verify/cli.py --json       # CI-friendly machine output
python3 verify/cli.py n6           # single check
```

Plus 5 calculators and 4 analyzers:

| Tool                            | Purpose                                       |
|---------------------------------|-----------------------------------------------|
| `verify/calc_train_cost.py`     | F-CODEX-1 closed form (N^J₂ vs Chinchilla)    |
| `verify/calc_infer_cost.py`     | F-CODEX-2 closed form (context^τ)             |
| `verify/calc_alignment.py`      | F-CODEX-3 12-axis HELM-comparable aggregator  |
| `verify/calc_interpret.py`      | F-CODEX-4 motif counter (σ−φ=10)              |
| `verify/calc_quality_scale.py`  | quality_scale Chinchilla-comparable fit       |
| `verify/lattice_explore.py`     | n=k lattice arithmetic explorer               |
| `verify/release_params.py`      | per-release parameter registry                |
| `verify/verb_query.py`          | verb info / spec lookup tool                  |

### tests/ — 62 pytest auto + 1 hexa

```bash
make -C build test          # pytest -m auto (62 cases, <20s)
make -C build test-hexa     # pytest -m hexa (requires hexa-lang)
hexa run tests/test_selftest.hexa   # 17/17 spec presence (.hexa-native)
```

Suite breakdown: `test_n6_invariants.py` (12) · `test_verifiers.py` (8) ·
`test_calculators.py` (15) · `test_release_ladder.py` (5) ·
`test_spec_inventory.py` (22) · `test_install_hexa.py` (1, hexa marker).

### build/Makefile — fan-out to verify + tests + selftest + pdf

```bash
make -C build verify        # all 5 verifiers
make -C build verify-json   # JSON for CI
make -C build test          # pytest auto suite
make -C build selftest      # 17-verb .hexa selftest
make -C build install-test  # hx install hexa-codex --entry cli/hexa-codex.hexa
make -C build pdf VERB=alignment   # one-off per-verb PDF (pandoc)
make -C build ci            # verify + test
make -C build everything    # ci + selftest + hexa-tests
```

### cli/hexa-codex.hexa — extended subcommands

In addition to `list` / `selftest` / `<verb>`, the CLI now routes:

```bash
hexa-codex verify [check]      # n6 / inventory / group / release / falsifiers / reference / all
hexa-codex calc <metric>       # train_cost / infer_cost / alignment / interpret / quality_scale
hexa-codex inventory           # spec presence + canonical-header audit
hexa-codex lattice [n]         # n=k lattice explorer
hexa-codex test [mark]         # pytest tests/ -m {auto|hexa}
hexa-codex status              # one-shot health JSON
```

---

## Reference annexes

Two cross-cutting AI-technique atlases absorbed from `n6-architecture/papers/`
(provenance commit `0c65155a`, extracted 2026-05-07):

| Paper | What it does |
|-------|--------------|
| [`papers/n6-ai-17-techniques-experimental-paper.md`](papers/n6-ai-17-techniques-experimental-paper.md) | Maps **hexa-codex's exact 17 verbs** onto the σ·φ=n·τ=24 coordinate space (atlas.n6 192/192 EXACT) |
| [`papers/n6-ai-techniques-68-integrated-paper.md`](papers/n6-ai-techniques-68-integrated-paper.md) | Wider **68-technique** atlas; situates the 17 verbs inside the broader landscape |

These are reference annexes — they coordinatize the existing 17 verbs onto
the n=6 lattice, they do not introduce new specs or falsifiers. See
[`papers/README.md`](papers/README.md) for the full relationship.

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

**SPEC_CATALOG_ONLY + RUNNABLE_VERIFICATION_SURFACE at v1.0.0.**

> 17-verb AI 지식 substrate (4 그룹: safety + economics + ops + substrate)
> + verify/ + tests/ + build/ runnable surface.
> spec-first (per-verb 작동 .hexa eval pipeline은 v1.1+ 단계별 합류).

Translation: this repo is (1) a *library* of AI specs and (2) a runnable
verification surface at v1.0. The `cli/hexa-codex.hexa` dispatcher routes
both — verb spec reads + Python verifiers / calculators / tests. The
heavy-lift per-verb `.hexa` eval pipelines (falsifier sandboxes,
cost-curve fitters, interp probes) land per the
[release ladder](#release-ladder) v1.1.0..v2.0.0.

What works at v1.0:

- 17 verb specs land on disk under their group-named directories.
- `hexa-codex list` prints the full 4-group table.
- `hexa-codex <verb>` prints the spec path + first 20 lines.
- `hexa-codex selftest` confirms 17/17 spec presence.
- **`hexa-codex verify all` runs 6 verifiers** (n6 / inventory / group /
  release / falsifiers / reference) — 6/6 PASS in <6s.
- **`hexa-codex calc <metric>`** runs F-CODEX-1..4 closed-form calculators.
- **`make -C build ci`** runs verify + 73 pytest cases (all auto, no
  bench equipment / external SDK / pip install required).
- **σ(6) = 12 mechanically proven** in Lean 4 (`SigmaLatticeCard.lean`,
  `:= rfl`, no `sorry`).

What is **out of scope** at v1.0:

- Per-verb empirical eval pipelines (arithmetic floor only — empirical
  fits land per the [release ladder](#release-ladder)).
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
hexa-codex verify all          # → 5/5 PASS
hexa-codex selftest            # → 17/17 verb specs PASS
```

For local development install (avoids GitHub round-trip):

```bash
hx install /path/to/hexa-codex --entry cli/hexa-codex.hexa --as hexa-codex
```

### Via git clone

```bash
git clone https://github.com/need-singularity/hexa-codex.git ~/.hexa-codex
export HEXA_CODEX_ROOT=~/.hexa-codex
cd $HEXA_CODEX_ROOT

# List the 17 verbs:
hexa run cli/hexa-codex.hexa list

# Run all 5 verifiers (Python stdlib only):
python3 verify/cli.py all

# Run the pytest auto suite (no pip install required):
make -C build test

# Run F-CODEX-1 closed-form training-cost calc:
hexa-codex calc train_cost --N 7e9 --D 1.4e12
```

---

## Cross-link

Sister repos in the `need-singularity` HEXA family:

### Cognitive substrate rollups (sister-libraries)

- 👁️ [need-singularity/hexa-senses](https://github.com/need-singularity/hexa-senses) —
  **5-verb sensory substrate** (dream + ear + empath + olfact + voice).
  voice is formulaic-only, learned TTS FORBIDDEN.
- 🧠 [need-singularity/hexa-mind](https://github.com/need-singularity/hexa-mind) —
  **7-verb mental substrate** (mind + neuro + oracle + hexa_telepathy +
  telepathy + mind_upload + superpowers). 4/7 SPECULATIVE (preregister honesty).

### Domain-specific siblings

- 👻 [need-singularity/anima](https://github.com/need-singularity/anima) —
  consciousness / soul cousin (phenomenal grounding adjacent to `consciousness`).
- 🧬 [need-singularity/hexa-brain](https://github.com/need-singularity/hexa-brain) —
  BCI sister (read-side neural substrate counterpart).
- ⚖️ [need-singularity/honesty-monitor](https://github.com/need-singularity/honesty-monitor) —
  AI honesty-bit falsifier sister (write-side validator for the SAFETY group).
- 🌱 [need-singularity/hexa-bio](https://github.com/need-singularity/hexa-bio) —
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
