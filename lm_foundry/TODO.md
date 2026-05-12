# TODO — hexa-forge

`v0.1.0` ships as a 2-verb RESEARCH_FIRST bundle (see
[README.md](README.md#verbs)). This TODO rolls up cross-cutting work
beyond the per-verb open questions in `docs/<verb>.md`.

---

## §1 v0.1.x — recipe sharpening

**Living roadmap:** [`ROADMAP.md`](ROADMAP.md) (latest spec at top,
append-only `§CHANGELOG` at bottom).

The `code` verb planning surface lives under [`papers/`](papers/):

### Decision + coverage + sequencing

- [`papers/plan-decisions-pending.md`](papers/plan-decisions-pending.md) —
  live decision ledger (D-NNN rows + 37 D-NEW-* prefixed in D-032..D-068)
- [`papers/plan-domain-coverage.md`](papers/plan-domain-coverage.md) —
  surface area matrix (langs × NL × DB × firmware × frontend × DPO)
- [`papers/plan-execution-roadmap.md`](papers/plan-execution-roadmap.md) —
  phased v0.1.x → v1.0.0 with exit bars
- [`papers/plan-multilingual-stage.md`](papers/plan-multilingual-stage.md) —
  NL-tag schema + 5-NL rebalance algorithm
- [`papers/plan-feedback-channel-ops.md`](papers/plan-feedback-channel-ops.md) —
  forge → hexa-codex PR routing + template + automation triggers
- [`papers/hexa-codex-techniques-applied.md`](papers/hexa-codex-techniques-applied.md) —
  63 techniques mined from 5 hexa-codex verb specs → forge surface mapping

### v1.0.0 acceptance gate bench specs (6 — gates ③④⑤⑥⑦⑧)

- [`papers/spec-hexa-eval.md`](papers/spec-hexa-eval.md) — gate ③ (750 tasks)
- [`papers/spec-five-nl-eval.md`](papers/spec-five-nl-eval.md) — gate ④ (1000)
- [`papers/spec-db-eval.md`](papers/spec-db-eval.md) — gate ⑤ (750)
- [`papers/spec-firmware-eval.md`](papers/spec-firmware-eval.md) — gate ⑥ (600)
- [`papers/spec-frontend-eval.md`](papers/spec-frontend-eval.md) — gate ⑦ (520)
- [`papers/spec-safety-eval.md`](papers/spec-safety-eval.md) — gate ⑧ (800)
- [`papers/spec-treesitter-rule-pack.md`](papers/spec-treesitter-rule-pack.md) — D-013 default

### Web-research findings (philosophy + frontend source pools)

- [`papers/tier-a-findings.md`](papers/tier-a-findings.md) — language-native idiom canon
- [`papers/tier-b-findings.md`](papers/tier-b-findings.md) — cross-lang principles
- [`papers/tier-c-findings.md`](papers/tier-c-findings.md) — post-mortem canon
- [`papers/tier-e-findings.md`](papers/tier-e-findings.md) — anti-corpus DPO negatives
- [`papers/frontend-f1-findings.md`](papers/frontend-f1-findings.md) — frameworks/state
- [`papers/frontend-f2-findings.md`](papers/frontend-f2-findings.md) — CSS/web platform
- [`papers/frontend-f3-findings.md`](papers/frontend-f3-findings.md) — perf/a11y/AI-UI
- [`papers/datasets-source-manifest.md`](papers/datasets-source-manifest.md) — 182-row consolidated source rollup
- [`papers/coding-philosophy-sources.md`](papers/coding-philosophy-sources.md) —
  pre-research draft (superseded by tier-* + frontend-f* findings)

### v0.1.2 tooling (paper-layer, all self-test PASS)

- [`tool/license_clean_scan.py`](tool/license_clean_scan.py) — SPDX scanner
- [`tool/stack_v2_sample.py`](tool/stack_v2_sample.py) — Stack v2 permissive 5% sampler
- [`tool/emit_t4.py`](tool/emit_t4.py) — forge → hexa-codex PR drafter (11 verbs)
- [`tool/_common.py`](tool/_common.py) — shared schema-lock + atomic manifest mutation
- [`tool/fetch_sources.py`](tool/fetch_sources.py) — license-respecting fetcher
- [`tool/tokenize.py`](tool/tokenize.py) — Qwen-tokenizer real-tokens populator
- [`tool/tokenizer_extension.toml`](tool/tokenizer_extension.toml) — D-008 hexa BPE manifest (207 tokens)
- [`tool/extend_tokenizer.py`](tool/extend_tokenizer.py) — manifest consumer
- [`tool/treesitter_rule_pack/`](tool/treesitter_rule_pack/) — 50 rules × 5 langs (D-013)
- [`datasets.toml`](datasets.toml) — 173-entry dataset registry
- [`outbox/hexa-codex/`](outbox/hexa-codex/) — 11 verb subdirs, write-once PR staging

The `bio` verb still has per-doc open Qs at the bottom of
[`docs/bio-llm.md`](docs/bio-llm.md#open-questions-v010) — base weights,
k-mer tokenization, safety stack layering, DUA management, paired-call
schema, IRB. Mirror to a `papers/plan-decisions-bio-pending.md` when
work resumes on that verb.

---

## §2 v0.2.0 — cross-cutting infrastructure

Shared across all forge verbs once we have ≥ 3. **Status updated 2026-05-11**
to reflect v0.1.2 paper-layer deliverables that partially satisfy these.

- [x] **dataset registry** — `datasets.toml` (173 entries, schema in header).
      LANDED at v0.1.2. Verb expansion needed when ≥2 verbs wired.
- [x] **tokenizer registry** — `tool/tokenizer_extension.toml` (207 tokens / 14 groups)
      + `tool/extend_tokenizer.py` consumer. LANDED at v0.1.2 (D-008 default).
- [x] **eval lineage** — `tool/eval_lineage.py` (1,611 lines, 7 subcommands) +
      DuckDB 4-table schema (forge_runs / forge_run_scores / forge_run_tasks /
      forge_upstream_prs). Gate ⑬ dual-clause check built in. LANDED at v0.1.2-r4.
- [ ] **serving handoff** — artifact format forge exports to hexa-codex.
      Default = GGUF first → MLX → vLLM per D-011 (resolved); planned `tool/serving_handoff.py` deferred.
- [x] **license-clean gate** — `tool/license_clean_scan.py` (now 1,022 lines after
      declarative-TOML upgrade) + CI workflow `.github/workflows/license-clean.yml`
      LANDED at v0.1.2-r3, refined at r4 (gate ① wired).
- [ ] **synth pipeline** — principle×idiom expansion (Tier B principles × Tier A idioms);
      capped at 80% effective tokens per D-NEW-TC-B (resolved as D-059). Planned `tool/synth_principle_idiom.py`.
- [x] **DPO data pipeline** — `tool/build_dpo_pairs.py` (1,832 lines, 6 subcommands)
      LANDED at v0.1.2-r4. Phase 1 mocks; `--apply-real` errors with stable "Phase 2 —
      corpus required" message. Tree-sitter rule pack v1 (50 rules) wired.
- [x] **anti-corpus filter** — `tool/anticorpus_filter.py` (1,246 lines) +
      `tool/anticorpus_allowlist.toml` (107 lines) LANDED at v0.1.2-r4.
      Schema-lock guard: `--apply` requires `--unsafe-schema` flag pending
      `_common.VALID_FETCH_STATUS` extension (v0.2.1 follow-up).
- [x] **universal eval runner** — `tool/run_eval.py` dispatches the 6 bench specs.
      LANDED at v0.1.2-r3 (real scorers stub-only at v0.1.2; Mk.I scorers at v0.1.3).
- [x] **corpus quality filter** — `tool/corpus_quality_filter.py` perplexity gate.
      LANDED at v0.1.2-r3 (D-NEW-TC-E = D-062, resolved).
- [x] **license declarative source** — `tool/license_allowlist.toml`. LANDED at v0.1.2-r3.

---

## §3 v0.3.0 — additional verbs (paired with sibling repos)

Per [README §Roadmap](README.md#roadmap-next-verbs--pending):

- [ ] `physics`  — paired with `hexa-physics` / `hexa-cosmos`
- [ ] `finance`  — paired with `hexa-finance`
- [ ] `medic`    — paired with `hexa-medic` (clinical-only; distinct from `bio`)
- [ ] `lang`     — paired with `hexa-lang` (compiler-internal model)
- [ ] `arts`     — paired with `hexa-arts` (multimodal)

Each new verb = one new `docs/<verb>-llm.md` following the
`§WHY · §COMPARE · §REQUIRES · §STRUCT · §FLOW · §EVOLVE · §VERIFY`
skeleton + 1 line in `[verbs]` block of `hexa.toml`.

---

## §4 v1.0.0 — first trained weights

`v1.0.0` = **at least one verb has shippable weights** that pass its
own `§EVOLVE` acceptance bar.

Most likely candidate: `code` (smaller eval surface; clearer green
signal from build success).

Gating:

- [ ] license audit complete (no GPL contamination in pretrain mix)
- [ ] eval bar met on `HumanEval+ ≥ DeepSeek-Coder-V2-7B` and
      `hexa-eval ≥ 80%`
- [ ] safety eval bar met (off-domain refusal rate ≥ 95%)
- [ ] handoff artifact accepted by `hexa-codex serve` end-to-end
- [ ] reproducibility: full pretrain → SFT → DPO pipeline runs on a
      single H100 box from scratch in ≤ 14 days

---

## §5 Cross-link policy

Do NOT re-implement these here; call sibling CLI / repo directly:

| concern                                | sibling                                           |
| -------------------------------------- | ------------------------------------------------- |
| model serving / inference              | `hexa-codex` CLI                                  |
| genomics & wet-lab primary data        | `hexa-bio` CLI                                    |
| cognitive / general-reasoning verbs    | `hexa-mind` (pending)                             |
| neuromorphic training fabric           | `hexa-chip` CLI                                   |
| federated training transport           | `hexa-grid` CLI                                   |
