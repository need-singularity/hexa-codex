<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->
<!-- SPDX-FileCopyrightText: 2026 hexa-forge contributors -->
<!-- @canonical: forge@v0.1.2:papers/spec-frontend-eval.md -->
<!-- @owns(sections=[HEADER, WHY, COMPARE, REQUIRES, STRUCT, FLOW, EVOLVE, VERIFY, FEEDBACK, TOOLING], strict=false, order=sequential, prefix="S") -->

# `frontend-eval` — custom benchmark spec for 2026-canon frontend fidelity

> **Acceptance gate (v1.0.0).** This spec defines benchmark **⑦** from
> [`docs/code-llm.md` §EVOLVE](../docs/code-llm.md#evolve--eval-harness)
> — the **frontend** row family: `component-synthesis`, `a11y-fix`,
> `RSC-vs-client decision`, `CSS-modernize`. The recipe pins per-row
> bars (Vitest+TL, "violation resolved + 0 new", ≥ 80% RSC agreement,
> ≥ 75% appropriate-use). This spec aggregates those rows into a
> **single bench (`frontend-eval`) with a unified pass bar of ≥ 65%**
> across all task families, plus the per-family floors below. Bars
> live in the recipe; **shape** is defined here. Implementation lands
> v0.1.3+ (post-D-007 base-model availability).
>
> **Decisions referenced.** D-024 (frontend stage placement — filter-
> expand, no new top-level stage), D-025 (frontend canon corpus
> sourcing — F-1/F-2/F-3 findings landed), D-026 (mobile/cross-
> platform: RN+Expo+Capacitor+Tauri T1, Flutter T2 quote-only),
> D-027 (AI-native UI — Vercel AI SDK + AI Elements, no LLM-judge
> synth per D-013), D-028 (4 benches at v0.1.x: component-synthesis
> + a11y-fix + RSC-vs-client + CSS-modernize; bundle-fit + AI-UI
> patterns deferred to v0.2.0). See
> [`papers/plan-decisions-pending.md`](plan-decisions-pending.md).
>
> **Sister methodology canon.** Section discipline (S-prefix,
> falsifier-anchored, Mk.I → Mk.V) mirrors
> [`spec-hexa-eval.md`](spec-hexa-eval.md) +
> [`spec-five-nl-eval.md`](spec-five-nl-eval.md) which in turn instantiate
> `~/core/hexa-codex/eval/ai-eval-pipeline.md`. Forge does not duplicate
> methodology — it instantiates it for one custom benchmark.

---

## S0 HEADER

| field             | value                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| verb              | `code` (sub-artifact `frontend-eval`)                                                              |
| family            | `hexa-forge`                                                                                       |
| status            | `RESEARCH_FIRST` — spec only, runner script planned                                                |
| dispatch          | `hexa-forge code eval --bench frontend-eval`                                                       |
| acceptance gate   | **≥ 65% pass aggregate** across all task families (single bar) + per-family floors (S7)            |
| task count target | **~520** (T1=150, T2=120, T3=100, T4=80, T5=50 [v0.2.0], T6=20 [v0.2.0])                           |
| owner             | `forge.code` verb                                                                                  |
| sister gates      | benchmark **③** = `hexa-eval` + benchmark **④** = `5-NL eval`                                      |
| codex feedback    | `hexa-codex/{quality_scale, eval, interpret, agent_serving}` per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md) |
| last updated      | 2026-05-11                                                                                         |

---

## S1 WHY — why a frontend-specific eval is needed

Frontend is **its own surface**. The `code` verb cannot collapse it
into "TS + CSS + HTML, already in scope" — the canon is qualitatively
different from backend / firmware / DB along **four orthogonal axes**:

1. **Component-driven, not function-driven.** Deliverable = component
   with props / behaviour / a11y semantics, not a free function.
   HumanEval+ measures "function from prompt"; frontend measures
   "component from contract." Unit of correctness is `getByRole`
   + Vitest, not stdout match.
2. **RSC / client split is non-trivial.** Next.js App Router canon
   (per [F-1 Part 2](frontend-f1-findings.md)) forces `'use server'`
   vs `'use client'` per file. Wrong choice = working code that ships
   3× the bundle and breaks streaming. No public bench tests this.
3. **A11y is the legal floor.** WCAG 2.2 is **ADA / Section 508 /
   EAA-binding** (per [F-3 Part 2](frontend-f3-findings.md)); WCAG
   3.0 is March 2026 draft, **must not** be used for compliance.
   "Good a11y = good agent-ability" — the accessibility tree is what
   downstream agents read, so a11y also gates the `agent_serving` UX
   canon. UI with axe violations ships a legal liability **and**
   breaks the agent loop.
4. **CSS-as-design-token.** Tailwind v4 Oxide + OKLCH + container
   queries + `:has()` + Anchor Positioning 2026 Baseline + `<dialog>`
   + Popover API collectively obsoleted ~70% of pre-2024 CSS canon
   (per [F-2](frontend-f2-findings.md)). A model trained on 2010-era
   jQuery/Bootstrap/`position:absolute`-float ships **wrong** by 2026
   standards even when the code "works."

**No public bench covers this surface.** WebDevEval is component-only;
Aider-bench is file-edit-only; SWE-bench is issue-resolution-only.
None enforce a11y, RSC decision, 2026 canon, or Compiler-1.0-era
no-manual-memoization style.

**Core falsifiable claim.** If the trained `code` verb cannot pass
frontend-eval at ≥ 65%, the **"2026-canon-first frontend competence"**
claim of `docs/code-llm.md §VERIFY style contract` is empirically
falsified for the v1.0.0 release. Recipe must downgrade scope (drop
frontend from the supported-surface table) or retrain.

## S2 COMPARE — vs public frontend / code benchmarks

```
+--------------------------------------------------------------------+
|  [Coverage on component + a11y + RSC + 2026-canon axes]            |
+--------------------------------------------------------------------+
|  HumanEval+              ##.......................  function only |
|  SWE-bench Lite          ####.....................  issue resolve |
|  Aider-bench             #####....................  file edits    |
|  WebDevEval              ##########...............  component only|
|  frontend-eval (this)    ##################........ all four axes |
+--------------------------------------------------------------------+
|  [A11y enforcement as scoring gate]                                |
+--------------------------------------------------------------------+
|  HumanEval+ / SWE-bench  #.........................  none         |
|  WebDevEval              ###.......................  optional     |
|  frontend-eval T1+T2     ##################........ axe 0-violation hard gate |
+--------------------------------------------------------------------+
|  [RSC decision discipline]                                         |
+--------------------------------------------------------------------+
|  any public bench        #.........................  none         |
|  frontend-eval T3        ##################........ ≥80% agreement|
+--------------------------------------------------------------------+
|  [2026-canon enforcement (container queries / OKLCH / `:has()`)]   |
+--------------------------------------------------------------------+
|  any public bench        #.........................  none         |
|  frontend-eval T4        ##################........ explicit canon|
+--------------------------------------------------------------------+
```

**frontend-eval's niche.** Complementary to general code benches —
covers the **frontend-specific** discriminators (component contract,
RSC/client split, a11y as floor, 2026 CSS canon) that public benches
treat as outside scope. Together with `hexa-eval` (hexa-fidelity),
`5-NL eval` (cross-lingual), and HumanEval+ (general synthesis), it
closes the v1.0.0 acceptance-bar matrix.

## S3 REQUIRES — prerequisites

| prerequisite                                                  | source / location                                                                                  | check                |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------- |
| **D-024–D-028 closed** — frontend scope frozen                | [`plan-decisions-pending.md §4`](plan-decisions-pending.md)                                        | resolved 2026-05-11  |
| Playwright (browser harness)                                  | `playwright` MIT — headless Chromium / Firefox / WebKit                                            | binary on $PATH      |
| **axe-core** (a11y engine)                                    | `axe-core` MPL-2 + `@axe-core/playwright`                                                          | npm-resolvable       |
| Vitest + Testing Library                                      | `vitest` + `@testing-library/{react,vue,svelte}` MIT                                               | npm-resolvable       |
| shadcn/ui registry (component reference)                      | `shadcn` MIT — copy-paste primitive shape                                                          | registry hash-pinned |
| Radix UI + **Base UI** primitives                             | `@radix-ui/*` MIT + `@base-ui-components/react` MIT (shadcn-supported since 2026-02 per F-1)       | npm-resolvable       |
| Next.js App Router reference impl (RSC canon)                 | `next` MIT — canonical `'use server'` / `'use client'` reference per F-1 Part 2                    | starter pinned       |
| Frontend canon SSOT                                           | [`frontend-f1-findings.md`](frontend-f1-findings.md) + [`f2`](frontend-f2-findings.md) + [`f3`](frontend-f3-findings.md) | hash-pinned at freeze |
| Senior FE reviewer (gold authoring per S5)                    | ≥ 1 reviewer with React 19 + RSC + WCAG 2.2 production experience                                  | sign-off recorded    |
| Bundle analyser (T6, v0.2.0)                                  | `vite-bundle-visualizer` / `@next/bundle-analyzer` MIT                                             | optional at v0.1.x   |
| Lighthouse CI (T4 perf floor)                                 | `lighthouse` Apache-2                                                                              | binary on $PATH      |

**Stage ordering.** `frontend-eval` runs **independently** of
`hexa-eval` and `5-NL eval` — the three benches aggregate separately
into the v1.0.0 gate. T2 (a11y-fix) and T1 (component-synthesis) share
the axe-core verifier path but score independently.

**No upstream pollution.** Per
[`plan-multilingual-stage.md §3`](plan-multilingual-stage.md) reject-
list pattern, frontend-eval task prose and gold components are tagged
`bench-text` and excluded from the training corpus to prevent
contamination. Same Shumailov 2024 risk applied to bench authoring.

## S4 STRUCT — task taxonomy

6 task families, ~520 total. Each task ties to one or more axes of the
recipe `docs/code-llm.md §EVOLVE frontend` rows and to a specific
F-1/F-2/F-3 finding so that the bench's coverage maps to the canon's
own structure (not arbitrary).

### S4.1 Task family table

| ID  | family                            | count | canon anchor                                             | what it measures                                                              | gold-format          |
| --- | --------------------------------- | ----- | -------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------- |
| T1  | component-synthesis               | ~150  | F-1 Part 1 / 3 (frameworks + design systems)             | spec (props/behavior/a11y) → React 19 / Vue 3 / Svelte 5 component            | Vitest+TL+axe        |
| T2  | a11y-fix                          | ~120  | F-3 Part 2 (WCAG 2.2 + ARIA APG)                         | axe violation + current code → fix that resolves it w/o regression            | axe diff + DOM delta |
| T3  | RSC-vs-client decision            | ~100  | F-1 Part 2 (Next.js App Router) + F-3 Part 1 (streaming) | component spec → `'use server'` vs `'use client'` correct label               | label match          |
| T4  | CSS-modernize                     | ~80   | F-2 Parts 1-3 + F-3 Part 2                               | legacy CSS → 2026 canon (container queries / OKLCH / `:has()` / `<dialog>`)   | rule-pack + lighthouse |
| T5  | streaming-aware AI-UI patterns    | ~50   | F-3 Part 3 (AI-native UI)                                | token-streaming component w/ `AbortController` + `AbortSignal.any`            | Playwright trace     |
| T6  | bundle-fit                        | ~20   | F-3 Part 1 (bundle budgets)                              | perf budget + spec → code splits hitting budget                               | `bundle_analyze`     |
|     | **total**                         | **~520** |                                                       |                                                                               |                      |

**v0.1.x scope.** T1+T2+T3+T4 = **450 tasks** are the v0.1.x bench (per
D-028). T5 + T6 are **design-floored here** but **enabled at v0.2.0**
to keep the v0.1.x runner surface tractable.

### S4.2 Per-family detail

**T1 — component-synthesis (~150).** Input: structured component spec
— typed props, behaviour, a11y requirements (e.g. "reachable by
`getByRole` + keyboard with `Enter`/`Space`/`Escape`"). Output: single
component in one of {React 19, Vue 3.6, Svelte 5}. Pass: Vitest + TL
suite (≥ 3 `getByRole` tests) **AND** axe 0 violations on Playwright
render **AND** **no manual `useMemo`/`useCallback`/`React.memo`** under
React 19 (Compiler 1.0 stable 2025-10-07 makes these counter-canon
per F-1). Hardness: 40% trivial (Button/Toggle/Disclosure), 40% medium
(Combobox/Tabs/Tooltip + anchor positioning), 20% hard (Dialog w/
focus + `inert` + Escape + return-focus, virtual-list Combobox).

**T2 — a11y-fix (~120).** Input: component source + axe JSON violation
report. Output: patched component. Pass: (a) reported violation
**resolved** (axe rerun clean for that rule), (b) **no new violation
introduced** (full-rule rerun 0 new), (c) **DOM-structure delta ≤ 5%**
by node count — an a11y "fix" that rewrites the whole tree is a
rewrite, not a fix; the 5% tolerance permits adding `aria-label` / `id`
/ wrapping element but rejects wholesale rewrites. Violation mix:
target-size-24×24 (WCAG 2.2 SC 2.5.8), focus-not-obscured
(SC 2.4.11/12), accessible-name (SC 4.1.2), colour-contrast (WCAG-2
7:1 / APCA when fit), `tabindex>0` removal, decorative-ARIA removal
("no ARIA is better than bad ARIA"). Semantic-first: adding
`role="button"` to a `<div>` **fails** when wrapping in `<button>`
would resolve it equally — runner enforces a "semantic-preferable"
rule per violation type.

**T3 — RSC-vs-client decision (~100).** Input: component spec (prose
+ intended use site). Output: directive label `'use server'` /
`'use client'` / `'mixed'` (the latter with `{child_directive}`
field). Runner accepts either the top-of-file directive or a JSON
answer. Pass: agreement with reference label authored by senior FE
reviewer using Next.js App Router canon (data-fetching default →
server; interactivity / browser APIs / event handlers → client;
genuinely-mixed → server shell + client island). Split target: 50%
server / 40% client / 10% mixed. Borderline cases excluded at
authoring (S5). Hardness: 50% easy (unambiguous — pure form vs pure
server data table), 35% medium (list with a single client-side
filter), 15% hard (third-party client lib called only on mount;
server-streamed search).

**T4 — CSS-modernize (~80).** Input: legacy CSS exhibiting one or more
pre-2024 anti-patterns — floats for layout, pixel-px media queries,
HSL/hex for new tokens, `position:absolute` modal centering, JS
focus-trap, `<div role="dialog">`, `@media (max-width: 768px)` on a
component-local widget. Output: modernised CSS + minimal HTML adjust.
Pass = deterministic **rule-pack** (tree-sitter-CSS scan):
container-queries where legacy `@media` was component-local; OKLCH
introduced for any new token (legacy HSL preserved if it's an
intentional reference); `:has()` where legacy used JS class toggling
for parent-conditional state; `<dialog>` replacing modal-by-
`position:absolute`; Popover API where appropriate; Logical Properties
(`inline-start`/`inline-end`/`margin-block`/`padding-inline`) over
physical; a11y not regressed (axe rerun 0-new); Lighthouse perf not
lower than legacy baseline. Threshold: **≥ 3 of the applicable canons
applied** (runner detects which canons are applicable per task — not
every task has a `:has()` opportunity).

**T5 — streaming-aware AI-UI patterns (~50, v0.2.0 enabled).** Input:
chat-message-component spec that streams tokens, supports user abort
mid-stream, retries on transient failure (Vercel AI SDK shape per F-3
Part 3). Output: React/Vue/Svelte component using `AbortController`
+ `AbortSignal.any` for compose + streaming-render. Pass = Playwright
trace shows: (a) **token-by-token DOM mutation** observable (not
single end-of-stream paint); (b) **abort clean** — user cancels mid-
stream, no further mutations, **no unhandled rejection** in console
(via `read_console`); (c) **retry clean** — after synthetic transient
failure the next attempt proceeds without leaking the previous
controller; (d) **optimistic UI** — user input appears before server
confirmation. Race probe: fast-cancel (abort within 50 ms of start)
must not produce a torn state.

**T6 — bundle-fit (~20, v0.2.0 enabled).** Input: component spec +
hard budget (e.g. ≤ 100 KB initial JS gzip, ≤ 170 KB total per F-3
Part 1 tier). Output: component (or component + route). Pass:
`bundle_analyze` total ≤ budget after `vite build` / `next build`.
Code-split discipline verified: dynamic `import()` for non-critical
paths, server components where applicable, no full-icon-library
import (per F-1 anti-canon).

### S4.3 Hardness distribution

Per-family hardness ratios match the aggregate-bar discriminant logic
of `spec-hexa-eval.md §S4.3`:

```
T1:  easy 40% / med 40% / hard 20%  -- primitive → composed → focus-trap
T2:  easy 30% / med 50% / hard 20%  -- single rule → composite a11y issue
T3:  easy 50% / med 35% / hard 15%  -- mostly binary; hard tail = streaming/mixed
T4:  easy 35% / med 45% / hard 20%  -- single canon → multi-canon modernization
T5:  easy 30% / med 50% / hard 20%  -- happy path → race / abort under fast-cancel
T6:  easy 40% / med 40% / hard 20%  -- single-component → multi-route budget
```

A candidate that passes ≥ 65% **overall** but fails any family's
`hard` tier completely is flagged for review (the 65% bar is the
single blocking number; hard-tier zeroes are **diagnostic**, not
release-blocking).

## S5 FLOW — generation + scoring discipline

```
[1] Task authoring   --> [2] Gold-output freeze --> [3] Hash-pin
        |                       |                       |
        v                       v                       v
   shadcn + Radix + Base    senior FE reviewer     canon + task hash;
   UI; Astro/Next/Nuxt/     sign-off; gold passes  shadcn registry SHA
   SvelteKit starters;      its own Vitest+TL+axe  pinned into runner
   senior FE author
        |                       |                       |
        +-----------+-----------+-----------+-----------+
                                |
                                v
                  [4] Candidate response  -->  [5] Score
                                |                |
                                v                v
                       Playwright headless    per-family pass/fail
                       axe-core 0-violation   aggregate 65% gate
                       Vitest + TL            rule-pack (T4)
                       label match (T3)       T3 agreement metric
                                |                |
                                +-------+--------+
                                        |
                                        v
                          [6] outbox/hexa-codex/quality_scale/
                          [7] outbox/hexa-codex/eval/ (methodology)
                          [8] outbox/hexa-codex/interpret/ (style audit)
                          [9] outbox/hexa-codex/agent_serving/ (T5 only)
```

### S5.1 Authoring discipline (D-013 + D-027 enforced)

**No LLM-judge synthesis for gold output.** All gold answers are:
- **hand-authored** by a senior FE reviewer with React 19 / RSC /
  WCAG 2.2 production experience, OR
- **mined** from shadcn registry, Radix / Base UI primitives, or
  canonical Astro / Next / Nuxt / SvelteKit starters (MIT/Apache-2
  license-clean, already passing their own Vitest + axe), OR
- **generated by a deterministic transformer** (e.g. Tailwind v4
  `@theme` → OKLCH token-table builder for T4 single-canon tasks) —
  never by a downstream LLM.

Mirrors D-013 (tree-sitter rule pack v1) + D-027 (no LLM-judge for
AI-UI corpus synth). Shumailov 2024 model-collapse risk applies to
bench authoring just as to DPO scoring.

**Reviewer load.** ≥ 1 senior FE reviewer per T1/T2/T3/T5/T6 gold
component; T4 rule-pack tasks are deterministic and skip per-task
review beyond task-set freeze.

### S5.2 Scoring algorithm (per-task)

```
score(task, candidate):
    emit = candidate(task.input)
    match task.family:
      T1: vitest_pass(emit, task.tests)
            && axe(playwright_render(emit)) == 0_VIOLATIONS
            && !/useMemo|useCallback|React\.memo/.test(emit)
      T2: !axe_rule_fires(emit, task.target_violation)
            && axe(emit).new_rules == 0
            && dom_node_delta(emit, task.input) <= 0.05
      T3: label_match(emit.label, task.gold_label)
      T4: |applied ∩ applicable| >= max(3, ceil(0.6 * |applicable|))
            && axe(emit).new_violations == 0
            && lighthouse(emit).perf >= lighthouse(task.input).perf
      T5: trace.token_stream && trace.abort_clean
            && trace.retry_clean && trace.no_race        (v0.2.0)
      T6: bundle_analyze(emit).gzip <= task.budget       (v0.2.0)
    tally per family + aggregate
```

### S5.3 Determinism + reproducibility

- Each task has `task_id` + `canon_anchor_hash` + `gold_hash` +
  `shadcn_registry_sha` + `playwright_version` + `axe_core_version`.
- Runner config pins: candidate model SHA + task-set hash + tool
  versions. Browser engine version pinned (Chromium build SHA) — axe
  results can drift across browser versions and ARIA-tree exposure
  differs across engines.
- Temperature = 0 for primary report. `pass@k` (k=5, temperature=0.7)
  reported as secondary diagnostic.

## S6 EVOLVE — Mk.I → Mk.V progression

Matches `spec-hexa-eval.md §S6` + `spec-five-nl-eval.md §S6` 5-stage shape.

- **Mk.I (1 month) — T1+T2 manual, ~80 tasks** (~50 T1 + ~30 T2),
  scored by a maintainer running Vitest + axe + Playwright by hand.
  No CI. Goal: establish bench discriminates between untrained base
  and forge-finetuned candidate. **Gate: ≥ 20pp base→SFT discrimination**.
- **Mk.II (2 months) — all T1–T4 automated, ~450 tasks.** Runner
  orchestrates: Playwright headless, axe scan, Vitest + TL, label
  match (T3), tree-sitter-CSS rule-pack (T4), Lighthouse compare.
  `tool/run_frontend_eval.py` (S9) emits JSON per run. **Gate:
  aggregate ≥ 50% on SFT-bias-only candidate** (calibration, not
  release).
- **Mk.III (3 months) — T5+T6 enabled + visual-regression added.**
  Streaming-aware T5 lights up; bundle-fit T6 lights up. Visual-
  regression via `visual_diff` (Playwright snapshot / Chromatic) on
  T1 catches silent regressions. Adversarial per `spec-hexa-eval.md
  §S6 Mk.III` pattern: framework swap (React→Svelte→Vue), prop-name
  perturbation, axe-rule swap within same WCAG-2.2 SC. **Gate:
  adversarial drop ≤ 15pp + T5 abort-path 100% on happy probe.**
- **Mk.IV (4 months) — CI integration.** Per-PR canary slice (~50
  tasks, 10% sample) on every forge PR touching frontend-philosophy
  corpus, tokenizer, or SFT mix. Full ~520-task run on tag-pushes
  only (compute cost — headless browser + axe + Lighthouse is non-
  trivial). Routes per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md).
  **Gate: aggregate ≥ 65% × 3 consecutive CI runs** on RC weights.
- **Mk.V (long-term) — industry-standard + contamination quarantine
  + public leaderboard.** Task set published with cryptographic hash;
  forks required to prove non-leakage (n-gram + embedding-similarity
  audit per `~/core/hexa-codex/eval/ai-eval-pipeline.md §S7.9`).
  Rotation: T1/T3/T4 quarterly (generatable from shadcn-registry
  shape + WCAG-2.2 SC matrix); T2/T5/T6 yearly (effort-bound). Public
  leaderboard at `frontend-eval.hexa-forge.org` (planned).

| Mk    | scope                                              | pass criterion                                                  | unlocks                                |
| ----- | -------------------------------------------------- | --------------------------------------------------------------- | -------------------------------------- |
| Mk.I  | T1+T2 manual ~80 tasks                             | ≥ 20pp base→SFT discrimination                                  | proceed to T3+T4 authoring             |
| Mk.II | T1-T4 automated ~450 tasks                         | aggregate ≥ 50% on SFT                                          | wire into CI                           |
| Mk.III | + T5 + T6 + visual-regression + adversarial       | adversarial drop ≤ 15pp + T5 abort 100%                         | publish bench v1                       |
| Mk.IV | + CI integration + feedback PR                     | aggregate ≥ 65% × 3 consecutive CI runs                         | **v1.0.0 forge release**               |
| Mk.V  | + contamination quarantine + public leaderboard    | hash-pinned, leak-audited, leaderboard live                     | community-standard candidate           |

## S7 VERIFY — acceptance bar + failure semantics

### S7.1 Acceptance arithmetic

- **Aggregate gate.** `passed / 520 ≥ 0.65` ⇒ release-eligible (this
  bench alone; other §EVOLVE rows must also hold). At v0.1.x with T5
  + T6 deferred, the gate is `passed / 450 ≥ 0.65`.
- **Per-family floor (diagnostic, non-blocking except T1+T2).** No
  family below 50%. **Exceptions: T1 axe-clean rate must be ≥ 90%**
  (a11y is the legal floor — even passing tasks that ship violations
  trip a sub-floor) and **T2 "no-new-violations" rate must be 100%**
  (a fix that regresses other rules is not a fix; this is binary).
- **Hard-tier sanity.** Each family's `hard` tier must be > 0% — no
  zeroes. A 0% hard tier implies mis-calibration, not capability.

### S7.2 Per-family scorers (canonical)

| family | scorer (PASS = all of)                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------- |
| T1     | Vitest + TL `getByRole` PASS · axe 0 violations · **no manual `useMemo`/`useCallback`/`React.memo`** (Compiler-1.0 era) |
| T2     | violation resolved · 0 new violations · DOM-structure delta ≤ 5% · semantic-preferable rule (no `role` where element exists) |
| T3     | label match against reference (`'use server'` / `'use client'` / `'mixed'`) · ≥ 80% agreement aggregate (S7.4)         |
| T4     | rule-pack ≥ 3 applicable canons applied · a11y not regressed · Lighthouse perf ≥ baseline                             |
| T5     | token-by-token rendering observable · abort path exercised · no race under fast-cancel · no leaked controllers         |
| T6     | bundle ≤ budget (gzip, post-build)                                                                                     |

### S7.3 Failure taxonomy

| failure code         | meaning                                                                                | family       | counts toward 65%?       |
| -------------------- | -------------------------------------------------------------------------------------- | ------------ | ------------------------ |
| `VITEST_FAIL`        | component test suite did not pass                                                      | T1           | yes (fail)               |
| `AXE_VIOLATION`      | axe-core reports ≥ 1 violation on rendered output                                      | T1, T2, T4   | yes (fail) + T1 sub-floor|
| `MANUAL_MEMO`        | source contains `useMemo`/`useCallback`/`React.memo` under React 19+                   | T1           | yes (fail)               |
| `STRUCT_REWRITE`     | T2 DOM-structure delta > 5% (whole-tree rewrite masquerading as fix)                   | T2           | yes (fail)               |
| `NEW_VIOLATION`      | T2 fix introduced a new axe rule failure                                               | T2           | yes (fail) + T2 sub-floor|
| `ROLE_OVER_SEMANTIC` | T2 added `role="X"` where the native element existed                                   | T2           | yes (fail)               |
| `LABEL_WRONG`        | T3 emitted directive disagrees with reference                                          | T3           | yes (fail)               |
| `CANON_NOT_APPLIED`  | T4 rule-pack count below threshold (< 3 of applicable)                                 | T4           | yes (fail)               |
| `PERF_REGRESS`       | T4 Lighthouse perf score lower than legacy baseline                                    | T4           | yes (fail)               |
| `STREAM_BLOCKED`     | T5 single end-of-stream paint (no token-by-token observable)                           | T5           | yes (fail)               |
| `ABORT_LEAK`         | T5 abort or fast-cancel left an unhandled rejection / orphaned controller              | T5           | yes (fail)               |
| `BUDGET_EXCEEDED`    | T6 bundle > budget                                                                     | T6           | yes (fail)               |
| `PASS`               | all family-specific checks green                                                       | all          | yes (pass)               |

### S7.4 T3 agreement metric

T3 is the only family where the recipe-level bar (`≥ 80% agreement
with reference` per `docs/code-llm.md §EVOLVE` row) is **tighter** than
the bench-level 65% aggregate. The runner emits T3 agreement
separately: a model scoring 65% aggregate but only 70% on T3 is
**release-blocked** (T3 has its own per-row recipe bar that must be
met; the 65% aggregate is necessary but not sufficient).

### S7.5 What doesn't count as a frontend-eval failure

- Stylistic divergence within shadcn / Radix / Base UI (primitive
  choice is gold-author-arbitrary — both pass when a11y + behaviour
  contract is met).
- Framework choice within a task's `allowed_frameworks` set (T1
  typically {React 19, Vue 3.6, Svelte 5}; T5 typically {React 19,
  Svelte 5} given Vercel AI SDK first-class hooks).
- Tailwind v4 utility ordering (no effect on axe / Vitest).
- Comment text (unless gold pins comment — none currently do).
- `<button>` vs `<button type="button">` — both semantic, runner emits
  `STYLE_NOTE` only.

### S7.6 Style contract enforcement (cross-link to recipe §VERIFY)

Generated code from every family MUST pass
[`docs/code-llm.md §VERIFY style contract`](../docs/code-llm.md#verify--serving-contract)
**2026-canon-first** clauses. The frontend-eval runner is the **live
enforcer**:

| recipe-canon clause                                | frontend-eval enforcement                                                       |
| -------------------------------------------------- | ------------------------------------------------------------------------------- |
| `<dialog>` over modal libs                         | T1 dialog tasks fail on `react-modal`/`headlessui Dialog`; T4 rule-pack detect  |
| Popover API over `position:absolute`               | T4 rule-pack; T1 anchor-positioned tasks                                        |
| Container Queries over media queries (local scope) | T4 rule-pack `@container` vs legacy `@media`                                    |
| OKLCH over HSL for new tokens                      | T4 rule-pack OKLCH-introduced count                                             |
| `:focus-visible` not `:focus`                      | T1 + T4 grep on emitted CSS                                                     |
| INP-driven, not FID                                | T1+T5+T6 — FID in code/comment is `STYLE_NOTE`; INP must be the perf axis        |
| WCAG 2.2 not 2.1                                   | T2 violation rules drawn from WCAG 2.2 SC set (9 new SCs over 2.1)              |
| agent-friendly DOM = a11y tree                     | T1 + T5 — axe-tree is the agent-readability proxy (no separate test surface)    |
| Compiler 1.0 (no manual memoization)               | T1 explicit `MANUAL_MEMO` failure code                                          |
| AbortController + AbortSignal.any                  | T5 `ABORT_LEAK` failure code                                                    |
| Vercel AI SDK shape                                | T5 reference impls use AI SDK; equivalent shapes accepted                       |

A working component using 2010-era canon (jQuery / `position:absolute`
modal / class components / manual memo / FID-mentioning perf comments)
is a `STYLE_FAIL` even when otherwise green — recipe canon is non-
negotiable.

## S8 FEEDBACK — upstream channel

Per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md),
frontend-eval results route to **four** hexa-codex destinations:

| forge output                                            | hexa-codex destination                                                                          | PR shape                                                                  | falsifier T4              |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------- |
| Aggregate frontend-eval pass rate per release           | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)                | cross-cutter: frontend-fidelity axis added to quality table               | cross-cutter              |
| Per-family failure dist + adversarial drop              | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 Mk.II/Mk.III                 | methodology delta — informs Mk.III adversarial gen on component+a11y      | meta (wraps F-1..4)       |
| Style-audit table (Compiler-1.0 / 2026-canon adherence) | [`hexa-codex/interpret`](../../hexa-codex/interpret/ai-interpretability.md)                     | motif-analog table — (canon-correct, canon-incorrect) per recipe clause   | **F-CODEX-4 T4** analog   |
| T5 AI-UI patterns + tool-use UX (v0.2.0)                | [`hexa-codex/agent_serving`](../../hexa-codex/agent_serving/ai-agent-serving.md)                | tool-use UX canon — abort path + streaming-render reference                | F-CODEX-2 SLO input       |

The hexa-codex `interpret` verb's F-CODEX-4 analog wants **style-motif
evidence** — frontend-eval's T1 (Compiler-1.0 detection) and T4 (2026-
canon-applied count) instantiate that as bench scores rather than raw
corpus audit. The `agent_serving` UX shape benefits from T5's empirical
abort + streaming + retry trace data.

**Outbox path** (per `plan-feedback-channel-ops.md §7`):
- `outbox/hexa-codex/quality_scale/<run_id>-frontend-eval.md`
- `outbox/hexa-codex/eval/<run_id>-frontend-eval-methodology.md`
- `outbox/hexa-codex/interpret/<run_id>-frontend-eval-styleaudit.md`
- `outbox/hexa-codex/agent_serving/<run_id>-frontend-eval-tooluseUX.md` (v0.2.0)

### S8.1 Contribution to v1.0.0 forge gate

`docs/code-llm.md §VERIFY upstream feedback contract` requires ≥ 5
PRs landed in hexa-codex. frontend-eval contributes up to **four**
PRs by design (quality_scale + eval-methodology + interpret + (v0.2.0)
agent_serving). Combined with `hexa-eval` (2 PRs) and `5-NL eval` (up
to 5 PRs), the ≥ 5 gate is trivially reachable from the eval surface
alone.

## S9 Tooling

Two scripts (planned; not yet written):

| script                              | reads                                                                          | writes                                                                                                                    | status  |
| ----------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | ------- |
| `tool/run_frontend_eval.py`         | `tests/frontend-eval/tasks/*.toml` + candidate model endpoint                  | `runs/<id>/frontend-eval.parquet` + per-task JSON + Playwright traces                                                     | PLANNED |
| `tool/emit_frontend_eval_pr.py`     | `runs/<id>/frontend-eval.parquet`                                              | `outbox/hexa-codex/{quality_scale,eval,interpret,agent_serving}/<id>-frontend-eval-*.md`                                  | PLANNED |

Both follow the existing `tool/emit_t4.py` shape (already in repo).
`run_frontend_eval.py` orchestrates Playwright headless + axe-core
+ Vitest in the headless browser + tree-sitter-CSS rule-pack scan +
Lighthouse. `emit_frontend_eval_pr.py` is the codex-PR emitter.
Wiring matches
[`plan-feedback-channel-ops.md §3`](plan-feedback-channel-ops.md)
automation triggers — emit on bench-run-complete.

**Browser engine pin.** `run_frontend_eval.py` pins Chromium build
SHA (axe results drift across major Chromium versions; ARIA-tree
exposure also varies). Cross-engine sanity probe (Firefox + WebKit)
runs at Mk.IV+ as a separate diagnostic, not a gate.

**Determinism contract.** Both scripts honour:
- `SOURCE_DATE_EPOCH` for any timestamps in output
- pinned hashes for shadcn registry SHA + canon-anchor (F-1/F-2/F-3)
  + task set + Playwright + axe-core + Lighthouse versions
- exit code 0 on aggregate pass; non-zero with structured stderr on
  any of (aggregate < 65%, T1 axe-clean < 90%, T2 new-violation > 0%,
  T3 agreement < 80%)

**Not in scope for v0.1.3.** Actual task TOMLs
(`tests/frontend-eval/tasks/`), the gold-component corpus, runner
implementation, or the public leaderboard — those land v0.1.3+ after
D-007 (base weights) closes and there is a candidate model to run
against.

---

## Open questions (v0.1.2 → v0.1.3 handoff)

- [ ] **D-NEW-H** — T1 multi-framework per task (same spec emitted in
      React+Vue+Svelte) or single-framework? *Proposed: single per task
      at Mk.II; multi-framework as Mk.III adversarial probe (cross-
      framework drop ≤ 15pp). Multi-framework as primary scorer doubles
      authoring cost without proportional signal.*
- [ ] **D-NEW-I** — T3 reference labels: single-reviewer vs ≥ 2-
      reviewer agreement? *Proposed: ≥ 2-reviewer for "mixed" tasks
      (the ambiguous tail); single-reviewer for the 50% server / 40%
      client unambiguous bulk. Lighter than `spec-five-nl-eval.md
      §D-NEW-D` because RSC decisions are more deterministic than
      commit-message judgments.*
- [ ] **D-NEW-J** — T4 rule-pack: tree-sitter only, or supplement with
      a JS-AST Tailwind class-drift scan (e.g. `text-gray-500` legacy
      vs new `text-fg-secondary` token)? *Proposed: tree-sitter only
      at Mk.II; class-drift deferred to Mk.III as optional, non-blocking.*
- [ ] **D-NEW-K** — T2 "semantic-preferable" rule (no `role` where
      element exists): hard fail or `STYLE_NOTE`? *Proposed: hard fail
      at v1.0.0 (matches "no ARIA is better than bad ARIA"); soften
      only if Mk.II shows ≥ 20% false-positive rate against reviewers.*
- [ ] **D-NEW-L** — T5 enablement timing: v0.2.0 hold, or accelerate
      to v0.1.x once Vercel AI SDK abort canon stabilises (4.x current
      2026-05; abort-signal stability across providers UNVERIFIED)?
      *Proposed: hold at v0.2.0; revisit after F-3 Part 3 UNVERIFIED
      items close.*

Resolved decisions referenced by this spec:
- D-024 (frontend stage placement — filter expansion) — closed 2026-05-11
- D-025 (frontend canon corpus sourcing — F-1/F-2/F-3 landed) — closed 2026-05-11
- D-026 (mobile / cross-platform — RN+Expo+Capacitor+Tauri T1, Flutter T2 quote-only) — closed 2026-05-11
- D-027 (AI-native UI corpus — Vercel AI SDK + AI Elements; no LLM-judge) — closed 2026-05-11
- D-028 (v0.1.x bench scope — 4 benches, T5+T6 deferred) — closed 2026-05-11
- D-013 (no LLM-judge for gold output) — closed 2026-05-11

---

## Cross-link

- Recipe SSOT: [`../docs/code-llm.md`](../docs/code-llm.md) §EVOLVE
  frontend rows (acceptance gate ⑦) + §VERIFY frontend tool surface
  (`run_dev`/`read_console`/`a11y_check`/`bundle_analyze`/`lighthouse`/
  `visual_diff`) + §VERIFY style contract (2026-canon-first).
- Sister specs: [`spec-hexa-eval.md`](spec-hexa-eval.md) (gate ③) +
  [`spec-five-nl-eval.md`](spec-five-nl-eval.md) (gate ④) — section
  shape parent.
- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
  (D-013, D-024, D-025, D-026, D-027, D-028).
- Domain coverage: [`plan-domain-coverage.md §9`](plan-domain-coverage.md)
  (§9.1 axes, §9.3 §EVOLVE row source, §9.4 §VERIFY tools, §9.5
  §VERIFY style-contract source).
- Feedback channel ops: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md).
- Canon SSOT (frontend):
  [`frontend-f1-findings.md`](frontend-f1-findings.md) — frameworks
  (React 19 + Compiler 1.0, Vue 3.6 Vapor, Svelte 5 runes, Angular 21
  zoneless), meta-frameworks (Next App Router / Nuxt 4 / SvelteKit /
  Astro 5), shadcn + Radix + Base UI, TanStack Query + Zustand + RHF
  + nuqs state.
  [`frontend-f2-findings.md`](frontend-f2-findings.md) — CSS canon
  (container queries, OKLCH, `:has()`, Anchor Positioning 2026,
  `<dialog>`, Popover API, Logical Properties), Tailwind v4 Oxide,
  Vite 6 / rolldown / Bun / Turbopack / Rspack.
  [`frontend-f3-findings.md`](frontend-f3-findings.md) — perf (INP
  replaced FID 2024-03, Speculation Rules, bundle budgets), a11y
  (WCAG 2.2 legal floor, "good a11y = good agent-ability"), AI-UI
  (Vercel AI SDK + AI Elements, AbortController + AbortSignal.any,
  Transformers.js / ONNX Web / Web LLM / WebNN), testing (Playwright
  + Vitest + Testing Library + axe-core).
- Methodology canon: [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.I–Mk.V shape source.
