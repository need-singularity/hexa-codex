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
