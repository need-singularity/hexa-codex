"""
Release-ladder monotonicity tests (independent of release_ladder.py module).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "verify"))


@pytest.mark.auto
def test_release_params_module_has_5_versions():
    import release_params as rp
    assert set(rp.RELEASE_PARAMS) == {"v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v2.0.0"}


@pytest.mark.auto
def test_verbs_wired_strictly_non_decreasing():
    import release_params as rp
    order = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v2.0.0"]
    wired = [rp.RELEASE_PARAMS[v]["verbs_wired"] for v in order]
    assert all(wired[i] <= wired[i+1] for i in range(len(wired)-1))


@pytest.mark.auto
def test_v2_wires_all_17_verbs():
    import release_params as rp
    assert rp.RELEASE_PARAMS["v2.0.0"]["verbs_wired"] == 17


@pytest.mark.auto
def test_eval_pipelines_one_per_version_post_seed():
    """Each release v1.1+ adds exactly one new eval pipeline (1, 2, 3, 4)."""
    import release_params as rp
    order = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v2.0.0"]
    eps = [rp.RELEASE_PARAMS[v]["eval_pipelines"] for v in order]
    assert eps == [0, 1, 2, 3, 4]


@pytest.mark.auto
def test_each_falsifier_focus_referenced_in_at_least_one_release():
    """F-CODEX-1..4 each appear in at least one release's falsifier_focus."""
    import release_params as rp
    blob = " ".join(p["falsifier_focus"] for p in rp.RELEASE_PARAMS.values())
    for tag in ("F-CODEX-1", "F-CODEX-2", "F-CODEX-3", "F-CODEX-4"):
        assert tag in blob, f"{tag} not referenced in any release plan"
