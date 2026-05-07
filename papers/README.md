# 📄 hexa-codex / papers — reference annexes

Reference papers absorbed from `n6-architecture/papers/` (provenance commit
`0c65155a`, extracted 2026-05-07). Each file carries a `@canonical`
header so its upstream coordinate is recoverable.

| Paper | Concern | Verb-link |
|-------|---------|-----------|
| [`n6-ai-17-techniques-experimental-paper.md`](n6-ai-17-techniques-experimental-paper.md) | Maps **hexa-codex's exact 17 verbs** into n=6 σ·φ=n·τ=24 coordinate space (atlas.n6 192/192 EXACT) | direct frame for all 17 verbs |
| [`n6-ai-techniques-68-integrated-paper.md`](n6-ai-techniques-68-integrated-paper.md) | Wider **68-technique** AI atlas; situates the 17 verbs inside the broader landscape (atlas.n6 0/24 EXACT for the 68-extension) | superset reference for cross-verb context |

## Why these are reference annexes (not new verbs)

Each paper is a **mapping document** — it does NOT introduce new verb specs
or new falsifiers. It coordinatizes the existing 17 verbs (and 51 adjacent
techniques) onto the n=6 lattice already declared by `.roadmap.hexa_codex`
§A.1. Treat them as authoritative cross-references, not as primary spec
sources.

## Falsifier-floor relationship

The arithmetic floors checked by `verify/falsifier_check.py` (F-CODEX-1..4)
are arithmetic *consequences* of the same σ·φ=n·τ=24 identity these
papers spell out in full. So:

- A failure in `verify/falsifier_check.py` ⇒ either (a) Python arithmetic
  drift, or (b) these papers contain an error in the lattice mapping.
- A change in either paper that revises the lattice mapping ⇒ requires
  re-running `verify/cli.py all` to confirm the floors still pass.

## DEFER candidates (not yet absorbed)

The following papers from the same upstream `n6-architecture/papers/`
directory are tracked in GitHub issues for later decision (consciousness
falsifier addition, ai-ethics-governance overlap review,
governance-safety-urban scope review).
