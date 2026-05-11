# t4_empirical — forge → hexa-codex T4 empirical data PRs

This directory holds **T4 empirical data PRs from sister forge repos**
(primarily `hexa-forge`). Each PR is a markdown file with:
- forge run provenance (forge commit, model, dataset snapshot)
- measurement payload (what's measured, in what units)
- falsifier closure delta (which F-CODEX-N moved, by how much)
- recipe §3 `closure_pct` impact

## Submission protocol

Forge produces `outbox/hexa-codex/<verb>/<run_id>.md` via
[`tool/emit_t4.py`](https://github.com/dancinlab/hexa-forge/blob/main/tool/emit_t4.py).
Operator copies the draft here, opens a PR, hexa-codex maintainer
reviews + lands.

Authoritative routing table:
[`hexa-forge/papers/plan-feedback-channel-ops.md`](https://github.com/dancinlab/hexa-forge/blob/main/papers/plan-feedback-channel-ops.md).

## Acceptance criteria (per forge v1.0.0 gate ⑬)

- ≥ 5 distinct PRs landed (covering ≥ 2 F-CODEX-N falsifiers).
- Each PR carries a forge_commit hash for reproducibility.
- token-hash provenance preserves operator privacy (no raw HF token).

## Current inbox (2026-05-11)

| verb            | run_id                             | F-CODEX target | source data |
| --------------- | ---------------------------------- | -------------- | ----------- |
| infer_cost      | 2026-05-11-stack-v1-fetch-pipeline | F-CODEX-2 T4   | fetch + tokenizer + HF upload throughput |
| safety          | 2026-05-11-stack-v1-license-audit  | F-CODEX-3 T4   | license-clean rate on Stack v1 perm subset |
| interpret       | 2026-05-11-interpret               | F-CODEX-4 T4 analog | tokenizer extension round-trip |
| quality_scale   | 2026-05-11-quality_scale           | cross-cutter   | Stack v1 perm sample @ 5% / 30K-per-lang |
| eval            | 2026-05-11-eval                    | meta wrapper   | v0.1.2 stub-pipeline verification |

This batch closes **forge v1.0.0 gate ⑬ draft tier**. Drafts carry
`<TODO>` markers where stage-1+ measurements will land.
