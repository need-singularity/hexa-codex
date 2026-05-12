# plan — domain coverage matrix (v0.1.x)

> **What surface area the `code` verb must cover, by tier, with license
> + token reality check.** This is the consolidated picture from Tier
> A/B/C/E research + post-SPEC.md firmware finding + 5 NL decision +
> DB tier proposal.

| field        | value                       |
| ------------ | --------------------------- |
| status       | `LIVE`                      |
| feeds        | `docs/code-llm.md §WHY + §STRUCT + §EVOLVE` |
| supersedes   | first-pass guesses in `coding-philosophy-sources.md` §1 (Tier A) |
| dependencies | per-cell decisions tracked in [`plan-decisions-pending.md`](plan-decisions-pending.md) |

---

## §1 Programming languages (8 core)

| lang       | tier | stages consumed                                   | source mix                                                                 | license risk |
| ---------- | ---- | ------------------------------------------------- | -------------------------------------------------------------------------- | ------------ |
| **hexa**   | T0×10 | hexa-native (×10), hexa-firmware (×10), philosophy | local `~/core/hexa-*` repos + canon corpus + this repo's `docs/`         | own license (MIT) — none |
| **Rust**   | T1   | pretrain, domain, build, diff, repair, philosophy | Stack v2 permissive + crates.io top-10k + Rust Book/Nomicon/API guidelines + Rust RFCs + Clippy lint docs | clean (MIT/Apache-2) |
| **Python** | T1   | pretrain, domain, build, diff, repair, philosophy | Stack v2 permissive + PyPI top-10k + PEP 8/20/257 + HOWTOs + Google Style (CC-BY 3.0) | clean (PSF + CC-BY 3.0) |
| **TypeScript** | T1 | pretrain, domain, build, diff, repair, philosophy | Stack v2 permissive + npm top-10k + TS Handbook (CC-BY-4.0) + TC39 proposals (per-repo gate) | mostly clean; TC39 needs per-proposal license scan |
| **Go**     | T1   | pretrain, domain, build, diff, repair, philosophy | Stack v2 permissive + go.dev (CC-BY-4.0): Effective Go, spec, FAQ, blog, CodeReviewComments, Proverbs | clean (CC-BY-4.0) |
| **C**      | T1   | pretrain, domain, build, diff, repair, philosophy, **firmware-native** | Stack v2 permissive + CERT C (CC-BY-4.0 + MIT) + OpenBSD style(9) + ISO C99 Rationale (WG14, fair use) + Linux `Documentation/process/coding-style.rst` (GPL → quote-only) | mixed — Linux kernel docs quote-only |
| **Zig**    | T2   | domain, build, diff, repair, philosophy           | Stack v2 permissive + Zig docs (MIT, `ziglang.org/learn/overview`) — *"Zig zen" page does NOT exist; replaced* | clean (MIT) |
| **SQL**    | T1   | domain, repair, **db-native**                     | PostgreSQL docs (PG license) + SQLite docs (public domain) + DuckDB docs (MIT) — *covered by db-native (§3)* | clean |

→ Decision: **D-020** (C + firmware stage adoption) blocks promoting `C` to its full T1 + firmware-native dual tier.

## §2 Natural-language coverage (5 NL)

| NL          | tier | rationale                              | code-adjacent sources                                  | license posture |
| ----------- | ---- | -------------------------------------- | ------------------------------------------------------ | --------------- |
| **English** | T0   | code lingua franca; lib/doc/identifier de facto | Stack v2 permissive + PR diffs + docs + comments | clean |
| **Korean**  | T1   | user's L1; hexa-canon largely Korean   | `~/core/hexa-*` repo §-docs + Korean PR comments | own; small volume |
| **Chinese (Simplified)** | T1 | largest dev pool ex-EN; Baidu/Alibaba ecosystem | GitHub issues + Stack Overflow Chinese mirror (license gate) + 掘金/CSDN (filter) | mixed; per-source audit |
| **Russian** | T1   | strong systems-prog community         | GitHub issues + Habr (license gate per article) | mixed; per-source audit |
| **Japanese** | T1  | Ruby + OSS culture                    | GitHub issues + Qiita (license gate) | mixed; per-source audit |

**Carve-out (D-023):** hexa-lang diagnostics are **English-only**
per `~/core/hexa-lang/SPEC.md §7` — Korean i18n permanently closed.
5-NL coverage applies to **prose, comments, PR/issue threads, commit
messages** — NOT compiler diagnostics. Refusal contract text remains
English-canonical with 5-NL friendly aliases.

**Stage mechanic:** no new stage. 5-NL is a **filter + weighting** on
existing `diff-edit`, `repair`, `philosophy` stages. NL-tag every
sample; rebalance to ~70% EN / 30% (KR+CN+RU+JA aggregate) target mix.

## §3 Database engines (proposal — D-014 / D-015 gating)

### T1 — full include (license-clean, weight ×1)

| engine        | category      | docs license               | est tokens  |
| ------------- | ------------- | -------------------------- | ----------- |
| PostgreSQL    | relational    | PostgreSQL License (BSD-like) | ~5M       |
| SQLite        | embedded SQL  | public domain              | ~2M         |
| DuckDB        | embedded OLAP | MIT                        | ~1M         |
| pgvector      | vector ext    | PostgreSQL License         | ~50k        |
| Qdrant        | vector OSS    | Apache-2                   | ~1M         |
| Chroma        | vector OSS    | Apache-2                   | ~200k       |
| LanceDB       | vector OSS    | Apache-2                   | ~300k       |
| Redis         | KV / cache    | BSD-3                      | ~3M         |
| ClickHouse    | OLAP          | Apache-2                   | ~2M         |
| Cassandra     | wide-column   | Apache-2                   | ~1M         |
| Kafka         | stream        | Apache-2                   | ~2M         |
| Neo4j Cypher / openCypher | graph spec | Apache-2 (spec)  | ~500k       |

### T2 — quote-only (license-restricted)

| engine        | category      | docs license       | reason for quote-only                |
| ------------- | ------------- | ------------------ | ------------------------------------ |
| MySQL / MariaDB | relational  | GFDL (GPL family)  | text GPL → excerpt only              |
| MongoDB       | doc store     | **CC-BY-NC-SA**    | NC clause blocks bulk training       |
| Elasticsearch | search        | Elastic 2.0 / SSPL | ambiguous re-distribution            |

### T3 — deferred to v0.2.0+ (specialty)

TimescaleDB · InfluxDB · Prometheus · Meilisearch · Typesense ·
JanusGraph · Dgraph · ScyllaDB · CouchDB.

### ❌ Skip entirely

Oracle · SQL Server · Snowflake · BigQuery · DynamoDB —
proprietary docs, scrape/EULA risk.

**Proposed §STRUCT row (D-015 = new stage):**

```
| db-native | T1 engine docs full + T2 quote + EXPLAIN traces + migration playbooks (alembic/flyway/atlas/prisma/sqitch) + ORM idioms (SQLAlchemy/sqlx/Diesel/GORM/Prisma) | ~15B tok (after synth expansion from ~20M raw) | T1=full, T2=quote; permissive only |
```

**Tools added to §VERIFY:** `run_query` · `explain_query` · `apply_migration` ·
`read_schema`.

## §4 Firmware coverage (post-SPEC.md finding)

hexa-lang itself is firmware-native (5 boards under `firmware/boards/*`).
The recipe must teach the model both **upstream RTOS canon** and
**hexa's own firmware tree**.

### Proposed `firmware-native` stage (T1)

| source             | category              | license               | volume          |
| ------------------ | --------------------- | --------------------- | --------------- |
| Zephyr RTOS        | RTOS                  | Apache-2              | large           |
| FreeRTOS           | RTOS                  | MIT                   | large           |
| NuttX              | RTOS                  | Apache-2              | medium          |
| Mbed OS            | RTOS                  | Apache-2              | medium          |
| Embassy (Rust)     | embedded Rust async   | MIT / Apache-2        | medium          |
| Tock OS            | embedded Rust         | MIT / Apache-2        | medium          |
| ESP-IDF            | SDK (Espressif)       | Apache-2 (most)       | large           |
| Pi Pico SDK        | SDK (Raspberry Pi)    | BSD-3                 | medium          |
| ARM CMSIS          | HAL standard          | Apache-2              | medium          |
| RIOT OS            | RTOS                  | LGPL → quote-only     | medium          |
| ChibiOS, u-boot, coreboot, Linux kernel drivers | bare-metal | GPL → quote-only | ref-only |

### Proposed `hexa-firmware` stage (T0×10)

| source                                                  | weight  |
| ------------------------------------------------------- | ------- |
| `~/core/hexa-rtsc` (D+ verified, 70/70 tests)           | ×10     |
| `~/core/hexa-chip`                                      | ×10     |
| `~/core/hexa-cern`                                      | ×10     |
| `~/core/hexa-antimatter`                                | ×10     |
| `~/core/hexa-space` (KiCad-first, deferred Phase E)     | ×10     |
| `stdlib/{core, alloc, hal, embedded, mcu}` (hexa-lang)  | ×10     |
| `firmware/linker_scripts/*.ld` from hexa-lang           | ×10     |

### Hardware reference literacy

- **ARM Cortex-M** reference manuals — proprietary EULA → ref-only (do
  not ingest text; teach pattern via Zephyr/CMSIS examples)
- **RISC-V** ISA specs — CC-BY → full include
- **ESP32 TRM** — proprietary "free to distribute" → quote-only

### Firmware-specific patterns to teach

interrupt handlers · DMA · MMIO + `volatile` semantics · ring buffers
· linker scripts (`.text/.bss/.data/.rodata`) · boot sequences ·
RTOS task/queue/mutex · real-time constraints · CMSIS/HAL patterns ·
cross-toolchain build (`arm-none-eabi-gcc`, `clang --target=thumbv7em-none-eabi`,
`riscv32-unknown-elf-gcc`, `xtensa-esp32-elf-gcc`, west, idf.py, pio,
cargo + `probe-rs`).

### §EVOLVE additions

- **MCU-bench** (custom) — peripheral init / IRQ / DMA correctness
- **linker-script literacy** (custom) — section placement + boot
- **memory-fit** (custom) — codegen under SRAM/FLASH budget
- **hexa target gate** — `--target=*-none-*` rejects host stdlib import

## §5 Philosophy stage (post-tier-research consolidation)

> Per-source detail: [`tier-a-findings.md`](tier-a-findings.md) ·
> [`tier-b-findings.md`](tier-b-findings.md) ·
> [`tier-c-findings.md`](tier-c-findings.md). This is the roll-up.

| tier | role                                  | raw tokens | license verdict                                |
| ---- | ------------------------------------- | ---------- | ---------------------------------------------- |
| A    | language-native idiom canon           | ~22-31M    | mostly clean (Rust/Go/Python/TS/Postgres/SQLite); Linux kernel GPL→quote |
| B    | cross-lang engineering principles     | ~3M        | many downgrades — see D-018 (danluu, NC clauses) |
| C    | post-mortem canon                     | ~2-3.5M    | downgrades — SRE Book→Workbook; Cloudflare `ai-train=yes` ✓; others excerpt |
| D    | hexa-canon (×10 weight)               | local      | own license — clean                            |
| E    | anti-corpus (DPO negatives)           | ~3K hand + ~2-5M lint-mined | linter rule licenses (clippy/ruff/golangci all permissive) |

**Token reality (D-017):** raw sum across A+B+C ≈ **28-37M**, against
the original §STRUCT goal of **~3B tok**. Two orders of magnitude gap.

**Closure plan:**
1. Treat A+B+C raw as **high-signal anchors**, not bulk.
2. Apply **10× weighting** (Tier D pattern) to A+B+C → ~300-370M effective.
3. Synthesize **principle × idiom** pairs (e.g. "DRY in idiomatic Rust"
   instantiates Tier B principle through Tier A idiom) → expand 5-10×.
4. Final §STRUCT row → **~500M-1B effective tok**, NOT 3B. Update
   `docs/code-llm.md §STRUCT philosophy` row.

## §6 Anti-corpus / DPO pipeline (Tier E roll-up)

> Per-language detail: [`tier-e-findings.md`](tier-e-findings.md).

| strategy                                      | yield est.   | confidence | gating decision |
| --------------------------------------------- | ------------ | ---------- | --------------- |
| Linter-autofix on Stack v2 (clippy/ruff/golangci) | 2-5M pairs   | **HIGH** | — (ready)     |
| Lint-rule docs hand examples                  | ~3K pairs    | HIGH       | — (ready)       |
| StackExchange vote-delta pairs                | 1-3M pairs   | MED        | D-016 (license) |
| CodeReviewer dataset (MSR, arxiv 2203.09095)  | 116K samples | MED        | license check   |
| ❌ LLM-judge synthesis                         | —            | **REJECTED** — Shumailov 2024 (model collapse) |

**Exclusion list (pollution):** medium.com / dev.to / hashnode / substack
post-2023; geeksforgeeks/quora/blogspot entirely; common-crawl raw never.

**Author allowlist (pre-LLM voices):** danluu, fasterthanli.me, drewdevault.com,
julia evans, charity.wtf, lwn.net (per-article license).

**Zig automation gap:** no clippy-equivalent. Zig DPO pairs hand-curated
+ `zls` diagnostics only.

## §7 Tokens consolidated roll-up (proposal)

| §STRUCT stage     | original target | proposed revision   | basis                         |
| ----------------- | --------------- | ------------------- | ----------------------------- |
| pretrain-bias     | ~1T tok         | ~600B tok           | Stack v2 permissive subset (D-009 confirm) |
| domain-bias       | ~150B tok       | ~150B tok           | crates/npm/PyPI top-10k + hexa-native ×10 (unchanged) |
| build-trace       | ~20B tok        | ~20B tok            | unchanged                     |
| diff-edit         | ~30B tok        | ~30B tok            | + 5-NL filter                 |
| repair            | ~5B tok         | ~5B tok             | + linter autofix yield (2-5M pairs) |
| hexa-native       | ~2B tok         | ~2B tok             | + Tier D philosophy ×10      |
| **philosophy**    | ~3B tok         | **~500M-1B effective** | Tier A+B+C raw ×10 + synth 5-10× (D-017) |
| **db-native** (new) | —             | **~15B tok**        | T1 full + T2 quote + EXPLAIN traces (D-014/D-015) |
| **firmware-native** (new) | —       | **~10B tok**        | RTOS + SDK Apache-2/MIT (D-020) |
| **hexa-firmware** (new) | —         | **~3B tok**         | hexa boards + stdlib/{core,alloc,hal,embedded,mcu} ×10 (D-020) |

**Total target (post-revision):** ~835B tok — same order as original
(~1.2T), with redistribution toward domain depth.

---

## §8 hexa-lang exclusion list — patterns NOT to learn

> **Language kind (frame this first).** Per SPEC.md §2.1 + §5:
> - **PRIMARY = native-compiled.** `hexa run x.hexa` ≡ build + exec
>   via the `lex → parse → resolve → check → lower → mono → ssa →
>   optimize → regalloc → emit → link` pipeline. This is the canonical
>   form the model must teach by default.
> - **SECONDARY (for reference) = simple AST interpreter.** Opt-in via
>   `--interp` / `hexa repl`. ~200–500 LOC walker over the typed AST
>   under `compiler/eval/`. Reuses the full frontend. Not the old
>   `hexa_interp` — that 20k-LOC bootstrap interpreter retires after
>   stage 3 byte-equal fixed point.
>
> **Why this section exists.** `~/core/hexa-lang/SPEC.md` (root, 2026-05-10)
> is the authoritative spec. The older `doc/spec.md` (2026-04-20) and many
> interpreter-era patterns have been **rejected or superseded**. The
> model must learn the NEW pipeline (compiled-first + slim interp opt-in),
> not the OLD bootstrap-interpreter patterns. Source of truth:
> SPEC.md §0/§2/§5/§11/§16 explicit rejects. When SPEC.md changes,
> this list updates — do not bake it permanently into `docs/code-llm.md`.

### §8.1 Hard rejects (NEVER learn as positive patterns)

Patterns explicitly rejected in SPEC.md. Mine these as **anti-corpus
DPO negatives** if at all:

| Reject pattern                              | SPEC.md ref     | Reason for reject                                  |
| ------------------------------------------- | --------------- | -------------------------------------------------- |
| Tracing GC                                  | §11             | "permanent reject" — never adds GC                 |
| Ref-counting (atomic / non-atomic)          | §11             | cycle handling burden + atomic cost — also rejected |
| Z3 / CVC5 prover bindings                   | §10.1           | in-house prover only, zero external dep            |
| LLVM-based codegen                          | §2.4            | direct codegen pipeline (lex→…→emit→link)          |
| C-transpile as primary codegen              | §2.4            | `hexa_cc.c` is bootstrap artifact, NOT pattern     |
| Korean i18n compiler diagnostics            | §7              | "ENGLISH ONLY permanently fixed"                   |
| CLI flag to disable strict lint             | §8              | forbidden — only `@grace` per-site                 |
| Env-var override of strict lint             | §8              | forbidden                                          |
| Silent `@grace` (no warning, no consent)    | §8.1            | `@grace` always emits `HX9000` + needs `Acked-grace` |
| `read_atlas_at_runtime` (200 ms / call)     | §2.2 rejected   | replaced by static embed (1-2 MB rodata cost only) |
| `mtime_disk_cache` for atlas                | §2.2 rejected   | replaced by static embed                           |
| Interpreter-only mode for CI/LSP            | §2.1 rejected   | "too slow at 4.2 MB atlas size"                    |
| Interpreter-with-cache mode                 | §2.1 rejected   | "still per-process overhead, not zero"             |
| 20k-LOC standalone interpreter (Option A)   | §5 rejected     | replaced by D+B: build+exec / opt-in repl AST eval |
| JIT-first bootstrap (Option C)              | §5 rejected     | replaced by stage 0 hexa_interp                    |
| Multi-field enum variants                   | §6.3 deferred   | single-field + struct embed only (RFC-020)         |

### §8.2 Soft rejects (in-flight migration — learn NEW, not OLD)

These are not banned but are being migrated. **Learn the post-migration
form, not the pre-migration form.**

| Old (do not emulate)                          | New (emulate)                                              | SPEC.md ref |
| --------------------------------------------- | ---------------------------------------------------------- | ----------- |
| `hexa_interp` internals (2 GB OOM cap)        | `hexa cc` native compiler pipeline                          | §1, §5      |
| Old `doc/spec.md` (April 2026, 1082 lines)    | root `SPEC.md` (May 2026, 675 lines)                       | top of SPEC |
| Standalone hexa-rtsc / hexa-chip / etc. repos | `firmware/boards/{rtsc,chip,…}/` under hexa-lang           | §18         |
| Mixed host+embedded stdlib                    | Option C: `stdlib/{core,alloc,hal,embedded,mcu}` split     | §18         |
| Scattered `exec()` fork-storm (1403 sites)    | `compiler/intrinsics/intrinsics.hexa` named intrinsics (L1) | §16        |
| Per-call shell-out for `now_ns`/`mkdir_p`/etc | L1 intrinsic surface → L2 libc-FFI later → L3 raw syscall  | §16         |
| Rust impl of hexa-cern / hexa-antimatter      | hexa migration during Phase E                              | §18.1       |
| Host stdlib import from firmware target       | rejected by `--target=*-none-*` gate                       | §18.2       |
| Manual heap `free` in 1.x                     | arena only (1.x); borrow-check (2.x)                       | §11         |
| `HX8003` Warning                              | superseded by `HX8004` Error — being retired               | §9          |

### §8.3 Verb whitelist (DO learn — positive patterns)

The hexa idiom canon to teach (positive bias):

- **Annotations**: `@grace(HX[0-9]{4}, until=YYYY-MM-DD, reason="…")`,
  `@verify`, `@prove`, `@implements(L[<id>])`, `@discover(kind="L")`,
  `@law(...)`, `@units`
- **Error model**: `HX[CCCC]` codes by group (HX0xxx parse → HX9xxx codegen)
- **Compile pipeline**: `lex → parse → resolve → check → lower → mono → ssa → optimize → regalloc → emit → link`
- **Lint stages**: S0–S8 (compile-time fatal except S6/S7 opt-in)
- **Memory**: arena (function-local / request-scoped / rodata static const)
- **Linker**: `hexa_ld` first, system `ld`/`lld` fallback
- **Enums**: payload-free where possible; single-field payload via RFC-020
- **Diagnostics**: English-only, did-you-mean (Levenshtein over atlas + scope), fix-it, `hexa explain`
- **Output modes**: pretty / short / json / github
- **Atlas binding**: every L[*]-citing function must `@implements` or `@discover`
- **Firmware tree shape**: `firmware/boards/{rtsc,chip,cern,antimatter,space}/` + `firmware/bsp/` + `firmware/linker_scripts/*.ld`
- **Stdlib direction**: stdlib MAY depend on stdlib; compiler/ MAY depend on stdlib; **stdlib MUST NOT depend on compiler/**

### §8.4 Sourcing rule for `hexa-native` / `hexa-firmware` stages

When ingesting hexa-* repos for Tier D weight ×10:

1. Prefer **most recent** commits over old.
2. Filter out files under `legacy/`, `archive/`, `raw_archive_*`,
   `*.deprecated.*`.
3. Mine the AST for `@grace` markers — these signal "in-progress
   technical debt" and should be DPO-negative-tagged (the post-fix
   version is the positive).
4. `hexa_interp` source tree (`self/` upstream) is OK to learn for
   pipeline literacy but mark `compiler/` upstream as **canonical
   pattern source** (×10 weight inside hexa-native).
5. Pre-2026-05-10 `doc/spec.md` content → quote-only excerpts; do
   NOT bulk include.

### §8.5 Refresh cadence

This §8 mirrors SPEC.md's reject/migrate decisions. **When SPEC.md
ships a new "Decision YYYY-MM-DD" block, re-audit this section.**
Per-decision deltas land in [`plan-decisions-pending.md`](plan-decisions-pending.md)
as `D-NNN` rows tagged `hexa-lang-spec`.

---

## §9 Frontend / web-app coverage

> **Why a dedicated section.** §3 (databases) covers the *backend*
> data plane; the model also needs to write **frontend** code — the
> UI plane. Per user steer (2026-05-11), align with **latest design
> philosophy** (2025-2026 canon), not 2010-era jQuery/Bootstrap tropes.

> **Sourcing status: WEB RESEARCH IN FLIGHT (3 parallel agents).**
> Concrete source list and license verdicts land in:
> - [`frontend-f1-findings.md`](frontend-f1-findings.md) — frameworks + design systems + state mgmt + type safety
> - [`frontend-f2-findings.md`](frontend-f2-findings.md) — CSS + native web platform + build tooling
> - [`frontend-f3-findings.md`](frontend-f3-findings.md) — perf + a11y + AI-native UI + mobile + testing
>
> This section pins the **shape** of the coverage (what to teach × what
> to avoid). Fill in source-specific cells from the F-1/F-2/F-3 reports
> when they land.

### §9.1 Coverage axes (the shape — post F-1/F-2/F-3 consolidation)

> Verified sources per row from `frontend-f1-findings.md` (frameworks/
> design/state), `frontend-f2-findings.md` (CSS/web platform),
> `frontend-f3-findings.md` (perf/a11y/AI-UI). Token estimates ~5M
> total across the canonical frontend corpus.

| axis                          | what to teach (2026 canon)                                                                                                                                                                                                                                                                                                                                                                                                       | what to deprecate (do NOT teach as positive)                                                                                                                                                                  | source                                |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **component frameworks**      | **React 19.2 + Compiler 1.0 stable (2025-10-07)** (no manual `useMemo`/`useCallback`/`forwardRef`); **Vue 3.6 Composition + `<script setup>`** (Vapor Mode beta.9 2026-04 — not yet stable); **Svelte 5 runes** (`$state`/`$derived`/`$effect`, reactive class in `.svelte.ts` replacing stores); **Angular 21 zoneless-by-default** + signals stable since v20 + `@if`/`@for`/`@defer` control flow + Signal Forms; Solid fine-grained reactivity; Astro Islands; Qwik resumability | class components, Options API (Vue), Svelte 4 stores, Angular Modules-everywhere, `forwardRef`, manual memoisation hooks under React 19+, jQuery, AngularJS                                                | F-1                                   |
| **meta-frameworks**           | **Next.js App Router** (RSC + Server Actions + ref-as-prop default); **Nuxt 4**; **SvelteKit**; **Astro 5** (server islands, content collections); **TanStack Start v1**; **React Router 7** (Remix merge result)                                                                                                                                                                                                                | Pages Router as new code, CRA / Create-React-App, Gatsby for new greenfield                                                                                                                                  | F-1                                   |
| **state management**          | **TanStack Query** (server state) + **Zustand** (client UI) + **React Hook Form** + **nuqs** (URL); TC39 **Signals proposal at Stage 1** (cross-framework primitive — Solid/Vue/Svelte/Angular/Preact; React opts for Compiler instead)                                                                                                                                                                                          | Redux Toolkit as new-greenfield default (enterprise-legacy OK), mapStateToProps, large global stores by default, prop-drilling beyond 2 levels                                                                | F-1                                   |
| **forms + validation**        | **React Hook Form** / **TanStack Form**; **Zod** default + **Valibot** for bundle size + **ArkType** for perf                                                                                                                                                                                                                                                                                                                    | Formik (legacy), uncontrolled inputs w/o ref                                                                                                                                                                  | F-1                                   |
| **design systems**            | **shadcn/ui paradigm** (copy-paste primitives — supports Radix + **Base UI** as of 2026-02); Radix UI / Ark UI / React Aria headless primitives; **Material Design 3 (Material You)**; **Apple HIG ref-only** (proprietary)                                                                                                                                                                                                       | wholesale MUI / Ant Design import w/o tree-shake; importing entire icon libs; vendor-tied dark patterns                                                                                                       | F-1                                   |
| **styling**                   | **Tailwind v4 (Jan 2025 GA)** — Rust **Oxide** engine, **CSS-first `@theme` config** (no `tailwind.config.js`), OKLCH default palette, container queries built-in; **CSS Cascade Layers (`@layer`)**; **`@property`** typed custom properties; zero-runtime CSS-in-JS via vanilla-extract / Panda CSS / CVA / Pigment CSS                                                                                                          | Tailwind v3 JS config as new code; runtime CSS-in-JS heavy emotion/styled-components; deep `!important` chains; `tailwind.config.js` in new projects                                                          | F-1                                   |
| **CSS layout & visual**       | Container Queries (`@container`, `cqi/cqw`), `:has()`, Logical Properties, **View Transitions API** (`document.startViewTransition`), **Popover API** (`popover`, `popovertarget`), `<dialog>` + `inert`, **Anchor Positioning** (2026 Baseline — collapses Floating UI / Popper.js); OKLCH + `light-dark()` + `color-mix()` + Relative Color Syntax; `:focus-visible`; **`@starting-style`**, **`interpolate-size`**, `::details-content`, Invoker Commands ★; **subgrid**; scroll-driven animations (Chrome 145+) | media queries when Container Queries fit; modal libs over `<dialog>`; HSL when OKLCH fits; JS focus-trap libs over `inert`; floats for layout; `position:absolute` for centering pre-flexbox                  | F-2                                   |
| **build tooling**             | **Vite 5/6** dominance + **rolldown** (Vite's Rust-based future); **Bun** runtime + bundler + test; **Turbopack** (Next.js); **Rspack** (Webpack Rust rewrite); **swc** / **esbuild** for transforms; **Oxc** ★ (production-scale UNVERIFIED)                                                                                                                                                                                     | Webpack as new-greenfield default; gulp/grunt; Babel where swc/esbuild suffice; CRA                                                                                                                            | F-2                                   |
| **type safety**               | TS-first; Bun + Deno 2 + Node 22+ `--experimental-strip-types`; `tsc --noEmit` + **`tsgo`** (TypeScript 7 / Project Corsa — **Go-based** (not Rust), ~10× perf, Beta 2026-04-21, stable mid-2026); **`moduleResolution: "bundler"`** is the 2026 tsconfig consensus; Zod / Valibot / ArkType end-to-end via tRPC / Server Actions / Hono RPC                                                                                       | `any`-typed boundaries; runtime cast-without-validate; `ts-node` / `tsx` when Node 22+ strips natively; `moduleResolution: node`/`node16` for Vite/Bun projects; `tsc → node dist/` build for app code        | F-1 / F-2                             |
| **performance**               | Core Web Vitals: **LCP / INP (replaced FID 2024-03-12) / CLS**; `fetchpriority`, `loading=lazy`, `decoding=async`, `srcset`/`sizes`, AVIF/WebP (with fallback); resource hints (`preconnect`/`preload`/`modulepreload`/`prefetch`) — note font crossorigin trap; **Speculation Rules API** (replaces `<link rel=prefetch>` for navigation); `scheduler.yield()` + Long Animation Frames API; bundle budgets 100 KB / 170 KB tier; **PPR + RSC streaming** | FID metric in any post-2024-03 doc; `<link rel=prefetch>` for navigation when Speculation Rules fits; sync `<script>` blocking; unbatched fetch waterfalls                                                    | F-3                                   |
| **a11y**                      | **WCAG 2.2** (legal floor — ADA / Section 508 / EAA); 9 new SCs over 2.1 (target size 24×24, dragging movements, focus appearance, consistent help, redundant entry, accessible authentication, focus not obscured ×2); **WCAG 3.0 Mar 2026 Draft** (do NOT use for compliance yet); 5 Rules of ARIA; **`<dialog>` + `inert`** retires manual focus traps; `:focus-visible`; `prefers-reduced-motion` / `prefers-contrast`; **APCA vs WCAG 2 contrast**; roving tabindex / `aria-activedescendant`; WebAIM screen-reader market shares as test-priority signal; "good a11y = good agent-ability" — agents read the accessibility tree | "no ARIA is better than bad ARIA" — refuse decorative ARIA; `tabindex > 0`; image without `alt`; ARIA on `<button>` (semantic already covers it); WCAG 2.1 as compliance bar (superseded by 2.2)              | F-3                                   |
| **i18n**                      | Intl API, **ICU MessageFormat** (shape UNVERIFIED for `Intl.MessageFormat`), `lang` + `dir` BiDi, Logical Properties throughout                                                                                                                                                                                                                                                                                                  | string concat for plurals; `margin-left`/`right` over `inline-start`/`end`; ad-hoc translation lookup w/o ICU                                                                                                  | F-3                                   |
| **AI-native UI**              | streaming token render + **AbortController** + **AbortSignal.any** for composition; **Vercel AI SDK** (Apache-2) + **AI Elements** patterns; tool-call state machine + citations + code-diff previews; **generative UI** via RSC; chat message virtualization; **DOMPurify** for streaming-markdown safety; **agent-friendly DOM = accessibility tree** (no separate spec yet — leverage a11y); local model stack: **Transformers.js** / **ONNX Web** / **Web LLM** / **WebNN** (final flag-off date UNVERIFIED) | rendering raw model output without sanitisation; `dangerouslySetInnerHTML(modelOutput)`; blocking UI on full completion; no abort path                                                                         | F-3                                   |
| **mobile + cross-platform**   | **React Native New Architecture** (Fabric + TurboModules **default**); **Expo SDK 55**; **Capacitor** (over Cordova); **Tauri 2** desktop+mobile (Rust-backed; mobile has caveats per F-3); Flutter (still strong share — Dart-specific, T2 quote-only); PWA 2026 capabilities matrix (incl. EU-DMA standalone removal context)                                                                                                   | Cordova as new code; old RN bridge; Electron when Tauri fits (desktop)                                                                                                                                         | F-3                                   |
| **testing**                   | **Playwright** dominance (E2E + component); **Vitest** > Jest for new code; **Testing Library** `getByRole` first principle; **Storybook 9** interaction testing (or **Ladle** for fast React-only); **@axe-core/playwright** + jest-axe; Chromatic / Percy / Playwright snapshots for visual                                                                                                                                       | Cypress over Playwright for new code; mocking keyboard events over real `keyboard()` input; querying by `data-testid` first (use role first)                                                                  | F-3                                   |
| **auth**                      | **WebAuthn / Passkeys** (passwords-replacement); OAuth 2.1 + PKCE; magic links; session-based with HttpOnly + Secure cookies; **WebAuthn.me** as reference                                                                                                                                                                                                                                                                        | passwords-only auth; `localStorage` for tokens; JWT in cookies w/o Secure; third-party-cookie SSO patterns                                                                                                     | F-2                                   |
| **storage / offline**         | **IndexedDB via Dexie** / idb-keyval; **local-first** (Replicache / Yjs / Automerge); Service Workers + Background Fetch; **Storage Buckets** (Chromium-experimental UNVERIFIED)                                                                                                                                                                                                                                                  | `localStorage` for > 1 MB; offline-as-afterthought; non-versioned migrations on IndexedDB                                                                                                                       | F-2                                   |
| **realtime**                  | **WebSockets** still canonical for general realtime; **WebTransport** for low-latency gaming / media (NOT a WebSocket replacement); **Streams API** for SSR + AI streaming                                                                                                                                                                                                                                                       | polling when push fits; WebTransport as default new-realtime (mis-positioned)                                                                                                                                  | F-2                                   |
| **graphics**                  | **WebGPU full cross-browser Jan 2026** (Firefox 147 + Safari 26) — ~70% global, **WebGL2 fallback still required**; Three.js (MIT) / Babylon.js (Apache-2)                                                                                                                                                                                                                                                                        | WebGL2 as primary for new greenfield where WebGPU fits + fallback OK                                                                                                                                           | F-2                                   |
| **layout future-canon (not yet Baseline)** | **Masonry** via `display: grid-lanes` (WG settled late 2025, shipping); `field-sizing: content` (Chromium-only mid-2025, progressive enhancement only)                                                                                                                                                                                                                                                                          | Polyfilling Masonry with brittle JS instead of progressive enhancement                                                                                                                                         | F-2                                   |

### §9.2 Token budget (per F-1/F-2/F-3)

| tier | volume estimate | basis                                                          |
| ---- | --------------- | -------------------------------------------------------------- |
| F-1  | ~4-5M tok       | ~35 sources, ~Apple HIG ref-only excluded                      |
| F-2  | ~25-40k tok     | report-derivable training shard                                |
| F-3  | ~5.5K tok       | report itself; canonical sources MDN/W3C/web.dev (CC-BY-SA)    |
| **Frontend total raw** | **~5M tok** | within philosophy stage 10× weighting → ~50M effective |

### §9.3 License gate (consolidated)

| issue                         | source     | action                                                          |
| ----------------------------- | ---------- | --------------------------------------------------------------- |
| **Apple HIG**                 | F-1        | **hard blocker — reference only**, no bulk include              |
| **Deque (axe) proprietary docs** | F-3     | reference only; use axe-core source (MPL-2) for examples         |
| **Vendor-blog paraphrase**    | F-3        | paraphrase required (no bulk re-publish); attribution mandatory  |
| MDN / web.dev / W3C drafts    | F-2 / F-3  | CC-BY-SA — full include with attribution                         |
| All major frameworks (React/Vue/Svelte/Angular/Solid/Astro/Qwik/Tailwind/shadcn/Radix/TanStack/Vite/Bun/Playwright/Vitest/Storybook) | F-1 / F-2 / F-3 | MIT or Apache-2 — full include |

### §9.2 Stage placement (proposed)

Frontend lives in **existing stages with filter expansion**, not a new
top-level stage — unlike DB or firmware, frontend code IS just
TypeScript / JS + CSS + HTML, already in scope:

| existing stage | frontend addition                                                     |
| -------------- | --------------------------------------------------------------------- |
| domain-bias    | npm top-10k now explicitly includes meta-frameworks (Next/Nuxt/SvelteKit/Astro), Vite ecosystem, Tailwind, shadcn registry |
| build-trace    | add `vite build`, `next build`, `bun build`, `playwright test` traces |
| diff-edit      | PR diffs filtered to high-signal repos (Next.js, Vite, Svelte, Astro, shadcn, Radix, TanStack) |
| repair         | failing component test → fix (Vitest + Testing Library), Playwright flakes → stabilize, a11y violation → fix (axe) |
| philosophy     | frontend canon — shadcn paradigm, "no ARIA is better than bad ARIA", Tailwind v4 OKLCH rationale, RSC tradeoffs |

### §9.3 §EVOLVE — frontend benchmarks (proposed)

| benchmark              | what it measures                            | acceptance bar (TBD)             |
| ---------------------- | ------------------------------------------- | -------------------------------- |
| component-synthesis    | spec → React/Svelte/Vue component           | passes Vitest + Testing Library  |
| a11y-fix               | given `axe-core` violation, produce fix     | violation resolved + no regression |
| CSS-modernize          | given CSS-2-era code, modernize             | uses container queries / `:has()` where appropriate; OKLCH where color-mix fits |
| RSC-vs-client decision | given component spec, pick `'use server'` vs `'use client'` correctly | 80% agreement with reference |
| bundle-fit             | given perf budget, code splits to fit       | meets target JS/CSS bytes        |
| AI-UI patterns         | streaming completion, tool-call render, abort | meets idiomatic shadcn/AI-SDK form |

### §9.4 §VERIFY — frontend tool additions (proposed)

Add to current `read_file, apply_patch, run_build, run_test, lsp_query, run_size, read_map, read_disasm, read_register, run_query, explain_query, apply_migration, read_schema`:

- `run_dev` — start Vite/Next/Bun dev server, capture HMR + first paint
- `read_console` — browser console (Playwright-driven)
- `a11y_check` — axe-core scan in headless browser
- `bundle_analyze` — vite-bundle-visualizer / `next-bundle-analyzer` output
- `lighthouse` — Core Web Vitals + a11y + perf score
- `visual_diff` — Playwright / Chromatic snapshot compare

### §9.5 §VERIFY — frontend style contract (proposed addition)

Adds to existing native-first / canon-first:

- **2026-canon-first**: pick `<dialog>` over modal libs, Popover API
  over `position: absolute` hacks, container queries over media
  queries when scope is component-local, OKLCH over HSL when designing
  new tokens, `:focus-visible` not `:focus`.
- **a11y-by-default**: generated UI passes axe-core with zero violations;
  semantic HTML first, ARIA only when semantic HTML insufficient.
- **streaming-aware**: AI-facing components render incrementally,
  support `AbortSignal`, never block on full completion.

### §9.6 Open items (rolled to decisions)

See `plan-decisions-pending.md`:

- **D-024**: Frontend stage placement — confirm "filter expansion" model
  (no new top-level stage) vs dedicated `frontend-native` stage.
- **D-025**: Frontend design-philosophy corpus sourcing — pending
  Tier F-1/F-2/F-3 web research output (3 agents in flight).
- **D-026**: Mobile / cross-platform inclusion — RN + Expo + Tauri yes;
  Flutter (Dart) yes/no/quote-only?
- **D-027**: AI-native UI corpus — Vercel AI SDK + AI Elements vs
  building from primitives. License posture per source.
- **D-028**: Frontend benchmarks — which 2-3 from §9.3 ship in v0.1.x
  vs deferred to v0.2.0.

---

## Cross-link

- Active decisions: [`plan-decisions-pending.md`](plan-decisions-pending.md)
- Sequencing: [`plan-execution-roadmap.md`](plan-execution-roadmap.md)
- Recipe spec being fed: [`../docs/code-llm.md`](../docs/code-llm.md)
- hexa-lang SSOT: [`../../hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md)
- hexa-codex sister specs (live): see `docs/code-llm.md` Cross-link policy
