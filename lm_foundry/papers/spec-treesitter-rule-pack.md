# spec — tree-sitter rule pack v1 (code verb)

> **Implementation half of `D-013`.** Native/canon-first DPO scoring uses
> a tree-sitter rule pack as the default deterministic judge; the
> LLM-judge alternative is **forever-blocked** for v1.0 to avoid
> Shumailov 2024 model-collapse. This document specifies the pack
> design, file layout, and the 50 starter rules (10 per language for
> Python, Rust, TypeScript, Go, C).

| field        | value                                                          |
| ------------ | -------------------------------------------------------------- |
| status       | `DESIGN_LOCKED` — implementation begins v0.1.3 G-BASE phase    |
| decision     | D-013 (proposed 2026-05-11 in `plan-decisions-pending.md`)     |
| spec anchor  | `docs/code-llm.md §VERIFY` "style contract"                    |
| anti-corpus  | `papers/tier-e-findings.md` Part 1                             |
| license      | MIT (matches repo `LICENSE`); tree-sitter itself is MIT        |
| dependencies | `tree-sitter-python` 0.20+, `tree-sitter-rust`, `tree-sitter-typescript`, `tree-sitter-go`, `tree-sitter-c` (all MIT) |
| last updated | 2026-05-11                                                     |

---

## §1 Overview

### §1.1 Purpose

The rule pack is a **deterministic, native-first idiom auditor**. Each
rule encodes one anti-idiom pattern from `papers/tier-e-findings.md`
Part 1 as a tree-sitter S-expression query, paired with the idiomatic
positive form. It is consumed in **two places**:

1. **DPO preference pair mining** — at training-data assembly time,
   the pack scans the-stack-v2 corpus, flags every match, and pairs
   the flagged hunk (negative) with the linter-fixed or
   hand-curated idiomatic equivalent (positive). Output feeds
   `rlhf` substrate per `plan-feedback-channel-ops.md §1`.
2. **Inference-time style audit** — at serving time, generated
   code passes through the pack; matches become evidence rows in
   the **F-CODEX-4 T4 motif analog** consumed by
   `outbox/hexa-codex/interpret/` (per
   `tool/emit_t4.py --verb interpret`).

### §1.2 Out of scope

- **LLM-judge synthesis of preference pairs** — forever-blocked
  (D-013 default). Rationale: training on
  model-output-of-model-output triggers the Shumailov collapse
  cycle. The deterministic rule pack is the only judge for v1.0.
- **Semantic equivalence verification** — out of scope. The pack
  identifies surface anti-idioms; behavioural correctness is the
  job of `eval` and `refactor` verbs.
- **Cross-language anti-patterns** ("Java-in-Rust") — defer to
  v0.2 per `tier-e-findings.md` open questions.
- **Custom hexa-lang rules** — defer to v2 (no upstream grammar
  yet).

### §1.3 Design constraints

- **No LLM in the loop.** Every rule is a static query.
- **Permissive licenses only.** Grammars all MIT; the pack itself MIT.
- **Reproducible.** Same input → same flags. No randomness.
- **Cross-validated.** Each rule cites a linter equivalent
  (clippy / ruff / golangci / clang-tidy) so corpus pre-mining
  can confirm yield numbers before training-time activation.
- **No emojis** in queries, comments, or output.

---

## §2 Architecture

### §2.1 Directory layout

```
tool/treesitter_rule_pack/
├── README.md                  — pack overview, ~80 lines
├── rules.toml                 — master index of all 50 rules
├── python/
│   ├── R-PY-001.anti.scm
│   ├── R-PY-001.positive.scm
│   └── ... (10 rules × {anti, positive})
├── rust/        (10 rules)
├── typescript/  (10 rules)
├── go/          (10 rules)
└── c/           (10 rules)
```

Each rule lives in two `.scm` files: `R-XX-NNN.anti.scm` (the
matcher for the negative form) and `R-XX-NNN.positive.scm` (either
a matcher for the positive form, or a textual sketch when the
positive is too varied to query).

### §2.2 Invocation surface

A future `tool/treesitter_rule_pack_run.py` (v0.1.3 G-BASE) loads
`rules.toml`, parses each `.scm`, and runs the queries via
`py-tree-sitter` bindings. Output is JSON per §6.

### §2.3 Composition with other tools

| stage | how the pack participates                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------- |
| DPO   | runs over linter-flagged hunks from `the-stack-v2` to confirm the linter hit and extract a localised AST pair   |
| audit | runs over `hexa-codex serve` generations; counts → `interpret` T4 analog via `tool/emit_t4.py --verb interpret` |
| eval  | runs over eval set baseline + post-finetune; delta → `quality_scale` substrate                                  |

---

## §3 Rule schema (TOML)

Every rule is one entry in `rules.toml` under `[[rule]]`. Fields:

| field                   | type   | required | description                                                                                       |
| ----------------------- | ------ | -------- | ------------------------------------------------------------------------------------------------- |
| `id`                    | string | yes      | stable ID, format `R-<LANG>-<NNN>` (`R-PY-001` … `R-C-010`)                                       |
| `lang`                  | string | yes      | one of `python`, `rust`, `typescript`, `go`, `c`                                                  |
| `anti_name`             | string | yes      | short kebab-case label for the negative pattern                                                   |
| `positive_name`         | string | yes      | short kebab-case label for the idiomatic positive                                                 |
| `anti_query`            | string | yes      | relative path to the `.anti.scm` file                                                             |
| `positive_query`        | string | yes      | relative path to `.positive.scm`, or the literal string `"inline"` if positive is freeform        |
| `severity`              | string | yes      | one of `block` (always rejected), `warn` (DPO-pair only), `info` (audit-only)                     |
| `linter_equivalent`     | string | no       | cross-validation hint (ruff/clippy/golangci/clang-tidy/eslint), if known                          |
| `mining_yield_estimate` | string | yes      | rough Stack v2 pair count: `10K`, `100K`, `1M`                                                    |
| `dpo_pair_template`     | string | yes      | one-line template for the chosen/rejected payload, e.g. `"rejected=hunk; chosen=ruff --fix hunk"` |
| `citation`              | string | no       | back-reference to `tier-e-findings.md` Part 1 row or external standard (CERT, MISRA)              |

### §3.1 Severity semantics

- `block` — generation containing this pattern is automatically
  rejected at audit time (high-severity bugs, e.g. `gets()` in C).
- `warn` — flagged for DPO mining; not a hard reject (most rules).
- `info` — recorded for audit motif-count only; never a reject.

### §3.2 Pair template grammar

`dpo_pair_template` is a free-text microformat hint, NOT executable:

- `rejected=<source>; chosen=<source>` — both sides come from the same
  mining channel (e.g. `rejected=hunk; chosen=ruff --fix hunk`).
- `rejected=stack_match; chosen=curated` — positive is hand-curated
  from rule docs.
- `rejected=hunk_pre; chosen=hunk_post` — diff-driven (PR review).

---

## §4 Languages covered v1

| lang       | grammar pkg                                  | rules | rationale                                                                              |
| ---------- | -------------------------------------------- | ----- | -------------------------------------------------------------------------------------- |
| Python     | `tree-sitter-python` 0.20+                   | 10    | largest Stack v2 share; ruff coverage is exceptional                                   |
| Rust       | `tree-sitter-rust`                           | 10    | clippy restriction lints provide deepest idiom signal                                  |
| TypeScript | `tree-sitter-typescript` (TS dialect)        | 10    | covers the "translated-from-Java" smell explicitly per `code-llm.md §VERIFY`           |
| Go         | `tree-sitter-go`                             | 10    | Effective Go anti-patterns are well-codified; golangci aggregates                      |
| C          | `tree-sitter-c`                              | 10    | CERT + MISRA give legally-defensible severity grounding; clang-tidy covers most rules  |

**Deferred to v2:**
- hexa-lang (no upstream grammar yet — hexa parser will land at S0–S8
  lint stage in `~/core/hexa-lang/SPEC.md §15`).
- Zig (no mature linter for cross-validation — `tier-e-findings.md`
  open question).
- SQL (sqlfluff covers most cases; lower marginal value for v1).
- JavaScript-without-TS (TS rules subsume the high-yield cases).
- C++ (clang-tidy covers; but separate grammar burden — defer).

---

## §5 Rule catalog by language

> **Verification status legend:** queries marked `UNVERIFIED` use
> grammar node names that have not been confirmed against the
> published grammar's `node-types.json`. v0.1.3 G-BASE phase will
> run each query through `tree-sitter parse` against representative
> fixtures and either confirm or rewrite. All such queries still
> exist as `.scm` files with the intent preserved as comments so
> reviewers see direction-of-travel.

### §5.1 Python (`tree-sitter-python`)

| id        | anti-pattern                                | idiomatic positive                                       | linter           | yield  |
| --------- | ------------------------------------------- | -------------------------------------------------------- | ---------------- | ------ |
| R-PY-001  | mutable default arg                         | `None` sentinel + body-local init                        | ruff `B006`      | 100K   |
| R-PY-002  | `for i in range(len(x))`                    | `for i, x in enumerate(xs)`                              | ruff `PLR1736`   | 100K   |
| R-PY-003  | bare `except:` / broad `except: pass`       | `except SpecificError as e: log.exception(e); raise`     | ruff `E722` `BLE001` | 100K |
| R-PY-004  | manual `f = open(...); f.close()`           | `with open(...) as f:`                                   | ruff `SIM115`    | 100K   |
| R-PY-005  | dict-as-namespace literal                   | `@dataclass class Cfg: ...`                              | partial: ruff `FURB` | 1M  |
| R-PY-006  | `s = ""; for x in xs: s += str(x)`          | `"".join(str(x) for x in xs)`                            | perflint `PERF401`/`PERF402` | 10K |
| R-PY-007  | `if len(x) == 0` / `if x == None`           | `if not xs:` / `if x is None:`                           | ruff `E711` `E712` | 100K |
| R-PY-008  | `os.path.join` / `os.path.exists`           | `Path(a) / b`; `p.exists()`                              | ruff `PTH` family | 1M    |
| R-PY-009  | string-typed pseudo-enum                    | `class Mode(StrEnum): FAST = "fast"`                     | partial: `PLR2004` | 10K   |
| R-PY-010  | Java-style getter `def get_x(self): ...`    | `@dataclass` direct attribute                            | (manual)         | 10K    |

### §5.2 Rust (`tree-sitter-rust`)

| id        | anti-pattern                                | idiomatic positive                                       | linter                     | yield |
| --------- | ------------------------------------------- | -------------------------------------------------------- | -------------------------- | ----- |
| R-RS-001  | gratuitous `Box<dyn Trait>` for struct fld  | `struct S<H: Handler> { handler: H }`                    | clippy `boxed_local` (partial) | 10K |
| R-RS-002  | `.unwrap()` on `Result` in lib code         | `?` operator + `Context`                                 | clippy `unwrap_used`       | 1M    |
| R-RS-003  | `let _ = expr` ignoring `Result`            | `expr?;` or `_ = expr.map_err(...)`                      | clippy `let_underscore_must_use` | 100K |
| R-RS-004  | Java-style getter `pub fn get_x(&self)`     | bare field or `pub fn x(&self)` (no `get_`)              | clippy `wrong_self_convention` | 100K |
| R-RS-005  | manual `impl Default { S { x: 0 } }`        | `#[derive(Default)]`                                     | clippy `derivable_impls`   | 10K   |
| R-RS-006  | `match` with single arm + `_ => ()`         | `if let Foo::A = x { ... }`                              | clippy `single_match`      | 100K  |
| R-RS-007  | `String` parameter where `&str` suffices    | `fn f(s: &str)`                                          | clippy `ptr_arg`           | 100K  |
| R-RS-008  | `.clone()` to defeat borrow checker         | borrow `&s` or restructure                               | clippy `redundant_clone`   | 100K  |
| R-RS-009  | `if let Some(x)=opt { x } else { default }` | `opt.unwrap_or(default)`                                 | clippy `manual_unwrap_or`  | 10K   |
| R-RS-010  | factory trait `trait FooFactory { ... }`    | `impl Foo { pub fn new(...) -> Self }`                   | (manual AST `*Factory`)    | 10K   |

### §5.3 TypeScript (`tree-sitter-typescript`)

| id        | anti-pattern                                | idiomatic positive                                       | linter                                  | yield |
| --------- | ------------------------------------------- | -------------------------------------------------------- | --------------------------------------- | ----- |
| R-TS-001  | `any` annotation in non-test code           | `unknown` + narrow, or precise type                      | `@typescript-eslint/no-explicit-any`    | 1M    |
| R-TS-002  | numeric `enum` with reverse mapping         | `type Mode = "fast" \| "slow"`                           | `@typescript-eslint/prefer-literal-enum-member` | 100K |
| R-TS-003  | `as X` cast instead of type guard           | `if (isX(data)) { ... }`                                 | `@typescript-eslint/consistent-type-assertions` | 100K |
| R-TS-004  | `Function` / `Object` ambient types         | precise signature `(x: number) => void`                  | `@typescript-eslint/ban-types`          | 100K  |
| R-TS-005  | `// @ts-ignore` (blanket)                   | `// @ts-expect-error: <reason>`                          | `@typescript-eslint/ban-ts-comment`     | 100K  |
| R-TS-006  | `!` non-null assertion in business code     | narrow via `if (user) {...}`                             | `@typescript-eslint/no-non-null-assertion` | 100K |
| R-TS-007  | floating promise (no await, no `.then`)     | `await someAsync()` or `void someAsync()`                | `@typescript-eslint/no-floating-promises` | 100K |
| R-TS-008  | `class` where module + functions would do   | `export function greet(n: string)`                       | (manual)                                | 10K   |
| R-TS-009  | barrel `export * from "./x"`                | explicit named export                                    | (manual)                                | 10K   |
| R-TS-010  | untagged string \| object union for results | discriminated union with `ok: boolean`                   | (manual)                                | 10K   |

### §5.4 Go (`tree-sitter-go`)

| id       | anti-pattern                                 | idiomatic positive                                       | linter                       | yield |
| -------- | -------------------------------------------- | -------------------------------------------------------- | ---------------------------- | ----- |
| R-GO-001 | `I`-prefixed interface name `IReader`        | `Reader`                                                 | revive `var-naming`; stylecheck `ST1003` | 100K |
| R-GO-002 | ignoring error: `result, _ := f()`           | `result, err := f(); if err != nil { return ... }`       | `errcheck`                   | 1M    |
| R-GO-003 | bare `panic("...")` for runtime branch       | `return fmt.Errorf("...")`                               | revive `panic`               | 100K  |
| R-GO-004 | `return nil, err` without wrap               | `return nil, fmt.Errorf("loading %s: %w", path, err)`    | `wrapcheck`; `errorlint`     | 100K  |
| R-GO-005 | getter named `GetFoo`                        | `Foo`                                                    | revive `getter-return`       | 100K  |
| R-GO-006 | `interface{}` parameter                      | `any` parameter                                          | `predeclared`                | 100K  |
| R-GO-007 | unnecessary `else` after `return`            | flatten: `if x { return a } return b`                    | revive `indent-error-flow`   | 100K  |
| R-GO-008 | preemptive `<Name>Service` interface         | concrete struct first; consumer-declared narrow iface    | `interfacebloat` (partial)   | 10K   |
| R-GO-009 | accepting concrete, returning interface      | accept interface, return concrete struct                 | (manual)                     | 10K   |
| R-GO-010 | init-required struct (zero-value broken)     | zero value usable (e.g. `var b bytes.Buffer`)            | (manual)                     | 10K   |

### §5.5 C (`tree-sitter-c`)

| id      | anti-pattern                                 | idiomatic positive                                       | linter                                   | yield |
| ------- | -------------------------------------------- | -------------------------------------------------------- | ---------------------------------------- | ----- |
| R-C-001 | `strcpy(dst, src)`                           | `strlcpy(dst, src, sizeof dst)` or `snprintf`            | clang-tidy `cert-str34-c`; `bugprone-unsafe-functions` | 100K |
| R-C-002 | `gets(buf)`                                  | `fgets(buf, sizeof buf, stdin)`                          | CERT MSC24-C                             | 10K   |
| R-C-003 | `p = malloc(n); p->x = ...;` no NULL check   | `p = malloc(n); if (!p) return ERR;`                     | clang-analyzer `unix.Malloc`             | 100K  |
| R-C-004 | `sizeof(p)` on a pointer (vs array)          | `sizeof(arr)` only on arrays; pass length explicitly     | clang-tidy `bugprone-sizeof-expression`  | 10K   |
| R-C-005 | `for (int i = 0; i < strlen(s); ++i)`        | hoist `size_t len = strlen(s);` outside loop             | clang-tidy `bugprone-narrowing-conversions` (partial) | 100K |
| R-C-006 | macro-as-function unparenthesised args       | inline function, or `#define SQ(x) ((x) * (x))`          | clang-tidy `bugprone-macro-parentheses`  | 100K  |
| R-C-007 | ignoring `fread` / `write` return value      | check `== n` or against `EOF`                            | clang-tidy `bugprone-unused-return-value` | 100K |
| R-C-008 | upward `goto` (loop emulation)               | structured loop; reserve `goto cleanup` for forward only | CERT MEM12-C (manual)                    | 10K   |
| R-C-009 | `memcpy` between incompatible types          | typed accessor / `memcpy_s` with size check              | MISRA C2012 21.15                        | 10K   |
| R-C-010 | signed-int overflow assumed wrap             | use `unsigned` or pre-add overflow check                 | UB sanitiser; CERT INT32-C               | 10K   |

### §5.6 Yield rollup

Summed mining-yield estimates across all 50 rules (order-of-magnitude):
roughly **9M** preference pairs from `the-stack-v2` if every rule fires
at its rough estimate. Realistic post-dedup yield after cross-rule
overlap and license-filter is **~2-4M pairs** — comfortably above the
3M target in `tier-e-findings.md` Part 3.

---

## §6 Composition pipeline

### §6.1 Training-time (DPO assembly)

```
the-stack-v2 (parquet shards)
  → split by lang
  → for each lang, for each rule in pack:
      run tree-sitter query (anti)
      for each match:
        - emit (rejected = matched hunk)
        - if positive_query is a query: search nearby file for matches
        - else: emit (chosen = linter --fix applied to the file)
        - skip if linter fix is unsafe (per ruff/clippy safety tier)
  → dedupe by (lang, rule_id, sha256(rejected_hunk))
  → write to rlhf/dpo_pairs/<lang>/<rule_id>.jsonl
```

Each `.jsonl` row matches the schema from
`tier-e-findings.md` Part 3 "Pairing format for DPO":

```json
{
  "context": "rule rationale text",
  "chosen":  "idiomatic positive code",
  "rejected": "anti-idiomatic negative code",
  "source":  "treesitter:R-PY-001+ruff:B006",
  "lang":    "python",
  "applicability": "safe"
}
```

### §6.2 Inference-time (audit)

```
hexa-codex serve generates code
  → tool/treesitter_rule_pack_run.py --input <code> --lang <lang>
  → output JSON:
      {
        "lang": "...",
        "summary": {"total_matches": N, "block": k, "warn": m, "info": p},
        "matches": [
          {"rule_id": "R-PY-001", "severity": "warn",
           "row": 12, "col": 4, "node_text": "...", "rule_anti_name": "...",
           "positive_hint": "rule R-PY-001 positive: None-sentinel"}
        ],
        "version": "treesitter_rule_pack_v1"
      }
```

This JSON feeds `tool/emit_t4.py --verb interpret` as the `measured`
payload (see `emit_t4.py` `load_measured`):

| emit_t4 `interpret` field         | derived from                                            |
| --------------------------------- | ------------------------------------------------------- |
| `native_idiom_correct_count`      | total generations with 0 matches                        |
| `translated_pattern_count`        | total matches across all generations                    |
| `ratio`                           | `correct / (correct + translated)`                      |
| `tree_sitter_rule_pack_version`   | literal `"v1"` (this spec) — bump on rule-set change    |

### §6.3 Output JSON schema (audit mode)

```json
{
  "$schema": "treesitter_rule_pack_v1",
  "lang": "python|rust|typescript|go|c",
  "input_path": "string",
  "summary": {
    "total_matches": "int",
    "by_severity": {"block": "int", "warn": "int", "info": "int"},
    "by_rule": {"R-XX-NNN": "int"}
  },
  "matches": [
    {
      "rule_id": "string",
      "severity": "block|warn|info",
      "row": "int", "col": "int",
      "node_text": "string (<= 256 chars)",
      "positive_hint": "string"
    }
  ],
  "version": "v1",
  "elapsed_ms": "number"
}
```

---

## §7 Reproducibility

### §7.1 Standalone run (v0.1.3 G-BASE target)

```
python tool/treesitter_rule_pack_run.py \
    --input path/to/file.py \
    --lang python \
    --rules tool/treesitter_rule_pack/rules.toml \
    --out out.json
```

The runner is **stateless**: same input bytes + same pack version =
same JSON. Pack version pinned in `rules.toml` top-level `pack_version`
field (set to `"v1"`).

### §7.2 Feeding `emit_t4.py --verb interpret`

```
python tool/treesitter_rule_pack_run.py --input generated/ --lang python --out interpret_run.json
python tool/emit_t4.py --verb interpret --run-id 2026-05-xx-aaa \
    --input interpret_run.json --model qwen2.5-coder-7b-q5_k_m \
    --compute "M4 Mini 16GB" --corpus-hash "datasets.toml@<sha>" \
    --tokenizer "qwen-base + hexa-ext@<sha>"
```

This emits an outbox draft at
`outbox/hexa-codex/interpret/<run_id>.md` per the F-CODEX-4 T4
analog convention (D-007).

### §7.3 Cross-validation against linters

For each rule with a `linter_equivalent` field set, the v0.1.3
verification pass MUST confirm: a representative anti-fixture
flagged by the linter is ALSO matched by the tree-sitter query
(precision check). Misses are documented; false positives are
rewritten or downgraded to `info`.

### §7.4 Determinism contract

- Grammar versions pinned via `tree-sitter`'s `package.json`
  (`tree-sitter-python@^0.20.4`, etc.) — recorded in
  `rules.toml` `[grammars]` table at v0.1.3 implementation time.
- Query files are static text; their SHA-256 is recorded in
  `rules.toml` `[rule.checksum]` at activation time.
- No locale/timezone dependence (queries are pure AST).

---

## §8 Forward path

| version | what changes                                                                            |
| ------- | --------------------------------------------------------------------------------------- |
| v1.0    | this spec — 50 rules, 5 langs, deterministic only                                       |
| v1.1    | verify all `UNVERIFIED` queries; add ≥1 fixture file per rule                           |
| v1.2    | add Zig + SQL (10 each) once linter equivalents identified                              |
| v1.3    | add hexa-lang (10 rules) once hexa-lang tree-sitter grammar published                   |
| v2.0    | optional LLM-judge layer **only** if Shumailov-collapse mitigations land upstream       |

---

## §9 Cross-links

- Anti-corpus source: [`papers/tier-e-findings.md`](./tier-e-findings.md)
- Spec contract: [`docs/code-llm.md §VERIFY`](../docs/code-llm.md#verify--serving-contract)
- Decision record: [`papers/plan-decisions-pending.md`](./plan-decisions-pending.md) D-013
- Feedback channel mapping: [`papers/plan-feedback-channel-ops.md`](./plan-feedback-channel-ops.md) §1 "Native-first / 2026-canon-first audit"
- Runner emitter (downstream): [`tool/emit_t4.py`](../tool/emit_t4.py) `--verb interpret`
- Implementation home: [`tool/treesitter_rule_pack/`](../tool/treesitter_rule_pack/)

---

## §10 Open verification items (v0.1.3 G-BASE pass)

- [ ] confirm `tree-sitter-python` node names: `function_definition`, `parameters`, `default_parameter`, `for_statement`, `try_statement`, `except_clause`, `with_statement`, `subscript`, `call`, `attribute`
- [ ] confirm `tree-sitter-rust` node names: `generic_type`, `dynamic_type`, `match_expression`, `match_arm`, `unit_expression`, `call_expression`, `reference_type`, `let_declaration`, `type_arguments`
- [ ] confirm `tree-sitter-typescript` node names: `type_assertion`, `as_expression`, `any` keyword node, `non_null_expression`, `predefined_type`, `enum_declaration`
- [ ] confirm `tree-sitter-go` node names: `interface_type`, `assignment_statement`, `blank_identifier`, `method_declaration`, `type_identifier`, `if_statement`
- [ ] confirm `tree-sitter-c` node names: `call_expression`, `pointer_expression`, `sizeof_expression`, `for_statement`, `preproc_function_def`, `goto_statement`, `cast_expression`
- [ ] for each rule with `UNVERIFIED` marker: parse representative fixture and either confirm node names or rewrite
- [ ] precision/recall report against linter equivalents (cross-validation §7.3)
