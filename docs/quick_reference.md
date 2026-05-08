# hexa-codex operator quick reference

One-pager of the canonical commands. For deeper context, see
`docs/numerics_methodology.md` (closure-depth narrative) and
`docs/closure_status.md` (per-pillar closure snapshot).

---

## §1 The single sat-1 verdict

```bash
make -C build sat1
# (or directly:)
RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT="$PWD" \
    ~/.hx/packages/hexa/hexa.real run verify/saturation_check.hexa
```

PASS iff every F-CODEX-1..4 carries `T1 + T2 + T3 ✓` AND the 4
cross-cutters are present. Emits:

```
__HEXA_CODEX_RSC_SATURATED__ STOP        # recipe §7.3 self-stop signal
__HEXA_CODEX_SATURATION_CHECK__ PASS     # check sentinel
```

---

## §2 Component runs (debugging)

| Goal                                    | Command                                                            |
|:----------------------------------------|:-------------------------------------------------------------------|
| Per-pillar closure tracker              | `hexa-codex verify falsifier-check`                                |
| Recipe §4 lint over numerics_*          | `hexa-codex verify lint-numerics`                                  |
| n=6 lattice algebraic floor             | `hexa-codex verify lattice`                                        |
| Cross-document anchor audit             | `hexa-codex verify cross-doc`                                      |
| Cross-pillar T2 cross-cutter            | `hexa-codex verify numerics-cross-pillar`                          |
| math_pure stability floor               | `hexa-codex verify numerics-lattice-arithmetic`                    |

---

## §3 Per-falsifier layer runs

Replace `<pillar>` with `train_cost` / `infer_cost` / `alignment` /
`interpret`.

| Tier           | Command                                                |
|:---------------|:-------------------------------------------------------|
| T1 (calc)      | `hexa-codex verify calc-<pillar>`                      |
| T2 (numerics)  | `hexa-codex verify numerics-<pillar>`                  |
| T2 (solver)    | `hexa-codex verify numerics-<pillar>-solver`           |
| T3 (parity)    | `hexa-codex verify numerics-<pillar>-parity`           |

Direct invocation pattern (bypasses CLI dispatch):

```bash
RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT="$PWD" \
    ~/.hx/packages/hexa/hexa.real run verify/<file>.hexa
```

---

## §4 Regression suites

| Goal                                    | Command                                                            |
|:----------------------------------------|:-------------------------------------------------------------------|
| Full 24-wrapper .hexa regression        | `make -C build test-hexa-all`                                      |
| Legacy Python verifiers (parallel CI)   | `make -C build verify`                                             |
| Pytest auto suite (83 cases, fast)      | `make -C build test`                                               |
| Pytest hexa marker (requires hexa-lang) | `make -C build test-hexa`                                          |
| Selftest (17-verb spec presence)        | `make -C build selftest`                                           |
| Everything (all of the above + sat1)    | `make -C build everything`                                         |

---

## §5 PDF (per-verb, on-demand)

```bash
make -C build pdf VERB=alignment   # → build/out/alignment.pdf via pandoc
```

Uses `verify/verb_query.py` to look up the spec path; no hard-coded
verb→path mapping in the Makefile.

---

## §6 Environment notes

- `RESOURCE_LOCAL_HEXA=1` — required env for `hexa.real` to bypass the
  `~/.hx/bin/hexa` remote-routing wrapper that ships with the resource
  toolkit. Without this env, `hexa run` is unconditionally routed to
  `hexa-r ubu-1` (TCP queue), which has no hexa interpreter on the
  remote machine; the wrapper returns exit 0 with empty stdout (silent
  fail mode).
- `HEXA_CODEX_ROOT` — required by every script for cross-process
  resolution; defaults to `$PWD` for local runs.
- The build/Makefile sets both env vars via `HEXA_LOCAL_ENV` so
  `make -C build sat1` etc. work without manual exports.

---

## §7 Recipe pointers

| Topic                                        | Source                                                               |
|:---------------------------------------------|:----------------------------------------------------------------------|
| Closure-depth recipe (SSOT)                  | `~/core/bedrock/docs/runnable_surface_recipe.md`                      |
| Recipe §3 closure ladder (T1/T2/T3)          | runnable_surface_recipe.md §3                                         |
| Recipe §4 invariants 1-5 (math_pure / etc.)  | runnable_surface_recipe.md §4                                         |
| Recipe §7.2 stop conditions (sat-1 / sat-2)  | runnable_surface_recipe.md §7.2                                       |
| Recipe §7.3 saturation self-stop signal      | runnable_surface_recipe.md §7.3                                       |
| Recipe §7.4 priority chunk order             | runnable_surface_recipe.md §7.4                                       |
| Recipe §9 T4 (live hardware / Stage-1+)      | runnable_surface_recipe.md §9                                         |
| In-repo narrative                            | `docs/numerics_methodology.md`                                        |
| Per-pillar closure snapshot                  | `docs/closure_status.md`                                              |
