#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""run_all_smoke.py — unified smoke runner for the v0.5.x stack (r63).

Runs every smoke test + scoring gate in sequence, reports a summary
table, and exits with non-zero if anything fails. Suitable for CI
(pre-commit hook, GitHub Actions, pre-push) or local `make verify`
equivalent.

WHAT IT RUNS

1. `tool/forge_runtime.py smoke` — 18 cases (legacy + orchestration +
   per-prompt cache + file cache + multi-turn + native messages +
   conv-history file + SQLite WAL cache + SQLite WAL conv + anthropic
   cache-mark + schema version).
2. `tool/classify_prompt.py` — 21 cases.
3. `tool/select_vendor_tier.py` — 14 cases.
4. `tool/forge_audit.py --smoke` — 20-row synthetic aggregation +
   gate alerts + 3 output formats.
5. `tool/forge_vacuum.py --smoke` — synthetic DB vacuum cycle.
6. `tool/score_orchestration_mk0.py` on the 300-task manifest, checking
   classifier overall ≥ 0.92 + tier_match ≥ 0.85 + tool_match ≥ 0.85.
7. `tool/score_brier_mk0.py` on r6's score artifacts, checking
   Brier ≤ 0.05 + ECE ≤ 0.10.

OUTPUT

- Per-step PASS/FAIL line with wall time.
- Summary table at the end with totals.
- Exit code: 0 = all green, 1 = any step failed.

USAGE

    # Default (all 7 steps)
    python3 tool/run_all_smoke.py

    # Verbose (stream sub-process output)
    python3 tool/run_all_smoke.py --verbose

    # Skip the slowest step (full DLG-mk0 re-score)
    python3 tool/run_all_smoke.py --skip-eval
"""
from __future__ import annotations

# Scrub tool/ from sys.path BEFORE stdlib imports (tool/tokenize.py
# shadows stdlib `tokenize` when at sys.path[0]; would break the
# dataclasses → inspect → linecache → tokenize chain).
import os as _os  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_THIS_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _THIS_DIR]

# Now safe to import stdlib that uses tokenize/inspect.
import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402

_REPO_ROOT = _THIS_DIR.parent  # lm_foundry/


@dataclass
class Step:
    name: str
    cmd: list[str]
    check_fn_name: str | None = None  # post-process step
    skip_flag: str | None = None       # flag that disables this step
    ok: bool = False
    elapsed_s: float = 0.0
    stdout_tail: str = ""              # last N lines of output
    error: str = ""

    extra: dict = field(default_factory=dict)


STEPS: list[Step] = [
    Step("forge_runtime smoke",
         cmd=["python3", str(_THIS_DIR / "forge_runtime.py"), "smoke"]),
    Step("classify_prompt smoke",
         cmd=["python3", str(_THIS_DIR / "classify_prompt.py")]),
    Step("select_vendor_tier smoke",
         cmd=["python3", str(_THIS_DIR / "select_vendor_tier.py")]),
    Step("forge_audit --smoke",
         cmd=["python3", str(_THIS_DIR / "forge_audit.py"), "--smoke"]),
    Step("forge_vacuum --smoke",
         cmd=["python3", str(_THIS_DIR / "forge_vacuum.py"), "--smoke"]),
    Step("score_orchestration_mk0 (300-task gate)",
         cmd=["python3", str(_THIS_DIR / "score_orchestration_mk0.py"),
              "--manifest", str(_REPO_ROOT / "eval/delegation-mk0/manifest.jsonl"),
              "--output", "/tmp/run_all_smoke_orch"],
         check_fn_name="check_orchestration_gates",
         skip_flag="--skip-eval"),
    Step("score_brier_mk0 (calibration gate)",
         cmd=["python3", str(_THIS_DIR / "score_brier_mk0.py"),
              "--input", "/tmp/run_all_smoke_orch/per_task_orchestration.jsonl",
              "--output", "/tmp/run_all_smoke_brier",
              "--bins", "10"],
         check_fn_name="check_brier_gates",
         skip_flag="--skip-eval"),
]


# ============================================================================
# Per-step post-process checks (for the scoring steps that don't have
# a built-in exit-code gate — we need to read the JSON output)
# ============================================================================

def check_orchestration_gates(step: Step) -> tuple[bool, str]:
    """Read scores_orchestration.json and apply r62 GA gates."""
    p = Path("/tmp/run_all_smoke_orch/scores_orchestration.json")
    if not p.exists():
        return False, "scores_orchestration.json not found"
    try:
        s = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e!r}"
    overall = s.get("overall_accuracy", 0.0)
    tier = s.get("tier_routing", {}).get("tier_match_accuracy", 0.0)
    tool = s.get("tier_routing", {}).get("tool_match_accuracy", 0.0)
    step.extra = {"overall": overall, "tier_match": tier, "tool_match": tool}
    breaches: list[str] = []
    if overall < 0.92:
        breaches.append(f"classifier overall {overall:.4f} < 0.92")
    if tier < 0.85:
        breaches.append(f"tier_match {tier:.4f} < 0.85")
    if tool < 0.85:
        breaches.append(f"tool_match {tool:.4f} < 0.85")
    if breaches:
        return False, "; ".join(breaches)
    return True, f"overall={overall:.4f} tier={tier:.4f} tool={tool:.4f}"


def check_brier_gates(step: Step) -> tuple[bool, str]:
    """Read brier.json and apply r62 calibration gates."""
    p = Path("/tmp/run_all_smoke_brier/brier.json")
    if not p.exists():
        return False, "brier.json not found"
    try:
        s = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e!r}"
    brier = s.get("brier_score", 1.0)
    ece = s.get("ece", 1.0)
    step.extra = {"brier": brier, "ece": ece}
    breaches: list[str] = []
    if brier > 0.05:
        breaches.append(f"Brier {brier:.4f} > 0.05")
    if ece > 0.10:
        breaches.append(f"ECE {ece:.4f} > 0.10")
    if breaches:
        return False, "; ".join(breaches)
    return True, f"Brier={brier:.4f} ECE={ece:.4f}"


_CHECK_FNS = {
    "check_orchestration_gates": check_orchestration_gates,
    "check_brier_gates": check_brier_gates,
}


# ============================================================================
# Runner
# ============================================================================

def run_step(step: Step, verbose: bool) -> None:
    """Run one step. Sets step.ok / step.elapsed_s / step.stdout_tail / step.error."""
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            step.cmd, capture_output=True, text=True, timeout=600,
            cwd=str(_REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        step.ok = False
        step.elapsed_s = time.monotonic() - t0
        step.error = "TIMEOUT after 600s"
        return
    except (OSError, FileNotFoundError) as e:
        step.ok = False
        step.elapsed_s = time.monotonic() - t0
        step.error = f"spawn failed: {e!r}"
        return
    step.elapsed_s = time.monotonic() - t0
    step.stdout_tail = "\n".join((result.stdout or "").splitlines()[-3:])

    if verbose:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")

    if result.returncode != 0:
        step.ok = False
        step.error = (
            f"exit {result.returncode}"
            + (f": {result.stderr.splitlines()[-1]}" if result.stderr.strip() else "")
        )
        return

    # Post-process check if defined
    if step.check_fn_name:
        check = _CHECK_FNS.get(step.check_fn_name)
        if check is None:
            step.ok = False
            step.error = f"unknown check_fn {step.check_fn_name}"
            return
        ok, msg = check(step)
        step.ok = ok
        if not ok:
            step.error = msg
        else:
            step.stdout_tail = msg
        return

    step.ok = True


def render_summary(steps: list[Step], total_s: float) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("v0.5.x STACK SMOKE SUMMARY")
    lines.append("=" * 78)
    for s in steps:
        flag = "✓" if s.ok else "✗"
        lines.append(f"  {flag} {s.name:<45} {s.elapsed_s:>6.2f}s  {s.stdout_tail[:80]}")
        if not s.ok and s.error:
            lines.append(f"      ERROR: {s.error[:200]}")
    n_pass = sum(1 for s in steps if s.ok)
    n_total = len(steps)
    verdict = "ALL GREEN" if n_pass == n_total else f"FAILED ({n_total - n_pass} step(s))"
    lines.append("-" * 78)
    lines.append(f"  TOTAL: {n_pass}/{n_total} steps in {total_s:.2f}s — {verdict}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="Stream sub-process output as it runs")
    ap.add_argument("--skip-eval", action="store_true",
                    help="Skip DLG-mk0 + Brier scoring steps (faster)")
    ap.add_argument("--json", action="store_true",
                    help="Emit summary as JSON instead of text")
    args = ap.parse_args()

    # Filter steps by skip flag
    steps = [s for s in STEPS if not (args.skip_eval and s.skip_flag == "--skip-eval")]

    print(f"Running {len(steps)} smoke step(s) ...\n")
    t_all = time.monotonic()
    for s in steps:
        print(f"  → {s.name} ...", flush=True)
        run_step(s, args.verbose)
        flag = "✓" if s.ok else "✗"
        print(f"    {flag} {s.elapsed_s:.2f}s  {s.stdout_tail[:120]}", flush=True)
        if not s.ok:
            print(f"    ERROR: {s.error}", file=sys.stderr, flush=True)
    total_s = time.monotonic() - t_all

    if args.json:
        out = {
            "n_steps": len(steps),
            "n_pass": sum(1 for s in steps if s.ok),
            "total_seconds": round(total_s, 2),
            "steps": [
                {"name": s.name, "ok": s.ok, "elapsed_s": round(s.elapsed_s, 2),
                 "error": s.error, "extra": s.extra}
                for s in steps
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print()
        print(render_summary(steps, total_s), end="")

    return 0 if all(s.ok for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
