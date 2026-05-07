"""
install.hexa runtime test — requires hexa-lang VM at /Users/ghost/.hx/bin/hexa.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _have_hexa() -> bool:
    return shutil.which("hexa") is not None or Path("/Users/ghost/.hx/bin/hexa").exists()


@pytest.mark.hexa
def test_install_hexa_runs_clean():
    if not _have_hexa():
        pytest.skip("hexa-lang runtime not available")
    hexa_bin = shutil.which("hexa") or "/Users/ghost/.hx/bin/hexa"
    env = os.environ.copy()
    env.update({
        "HX_PKG_DIR":     str(ROOT),
        "HX_HOOK_PHASE":  "both",
        "HX_BIN_DIR":     "/tmp/hx-bin-test",
    })
    rc = subprocess.run(
        [hexa_bin, "run", "install.hexa"],
        capture_output=True, text=True, cwd=str(ROOT), env=env,
    )
    assert rc.returncode == 0, (
        f"install.hexa exit {rc.returncode}\nstdout:\n{rc.stdout}\nstderr:\n{rc.stderr}"
    )
    assert "selftest PASS — 17/17 verb specs present" in rc.stdout
