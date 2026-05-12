# plan — execution roadmap (v0.1.x → v1.0.0)

> **Phase-by-phase sequencing for the `code` verb.** Anchored on
> decision gates from [`plan-decisions-pending.md`](plan-decisions-pending.md)
> and surface coverage from [`plan-domain-coverage.md`](plan-domain-coverage.md).
> Every phase exits on a measurable bar.

| field         | value                                    |
| ------------- | ---------------------------------------- |
| status        | `LIVE`                                   |
| current phase | **v0.1.0 → v0.1.1** (spec consolidation) |
| status flag   | `RESEARCH_FIRST` — no GPU yet            |
| last updated  | 2026-05-11                               |

---

## §0 Status snapshot

| Aspect                | State                                                |
| --------------------- | ---------------------------------------------------- |
| recipe spec           | `docs/code-llm.md` — ~150 lines, partial deltas      |
| philosophy sources    | `papers/coding-philosophy-sources.md` — pre-research draft |
| web research          | 4/4 tier reports landed (A/B/C/E)                     |
| pending spec deltas   | 5 batched items (D-018..D-022 — see decisions)       |
| pending decisions     | 12 open (3 critical-path)                            |
| code (verb tooling)   | `cli/hexa-forge.hexa` selftest only                  |
| weights / training    | 0/2 (RESEARCH_FIRST)                                 |
| corpus on disk        | 0 (no fetch yet)                                     |

---

## §1 Decision gates

Two gates dominate the v0.1.x phase:

**Gate G-CONSOLIDATE** — close domain coverage decisions, batch-apply
spec edits.
- inputs: D-014 (DB tier), D-015 (DB placement), D-017 (token target),
  D-018 (license downgrades), D-019 (URL fixes), D-020 (C+firmware),
  D-021 (hexa-fidelity), D-022 (5 NL), D-023 (NL diag carve-out)
- output: M-001 batch edit lands on `docs/code-llm.md`; M-002 patch
  lands on `papers/coding-philosophy-sources.md`
- exit: spec read-through is internally consistent + all tier findings
  reflected

**Gate G-BASE** — pick base weights + tokenizer + serving format.
- inputs: D-007 (base), D-008 (tokenizer), D-009 (license confirm),
  D-010 (eval lineage), D-011 (serving format)
- output: §REQUIRES + §FLOW + §VERIFY frozen for SFT
- exit: ready to enter v0.2.0 infrastructure phase

Gates are sequential — `G-CONSOLIDATE` first (cheap, paper-only),
`G-BASE` next (needs sampling experiments).

---

## §2 v0.1.1 — spec consolidation (current)

> Goal: every accumulated decision shows up in `docs/code-llm.md`. No
> new research. No corpus fetch yet. Tightening only.

### Tasks

1. **Apply 5-NL §WHY block (D-022)** — add line under core langs:
   `code-adjacent natural language: English (T0), Korean / Chinese / Russian / Japanese (T1)`.
2. **Apply NL diagnostic carve-out (D-023)** — refusal contract line
   notes English-only for diagnostics per hexa-lang SPEC §7.
3. **Apply C + firmware (D-020)** —
   - §WHY: add "systems & firmware" + "hardware reference literacy" lines
   - §STRUCT: add 2 rows (`firmware-native`, `hexa-firmware`)
   - §EVOLVE: add 4 bench rows (MCU-bench, linker-script literacy,
     memory-fit, hexa target gate)
   - §VERIFY: add 4 tools (`run_size`, `read_map`, `read_disasm`,
     `read_register`)
4. **Apply hexa-fidelity contract (D-021)** — §VERIFY new bullet
   enumerating S0–S8 lint, `HX[CCCC]` codes, `@grace` 3-field, arena
   memory model, Z3/CVC5 ban, host-stdlib gate for `*-none-*` targets.
5. **Apply DB tier scope (D-014 + D-015)** —
   - §WHY: add "databases & query engines" line
   - §STRUCT: add `db-native` row (T1 full + T2 quote)
   - §EVOLVE: add Spider/BIRD + EXPLAIN literacy + schema design rows
   - §VERIFY: add 4 tools (`run_query`, `explain_query`,
     `apply_migration`, `read_schema`)
6. **Re-state §STRUCT philosophy tokens (D-017)** — replace `~3B tok`
   with `~500M-1B effective (raw ~30M + ×10 weight + ×5-10 synth)`.
   Note the synth requirement explicitly.
7. **Patch `papers/coding-philosophy-sources.md` (M-002)** — apply
   D-018 license downgrades + D-019 URL fixes; cross-link to
   tier-*-findings.md as the live detail layer.
8. **Update TODO §1** — add "v0.1.1 consolidation" checklist; remove
   per-verb open-Qs from TODO since they live in the decision ledger
   now.

### Exit bar

- [ ] `docs/code-llm.md` re-read end-to-end is internally consistent
- [ ] every D-NNN in `plan-decisions-pending.md` §3 maps to a paragraph
      in the recipe OR an entry in the ledger (no orphan decisions)
- [ ] `papers/coding-philosophy-sources.md` Tier A §1 reflects
      tier-a-findings corrections (Zig zen removed, ANSI SQL row removed,
      CERT C promoted, Google Style added)
- [ ] all CC-BY / PSF / PostgreSQL attribution requirements logged for
      the license-clean CI gate

### Out of scope

corpus fetch · base model selection · training stage execution

### Estimate

paper-only, single session. **No GPU.**

---

## §3 v0.1.2 — corpus audit + sampling

> Goal: turn license claims into verified facts on disk. Sample 1-5%
> of each tier, hash + license-tag, measure real token counts.

### Tasks

1. **License-clean CI prototype** — small Python tool that scans a
   directory + verifies LICENSE/SPDX header against the allowlist.
   Fails on GPL/AGPL/SSPL/NC. Hook into a sample fetch.
2. **Sampling pipeline** —
   - 5% sample of Stack v2 permissive subset (D-009)
   - 100% fetch of small Tier A/B/C sources (PEPs, Rust Book, etc.)
   - canon `~/core/hexa-*` repo enumerate + token count (Tier D)
3. **Real tokens** — feed sample through candidate tokenizer (Qwen
   default). Record per-source token counts → revise
   `plan-domain-coverage.md §7`.
4. **License gate alarms** — flag any cell whose claimed license fails
   the scanner. Resolve before corpus expansion.
5. **Stack Exchange policy resolution (D-016)** — decide pre-2024-07
   Academic Torrents mirror vs full exclusion; record verdict.

### Exit bar

- [ ] real token counts in `plan-domain-coverage.md §7` (replace
      estimates)
- [ ] license-clean CI passes on the sampled corpus
- [ ] D-009 (Stack v2 perm subset) confirmed with measured volume
- [ ] D-016 (Stack Exchange) resolved

### Out of scope

base model selection · training · full corpus fetch (sample only)

### Estimate

paper + light scripting. CPU + ~100 GB disk for samples. **No GPU.**

---

## §4 v0.1.3 — base model + tokenizer + serving (G-BASE)

> Goal: close the 5 critical-path open Qs. After this, no recipe
> ambiguity remains for SFT planning.

### Tasks

1. **D-007 base weights** — benchmark Qwen2.5-Coder-7B vs
   DeepSeek-Coder-V2-Lite vs StarCoder2-15B on:
   - hexa-eval cold (zero hexa training)
   - 5-NL multilingual code comprehension
   - firmware target literacy (Cortex-M / RISC-V / ESP32)
   - DB query understanding (SQL + Cypher + Redis cmd)
   - 7B Q5/Q6 fit on M4 Mini 16GB (hardware tier check)

   **Expected winner:** Qwen2.5-Coder-7B (strongest CJK + multilingual
   + sized for M4 Mini target).

2. **D-008 tokenizer policy** — for chosen base, decide:
   - extend BPE with hexa keywords (likely)
   - extend BPE with `@grace/@verify/@implements/L[*]/HX[CCCC]` tokens
   - retain base multilingual coverage (5 NL)
3. **D-011 serving format** — sequence: GGUF first (broadest llama.cpp /
   Ollama / LM Studio reach) → MLX for M-series laptops → vLLM for
   server. Document conversion path.
4. **D-010 eval lineage storage** — DuckDB recommended (cross-pattern
   with hexa-codex sister); decide.
5. **D-013 DPO scoring (preview)** — sketch tree-sitter rule pack v1
   for "idiomatic vs translated" detection; defer full impl to v0.2.0.

### Exit bar

- [ ] Recipe `Open questions (v0.1.0)` section in `docs/code-llm.md`
      reduced to zero items (or moved to v0.2.0 open Qs)
- [ ] Base weights decision recorded with measured numbers in §4 ledger
- [ ] Tokenizer manifest skeleton drafted (extension list, not yet
      trained)

### Out of scope

training run (SFT) · full DPO pipeline impl · synth corpus generation

### Estimate

eval-only, requires running 3 base models locally for comparison.
**Single H100 or M4 Pro/Studio sufficient for eval. No training.**

---

## §5 v0.2.0 — cross-cutting infrastructure

> Existing TODO §2 — now informed by v0.1.x decisions. Mostly engineering,
> not research.

| infra                                   | notes                                                     |
| --------------------------------------- | --------------------------------------------------------- |
| dataset registry (`datasets.toml`)      | (verb, stage, corpus) keyed; checksum + license tag; attribution metadata required (CC-BY / PSF / PostgreSQL) |
| tokenizer registry                      | per D-008; base + per-verb extensions versioned together  |
| eval lineage (DuckDB per D-010)         | store (model SHA, eval set SHA, config, result). Cross-pattern with hexa-codex |
| serving handoff                         | per D-011; GGUF first, MLX next; documented conversion CLI |
| license-clean CI gate                   | scanner from v0.1.2 promoted to required check; attribution validator added |
| synth pipeline                          | principle × idiom + linter-autofix pair generator (~5-10× expansion of Tier A/B sources) |
| DPO data pipeline                       | linter-driven (clippy/ruff/golangci) + optional CodeReviewer / SE pairs (D-016 outcome) |
| anti-corpus filter                      | pollution exclusion enforcer (medium/dev.to/hashnode post-2023, geeksforgeeks/quora/blogspot all) |

### Exit bar

- [ ] all 8 infra components have a working CLI surface
- [ ] one verb (code) runs an end-to-end synthetic SFT pass through the
      pipeline (small subset, no model quality bar yet)

### Estimate

multi-session engineering work. CI + storage budgets relevant. **No
training compute yet.**

---

## §6 v1.0.0 — first weights gate

> Existing TODO §4 unchanged in spirit; gating bars updated with v0.1.x
> findings.

| Gate                                       | Bar                                              |
| ------------------------------------------ | ------------------------------------------------ |
| license audit                              | zero GPL/AGPL/NC/SSPL in pretrain mix (CI green) |
| HumanEval+                                 | ≥ DeepSeek-Coder-V2-7B                           |
| hexa-eval                                  | ≥ 80% pass                                       |
| **5-NL eval**                              | ≥ 70% pass cross-lang (EN/KR/CN/RU/JA)           |
| **DB-eval** (Spider/BIRD + EXPLAIN + DDL)  | ≥ 60% pass                                       |
| **firmware-eval** (MCU-bench + linker)     | ≥ 50% pass on Cortex-M target                    |
| **frontend-eval** (component + a11y + RSC) | ≥ 65% pass (axe 0 violations)                    |
| safety eval                                | off-domain refusal ≥ 95% (5-NL × adversarial matrix) |
| hexa-fidelity contract                     | 100% generated hexa code passes S0–S8 lint       |
| handoff                                    | `hexa-codex serve` E2E accepted                  |
| reproducibility                            | pretrain → SFT → DPO on 1× H100 box in ≤ 14 days |
| hardware tier                              | 7B Q5/Q6 GGUF runs on M4 Mini 16GB (inline use)  |
| **hexa-codex upstream contribution**       | ≥ **5 PRs landed** in hexa-codex from forge findings; T4 empirical floor delivered for ≥ 2 F-CODEX-N falsifiers (F-CODEX-1 + F-CODEX-2 default targets — measurement window overlaps SFT/inference dev) |

### Out of scope

multimodal · prose chat · 14B target (laptop bar is 7B)

### Estimate

requires real training compute. Pre-flight all infra. **8× H100 for SFT
window per §REQUIRES.**

---

## §7 Critical path

```
v0.1.1 spec consolidation
   ↓ (G-CONSOLIDATE: 9 decisions, paper-only)
v0.1.2 corpus audit + sampling
   ↓ (D-009 confirmed, D-016 resolved, real tokens measured)
v0.1.3 base model + tokenizer + serving
   ↓ (G-BASE: 5 decisions, eval-only)
v0.2.0 infrastructure
   ↓ (8 infra components, engineering, no training)
v1.0.0 first weights
       (training compute, 11-gate acceptance)
```

The earliest training compute is required at v1.0.0. v0.1.x and v0.2.0
are paper / sampling / infra — survivable on a laptop + sample storage.

---

## §8 What's deliberately deferred

| item                                  | deferred to | reason                                                 |
| ------------------------------------- | ----------- | ------------------------------------------------------ |
| 14B target weights                    | v1.1.0+     | M4 Mini 16GB tier is 7B; 14B serves M4 Pro 24GB+       |
| Tier C T3-DB (Timescale/InfluxDB/etc) | v0.2.0      | smaller signal; revisit when ≥3 forge verbs exist      |
| Z3 / CVC5 integration                 | NEVER       | hexa-lang SPEC §10.1 — in-house prover only            |
| Tracing GC support codegen           | NEVER       | hexa-lang SPEC §11 — permanent reject                  |
| LLM-judge synth                       | NEVER       | Shumailov 2024 model-collapse risk                    |
| Anti-corpus from medium/dev.to post-2023 | NEVER    | LLM-slop pollution                                     |
| Korean compiler diagnostics           | NEVER       | hexa-lang SPEC §7 — Korean i18n permanently closed     |

---

## Cross-link

- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
- Coverage matrix: [`plan-domain-coverage.md`](plan-domain-coverage.md)
- Tier findings: [`tier-a-findings.md`](tier-a-findings.md) ·
  [`tier-b-findings.md`](tier-b-findings.md) ·
  [`tier-c-findings.md`](tier-c-findings.md) ·
  [`tier-e-findings.md`](tier-e-findings.md)
- Recipe spec: [`../docs/code-llm.md`](../docs/code-llm.md)
- Existing TODO buckets: [`../TODO.md`](../TODO.md) — superseded for v0.1.x by this roadmap
- hexa-codex sister specs: see [`../docs/code-llm.md` Cross-link policy](../docs/code-llm.md#cross-link-policy)
