# hexa-codex numerics methodology — recipe §7.4 priority 13 narrative

**Status (post iter 23):** sat-1 saturation reached.
**Source-of-truth recipe:** `~/core/bedrock/docs/runnable_surface_recipe.md`.

This document explains *why* the runnable surface is structured the way
it is — it does not duplicate the verifier code, but maps each runnable
back to the closure-depth taxonomy and explains what that closure
*means* for the four F-CODEX falsifiers.

---

## §1 The closure-depth taxonomy

Every runnable in `verify/` belongs to one of three tiers:

| Tier | What it proves                                                              | Example file                          |
|:----:|:----------------------------------------------------------------------------|:--------------------------------------|
| T1   | Closed-form **algebraic** identity (integer arithmetic, no float)           | `calc_train_cost.hexa`                |
| T2   | Closed-form **numerical** evaluation under `math_pure` (float64, no deps)   | `numerics_train_cost.hexa`            |
| T3   | **Empirical** evidence — live measurement on a frontier-class system       | (TBD — Chinchilla / HELM / etc.)      |

A "stack" extends T2 horizontally: a falsifier with three T2 children
(one closed-form re-derivation, one published-ref parity, one ODE
solver) reaches the recipe §7.2 sat-1 saturation threshold even before
any T3 evidence lands.

The four F-CODEX falsifiers are:

| #  | Pillar       | Closed-form prediction                                                          |
|:--:|:-------------|:---------------------------------------------------------------------------------|
| 1  | train_cost   | `cost_ratio(N·D) = (N·D / 1e22) ^ N6_EXP`,    `N6_EXP = J₂/(J₂+1) = 24/25 = 0.96` |
| 2  | infer_cost   | `cost_ratio(ctx)  = (ctx / 8192)   ^ τ(6)`,   `τ(6) = J₂/n = 4`                   |
| 3  | alignment    | `score(profile)   = (1/σ) Σᵢ profile_i`,      `σ = J₂/φ = 12`                     |
| 4  | interpret    | `motif_count       = σ − φ = 10` (drift ≤ 3 vs SAE-class observations)            |

All four predictions ride on the same n=6 lattice
`σ·φ = n·τ = J₂ = 24`.

---

## §2 What the T2 ×3 stack actually verifies

Per pillar we ship three T2 layers; each catches a different class of
failure:

### T2 #1 — `numerics_<pillar>.hexa`
Synthetic anchor grid. Verifies the closed-form prediction holds over
a 5-point grid spanning two orders of magnitude in the input axis.
This is the "does the formula compute" check; it catches division-by-
zero, overflow at the extreme grid points, and trivial sign errors.

### T2 #2 — `numerics_<pillar>_parity.hexa`
Published-reference anchors. Verifies the closed-form prediction
agrees with **independently published numbers** (Chinchilla /
GPT-3 / Llama-2 / PaLM for cost; Olsson / Cunningham / Bricken /
Anthropic-2024 for interpret; HELM-Core for alignment). This is the
"does it agree with the rest of the field" check; it catches
calibration errors that T2 #1 cannot see because T2 #1 only checks
the formula against itself.

### T2 #3 — `numerics_<pillar>_solver.hexa`
ODE re-derivation. Each pillar's closed-form prediction can be
recovered as the solution / asymptote of a small dynamical system:

| Pillar       | ODE / Lyapunov                                          | Solver class                       |
|:-------------|:--------------------------------------------------------|:-----------------------------------|
| train_cost   | `dc/du = N6_EXP · c`,  `u = log(N·D / ND_REF)`           | Euler / midpoint-RK2 / RK4         |
| infer_cost   | `dc/du = τ(6)   · c`,  `u = log(ctx  / CTX_REF)`         | Euler / midpoint-RK2 / RK4         |
| alignment    | `d²x/dt² = −(x − M)`,  `M = mean(σ axes)`                | symplectic leapfrog (Verlet) + RK4 |
| interpret    | `dx/dt   = M − x`,     `M = σ − φ = 10`                  | Euler / midpoint-RK2 / RK4         |

This is the "is it consistent with continuum dynamics" check — it
catches errors that survive both T2 #1 and T2 #2 because both of
those check the closed-form algebra in isolation.

For the alignment pillar in particular, the choice of *symplectic*
leapfrog matters: the conservative Newton-flow on the σ=12-axis L2
loss has a constant-energy oscillator solution `x(t) = M(1 − cos t)`
whose **time-average over one period equals M**. Symplectic leapfrog
preserves the time-average to second order in h with bounded energy
drift, which is exactly the property that recovers the σ=12 mean
from the dynamical system. Non-symplectic RK4 also recovers M but
only in the limit of vanishing h; long-time energy drift makes its
time-average less reliable as a stand-alone mean estimator.

For pillar 4 (interpret) the gradient flow is dissipative and the
Lyapunov function `L(x) = ½(x − M)²` decays monotonically along the
trajectory — directly checked in `numerics_interpret_solver.hexa`
check #10.

---

## §3 Cross-cutters and meta verifiers

T2 ×3 per pillar gives 12 numerical runs total; the runnable surface
also ships four cross-cutters and three meta verifiers:

### Cross-cutters (X1 row)

| File                                  | Role                                                                |
|:--------------------------------------|:---------------------------------------------------------------------|
| `lattice_check.hexa`                  | 24 algebraic invariants of the n=6 lattice (T1 master)               |
| `cross_doc_audit.hexa`                | Taxonomy + falsifier-prefix + provenance + identity drift across docs |
| `numerics_cross_pillar.hexa`          | Identities tying multiple pillars (F1×F2, F3×F4, coupled F1+F4 ODE)  |
| `numerics_lattice_arithmetic.hexa`    | `math_pure` stability floor (assoc / dist / log/exp / pow round-trip) |

`numerics_cross_pillar.hexa` is the verifier most likely to break
under a silent lattice perturbation: its checks 1–4 establish that the
single identity `σ·φ = n·τ = J₂ = 24` propagates correctly into all
four pillars' structural constants. Check 8 then solves a coupled
F1 + F4 RK4 ODE system and demands both rel_err ≤ 1e-8 — a stronger
floor than any single pillar's solver test.

### Meta verifiers (M row)

| File                                | Role                                                                 |
|:------------------------------------|:----------------------------------------------------------------------|
| `falsifier_check.hexa`              | Layer-by-layer closure tally — emits the recipe §7.2 sat-1 verdict    |
| `lint_numerics.hexa`                | Recipe §4 invariants 1-5 over every `numerics_*.hexa` (must-have)     |
| `saturation_check.hexa`             | Aggregate self-stop — re-runs 6 closure components, emits self-stop   |

`saturation_check.hexa` is the canonical command for downstream
automation: `RESOURCE_LOCAL_HEXA=1 hexa run verify/saturation_check.hexa`
returns exit 0 + `__HEXA_CODEX_SATURATION_CHECK__ PASS` iff and only
if the closure goal is reached. Any cron / CI / loop runner can grep
that sentinel as the single source of truth.

---

## §4 Why `math_pure`?

Recipe §4 invariant 1 forbids raw float arithmetic for any
`numerics_*.hexa` — every script must `use "self/runtime/math_pure"`.
The `math_pure` runtime ships:

```
abs_pure  neg_pure   sign_pure  min_pure   max_pure  clamp_pure
sqrt_pure cbrt_pure  exp_pure   log_pure   log2_pure log10_pure
pow_pure  sin_pure   cos_pure   tan_pure   atan_pure …
```

Two reasons matter for hexa-codex specifically:

1. **Stability under lattice perturbation.** `numerics_lattice_arithmetic.hexa`
   pins the algebraic invariants those primitives must preserve
   (associativity, log∘exp = id within 1e-13, pow round-trip within
   6e-16, accumulation of 24 ones = J₂ EXACT). If `pow_pure` ever
   regresses, every `numerics_*_solver` and `numerics_*_parity` shifts
   in lockstep — the stability floor catches that one place rather
   than 14 places.

2. **Reproducibility across runtimes.** `math_pure` is implemented in
   pure Hexa (no platform-specific FFI), so the same float64 result
   is produced by `hexa.real` on macOS arm64 and on Linux x86_64. The
   parity layer (T2 #2) then becomes a portability check as a
   side-effect.

`lint_numerics.hexa` enforces this convention statically by grepping
each `numerics_*.hexa` for the import line.

---

## §5 The single regression command

```bash
RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT="$PWD" \
    ~/.hx/packages/hexa/hexa.real run tests/test_all.hexa
```

emits `__HEXA_CODEX_TEST_ALL__ PASS — full .hexa test suite green` on
exit 0 when all 24 regression wrappers pass. Each wrapper invokes its
verify counterpart and asserts both exit 0 *and* the expected sentinel
string is present in stdout — this catches the silent-fail mode where
a remote-routing wrapper would return exit 0 with an empty stdout.

For the saturation gate specifically:

```bash
hexa-codex verify saturation-check
# (or)
RESOURCE_LOCAL_HEXA=1 hexa run verify/saturation_check.hexa
```

is the single command that re-runs the 6 closure components in one
process and emits the canonical sat-1 marker.

---

## §6 What sat-2 would add

Recipe §7.2 sat-2 is the next saturation tier — adds T3 (live
empirical) anchors per pillar, plus optional second T2 stacks. For
hexa-codex that maps to:

| Pillar       | T3 (empirical) candidate                                          |
|:-------------|:------------------------------------------------------------------|
| train_cost   | Live FLOP / loss measurements on a frontier training run          |
| infer_cost   | Live latency / KV-cache profiles at 1M-ctx on a deployed model    |
| alignment    | Live HELM-Core composite on a frontier model                      |
| interpret    | Live SAE feature counts via a dictionary-learning toolchain       |

Each T3 anchor lifts its falsifier to closure pct = 5/5 = 1.0;
collectively they unlock the recipe §7.2 sat-2 verdict. The
`falsifier_check.hexa` closure tracker already exposes the T3 gap as
an informational check (it does not block sat-1).

Until the T3 row lands, sat-1 is the operational closure goal — and
that goal is reached as of iter 23.

---

## §7 References

- `~/core/bedrock/docs/runnable_surface_recipe.md` — closure-depth recipe (SSOT)
- `CHANGELOG.md` — per-iter delta, including sat-1 verdict
- `formal/lean4/N6/InvariantLattice/Sigma.lean` — Lean4 PROVEN σ(6)=12
- `papers/n6-ai-17-techniques-experimental-paper.md` — 192/192 EXACT verb σ·φ map
- `papers/n6-ai-techniques-68-integrated-paper.md` — wider 68-tech atlas
