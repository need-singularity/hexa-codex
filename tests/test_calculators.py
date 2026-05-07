"""
Round-trip smoke tests for verify/calc_*.py + analyzers.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "verify"


def _run_json(script: str, *args: str) -> dict:
    rc = subprocess.run(
        [sys.executable, str(VERIFY / script), "--json", *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, (
        f"{script} exit {rc.returncode}\nstdout:\n{rc.stdout}\nstderr:\n{rc.stderr}"
    )
    return json.loads(rc.stdout)


# ----- F-CODEX-1 training cost ---------------------------------------------

@pytest.mark.auto
def test_calc_train_cost_default_passes_arithmetic_floor():
    d = _run_json("calc_train_cost.py")
    assert d["exponent_J2"] == 24
    assert d["falsifier_ok"] is True
    assert d["n6_exponent"] >= 0.95


@pytest.mark.auto
def test_calc_train_cost_scales_with_size():
    small = _run_json("calc_train_cost.py", "--N", "1e8", "--D", "1e10")
    large = _run_json("calc_train_cost.py", "--N", "1e12", "--D", "1e13")
    assert large["n6_cost_ratio"] > small["n6_cost_ratio"]


# ----- F-CODEX-2 inference cost --------------------------------------------

@pytest.mark.auto
def test_calc_infer_cost_default_arithmetic_floor():
    d = _run_json("calc_infer_cost.py")
    assert d["exponent_tau"] == 4
    assert d["falsifier_ok"] is True


@pytest.mark.auto
def test_calc_infer_cost_long_context():
    d = _run_json("calc_infer_cost.py", "--context", "1000000")
    assert d["context"] == 1_000_000
    # cost ratio for long context >> 1
    assert d["n6_cost_ratio"] > 1.0


# ----- F-CODEX-3 alignment --------------------------------------------------

@pytest.mark.auto
def test_calc_alignment_axis_count_is_sigma_6():
    d = _run_json("calc_alignment.py")
    assert d["axis_count"] == 12


@pytest.mark.auto
def test_calc_alignment_aggregates():
    d = _run_json("calc_alignment.py", "--helpfulness", "1.0",
                  "--harmlessness", "1.0")
    assert 0.6 <= d["n6_aggregate"] <= 1.0


# ----- F-CODEX-4 interpret --------------------------------------------------

@pytest.mark.auto
def test_calc_interpret_predicted_motif_count_is_10():
    d = _run_json("calc_interpret.py")
    assert d["predicted_motifs"] == 10
    assert d["falsifier_ok"] is True


@pytest.mark.auto
def test_calc_interpret_far_drift_falsifies():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "calc_interpret.py"),
         "--json", "--observed-motifs", "20"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode != 0
    d = json.loads(rc.stdout)
    assert d["falsifier_ok"] is False
    assert d["drift"] == 10


# ----- quality_scale --------------------------------------------------------

@pytest.mark.auto
def test_calc_quality_scale_alpha_is_phi_over_sigma():
    d = _run_json("calc_quality_scale.py")
    # alpha = 2/12 ≈ 0.1667
    assert 0.16 <= d["n6_alpha"] <= 0.17


# ----- analyzers ------------------------------------------------------------

@pytest.mark.auto
def test_lattice_explore_n6_master_row():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "lattice_explore.py"), "--json", "6"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0
    rows = json.loads(rc.stdout)
    assert len(rows) == 1
    r = rows[0]
    assert r["sigma"] == 12 and r["tau"] == 4 and r["phi"] == 2
    assert r["balanced"] is True
    assert r["n6_master_row"] is True


@pytest.mark.auto
def test_release_params_table_emits_5_versions():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "release_params.py"), "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0
    data = json.loads(rc.stdout)
    assert set(data) == {"v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v2.0.0"}
    assert data["v1.0.0"]["status"] == "RELEASED"
    assert data["v2.0.0"]["status"] == "ASPIRATIONAL"


@pytest.mark.auto
def test_verb_query_finds_alignment():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "verb_query.py"), "--json", "alignment"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, rc.stdout
    data = json.loads(rc.stdout)
    assert len(data) == 1
    assert data[0]["verb"] == "alignment"
    assert data[0]["group"] == "safety"
    assert data[0]["present"] is True


@pytest.mark.auto
def test_verb_query_filters_by_group():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "verb_query.py"), "--json", "--group", "economics"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0
    data = json.loads(rc.stdout)
    assert len(data) == 3
    assert {d["verb"] for d in data} == {"train_cost", "infer_cost", "quality_scale"}
