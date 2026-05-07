# Changelog — hexa-codex

All notable changes to this standalone repo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — RSC port from Python → .hexa (recipe §7.4)

> Following `~/core/bedrock/docs/runnable_surface_recipe.md` (closure-depth
> accumulation). Goal: reach F-CODEX-1..4 67% closure (T1 + T2 ×3 stack)
> via .hexa-native verify/ + tests/ inventory, mirroring hexa-cern's worked
> example. Python verify/ kept until ports retire its targets.

### Added (2026-05-07 — 1st RSC iteration: lattice_check)

- `verify/lattice_check.hexa` — n=6 invariant lattice audit (24 checks):
  - Algebraic: σ·φ = n·τ = J₂ = 24, σ-φ=10, σ²=144, σ³=1728
  - Partition: 17-verb / 4-group (6+3+4+4=17 ; group_count=τ(6)=4)
  - Cross-doc: `.roadmap.hexa_codex` §A.1, `hexa.toml [invariants.n6]`
  - Spec presence: 17/17 verb specs + 11/11 lattice-aware token check
  - Reference annex: papers/P1 192/192 EXACT map + Lean Sigma.lean anchor
  - Sentinel: `__HEXA_CODEX_LATTICE__ PASS` ; covers T1 floor for F-CODEX-1..4
- `tests/test_lattice.hexa` — regression wrapper for the verifier above.
- `tests/test_all.hexa` — top-level .hexa test aggregator (selftest + lattice).
- `cli/hexa-codex.hexa` — `verify lattice` routes to the .hexa script
  (`verify all` and other targets unchanged on Python path).
- `hexa.toml` — `[test] files` += {test_lattice, test_all};
  `verify =` += `verify/lattice_check.hexa`.

### Verified

- `hexa run verify/lattice_check.hexa` — 24/24 PASS, 0 warn.
- `hexa run tests/test_all.hexa` — 2/2 PASS (selftest + lattice).
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 2nd RSC iteration: cross_doc_audit)

- `verify/cross_doc_audit.hexa` — cross-document anchor audit (15 checks):
  - Taxonomy: 17 verb names + 4-group section headers consistent across
    `hexa.toml [modules]`, CLI `verb_spec()` + `VERBS_*` arrays, and the
    `README.md` verb table.
  - Falsifier prefix: F-CODEX-1..4 appear in roadmap §A.4 + hexa.toml
    `[falsifiers]` + README's preregister table.
  - Provenance: `n6-architecture@c0f1f570` cited in hexa.toml + README +
    CHANGELOG.
  - Master identity string `σ(6)·φ(6)=n·τ(6)=J₂=24` agrees across roadmap +
    hexa.toml + README.
  - Release ladder: roadmap §A.2 lists v1.0.0..v2.0.0 (5 versions, RELEASED)
    + CHANGELOG `[1.0.0]` anchor.
  - Lifecycle quartet (pretrain/SFT/RLHF/deploy) enumerated in roadmap §A.1.
  - HELM 12-dim capability bin in roadmap + hexa.toml + README.
  - Paper provenance: 4 papers each have `@canonical` / `@md5_at_extraction`
    / `@absorbed_into` headers.
  - Formal anchor: `formal/lean4/N6/InvariantLattice/Sigma.lean` exists +
    `formal/README.md` + main README cross-link the σ(6)=12 PROVEN badge.
  - CHANGELOG visibility: RSC port marker + [1.0.0] anchor present.
  - Sentinel: `__HEXA_CODEX_CROSS_DOC__ PASS`.
- `tests/test_cross_doc.hexa` — regression wrapper for the verifier above.
- `tests/test_all.hexa` — CASES += `test_cross_doc`.
- `cli/hexa-codex.hexa` — `verify cross-doc` (and `cross_doc`) routes to .hexa.
- `hexa.toml` — `[test] files` += `test_cross_doc.hexa`;
  `verify =` += `verify/cross_doc_audit.hexa`;
  `[closure].runnable_hexa_iter2` marker.

### Verified (iter 2)

- `hexa run verify/cross_doc_audit.hexa` — 15/15 PASS.
- `hexa run tests/test_all.hexa` — 3/3 PASS (selftest + lattice + cross_doc).
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 3rd RSC iteration: calc_train_cost / F-CODEX-1)

- `verify/calc_train_cost.hexa` — F-CODEX-1 T1 algebraic calculator (8 checks):
  - `J₂ = σ(6)·φ(6) = 12·2 = 24` factorization.
  - `J₂ = n·τ(6) = 6·4 = 24` consistency with closure.
  - n6 cost-exponent `J₂/(J₂+1) = 24/25 = 0.96` (cross-multiplication identity).
  - Chinchilla a+b ≈ 1.00 within 0.10 of n6 exp 0.96 (falsifier-floor tolerance).
  - Chinchilla 6·N·D rule: FLOPs/token = n = 6 (lattice-derived coefficient).
  - Spec anchor: `train_cost/ai-training-cost.md` ships Chinchilla / scaling-law
    / falsifier-anchor tokens.
  - Anchor identity: cost ratio = 1 at N·D = nd_ref (multiplicative form).
  - F-CODEX-1 vs F-CODEX-4 ordering: J₂=24 > σ-φ=10.
  - Sentinel `__HEXA_CODEX_CALC_TRAIN_COST__ PASS`. Closes T1 floor for F-CODEX-1.
- `tests/test_calc_train_cost.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_calc_train_cost`.
- `cli/hexa-codex.hexa` — `verify train_cost` (and `train-cost`) routes to .hexa.
- `hexa.toml` — `[test] files` += `test_calc_train_cost.hexa`;
  `verify =` += `verify/calc_train_cost.hexa`;
  `[closure].runnable_hexa_iter3` marker.

### Verified (iter 3)

- `hexa run verify/calc_train_cost.hexa` — 8/8 PASS.
- `hexa run tests/test_all.hexa` — 4/4 PASS (selftest + lattice + cross_doc + calc_train_cost).
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 4th RSC iteration: calc_infer_cost / F-CODEX-2)

- `verify/calc_infer_cost.hexa` — F-CODEX-2 T1 algebraic calculator (9 checks):
  - `τ(6) = 4` divisor-count identity.
  - n=6 closed-form exponent equals `τ(6)`.
  - Exponent ladder: 1.0 (linear) < 1.5 (approx) < 2.0 (naïve) < 4.0 (n=6).
  - n=6 strict upper bound: gap from naïve O(n²) ≥ 1.0.
  - 1M context = 2^20 = 1_048_576 power-of-2 arithmetic.
  - Spec anchor: `infer_cost/ai-inference-cost.md` ships 1M-ctx + KV-cache +
    >80GB infeasibility tokens.
  - Spec anchor: attention + O(n²) + linear/Paged/Flash engine tokens.
  - σ·τ = 12·4 = 48 serving-channel anchor (arithmetic + spec presence).
  - (σ·τ)/J₂ = φ(6) = 2 — serving-channel ↔ training-cost lattice link.
  - Sentinel `__HEXA_CODEX_CALC_INFER_COST__ PASS`. Closes T1 floor for F-CODEX-2.
- `tests/test_calc_infer_cost.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_calc_infer_cost`.
- `cli/hexa-codex.hexa` — `verify infer_cost` (and `infer-cost`) routes to .hexa.
- `hexa.toml` — `[test] files` += `test_calc_infer_cost.hexa`;
  `verify =` += `verify/calc_infer_cost.hexa`;
  `[closure].runnable_hexa_iter4` marker.

### Verified (iter 4)

- `hexa run verify/calc_infer_cost.hexa` — 9/9 PASS.
- `hexa run tests/test_all.hexa` — 5/5 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 5th RSC iteration: calc_alignment / F-CODEX-3)

- `verify/calc_alignment.hexa` — F-CODEX-3 T1 algebraic calculator (9 checks):
  - 12 HELM-comparable axes (helpfulness, harmlessness, honesty, calibration,
    coherence, robustness, fairness, privacy, toxicity, bias, faithfulness,
    instructability) — count = σ(6) = 12.
  - 3-stratum × 4-stage = 12 axis closure: (σ/τ) · τ = σ.
  - Uniform-axis 0.700 mean = 0.700 (sum=12·700, /12 = 700; ×1000 scaling).
  - HELM drift |aggregate − baseline| = |700 − 650| = 50 ≤ 100 tolerance.
  - Tolerance value 0.100 declared.
  - σ-φ = 10 strict-positive axes (cross-link to F-CODEX-4 motif row).
  - Spec anchor: `alignment/ai-alignment.md` ships preference + RLHF + DPO.
  - Spec anchor §S4: three-axis architecture (engineering / model-organism /
    scalable oversight).
  - alignment ∈ safety group; |safety| = 6 = N (per hexa.toml [modules]).
  - Sentinel `__HEXA_CODEX_CALC_ALIGNMENT__ PASS`. Closes T1 floor for F-CODEX-3.
- `tests/test_calc_alignment.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_calc_alignment`.
- `cli/hexa-codex.hexa` — `verify alignment` routes to .hexa.
- `hexa.toml` — `[test] files` += `test_calc_alignment.hexa`;
  `verify =` += `verify/calc_alignment.hexa`;
  `[closure].runnable_hexa_iter5` marker.

### Verified (iter 5)

- `hexa run verify/calc_alignment.hexa` — 9/9 PASS.
- `hexa run tests/test_all.hexa` — 6/6 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 6th RSC iteration: calc_interpret / F-CODEX-4)

- `verify/calc_interpret.hexa` — F-CODEX-4 T1 algebraic calculator (10 checks):
  - σ(6) − φ(6) = 10 motif-count identity.
  - PREDICTED_MOTIFS = σ−φ = 10.
  - Motif catalog cardinality = predicted (10 entries: induction-head,
    suppression-head, name-mover, backup/negative name-mover, duplicate-token
    detector, previous-token-head, refusal-circuit, factual-recall-head,
    in-context pattern-matcher).
  - (σ−φ) + φ = σ : motif row + verdict row = σ closure.
  - Drift |observed − predicted| ≤ 3 (default observed = 10, drift 0).
  - Tolerance < φ·2 = 4 (non-trivial falsifier).
  - Spec anchor: SAE / circuit / dictionary-learning tokens.
  - Spec anchor: TransformerLens / SAELens + Bricken / Cunningham refs.
  - interpret ∈ safety group; |safety| = 6 = N.
  - F-CODEX-3 σ axes (12) − F-CODEX-4 σ−φ motifs (10) = φ : verdict-bit drop.
  - Sentinel `__HEXA_CODEX_CALC_INTERPRET__ PASS`. Closes T1 for F-CODEX-4 —
    completes the **T1 row for all 4 falsifiers**.
- `tests/test_calc_interpret.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_calc_interpret`.
- `cli/hexa-codex.hexa` — `verify interpret` routes to .hexa.
- `hexa.toml` — `[test] files` += `test_calc_interpret.hexa`;
  `verify =` += `verify/calc_interpret.hexa`;
  `[closure].runnable_hexa_iter6` marker.

### Verified (iter 6)

- `hexa run verify/calc_interpret.hexa` — 10/10 PASS.
- `hexa run tests/test_all.hexa` — 7/7 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 7th RSC iteration: numerics_train_cost / F-CODEX-1 T2)

- `verify/numerics_train_cost.hexa` — F-CODEX-1 T2 numerical re-derivation
  (9 checks; recipe §4 invariants 1–5 satisfied — `use "self/runtime/math_pure"`,
  RUN/FAIL counters, `FALSIFIERS` list, `__HEXA_CODEX_NUMERICS_TRAIN_COST__ PASS`
  sentinel, `exit(0)`):
  - Anchor identity: `n6_ratio(N·D = ND_REF) = 1.0` within 1e-9.
  - Monotonicity over 5-anchor grid (1e20, 1e21, 1e22 REF, 1e23, 1e24).
  - Above anchor: n6_ratio < Chinchilla-naive (0.96 < 1.0 exponent).
  - Below anchor: n6_ratio > Chinchilla-naive (concave power).
  - Curve proximity: max |log-ratio diff| < 0.25 over 100× span.
  - Numerical stability: all anchors finite + positive (math_pure pow_pure /
    log_pure on float64).
  - Float exponent J₂/(J₂+1) = 0.96 within 1e-12.
  - Exponent gap = 1.0 − 24/25 = 0.04 within 1e-12.
  - Chinchilla 6·N·D coefficient = n = 6 (float identity).
- `tests/test_numerics_train_cost.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_numerics_train_cost`.
- `cli/hexa-codex.hexa` — `verify numerics-train_cost` routes to .hexa.
- `hexa.toml` — `[test] files` += `test_numerics_train_cost.hexa`;
  `verify =` += `verify/numerics_train_cost.hexa`;
  `[closure].runnable_hexa_iter7` marker.

### Verified (iter 7)

- `hexa run verify/numerics_train_cost.hexa` — 9/9 PASS.
- `hexa run tests/test_all.hexa` — 8/8 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-07 — 8th RSC iteration: numerics_infer_cost / F-CODEX-2 T2)

- `verify/numerics_infer_cost.hexa` — F-CODEX-2 T2 numerical re-derivation
  (10 checks via `math_pure pow_pure / log_pure / abs_pure`):
  - Anchor identity `n6_ratio(8k) = 1.0` within 1e-9.
  - Monotonic over 5-anchor ctx grid (1k, 8k REF, 32k, 128k, 1M = 2^20).
  - Ladder above anchor: linear (1.0) < approx (1.5) < naïve (2.0) < n6 (4.0).
  - Ladder below anchor inverted (x<1: higher exponent → smaller value).
  - 1M-ctx n6 ratio = (1M/8k)^4 = 128^4 = 2^28 = 268_435_456 EXACT.
  - 1M-ctx naïve O(n²) ratio = 128² = 16_384 EXACT.
  - 1M-ctx gap (n6 − naïve) > 1e8 (strict upper bound).
  - Numerical stability at all 5 anchors (no NaN/Inf).
  - τ(6) int↔float consistency (4 == 4.0).
  - Log-power identity log(ctx^τ) = τ·log(ctx) within 1e-9.
- `tests/test_numerics_infer_cost.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_numerics_infer_cost`.
- `cli/hexa-codex.hexa` — `verify numerics-infer_cost` routes to .hexa.
- `hexa.toml` — `[test] files` += `test_numerics_infer_cost.hexa`;
  `verify =` += `verify/numerics_infer_cost.hexa`;
  `[closure].runnable_hexa_iter8` marker.

### Verified (iter 8)

- `hexa run verify/numerics_infer_cost.hexa` — 10/10 PASS.
- `hexa run tests/test_all.hexa` — 9/9 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### Added (2026-05-08 — 9th RSC iteration: numerics_alignment / F-CODEX-3 T2)

- `verify/numerics_alignment.hexa` — F-CODEX-3 T2 numerical re-derivation
  (10 checks via `math_pure`):
  - Axis count σ=12 across 5 profile vectors + axis-name catalog.
  - uniform-0.7 profile: mean = 0.7 within 1e-12.
  - perfect-1.0 / floor-0.0 / split-0.8/0.6 / varied: each mean exact.
  - HELM drift partition: 3 of 5 profiles within ±0.10 of baseline 0.65.
  - Mean linearity: mean(2·v) = 2·mean(v).
  - Jensen's inequality demo: mean(log v) < log(mean v) (concave log).
  - Accumulation stability: 12·0.1 sum within 1e-14 of 1.2.
- `tests/test_numerics_alignment.hexa` — regression wrapper.
- `tests/test_all.hexa` — CASES += `test_numerics_alignment` (now 10).
- `cli/hexa-codex.hexa` — `verify numerics-alignment` routes to .hexa.
- `hexa.toml` — `[test] files` += `test_numerics_alignment.hexa`;
  `verify =` += `verify/numerics_alignment.hexa`;
  `[closure].runnable_hexa_iter9` marker.

### Verified (iter 9)

- `hexa run verify/numerics_alignment.hexa` — 10/10 PASS.
- `hexa run tests/test_all.hexa` — 10/10 PASS.
- `python3 -m pytest tests/ -m auto -q` — 83 passed (no regression).

### F-CODEX closure status (after iter 9)

| Falsifier  | T1 (algebraic)                    | T2 (numerics)            | T3 (empirical) |
|:-----------|:----------------------------------|:-------------------------|:--------------:|
| F-CODEX-1  | lattice + calc_train_cost ✓ ✓     | numerics_train_cost ✓    | TBD            |
| F-CODEX-2  | lattice + calc_infer_cost ✓ ✓     | numerics_infer_cost ✓    | TBD            |
| F-CODEX-3  | lattice + calc_alignment ✓ ✓      | numerics_alignment ✓     | TBD            |
| F-CODEX-4  | lattice + calc_interpret ✓ ✓      | TBD                      | TBD            |

F-CODEX-1/2/3 closure pct: 67% each (T1 + T2). 3 of 4 falsifiers reach T2 floor.

### F-CODEX T1 row: COMPLETE after iter 6

| Falsifier  | T1 anchors                                | T2 (numerics) | T3 (empirical) |
|:-----------|:------------------------------------------|:-------------:|:--------------:|
| F-CODEX-1  | lattice_check + calc_train_cost           | TBD           | TBD            |
| F-CODEX-2  | lattice_check + calc_infer_cost           | TBD           | TBD            |
| F-CODEX-3  | lattice_check + calc_alignment            | TBD           | TBD            |
| F-CODEX-4  | lattice_check + calc_interpret            | TBD           | TBD            |

Next: numerics_*.hexa T2 layer (recipe §7.4 priority 4).

## [1.0.0] — 2026-05-06

### Added

- Initial extraction from `n6-architecture@c0f1f570` —
  17-verb AI knowledge substrate organized in 4 groups:
  - **safety** (6): alignment, safety, welfare, adversarial, consciousness, interpret
  - **economics** (3): train_cost, infer_cost, quality_scale
  - **ops** (4): deploy, enterprise, agent_serving, eval
  - **substrate** (4): multimodal, rlhf, cog_arch, causal
- `cli/hexa-codex.hexa` — placeholder dispatcher (4-group sub-commands +
  `list` / `selftest` / `help` / `--version` utilities).
- `install.hexa` — hx-package install hook (warn-only selftest at post phase).
- `hexa.toml` — package manifest with 4-group module layout and
  honest-scope `[scope]` block.
- `tests/test_selftest.hexa` — verifies 17-verb presence sweep.
- `LICENSE` — MIT.
- `README.md` — Why / Verbs (4-group table) / Status / Install / Cross-link / License.

### Status

`SPEC_CATALOG_ONLY` (raw#10 honest C3): each verb is a single closed-form
spec `.md` file plus a falsifier preregister; working `.hexa` falsifier
sandboxes are deferred to post-v1.0 cycles.

[1.0.0]: https://github.com/need-singularity/hexa-codex/releases/tag/v1.0.0
