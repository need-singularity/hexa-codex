<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->
<!-- SPDX-FileCopyrightText: 2026 hexa-forge contributors -->
<!-- @canonical: forge@v0.1.2:papers/spec-db-eval.md -->
<!-- @owns(sections=[HEADER, WHY, COMPARE, REQUIRES, STRUCT, FLOW, EVOLVE, VERIFY, FEEDBACK, TOOLING], strict=false, order=sequential, prefix="S") -->

# `DB-eval` — custom benchmark spec for database surface fidelity

> **Acceptance gate (v1.0.0).** This spec defines benchmark **⑤** from
> [`docs/code-llm.md` §EVOLVE](../docs/code-llm.md#evolve--eval-harness)
> — the three `database` rows (Spider/BIRD `≥ 60% exec-correct` + EXPLAIN
> literacy `≥ 70%` + schema-design `≥ 70%`), aggregated under a single
> custom bench. The bars exist in the recipe; the **shape** is defined
> here. Implementation lands v0.1.3+.
>
> **Decisions referenced.** D-014 (DB tier scope — T1 full include /
> T2 quote-only / T3 deferred), D-015 (DB stage placement —
> `db-native` ~15B-tok stage in §STRUCT), D-013 (no LLM-judge for
> gold — Shumailov 2024 model-collapse risk).
> See [`papers/plan-decisions-pending.md`](plan-decisions-pending.md).
>
> **Sister methodology canon.** Section discipline (S-prefix,
> falsifier-anchored, arithmetic floor → numerics → parity → live)
> mirrors [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md)
> §S1 WHY → §S7 VERIFY. The DB surface is treated as **one capability
> axis** sliced across 7 task families.

---

## S0 HEADER

| field             | value                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------- |
| verb              | `code` (sub-artifact `DB-eval`)                                                             |
| family            | `hexa-forge`                                                                                |
| status            | `RESEARCH_FIRST` — spec only, runner script planned                                         |
| dispatch          | `hexa-forge code eval --bench db-eval`                                                      |
| acceptance gate   | **≥ 60% aggregate** (exec-correct + plan-ID + migration-reversibility, single bar)          |
| task count target | **~750** (T1=200, T2=100, T3=100, T4=100, T5=100, T6=100, T7=50)                            |
| owner             | `forge.code` verb                                                                           |
| sister gates      | ③ `hexa-eval` ([`spec-hexa-eval.md`](spec-hexa-eval.md)); ④ `5-NL eval` ([`spec-five-nl-eval.md`](spec-five-nl-eval.md)) |
| codex feedback    | `hexa-codex/quality_scale` (cross-cutter — DB axis) + `hexa-codex/eval` (Mk progression) — per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md) |
| §STRUCT source    | `db-native` stage (~15B tok target, D-015) — [`plan-domain-coverage.md §3`](plan-domain-coverage.md) |
| §VERIFY tool surface | `run_query` (sandbox) · `explain_query` · `apply_migration` · `read_schema`              |
| last updated      | 2026-05-11                                                                                  |

---

## S1 WHY — why DB code is a distinct surface

A "code LLM" that ships without database fidelity ships **incomplete**.
The DB surface is *not* one capability — it is a **stack of five
distinct sub-capabilities** that public benches do not cover jointly:

1. **Query synthesis.** NL → SQL (Spider/BIRD), NL → Redis cmd, NL →
   Cypher, NL → ANN-vector query. Dialect-aware.
2. **Schema literacy.** DDL reading, FK chains, partitioning, normal
   form intuition (3NF vs star vs document shape).
3. **Plan literacy (EXPLAIN reading).** Given `EXPLAIN (ANALYZE,
   BUFFERS)` output, identify the bottleneck: seq-scan, nested-loop
   blow-up, missing index, cardinality gap, hash-spill. **Off-the-
   shelf benches do not test this at all.**
4. **Migration safety.** alembic/flyway/atlas/prisma/sqitch
   reversibility, online vs locking DDL, zero-downtime patterns
   (shadow column, backfill batching). Public benches do not test it.
5. **ORM idiom.** SQLAlchemy / sqlx / Diesel / GORM / Prisma —
   prose-to-idiom translation; mismatches survive type-checking and
   ship.

Spider 1.0 and BIRD-SQL cover only (1) on the relational sub-surface,
on a single dialect each. They do not test cross-engine portability
(`STRING_AGG` ⟷ `GROUP_CONCAT`), EXPLAIN literacy, or migration
safety. A model scoring 80% on BIRD might still produce a migration
that locks a production table for 6 hours — the recipe has no signal
for that today.

The recipe's §VERIFY tool surface (`run_query`, `explain_query`,
`apply_migration`, `read_schema`) only makes sense if the model has
all five sub-capabilities *jointly*; testing (1) alone leaves four
tools as unverified product surface.

**Core falsifiable claim.** If the trained `code` verb cannot pass
DB-eval at ≥ 60% aggregate (with non-zero hard-tier floor on each of
the seven families), the **"production-DB-capable programming model"**
thesis is empirically falsified for v1.0.0. The recipe must either
downgrade the §VERIFY DB tool surface or retrain with a richer
`db-native` stage.

## S2 COMPARE — vs public DB benchmarks

```
+--------------------------------------------------------------------+
|  [Coverage of DB sub-capabilities]                                 |
+--------------------------------------------------------------------+
|  Spider 1.0              #####....................  NL→SQL (1 dial)|
|  BIRD-SQL                #######..................  NL→SQL + value |
|  SParC / CoSQL           ######...................  conv/dialog SQL|
|  DB-Bench (academic)     ########.................  multi-task SQL |
|  DB-eval (this spec)     ##################........ +NoSQL+EXPLAIN |
|                                                     +DDL+migration |
|                                                     +ORM+vector    |
+--------------------------------------------------------------------+
|  [Multi-engine dialect awareness]                                  |
+--------------------------------------------------------------------+
|  Spider 1.0 / BIRD       ###......................  SQLite-ish    |
|  DB-eval T1              ##################........ PG+SQLite+DuckDB|
|  DB-eval T2              ##################........ Redis/Cypher/Mongo|
+--------------------------------------------------------------------+
|  [Plan + safety verification]                                      |
+--------------------------------------------------------------------+
|  Spider / BIRD           ##.......................  exec only      |
|  DB-eval T3 (EXPLAIN)    ##################........ bottleneck-ID  |
|  DB-eval T5 (migration)  ##################........ reversibility  |
+--------------------------------------------------------------------+
|  [Contamination resistance]                                        |
+--------------------------------------------------------------------+
|  Spider 1.0              ##.......................  saturated      |
|  BIRD-SQL                #####....................  partial leak   |
|  DB-eval T3/T5/T7        ##################........ handcrafted    |
+--------------------------------------------------------------------+
```

**DB-eval's niche.** Complementary, not competitive, to Spider/BIRD.
DB-eval *reuses* Spider/BIRD splits for T1 (NL → SQL is a solved
benchmark shape) and **extends** with the four sub-capabilities those
benches don't measure: EXPLAIN literacy (T3), schema design (T4),
migration safety (T5), and vector-DB ops (T7).

A model that passes Spider/BIRD ≥ 60% **but** fails DB-eval T3/T5/T7
is still **release-blocked** under the v1.0.0 gate — the public bench
alone is *necessary but not sufficient*.

## S3 REQUIRES — prerequisites

| prerequisite                                                  | source / location                                                                              | check                |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------- |
| **D-013 / D-014 / D-015 closed**                              | [`plan-decisions-pending.md`](plan-decisions-pending.md) (all closed 2026-05-11)               | resolved             |
| Sandbox SQL engines (PostgreSQL 16, SQLite 3.45+, DuckDB 1.x) | `tool/run_db_eval.py` docker-compose harness (S9); SQLite/DuckDB in-process                    | engines up + healthy |
| Sandbox KV / graph / Mongo-shape (Redis 7.x, Neo4j 5.x, FerretDB) | same harness                                                                               | engines up + healthy |
| Vector-DB sandbox (pgvector, Qdrant, Chroma, LanceDB)         | same harness; ANN fixtures + ground-truth hash-pinned                                          | indexes built        |
| License-clean schema corpus                                   | Spider (CC-BY-SA), BIRD-SQL (CC-BY-SA), DuckDB TPC-H sample (MIT), Mongo Atlas sample shape    | per-fixture audit    |
| Spider 1.0 + BIRD-SQL devsets, hash-pinned                    | upstream releases; SHA recorded in runner config                                               | hash-match           |
| EXPLAIN-trace + migration corpora (handcrafted)               | mined adjunct to `db-native` stage — [`plan-domain-coverage.md §3`](plan-domain-coverage.md)   | per-source check     |
| `run_query` / `explain_query` / `apply_migration` / `read_schema` tool surface wired in candidate | [`docs/code-llm.md §VERIFY`](../docs/code-llm.md#verify--serving-contract) tool list | candidate must wire  |

**Stage ordering.** Independent of `hexa-eval` / `5-NL eval` — three
benches run in parallel and aggregate separately. DB-eval depends on
the `db-native` stage actually having been trained into the
candidate (D-015); a candidate trained only on generic code stages
will trivially fail T3/T5/T7.

**No upstream pollution.** Per [`plan-multilingual-stage.md §3`](plan-multilingual-stage.md)
reject-list shape, DB-eval prose + gold queries are tagged
`bench-text` and excluded from the `db-native` training corpus.
Spider/BIRD splits are public — risk is real; Mk.V quarantine (S6)
is the mitigation.

## S4 STRUCT — task taxonomy

7 families, **~750** tasks total. Each ties to one or more of the
five S1 sub-capabilities; coverage maps to the capability surface.

### S4.1 Task family table

| ID  | family                          | count | sub-cap                  | engines covered                                            | gold-format               |
| --- | ------------------------------- | ----- | ------------------------ | ---------------------------------------------------------- | ------------------------- |
| T1  | NL → SQL                        | 200   | (1) query synth          | PostgreSQL / SQLite / DuckDB (Spider/BIRD-derived)         | exec-equality             |
| T2  | NL → NoSQL query                | 100   | (1) query synth          | Redis cmd / MongoDB shape / Cypher (openCypher)            | exec-equality             |
| T3  | EXPLAIN reading                 | 100   | (3) plan literacy        | PostgreSQL EXPLAIN, DuckDB PROFILE                         | bottleneck-class label    |
| T4  | schema design                   | 100   | (2) schema literacy      | PostgreSQL DDL (FK + indexes + partitioning)               | DDL diff + NF check       |
| T5  | migration safety                | 100   | (4) migration            | alembic / flyway / atlas / prisma (Postgres-targeted)      | reverse + re-apply byte-equal |
| T6  | ORM idiom                       | 100   | (5) ORM                  | SQLAlchemy (Py) / sqlx (Rust) / Diesel (Rust) / GORM (Go) / Prisma (TS) | idiom-class match (tree-sitter rule pack v1) |
| T7  | vector DB ops                   | 50    | (1)+(2) on ANN           | pgvector / Qdrant / Chroma / LanceDB                       | ANN top-K recall          |
|     | **total**                       | **750** |                        |                                                            |                           |

### S4.2 Per-family detail

**T1 — NL → SQL (200).** Spider 1.0 dev + BIRD-SQL dev derived;
prompts EN. Per-engine variants: PostgreSQL 80 / SQLite 80 / DuckDB
40 — same NL prompt across dialects where relevant (forces literacy
on `STRING_AGG`/`GROUP_CONCAT`/`LIST`, window funcs, recursive CTEs).
Hardness 40/40/20 (matches BIRD's split). Pass: **execution equality**
on the fixture DB — set-equal unless query has `ORDER BY`.

**T2 — NL → NoSQL query (100).** Three sub-tracks: **Redis (40)**
— NL → command sequence (`HSET`/`ZADD`/`XADD`, `MULTI/EXEC`, `Lua
EVAL`); pass = exec-equality on Redis sandbox via `run_query`.
**MongoDB-shape (30)** — NL → aggregation pipeline / find-query,
authored *only* against the public Mongo Atlas sample shape (D-014
quote-only — no proprietary doc text); sandbox is a compatible-shape
engine (FerretDB/DocumentDB per S9), not the proprietary binary.
**Cypher (30)** — NL → Cypher / openCypher pattern; pass =
exec-equality on Neo4j sandbox.

**T3 — EXPLAIN reading (100).** Input: SQL query + `EXPLAIN
(ANALYZE, BUFFERS)` trace from Postgres (or `PROFILE` from DuckDB).
Output: bottleneck-class label from a **fixed 9-way taxonomy**
(frozen at task-set freeze): `seq-scan-on-large-table`,
`nested-loop-blow-up`, `missing-index`, `cardinality-estimate-gap`,
`hash-spill`, `index-only-scan-miss`, `correlated-subquery`,
`sort-spill`, `cte-materialization`. Pass: single-label exact match
(gold is single-best by construction; no multi-label credit at
Mk.II — see D-NEW-I). Anchors `db-native` stage EXPLAIN-trace mining
(D-015).

**T4 — schema design (100).** Input: requirements prose ("e-commerce
order system, customers + line items + products + shipping + refund
history, 100M orders/yr, OLAP on revenue per region per month").
Output: PostgreSQL DDL (`CREATE TABLE`, FK, `CREATE INDEX`,
partitioning). Pass: **all three sub-checks** — (a) DDL diff (table/
column/type set matches gold up to `text`↔`varchar(n)`, `int`↔`int4`);
(b) required-index presence (extra indexes diagnostic, not blocking);
(c) 3NF check via deterministic FD checker (per-task FD annotation
frozen at task-set freeze).

**T5 — migration safety (100).** Input: schema-change prose ("rename
`customer.email` → `customer.email_address`, online, zero-downtime,
Postgres 16, active writes"). Output: migration in the requested
tool's idiom (alembic 25 / flyway 25 / atlas 25 / prisma 25). Pass:
**reverse + re-apply → byte-equal** — apply `up` → snapshot A; apply
`down` → snapshot must equal pre-migration; re-apply `up` → must
equal A. Plus **lock-class** sub-check: DDL regex flags `ACCESS
EXCLUSIVE` on tables > 1M rows (per fixture size hint); if prose says
"online", such locks fail the task. Both reversibility AND lock-class
respect required.

**T6 — ORM idiom (100).** Input: prose intent ("fetch `User` rows
where `created_at` in last 30 days, eager-load `Profile`+`Orders`
(orders only `status='paid'`), order by `created_at` desc, paginate
offset/limit"). Output: idiomatic ORM code (SQLAlchemy 20 / sqlx 20
/ Diesel 20 / GORM 20 / Prisma 20) — **no Java-port Hibernate**,
native-first per [`docs/code-llm.md §VERIFY style contract`](../docs/code-llm.md#verify--serving-contract).
Pass: **idiom-class match** via tree-sitter rule pack v1 (per D-013)
— candidate AST matches a gold idiom class for the operation (e.g.
"SQLAlchemy: `selectinload` not `joinedload` for collections";
"Prisma: `include` with `where`, not nested `findMany`"). No
LLM-judge.

**T7 — vector DB ops (50).** Input: vector-search requirement
("build ANN over 1M × 768-dim embeddings on pgvector/Qdrant/Chroma/
LanceDB; tune `m`, `ef_construction`; top-10 cosine"). Output:
index-build DDL/API + query. Pass: **top-K recall ≥ 0.90** vs
hash-pinned brute-force ground truth — any parameter choice that
clears the bar is accepted. Engine split: pgvector 20 / Qdrant 10 /
Chroma 10 / LanceDB 10.

### S4.3 Task math + coverage proof

```
T1  NL→SQL          200   (PG 80 + SQLite 80 + DuckDB 40)
T2  NL→NoSQL        100   (Redis 40 + Mongo-shape 30 + Cypher 30)
T3  EXPLAIN         100   (PG EXPLAIN 80 + DuckDB PROFILE 20)
T4  schema design   100   (PostgreSQL DDL)
T5  migration       100   (alembic 25 + flyway 25 + atlas 25 + prisma 25)
T6  ORM idiom       100   (SQLAlchemy/sqlx/Diesel/GORM/Prisma — 20 each)
T7  vector DB        50   (pgvector 20 + Qdrant 10 + Chroma 10 + LanceDB 10)
────────────────────────────
total               750
```

S1 sub-cap coverage: (1) query synth → T1+T2+T7; (2) schema literacy
→ T4 (+ implicit in T1); (3) plan literacy → T3; (4) migration → T5;
(5) ORM → T6. All five anchored.

### S4.4 Hardness distribution

Per-family `easy / med / hard` ratios so the ≥ 60% bar is meaningful
regardless of which families saturate first:

```
T1: 40/40/20  -- inherits Spider/BIRD split
T2: 40/40/20  -- handcrafted; matched to T1
T3: 30/40/30  -- 9-way label has hard tail
T4: 20/50/30  -- partitioning + FD is hard
T5: 20/50/30  -- online migration is genuinely hard
T6: 40/40/20  -- idiom recognition mostly clean
T7: 30/50/20  -- index tuning is medium-core
```

A candidate ≥ 60% **overall** with 0 on any hard tier is flagged for
review (diagnostic, not blocking — matches `spec-hexa-eval.md §S4.3`).

## S5 FLOW — generation + scoring discipline

```
[1] Task sourcing      [2] Gold-output freeze   [3] Hash-pin
  Spider/BIRD (T1)  --> handcrafted T2-T7    --> engine SHA + fixture
  (license-clean)       scenarios                SHA + task hash
                                                    |
                                                    v
                          [4] Candidate response --> [5] Score
                            sandbox engines run     per-family scorer
                            run_query/explain_      aggregate ≥ 60% gate
                            query/apply_migration   per-family floor diag
                                                       |
                                                       v
                          [6] outbox/hexa-codex/quality_scale/
                          [7] outbox/hexa-codex/eval/ (Mk delta)
```

### S5.1 Authoring discipline (D-013 enforced)

**No LLM-judge synthesis for gold output.** Gold sources:
- T1 only: mined from Spider 1.0 / BIRD-SQL public splits (CC-BY-SA,
  license-clean), upstream gold preserved as-is, hash-pinned.
- T2-T7: **handcrafted** by a DB-fluent maintainer — EXPLAIN class
  labels, schema requirements, migration scenarios, ORM idioms,
  vector index parameters.
- Where applicable: **deterministic** transforms (Spider gold →
  Postgres dialect via hand-written rule pack — no LLM in the loop).

Per D-013 + `spec-hexa-eval.md §S5.1`: Shumailov 2024 model-collapse
risk applies to bench authoring. No LLM-judge for gold, period.

### S5.2 Scoring algorithm (per-task)

```
score(task, candidate):
    emit = candidate(task.input)
    match task.family:
      T1|T2: rows_g = run_query(task.gold_query, task.fixture_db)
             rows_c = run_query(emit, task.fixture_db)
             return set_equal(rows_g, rows_c) OR
                    (task.has_order_by AND list_equal(rows_g, rows_c))
      T3:    return emit.label == task.gold_label   # 9-way categorical
      T4:    return ddl_diff(emit, task.gold_ddl) == OK
                AND index_set(emit) >= task.required_indexes
                AND nf_check(emit, task.fd_annotations) == OK
      T5:    snap0 = snapshot(db); apply(emit.up);  snapA  = snapshot(db)
             apply(emit.down);     snapB  = snapshot(db)
             apply(emit.up);       snapA2 = snapshot(db)
             return snapB == snap0 AND snapA == snapA2
                AND lock_class_respect(emit, task.online_required)
      T6:    return ts_rule_pack_match(parse(emit), task.idiom_class)
      T7:    build_index(emit.ddl); cand_topk = run_ann(emit.query)
             return recall(cand_topk, task.ground_truth_topk) >= 0.90
    # tally per family + aggregate
```

### S5.3 Determinism + reproducibility

- Each task: `task_id` + `engine_sha` + `fixture_sha` + `gold_hash`.
- Runner pins: engine container digests (Postgres 16.x, SQLite 3.45.x,
  DuckDB 1.x, Redis 7.x, Neo4j 5.x, pgvector/Qdrant/Chroma/LanceDB),
  fixture DB dump SHA, candidate model SHA. Drift in any → new
  `run_id`, no in-place re-grade.
- Temperature = 0 primary; `pass@k` secondary diagnostic (matches
  hexa-eval / 5-NL eval pattern).
- **Sandbox isolation**: every T5 task runs against a fresh container
  snapshot — no cross-task state leakage. Post-task teardown SHA must
  match clean-engine teardown SHA (post-migration drift = test
  pollution → task invalidated).

## S6 EVOLVE — Mk.I → Mk.V progression

Matches hexa-codex `eval/ai-eval-pipeline.md §S6 EVOLVE` 5-stage shape.
Sister specs use the same staging — DB-eval Mk progression holds the
same breadth-vs-rigor ratio as hexa-eval / 5-NL eval.

- **Mk.I (1 month) — T1+T2 only, manual rubric.** ~300 tasks
  (T1=200 + T2=100). Maintainer runs queries against sandbox engines
  and tallies. Goal: confirm the bench discriminates between a base
  model (no `db-native` stage) and an SFT-bias-only candidate.

- **Mk.II (2 months) — full T1-T7 automated via real engines in
  containers.** All 750 tasks live. `tool/run_db_eval.py` (S9)
  orchestrates the docker-compose harness, dispatches per-task
  scoring, emits per-family JSON + aggregate Parquet. Calibration
  stage, not release.

- **Mk.III (3 months) — adversarial perturbation + plan-instability
  injection.** T1: schema-noise (irrelevant columns, FK chain
  extension). T3: **plan-instability injection** — re-run `EXPLAIN`
  after `ANALYZE` on different row counts; gold bottleneck must hold
  (forces *reasoning* about the plan, not trace pattern-match). T5:
  fixture-size variation (small vs large → different lock semantics).
  T6: idiom swap (same intent, different ORM).

- **Mk.IV (4 months) — full pipeline + hexa-forge CI integration.**
  PRs touching `db-native` data / SFT mix / base weights trigger a
  shadow run on a canary subset (~75 tasks, 10%, all families
  represented). Full-run on tag-pushes only (container spin-up is the
  cost driver). Output routes per
  [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md).

- **Mk.V (long-term) — industry-standard + contamination quarantine.**
  Task set published with cryptographic hash; forks must prove
  `gold_hash` non-leakage. Rotation: T1 **annual** (upstream-pinned,
  rotate when Spider/BIRD release new splits); T2/T7 **quarterly**
  (template-generatable); T3/T4/T5/T6 **yearly** (effort-bound).
  Contamination check **per engine** — PG n-gram overlap is
  independent of DuckDB overlap. Mirrors hexa-codex eval Mk.V
  "automatic contamination quarantine."

| Mk    | scope                                  | pass criterion                  | unlocks                          |
| ----- | -------------------------------------- | ------------------------------- | -------------------------------- |
| Mk.I  | T1+T2 manual                           | ≥ 20pp base→SFT discrimination  | proceed to T3-T7 authoring       |
| Mk.II | T1-T7 automated (containers)           | ≥ 45% SFT aggregate             | wire into CI                     |
| Mk.III | + perturbation + plan-instability     | ≤ 15pp adversarial drop         | publish bench v1                 |
| Mk.IV | + CI integration + feedback PR         | ≥ 60% × 3 consecutive CI runs   | **v1.0.0 forge release**         |
| Mk.V  | + contamination quarantine + rotation  | hash-pinned, leak-audited       | community-standard candidate     |

## S7 VERIFY — acceptance bar + failure semantics

### S7.1 Acceptance arithmetic

- **Aggregate gate.** `passed / 750 ≥ 0.60` ⇒ release-eligible (this
  bench alone; other §EVOLVE rows must also hold).
- **Per-family floor (diagnostic).** No family below 40% (an
  aggregate ≥ 60% dominated by easy families is still flagged).
- **Per-engine floor (diagnostic).** T1: no engine variant (PG /
  SQLite / DuckDB) below 50%. T2: no sub-track (Redis / Mongo-shape
  / Cypher) below 40%.
- **Hard-tier sanity.** Each family's `hard` tier > 0% — a 0% hard
  tier implies hardness mis-calibration (matches hexa-eval §S7.1).

### S7.2 Per-family scoring rubric (canonical bars)

| family | sub-bar (Mk.IV target) | note                            |
| ------ | ----------------------- | ------------------------------- |
| T1     | ≥ 60% exec-correct      | recipe-named (Spider/BIRD bar)  |
| T2     | ≥ 50% exec-correct      | weight 100/750                  |
| T3     | ≥ 70% label match       | recipe-named (EXPLAIN bar)      |
| T4     | ≥ 70% all 3 sub-checks  | recipe-named (schema-design bar)|
| T5     | ≥ 50% reverse-byte-equal | weight 100/750                 |
| T6     | ≥ 60% idiom-class match | weight 100/750                  |
| T7     | ≥ 60% ANN recall ≥ 0.90 | weight 50/750                   |

The **three recipe-named bars** (T1 ≥ 60%, T3 ≥ 70%, T4 ≥ 70%) are
also **diagnostic floors** — failing any one even when aggregate
≥ 60% triggers release-block review. The aggregate does NOT override
the named recipe bars.

### S7.3 Failure taxonomy

| failure code        | meaning                                                              | family    |
| ------------------- | -------------------------------------------------------------------- | --------- |
| `EXEC_DIVERGE`      | query runs but rows differ from gold                                 | T1, T2    |
| `EXEC_ERROR`        | query fails to execute (syntax/type/fixture mismatch)                | T1, T2    |
| `LABEL_WRONG`       | EXPLAIN bottleneck-class label off                                   | T3        |
| `DDL_DRIFT`         | T4 DDL diff fails (missing table/column/type mismatch)               | T4        |
| `INDEX_MISS`        | T4 missing required index                                            | T4        |
| `NF_VIOLATION`      | T4 schema violates 3NF given gold FD set                             | T4        |
| `REVERSE_DRIFT`     | T5 reverse doesn't restore byte-equal snapshot                       | T5        |
| `LOCK_CLASS_BAD`    | T5 online migration acquires `ACCESS EXCLUSIVE` on large table       | T5        |
| `IDIOM_MISMATCH`    | T6 tree-sitter rule pack v1 didn't match idiom class                 | T6        |
| `RECALL_LOW`        | T7 top-K recall < 0.90 vs ground truth                               | T7        |
| `SANDBOX_TIMEOUT`   | query/migration exceeded sandbox wall-clock                          | T1/T2/T5  |
| `PASS`              | all checks green                                                     | all       |

All non-`PASS` codes count as fail toward aggregate. `SANDBOX_TIMEOUT`
is distinguished from `EXEC_DIVERGE` for diagnostics — the former
indicates a pathologically expensive plan, the latter a wrong answer
fast. The split informs which `db-native` subset to investigate
(plan-aware codegen vs query semantics).

### S7.4 Intent vs surface failure

A response that **refuses** any DB-eval prompt is scored **fail**
(intent failure — DB code is in-domain; emitting the English-
canonical refusal text per D-006 here is mis-calibration). A response
that emits SQL with a syntax error is fail (surface — `EXEC_ERROR`).
Both fail equally; the distinction is diagnostic only.

### S7.5 What doesn't count as a DB-eval failure

- Whitespace / case in non-string SQL keywords.
- Column aliasing when prose underspecifies output name.
- Extra indexes beyond the gold required set (T4 — diagnostic only).
- Engine-accepted quoting variants (`"col"` vs `` `col` `` vs `col`).
- T6 idiom-*style* divergence within the same idiom class (any
  variant the rule pack tags as the gold class qualifies).

## S8 FEEDBACK — upstream channel

Per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md),
DB-eval results route to **two** hexa-codex destinations (matching
hexa-eval's footprint — sister-spec parity):

| forge output                                            | hexa-codex destination                                                                       | PR shape                                                                              | falsifier T4         |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------- |
| Aggregate DB-eval pass rate + per-family + per-engine slice | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)         | cross-cutter contribution: **DB-fidelity axis** added to quality table                | cross-cutter         |
| Per-family failure distribution + adversarial drop + plan-instability robustness | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.II/Mk.III | methodology delta — empirical evidence for "multi-engine eval design" and "plan-instability adversarial test gen" items | meta (wraps F-1..4)  |

DB-eval contributes a **new** quality-scale axis (DB-fidelity) that
none of HumanEval+ / SWE-bench / hexa-eval / 5-NL eval cover. This is
the unique upstream contribution of the spec — the cross-cutter row
is *load-bearing* for hexa-codex's complete quality picture.

**Outbox path** (per `plan-feedback-channel-ops.md §7`):
- `outbox/hexa-codex/quality_scale/<run_id>-db-eval.md`
- `outbox/hexa-codex/eval/<run_id>-db-eval-methodology.md`

The emit script (S9 below) writes the PR draft using the template in
`plan-feedback-channel-ops.md §2`.

### S8.1 Contribution to v1.0.0 forge gate

`docs/code-llm.md §VERIFY upstream feedback contract` requires ≥ 5
PRs landed in hexa-codex. DB-eval contributes **two** of those by
design (quality_scale + eval-methodology). Combined with `hexa-eval`
(2 PRs) and `5-NL eval` (up to 5 PRs) + at least one of
{train_cost / infer_cost} T4, the gate is **comfortably** reachable
from the eval surface alone.

## S9 Tooling

Two scripts (planned; not yet written), both following the existing
`tool/emit_t4.py` shape:

| script                          | reads                                                                | writes                                                                                            | status  |
| ------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------- |
| `tool/run_db_eval.py`           | `tests/db-eval/tasks/*.toml` + candidate endpoint + docker-compose harness | `runs/<id>/db-eval.parquet` + per-task JSON                                                       | PLANNED |
| `tool/emit_db_eval_pr.py`       | `runs/<id>/db-eval.parquet`                                          | `outbox/hexa-codex/{quality_scale,eval}/<id>-db-eval*.md`                                          | PLANNED |

Wiring matches [`plan-feedback-channel-ops.md §3`](plan-feedback-channel-ops.md)
automation triggers — emit on bench-run-complete.

**Container harness.** `run_db_eval.py` wraps a docker-compose stack:
`postgres:16-alpine` (T1-PG + T3 + T4 + T5 + T7 pgvector via
`ankane/pgvector`); SQLite + DuckDB in-process; `redis:7-alpine` (T2
Redis); `neo4j:5-community` (T2 Cypher); FerretDB-style Mongo-shape
sandbox (T2 Mongo — **not** the proprietary binary, per D-014);
`qdrant/qdrant`, `chromadb/chroma`, LanceDB in-process (T7). Each
image is **digest-pinned** in `runs/<id>/engines.lock`.

**Determinism contract.** Both scripts honour `SOURCE_DATE_EPOCH`;
pin engine + fixture + task-set + model SHAs; exit 0 only when
aggregate ≥ 60% AND per-family floors green AND recipe 3-bar named
floors (T1 ≥ 60%, T3 ≥ 70%, T4 ≥ 70%) all green; non-zero with
structured stderr on any miss (CI-friendly).

**Not in scope for v0.1.3.** Actual task TOMLs, gold corpus,
migration scenarios, idiom-class definitions, or runner
implementation — those land v0.1.3+ after D-015 has trained the
`db-native` stage into a candidate model.

---

## Open questions (v0.1.2 → v0.1.3 handoff)

- [ ] **D-NEW-H** — T2 Mongo-shape sandbox: FerretDB (Postgres-backed,
      Apache-2) vs DocumentDB-compatible vs skip Mongo entirely until
      D-014 reconsiders. *Proposed: FerretDB at Mk.II; revisit at Mk.V
      if upstream Mongo licensing changes.*
- [ ] **D-NEW-I** — T3 multi-label gold: a plan can have both seq-scan
      AND nested-loop-blow-up issues. *Proposed: single-best label at
      Mk.II (matches Spider/BIRD); revisit at Mk.III if perturbation
      shows confusion.*
- [ ] **D-NEW-J** — T6 rule pack: does tree-sitter rule pack v1 cover
      SQLAlchemy 2.x async, sqlx query macros, Prisma `select`-vs-
      `include` out of the box? *Proposed: extension v1.1 scoped to
      T6; coordinate with `spec-treesitter-rule-pack.md`.*
- [ ] **D-NEW-K** — T5 lock-class detection: DDL regex vs running
      probe on migration. *Proposed: regex at Mk.II (deterministic,
      covers 90% of traps); upgrade to live PG lock probe at Mk.III
      if false-positive rate > 10%.*
- [ ] **D-NEW-L** — T1 cross-engine: require same NL prompt across
      PG/SQLite/DuckDB variants (forcing dialect literacy on identical
      intent), or allow dialect-specific prompts? *Proposed: same NL
      prompt at Mk.II — precisely the axis Spider/BIRD lacks.*

Resolved decisions referenced by this spec:
- D-013 (no LLM-judge for gold) — closed 2026-05-11
- D-014 (DB tier scope: T1 full / T2 quote / T3 deferred) — closed 2026-05-11
- D-015 (`db-native` stage placement, ~15B tok target) — closed 2026-05-11

---

## Cross-link

- Recipe SSOT: [`../docs/code-llm.md`](../docs/code-llm.md) §EVOLVE database rows (acceptance gate ⑤ — Spider/BIRD ≥ 60% + EXPLAIN ≥ 70% + schema-design ≥ 70%) + §VERIFY DB tool surface (`run_query`, `explain_query`, `apply_migration`, `read_schema`).
- Sister spec: [`spec-hexa-eval.md`](spec-hexa-eval.md) (acceptance gate ③).
- Sister spec: [`spec-five-nl-eval.md`](spec-five-nl-eval.md) (acceptance gate ④).
- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md) (D-013, D-014, D-015).
- DB engine matrix: [`plan-domain-coverage.md §3`](plan-domain-coverage.md) — T1/T2/T3 split + `db-native` stage proposal.
- Feedback channel ops: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md) — upstream PR routing + outbox layout.
- Tree-sitter rule pack canon (T6 idiom matcher): [`spec-treesitter-rule-pack.md`](spec-treesitter-rule-pack.md).
- Methodology canon: [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 EVOLVE Mk.I–Mk.V shape source.
- Tier findings (philosophy stage adjacency for DB idioms): [`tier-a-findings.md`](tier-a-findings.md) · [`tier-e-findings.md`](tier-e-findings.md).
