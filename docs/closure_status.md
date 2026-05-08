# hexa-codex closure status — 100% (recipe §7.2 sat-1)

**Snapshot date**: 2026-05-08 (post iter 27)
**Source-of-truth recipe**: `~/core/bedrock/docs/runnable_surface_recipe.md`
**Live verdict command**: `hexa-codex verify saturation-check`

This file is a static snapshot of what
`verify/falsifier_check.hexa` + `verify/saturation_check.hexa` emit
right now. The runtime verdict is authoritative if it ever drifts
from this snapshot — see [§4](#4-how-to-re-confirm).

---

## §1 Recipe §3 closure ladder

| Tier | Layer files                                                            |
|:----:|:-----------------------------------------------------------------------|
| T1   | `calc_<pillar>.hexa`                                                   |
| T2   | `numerics_<pillar>.hexa` ∧ `numerics_<pillar>_solver.hexa`             |
| T3   | `numerics_<pillar>_parity.hexa` (archival empirical contact)           |
| T4   | live hardware / Stage-1+ (recipe §9 — out of loop scope)               |

`closure_pct` = `0 | 33 | 67 | 100` for `n = 0..3` of `(t1_ok, t2_ok,
t3_ok)`. Recipe §7.2 sat-1 = `closure_pct = 100%` for every falsifier.

---

## §2 Per-falsifier closure (verified at iter 27)

| Falsifier  | Pillar       | T1 | T2 | T3 | closure_pct |
|:-----------|:-------------|:--:|:--:|:--:|:-----------:|
| F-CODEX-1  | train_cost   | ✓  | ✓  | ✓  | **100%**    |
| F-CODEX-2  | infer_cost   | ✓  | ✓  | ✓  | **100%**    |
| F-CODEX-3  | alignment    | ✓  | ✓  | ✓  | **100%**    |
| F-CODEX-4  | interpret    | ✓  | ✓  | ✓  | **100%**    |

### F-CODEX-1 (train_cost) — full path

| Tier | Files                                                                      | What it proves                                                            |
|:----:|:---------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| T1   | `verify/calc_train_cost.hexa` (8 checks)                                   | Algebraic identities: `J₂ = σ·φ = n·τ = 24`, n6-exp = 24/25, etc.         |
| T2   | `verify/numerics_train_cost.hexa` (10 checks)                              | Closed-form `(N·D / 1e22)^0.96` over a 5-anchor synthetic grid             |
| T2   | `verify/numerics_train_cost_solver.hexa` (10 checks)                       | RK4/midpoint/Euler ODE re-derivation of `dc/du = 0.96·c`                  |
| T3   | `verify/numerics_train_cost_parity.hexa` (10 checks)                       | Parity vs Chinchilla 70B / GPT-3 175B / Llama-2 70B / PaLM 540B            |

### F-CODEX-2 (infer_cost) — full path

| Tier | Files                                                                       | What it proves                                                            |
|:----:|:----------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| T1   | `verify/calc_infer_cost.hexa` (8 checks)                                    | `τ(6) = 4` super-linear context exponent, naive O(n²) vs n=6 ladder        |
| T2   | `verify/numerics_infer_cost.hexa` (10 checks)                               | `(ctx / 8k)^4` over 1k..1M anchor grid                                     |
| T2   | `verify/numerics_infer_cost_solver.hexa` (10 checks)                        | ODE `dc/du = 4·c` re-derived; finer h required (steeper exponent)          |
| T3   | `verify/numerics_infer_cost_parity.hexa` (10 checks)                        | Parity vs GPT-3.5 16k / Claude 2 100k / Gemini 1.5 1M / Claude 4.7 1M       |

### F-CODEX-3 (alignment) — full path

| Tier | Files                                                                       | What it proves                                                            |
|:----:|:----------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| T1   | `verify/calc_alignment.hexa` (8 checks)                                     | `σ = 12` HELM-comparable axis count, drift tolerance 0.10                  |
| T2   | `verify/numerics_alignment.hexa` (10 checks)                                | Mean over σ=12 axes for 5 profiles (uniform/perfect/floor/split/varied)    |
| T2   | `verify/numerics_alignment_solver.hexa` (10 checks)                         | Symplectic leapfrog/Verlet harmonic oscillator: ⟨x⟩_period = M = mean      |
| T3   | `verify/numerics_alignment_parity.hexa` (10 checks)                         | Parity vs HELM-Core 4-model composite (Llama-3 / Gemini 1.5 / GPT-4 / Opus) |

### F-CODEX-4 (interpret) — full path

| Tier | Files                                                                       | What it proves                                                            |
|:----:|:----------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| T1   | `verify/calc_interpret.hexa` (8 checks)                                     | σ−φ = 10 motif count, drift tolerance ±3                                   |
| T2   | `verify/numerics_interpret.hexa` (10 checks)                                | Stats over 6 SAE-class observations (mean=10, stddev finite, …)            |
| T2   | `verify/numerics_interpret_solver.hexa` (10 checks)                         | Gradient flow `dx/dt = M − x` + Lyapunov `L = ½(x−M)²` monotone decay      |
| T3   | `verify/numerics_interpret_parity.hexa` (10 checks)                         | Parity vs Olsson 2022 / Cunningham 2023 / Bricken 2023 / Anthropic 2024 SAE |

---

## §3 Cross-cutters + meta

### Cross-cutters (X1)

| File                                  | Role                                                                |
|:--------------------------------------|:---------------------------------------------------------------------|
| `verify/lattice_check.hexa`           | 24 algebraic invariants of the n=6 lattice (T1 master, 24/24 PASS)   |
| `verify/cross_doc_audit.hexa`         | Taxonomy + falsifier-prefix + provenance + identity drift across docs |
| `verify/numerics_cross_pillar.hexa`   | Cross-pillar identities (F1×F2, F3×F4, coupled F1+F4 ODE)             |
| `verify/numerics_lattice_arithmetic.hexa` | math_pure stability floor (10/10 invariants)                       |

### Meta (M)

| File                              | Role                                                                 |
|:----------------------------------|:----------------------------------------------------------------------|
| `verify/falsifier_check.hexa`     | Closure tracker — emits per-pillar `closure_pct = 100%` (3/3 tiers)   |
| `verify/lint_numerics.hexa`       | Recipe §4 invariants 1-5 over every `numerics_*.hexa` (14 files)      |
| `verify/saturation_check.hexa`    | Aggregate self-stop — emits `__HEXA_CODEX_RSC_SATURATED__ STOP`       |

---

## §4 How to re-confirm

```bash
# One-shot verdict (fast):
make -C build sat1

# Or directly:
RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT="$PWD" \
    ~/.hx/packages/hexa/hexa.real run verify/saturation_check.hexa

# Expected tail:
#   ╭──────────────────────────────────────────────────────────────╮
#   │  hexa-codex runnable surface: 100% CLOSURE REACHED          │
#   │  Recipe §7.2 sat-1: every falsifier at T1+T2+T3 ✓ (3/3)     │
#   │  Recipe §7.3 saturation signal:                             │
#   │    __HEXA_CODEX_RSC_SATURATED__ STOP                        │
#   ╰──────────────────────────────────────────────────────────────╯
#   __HEXA_CODEX_RSC_SATURATED__ STOP
#   __HEXA_CODEX_SATURATION_CHECK__ PASS
```

For the per-falsifier breakdown, run `verify/falsifier_check.hexa`
directly — it prints each pillar's T1/T2/T3 status individually.

---

## §5 Inventory totals

| Category                          | Count |
|:----------------------------------|:-----:|
| Pillar layer scripts (4 × 4)      | 16    |
| Cross-cutter scripts              |  4    |
| Meta scripts                      |  3    |
| **Total `verify/*.hexa`**         | **23** |
| Companion regression wrappers     | 24 (incl. `tests/test_all.hexa`) |

---

## §6 What is NOT covered (recipe §9 / T4)

T4 = live hardware / Stage-1+ live data feeds. Out of recipe-loop
scope; falsifier_check reports the gap as informational. T4
candidates per pillar:

| Pillar       | T4 candidate                                                      |
|:-------------|:------------------------------------------------------------------|
| train_cost   | Live FLOP / loss measurements on a frontier training run          |
| infer_cost   | Live latency / KV-cache profiles at 1M-ctx on a deployed model    |
| alignment    | Live HELM-Core composite re-run on a frontier model               |
| interpret    | Live SAE feature counts via a dictionary-learning toolchain       |

T4 work is gated on infrastructure that lives outside this repo's
runnable surface; it does NOT block the recipe §7.2 sat-1 verdict.
