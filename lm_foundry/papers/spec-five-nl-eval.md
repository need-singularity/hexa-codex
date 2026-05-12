<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->
<!-- SPDX-FileCopyrightText: 2026 hexa-forge contributors -->
<!-- @canonical: forge@v0.1.2:papers/spec-five-nl-eval.md -->
<!-- @owns(sections=[HEADER, WHY, COMPARE, REQUIRES, STRUCT, FLOW, EVOLVE, VERIFY, FEEDBACK, TOOLING], strict=false, order=sequential, prefix="S") -->

# `5-NL eval` — custom benchmark spec for cross-lingual code-adjacent NL

> **Acceptance gate (v1.0.0).** This spec defines benchmark **④** from
> [`docs/code-llm.md` §EVOLVE](../docs/code-llm.md#evolve--eval-harness)
> — `5-NL eval (custom) — ≥ 70% pass cross-lang`. The bar exists in the
> recipe; the **shape** is defined here. Implementation lands v0.1.3+.
>
> **Decisions referenced.** D-005 (5 NL set: **EN / KR / CN / RU / JA**
> closed — no Spanish, no Portuguese, no Arabic, no Hindi at v1.0.0),
> D-006 (NL diagnostic carve-out — diagnostics and refusal text remain
> English-canonical even when input is non-EN), D-013 (no LLM-judge or
> machine-translation for gold — Shumailov 2024 model-collapse risk).
> See [`papers/plan-decisions-pending.md`](plan-decisions-pending.md).
>
> **Sister methodology canon.** Section discipline mirrors
> [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md)
> §S1 WHY → §S7 VERIFY. The cross-lingual capability axis is the
> falsifier-anchor: pass on EN alone is **not** sufficient.

---

## S0 HEADER

| field             | value                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| verb              | `code` (sub-artifact `5-NL eval`)                                                                    |
| family            | `hexa-forge`                                                                                         |
| status            | `RESEARCH_FIRST` — spec only, runner script planned                                                  |
| dispatch          | `hexa-forge code eval --bench 5-nl`                                                                  |
| acceptance gate   | **≥ 70% pass cross-lang aggregate** (single bar — NOT per-NL)                                        |
| task count target | **1000** = 5 NLs × 200 tasks per NL (6 sub-families per NL)                                          |
| owner             | `forge.code` verb                                                                                    |
| sister gate       | benchmark **③** = `hexa-eval` ([`spec-hexa-eval.md`](spec-hexa-eval.md))                             |
| codex feedback    | `hexa-codex/quality_scale` (cross-cutter) + `hexa-codex/eval` Mk.II "multilingual eval-set design"   |
| last updated      | 2026-05-11                                                                                           |

---

## S1 WHY — why code-adjacent multilingual matters

Pure code is language-neutral. **Code-adjacent natural language is not.**
The developer population that ships the world's software writes:
- **PR comments** — review feedback, change requests, "LGTM with nit"
- **issue reports** — bug descriptions, repro steps, expected/actual
- **commit messages** — subject lines + body conventions per project
- **in-code explanations** — comments, docstrings, JSDoc, doc tests
- **task instructions** — "write a function that does X" — the
  ChatGPT-style ask

…in their own language. A `code` verb that only works when the user
writes English fails for ~70% of the global dev population.

Recipe `docs/code-llm.md §WHY` already commits to **EN (T0) + KR + CN
+ RU + JA (T1)** per D-005. This spec operationalises that commitment
as an **acceptance gate**: 5-NL pass cross-lang ≥ 70%.

**Why these 5 and not others?** D-005 closed on coverage/cost/
maintainer-availability grounds:
- **EN** — code lingua franca, must work
- **KR** — hexa-canon home; primary maintainer NL; canon-heavy
- **CN (Simplified)** — largest non-EN dev pool by absolute count
- **RU** — strong systems-programming community (Cortex-M, kernel,
  embedded C)
- **JA** — Ruby/OSS culture; Qiita/Zenn ecosystem; mature dev-docs
  tradition

Spanish/Portuguese/German/French/Arabic/Hindi are **out of scope**
for v1.0.0 — they will be considered for v2.0.0 only after the 5-NL
gate is empirically demonstrated to be reachable.

**Core falsifiable claim.** If the trained `code` verb scores ≥ 70%
on EN but < 50% on any of {KR, CN, RU, JA}, the "code-adjacent
multilingual" thesis is empirically falsified — the model has only
learned **English-flavoured code** and the multilingual filter in
`plan-multilingual-stage.md` failed to land.

## S2 COMPARE — vs public multilingual benchmarks

```
+--------------------------------------------------------------------+
|  [Task-naturalness]  (is the task itself in the NL?)               |
+--------------------------------------------------------------------+
|  MMLU-multilingual       ####.....................  knowledge MCQ |
|  HumanEval-X             ######...................  code transl.  |
|  MBPP-translate          #####....................  ask translated|
|  XLSum / FLORES          ###......................  summarization |
|  MGSM                    #######..................  math word     |
|  5-NL eval (this spec)   ##################........ ask NL→code NAT|
+--------------------------------------------------------------------+
|  [Task surface alignment to dev work]                              |
+--------------------------------------------------------------------+
|  HumanEval-X             ########.................  function only |
|  CodeXGLUE               ##########................  many tasks   |
|  5-NL eval               ##################........ PR/issue/commit|
+--------------------------------------------------------------------+
|  [Cross-NL parity discipline]                                      |
+--------------------------------------------------------------------+
|  HumanEval-X             ######...................  EN-anchor     |
|  XCOPA                   ########.................  reasoning par |
|  5-NL eval               ##################........ explicit ≤15pp|
+--------------------------------------------------------------------+
```

**Why "task-natural" matters.** HumanEval-X translates the **instruction**
into KR/CN/JA but keeps the task identity (function synthesis). 5-NL
eval is broader: 6 sub-families that map to actual developer
activities, not just "function from prompt." It is **also**
task-natural in the HumanEval-X sense (the task is given in the NL;
the model outputs code or NL), not a translation-of-EN task.

**5-NL eval's niche.** Complementary to HumanEval-X (function
synthesis) — covers the **other** 5 dev activities (bug-fix, code
explanation, commit message, issue triage, refusal) that public
multilingual code benches don't measure. Together with hexa-eval
(hexa-fidelity) and HumanEval+ (general synthesis), it closes the
acceptance-bar matrix.

## S3 REQUIRES — prerequisites

| prerequisite                                                  | source / location                                                                  | check                |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------- |
| **D-005 closed** — 5 NL set frozen                            | [`plan-decisions-pending.md §4`](plan-decisions-pending.md) row D-005              | resolved 2026-05-11  |
| **D-006 closed** — diagnostic carve-out (refusal EN canonical) | [`plan-decisions-pending.md §4`](plan-decisions-pending.md) row D-023 (now D-006)  | resolved 2026-05-11  |
| Native-speaker authors                                        | ≥ 2 per NL (KR, CN, RU, JA); EN by default                                         | sign-off recorded    |
| License-clean source prose for tasks                          | per [`plan-multilingual-stage.md §3`](plan-multilingual-stage.md) per-NL source map | per-row audit       |
| Refusal text canon                                            | `out-of-domain: this is a code-only model` (EN, byte-exact)                        | recipe §VERIFY       |
| NL-detection probe                                            | fastText `lid.176.bin` or CLD3 — for spot-check, not gating                        | binary on $PATH      |
| Multilingual stage filter design                              | [`plan-multilingual-stage.md`](plan-multilingual-stage.md) §1-§4                   | M-003 DESIGN_LOCKED  |

**No machine-translation as gold.** A KR task is authored by a KR
speaker. A CN task is authored by a CN speaker. Round-trip MT for
gold answers is **forbidden** (per
[`plan-multilingual-stage.md §3 reject list`](plan-multilingual-stage.md)).
The eval slice is the **only** place forge spends genuine human-author
budget at v0.1.x — the corpus stages are mined, but the bench is
hand-built.

**Stage ordering.** `5-NL eval` is **independent** of `hexa-eval` —
the two run in parallel and aggregate separately. T8 in hexa-eval
overlaps T6 (refusal) here intentionally (5-NL refusal is the floor
in both specs).

## S4 STRUCT — task taxonomy

5 NLs × 200 tasks per NL = **1000** total. 6 sub-families, mirroring
real developer activity types.

### S4.1 Per-NL task family table

Per-NL count breakdown (identical shape across all 5 NLs to keep
parity meaningful):

| sub-family ID | activity                       | per-NL count | input → output                                       | scoring               |
| ------------- | ------------------------------ | ------------ | ---------------------------------------------------- | --------------------- |
| F1            | function synthesis             | 50           | NL instruction → code (any of Python/Rust/TS/Go/hexa) | unit test exec        |
| F2            | bug-fix                        | 50           | NL bug description + buggy code → fixed code         | unit test exec        |
| F3            | code explanation               | 30           | code → NL summary (in the input NL)                  | back-translation parity |
| F4            | commit message generation      | 30           | diff → NL commit subject + body                      | rubric + reviewer     |
| F5            | issue triage                   | 30           | NL issue text → root-cause hypothesis + repro        | reviewer label match  |
| F6            | refusal correctness            | 10           | off-domain NL request → English-canonical refusal    | byte-exact match      |
|               | **per-NL total**               | **200**      |                                                      |                       |

**5 NLs × 200 = 1000 total tasks.**

### S4.2 Per-sub-family detail

**F1 — function synthesis (50 per NL = 250 total).** NL instruction
in the target NL. Output: code in one of the recipe's core languages
(Python / Rust / TS / Go / C / hexa). The **output language** is
specified in the task. Pass criterion: candidate code passes the
task's hidden unit-test set (typically 3-5 tests per task). Mirrors
HumanEval-X scope but with hexa added and the instruction native to
the NL (not translated from EN).

**F2 — bug-fix (50 per NL = 250 total).** Input: NL bug report (in
the NL) + buggy source. Output: patched source. Pass criterion:
candidate's patch passes the hidden unit tests **and** the original
test that demonstrated the bug. Mining source: GitHub PRs with NL
descriptions that fix a `bug` / `regression` label, license-clean.

**F3 — code explanation (30 per NL = 150 total).** Input: a code
snippet (any core lang). Output: NL summary, in the **same NL as the
NL surface of this row** (KR row produces KR summary). Pass criterion:
**back-translation parity** — the candidate's NL summary, given as
input to a separate F1-style task ("write code that does X"), produces
code that is **AST-equivalent up to renaming** to the original snippet.
This avoids prose-similarity scoring (subjective) by reducing
explanation quality to a downstream code-synthesis task.

**F4 — commit message generation (30 per NL = 150 total).** Input:
a unified diff. Output: NL commit message (subject ≤ 72 chars + body
≤ 6 lines wrapped at 72) in the NL. Pass criterion: combined of (a)
deterministic rubric (subject ≤ 72, body wrapped, imperative mood
per Conventional Commits spec) and (b) ≥ 1 native-speaker reviewer
marks the message as "what I would write." Reviewer agreement
threshold: ≥ 2/3 reviewers per task agree (recorded once at task-set
freeze; not re-asked per model run).

**F5 — issue triage (30 per NL = 150 total).** Input: an NL issue
text (in the NL). Output: a structured `{hypothesis, minimal_repro}`
pair where `hypothesis` is in the NL and `minimal_repro` is code.
Pass criterion: `minimal_repro` runs and **reproduces the symptom**
described in the issue (the runner has a hidden "symptom-detection"
function per task). Hypothesis text is graded **diagnostic-only** —
not part of pass/fail.

**F6 — refusal correctness (10 per NL = 50 total).** Input: off-domain
prose request in the NL ("write me a haiku in Korean"). Output: the
**English-canonical** refusal string `out-of-domain: this is a code-
only model`. Pass criterion: byte-exact match. **The EN canonical
text is the same regardless of input NL** — that is the entire point
of D-006 (diagnostic carve-out). **Mirrors `hexa-eval` T8** —
intentionally redundant so either spec can stand on its own.

### S4.3 Per-NL task budget rationale

```
per-NL = 50 + 50 + 30 + 30 + 30 + 10 = 200
NL count = 5
total = 1000
```

200 per NL is the **minimum** for stable rank correlation at the
sub-family level (per `ai-eval-pipeline.md §S7.4` sensitivity
analysis — 100+ items gives ρ > 0.8 rank stability; 200 gives margin
for sub-family slicing of size 30-50). Going below 200 per NL would
make per-NL diagnostics noisier than the 15pp parity check (S7.3
below) can support.

## S5 FLOW — task curation + scoring discipline

```
[1] Author recruitment  --> [2] Per-NL authoring (200/NL)
        |                          |
        v                          v
   ≥2 native authors/NL    license-clean source-prose corpus
   sign-off recorded       (per plan-multilingual-stage §3)
        |                          |
        +-------+-----------+------+
                |
                v
       [3] Gold-set freeze + hash-pin
       (1000 tasks; SPEC.md + task_set hash)
                |
                v
       [4] Reviewer cross-check (F4 only)
       ≥ 2/3 agree per task; otherwise drop
                |
                v
       [5] Candidate response  -->  [6] Score
                |                       |
                v                       v
       per sub-family algorithm   aggregate + per-NL + parity check
                |                       |
                +---------+-------------+
                          |
                          v
            [7] Emit to outbox/hexa-codex/quality_scale/
            [8] Emit to outbox/hexa-codex/eval/ (Mk.II input)
```

### S5.1 Authoring discipline (D-013 enforced)

- **Native authors only.** Round-trip machine translation is rejected
  outright (model-collapse adjacent — same Shumailov 2024 risk
  applies to bench text as to training corpora).
- **License-clean prose sources** for any mined inputs (commit-message
  corpora, issue-tracker text) per
  [`plan-multilingual-stage.md §3`](plan-multilingual-stage.md):
  EN clean; KR own-license; CN/RU/JA per-source audit; reject medium
  / dev.to / hashnode post-2023; reject Habr articles without
  per-article license confirmation.
- **One author may not author > 30%** of any single NL's tasks
  (anti-stylistic-monoculture).

### S5.2 Scoring algorithm (per-task)

```
score(task, candidate):
    1. emit = candidate(task.input)
    2. if task.family == F1 or F2:
         return run_unit_tests(emit, task.tests) == ALL_PASS
    3. if task.family == F3:
         summary = emit  # NL text
         resynth = synthesis_model(summary)   # SAME candidate, F1-style call
         return ast_equal_modulo_renaming(parse(resynth), parse(task.original_code))
    4. if task.family == F4:
         rubric_pass = subject_len(emit) <= 72 and body_wrapped(emit) and imperative(emit)
         reviewer_pass = task.reviewer_agreement >= 2  # frozen at task-set freeze
         return rubric_pass and reviewer_pass
    5. if task.family == F5:
         return reproduces_symptom(emit.repro, task.symptom_probe)
    6. if task.family == F6:
         return emit == "out-of-domain: this is a code-only model"
    7. tally per (NL, sub-family) + aggregate + parity check
```

### S5.3 Determinism + reproducibility

- Each task: `task_id` + `nl` tag + `sub_family` + `gold_hash` +
  `author_id` + `reviewer_ids`.
- Runner config pins: candidate model SHA + task-set hash + tool
  versions (compiler / unit-test runner / NL-detection probe).
- Temperature = 0 for primary report. `pass@k` (k=5, temperature=0.7)
  reported as secondary diagnostic.

## S6 EVOLVE — Mk.I → Mk.V progression

Mirrors hexa-codex `eval/ai-eval-pipeline.md §S6 EVOLVE`.

- **Mk.I (1 month) — EN-only baseline + KR pilot.** ~250 tasks (EN
  200 + KR pilot 50, all 6 sub-families on EN, F1+F6 only on KR).
  Goal: establish that the bench discriminates **at all** between an
  English-only candidate (e.g. pre-mix base) and a 5-NL-mix
  candidate. **Gate at Mk.I: KR pilot pass-rate within 25pp of EN
  on F1.**

- **Mk.II (2 months) — full 5 NL × 200 tasks.** All 1000 tasks live.
  Automated scoring for F1/F2/F3/F5/F6; F4 reviewer agreements
  pre-frozen. `tool/run_5nl_eval.py` (S9) emits per-NL JSON + cross-
  NL parity table. **Gate: aggregate ≥ 50% on SFT-bias-only candidate
  + parity drop ≤ 25pp** (Mk.II is calibration, not release).

- **Mk.III (3 months) — adversarial NL perturbation + cross-NL probe.**
  Each F1/F2 task perturbed: paraphrase in NL (native author rewrites
  the same task differently), code-language swap (F1 Python → Rust),
  named-entity scramble for F5. Cross-NL probe: take EN F6 refusal
  prompts and **prepend KR/CN/RU/JA phrases** ("please answer in
  English") to confirm the refusal canon holds under code-switching.
  **Gate: parity drop under perturbation ≤ 20pp.**

- **Mk.IV (4 months) — full pipeline + hexa-forge CI integration.**
  Per-NL canary slice (~20 tasks per NL, 100 total) runs on every
  forge PR that touches the multilingual filter or tokenizer; full
  1000-task run on tag-pushes. Output routes per
  [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md).
  **Gate: aggregate ≥ 70% + per-NL parity ≤ 15pp + F6 = 100% per NL,
  across 3 consecutive CI runs** on RC weights.

- **Mk.V (long-term) — industry-standard + contamination quarantine.**
  Task set published with cryptographic hash per NL. Downstream
  forks must prove non-leakage. Task rotation: F1/F2 quarterly
  (generatable from a per-NL task template by native authors),
  F3/F4/F5/F6 yearly (effort-bound). Per-NL leakage check is **per
  language** — KR n-gram overlap against KR training corpus is
  independent of EN overlap (different corpora, different leakage
  surfaces).

| Mk    | scope                                              | pass criterion                                                  | unlocks                          |
| ----- | -------------------------------------------------- | --------------------------------------------------------------- | -------------------------------- |
| Mk.I  | EN-200 + KR-50 pilot                               | KR F1 within 25pp of EN F1                                      | greenlight full per-NL authoring |
| Mk.II | Full 5 NL × 200                                    | aggregate ≥ 50% + parity ≤ 25pp                                 | wire into CI                     |
| Mk.III | + perturbation + cross-NL probe                   | parity drop ≤ 20pp under adversarial                            | publish bench v1                 |
| Mk.IV | + CI integration + feedback PR                     | aggregate ≥ 70% + per-NL parity ≤ 15pp + F6 = 100% × 3 CI runs  | **v1.0.0 forge release**         |
| Mk.V  | + contamination quarantine + per-NL rotation       | hash-pinned, leak-audited per NL                                | community-standard candidate     |

## S7 VERIFY — acceptance bar + parity discipline

### S7.1 Acceptance arithmetic — the **single bar**

- **Aggregate gate.** `passed / 1000 ≥ 0.70` ⇒ release-eligible (this
  bench alone; other §EVOLVE rows must also hold).
- **Single bar by design.** The bar is **NOT** per-NL — it is the
  combined cross-lingual pass rate. A model that scores 95% on EN
  and 50% on every other NL aggregates to 0.95×0.2 + 0.5×0.8 = 0.59
  → **fail** at 70%. A model that scores 70% on every NL aggregates
  to 0.70 → **pass**. **The single-bar design intentionally
  penalises EN-favouritism.**

### S7.2 Per-NL diagnostic floor (refusal must be 100%)

- **F6 must be 100%** in every NL. This is **NOT** part of the 70%
  aggregate — it is a **separate, blocking** diagnostic. A model
  that scores 75% aggregate but refuses correctly only in EN fails
  the gate (the refusal text must be **English-canonical regardless
  of input NL** per D-006; failure here means the diagnostic
  carve-out was not learned).
- F6 = 100% per NL means: all 10 F6 tasks per NL must produce the
  byte-exact refusal string. Single byte off = full F6-per-NL fail =
  release blocked.

### S7.3 Per-NL parity check (≤ 15pp variance)

- **Parity bar.** `max(per_nl_passrate) - min(per_nl_passrate) ≤ 0.15`
  across the 5 NLs. This is the **cross-lingual capability** check
  — the model must be **actually** multilingual, not "English plus
  rote responses in 4 other NLs."
- Parity is computed on F1+F2+F3+F5 (the four code-correctness
  sub-families). F4 reviewer-based scores are excluded from parity
  (reviewer culture differs per NL — variance there is not a model
  failure). F6 is excluded because it has its own 100% floor.
- A parity bar > 15pp **with** an aggregate ≥ 70% is **release-
  blocked** — the recipe is honest about its EN-favouritism and the
  multilingual filter is empirically inadequate.

### S7.4 Failure taxonomy

| failure code        | meaning                                                                       | sub-family    | aggregate impact |
| ------------------- | ----------------------------------------------------------------------------- | ------------- | ---------------- |
| `TEST_FAIL`         | unit tests don't pass                                                         | F1, F2        | fail             |
| `BACKTRANS_DRIFT`   | F3 re-synthesis didn't AST-match original (modulo renaming)                   | F3            | fail             |
| `RUBRIC_FAIL`       | commit-msg rubric (subject ≤ 72, body wrap, imperative) violated              | F4            | fail             |
| `REVIEWER_REJECT`   | < 2/3 reviewer agreement (frozen-time) — task pre-dropped, not a model fail  | F4            | task excluded    |
| `SYMPTOM_NOT_REPRO` | F5 repro didn't trigger the symptom                                           | F5            | fail             |
| `REFUSAL_DRIFT`     | F6 output != byte-exact English canon                                         | F6            | fail + diag-block|
| `WRONG_NL_OUTPUT`   | F3 summary in the wrong NL (e.g. EN where KR expected)                        | F3            | fail             |
| `PASS`              | all checks green                                                              | all           | pass             |

### S7.5 What doesn't count as a 5-NL eval failure

- Stylistic NL choice within the same NL (informal vs formal KR —
  both pass if the **content** is correct).
- Code-language choice within the task's `allowed_langs` set (F1
  often allows {Python, Rust, TS} — any works).
- Whitespace / punctuation in non-string contexts.
- F4 prose disagreement among reviewers — pre-resolved at freeze.

### S7.6 Cross-spec floor: refusal canon

**Shared canon with hexa-eval T8.** Both specs require byte-exact
English refusal text regardless of input NL. The two specs are
intentionally **redundant** on this floor — D-006 is important
enough to test in both surfaces. A model passing hexa-eval T8 should
trivially pass 5-NL F6 (the test surface is the same; only the
input prose differs).

## S8 FEEDBACK — upstream channel

Per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md),
5-NL eval results route to:

| forge output                                                  | hexa-codex destination                                                                   | PR shape                                                                          | falsifier T4               |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------- |
| Aggregate 5-NL pass rate + per-NL slice                       | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)         | cross-cutter contribution: multilingual axis added to quality table               | cross-cutter               |
| Per-NL parity table + adversarial-perturbation drop           | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.II item     | direct empirical input to **Mk.II "multilingual eval-set design"** item           | meta (wraps F-1..4)        |
| Refusal-rate matrix (5 NL × F6) + cross-NL refusal probe      | [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md) + alignment + adversarial    | refusal table per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md) | **F-CODEX-3 T4** input    |

The hexa-codex `eval` verb's Mk.II promotion criterion **explicitly
lists** "multilingual eval-set design" as a deliverable. 5-NL eval
is precisely that artifact — the forge produces the design, the codex
verb absorbs it as the live methodology canon.

**Outbox path** (per `plan-feedback-channel-ops.md §7`):
- `outbox/hexa-codex/quality_scale/<run_id>-5nl.md`
- `outbox/hexa-codex/eval/<run_id>-5nl-methodology.md`
- `outbox/hexa-codex/safety/<run_id>-5nl-refusal.csv`
- `outbox/hexa-codex/alignment/<run_id>-5nl-refusal.md`
- `outbox/hexa-codex/adversarial/<run_id>-5nl-codeswitch.md`

### S8.1 Contribution to v1.0.0 forge gate

`docs/code-llm.md §VERIFY upstream feedback contract` requires ≥ 5
PRs landed in hexa-codex. 5-NL eval contributes up to **five** PRs
by design (quality_scale + eval-methodology + safety + alignment +
adversarial). Combined with `hexa-eval` (2 PRs) and at least one of
{train_cost / infer_cost} T4, the gate is easily reachable.

## S9 Tooling

Two scripts (planned; not yet written):

| script                             | reads                                                          | writes                                                                                                                          | status  |
| ---------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `tool/run_5nl_eval.py`             | `tests/5nl-eval/<NL>/tasks/*.toml` + candidate model endpoint  | `runs/<id>/5nl-eval.parquet` + per-(NL, sub_family) JSON                                                                        | PLANNED |
| `tool/emit_5nl_eval_pr.py`         | `runs/<id>/5nl-eval.parquet`                                   | `outbox/hexa-codex/{quality_scale,eval,safety,alignment,adversarial}/<id>-5nl-*.md`                                              | PLANNED |

Both follow the existing `tool/emit_t4.py` shape (already in repo).
`run_5nl_eval.py` is the bench runner; `emit_5nl_eval_pr.py` is the
codex-PR emitter. Wiring matches
[`plan-feedback-channel-ops.md §3`](plan-feedback-channel-ops.md)
automation triggers — emit on bench-run-complete.

**Determinism contract.** Same as hexa-eval:
- `SOURCE_DATE_EPOCH` for any timestamps
- pinned hashes for task set + candidate model SHA
- exit code 0 on aggregate + parity + F6 = 100% all green; non-zero
  with structured stderr on any of (aggregate < 70%, parity > 15pp,
  F6 < 100% per NL)

**Not in scope for v0.1.3.** Actual per-NL task TOMLs
(`tests/5nl-eval/{en,ko,zh,ru,ja}/tasks/`), gold answers, native-
author sign-off records, or runner implementation — those land
v0.1.3+ after author recruitment closes and D-007 (base weights)
makes a candidate model available.

---

## Open questions (v0.1.2 → v0.1.3 handoff)

- [ ] **D-NEW-D (this spec)** — F4 reviewer-pool size: 2 vs 3
      reviewers per NL? *Proposed: 3 reviewers per NL for first
      freeze, ≥ 2/3 agreement, scaled down to 2 reviewers ≥ 2/2 if
      author budget is tight.*
- [ ] **D-NEW-E (this spec)** — F3 back-translation parity tolerance:
      AST-equal-modulo-renaming is the proposed default; should it
      also tolerate function decomposition (refactored into helpers
      semantically equivalent)? *Proposed: strict modulo-renaming
      at Mk.II; loosen at Mk.III with documented equivalence rules.*
- [ ] **D-NEW-F (this spec)** — Should F5 (issue triage) hypothesis
      text feed back into `hexa-codex/alignment` as diagnostic
      training-signal data? *Proposed: diagnostic-only at v1.0.0;
      revisit if SAE-trained F-CODEX-4 analog wants the texture.*
- [ ] **D-NEW-G (this spec)** — Per-NL parity bar of 15pp: should
      it tighten over Mk.IV → Mk.V? *Proposed: hold at 15pp through
      v1.0.0; tighten to 10pp at v2.0.0 only if v1.0.0 demonstrably
      cleared 15pp by ≥ 5pp margin.*

Resolved decisions referenced by this spec:
- D-005 (5 NL set: EN/KR/CN/RU/JA) — closed 2026-05-11
- D-006 / D-023 (NL diagnostic carve-out — refusal EN canonical) — closed 2026-05-11
- D-013 (no LLM-judge / no MT for gold) — closed 2026-05-11
- M-003 (multilingual stage filter design) — closed 2026-05-11

---

## Cross-link

- Recipe SSOT: [`../docs/code-llm.md`](../docs/code-llm.md) §EVOLVE row 7 (acceptance gate ④).
- Sister spec: [`spec-hexa-eval.md`](spec-hexa-eval.md) (acceptance gate ③) — T8 mirrors F6.
- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md) (D-005, D-006, D-013, M-003).
- Multilingual stage filter (input source map + reject list): [`plan-multilingual-stage.md`](plan-multilingual-stage.md).
- Feedback channel ops: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md).
- Methodology canon: [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md) §S1 WHY (multilingual bias), §S6 EVOLVE Mk.II (multilingual eval-set design item), §S7.4 SENSITIVITY (200-item floor).
- Hexa SPEC.md §7 (refusal contract source): [`~/core/hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md).
