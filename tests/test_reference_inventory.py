"""
Tests for verify/reference_inventory.py — papers/ + formal/ absorption audit.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "verify"


REFERENCE_FILES = [
    "papers/n6-ai-17-techniques-experimental-paper.md",
    "papers/n6-ai-techniques-68-integrated-paper.md",
    "formal/lean4/N6/InvariantLattice/Sigma.lean",
    "formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean",
]


@pytest.mark.auto
@pytest.mark.parametrize("relpath", REFERENCE_FILES)
def test_reference_present(relpath):
    path = ROOT / relpath
    assert path.exists(), f"missing absorbed reference: {relpath}"


@pytest.mark.auto
@pytest.mark.parametrize("relpath", REFERENCE_FILES)
def test_reference_has_canonical_provenance(relpath):
    text = (ROOT / relpath).read_text(encoding="utf-8")[:1024]
    assert "@canonical" in text, f"{relpath}: no @canonical header"
    assert "n6-architecture@" in text, f"{relpath}: no n6-architecture@<sha> coord"
    assert re.search(r"@md5_at_extraction:\s*[0-9a-f]{32}", text), (
        f"{relpath}: no @md5_at_extraction header"
    )


@pytest.mark.auto
def test_reference_inventory_runs_clean():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "reference_inventory.py"), "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, rc.stdout
    data = json.loads(rc.stdout)
    assert data["all_ok"] is True
    assert all(r["status"] == "OK" for r in data["rows"])


@pytest.mark.auto
def test_papers_referenced_in_papers_README():
    p = ROOT / "papers/README.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "n6-ai-17-techniques-experimental-paper.md" in text
    assert "n6-ai-techniques-68-integrated-paper.md" in text


@pytest.mark.auto
def test_lean_proofs_referenced_in_formal_README():
    p = ROOT / "formal/README.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Sigma.lean" in text
    assert "SigmaLatticeCard.lean" in text
    assert "PROVEN" in text


@pytest.mark.auto
def test_proven_sigma_lattice_card_no_sorry():
    """The Lean 4 proof must remain `rfl` (no sorry). If anyone changes it
    to `sorry` we surface it immediately."""
    p = ROOT / "formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean"
    text = p.read_text(encoding="utf-8")
    assert ":= rfl" in text, "SigmaLatticeCard proof regressed away from rfl"
    # Comments mentioning sorry are fine; an actual `sorry` term is not.
    code_lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    code = "\n".join(code_lines)
    assert "sorry" not in code, "SigmaLatticeCard contains active `sorry`"
