#!/usr/bin/env python3
"""
hexa-codex verify/cli.py — unified verifier CLI dispatcher.

One entry point for all hexa-codex verifiers. Each verifier is invoked
as a subprocess so output stays bit-identical to direct invocations and
exit codes aggregate cleanly.

Usage:
    python3 verify/cli.py                # all-checks, human readable
    python3 verify/cli.py all
    python3 verify/cli.py n6             # n=6 lattice arithmetic
    python3 verify/cli.py inventory      # 17-verb spec presence + headers
    python3 verify/cli.py group          # 4-group / 17-verb consistency
    python3 verify/cli.py release        # v1.0..v2.0 ladder monotonicity
    python3 verify/cli.py falsifiers     # F-CODEX-1..4 arithmetic floors
    python3 verify/cli.py --json
    python3 verify/cli.py --quiet
    python3 verify/cli.py --list

Exit code:
    0 = all selected checks passed
    1 = one or more checks failed
    2 = invocation error
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parent
ROOT = VERIFY_DIR.parent

CHECKS: list[tuple[str, str, str]] = [
    ("n6",         "n6_arithmetic.py",  "n=6 lattice arithmetic identity"),
    ("inventory",  "spec_inventory.py", "17-verb spec presence + headers"),
    ("group",      "group_audit.py",    "4-group / 17-verb consistency audit"),
    ("release",    "release_ladder.py", "release ladder v1.0→v2.0 monotonicity"),
    ("falsifiers", "falsifier_check.py","F-CODEX-1..4 arithmetic-floor checklist"),
]
SCRIPT_FOR = {name: script for name, script, _ in CHECKS}
LABEL_FOR  = {name: label  for name, _, label  in CHECKS}


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()

def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _use_color() else t

def _green(t: str)  -> str: return _c("32", t)
def _red(t: str)    -> str: return _c("31", t)
def _yellow(t: str) -> str: return _c("33", t)
def _bold(t: str)   -> str: return _c("1",  t)


def _run_one(name: str) -> dict:
    script = VERIFY_DIR / SCRIPT_FOR[name]
    if not script.exists():
        return {
            "name": name, "label": LABEL_FOR[name],
            "exit_code": 2, "duration_s": 0.0,
            "stdout": "", "stderr": f"missing script: {script}",
            "ok": False,
        }
    t0 = time.monotonic()
    rc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    dt = time.monotonic() - t0
    return {
        "name": name, "label": LABEL_FOR[name],
        "exit_code": rc.returncode, "duration_s": round(dt, 3),
        "stdout": rc.stdout, "stderr": rc.stderr,
        "ok": rc.returncode == 0,
    }


def _print_human(results: list[dict], quiet: bool) -> None:
    if not quiet:
        print()
    for r in results:
        if not quiet:
            print("=" * 72)
            print(f"  ▶ {_bold(r['name'])}  —  {r['label']}")
            print("=" * 72)
            if r["stdout"]:
                print(r["stdout"].rstrip("\n"))
            if r["stderr"].strip():
                print(_yellow(r["stderr"].rstrip("\n")))
        verdict = _green("PASS") if r["ok"] else _red("FAIL")
        if not quiet:
            print()
        print(f"  [{verdict}] {r['name']:11s}  ({r['duration_s']:5.2f}s)  {r['label']}")
    print("=" * 72)
    n = len(results)
    n_ok = sum(1 for r in results if r["ok"])
    line = f"  {n_ok}/{n} checks PASS"
    print(_bold(_green(line)) if n_ok == n else _bold(_red(line)))
    if n_ok != n:
        for r in results:
            if not r["ok"]:
                print(f"    ✗ {r['name']}  exit={r['exit_code']}  {r['label']}")
    total_dt = sum(r["duration_s"] for r in results)
    print(f"  total wall time: {total_dt:.2f}s")
    print("=" * 72)


def _print_json(results: list[dict]) -> None:
    n = len(results)
    n_ok = sum(1 for r in results if r["ok"])
    print(json.dumps({
        "tool": "hexa-codex verify/cli.py",
        "schema": "hexa-codex/verify/cli/v1",
        "checks_total": n,
        "checks_pass":  n_ok,
        "checks_fail":  n - n_ok,
        "ok":           n_ok == n,
        "results":      [
            {k: v for k, v in r.items() if k != "stderr" or v.strip()}
            for r in results
        ],
    }, indent=2, ensure_ascii=False))


def _print_listing() -> None:
    print(_bold("hexa-codex verify/ registered checks:"))
    for name, script, label in CHECKS:
        exists = (VERIFY_DIR / script).exists()
        mark = _green("ok ") if exists else _red("MISS")
        print(f"  [{mark}] {name:11s} → verify/{script:24s}  {label}")
    present = sum(1 for _, s, _ in CHECKS if (VERIFY_DIR / s).exists())
    print(f"  total: {len(CHECKS)} check(s) — present: {present}/{len(CHECKS)}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="verify/cli.py")
    p.add_argument("target", nargs="?", default="all")
    p.add_argument("--json",  action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--list",  action="store_true")
    return p


def main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv[1:])
    if args.list:
        _print_listing()
        return 0
    if args.target == "all":
        names = [n for n, _, _ in CHECKS]
    elif args.target in SCRIPT_FOR:
        names = [args.target]
    else:
        print(_red(f"unknown check: {args.target!r}"), file=sys.stderr)
        print("known:", ", ".join(n for n, _, _ in CHECKS), file=sys.stderr)
        return 2
    results = [_run_one(n) for n in names]
    if args.json:
        _print_json(results)
    else:
        _print_human(results, args.quiet)
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
