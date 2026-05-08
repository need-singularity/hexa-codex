# 🔬 hexa-codex / formal — formal substrate (Lean 4)

Mechanically-checked proofs of the n=6 lattice identities that underpin
hexa-codex's 17-verb / 4-group taxonomy. Absorbed from
`n6-architecture/formal/lean4/N6/InvariantLattice/` (provenance commit
`0c65155a`, extracted 2026-05-07).

## What is proven

| File | Theorem | Status | Pairs with |
|------|---------|--------|------------|
| [`lean4/N6/InvariantLattice/Sigma.lean`](lean4/N6/InvariantLattice/Sigma.lean) | `def sigma (n : Nat) : Nat` — divisor sum σ(n) computable definition | DEFINITION (no theorem) | consumer of `SigmaLatticeCard.lean` |
| [`lean4/N6/InvariantLattice/SigmaLatticeCard.lean`](lean4/N6/InvariantLattice/SigmaLatticeCard.lean) | `theorem sigma_lattice_card : sigma 6 = 12 := rfl` | **PROVEN** (no `sorry`) — F-CL-FORMAL-1 | F-CODEX-1..4 arithmetic floors, `verify/n6_arithmetic.py`, `verify/falsifier_check.py` |

## Why this matters for hexa-codex

Every F-CODEX-N falsifier in `.roadmap.hexa_codex §A.4` is parameterized
by σ(6), τ(6), φ(6), or J₂ — all derived from the σ-invariant. The
Lean 4 proof in `SigmaLatticeCard.lean` is a **kernel-checked anchor**:

- F-CODEX-1: training_cost ∝ N^**24** ← σ(6)·φ(6) = 24 (proof: rfl via `sigma 6 = 12` × 2)
- F-CODEX-2: inference_cost ∝ context^**4** ← τ(6) = #divisors(6) = 4 (corollary)
- F-CODEX-3: alignment_score = mean over **12** axes ← σ(6) = 12 (this proof)
- F-CODEX-4: interpret_motifs = σ−φ = **10** ← σ(6) − φ(6) = 10 (corollary)

The .hexa-native runnable surface cross-checks the same identity at
runtime — `verify/lattice_check.hexa` (24 algebraic invariants),
`verify/numerics_lattice_arithmetic.hexa` (math_pure stability floor),
and the cross-cutter `verify/numerics_cross_pillar.hexa` (which feeds
σ·φ = n·τ = J₂ = 24 into all four pillars in one pass). The Lean proof
gives the **mathematical bedrock** those .hexa runtime checks are
faithful to.

## How to verify

```bash
# kernel-check the Lean 4 proof (requires lake / Lean 4 toolchain):
cd /path/to/lean4-project-with-N6-imports
lake build N6.InvariantLattice.SigmaLatticeCard
# expected: 0 errors, 0 sorries
```

The Lean 4 toolchain is **not required** for hexa-codex's runnable
verification surface — the .hexa scripts run on `~/.hx/packages/hexa/hexa.real`
with `RESOURCE_LOCAL_HEXA=1` and the `math_pure` runtime (no external
deps). The formal proof is a **reference annex** that mirrors the
runtime claims emitted by `verify/lattice_check.hexa` and
`verify/numerics_lattice_arithmetic.hexa`.

## Provenance + sister-repo relationship

`SigmaLatticeCard.lean` is also referenced by `hexa-bio` (per its
preamble: *"Pairs with: hexa-bio/weave/spec/lean4_mechanical_layer_v0.scaffold.md
§2.1"*). hexa-codex absorbs the proof file as a **read-only mirror** —
the SSOT remains `n6-architecture/formal/lean4/`. Updates flow upstream
first.
