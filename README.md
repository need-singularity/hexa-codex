# hexa-codex — AI knowledge substrate (HEXA family) 📚

> 17-verb AI knowledge substrate organized in **4 groups**: safety + economics
> + ops + substrate. A library-style (codex) spec catalog — each verb ships
> a closed-form candidate spec + falsifier preregister, extracted from
> n6-architecture (`domains/cognitive/`) on 2026-05-06.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)](CHANGELOG.md)
[![Verbs: 17 / 4 groups](https://img.shields.io/badge/verbs-17_(4_groups)-blue.svg)](#verbs)
[![Status: spec-catalog](https://img.shields.io/badge/status-SPEC__CATALOG__ONLY-orange.svg)](#status)

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

## Status

**SPEC_CATALOG_ONLY at v1.0.0.**

> 17-verb AI 지식 substrate (4 그룹: safety + economics + ops + substrate).
> spec-first (작동 .hexa CLI TBD). 도서관(codex)식 spec catalog — 각 verb는
> closed-form 후보 + falsifier preregister.

Translation: this repo is a *library* of AI specs at v1.0. The `cli/hexa-codex.hexa`
dispatcher is a placeholder that prints verb-spec paths + a 20-line head; the
heavy-lift `.hexa` modules (per-verb falsifier sandboxes, cost-curve fitters,
interp probes, etc) are deferred to post-v1.0 cycles — same posture as
`hexa-bio` 3/4 stub axes (raw#10 honest C3).

What works at v1.0:

- 17 verb specs land on disk under their group-named directories.
- `hexa-codex list` prints the full 4-group table.
- `hexa-codex <verb>` prints the spec path + first 20 lines.
- `hexa-codex selftest` confirms 17/17 spec presence.

What is **out of scope** at v1.0:

- Per-verb falsifier sandboxes (no ODE / probe / fitter shipped).
- Model training, inference SaaS, or RLHF labeling production pipeline.
- Any regulatory, alignment, or capability claim — these specs are
  preregistered hypotheses, not validated results.

---

## Install

### Via `hx` (forthcoming)

```bash
hx install hexa-codex          # global, pulls latest from registry
hexa-codex --version           # → 1.0.0
```

### Via git clone (works today)

```bash
git clone https://github.com/need-singularity/hexa-codex.git ~/.hexa-codex
export HEXA_CODEX_ROOT=~/.hexa-codex
export PATH="$HEXA_CODEX_ROOT/cli:$PATH"

# List the 17 verbs:
hexa run $HEXA_CODEX_ROOT/cli/hexa-codex.hexa list

# Read a verb spec (path + head):
hexa run $HEXA_CODEX_ROOT/cli/hexa-codex.hexa alignment

# Verify all 17 verb specs are on disk:
hexa run $HEXA_CODEX_ROOT/cli/hexa-codex.hexa selftest
```

---

## Cross-link

Sister repos in the `need-singularity` HEXA family:

- [need-singularity/anima](https://github.com/need-singularity/anima) —
  consciousness / soul cousin (phenomenal grounding adjacent to `consciousness`).
- [need-singularity/hexa-brain](https://github.com/need-singularity/hexa-brain) —
  BCI sister (read-side neural substrate counterpart).
- [need-singularity/honesty-monitor](https://github.com/need-singularity/honesty-monitor) —
  AI honesty-bit falsifier sister (write-side validator for the SAFETY group).
- [need-singularity/hexa-bio](https://github.com/need-singularity/hexa-bio) —
  4-verb molecular toolkit (same HEXA-family pattern, biology domain).

Upstream concept SSOT: `n6-architecture/domains/cognitive/` (declarative
sources for all 17 verbs in this repo).

---

## License

MIT. See [LICENSE](LICENSE).
