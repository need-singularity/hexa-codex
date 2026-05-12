#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""hexa_s0_scorer.py — real hexa S0 parse scorer using hexa_v2_linux_x86_64.

Phase v0.2.0-r3 deliverable. Replaces the substring-fallback s0_s1_exit_0
scorer in tool/score_mk0_eval.py with a real compile-and-check via the
self-hosted hexa-cc binary.

The hexa-cc binary (hexa_v2_linux_x86_64) reports OK or an error when
asked to compile `<input.hexa>` to `<output.c>`. Exit code 0 = parse +
resolve OK; non-zero = lint/parse/resolve failure.

USAGE (programmatic)
    from tool.hexa_s0_scorer import score_s0
    passed, detail = score_s0(generated_hexa_code)

USAGE (CLI smoke)
    python3 tool/hexa_s0_scorer.py --code 'fn add(a:i32,b:i32)->i32{return a+b;}'

CROSS-LINKS
    tool/score_mk0_eval.py  — sister scorer dispatch table
    hexa-lang SPEC.md §0.4 — stage-1 self-hosted compiler
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

HEXA_CC_BIN = Path("/home/summer/mac_home/core/hexa-lang/build/hexa_v2_linux_x86_64")
TIMEOUT_S = 10.0


_ERROR_PATTERNS = (
    "Parse error",
    "parse error",
    "CODEGEN ERROR",
    "Resolve error",
    "Type error",
    "Lint S",  # S0..S8 lint failures
    "unhandled binop",
    "unhandled operator",
    "unexpected token",
)


def score_s0(hexa_code: str, *, bin_path: Path = HEXA_CC_BIN, timeout: float = TIMEOUT_S) -> Tuple[bool, str]:
    """Compile-test hexa_code via real hexa-cc.

    hexa-cc returns exit 0 even on parse/codegen errors, but writes error
    text to stderr/stdout. We check exit code AND scan output for known
    error patterns to derive PASS / FAIL.

    Returns (passed, detail) where passed=True iff hexa-cc reports no
    errors anywhere in stdout/stderr.
    """
    if not bin_path.exists():
        return (False, f"hexa-cc binary missing at {bin_path}")
    with tempfile.TemporaryDirectory() as td:
        in_path = Path(td) / "in.hexa"
        out_path = Path(td) / "out.c"
        in_path.write_text(hexa_code, encoding="utf-8")
        try:
            r = subprocess.run(
                [str(bin_path), str(in_path), str(out_path)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return (False, f"TIMEOUT after {timeout}s")
        except Exception as exc:
            return (False, f"{type(exc).__name__}: {exc}")
        combined = (r.stdout or "") + "\n" + (r.stderr or "")
        if r.returncode != 0:
            return (False, combined[-200:].strip())
        # check error patterns in output
        for pat in _ERROR_PATTERNS:
            if pat in combined:
                idx = combined.find(pat)
                snippet = combined[max(0, idx-20):idx+150].replace("\n", " ")
                return (False, f"detected '{pat}': {snippet.strip()}")
        return (True, "OK")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="hexa_s0_scorer")
    parser.add_argument("--code", help="hexa source code as string")
    parser.add_argument("--file", type=Path, help="path to .hexa file")
    args = parser.parse_args(argv)

    if args.code:
        code = args.code
    elif args.file:
        code = args.file.read_text()
    else:
        # Self-test
        passing = "fn add(a: i32, b: i32) -> i32 {\n    return a + b;\n}\n"
        failing = "fn add(a: i32 b: i32) -> i32 { return a + b }"
        p, d = score_s0(passing)
        print(f"PASSING TEST: passed={p} detail={d}")
        p, d = score_s0(failing)
        print(f"FAILING TEST: passed={p} detail={d}")
        return 0

    passed, detail = score_s0(code)
    print(f"passed: {passed}")
    print(f"detail: {detail}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
