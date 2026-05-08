# hexa-codex numerics methodology — recipe §7.4 priority 13 narrative

**Status (post iter 27):** recipe §7.2 sat-1 = **100% closure** reached
under recipe §3 taxonomy (T1=`calc_*`, T2=`numerics_*` ∧
`numerics_*_solver`, T3=`numerics_*_parity`).
**Source-of-truth recipe:** `~/core/bedrock/docs/runnable_surface_recipe.md`.

This document explains *why* the runnable surface is structured the way
it is — it does not duplicate the verifier code, but maps each runnable
back to the closure-depth taxonomy and explains what that closure
*means* for the four F-CODEX falsifiers.

---

## §1 The closure-depth taxonomy

Recipe §3 defines a **3-tier ladder** for each falsifier:

| Tier | Layer files                                                                      | What it proves                                                                                |
|:----:|:---------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------|
| T1   | `calc_<pillar>.hexa`                                                             | Closed-form **algebraic** identity (integer arithmetic floor)                                 |
| T2   | `numerics_<pillar>.hexa` ∧ `numerics_<pillar>_solver.hexa`                       | **Pure-math** closed-form re-derivation (math_pure float64; analytic + ODE consistency)        |
| T3   | `numerics_<pillar>_parity.hexa`                                                  | **Archival empirical contact** — comparison against published-ref data (no live measurement) |
| T4   | `<pillar>_t4_*.hexa` *(out of loop scope, recipe §9)*                            | **Live hardware / Stage-1+** measurement — out of recipe loop                                  |

Recipe §3 closure_pct ladder:

```
n = sum(t1_ok, t2_ok, t3_ok)        # 0..3
pct = 0 | 33 | 67 | 100
```

Recipe §7.2 sat-1 saturation = `closure_pct = 100%` for *every*
falsifier (i.e. T1 ✓ + T2 ✓ + T3 ✓ on every pillar). T4 is recipe §9
territory (live hardware) and not part of the loop's stop condition.

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

## §2 What the T1/T2/T3 stack actually verifies

Per pillar we ship four scripts (one per tier file slot); each catches
a different class of failure.

### T1 — `calc_<pillar>.hexa`
Algebraic closed-form check. Verifies the structural identities of the
n=6 lattice (σ·φ = n·τ = J₂ = 24, etc.) at the integer level. Catches
typos in the σ/φ/τ/n constants and trivial sign errors in the
prediction formula.

### T2.a — `numerics_<pillar>.hexa`
Synthetic anchor grid (math_pure float64). Verifies the closed-form
prediction holds over a 5-point grid spanning two orders of magnitude
in the input axis. Catches division-by-zero, overflow at the extreme
grid points, and any rounding-class divergence between integer and
float arithmetic.

### T2.b — `numerics_<pillar>_solver.hexa`
ODE re-derivation. Each pillar's closed-form prediction can be
recovered as the solution / asymptote of a small dynamical system:

| Pillar       | ODE / Lyapunov                                          | Solver class                       |
|:-------------|:--------------------------------------------------------|:-----------------------------------|
| train_cost   | `dc/du = N6_EXP · c`,  `u = log(N·D / ND_REF)`           | Euler / midpoint-RK2 / RK4         |
| infer_cost   | `dc/du = τ(6)   · c`,  `u = log(ctx  / CTX_REF)`         | Euler / midpoint-RK2 / RK4         |
| alignment    | `d²x/dt² = −(x − M)`,  `M = mean(σ axes)`                | symplectic leapfrog (Verlet) + RK4 |
| interpret    | `dx/dt   = M − x`,     `M = σ − φ = 10`                  | Euler / midpoint-RK2 / RK4         |

The solver layer is the "is it consistent with continuum dynamics"
check — it catches closed-form errors that survive T2.a (synthetic
grid) because T2.a only checks the formula against itself; the solver
re-derives the same prediction by independent integration.

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

### T3 — `numerics_<pillar>_parity.hexa`
**Archival empirical contact.** Recipe §3 distinguishes T2 (pure-math
re-derivation, closed-form internal consistency) from T3 (published-ref
comparison) because they catch different failure modes:

- A T2 failure ⇒ the closed-form is internally inconsistent
  (formula bug, math_pure regression, ODE/algebra mismatch).
- A T3 failure ⇒ the closed-form is *consistent with itself* but
  *disagrees with the empirical record* (Chinchilla / GPT-3 / Llama-2
  / PaLM cost numbers; HELM-Core composites; Olsson / Cunningham /
  Bricken / Anthropic-2024 SAE motif counts).

T3 is "archival" because the ref data is read off published papers,
not measured live; live measurement is recipe §9 / T4 territory.

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

## §6 What's beyond 100% closure (recipe §9 — T4 / Stage-1+)

Recipe §7.2 sat-1 = `closure_pct = 100%` per falsifier under the
3-tier ladder is the operational stop condition for the loop, and
that condition is reached as of iter 27.

Recipe §7.2 sat-2 = the §1 16-script inventory is fully populated +
meta-lint passes. Cross-checked at iter 21 (`falsifier_check.hexa`)
and iter 22 (`lint_numerics.hexa`) → sat-2 also reached.

Beyond sat-1 + sat-2 lies recipe §9 (T4 — live hardware / Stage-1+
data feeds), which is *out of recipe loop scope*. T4 candidates per
pillar:

| Pillar       | T4 (live hardware / Stage-1+) candidate                            |
|:-------------|:-------------------------------------------------------------------|
| train_cost   | Live FLOP / loss measurements on a frontier training run           |
| infer_cost   | Live latency / KV-cache profiles at 1M-ctx on a deployed model     |
| alignment    | Live HELM-Core composite re-run on a frontier model                |
| interpret    | Live SAE feature counts via a dictionary-learning toolchain        |

T4 work is gated on infrastructure (training runs, deploy fleets,
HELM access, SAE toolchain) that lives outside this repo's runnable
surface. The `falsifier_check.hexa` closure tracker reports the T4
gap as an informational metric; it does not block the sat-1 verdict.

---

## §7 References

- `~/core/bedrock/docs/runnable_surface_recipe.md` — closure-depth recipe (SSOT)
- `CHANGELOG.md` — per-iter delta, including sat-1 verdict
- `formal/lean4/N6/InvariantLattice/Sigma.lean` — Lean4 PROVEN σ(6)=12
- `papers/n6-ai-17-techniques-experimental-paper.md` — 192/192 EXACT verb σ·φ map
- `papers/n6-ai-techniques-68-integrated-paper.md` — wider 68-tech atlas
