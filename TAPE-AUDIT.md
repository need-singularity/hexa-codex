# TAPE-AUDIT — hexa-codex

17-verb cognitive substrate (alignment / adversarial / agent_serving / causal / cog_arch / consciousness / deploy / enterprise / eval / formal / interpret / multimodal / quality_scale / rlhf / safety / train_cost / infer_cost / welfare / cognitive-social-psychology / discovery / experiments / reality-map / t4_empirical / lm_foundry). Parent of `hexa-mind`'s 7-verb rollup.

## A. Audit-class ledgers (cargo / migration candidates)

- **`state/markers/`** — many `*.marker` files (`calc_*`, `numerics_*_parity_*`, `numerics_*_solver_*`, `test_*`, `lattice_check_*`, `cross_doc_*`). Per-verifier-run cargo. Direct `state/markers.tape` migration; the `numerics_*_parity_*` set is exactly the per-verifier-tick stream `.tape` is designed for.
- **`state/hexa_codex_cli.log`** — single CLI log. Light.
- **`verify/cross_doc_audit.hexa`**, **`verify/group_audit.py`** — audit programs. Outputs today are markers in `state/markers/`; tape-shaped target = `verify.tape`.
- **`t4_empirical/2026-05-11-stack-v1-license-audit.md`** — per-license-audit doc; tape-shape if recurring.
- No `*.jsonl` ledgers under `state/` (a notable gap given the 17-verb scope — verifiers currently emit markers + logs, not structured event streams).

## B. Identity surface

Medium. Substrate identity = verbs catalog + lattice constants encoded in `hexa.toml` (21 KB — substantial) + `LATTICE_POLICY.md` + `IMPORTED_FROM_CANON.md` (canon provenance: extracted from canon ref). Could become `hexa-codex/identity.tape` per release.

## C. Domain.md files

`UPPERCASE.md` convention partial: `AGENTS.md`, `CHANGELOG.md`, `IMPORTED_FROM_CANON.md`, `LATTICE_POLICY.md`, `LIMIT_BREAKTHROUGH.md`, `README.md`, `RELEASE_NOTES_v1.0.0.md` at top, but the **verb-named subtrees themselves substitute for per-verb domain.md** (`adversarial/`, `alignment/`, `causal/`, `consciousness/`, `cog_arch/`, ... — 17+ subtrees). Each subtree could host a `<verb>.tape` sibling.

## D. Per-run / per-event history surfaces

`experiments/` (per-experiment runs), `discovery/` (8 subdirs — discovery-loop ticks), `t4_empirical/` (per-empirical-study date-stamped), `verify/` (per-verifier outputs). All event-stream-shaped → `.tape` per experiment / per discovery cycle.

## E. Promotion candidates

- **n6 atoms** — every numerics parity/solver pass is a quantitative claim ratified vs lattice. `t4_empirical/` empirical anchors. Large promotion target.
- **hxc wire** — N/A at this layer (substrate spec, not byte streams).
- **n12 cells** — verify pass/fail × verb × version × numerics-class is the canonical codex n12 cube.

**Verdict: HEAVY** (5+ tape surfaces — markers, audit programs, verb-subtree tapes, experiments/, discovery/, t4_empirical/, identity).
