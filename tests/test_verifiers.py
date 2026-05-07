"""
Smoke tests for every hexa-codex verify/*.py script.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "verify"


VERIFIER_CASES = [
    ("n6_arithmetic.py",   r"\d+/\d+ PASS  —  n=6 arithmetic identity"),
    ("spec_inventory.py",  r"17/17 verb specs present"),
    ("group_audit.py",     r"\d+/\d+ surfaces agree"),
    ("release_ladder.py",  r"release ladder monotone"),
    ("falsifier_check.py", r"\d+/\d+ arithmetic floors PASS"),
]


@pytest.mark.auto
@pytest.mark.parametrize("script,expected", VERIFIER_CASES,
                         ids=[c[0] for c in VERIFIER_CASES])
def test_verifier_runs_clean(script, expected):
    rc = subprocess.run(
        [sys.executable, str(VERIFY / script)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, (
        f"{script}: exit {rc.returncode}\nstdout:\n{rc.stdout}\nstderr:\n{rc.stderr}"
    )
    assert re.search(expected, rc.stdout), (
        f"{script}: missing summary marker {expected!r}\n{rc.stdout}"
    )


@pytest.mark.auto
def test_cli_dispatcher_all_pass():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "cli.py"), "all", "--quiet"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, rc.stdout
    m = re.search(r"(\d+)/(\d+) checks PASS", rc.stdout)
    assert m, f"no 'N/M checks PASS' line in:\n{rc.stdout}"
    n_ok, n_total = int(m.group(1)), int(m.group(2))
    assert n_ok == n_total
    assert n_total >= 5


@pytest.mark.auto
def test_cli_dispatcher_json_mode():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "cli.py"), "all", "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0, rc.stdout
    data = json.loads(rc.stdout)
    assert data["ok"] is True
    assert {r["name"] for r in data["results"]} >= {
        "n6", "inventory", "group", "release", "falsifiers"
    }


@pytest.mark.auto
def test_cli_dispatcher_listing():
    rc = subprocess.run(
        [sys.executable, str(VERIFY / "cli.py"), "--list"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert rc.returncode == 0
    assert "[MISS]" not in rc.stdout
    assert "present:" in rc.stdout
