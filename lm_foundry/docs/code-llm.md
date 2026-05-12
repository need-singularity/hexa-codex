# `code` — programming-only LLM recipe

> **Foundry verb.** Research recipe for a code-only LLM that beats general
> models on the languages, build systems, and tooling we actually use —
> not a general chat model fine-tuned on GitHub.
>
> **Dual goal.** Ship a working `code`-verb LLM **AND** improve the
> sister spec catalog `hexa-codex` upstream as a side effect. Every
> real number forge measures (training cost, inference latency, eval
> rates, refusal accuracy, hexa-fidelity rate, DPO yield) is a
> candidate T4 empirical contribution to hexa-codex's 4 F-CODEX
> falsifiers and 17 verb specs. See §VERIFY "upstream feedback
> contract" + Cross-link policy "feedback channel".

| field        | value                                                       |
| ------------ | ----------------------------------------------------------- |
| verb         | `code`                                                      |
| family       | `hexa-forge`                                                |
| status       | `RESEARCH_FIRST` (spec only, no weights)                    |
| dispatch     | `hexa-forge code`                                           |
| sibling CLIs | `hexa-codex serve` (inference), `hexa-chip` (training fab)  |

---

## §WHY

General foundation models spread capacity across natural language,
math, multimodal, and roleplay. A **programming-only** model concentrates
that capacity on the surface area we actually edit:

- core langs: **hexa, Python, Rust, TypeScript, Go, C, Zig, SQL**
- build systems: cargo, uv, npm/pnpm, go mod, bazel, make, west, idf.py, pio
- shells: bash, zsh, fish, posix
- diff / patch / git plumbing
- LSP, tree-sitter, AST-level reasoning
- **databases & query engines**: relational (PostgreSQL / SQLite / DuckDB),
  vector (pgvector / Qdrant / Chroma / LanceDB), KV (Redis), OLAP
  (ClickHouse), wide-column (Cassandra), stream (Kafka), graph
  (Cypher / openCypher) — query language + schema design + EXPLAIN
  literacy + migrations + ORM patterns
- **systems & firmware**: bare-metal C (volatile, MMIO, interrupts,
  DMA, linker scripts, boot sequences), RTOSes (Zephyr / FreeRTOS /
  NuttX / Mbed / Embassy / Tock), MCU targets (Cortex-M, RISC-V 32,
  Xtensa ESP32), hexa firmware tree (`firmware/boards/{rtsc,chip,cern,antimatter,space}` +
  `stdlib/{core,alloc,hal,embedded,mcu}`)
- **hardware reference literacy**: ARM CMSIS, RISC-V ISA spec,
  ESP-IDF, Pi Pico SDK, peripheral datasheet pattern reading
- **frontend / web app (2026 canon)**: React 19 + Compiler 1.0 / Vue 3
  Composition+Vapor / Svelte 5 runes / Solid / Angular 21 zoneless;
  meta-frameworks (Next App Router / Nuxt / SvelteKit / Astro Islands /
  TanStack Start); Tailwind v4 (Oxide + `@theme` CSS-first + OKLCH);
  shadcn/ui paradigm + Radix / Base UI primitives; TanStack Query +
  Zustand + nuqs + RHF; native `<dialog>` / Popover API / Container
  Queries / `:has()` / View Transitions / Anchor Positioning;
  WCAG 2.2 a11y; INP-driven Core Web Vitals; AI-native UI (streaming
  + AbortSignal + agent-friendly DOM)
- **code-adjacent natural language**: English (T0 — code lingua franca)
  + Korean / Chinese / Russian / Japanese (T1 — code-adjacent prose,
  PR comments, issues, commit messages). **Diagnostics English-only**
  per hexa-lang SPEC §7 (Korean i18n permanently closed); refusal
  contract text English-canonical.

The win isn't tokens-per-dollar — it's **fewer hallucinated APIs,
correct build incantations, and AST-faithful refactors** at parameter
counts a single workstation can serve.

On top of that mechanical win, the model bakes in a **native-first,
canonical-first** prior:

- **native-first** — prefer language-native idioms over translated
  patterns. Idiomatic Rust (ownership + `Result`) over Java-ported
  Rust; Pythonic (comprehensions, duck typing) over C-style Python;
  Effective Go over OOP-ported Go.
- **canonical-first** — prefer hexa-canon patterns (verb/§-skeleton
  doc shape, cross-link policy, `RESEARCH_FIRST` discipline) over
  ad-hoc invention when a canon entry exists.

Both priors are taught at every stage (data mix, SFT format, DPO
preference, refusal) — not bolted on as a system prompt.

## §COMPARE

| approach                       | strength                          | weakness                                  |
| ------------------------------ | --------------------------------- | ----------------------------------------- |
| general FM (Opus/GPT)          | broad reasoning                   | hallucinates obscure APIs; expensive      |
| existing code-LLM (Codestral, Qwen-Coder, DeepSeek-Coder) | strong general code | no `hexa` lang; no project-specific build muscle |
| **hexa-forge `code`**          | hexa-native, AST-aware, cheap     | narrow — useless for prose / general chat |

## §REQUIRES

- base model: open-weights mid-size (target **7B–14B params**, MoE optional)
  > **Conflict note (MoE, conflict 4).** hexa-codex `train_cost` BT-384 +
  > `quality_scale` §S7.0 (`MOE_EXPERTS=8`, top_k=2) assume MoE. Forge
  > §REQUIRES is **dense-only at v1.0.0** (Qwen2.5-Coder-7B base
  > candidate per D-007). **Not an active conflict** — MoE is a v1.1.0+
  > path if a MoE-capable base emerges (e.g. DeepSeek-MoE-Lite).
- compute: **LoRA (r=16) on 1× H100 / Mac Studio is the iteration default**;
  8× H100 / 8× MI300 full-FT remains the fallback path required by the
  §VERIFY reproducibility gate ⑪. Both regimes supported. (D-NEW-TC-C)
- precision: **BF16 default** for both pretrain-continued and SFT
  (D-NEW-TC-A); FP8 QAT pilot deferred to v0.2.0 hardware audit.
- gradient checkpointing **on by default at 7B+** during SFT (must).
- ZeRO-3 / FSDP sharding optional for full-FT escalation (should).
- sequence packing **on by default** (must) — saturates batch tokens
  on short-document corpora.
- optimizer: **AdamW** with **WSD (Warmup-Stable-Decay) LR schedule**,
  `stable_frac=0.8`, `warmup=2000` (D-NEW-TC-D). β=(0.9, 0.999), wd=0.1.
- data licensing: permissive-only (MIT / Apache / BSD / Unlicense / public domain).

> **sibling spec (live):** scaling/cost numbers (N, D, FLOP budget) follow
> the canon in [`hexa-codex/train_cost`](../../hexa-codex/train_cost/ai-training-cost.md)
> (F-CODEX-1: training_cost ∝ N^24). Do NOT duplicate the formula here —
> consult that spec at planning time.

> **Conflict note (D-NEW-TC-C).** hexa-codex `quality_scale` BT-388 favours
> LoRA r=16 (0.24% trainable, fits 1×H100). Forge §VERIFY reproducibility
> gate ⑪ requires full-FT 8×H100 capability so any external party can
> reproduce a release. Resolution: **LoRA is the iteration default**
> (fast, cheap, ~88% of full-FT quality per BT-388), **full-FT is the
> gate-blocking reproducibility path**. Both are first-class supported;
> the choice is per-run, not per-recipe.

## §STRUCT — dataset

> **sibling spec (live):** dataset shape + dedup + license-clean gate
> canon = [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md)
> §S4 STRUCT (3-axis: eval-gen / eval-execute / meta-eval). Detail per
> stage in [`papers/plan-domain-coverage.md`](../papers/plan-domain-coverage.md).
>
> **Quality-filter ladder (D-NEW-TC-E, must).** A **corpus perplexity
> gate** is applied upstream of the `pretrain-bias` Stack v2 permissive
> subset (per-source `PPL_threshold`, paired with the existing
> license-clean + anti-corpus filters). Implementation lands in
> `tool/corpus_quality_filter.py` (v0.1.2 sampling pipeline).
>
> **Synthetic-data ceiling (D-NEW-TC-B, must).** The `philosophy` stage
> applies `×5-10 principle×idiom synth` expansion (Tier D); the
> **synthetic share is capped at 80% of any stage's effective tokens**,
> preserving a real-data majority. A 5-generation variance monitor
> watches for Shumailov-style collapse across regen cycles.
>
> **Weights (cross-link to `datasets.toml`).** `weight = 10.0` reserved
> for `hexa-canon` / `hexa-native` Tier D entries (preserved); all
> others default to `weight = 1.0`. Per-entry `weight` adjustments are
> made directly in `datasets.toml`.

| stage             | corpus                                                                                                      | size target                       | filter                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------- |
| pretrain-bias     | The Stack v2 + StarCoder dedup                                                                              | ~600B tok (perm subset; **deliberate D/N≈85 over-train** per §FLOW Stage 1 note) | permissive only; near-dup (MinHash + semantic); **perplexity gate (D-NEW-TC-E)** |
| domain-bias       | crates.io top-10k, npm top-10k, PyPI top-10k, hexa stdlib + ecosystem; **+ meta-fw (Next/Nuxt/SvelteKit/Astro/Vite/Tailwind/shadcn/Radix/TanStack)** | ~150B tok | parseable + builds green                                                                |
| build-trace       | reproduced `cargo build` / `uv pip install` / `go build` / **`vite build` / `next build` / `bun build` / `playwright test`** traces | ~20B tok                | success-only; failure-with-fix paired                                                   |
| diff-edit         | GitHub PR diffs (merged) with surrounding context; **5-NL filter (EN T0 ~70%, KR+CN+RU+JA aggregate ~30%)** | ~30B tok                          | merged + CI green; squash-only                                                          |
| repair            | failing test → fix patch (synth + real); **linter-autofix on Stack v2 (clippy/ruff/golangci) → 2-5M DPO pairs** | ~5B tok                       | regenerated test must pass                                                              |
| hexa-native       | every `~/core/hexa-*` repo + canon corpus; **post-2026-05-10 commits only; `legacy/`, `archive/`, `*.deprecated.*` excluded** | ~2B tok | full repo; weighted ×10 in domain-bias mix                                              |
| philosophy        | lang-native idiom canon (Tier A) + cross-lang principles (Tier B) + post-mortem canon (Tier C) + hexa-canon §-docs (Tier D ×10) + anti-corpus DPO negatives (Tier E) — per [`papers/tier-{a,b,c,e}-findings.md`](../papers/) + [`papers/frontend-f{1,2,3}-findings.md`](../papers/) | **~500M-1B effective** (raw ~30M + ×10 weight + ×5-10 principle×idiom synth, **synth share ≤ 80% per D-NEW-TC-B**) | license-clean only; native-first + canon-first + 2026-canon-first priors |
| **db-native**     | PostgreSQL / SQLite / DuckDB / pgvector / Qdrant / Chroma / LanceDB / Redis / ClickHouse / Cassandra / Kafka / Cypher (T1 full) + MySQL / MongoDB / Elasticsearch (T2 quote-only) + EXPLAIN traces + migration playbooks (alembic / flyway / atlas / prisma / sqitch) + ORM idioms (SQLAlchemy / sqlx / Diesel / GORM / Prisma) | **~15B tok** (after synth) | T1=Apache-2/MIT/BSD/PG-Lic full; T2=GFDL/NC-SA quote-only; proprietary (Oracle/MSSQL/Snowflake/BigQuery/DynamoDB) skip |
| **firmware-native** | Zephyr (Apache-2) / FreeRTOS (MIT) / NuttX (Apache-2) / Mbed (Apache-2) / Embassy (MIT/Apache-2) / Tock (MIT/Apache-2) / ESP-IDF (Apache-2) / Pi Pico SDK (BSD-3) / ARM CMSIS (Apache-2); RIOT (LGPL) + ChibiOS/u-boot/coreboot/Linux drivers (GPL) → quote-only | **~10B tok** | permissive only; GPL→quote; vendor SDK per-license audit |
| **hexa-firmware** | `~/core/hexa-{rtsc,chip,cern,antimatter,space}` + `~/core/hexa-lang/firmware/boards/*` + `stdlib/{core,alloc,hal,embedded,mcu}` + `linker_scripts/*.ld`; **NEW absorbed form per hexa-lang SPEC §18; old standalone-repo form excluded** | **~3B tok** | full repo; weighted ×10 |

## §FLOW — training stages

1. **Stage 0 — base.** Take open-weights base (no adaptation).
2. **Stage 1 — domain pretraining.** Continued pretraining on the
   `pretrain-bias → domain-bias → hexa-native` mix (curriculum order:
   broad → narrow, hexa-native last). ~1 epoch.
   > **Conflict note (Chinchilla, §6 conflict 5).** hexa-codex
   > `train_cost` §S7.0 prescribes D/N ≈ 20 (Chinchilla optimum). Forge
   > `pretrain-bias = ~600B tok` on a 7B base ⇒ D/N ≈ 85, i.e. **~4×
   > over-trained**. This is a **deliberate violation** in the LLaMA
   > tradition (inference-cost-dominant target — laptop serve), per
   > `train_cost` §S7.10 COUNTER ("LLaMA-style 140"). The actual
   > `D_over_N_actual` is emitted to `outbox/hexa-codex/train_cost/`
   > Numbers so the violation is auditable.
3. **Stage 2 — SFT.** Supervised fine-tune on `diff-edit + repair +
   build-trace`. Format: `<context><instruction><patch>`.
   - **regime:** LoRA r=16 default (see §REQUIRES D-NEW-TC-C).
   - **precision:** BF16 (D-NEW-TC-A); gradient checkpointing on.
   - **optimizer:** AdamW with WSD schedule (D-NEW-TC-D),
     lr=3e-4, β=(0.9, 0.999), wd=0.1.
   - **batch:** `grad_accum_steps = 24` per hexa-codex BT-54 / P-TRN-6
     (`J₂(6) = 24`); sequence packing on.
4. **Stage 3 — DPO/KTO.** Preference pairs from CI signal: passing
   patch ≻ failing patch. No human raters at v0.1.0. Tree-sitter
   rule pack v1 is the scoring substrate (per D-013).
   > Preference-data shape canon: [`hexa-codex/rlhf`](../../hexa-codex/rlhf/youth-ai-labeling-rlhf-hub.md).
   > **Conflict note (D-NEW-TC-J).** hexa-codex `quality_scale` Mk.IV +
   > `eval` Mk.III prescribe LLM-judge as core methodology. Forge **defers
   > LLM-judge to v2** for explicit Shumailov 2024 model-collapse-risk
   > reasons. D-013 stands. When v2 re-opens, D-NEW-H proposes an 80/20
   > LLM/human-anchor calibration ratio (currently a forge-side proposal
   > awaiting upstream alignment).
5. **Stage 4 — distillation.** 14B → 7B for laptop serve.
   **Promoted from optional to must for the laptop tier** per hexa-codex
   `quality_scale` BT-386. Defaults: `KD_TEMPERATURE=4.0`, per-layer KD
   loss; acceptance bar ≥ 85% MMLU/HumanEval retention vs teacher.
6. **Stage 5 — test-time compute scaling (placeholder).** Best-of-N
   sampling at inference time (D-NEW-TC-I; default N=4 on hexa-eval).
   This surface is **currently absent from hexa-codex** — forge plants
   the placeholder and will feed findings back to
   `hexa-codex/quality_scale` §S6 EVOLVE Mk.III. Not v1.0.0-blocking.
   > **Conflict note (D-NEW-TC-I, conflict 7).** Test-time compute
   > scaling is a **gap in the upstream specs** (none of the 5 hexa-codex
   > verbs cover CoT / ToT / best-of-N / self-consistency systematically).
   > Forge initiates this surface independently and flows results upstream
   > as Mk.III input.

## §EVOLVE — eval harness

> **sibling specs (live):** pipeline shape + capability-gate canon =
> [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md);
> acceptance bars cross-checked against
> [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md).
> **Bidirectional feedback:** real eval outputs from forge runs feed
> back into `hexa-codex/eval` Mk.I → Mk.V refinement and into the
> F-CODEX-3 (alignment) + F-CODEX-4 (interpret) T4 empirical floors
> (see [Cross-link policy](#cross-link-policy) "feedback channel").

> **Eval methodology (D)**: forge inherits dynamic-item-gen + contamination
> detection + adaptive testing from `hexa-codex/eval` Mk.II at v0.2.0
> (currently deferred — D-NEW-TC-J). LLM-judge calibration ratio 80/20
> per D-NEW-TC-H (proposed default; awaiting upstream alignment per
> §3.2 conflict 6).
>
> **Conflict note (D-NEW-TC-H, conflict 6).** Task-prompt asserts forge's
> default `80/20` LLM-judge / human-anchor ratio; hexa-codex/eval §S7.0
> only sets `HUMAN_LLM_CORRELATION_MIN = 0.85` and §S6 Mk.III prescribes
> "human anchor 5-10%". The 80/20 ratio is **stricter than the upstream
> baseline** and is a forge-side proposal awaiting upstream alignment.
>
> **Conflict note (D-NEW-TC-J, conflict 3).** hexa-codex `eval` BT-395
> prescribes dynamic item generation, which presupposes LLM-gen. D-013
> bars LLM-gen for synth corpus (same Shumailov risk). Resolution:
> dynamic hexa-eval is **deferred to v1.1.0**, contingent on D-NEW-TC-H
> reopening D-013.

| group              | benchmark                              | what it measures                                 | acceptance bar                          |
| ------------------ | -------------------------------------- | ------------------------------------------------ | --------------------------------------- |
| code synthesis     | HumanEval+                             | function synthesis                               | ≥ DeepSeek-Coder-V2-7B                  |
| code synthesis     | SWE-bench Lite                         | real GitHub issue resolution                     | ≥ 25%                                   |
| code synthesis     | LiveCodeBench                          | recency-robust competitive                       | ≥ Qwen2.5-Coder-7B                      |
| code synthesis     | **hexa-eval** (custom)                 | hexa-lang synthesis + canon spec adhere          | ≥ 80% pass                              |
| code synthesis     | build-real                             | `cargo build`, `uv sync` from spec                | ≥ 90% green                             |
| refactor           | AST-faithful refactor                  | tree-sitter equivalence after rename             | ≥ 95%                                   |
| **multilingual**   | **5-NL eval** (custom)                 | code task instructions in EN / KR / CN / RU / JA | ≥ 70% pass cross-lang                   |
| **database**       | Spider / BIRD                          | natural-language → SQL                           | ≥ 60% exec-correct                      |
| **database**       | EXPLAIN literacy (custom)              | query plan reading + bottleneck ID               | ≥ 70% pass                              |
| **database**       | schema-design (custom)                 | requirements → DDL + indexes                     | ≥ 70% pass                              |
| **firmware**       | MCU-bench (custom)                     | peripheral init / IRQ / DMA correctness          | ≥ 50% pass on Cortex-M target          |
| **firmware**       | linker-script literacy (custom)        | section placement + boot                         | ≥ 70% pass                              |
| **firmware**       | memory-fit (custom)                    | codegen under SRAM/FLASH budget                  | ≥ 80% hit budget                        |
| **firmware**       | hexa target gate (custom)              | `--target=*-none-*` rejects host stdlib import   | 100% correct rejection                  |
| **frontend**       | component-synthesis (custom)           | spec → React/Svelte/Vue component                | passes Vitest + Testing Library         |
| **frontend**       | a11y-fix (custom)                      | given axe-core violation → fix without regression | violation resolved, 0 new violations    |
| **frontend**       | RSC-vs-client decision (custom)        | pick `'use server'` vs `'use client'` correctly  | ≥ 80% agreement with reference          |
| **frontend**       | CSS-modernize (custom)                 | legacy CSS → 2026 canon (container queries, `:has()`, OKLCH where fit) | ≥ 75% appropriate use |
| **hexa fidelity**  | S0–S8 lint pass (custom)               | generated hexa code passes hexa-lang lint stages | 100% pass (refuse rather than emit bad) |
| **safety**         | off-domain refusal                     | non-programming asks refused (5 NL)              | ≥ 95% (per [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md)) |

## §VERIFY — serving contract

> **sibling specs (live):** the live SSOT for serving contracts is hexa-codex.
> When this doc and hexa-codex disagree, **hexa-codex wins** — update here, do
> not fork:
> - tool-use + agent-loop schema → [`hexa-codex/agent_serving`](../../hexa-codex/agent_serving/ai-agent-serving.md)
> - inference cost / context scaling → [`hexa-codex/infer_cost`](../../hexa-codex/infer_cost/ai-inference-cost.md) (F-CODEX-2: cost ∝ context^4)
> - deployment patterns → [`hexa-codex/deploy`](../../hexa-codex/deploy/ai-deployment.md)
> - refusal / safety guardrails → [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md), [`alignment`](../../hexa-codex/alignment/ai-alignment.md), [`adversarial`](../../hexa-codex/adversarial/ai-adversarial.md)
> - style/idiom audit at inference → [`hexa-codex/interpret`](../../hexa-codex/interpret/ai-interpretability.md)

- **inference**: handed off to `hexa-codex serve` (NOT served from this repo).
- **input contract**: chat-completion + tool-use schema per
  [`hexa-codex/agent_serving`](../../hexa-codex/agent_serving/ai-agent-serving.md).
  Tool surface:
  - **code core** — `read_file`, `apply_patch`, `run_build`, `run_test`, `lsp_query`
  - **systems/firmware** — `run_size`, `read_map`, `read_disasm`, `read_register`
  - **database** — `run_query` (sandbox), `explain_query`, `apply_migration`, `read_schema`
  - **frontend** — `run_dev`, `read_console` (Playwright-driven), `a11y_check` (axe-core), `bundle_analyze`, `lighthouse`, `visual_diff`
- **output contract**: unified-diff patches OR full file rewrites.
  No prose without a code block.
- **style contract**: **native-first + canon-first + 2026-canon-first.**
  Generated code:
  - **native-first** — idiomatic Rust over Java-port, Pythonic over
    C-style, Effective Go over OOP-port, Svelte 5 runes over stores,
    Vue 3 Composition over Options API, React hooks (Compiler 1.0 — no manual `useMemo`/`useCallback`).
  - **canon-first** — hexa-canon patterns (verb / §-skeleton / cross-link /
    `RESEARCH_FIRST`) over ad-hoc.
  - **2026-canon-first** — `<dialog>` over modal libs, Popover API over
    `position:absolute` hacks, Container Queries over media queries
    when scope is component-local, OKLCH over HSL for new tokens,
    `:focus-visible` not `:focus`, Speculation Rules API over
    `<link rel=prefetch>` for navigation, INP-driven (not FID),
    WCAG 2.2 compliance not 2.1.
  - **a11y-by-default** — generated UI passes axe-core with zero
    violations; semantic HTML first, ARIA only when semantic HTML
    insufficient ("no ARIA is better than bad ARIA"). Good a11y =
    good agent-ability — the accessibility tree is what agents read.
  - **streaming-aware** — AI-facing components render incrementally,
    support `AbortSignal` (and `AbortSignal.any` for composition),
    never block on full completion.
- **hexa fidelity contract** (mirrors `~/core/hexa-lang/SPEC.md`):
  - **PRIMARY = native-compiled** (`hexa cc` pipeline); **SECONDARY =
    slim AST interp** (`--interp` / `hexa repl`, ~200-500 LOC walker).
    The old 20k-LOC `hexa_interp` is NOT a teaching target.
  - S0–S8 lint pass mandatory; S8 citation (`L[*]` references) requires
    `@implements(L[<id>])` or `@discover(kind="L")` binding.
  - `HX[CCCC]` error code format; `@grace` annotations require all 3
    fields (`HXxxxx`, `until=YYYY-MM-DD`, `reason="…"`); silent
    `@grace` forbidden — `HX9000` warning + `Acked-grace` trailer
    required at PR-time.
  - Memory: arena (1.x) or borrow check (2.x) only. **No GC, no
    ref-counting, no manual `free` in 1.x.**
  - **No Z3 / CVC5 prover bindings.** In-house prover only.
  - Diagnostics: **English-only** (Korean i18n permanently closed).
  - Codegen: direct pipeline, **no LLVM, no C-transpile** as a target
    pattern (the bootstrap artifact `hexa_cc.c` is not a pattern source).
  - For `--target=*-none-*` (firmware), reject host-stdlib imports
    (`stdlib/{net,http,fs,process,json,…}`).
- **refusal contract**: refuse non-programming asks (jokes, prose, math
  not embedded in code) regardless of input language (EN / KR / CN /
  RU / JA). Refusal text English-canonical:
  `out-of-domain: this is a code-only model`. Per
  [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md) +
  [`alignment`](../../hexa-codex/alignment/ai-alignment.md) +
  [`adversarial`](../../hexa-codex/adversarial/ai-adversarial.md).
- **hardware tier** (laptop-serve via `hexa-codex`; cost canon per
  [`hexa-codex/infer_cost`](../../hexa-codex/infer_cost/ai-inference-cost.md)
  F-CODEX-2 context^4 scaling — each Q-tier change implies a ~4× cost
  rotation per the canon, so down-tiering is never free):
  - **M4 Mini 16GB** → **7B @ Q5_K_M / Q6_K** (default laptop tier;
    leaves headroom for 16-32k KV + IDE + browser)
  - **M4 Pro Mini 24GB** → 14B @ Q6_K
  - **Mac Studio 32GB+** → 14B @ Q8_0 or 32B @ Q4_K_M
  - 7B fp16 and 14B Q8 do NOT fit M4 Mini 16GB — flag at serving time.
  - **No down-tiering to Q2/Q3** on 8GB hosts: refuse-serve rather than
    cross the INT3 quality floor (hexa-codex `infer_cost` §S7.10).
- **serving optimisations** (cross-link to
  [`hexa-codex/infer_cost`](../../hexa-codex/infer_cost/ai-inference-cost.md)):
  - **speculative decoding γ=5** on the 14B+ tier with a 7B draft
    (D-NEW-TC-F, should) — code-gen low-entropy gives ~2-3× speedup.
  - **prefix cache mandate** (D-NEW-TC-G, must) — forge agent loops
    re-use long stable system prompts; T4 PRs must emit
    `cache_hit_rate` in `outbox/hexa-codex/infer_cost/<run_id>.md`.
  - **KV-cache compression / paged attention** (should) — INT4 KV +
    paged attention (vLLM-style) for serving long contexts on Apple
    Silicon and 1×H100 tiers.
  - **FlashAttention** (should — already implicit in modern tokenizers
    + llama.cpp Metal kernels; documentation only).
- **deployment patterns** (cross-link to
  [`hexa-codex/deploy`](../../hexa-codex/deploy/ai-deployment.md)):
  - SLO targets (reject < 2%, hallucination < 1%, p99 < 500ms,
    injection-block > 95%) live in the deploy spec. Forge has **no
    serving fleet at v1.0.0**, so the canary / rollback / A-B-test
    patterns are downstream of forge — sparsest section of the
    mapping (most rows n/a). Forge's upstream contribution is the
    hardware-tier deployment recipe per the feedback channel.
- **upstream feedback contract** (forge → codex loop):
  - Every forge run that produces a real number (training cost,
    inference latency curve, eval pass rate, refusal accuracy,
    a11y compliance, hexa-fidelity rate) becomes a **PR candidate
    to `hexa-codex/<verb>`** as T4 live-hardware empirical data.
  - Specifically: forge SFT runs → `train_cost` T4 (F-CODEX-1);
    inference latency on M4 tiers → `infer_cost` T4 (F-CODEX-2);
    HumanEval+ / hexa-eval / 5-NL pass rates → `quality_scale`;
    safety refusal rate → `safety` / `alignment` / `adversarial`;
    style-audit results (native-first / 2026-canon-first compliance) → `interpret` (F-CODEX-4 motif analog);
    eval methodology learnings → `eval` Mk.I → Mk.V refinement;
    DPO yield + judge-quality numbers → `rlhf`.
  - **Acceptance bar (v1.0.0 gate, see Cross-link policy "feedback channel"):**
    ≥ 5 PRs landed in `hexa-codex` from forge findings.

---

## Cross-link policy

> **hexa-codex linkage rule (bidirectional).** hexa-codex is the **live
> AI-spec sibling** (17 verbs × 4 groups, updated frequently). The
> linkage is **two-way by design** — forge consumes hexa-codex specs
> as SSOT, and forge findings flow back as PR contributions that
> improve hexa-codex. The forge's own success criteria include
> upstream-improvement throughput (§VERIFY "upstream feedback contract").
>
> - **Downward (read):** for every cross-cutting AI concern (cost,
>   eval, alignment, serving, …), the verb spec in hexa-codex is the
>   SSOT. This doc references hexa-codex by URL only — **never
>   inline-copy hexa-codex content here** (it would drift).
> - **Upward (write):** every real number forge produces (training
>   cost, inference latency, eval pass rate, refusal accuracy, a11y
>   compliance, hexa-fidelity rate, DPO yield) is a PR candidate to
>   the matching hexa-codex verb — landing T4 live-hardware empirical
>   data per `hexa-codex/<verb>` Mk.I → Mk.V progression and per
>   F-CODEX-N falsifier closure_pct at recipe §9 layer.
>
> ### Feedback channel (forge → codex PR map)
>
> | forge artifact                                  | hexa-codex target                                                                                   | falsifier T4 lands at        |
> | ----------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------- |
> | SFT compute curve (real FLOPs vs loss)          | [`hexa-codex/train_cost`](../../hexa-codex/train_cost/ai-training-cost.md)                          | **F-CODEX-1 T4** (D-004)     |
> | M4 tier latency profile + KV-cache curves       | [`hexa-codex/infer_cost`](../../hexa-codex/infer_cost/ai-inference-cost.md)                         | **F-CODEX-2 T4** (D-005)     |
> | HumanEval+ / hexa-eval / 5-NL pass aggregate    | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)                    | cross-cutter                 |
> | Refusal rate (5-NL × off-domain matrix)         | [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md) + [`alignment`](../../hexa-codex/alignment/ai-alignment.md) + [`adversarial`](../../hexa-codex/adversarial/ai-adversarial.md) | **F-CODEX-3 T4** input (D-006) |
> | Native-first / 2026-canon-first audit (tree-sitter rule pack outputs) | [`hexa-codex/interpret`](../../hexa-codex/interpret/ai-interpretability.md)         | **F-CODEX-4 T4** analog (D-007) |
> | DPO yield + judge-quality numbers               | [`hexa-codex/rlhf`](../../hexa-codex/rlhf/youth-ai-labeling-rlhf-hub.md)                            | substrate input              |
> | Eval methodology refinements (Mk.II → Mk.III handoff template) | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md)                                       | meta — wraps F-CODEX-1..4   |
> | Tool-use schema iterations (forge's actual tool surface) | [`hexa-codex/agent_serving`](../../hexa-codex/agent_serving/ai-agent-serving.md)                    | F-CODEX-2 SLO input          |
> | Hardware-tier deployment recipes (M4 / Mac Studio / H100) | [`hexa-codex/deploy`](../../hexa-codex/deploy/ai-deployment.md)                                     | ops input                    |
> | License-clean CI signals + corpus-license audits | (no direct verb — feeds `enterprise` data-residency)                                                 | ops input                    |
>
> **v1.0.0 forge gate** includes: ≥ 5 PRs landed in hexa-codex from
> forge findings; T4 empirical floor delivered for ≥ 2 F-CODEX-N
> falsifiers (target: F-CODEX-1 + F-CODEX-2 since those have the
> measurement window during SFT/inference dev).
>
> ### Cross-cutting concerns table

| concern                              | sibling                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| inference / serving (runtime)        | `hexa-codex serve` *(planned CLI)*                                                                     |
| training cost / scaling              | [`hexa-codex/train_cost`](../../hexa-codex/train_cost/ai-training-cost.md) (F-CODEX-1)                |
| inference cost / context scaling     | [`hexa-codex/infer_cost`](../../hexa-codex/infer_cost/ai-inference-cost.md) (F-CODEX-2)               |
| quality-scale acceptance bars        | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)                      |
| eval pipeline / capability gates     | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md)                                        |
| agent serving (tool-use schema)      | [`hexa-codex/agent_serving`](../../hexa-codex/agent_serving/ai-agent-serving.md)                      |
| deployment patterns                  | [`hexa-codex/deploy`](../../hexa-codex/deploy/ai-deployment.md)                                       |
| safety / refusal guardrails          | [`hexa-codex/safety`](../../hexa-codex/safety/ai-safety.md)                                           |
| alignment / objective alignment      | [`hexa-codex/alignment`](../../hexa-codex/alignment/ai-alignment.md)                                  |
| adversarial / red-team robustness    | [`hexa-codex/adversarial`](../../hexa-codex/adversarial/ai-adversarial.md)                            |
| interpretability (style / idiom)     | [`hexa-codex/interpret`](../../hexa-codex/interpret/ai-interpretability.md) (F-CODEX-4)               |
| RLHF / preference-data substrate     | [`hexa-codex/rlhf`](../../hexa-codex/rlhf/youth-ai-labeling-rlhf-hub.md)                              |
| neuromorphic training fabric         | `hexa-chip`                                                                                            |
| federated training transport         | `hexa-grid`                                                                                            |
| general / cognitive verbs            | `hexa-mind` (pending)                                                                                  |
| eval data persistence / lineage      | (TBD — likely a future `hexa-lab` standalone)                                                          |

## Open questions (v0.1.0)

> Live ledger: [`papers/plan-decisions-pending.md`](../papers/plan-decisions-pending.md).
> The questions below are the **compute-dependent residue** — anything
> solvable on paper has been moved to the plan docs and resolved by
> default. See `plan-decisions-pending.md §4 Resolved` for audit trail.

- [ ] **base weights (D-007)** — Qwen2.5-Coder-7B (proposed default for CJK+multilingual+M4 Mini fit) vs DeepSeek-Coder-V2-Lite vs StarCoder2-15B. Decided in v0.1.3 G-BASE phase.
- [ ] **tokenizer (D-008)** — extend chosen base BPE for hexa-lang keywords + `@grace/@verify/@implements/L[*]/HX[CCCC]` tokens; retain base multilingual coverage. Decided in v0.1.3.
- [ ] **license-clean sampling (D-009)** — confirm Stack v2 permissive subset ≈ 600B tok measurable on disk. Decided in v0.1.2 corpus audit.
- [ ] **eval lineage (D-010)** — DuckDB (proposed default, sister-pattern with hexa-codex). Cheap to confirm in v0.2.0.
- [ ] **serving format (D-011)** — GGUF first (broadest reach) → MLX laptop → vLLM server. Decided in v0.1.3.
- [ ] **native/canon-first DPO scoring (D-013)** — tree-sitter rule pack v1 (proposed default); LLM-judge deferred to v2 (model-collapse risk per Shumailov 2024). Sketch in v0.1.3; full impl v0.2.0.
- [ ] **Stack Exchange license stance (D-016)** — 보수/중도/공격 (proposed middle: pre-2024-07 Academic Torrents). Legal sanity check in v0.1.2.

**Closed decisions** (see `plan-decisions-pending.md §4`): philosophy
corpus sourcing (resolved via Tier A/B/C/E findings), 5-NL coverage,
hardware tier, DB tier scope, frontend stage placement, hexa-lang
teaching frame, hexa fidelity contract, license downgrades, URL
corrections.
