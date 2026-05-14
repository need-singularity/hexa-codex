# hexa-codex v1.0.0 — Release Notes

**Release date**: 2026-05-06
**Provenance**: extracted from `canon@c0f1f570`
**License**: MIT

---

## Highlights

- **17-verb AI knowledge substrate** organized in **4 groups**
  (safety + economics + ops + substrate) lands as a standalone
  `dancinlab/hexa-codex` repo.
- Each verb is the unchanged closed-form spec `.md` from
  `canon/domains/cognitive/`, preserved verbatim under a
  group-relevant directory name (`alignment/`, `train_cost/`, etc).
- Placeholder CLI dispatcher (`cli/hexa-codex.hexa`) routes by verb and
  prints spec path + a 20-line head; `selftest` confirms 17/17 specs on disk.
- README ships a 4-group verb table for navigation and an honest §Status
  caveat that working `.hexa` falsifier sandboxes are TBD.

## 4-group verb count

| Group        | Verb count | Verbs                                                                  |
|--------------|:----------:|------------------------------------------------------------------------|
| safety       | 6          | alignment, safety, welfare, adversarial, consciousness, interpret      |
| economics    | 3          | train_cost, infer_cost, quality_scale                                  |
| ops          | 4          | deploy, enterprise, agent_serving, eval                                |
| substrate    | 4          | multimodal, rlhf, cog_arch, causal                                     |
| **total**    | **17**     |                                                                        |

## Status (SPEC_CATALOG_ONLY)

What ships at v1.0.0:

- 17 verb spec `.md` files in their group-named directories.
- `hexa-codex list` — 4-group verb table.
- `hexa-codex <verb>` — spec path + first 20 lines.
- `hexa-codex selftest` — 17-verb presence sweep, emits
  `__HEXA_CODEX_SELFTEST__ PASS` when 17/17 are on disk.

What does **not** ship:

- Per-verb falsifier sandboxes (no ODE / probe / fitter at v1.0).
- Numerical empirical paths (no python deps; pure spec library).
- Production training, serving, or RLHF labeling pipelines.
- Any regulatory, alignment, or capability claim — preregister only.

## Cross-link

- `dancinlab/anima` — consciousness / soul cousin.
- `dancinlab/hexa-brain` — BCI sister.
- `dancinlab/honesty-monitor` — AI honesty falsifier sister.
- `dancinlab/hexa-bio` — molecular HEXA-family sister (4 verb).


1. `SPEC_CATALOG_ONLY` — 0/17 verbs ship a working `.hexa` module at v1.0.
2. Falsifier deadlines + thresholds inside each verb spec are
   **initial-guess** values; revision tracked alongside per-verb sandboxes.
3. The 4-group taxonomy is a **librarian's grouping** — it does NOT imply
   any verb-internal cross-validation or shared lattice invariant.
4. No model training, inference SaaS, RLHF labeling pipeline, or
   regulatory claim is made — write-side spec library only.

## Next

- Wire the first per-verb falsifier sandbox (likely `interpret` or
  `eval`, both have the cleanest measurement protocols upstream).
- Surface a `hexa-codex audit` cross-check against
  `canon@c0f1f570` to detect drift in the upstream specs.
