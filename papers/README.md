# 📄 hexa-codex / papers — reference annexes

Reference papers absorbed from `canon/papers/` (provenance commit
`0c65155a`, extracted 2026-05-07). Each file carries a `@canonical`
header so its upstream coordinate is recoverable.

| Paper | Concern | Verb-link | Maturity |
|-------|---------|-----------|----------|
| [`n6-ai-17-techniques-experimental-paper.md`](n6-ai-17-techniques-experimental-paper.md) | Maps **hexa-codex's exact 17 verbs** into n=6 σ·φ=n·τ=24 coordinate space | direct frame for all 17 verbs | atlas.n6 **192/192 EXACT** |
| [`n6-ai-techniques-68-integrated-paper.md`](n6-ai-techniques-68-integrated-paper.md) | Wider **68-technique** AI atlas; situates the 17 verbs inside the broader landscape | superset reference for cross-verb context | atlas.n6 0/24 EXACT (extension) |
| [`n6-ai-ethics-governance-paper.md`](n6-ai-ethics-governance-paper.md) | **AI ethics + governance** σ·φ=24 overlay (P4) | SAFETY-group annex (no new verb) | atlas.n6 **0/24 EXACT, MATURITY=LOW** |
| [`n6-governance-safety-urban-paper.md`](n6-governance-safety-urban-paper.md) | **Governance + safety + urban planning** σ·φ=24 overlay (P5) | SAFETY-group annex (no new verb) | atlas.n6 **58/58 EXACT, MATURITY=HIGH** |

## Why these are reference annexes (not new verbs)

Each paper is a **mapping document** — it does NOT introduce new verb specs
or new falsifiers. It coordinatizes the existing 17 verbs (and 51 adjacent
techniques) onto the n=6 lattice already declared by `.roadmap.hexa_codex`
§A.1. Treat them as authoritative cross-references, not as primary spec
sources.

## Falsifier-floor relationship

Recipe §3 defines a 3-tier ladder per falsifier:

  - **T1** = `calc_<pillar>.hexa` (algebraic identity)
  - **T2** = `numerics_<pillar>.hexa` ∧ `numerics_<pillar>_solver.hexa`
    (pure-math closed-form re-derivation — internal consistency)
  - **T3** = `numerics_<pillar>_parity.hexa` (archival empirical
    contact via published-ref comparison — these papers + their
    upstream Chinchilla / GPT-3 / Llama-2 / PaLM / HELM-Core / Olsson
    / Cunningham / Bricken / Anthropic-2024 anchors)

Plus cross-cutters (`lattice_check.hexa`, `cross_doc_audit.hexa`,
`numerics_cross_pillar.hexa`, `numerics_lattice_arithmetic.hexa`) and
the closure tracker meta (`falsifier_check.hexa`).

All four F-CODEX-1..4 reach `closure_pct = 100%` (3/3 tiers) — every
checked floor is an arithmetic *consequence* of the same σ·φ=n·τ=24
identity these papers spell out in full. So:

- A failure in any T2 floor ⇒ either (a) `math_pure` drift (caught
  directly by `numerics_lattice_arithmetic.hexa`), or (b) these papers
  contain an error in the lattice mapping.
- A failure in any T3 floor ⇒ either (a) the published-ref number
  was transcribed wrong, or (b) the closed-form prediction is
  off-spec versus the field — both are calibration / archival
  contact issues that pure-math T2 cannot see.
- A change in either paper that revises the lattice mapping ⇒
  requires re-running `verify/saturation_check.hexa` to confirm
  the recipe §7.2 sat-1 = 100% closure still holds.

## Per-verb deep-dive sub-files

Some verbs receive long-form companion documents that are too dense for
their seed spec. These live in the verb's directory rather than `papers/`:

| Verb | Deep-dive file | Concern |
|------|----------------|---------|
| `consciousness` | [`consciousness/measurement-protocol.md`](../consciousness/measurement-protocol.md) | BT-19 α_IIT·α_GWT=1 reproducible EEG/fMRI protocol |
| `consciousness` | [`consciousness/red-team-failure.md`](../consciousness/red-team-failure.md) | BT-19 red-team refutation (verdict MISS, [7?]→[5] downgrade) — falsifier-discipline-in-action |

The pattern: when the upstream `canon/papers/` ships
verb-specific protocols or refutation reports, hexa-codex absorbs them
**inside the verb's directory** (not under `papers/`) so a single
`hexa-codex consciousness` invocation can route to all consciousness
material.
