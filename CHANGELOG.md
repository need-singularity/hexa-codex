# Changelog — hexa-codex

All notable changes to this standalone repo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

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
