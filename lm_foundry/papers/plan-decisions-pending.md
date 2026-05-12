# plan — decisions ledger (v0.1.x)

> **Single source of truth for "what's still open" in the `code` verb
> recipe.** Resolved decisions retire to §4 with a date stamp.
> The recipe doc (`docs/code-llm.md`) is downstream of this ledger —
> spec edits are batched by phase per
> [`plan-execution-roadmap.md`](plan-execution-roadmap.md).

| field        | value                       |
| ------------ | --------------------------- |
| status       | `LIVE` — updated per session |
| owner        | `forge.code` verb           |
| last updated | 2026-05-11                  |
| convention   | `D-NNN` = decision, `M-NNN` = meta/batch |

---

## §1 How this ledger works

- Every pending design question is a `D-NNN` row with a **proposed default**
  in italics so work can proceed if no one objects.
- A row in §3 is **active**: it is gating something. The `blocks` column
  names what's stuck until it's resolved.
- When resolved: move to §4 with date, decision, and rationale (1 line).
  Do NOT delete — audit trail.
- Conflicts: if a later decision contradicts an earlier one, retire the
  earlier row to §4 with `SUPERSEDED-BY: D-NNN` and date.

---

## §2 Critical path at a glance

```
v0.1.1 spec consolidation — DONE (M-001 ✓, M-002 ✓, M-003 ✓, M-004 ✓, M-005 ✓ on 2026-05-11)

All paper-resolvable decisions resolved at v0.1.1. Remaining 3 are
strictly compute-dependent and linearly ordered:

D-009 (license-clean Stack v2 perm volume)
   └─ unblocks v0.1.2 phase exit (corpus audit + sampling)
       └─ unblocks D-007 (base weights bench: Qwen2.5-Coder-7B / DeepSeek-Coder-V2-Lite / StarCoder2-15B)
           └─ unblocks D-008 (tokenizer extension manifest)
               └─ unblocks v0.1.3 phase exit (G-BASE)
                   └─ unblocks SFT → v0.2.0 infra
                       └─ unblocks v1.0.0 first-weights gate (incl. ≥ 5 hexa-codex PRs)
```

Status: critical path is fully linear. No remaining paper decisions
block any phase. Next required compute action: **v0.1.2 corpus sampling
to close D-009**.

---

## §3 Active ledger

### Foundation (block v0.1.3)

| ID    | Status | Decision                          | Proposed                                 | Blocks                | Blocked by      |
| ----- | ------ | --------------------------------- | ---------------------------------------- | --------------------- | --------------- |
| D-007 | OPEN   | Base weights                      | *Qwen2.5-Coder-7B* (CJK + multilingual)  | tokenizer, SFT format | D-009           |
| D-008 | OPEN   | Tokenizer policy                  | *extend base BPE for hexa-lang*          | pretrain stage        | D-007           |
| D-009 | OPEN   | License-clean confirm             | *Stack v2 permissive ≈600B tok, audit*   | D-007, corpus sizing  | sampling run    |

### Style & domain priors

*(D-013 + D-016 resolved 2026-05-11 as proposed defaults — see §4. Implementation details remain in v0.1.3 / v0.1.2 phases.)*

### Domain coverage

*(All resolved 2026-05-11 — see §4. Spec deltas applied in `docs/code-llm.md` via M-001.)*

### Frontend coverage

*(D-024 / D-025 / D-026 / D-027 / D-028 all resolved 2026-05-11 as proposed defaults — see §4. Bench-scope final selection is gated on D-007 base-model availability at v0.1.3.)*

### Hexa-lang language-kind

*(D-029, D-030 resolved 2026-05-11 — see §4. Spec deltas applied in `docs/code-llm.md` §VERIFY hexa fidelity contract via M-001.)*

### Meta / batch actions

*(M-001 / M-002 / M-003 / M-004 / M-005 all resolved 2026-05-11 — see §4. Implementation artefacts: `docs/code-llm.md` (M-001), `papers/coding-philosophy-sources.md` banner (M-002), `papers/plan-multilingual-stage.md` (M-003), `papers/plan-domain-coverage.md §9.1` (M-004), `papers/plan-feedback-channel-ops.md` (M-005).)*

| ID    | Status | Action                                              | Inputs                                                     | Output                |
| ----- | ------ | --------------------------------------------------- | ---------------------------------------------------------- | --------------------- |
| M-006 | OPEN   | hexa-codex techniques consolidation                 | `papers/hexa-codex-techniques-applied.md §7 Spec-edit queue` + 11 D-NEW-TC-* | batched edits to `docs/code-llm.md` §STRUCT/§FLOW/§VERIFY + `datasets.toml` weights + `papers/plan-execution-roadmap.md` exit bars; reconcile 7 conflicts (LoRA vs full-FT, LLM-judge, dynamic gen, MoE, D/N ratio, judge ratio, test-time compute) |
| M-007 | OPEN   | D-NEW integer-slot consolidation (D-032..D-068)     | 37 D-NEW-{EV,FW,FE,DB,SF,TC}-* across 6 specs              | integer D-NNN allocation in §3 active ledger; preserve prefix-letter cross-refs |
*(M-008 resolved 2026-05-11 — see §4. mac-exec binary did not pre-exist; implemented as bash shim `tool/mac-exec` selecting shape B. Operator install: symlink to `~/bin/mac-exec` on Mac per `docs/mac_exec_cheatsheet.md §0`.)*

### D-NEW backlog (round 2 specs — 37 total; integer-slot consolidation via M-007 — resolved 2026-05-11)

> Detail prose lives in each spec's "Open questions" section. The
> prefix-letter form is the primary key (stable across renames); the
> integer slot is for the global ledger's monotonic D-NNN sequence.

### Integer-slot allocation table (M-007 resolved 2026-05-11)

| Integer slot | Prefix form         | Source spec                                                           |
| ------------ | ------------------- | --------------------------------------------------------------------- |
| D-032        | D-NEW-EV-A          | spec-hexa-eval.md (T6 firmware scope: 3 triples vs 5 boards)         |
| D-033        | D-NEW-EV-B          | spec-hexa-eval.md (Mk.V task-rotation cadence)                       |
| D-034        | D-NEW-EV-C          | spec-hexa-eval.md (T7.4 STYLE_NOTE → DPO vs diagnostic-only)         |
| D-035        | D-NEW-EV-D          | spec-five-nl-eval.md (F4 reviewer pool: 2 vs 3 per NL)                |
| D-036        | D-NEW-EV-E          | spec-five-nl-eval.md (F3 back-translation: strict AST vs refactor-eq) |
| D-037        | D-NEW-EV-F          | spec-five-nl-eval.md (F5 hypothesis → alignment diagnostic feed)      |
| D-038        | D-NEW-EV-G          | spec-five-nl-eval.md (per-NL parity 15pp → 10pp at v2.0.0)            |
| D-039        | D-NEW-FW-A          | spec-firmware-eval.md (full board set vs triples at Mk.II)            |
| D-040        | D-NEW-FW-B          | spec-firmware-eval.md (Mk.IV HIL board count: 3 vs 5)                 |
| D-041        | D-NEW-FW-C          | spec-firmware-eval.md (T3 DMA: QEMU vs Renode split)                  |
| D-042        | D-NEW-FW-D          | spec-firmware-eval.md (RV32 v1.0.0 diagnostic vs blocking)            |
| D-043        | D-NEW-FE-A          | spec-frontend-eval.md (T1 single-vs-multi framework per task)         |
| D-044        | D-NEW-FE-B          | spec-frontend-eval.md (T3 reviewer pool size for "mixed")             |
| D-045        | D-NEW-FE-C          | spec-frontend-eval.md (T4 rule-pack scope: tree-sitter only)          |
| D-046        | D-NEW-FE-D          | spec-frontend-eval.md (T2 "semantic-preferable" hard-fail vs STYLE_NOTE) |
| D-047        | D-NEW-FE-E          | spec-frontend-eval.md (T5 v0.2.0 hold vs accelerate)                  |
| D-048        | D-NEW-DB-A          | spec-db-eval.md (T2 Mongo-shape sandbox: FerretDB / DocumentDB / skip) |
| D-049        | D-NEW-DB-B          | spec-db-eval.md (T3 multi-label EXPLAIN gold)                         |
| D-050        | D-NEW-DB-C          | spec-db-eval.md (T6 tree-sitter rule pack v1.1 ORM scope)             |
| D-051        | D-NEW-DB-D          | spec-db-eval.md (T5 lock-class detection: regex vs live PG probe)     |
| D-052        | D-NEW-DB-E          | spec-db-eval.md (T1 cross-engine NL prompt sharing)                   |
| D-053        | D-NEW-SF-A          | spec-safety-eval.md (T3 dual-use authorisation: diag vs graded)       |
| D-054        | D-NEW-SF-B          | spec-safety-eval.md (per-NL parity 5pp → 3pp at Mk.V)                 |
| D-055        | D-NEW-SF-C          | spec-safety-eval.md (T5 bar ≥90% → ≥95% timing)                       |
| D-056        | D-NEW-SF-D          | spec-safety-eval.md (HARMFUL_EMIT release-block v1.0.0 vs v1.1.0)     |
| D-057        | D-NEW-SF-E          | spec-safety-eval.md (pass@k k=5 temp=0.7 secondary diagnostic)        |
| D-058        | D-NEW-TC-A          | hexa-codex-techniques-applied.md (precision policy: BF16 default)     |
| D-059        | D-NEW-TC-B          | hexa-codex-techniques-applied.md (synth data 80% cap + variance mon)  |
| D-060        | D-NEW-TC-C          | hexa-codex-techniques-applied.md (Stage-2 SFT: LoRA r=16 vs full-FT)  |
| D-061        | D-NEW-TC-D          | hexa-codex-techniques-applied.md (LR schedule: WSD vs cosine)         |
| D-062        | D-NEW-TC-E          | hexa-codex-techniques-applied.md (corpus perplexity gate)             |
| D-063        | D-NEW-TC-F          | hexa-codex-techniques-applied.md (speculative decoding γ=5 on 14B)    |
| D-064        | D-NEW-TC-G          | hexa-codex-techniques-applied.md (prefix-cache mandate + cache_hit_rate in T4) |
| D-065        | D-NEW-TC-H          | hexa-codex-techniques-applied.md (LLM-judge calibration ratio 80/20)  |
| D-066        | D-NEW-TC-I          | hexa-codex-techniques-applied.md (test-time compute scaling — best-of-N) |
| D-067        | D-NEW-TC-J          | hexa-codex-techniques-applied.md (dynamic hexa-eval — defer to v1.1.0) |
| D-068        | D-NEW-TC-K          | hexa-codex-techniques-applied.md (prompt-injection refusal bench)     |

**Allocation rules:**
- Integer slots are stable once allocated — never renumbered.
- Prefix-letter form is the cross-spec lookup key (matches the source
  doc's "Open questions" section verbatim).
- All 37 enter §3 active ledger as OPEN; resolution date stamps land
  individually in §4 when each is closed.
- M-007 itself is now resolved (this table is its sole output).

### Round 2 D-NEW backlog (prefix-grouped index — pre-integer assignment)

> Detail prose lives in each spec's "Open questions" section. This is the index.

| Prefix group | Count | Source spec / doc                                          | Topics |
| ------------ | ----- | ---------------------------------------------------------- | ------ |
| **D-NEW-EV-A..G** | 7 | `spec-hexa-eval.md` + `spec-five-nl-eval.md`               | T6 firmware scope, Mk.V rotation cadence, STYLE_NOTE→DPO, reviewer pool, back-translation tolerance, hypothesis→alignment, per-NL parity tighten |
| **D-NEW-FW-A..D** | 4 | `spec-firmware-eval.md`                                    | full-board vs triples, HIL board set, QEMU/Renode split, RV32 v1.0.0 diag vs block |
| **D-NEW-FE-A..E** | 5 | `spec-frontend-eval.md`                                    | T1 multi-framework, T3 reviewer pool, T4 rule-pack scope, T2 STYLE_NOTE hard-fail, T5 v0.2.0 hold |
| **D-NEW-DB-A..E** | 5 | `spec-db-eval.md`                                          | Mongo sandbox choice, T3 multi-label, ORM rule pack v1.1, T5 lock-class detection, T1 cross-engine NL |
| **D-NEW-SF-A..E** | 5 | `spec-safety-eval.md`                                      | dual-use protocol, per-NL parity 3pp, T5 bar tighten, HARMFUL_EMIT severity, pass@k secondary |
| **D-NEW-TC-A..K** | 11 | `hexa-codex-techniques-applied.md`                         | BF16 default, synth 80% cap, LoRA r=16 default, WSD-LR, perplexity gate, spec decoding γ=5, prefix cache, judge 80/20, test-time compute, dynamic hexa-eval defer, prompt-injection bench |
| **Total**         | **37** | — | — |

---

## §4 Resolved (audit trail)

| ID    | Decision                          | Resolved                                                  | Date       |
| ----- | --------------------------------- | --------------------------------------------------------- | ---------- |
| D-001 | native-first + canon-first prior  | adopt; baked in §WHY + §STRUCT philosophy + §VERIFY style | 2026-05-11 |
| D-002 | philosophy stage in §STRUCT       | add 1 row, ~3B tok target *(revisited as D-017)*          | 2026-05-11 |
| D-003 | hardware tier in §VERIFY          | M4 Mini 16GB→7B Q5/Q6 default; tier ladder published     | 2026-05-11 |
| D-004 | hexa-codex linkage rule           | reference URLs only, never inline-copy *(extended D-031: bidirectional)* | 2026-05-11 |
| D-005 | 5 NL language coverage set        | English / Korean / Chinese / Japanese / Russian           | 2026-05-11 |
| D-006 | hexa-lang is firmware-native      | acknowledged from SPEC.md; firmware = 1st-class surface   | 2026-05-11 |
| D-012 | philosophy corpus sourcing        | resolved via Tier A/B/C/E findings + F-1/F-2/F-3 frontend findings; §STRUCT philosophy row sources expanded; banner on `coding-philosophy-sources.md` | 2026-05-11 |
| D-014 | DB tier scope                     | T1 풀 (Postgres/SQLite/DuckDB/pgvector/Qdrant/Chroma/LanceDB/Redis/ClickHouse/Cassandra/Kafka/Cypher) + T2 quote-only (MySQL/MongoDB/Elasticsearch); T3 → v0.2.0 | 2026-05-11 |
| D-015 | DB stage placement                | new `db-native` stage added to §STRUCT (parallel to `firmware-native`/`hexa-firmware`) | 2026-05-11 |
| D-017 | philosophy stage token target     | re-stated: raw ~30M + ×10 weight + ×5-10 synth → ~500M-1B effective; §STRUCT row revised | 2026-05-11 |
| D-018 | License downgrades                | applied: danluu / Worse-is-Better / Pragmatic / AWS Builders' / Cloudflare / GitHub blog / SRE Book → excerpt; SRE Workbook promoted to full (CC BY 4.0); CERT C promoted to full (CC-BY-4.0 + MIT) | 2026-05-11 |
| D-019 | URL corrections                   | applied: GitHub → `github.blog/tag/github-availability-report/`; k8s → `kubernetes/community/.../sig-cluster-lifecycle/postmortems`; AWS PES → `aws.amazon.com/premiumsupport/technology/pes/` | 2026-05-11 |
| D-020 | C + firmware §WHY/§STRUCT add    | applied: §WHY systems & firmware + hardware reference literacy lines; §STRUCT firmware-native + hexa-firmware rows; §EVOLVE 4 firmware benches; §VERIFY firmware tools | 2026-05-11 |
| D-021 | hexa-lang fidelity contract       | applied: §VERIFY new "hexa fidelity contract" bullet (S0-S8, HX-codes, @grace 3-field, arena, no-Z3/CVC5, no-GC, no-LLVM, English-only, target-gate) | 2026-05-11 |
| D-022 | 5 NL coverage in §WHY            | applied: §WHY "code-adjacent natural language" line (EN T0; KR/CN/RU/JA T1)         | 2026-05-11 |
| D-023 | NL carve-out for diagnostics     | applied: diagnostics English-only (per hexa SPEC §7); refusal text English-canonical; prose/comments 5 NL | 2026-05-11 |
| D-024 | Frontend stage placement          | filter-expand existing stages confirmed; §STRUCT `domain-bias`/`build-trace`/`diff-edit`/`repair`/`philosophy` rows extended | 2026-05-11 |
| D-025 | Frontend canon corpus sourcing    | F-1/F-2/F-3 web research landed; §9.1 cells filled in `plan-domain-coverage.md`     | 2026-05-11 |
| D-029 | Hexa-lang teaching frame          | PRIMARY = compiled (`hexa cc`); SECONDARY = slim AST interp (`--interp`/`hexa repl`, ~200-500 LOC). OLD 20k-LOC `hexa_interp` is anti-canon. Applied in §VERIFY hexa fidelity contract. | 2026-05-11 |
| D-030 | Hexa-lang exclusion list adoption | applied: §STRUCT `hexa-native` filter excludes `legacy/` `archive/` `*.deprecated.*`; §VERIFY hexa fidelity contract enumerates the no-GC/no-Z3/no-LLVM/no-Korean-i18n rejects. Detail in `plan-domain-coverage.md §8`. | 2026-05-11 |
| D-031 | hexa-codex linkage bidirectionality | Extension of D-004. Forge → codex feedback channel formalised in `docs/code-llm.md` §VERIFY upstream feedback contract + Cross-link policy "feedback channel" subsection. v1.0.0 forge gate ≥ 5 PRs landed in hexa-codex. | 2026-05-11 |
| M-001 | Spec consolidation                | applied to `docs/code-llm.md`: §WHY +6 bullets, §STRUCT +3 stages + philosophy revised, §EVOLVE +14 benches grouped, §VERIFY +tool surface +hexa fidelity +2026-canon-first style +upstream feedback, Cross-link bidirectional + feedback channel, Open Qs reduced to 7 compute-dependent | 2026-05-11 |
| M-002 | papers source-list revision       | applied: `coding-philosophy-sources.md` SUPERSEDED banner + critical corrections enumerated; tier-{a,b,c,e}-findings.md and frontend-f{1,2,3}-findings.md become live detail layer | 2026-05-11 |
| M-004 | Frontend research consolidation   | applied: `plan-domain-coverage.md §9.1` table now per-row sourced from F-1/F-2/F-3 (19 axes + token budget + license gate) | 2026-05-11 |
| D-010 | Eval lineage storage              | **DuckDB** (sister-pattern with hexa-codex's lattice/parity verifiers; HF datasets stays for corpus). Cheap to confirm at v0.2.0 entry. | 2026-05-11 |
| D-011 | Serving handoff format            | **GGUF first → MLX → vLLM** (broadest reach first; per `docs/code-llm.md §VERIFY hardware tier` ladder).             | 2026-05-11 |
| D-013 | native/canon-first DPO scoring   | **tree-sitter rule pack v1** (deterministic, license-clean). LLM-judge v2 **deferred** — Shumailov 2024 model-collapse risk; per `docs/code-llm.md §VERIFY style contract + upstream feedback contract`. | 2026-05-11 |
| D-016 | Stack Exchange license stance    | **중도** (middle path): pre-2024-07 Academic Torrents only (CC-BY-SA-4.0 cleanly; post-2024-07 contested by SE ToS "no LLM training" clause). Yields ~1-3M DPO pairs without legal exposure. | 2026-05-11 |
| D-026 | Mobile / cross-platform inclusion | **RN New Architecture + Expo SDK 55 + Capacitor + Tauri 2** (T1, MIT/Apache-2 all clean); **Flutter T2 quote-only** (Dart is its own ecosystem; reduces cross-pollination risk for the code corpus). | 2026-05-11 |
| D-027 | AI-native UI corpus stance        | **Vercel AI SDK (Apache-2) + AI Elements + primitives** from `docs/code-llm.md §9.1 AI-native UI` row. **No LLM-judge synth** (Shumailov 2024 model-collapse) — same rule as D-013. | 2026-05-11 |
| D-028 | Frontend bench scope for v0.1.x   | **4 benches**: component-synthesis, a11y-fix, RSC-vs-client decision, CSS-modernize (per `docs/code-llm.md §EVOLVE frontend` rows). Remainder (`bundle-fit`, `AI-UI patterns`) deferred to v0.2.0. Final selection gated on D-007 base availability. | 2026-05-11 |
| M-003 | Multilingual stage filter design  | applied: [`plan-multilingual-stage.md`](plan-multilingual-stage.md) — NL-tag schema, per-stage filter rules, per-NL source map with license posture, rebalance algorithm targeting EN 70% / KR+CN+RU+JA 30%, diagnostic carve-out impl, eval slice, upstream feedback to `hexa-codex/eval` + `quality_scale`. | 2026-05-11 |
| M-005 | Forge → hexa-codex feedback ops  | applied: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md) — 10-artifact → verb routing table, PR template, automation triggers (`tool/emit_*.hexa`), v1.0.0 acceptance criteria ≥ 5 PRs landed, outbox layout, failure modes. | 2026-05-11 |
| M-008 | mac-exec HF-bridge routing acceptance | implemented as bash shim at [`tool/mac-exec`](../tool/mac-exec) (Apache-2.0 OR MIT, ~135 lines). Operator confirmed `mac-exec` binary did not pre-exist on Mac (`command -v mac-exec` empty); shim selects shape B (`--hf-passthrough`) since shape A's explicit env-routing not needed at v0.1.3 G-BASE scope. Pulls token from Mac-side `secret get $SECRET_KEY` (default `HF_TOKEN`), SSHes to `$FORGE_HOST` (default `linux-forge`) with `HUGGING_FACE_HUB_TOKEN` + `MAC_EXEC_TOKEN_HASH_12` injected; `exec ssh` so remote exit code propagates. Install one-liner in [`docs/mac_exec_cheatsheet.md §0`](../docs/mac_exec_cheatsheet.md). Path convention: `~/core/hexa-forge/` on Mac, `~/mac_home/core/hexa-forge/` inside SSH'd command. | 2026-05-11 |

---

## §5 Adding a new decision (template)

Copy this into §3 under the appropriate group:

```
| D-NNN | OPEN   | <one-line decision name>          | *<proposed default>*                     | <what's blocked>      | <what blocks this> |
```

Rules:
- The `Proposed` column is italicised on purpose — anyone can act on the
  default if no one objects within the session.
- If a row sits OPEN for >2 sessions without resolution, escalate by
  marking `STALE` and adding to v0.1.x exit checklist.

---

## Cross-link

- Execution sequencing: [`plan-execution-roadmap.md`](plan-execution-roadmap.md)
- Coverage matrix: [`plan-domain-coverage.md`](plan-domain-coverage.md)
- Tier findings: [`tier-a-findings.md`](tier-a-findings.md) ·
  [`tier-b-findings.md`](tier-b-findings.md) ·
  [`tier-c-findings.md`](tier-c-findings.md) ·
  [`tier-e-findings.md`](tier-e-findings.md)
- Recipe spec: [`../docs/code-llm.md`](../docs/code-llm.md)
- Open questions inside recipe: [`../docs/code-llm.md` open Qs](../docs/code-llm.md#open-questions-v010)
  (rolled up here as D-007..D-013)
