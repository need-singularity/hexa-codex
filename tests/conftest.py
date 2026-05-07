"""
hexa-codex pytest configuration.

Most checks are auto-runnable (Python stdlib only); a few are tagged
`hexa` because they require the hexa-lang runtime (`/Users/ghost/.hx/bin/hexa`).
"""
from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "auto: check that runs without external dependencies (Python stdlib only)",
    )
    config.addinivalue_line(
        "markers",
        "hexa: check that requires the hexa-lang runtime (`hexa run ...`)",
    )
