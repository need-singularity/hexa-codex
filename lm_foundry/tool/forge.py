#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge — unified CLI dispatcher for the v0.6.x stack (r72).

Single entry point that routes to the appropriate sub-tool. Replaces
the scattered `python3 tool/X.py` pattern in OPERATIONS.md crons /
runbooks with one consistent `forge <subcommand>` interface.

USAGE
    forge status                            # vendor key status
    forge keys add openai                   # add openai key (interactive)
    forge keys setup                        # interactive walkthrough
    forge keys test all --paid              # verify paid-tier access
    forge audit --since-hours 24            # production health audit
    forge audit --alert-cache-hit-min 0.20 --alert-error-rate-max 0.05
    forge vacuum --db /var/lib/forge/forge.sqlite3 --keep-recent 4096
    forge route "Write a Rust async server"   # decision trace
    forge route --output json "Derive complexity of binary search"
    forge smoke                             # run all 20 forge smoke + scoring gates
    forge smoke --skip-eval                 # fast pre-commit mode
    forge perf                              # latency benchmark
    forge xcache                            # anthropic cross-turn cache A/B measurement

SUBCOMMAND ROUTING (each delegates to the matching tool):
    forge status   → forge_keys.py status
    forge keys     → forge_keys.py <args>
    forge audit    → forge_audit.py <args>
    forge vacuum   → forge_vacuum.py <args>
    forge route    → forge_route.py <args>
    forge smoke    → run_all_smoke.py <args>
    forge perf     → perf_bench.py <args>
    forge xcache   → bench_anthropic_cross_turn.py <args>

For full per-subcommand --help, run `forge <sub> --help`.
"""
from __future__ import annotations

# Scrub tool/ from sys.path BEFORE stdlib imports
import os as _os  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_THIS_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _THIS_DIR]

import subprocess  # noqa: E402


# Map subcommand → tool path. Each tool already has its own argparse.
SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "status":  ("forge_keys.py",          "Show vendor key status (alias for `forge keys status`)"),
    "keys":    ("forge_keys.py",          "Vendor API key management (status / add / remove / test / setup)"),
    "audit":   ("forge_audit.py",         "Production observability audit + health gates"),
    "vacuum":  ("forge_vacuum.py",        "SQLite cache + conv-memory cleanup (cron-friendly)"),
    "route":   ("forge_route.py",         "Offline decision-trace: classify → tier → cost estimate"),
    "smoke":   ("run_all_smoke.py",       "Run all forge smoke + DLG-mk0 + Brier gates"),
    "perf":    ("perf_bench.py",          "Classifier + tier-selector latency benchmark"),
    "xcache":  ("bench_anthropic_cross_turn.py",
                "Anthropic cross-turn prompt-cache A/B ROI measurement (real API)"),
}


def _usage(exit_code: int = 0) -> int:
    print("forge — unified CLI dispatcher for the v0.6.x stack\n")
    print("usage: forge <subcommand> [args...]\n")
    print("subcommands:")
    for name, (tool, doc) in SUBCOMMANDS.items():
        print(f"  {name:<10} → {tool:<35} {doc}")
    print()
    print("Run `forge <sub> --help` for per-subcommand options.")
    print()
    print("Examples:")
    print("  forge status")
    print("  forge keys setup")
    print("  forge audit --since-hours 24 --alert-cache-hit-min 0.20")
    print("  forge route --output json 'What is RoPE?'")
    print("  forge smoke")
    return exit_code


def main() -> int:
    if len(sys.argv) < 2:
        return _usage(0)

    sub = sys.argv[1]
    rest = sys.argv[2:]

    if sub in ("-h", "--help", "help"):
        return _usage(0)

    if sub not in SUBCOMMANDS:
        print(f"forge: unknown subcommand '{sub}'\n", file=sys.stderr)
        return _usage(1)

    tool_name, _doc = SUBCOMMANDS[sub]
    tool_path = _THIS_DIR / tool_name
    if not tool_path.exists():
        print(f"forge: tool not found at {tool_path}", file=sys.stderr)
        return 2

    # Special: `forge status` is an alias for `forge keys status`
    args: list[str]
    if sub == "status":
        args = ["status"]
    elif sub == "keys" and not rest:
        # `forge keys` alone → show keys help
        args = ["--help"]
    else:
        args = rest

    cmd = ["python3", str(tool_path)] + args
    try:
        r = subprocess.run(cmd, cwd=str(_THIS_DIR.parent))
        return r.returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
