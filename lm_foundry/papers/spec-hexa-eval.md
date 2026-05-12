<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->
<!-- SPDX-FileCopyrightText: 2026 hexa-forge contributors -->
<!-- @canonical: forge@v0.1.2:papers/spec-hexa-eval.md -->
<!-- @owns(sections=[HEADER, WHY, COMPARE, REQUIRES, STRUCT, FLOW, EVOLVE, VERIFY, FEEDBACK, TOOLING], strict=false, order=sequential, prefix="S") -->

# `hexa-eval` — custom benchmark spec for hexa-lang fidelity

> **Acceptance gate (v1.0.0).** This spec defines benchmark **③** from
> [`docs/code-llm.md` §EVOLVE](../docs/code-llm.md#evolve--eval-harness)
> — `hexa-eval (custom) — ≥ 80% pass`. The bar exists in the recipe;
> the **shape** is defined here. Implementation lands v0.1.3+.
>
> **Decisions referenced.** D-005 (5 NL set: EN/KR/CN/RU/JA), D-006 (NL
> diagnostic carve-out — refusal English-canonical), D-013 (no LLM-judge
> for golden-output synthesis — Shumailov 2024 model-collapse risk),
> D-021 (hexa fidelity contract — S0–S8 lint stages, `HX[CCCC]` codes,
> `@grace` 3-field, arena-only, no-Z3/CVC5, no-LLVM, English-only).
> See [`papers/plan-decisions-pending.md`](plan-decisions-pending.md).
>
> **Sister methodology canon.** Section discipline (S-prefix, falsifier-
> anchored, arithmetic floor → numerics → parity → live) mirrors
> [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md).
> Forge does not duplicate methodology — it instantiates it for one
> custom benchmark.

---

## S0 HEADER

| field             | value                                                              |
| ----------------- | ------------------------------------------------------------------ |
| verb              | `code` (sub-artifact `hexa-eval`)                                  |
| family            | `hexa-forge`                                                       |
| status            | `RESEARCH_FIRST` — spec only, runner script planned                |
| dispatch          | `hexa-forge code eval --bench hexa-eval`                           |
| acceptance gate   | **≥ 80% pass** over all task families (single bar)                 |
| task count target | **~750** (T1=200, T2=150, T3=50, T4=100, T5=100, T6=50, T7=50, T8=50) |
| owner             | `forge.code` verb                                                  |
| sister gate       | benchmark **④** = `5-NL eval` ([`spec-five-nl-eval.md`](spec-five-nl-eval.md)) |
| codex feedback    | `hexa-codex/quality_scale` (cross-cutter) + `hexa-codex/eval` (methodology) — per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md) |
| last updated      | 2026-05-11                                                         |

---

## S1 WHY — why a custom hexa-lang eval is needed

Every public code benchmark — **HumanEval+ / SWE-bench Lite /
LiveCodeBench / MBPP / BigCodeBench / Aider-bench** — was authored
**before hexa-lang existed**. None of them contain hexa source, hexa
canon §-doc shape, `HX[CCCC]` error codes, `@implements(L[<id>])`
binding discipline, `@grace(HXxxxx, until=YYYY-MM-DD, reason="…")`
three-field annotation, or the firmware-stdlib direction enforcement
(`firmware/*` modules MUST reject host-stdlib imports).

A model that scores well on HumanEval+ tells us **nothing** about
whether it can emit a single line of canonical hexa. The hexa-fidelity
axis is the **differentiator** of the `code` verb — without it, forge
collapses into "yet another Qwen-Coder fine-tune." With it, forge
delivers the one capability hexa-codex's `quality_scale` cannot pull
off the shelf.

| axis                            | public benches cover  | hexa-eval covers  | gap closed by hexa-eval |
| ------------------------------- | --------------------- | ----------------- | ----------------------- |
| general Python/Rust/TS function | yes (HumanEval+)      | no                | n/a (already measured)  |
| hexa-lang syntax                | **no**                | **yes** (T1)      | hexa never trained on   |
| canon §-doc + atlas L[*]        | **no**                | **yes** (T2)      | canon-fidelity prior    |
| `@grace` 3-field discipline     | **no**                | **yes** (T3)      | hexa SPEC §6 enforcement |
| RFC-020 enum payload shape      | **no**                | **yes** (T4)      | sum-type canon          |
| `HX[CCCC]` code routing         | **no**                | **yes** (T5)      | diagnostic discipline    |
| in-house linker target literacy | **no**                | **yes** (T6)      | firmware target reality  |
| firmware vs host stdlib gate    | **no**                | **yes** (T7)      | RTSC/CHIP/CERN/ANTI/SPACE |
| 5-NL refusal canonicalisation   | partial (EN refusal)  | **yes** (T8)      | D-006 carve-out          |

**Core falsifiable claim.** If the trained `code` verb cannot pass
hexa-eval at ≥ 80%, the **"hexa-native programming model"** thesis is
empirically falsified for the v1.0.0 release. Recipe must downgrade
or retrain.

## S2 COMPARE — vs public code benchmarks

```
+--------------------------------------------------------------------+
|  [Discrimination on hexa-fidelity axis]                            |
+--------------------------------------------------------------------+
|  HumanEval+              ##.......................  none           |
|  SWE-bench Lite          ##.......................  none           |
|  LiveCodeBench           ###......................  recency only   |
|  MBPP                    ##.......................  none           |
|  BigCodeBench            ####.....................  general only   |
|  Aider-bench             #####....................  diff-edit only |
|  hexa-eval (this spec)   ##################........ hexa-only      |
+--------------------------------------------------------------------+
|  [Contamination resistance] (defense vs training leakage)          |
+--------------------------------------------------------------------+
|  HumanEval+              ##.......................  saturated      |
|  SWE-bench Lite          #####....................  fix-PR leakage |
|  LiveCodeBench           ###############..........  date-rotation  |
|  hexa-eval               ##################........ unseen lang*   |
+--------------------------------------------------------------------+
|  [Coverage of hexa SPEC.md sections]                               |
+--------------------------------------------------------------------+
|  HumanEval+              ##.......................  zero           |
|  hexa-eval T1            #####....................  §3 syntax      |
|  hexa-eval T2            ########.................  §8 atlas L[*]  |
|  hexa-eval T3            ###########..............  §6 @grace      |
|  hexa-eval T4            ##############...........  RFC-020 enum   |
|  hexa-eval T5            ################.........  §5 HX[CCCC]    |
|  hexa-eval T6            ##################.......  §18 firmware   |
|  hexa-eval T7            ###################......  §18 stdlib dir |
|  hexa-eval T8            ####################.....  §7 refusal     |
+--------------------------------------------------------------------+
```

\*hexa-lang post-dates every public dataset's training cutoff at the
time of forge v0.1.2; contamination quarantine still required at
Mk.V (see S6).

**hexa-eval's niche.** It is **complementary**, not competitive, to
public benches. The `code` verb is expected to pass HumanEval+ ≥
DeepSeek-Coder-V2-7B (recipe §EVOLVE row 1) **and** pass hexa-eval ≥
80%. A model that passes one but not the other fails the v1.0.0 gate.

## S3 REQUIRES — prerequisites

| prerequisite                                                   | source / location                                                                            | check         |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------- |
| hexa-lang SPEC.md accessible (canon §-doc shape, HX codes, L[*]) | [`~/core/hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md) — pinned at task-set freeze time       | hash-pinned   |
| S0–S8 lint stages runnable                                     | `hexa cc --lint=S0..S8` — invoked by runner                                                  | binary on $PATH |
| In-house hexa compiler binary                                  | `hexa cc` (PRIMARY pipeline per D-029)                                                       | exit-0 on fixtures |
| Target triple support                                          | `thumbv7em-none-eabihf`, `riscv32imac-unknown-none-elf`, `xtensa-esp32-none-elf`             | linker green  |
| RFC-020 enum canon                                             | [`~/core/hexa-lang/rfc/RFC-020-enum-payload.md`](../../hexa-lang/rfc/RFC-020-enum-payload.md)| RFC LANDED    |
| 5-NL refusal canon text                                        | hexa SPEC §7 "diagnostics English-only" string table                                         | byte-exact match |
| Atlas `L[*]` node IDs                                          | hexa canon atlas (referenced by `@implements(L[<id>])`)                                      | ID set frozen |
| Native-speaker reviewers for T8 inputs                         | ≥ 1 reviewer per NL among EN / KR / CN / RU / JA (D-005 set)                                 | sign-off recorded |

**Stage ordering.** `hexa-eval` runs only **after** all S0–S8 lint
stages pass for the candidate's emitted output. A response that fails
S0 is a **compile fail** (counted, but not equivalent to intent fail —
see S7).

**No upstream pollution.** Per [`plan-multilingual-stage.md §3`](plan-multilingual-stage.md)
reject list, hexa-eval prose is tagged `bench-text` and excluded from
the training corpus to prevent benchmark contamination.

## S4 STRUCT — task taxonomy

8 task families, ~750 total. Each task ties to one or more sections of
hexa-lang `SPEC.md` so that the bench's coverage maps to the spec's
own structure (not arbitrary).

### S4.1 Task family table

| ID  | family                          | count | SPEC.md anchor                  | what it measures                                                         | gold-format       |
| --- | ------------------------------- | ----- | ------------------------------- | ------------------------------------------------------------------------ | ----------------- |
| T1  | syntax-correct hexa from spec   | ~200  | §3 (lexical + grammar)          | 1-3 line prose → hexa code passing S0 (parse) + S1 (resolve)             | S0/S1 exit-0      |
| T2  | atlas-citation discipline       | ~150  | §8 (citation / L[*] binding)    | function body referencing `L[*]` → correct `@implements` vs `@discover`  | annotation match  |
| T3  | `@grace` 3-field                | ~50   | §6 (deprecation / `@grace`)     | deprecation scenario → `@grace(HXxxxx, until=YYYY-MM-DD, reason="...")`  | byte-exact subset |
| T4  | RFC-020 enum payload            | ~100  | RFC-020                         | sum-type spec → canonical enum w/ single-field payload                   | AST equality      |
| T5  | `HX[CCCC]` code routing         | ~100  | §5 (diagnostics + HX taxonomy)  | error scenario → correct HX category (parse/resolve/bind/type/domain/units/equational/proof/citation/codegen) | label match |
| T6  | linker-aware codegen            | ~50   | §18 (firmware) + linker scripts | target triple → code that in-house linker resolves                       | linker exit-0     |
| T7  | stdlib direction enforcement    | ~50   | §18 + D-021                     | `firmware/*` module + host-stdlib import → must-reject decision          | binary label      |
| T8  | refusal correctness (5-NL)      | ~50   | §7 (refusal contract)           | off-domain prose in EN/KR/CN/RU/JA → canonical English refusal text      | byte-exact string |
|     | **total**                       | **~750** |                              |                                                                          |                   |

### S4.2 Per-family detail

**T1 — syntax-correct hexa from spec (~200).** Input: 1-3 line prose
description in English (the hexa lingua franca). Output: hexa source.
Pass criterion: candidate output passes `hexa cc --lint=S0,S1` with
exit 0. Hardness distribution: 40% trivial (single function), 40%
medium (struct + 1-2 methods), 20% hard (multi-decl with `@implements`
binding). Anchors §3 (grammar).

**T2 — atlas-citation discipline (~150).** Input: a function body
that references atlas `L[*]` nodes. Output: one of `@implements(L[<id>])`
(when implementing a known canonical node) or `@discover(kind="L")`
(when introducing a new node). Pass criterion: annotation kind matches
gold; node ID matches gold for `@implements`. Anchors §8.

**T3 — `@grace` 3-field (~50).** Input: a deprecation scenario described
in English ("Function `foo` returning `Option<T>` is being replaced
by `bar` returning `Result<T, E>` over 4 weeks; reason: error
propagation"). Output: a single line `@grace(HXxxxx, until=YYYY-MM-DD,
reason="...")` annotation. Pass criterion: all 3 fields present, HX
code valid, date ISO-8601, reason non-empty. Anchors §6.

**T4 — RFC-020 enum payload (~100).** Input: sum-type spec ("a `Shape`
that is either `Circle{r: f64}`, `Rect{w: f64, h: f64}`, or
`Triangle{base: f64, height: f64}`"). Output: canonical hexa enum with
**single-field payload per variant** (RFC-020 canon — variants carry
a struct, not positional fields). Pass criterion: AST equality (post
hexa-cc-parse) with gold AST. Anchors RFC-020.

**T5 — `HX[CCCC]` code routing (~100).** Input: an error description
("a literal `0x80000000` used where an `i32` was expected"). Output:
the correct HX category. The 10 categories from §5:
**parse, resolve, bind, type, domain, units, equational, proof,
citation, codegen.** Pass criterion: category label exact match.
Anchors §5.

**T6 — linker-aware codegen (~50).** Input: target triple +
peripheral description ("`thumbv7em-none-eabihf` STM32F4, init UART2
at 115200"). Output: hexa firmware module body. Pass criterion: passes
S0–S8 lint **and** in-house linker resolves all symbols. Triples
covered: `thumbv7em-none-eabihf`, `riscv32imac-unknown-none-elf`,
`xtensa-esp32-none-elf` (each ~17 tasks). Anchors §18.

**T7 — stdlib direction enforcement (~50).** Input: a `firmware/*`
module that imports a host-stdlib symbol (`stdlib/net`, `stdlib/http`,
`stdlib/fs`, `stdlib/process`, `stdlib/json`, `stdlib/threading`,
`stdlib/asyncio`, …). Output: binary decision **REJECT** + the HX
code (typically `HX5xxx` codegen-family). Pass criterion: rejection
correct AND HX code in correct family. Anchors §18 + D-021.

**T8 — refusal correctness (5-NL) (~50).** Input: off-domain prose
request in one of EN/KR/CN/RU/JA (10 tasks per NL). Output: the
**English-canonical** refusal string `out-of-domain: this is a code-
only model` (per recipe §VERIFY refusal contract + D-006). Pass
criterion: byte-exact match on the refusal string (no translation,
no prose extras). Anchors §7. Mirrored in
[`spec-five-nl-eval.md`](spec-five-nl-eval.md) §S4 as the cross-spec
refusal floor.

### S4.3 Hardness distribution

Per-family hardness is encoded as `easy / medium / hard` ratios so
the aggregate bar (≥ 80%) is meaningful regardless of which families
saturate first. Target ratios:

```
T1:  easy 40% / med 40% / hard 20%  -- grammar coverage breadth
T2:  easy 30% / med 50% / hard 20%  -- atlas binding is intrinsically medium
T3:  easy 20% / med 60% / hard 20%  -- 3-field discipline is the medium core
T4:  easy 30% / med 50% / hard 20%  -- RFC-020 single-field payload
T5:  easy 30% / med 40% / hard 30%  -- 10 categories => more hard tail
T6:  easy 20% / med 50% / hard 30%  -- linker is genuinely hard
T7:  easy 50% / med 30% / hard 20%  -- mostly binary, hard tier = edge cases
T8:  easy 60% / med 30% / hard 10%  -- refusal is mostly easy by design
```

A candidate that passes ≥ 80% **overall** but fails any single
family's `hard` tier completely is flagged for review (the 80% bar
is a single number; the per-family hard-tier floor is **diagnostic**,
not blocking).

## S5 FLOW — generation + scoring discipline

```
[1] Task authoring   --> [2] Gold-output freeze --> [3] Hash-pin
        |                       |                       |
        v                       v                       v
   native authors        S0-S8 self-pass         SPEC.md hash + task hash
   per family            (gold passes own lint)  pinned into runner config
        |                       |                       |
        +-----------+-----------+-----------+-----------+
                                |
                                v
                  [4] Candidate response  -->  [5] Score
                                |                |
                                v                v
                       hexa cc --lint=S0..S8   per-family pass/fail
                       in-house linker         aggregate 80% gate
                       byte/AST equality       hardness distribution
                                |                |
                                +-------+--------+
                                        |
                                        v
                          [6] Emit to outbox/hexa-codex/quality_scale/
                          [7] Emit to outbox/hexa-codex/eval/ (methodology delta)
```

### S5.1 Authoring discipline (D-013 enforced)

**No LLM-judge synthesis for gold output.** All gold answers are:
- hand-authored by a hexa-lang maintainer, OR
- mined from `~/core/hexa-lang/SPEC.md` examples + RFCs + canonical
  test fixtures (already license-clean, already hexa-cc-passing), OR
- generated by a **deterministic** transformer (template + hexa AST
  builder) — never by a downstream LLM.

This mirrors D-013's tree-sitter rule pack v1 stance — Shumailov 2024
model-collapse risk applies to bench authoring just as to DPO scoring.

### S5.2 Scoring algorithm (per-task)

```
score(task, candidate):
    1. emit = candidate(task.input)
    2. if task.family in {T1, T6}:
         if hexa_cc_lint(emit, stages=task.lint_stages) == OK:
             if task.family == T6:
                 return linker_resolve(emit, task.target) == OK
             return PASS
         else:
             return COMPILE_FAIL  (counts as fail for aggregate; tagged distinctly)
    3. if task.family in {T2, T3, T8}:
         return byte_exact_match(emit, task.gold)   # T3 with field-tolerance regex
    4. if task.family == T4:
         return ast_equal(parse(emit), parse(task.gold))
    5. if task.family in {T5, T7}:
         return label_match(emit, task.gold_label)
    6. tally per family + aggregate
```

### S5.3 Determinism + reproducibility

- Each task has `task_id` + `spec_anchor_hash` + `gold_hash`.
- Runner config pins: `hexa cc` binary SHA + SPEC.md content hash +
  task-set hash. Drift in any of these triggers a **new run_id**, no
  in-place re-grade.
- Sampling temperature = 0 for the candidate model (deterministic
  pass-rate); the optional `temp>0` mode is a separate diagnostic
  metric (`pass@k`) reported alongside but not gating.

## S6 EVOLVE — Mk.I → Mk.V progression

Matches hexa-codex `eval/ai-eval-pipeline.md §S6 EVOLVE` 5-stage shape.

- **Mk.I (1 month) — T1+T2 only, manual rubric.**
  ~350 tasks total (200 T1 + 150 T2). Scoring: a maintainer runs
  `hexa cc --lint=S0,S1` over candidate output and tallies. No
  automation beyond invoking the compiler. Goal: establish whether
  the bench discriminates **at all** between an untrained base and a
  forge-finetuned candidate. **Gate at Mk.I: discrimination ≥ 20pp
  between base and SFT-bias-only candidate.**

- **Mk.II (2 months) — full T1-T8, automated scoring via `hexa cc`
  invocation.** All ~750 tasks live. Runner orchestrates: compile,
  lint, AST diff, byte match, label match, linker invocation.
  `tool/run_hexa_eval.py` (see S9) emits a JSON report per run.
  Gate: aggregate pass ≥ 60% on the SFT-bias-only candidate (well
  below the v1.0.0 80% gate — Mk.II is calibration, not release).

- **Mk.III (3 months) — adversarial test generation (perturbation-
  based).** Each existing task is perturbed by ~5 transformations
  (synonym swap in prose, atlas-ID renaming, NL switch for T8,
  target-triple swap for T6) to defeat memorisation. Adversarial
  pass-rate is reported separately; the **gold task set remains
  pinned** at Mk.II. New adversarial cases that flip the model's
  answer become candidate Mk.IV inclusions after maintainer review.
  Gate: adversarial drop ≤ 15pp from base aggregate.

- **Mk.IV (4 months) — full pipeline + hexa-forge CI integration.**
  Every PR to forge that touches the SFT data mix, base weights, or
  tokenizer triggers a `hexa-eval` shadow run on a canary subset
  (~75 tasks, 10% sample). Full-run on tag-pushes only (compute cost
  control). Output routes per
  [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md).
  Gate: aggregate ≥ 80% (the v1.0.0 release bar) **must hold across
  3 consecutive CI runs** on the release-candidate weights.

- **Mk.V (long-term) — industry-standard + contamination quarantine.**
  Task set published with cryptographic hash; downstream forks
  required to prove `gold_hash` non-leakage into training (n-gram
  overlap + embedding similarity per
  [`~/core/hexa-codex/eval/ai-eval-pipeline.md §S7.9`](../../hexa-codex/eval/ai-eval-pipeline.md));
  task rotation at every minor forge release (T1/T2/T4/T5 are
  generatable by template — rotate quarterly; T3/T6/T7/T8 are
  effort-bound — rotate yearly). Mirrors hexa-codex eval Mk.V
  "automatic contamination quarantine."

| Mk    | scope                                  | pass criterion                  | unlocks                          |
| ----- | -------------------------------------- | ------------------------------- | -------------------------------- |
| Mk.I  | T1+T2 manual                           | ≥ 20pp base→SFT discrimination  | proceed to T3-T8 authoring       |
| Mk.II | T1-T8 automated                        | ≥ 60% SFT aggregate             | wire into CI                     |
| Mk.III | + adversarial perturbations           | ≤ 15pp adversarial drop         | publish bench v1                 |
| Mk.IV | + CI integration + feedback PR         | ≥ 80% × 3 consecutive runs      | **v1.0.0 forge release**         |
| Mk.V  | + contamination quarantine + rotation  | hash-pinned, leak-audited       | community-standard candidate     |

## S7 VERIFY — acceptance bar + failure semantics

### S7.1 Acceptance arithmetic

- **Aggregate gate.** `passed / 750 ≥ 0.80` ⇒ release-eligible (this
  bench alone; other §EVOLVE rows must also hold).
- **Per-family floor (diagnostic, non-blocking).** No family below
  50% (an 80% aggregate dominated by easy families is still flagged).
- **Per-NL refusal floor (diagnostic, non-blocking but tracked).**
  T8 must be 100% in EN; ≥ 90% per other NL. Sister spec
  [`spec-five-nl-eval.md`](spec-five-nl-eval.md) §S7 owns the
  cross-NL parity contract.
- **Hard-tier sanity.** Each family's `hard` tier must be > 0% — no
  zeroes. (A 0% on hard tier implies hardness mis-calibration, not
  capability.)

### S7.2 Failure taxonomy

Not every failure means the same thing — the runner distinguishes:

| failure code   | meaning                                                       | family    | counts toward 80%? |
| -------------- | ------------------------------------------------------------- | --------- | ------------------ |
| `COMPILE_FAIL` | candidate output didn't pass S0/S1 lint                       | T1, T6    | yes (fail)         |
| `LINT_FAIL`    | passed S0/S1 but failed S2..S8                                | T1, T6    | yes (fail)         |
| `AST_MISMATCH` | parses, but post-parse AST != gold AST                        | T4        | yes (fail)         |
| `LABEL_WRONG`  | category label off (HX family wrong, REJECT/ALLOW wrong)      | T5, T7    | yes (fail)         |
| `STRING_DRIFT` | byte-exact comparison fails (extra prose, translation, etc.)  | T3, T8    | yes (fail)         |
| `LINKER_FAIL`  | lint OK but in-house linker can't resolve                     | T6        | yes (fail)         |
| `ANNOT_WRONG`  | `@implements` vs `@discover` mis-chosen, or wrong L[<id>]      | T2        | yes (fail)         |
| `PASS`         | all checks green                                              | all       | yes (pass)         |

A `COMPILE_FAIL` is a fail, but it is **distinguished** from an
`AST_MISMATCH` in the report — the former indicates "the model
doesn't speak hexa," the latter indicates "the model speaks hexa
but disagrees with canon." Both downgrade the score equally; the
distinction informs which training stage to investigate (S2 SFT vs
S3 DPO vs S0 pretrain).

### S7.3 Intent vs surface failure

A response that **refuses** to emit hexa for a T1 prompt is scored
**fail** (intent failure — the candidate should have emitted code).
A response that **emits hexa with a syntax error** for a T1 prompt
is also **fail** (surface failure — `COMPILE_FAIL`). A response that
emits the English-canonical refusal text for a **T8** prompt is
**pass** (intent match). The taxonomy is symmetric across "should
refuse" and "should emit" cases.

### S7.4 What doesn't count as a hexa-eval failure

- Stylistic divergence within RFC-020 canon (variant ordering doesn't
  affect AST equality).
- Whitespace in non-string contexts.
- Comment text (unless gold pins comment text — none currently do).
- Choice of `i32` vs `i64` where the prose underspecifies (gold accepts
  the SPEC.md default, but the runner emits a `STYLE_NOTE` for the
  alternative).

## S8 FEEDBACK — upstream channel

Per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md),
hexa-eval results route to **two** hexa-codex destinations:

| forge output                                                | hexa-codex destination                                                                   | PR shape                                                              | falsifier T4         |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------- |
| Aggregate hexa-eval pass rate per release                   | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)         | cross-cutter contribution: hexa-fidelity axis added to quality table  | cross-cutter         |
| Per-family failure-distribution + adversarial drop          | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.II/Mk.III   | methodology delta — informs hexa-codex eval Mk.II adversarial gen     | meta (wraps F-1..4)  |

The hexa-codex `eval` verb's Mk.II promotion criterion includes
"multilingual eval-set design" + "adversarial test generation" — the
T6/T8 + Mk.III work here lands as empirical confirmation that those
techniques transfer to a single-language, single-domain niche bench.

**Outbox path** (per `plan-feedback-channel-ops.md §7`):
- `outbox/hexa-codex/quality_scale/<run_id>-hexa-eval.md`
- `outbox/hexa-codex/eval/<run_id>-hexa-eval-methodology.md`

The emit script (S9 below) writes the PR draft using the template in
`plan-feedback-channel-ops.md §2`.

### S8.1 Contribution to v1.0.0 forge gate

`docs/code-llm.md §VERIFY upstream feedback contract` requires ≥ 5
PRs landed in hexa-codex. hexa-eval contributes **two** of those by
design (quality_scale + eval-methodology). Combined with `5-NL eval`
(another 2) + at least one of {train_cost / infer_cost} T4, the gate
is reachable from the eval surface alone.

## S9 Tooling

Two scripts (planned; not yet written):

| script                          | reads                                                                 | writes                                                                            | status  |
| ------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------- |
| `tool/run_hexa_eval.py`         | `tests/hexa-eval/tasks/*.toml` + candidate model endpoint              | `runs/<id>/hexa-eval.parquet` + per-task JSON                                     | PLANNED |
| `tool/emit_hexa_eval_pr.py`     | `runs/<id>/hexa-eval.parquet`                                          | `outbox/hexa-codex/quality_scale/<id>-hexa-eval.md` + `eval/<id>-methodology.md`  | PLANNED |

Both follow the existing `tool/emit_t4.py` shape (already in repo).
`run_hexa_eval.py` is the bench runner; `emit_hexa_eval_pr.py` is the
codex-PR emitter. Wiring matches
[`plan-feedback-channel-ops.md §3`](plan-feedback-channel-ops.md)
automation triggers — emit on bench-run-complete.

**Determinism contract.** Both scripts honour:
- `SOURCE_DATE_EPOCH` for any timestamps in output
- pinned hashes for SPEC.md + task set + hexa cc binary
- exit code 0 on aggregate pass, non-zero with structured stderr on
  fail (CI-friendly)

**Not in scope for v0.1.3.** Actual task TOMLs (`tests/hexa-eval/tasks/`),
the gold-output corpus, or the runner implementation — those land
v0.1.3+ after D-007 (base weights) closes and there is a candidate
model to run against.

---

## Open questions (v0.1.2 → v0.1.3 handoff)

- [ ] **D-NEW-A (this spec)** — Should T6 cover the full hexa firmware
      board set (`rtsc`, `chip`, `cern`, `antimatter`, `space`) or only
      the 3 target triples listed? *Proposed: triples only at Mk.II;
      per-board at Mk.IV after firmware-native stage matures.*
- [ ] **D-NEW-B (this spec)** — Task-rotation cadence at Mk.V: quarterly
      for T1/T2/T4/T5 (generatable) vs yearly for T3/T6/T7/T8 (effort-
      bound). *Proposed: as written; revisit when first rotation
      planned.*
- [ ] **D-NEW-C (this spec)** — Does `STYLE_NOTE` (S7.4) feed back into
      DPO as a soft negative, or stay purely diagnostic? *Proposed:
      diagnostic only at v1.0.0; revisit at v1.1.0.*

Resolved decisions referenced by this spec:
- D-005 (5 NL set) — closed 2026-05-11
- D-006 (NL diagnostic carve-out) — closed 2026-05-11
- D-013 (no LLM-judge for gold) — closed 2026-05-11
- D-021 (hexa fidelity contract) — closed 2026-05-11
- D-029 (PRIMARY = `hexa cc` compiled) — closed 2026-05-11

---

## Cross-link

- Recipe SSOT: [`../docs/code-llm.md`](../docs/code-llm.md) §EVOLVE row 4 (acceptance gate ③).
- Sister spec: [`spec-five-nl-eval.md`](spec-five-nl-eval.md) (acceptance gate ④).
- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md) (D-005, D-006, D-013, D-021, D-029).
- Feedback channel ops: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md).
- Multilingual stage filter (T8 input source for refusal-NL tasks): [`plan-multilingual-stage.md`](plan-multilingual-stage.md).
- Methodology canon: [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.I–Mk.V shape source.
- Hexa SPEC.md: [`~/core/hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md) — §3/§5/§6/§7/§8/§18 + RFC-020.
- Tier E corpus (provides idiomatic negative pairs adjacent to T2 patterns): [`tier-e-findings.md`](tier-e-findings.md).
