-- @canonical: canon@0c65155a:formal/lean4/N6/InvariantLattice/Sigma.lean
-- @extracted: 2026-05-07
-- @md5_at_extraction: 77da6c22ccd0d2d27782e1fdd26afe42
-- @absorbed_into: hexa-codex (P3 formal substrate — σ definition for SigmaLatticeCard)
-- N6.InvariantLattice.Sigma
--
-- Canonical definition of the σ (divisor-sum) function used by the n=6
-- invariant-lattice axis. Stub layer: definition is here only so that
-- `SigmaLatticeCard.lean` can name `sigma 6 = 12` without dangling
-- references; full proof bodies remain `sorry` per stub-layer policy
-- (raw_91 honest C3 disclosure: structural skeleton only).

namespace N6
namespace InvariantLattice

/-- Divisor sum σ(n) = Σ_{d | n} d. Naive enumerative form. -/
def sigma (n : Nat) : Nat :=
  (List.range (n + 1)).filter (fun d => d > 0 ∧ n % d = 0) |>.foldl (· + ·) 0

end InvariantLattice
end N6
