"""
17-verb spec inventory tests — independent witness to spec_inventory.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "verify"))


VERB_FILES = [
    ("safety",     "alignment",     "alignment/ai-alignment.md"),
    ("safety",     "safety",        "safety/ai-safety.md"),
    ("safety",     "welfare",       "welfare/ai-welfare.md"),
    ("safety",     "adversarial",   "adversarial/ai-adversarial.md"),
    ("safety",     "consciousness", "consciousness/ai-consciousness.md"),
    ("safety",     "interpret",     "interpret/ai-interpretability.md"),
    ("economics",  "train_cost",    "train_cost/ai-training-cost.md"),
    ("economics",  "infer_cost",    "infer_cost/ai-inference-cost.md"),
    ("economics",  "quality_scale", "quality_scale/ai-quality-scale.md"),
    ("ops",        "deploy",        "deploy/ai-deployment.md"),
    ("ops",        "enterprise",    "enterprise/ai-enterprise-custom.md"),
    ("ops",        "agent_serving", "agent_serving/ai-agent-serving.md"),
    ("ops",        "eval",          "eval/ai-eval-pipeline.md"),
    ("substrate",  "multimodal",    "multimodal/ai-multimodal.md"),
    ("substrate",  "rlhf",          "rlhf/youth-ai-labeling-rlhf-hub.md"),
    ("substrate",  "cog_arch",      "cog_arch/cognitive-architecture.md"),
    ("substrate",  "causal",        "causal/causal-chain.md"),
]


@pytest.mark.auto
@pytest.mark.parametrize("group,verb,relpath", VERB_FILES,
                         ids=[v for _, v, _ in VERB_FILES])
def test_each_verb_spec_present_with_canonical(group, verb, relpath):
    path = ROOT / relpath
    assert path.exists(), f"missing verb spec: {relpath}"
    text = path.read_text(encoding="utf-8")
    # canonical provenance header introduced by commit 59566ba
    assert "@canonical" in text[:1024], (
        f"{relpath}: no @canonical provenance header in first 1024 bytes"
    )


@pytest.mark.auto
def test_total_verb_count_is_17():
    assert len(VERB_FILES) == 17


@pytest.mark.auto
def test_group_distribution_matches_n6_lattice():
    """Per-group count: 6 + 3 + 4 + 4 = 17."""
    counts = {"safety": 0, "economics": 0, "ops": 0, "substrate": 0}
    for g, _, _ in VERB_FILES:
        counts[g] += 1
    assert counts == {"safety": 6, "economics": 3, "ops": 4, "substrate": 4}


@pytest.mark.auto
def test_inventory_module_matches_test_fixture():
    """spec_inventory.VERB_TABLE must match the per-test fixture exactly."""
    import spec_inventory as si
    assert si.VERB_TABLE == VERB_FILES


@pytest.mark.auto
def test_no_duplicate_verb_names():
    names = [v for _, v, _ in VERB_FILES]
    assert len(names) == len(set(names))


@pytest.mark.auto
def test_no_duplicate_paths():
    paths = [rp for _, _, rp in VERB_FILES]
    assert len(paths) == len(set(paths))
