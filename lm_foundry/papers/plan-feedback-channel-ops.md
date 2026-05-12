# plan — forge → hexa-codex feedback channel ops (M-005)

> **Resolves M-005.** Operationalises the bidirectional linkage rule
> from `docs/code-llm.md` §VERIFY "upstream feedback contract" +
> Cross-link policy "feedback channel". Every real number forge
> produces becomes a PR candidate to hexa-codex. This doc specifies
> the **PR template + automation triggers + acceptance criteria**.

| field        | value                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------- |
| status       | `DESIGN_LOCKED` — implementation gated on v0.1.3 base-model decision (D-007)                      |
| gate         | v1.0.0 forge release requires ≥ **5 PRs landed** in hexa-codex                                    |
| primary T4   | F-CODEX-1 (training cost) + F-CODEX-2 (inference cost) — measurement window overlaps SFT + serving |
| secondary    | F-CODEX-3 (alignment T4) + F-CODEX-4 (interpret T4 analog)                                        |
| last updated | 2026-05-11                                                                                        |

---

## §1 Artifact → hexa-codex verb mapping (PR routing)

| forge measurement / artifact                                | hexa-codex destination                                                                                | PR shape                                                                                          | F-CODEX target                  |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------- |
| **SFT loss-vs-FLOP curve** (per scaling sweep)              | `hexa-codex/train_cost`                                                                               | `t4-empirical/forge-<run_id>.json` + parity row in `numerics_train_cost_parity.hexa`              | **F-CODEX-1 T4** (D-004)        |
| **M4 / Mac Studio / H100 latency profile** + KV-cache curve | `hexa-codex/infer_cost`                                                                               | `t4-empirical/forge-<run_id>.json` + parity row in `numerics_infer_cost_parity.hexa`              | **F-CODEX-2 T4** (D-005)        |
| **HumanEval+ / hexa-eval / 5-NL aggregate pass rates**      | `hexa-codex/quality_scale`                                                                            | per-pillar score table + cross-cutter contribution                                                | cross-cutter                    |
| **Refusal rate matrix** (5 NL × adversarial categories)     | `hexa-codex/safety` + `alignment` + `adversarial`                                                     | `safety/empirical/forge-refusal-<run_id>.csv` + HELM-style table                                  | **F-CODEX-3 T4** input (D-006)  |
| **Native-first / 2026-canon-first audit** (tree-sitter rule pack outputs) | `hexa-codex/interpret`                                                                       | motif analog table — count of (idiom-correct, idiom-incorrect) patterns                           | **F-CODEX-4 T4** analog (D-007) |
| **DPO yield numbers** (linter-driven pair count, quality)   | `hexa-codex/rlhf`                                                                                     | preference-data substrate annex                                                                   | substrate input                 |
| **Eval methodology refinements** (Mk.II → Mk.III templates) | `hexa-codex/eval`                                                                                     | template diff in `eval/ai-eval-pipeline.md §S6 EVOLVE` Mk progression                             | meta — wraps F-1..4             |
| **Tool-use schema iterations** (actual forge tool surface)  | `hexa-codex/agent_serving`                                                                            | schema diff in `agent_serving/ai-agent-serving.md`                                                | F-CODEX-2 SLO input             |
| **Hardware-tier deployment recipes** (M4 / Studio / H100)   | `hexa-codex/deploy`                                                                                   | recipe annex in `deploy/ai-deployment.md`                                                         | ops input                       |
| **License-clean CI audit summaries**                        | (no direct verb — feeds `enterprise`)                                                                 | data-residency annex                                                                              | ops input                       |

## §2 PR template

Each PR follows this shape (mirrors hexa-codex's `IMPORTED_FROM_CANON.md`
provenance discipline):

```markdown
# forge T4 empirical: <verb> — <run-id>

## Provenance
- forge run: `<run_id>` (commit SHA: `<sha>`)
- model: `<base>-<variant>-<size>-<quant>`
- date: `YYYY-MM-DD`
- compute: `<H100×N / Mac Studio M4 Max ...>`
- corpus snapshot: `datasets.toml@<hash>`
- tokenizer: `<base-bpe + hexa-extension@<hash>>`

## What this measures
<one paragraph — tie back to the verb's §S1 WHY>

## Falsifier closure delta
- `F-CODEX-<N>`: T4 was `PENDING`; now `<PASS|REGRESS|UNDETERMINED>` with `<numbers>`
- Recipe §3 `closure_pct` impact: <none / +T4 ✓ → 4/4 = 100%>

## Numbers
| metric | value | reference |
|--------|-------|-----------|
| ...    | ...   | ...       |

## Reproducibility
- script: `<path in forge repo>`
- inputs: `<corpus subset SHA / eval set SHA>`
- runtime: `<wall-clock>`
- determinism: `<seed / nondeterminism notes>`

## Cross-link
- forge-side artifact: `<path>`
- hexa-codex landing site: `<file>` (parity row appended)
- F-CODEX-<N> arithmetic floor (T1+T2+T3): already ✓ at v1.0.0

## License / attribution
- corpus license tags: `<list>`
- benchmark sources: `<list with license>`

## Validation checklist
- [ ] `hexa-codex verify falsifier-check` still PASS
- [ ] `hexa-codex verify saturation-check` still emits `__HEXA_CODEX_SATURATION_CHECK__ PASS`
- [ ] `hexa-codex verify release-ladder` monotonicity holds
- [ ] new T4 layer's parity verifier added under `verify/numerics_<verb>_t4_parity.hexa`
- [ ] CHANGELOG entry in hexa-codex (`[Unreleased]` block)
```

## §3 Automation triggers

Hooks live in **forge** (output side), not hexa-codex (input side):

| forge event                                  | hook                                                                          | output                                                       |
| -------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| SFT run complete (loss curve frozen)         | `tool/emit_t4_train_cost.hexa` reads `runs/<id>/loss.parquet`                 | `t4-train-cost-<id>.md` PR body draft                        |
| Inference benchmark on a hardware tier       | `tool/emit_t4_infer_cost.hexa` reads `runs/<id>/latency.parquet`              | `t4-infer-cost-<id>.md` PR body draft                        |
| `hexa-eval` / `5-NL eval` aggregate complete | `tool/emit_quality_scale.hexa` reads `runs/<id>/eval.parquet`                 | `quality-scale-<id>.md` PR body draft                        |
| Refusal-matrix audit                         | `tool/emit_refusal_matrix.hexa`                                               | `safety-empirical-<id>.csv` + alignment / adversarial PRs    |
| Style audit (tree-sitter rule pack)          | `tool/emit_style_audit.hexa`                                                  | `interpret-motif-<id>.md`                                    |

Each `emit_*.hexa` script:
1. reads the forge run artifact
2. renders the `§2 PR template` with measured values
3. writes a Markdown draft to `outbox/hexa-codex/<verb>/<id>.md`
4. emits a one-line summary signal (similar to hexa-codex sat-1
   sentinel pattern) `__FORGE_T4_EMITTED__ <verb> <id>`
5. (optional) shells out `gh pr create -R dancinlab/hexa-codex` if
   `--auto-pr` flag is set

## §4 Acceptance criteria (forge v1.0.0 gate)

```
gate: forge → hexa-codex feedback channel (per docs/code-llm.md §VERIFY upstream feedback contract)
   requires: ≥ 5 PRs landed in hexa-codex (any combination from §1 routing)
   strongly favored: at least 1 PR per F-CODEX-N to land T4 empirical floor for ≥ 2 falsifiers
   default targets (highest-yield, measurement-window-overlap):
     - F-CODEX-1 T4 (train_cost) — lands when SFT sweep completes
     - F-CODEX-2 T4 (infer_cost) — lands when M4 / Studio / H100 latency profile completes
```

Non-blocking (nice-to-have at v1.0.0):
- F-CODEX-3 T4 (alignment) — needs the model to actually respond to
  HELM-Core-style multi-axis eval; lands when refusal matrix +
  hexa-eval + 5-NL eval all complete.
- F-CODEX-4 T4 analog (interpret) — needs SAE-trained features over
  the forge weights; this is more aspirational and may slip to v1.1.0.

## §5 Concurrency + provenance guarantees

- Every forge run gets a **monotonically increasing run_id** + commit
  SHA pinned at start of run.
- Outbox drafts are **immutable** once written (`outbox/hexa-codex/<verb>/<id>.md`
  is write-once). If a re-emit is needed (bug in emit script), a new
  `<id>` is allocated.
- PR drafts include the corpus snapshot hash (`datasets.toml@<hash>`) so
  hexa-codex can verify the empirical numbers came from the corpus
  state forge claims.
- No re-pollination: forge MUST NOT consume hexa-codex content as
  training data. The downstream-only relationship is one-directional
  for the `code` verb's corpus (avoid model-feedback loops).

## §6 Failure modes + mitigations

| failure                                                  | symptom                                                | mitigation                                                                                       |
| -------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Forge measures something that contradicts F-CODEX-N arithmetic floor | T1 still PASS, T4 numbers conflict                | open `D-NNN` in hexa-codex `plan-decisions-pending.md`; mark falsifier as `T4 ANOMALOUS PENDING`; do NOT auto-tombstone arithmetic. Investigate together. |
| Corpus license drift causes T4 retraction                | downstream regret                                      | hexa-codex `verify/cross_doc_audit.hexa` flags license-tag drift; forge re-runs with cleaned corpus |
| Repeated forge-runs produce divergent T4 numbers         | T4 noise floor                                         | forge publishes mean ± stdev; hexa-codex parity row records range, not point estimate            |
| LLM-judge ratio mid-run change                           | quality-scale T4 invalidated                           | freeze judge config at start of T4 sweep; recorded in PR template `Reproducibility` block        |
| Hexa-codex spec changes mid-PR-review                    | drift                                                  | PR draft includes hexa-codex spec hash at draft time; reviewer rebases on current hexa-codex     |

## §7 Forge-side outbox layout (proposed)

```
~/core/hexa-forge/outbox/hexa-codex/
├── train_cost/
│   └── 2026-XX-XX-<run_id>.md         # F-CODEX-1 T4 PR draft
├── infer_cost/
│   └── 2026-XX-XX-<run_id>.md         # F-CODEX-2 T4 PR draft
├── quality_scale/
│   └── 2026-XX-XX-<run_id>.md
├── safety/
│   └── 2026-XX-XX-<run_id>.md
├── alignment/
│   └── 2026-XX-XX-<run_id>.md
├── adversarial/
│   └── 2026-XX-XX-<run_id>.md
├── interpret/
│   └── 2026-XX-XX-<run_id>.md
├── rlhf/
│   └── 2026-XX-XX-<run_id>.md
├── eval/
│   └── 2026-XX-XX-<run_id>.md
├── agent_serving/
│   └── 2026-XX-XX-<run_id>.md
└── deploy/
    └── 2026-XX-XX-<run_id>.md
```

## §8 Codex-side intake decision (companion)

A mirror decision lives in hexa-codex side:
[`~/core/hexa-codex/papers/plan-decisions-pending.md` D-021](../../hexa-codex/papers/plan-decisions-pending.md)
— "hexa-forge cross-link" resolved as: hexa-codex provides spec canon
to forge; **forge contributes T4 empirical data back**. PR review SLA:
≤ 2 weeks per T4 PR (target).

## Cross-link

- This doc resolves M-005 in [`plan-decisions-pending.md`](plan-decisions-pending.md).
- Triggering specs: [`../docs/code-llm.md` §VERIFY upstream feedback contract](../docs/code-llm.md#verify--serving-contract) + Cross-link policy "feedback channel".
- Hexa-codex consumption side: [`../../hexa-codex/papers/plan-execution-roadmap.md`](../../hexa-codex/papers/plan-execution-roadmap.md) v1.1.0 / v1.2.0 / v1.3.0 phases all include "hexa-forge handoff" markers.
- Hexa-codex falsifier closure tracker: [`../../hexa-codex/papers/plan-coverage-matrix.md §2`](../../hexa-codex/papers/plan-coverage-matrix.md) (T4 empirical row).
