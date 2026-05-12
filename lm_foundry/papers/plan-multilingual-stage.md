# plan — multilingual stage filter design (M-003)

> **Resolves M-003.** D-022 (5 NL coverage) + D-023 (NL diagnostic
> carve-out) are already closed; this doc specifies HOW the
> multilingual filter operates inside the existing stages.

| field        | value                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------- |
| status       | `DESIGN_LOCKED`                                                                             |
| applies to   | `domain-bias`, `build-trace`, `diff-edit`, `repair`, `philosophy` stages                    |
| does NOT add | new top-level stage (decision in §STRUCT of `docs/code-llm.md`)                             |
| last updated | 2026-05-11                                                                                  |

---

## §1 NL tag schema

Every sample entering forge gets a frontmatter / sidecar JSON line:

```
{
  "nl": "en" | "ko" | "zh" | "ru" | "ja" | "mixed" | "code-only",
  "nl_confidence": 0.0..1.0,
  "primary_code_lang": "rust" | "python" | "ts" | "go" | "c" | "zig" | "hexa" | "sql" | ...,
  "stage": "domain-bias" | "build-trace" | "diff-edit" | "repair" | "philosophy",
  "license": "MIT" | "Apache-2.0" | "CC-BY-4.0" | ...,
  "src_url": "<canonical url>",
  "extracted_at": "YYYY-MM-DD",
  "weight": 1.0   // ×10 for hexa-canon / philosophy Tier D
}
```

Detection:
- **Code-only** (zero prose) → tag `nl: code-only`, weight unchanged.
- **Mixed prose + code** → detect prose lang via fastText `lid.176.bin`
  (CC-BY-SA, 176-lang capable) or CLD3 (Apache-2). Confidence ≥ 0.85
  required for non-EN tag; otherwise default to `en`.
- **PR / commit / issue text** → tag based on the text portion only;
  code-only diff is `nl: code-only`.

## §2 Stage-by-stage filter rules

| stage          | NL filter / weighting                                                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `pretrain-bias` | Stack v2 permissive is code-only by design. No NL filter required — defer multilingual learning to other stages.                       |
| `domain-bias`  | crates/npm/PyPI docs are EN-dominant; do not artificially upsample non-EN docs (license-clean rarely permits).                          |
| `build-trace`  | tool output is EN. Locale-specific error messages (LC_ALL=C) — normalise to EN. No NL filter.                                          |
| `diff-edit`    | PR diffs: filter prose to ≥ 0.85 confidence on tagged NL. **Target mix: EN ~70%, KR+CN+RU+JA aggregate ~30%** (resampled).             |
| `repair`       | test failure → fix narratives: filter same as `diff-edit`. Linter-autofix samples (Tier E) are code-only and exempt.                   |
| `philosophy`   | Tier A canon is EN-dominant (PEPs / Rust Book / Effective Go). Tier B/C similarly EN. Tier D (`hexa-canon`) is KR-heavy — preserve it. |

## §3 Per-NL source map

| NL          | volume signal                                                       | source candidates                                                                  | license posture            |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------------- |
| **English (T0)** | dominant in Stack v2, all top-tier docs, ~70% PR comments     | every Tier A/B/C/D primary source                                                  | clean                      |
| **Korean (T1)**  | `~/core/hexa-*` repos (canon-heavy KR), Korean GitHub PRs     | hexa-canon §-docs ×10 (Tier D); KR PR diffs (perm-licensed repos only)             | own license; small volume  |
| **Chinese (T1, Simplified)** | largest non-EN dev pool; GitHub issues; mirror sites  | GitHub issue/PR comments on permissive-licensed CN-owned projects                  | mixed — per-repo audit      |
| **Russian (T1)** | strong systems-prog community                                  | GitHub issue/PR comments on permissive-licensed RU-owned projects; **Habr → per-article license gate (CC-BY-SA 3.0 common but not universal)** | mixed — per-source audit |
| **Japanese (T1)** | Ruby / OSS culture; Qiita / Zenn                              | GitHub issue/PR comments on JP-owned projects; **Qiita → per-article license gate; Zenn → CC0 by default** | mixed — per-source audit |

**Reject list (do NOT source from):**
- medium.com / dev.to / hashnode post-2023 (LLM-slop pollution per Tier E)
- machine-translation between langs (round-trip noise)
- benchmark contamination sources (HumanEval+ / SWE-bench / hexa-eval prose) → mark `bench-text` and exclude from training

## §4 Rebalance algorithm (per epoch)

Target distribution at the **prose token** level (excludes `code-only`
samples which dominate raw count):

```
target_mix = {
  "en": 0.70,
  "ko": 0.075,
  "zh": 0.075,
  "ru": 0.075,
  "ja": 0.075,
}
```

Pre-epoch:
1. count tokens per `nl` tag across all eligible samples
2. compute resampling weight `w_nl = target_mix[nl] / observed_share[nl]`
3. clamp `w_nl` to `[0.25, 4.0]` to avoid extreme oversampling that
   would re-pollinate small corpora into memorisation
4. shuffle with `w_nl`-weighted reservoir sampling

Re-check at epoch end; abort training if the realised mix drifts
> 5 percentage points from target — usually means tag drift.

## §5 Diagnostic carve-out (D-023 implementation)

`docs/code-llm.md §VERIFY refusal contract` requires **diagnostics
English-only** per hexa-lang SPEC §7. Concrete implementation:

- All compiler error / lint / refusal text — English canonical strings.
- Multilingual support at inference is **input-detection only**: model
  can accept Korean prose explaining a task, but its compiler-style
  diagnostics and refusal text remain English.
- This mirrors hexa-lang's own decision (Korean i18n permanently closed)
  — forge enforces the same downstream.

## §6 Eval slice

`hexa-eval` and the dedicated **5-NL eval** in `docs/code-llm.md
§EVOLVE`:

- 5 NL × N tasks (~200 tasks per language) = 1000 samples
- Each task: instruction in NL, expected code output (in primary code
  lang), expected diagnostic output (English-canonical).
- Acceptance bar: ≥ 70% cross-lang pass (single bar; not per-NL).

## §7 Upstream feedback to hexa-codex

5-NL pass results feed into:
- [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S1 WHY:
  "Multilingual: English-centric benchmark bias → Balanced multilingual
  evaluation" — forge's actual multilingual pass-rate distribution
  becomes empirical evidence for the eval verb's Mk.II adaptive-test
  + multilingual eval-set design.
- [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md):
  per-NL pass rate becomes a quality-scaling axis. Per
  [`docs/code-llm.md` Cross-link feedback channel](../docs/code-llm.md#feedback-channel-forge--codex-pr-map).

## Cross-link

- Decisions: [`plan-decisions-pending.md`](plan-decisions-pending.md)
  D-022 + D-023 (resolved); M-003 (this doc resolves).
- Recipe spec: [`../docs/code-llm.md`](../docs/code-llm.md) §WHY 5-NL
  bullet, §STRUCT `diff-edit` 5-NL filter row, §EVOLVE 5-NL eval row,
  §VERIFY refusal-contract NL-aware.
- Hexa-lang SPEC.md §7: [`../../hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md)
  "English only" diagnostic rule (the source of D-023).
