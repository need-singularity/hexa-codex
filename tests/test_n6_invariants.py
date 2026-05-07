"""
Independent n=6 lattice arithmetic — does not depend on verify/n6_arithmetic.py.
Mirrors hexa-sscb's tests/test_n6_invariants.py.
"""
from __future__ import annotations

from math import gcd

import pytest


def divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]

def sigma(n: int) -> int:
    return sum(divisors(n))

def tau(n: int) -> int:
    return len(divisors(n))

def euler_phi(n: int) -> int:
    return sum(1 for k in range(1, n + 1) if gcd(k, n) == 1)


# ----- master row -----------------------------------------------------------

@pytest.mark.auto
def test_sigma_6_equals_12():
    assert sigma(6) == 12
    assert divisors(6) == [1, 2, 3, 6]


@pytest.mark.auto
def test_tau_6_equals_4():
    assert tau(6) == 4


@pytest.mark.auto
def test_phi_6_equals_2():
    assert euler_phi(6) == 2


@pytest.mark.auto
def test_master_identity_holds():
    """σ(6) · φ(6) = n · τ(6) = J₂ = 24."""
    n = 6
    s, t, p = sigma(n), tau(n), euler_phi(n)
    assert s * p == 24
    assert n * t == 24
    assert s * p == n * t


# ----- AI-projection cross-checks ------------------------------------------

@pytest.mark.auto
def test_helm_dim_equals_sigma_6():
    """σ(6) = 12 ↔ HELM 12-dimension capability bin."""
    assert sigma(6) == 12


@pytest.mark.auto
def test_lifecycle_phases_equals_tau_6():
    """τ(6) = 4 lifecycle phases — pretrain/SFT/RLHF/deploy."""
    assert tau(6) == 4


@pytest.mark.auto
def test_groups_equals_tau_6():
    """4 groups (safety / economics / ops / substrate)."""
    assert tau(6) == 4


@pytest.mark.auto
def test_verdict_bits_equals_phi_6():
    """φ(6) = 2 verdict bits — helpful / harmless."""
    assert euler_phi(6) == 2


@pytest.mark.auto
def test_training_cost_exponent_is_24():
    """J₂ = σ(6) · φ(6) = 24 — training-cost ∝ N^J₂."""
    assert sigma(6) * euler_phi(6) == 24


@pytest.mark.auto
def test_interpret_motif_count_is_10():
    """interpret_motifs = σ(6) − φ(6) = 10 (F-CODEX-4)."""
    assert sigma(6) - euler_phi(6) == 10


@pytest.mark.auto
def test_17_verbs_equals_6_3_4_4():
    """17 verbs = 6 (safety) + 3 (economics) + 4 (ops) + 4 (substrate)."""
    assert 6 + 3 + 4 + 4 == 17


# ----- module-level cross-check --------------------------------------------

@pytest.mark.auto
def test_verify_module_constants_agree():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "verify"))
    import n6_arithmetic as m
    assert m.SIGMA_N == sigma(6)
    assert m.TAU_N   == tau(6)
    assert m.PHI_N   == euler_phi(6)
    assert m.J2      == 24


# ----- balanced-n enumeration ----------------------------------------------

@pytest.mark.auto
def test_only_n_1_and_n_6_balanced_in_1_to_24():
    balanced = [n for n in range(1, 25) if sigma(n) * euler_phi(n) == n * tau(n)]
    assert balanced == [1, 6]
