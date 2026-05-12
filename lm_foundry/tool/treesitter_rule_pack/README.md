# tree-sitter rule pack — v1

Deterministic, native-first idiom auditor for the `code` verb.
Default judge for native/canon-first DPO scoring per decision **D-013**
in `papers/plan-decisions-pending.md`. Full design in
`papers/spec-treesitter-rule-pack.md`.

## What this is

Fifty starter rules (10 per language × 5 langs) that encode anti-idiom
patterns from `papers/tier-e-findings.md` Part 1 as tree-sitter
S-expression queries paired with idiomatic positives. Two use sites:

1. **DPO preference pair mining** — scan `the-stack-v2`, emit
   `(rejected, chosen)` pairs into the `rlhf` substrate.
2. **Inference-time style audit** — score `hexa-codex serve`
   generations; counts feed `tool/emit_t4.py --verb interpret`
   (F-CODEX-4 T4 analog, D-007).

LLM-judge synthesis is **forever-blocked** for v1 to avoid Shumailov
2024 model-collapse — see D-013 rationale.

## Layout

```
treesitter_rule_pack/
├── README.md              this file
├── rules.toml             master index of all 50 rules
├── python/      R-PY-001..010      (10 rules × {anti,positive}.scm)
├── rust/        R-RS-001..010
├── typescript/  R-TS-001..010
├── go/          R-GO-001..010
└── c/           R-C-001..010
```

## Status

- **v1 spec:** locked (this directory + `papers/spec-treesitter-rule-pack.md`).
- **`.scm` queries:** first 3 rules per language are written out as
  query stubs (15 files); remaining 7 per language carry the intended
  query as a comment plus a `STUB - implementation pending v0.1.3 G-BASE`
  marker. Many queries are marked `UNVERIFIED` — node names are not
  yet confirmed against canonical `node-types.json` files; v0.1.3
  G-BASE pass runs each through `tree-sitter parse` to verify.
- **Runner:** not yet written. `tool/treesitter_rule_pack_run.py` is the
  target v0.1.3 deliverable.

## Languages

| lang       | grammar                                | rule range          |
| ---------- | -------------------------------------- | ------------------- |
| Python     | `tree-sitter-python` 0.20+             | `R-PY-001..010`     |
| Rust       | `tree-sitter-rust`                     | `R-RS-001..010`     |
| TypeScript | `tree-sitter-typescript` (TS dialect)  | `R-TS-001..010`     |
| Go         | `tree-sitter-go`                       | `R-GO-001..010`     |
| C          | `tree-sitter-c`                        | `R-C-001..010`      |

## License

MIT, matching the repo root `LICENSE` and the tree-sitter grammar
licenses. Anti-pattern catalogue is derived from public linter docs
(ruff/clippy/golangci/clang-tidy/eslint), which are MIT or Apache-2.

## Reproducing

Once `tool/treesitter_rule_pack_run.py` lands at v0.1.3:

```
python tool/treesitter_rule_pack_run.py \
    --input path/to/file.py --lang python \
    --rules tool/treesitter_rule_pack/rules.toml \
    --out audit.json
```

Audit JSON feeds `emit_t4.py --verb interpret` per
`spec-treesitter-rule-pack.md §7.2`.
