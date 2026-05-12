#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""bench_humaneval.py — cold-bench Qwen2.5-Coder on HumanEval (D-007).

Phase v0.1.3 deliverable per `papers/plan-runbook-v0.1.3.md §4.3`. Runs
HumanEval on a base model + writes results to runs/<model>/humaneval.json.

USAGE
    python3 tool/bench_humaneval.py \\
        --model Qwen/Qwen2.5-Coder-1.5B \\
        --output /home/summer/runs/bench-cold-v0.1.3/qwen2.5-coder-1.5b/ \\
        --num-tasks 164          # full set ; 0 = unlimited

OUTPUT
    <output>/humaneval.json      summary + pass@1 + per-task verdicts
    <output>/samples.jsonl       one row per (task_id, completion, passed)
    <output>/README.md           dataset card

NOTES
    - Greedy decoding (do_sample=False) for deterministic baseline.
    - Sandbox: shell-out to `python3 -c "exec(...)"` with the canonical
      `check(candidate)` harness pattern from the HumanEval paper.
    - 30s wall-clock budget per task; any timeout = fail.

CROSS-LINKS
    papers/plan-runbook-v0.1.3.md §4.3 — cold-bench step
    tool/hf_publish.py target=cold-bench — uploads `<output>/` to
        dancinlab/hexa-forge-bench-cold-v0.1.3
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-1.5B"
DEFAULT_OUTPUT = Path.home() / "runs" / "bench-cold-v0.1.3" / "qwen2.5-coder-1.5b"


def load_model(model_id: str, dtype: str = "bfloat16"):
    """Lazy import to keep --help fast."""
    import torch  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

    tdtype = {"bfloat16": torch.bfloat16, "float16": torch.float16}.get(dtype, torch.bfloat16)
    print(f"loading {model_id} (dtype={dtype})...", flush=True)
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=tdtype,
        device_map="auto",
    )
    model.eval()
    print(f"  vocab={tok.vocab_size} max_pos={getattr(model.config, 'max_position_embeddings', '?')}", flush=True)
    return tok, model


def generate(tok, model, prompt: str, max_new_tokens: int = 512) -> str:
    import torch  # type: ignore

    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    full = tok.decode(out[0], skip_special_tokens=True)
    # strip prompt
    if full.startswith(prompt):
        full = full[len(prompt):]
    return full


def truncate_completion(text: str) -> str:
    """Heuristic stop: end of function body."""
    # Find any newline followed by non-indented chars (next def / module-level)
    lines = text.split("\n")
    out = []
    for line in lines:
        if out and line and not line.startswith((" ", "\t", ")", "]", "}", "#")):
            break
        out.append(line)
    return "\n".join(out)


def run_test(prompt: str, completion: str, test: str, entry_point: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Execute the HumanEval test harness in a subprocess."""
    program = (
        prompt + completion + "\n\n" + test
        + f"\n\ncheck({entry_point})\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(program)
        path = f.name
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=timeout,
        )
        elapsed = time.monotonic() - t0
        return {
            "passed": r.returncode == 0,
            "stderr": r.stderr[-200:],
            "elapsed_s": round(elapsed, 2),
            "timeout": False,
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "stderr": "TIMEOUT", "elapsed_s": timeout, "timeout": True}
    finally:
        _os.unlink(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bench_humaneval", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--num-tasks", type=int, default=164, help="0 = all 164")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)

    from human_eval.data import read_problems  # type: ignore
    problems = read_problems()
    task_ids = sorted(problems.keys())
    if args.num_tasks > 0:
        task_ids = task_ids[: args.num_tasks]
    print(f"plan: model={args.model} dtype={args.dtype} tasks={len(task_ids)} out={args.output}", flush=True)

    if args.dry_run:
        print("--dry-run: stopping")
        return 0

    tok, model = load_model(args.model, dtype=args.dtype)

    samples = []
    n_pass = 0
    t_start = time.monotonic()
    for i, tid in enumerate(task_ids):
        p = problems[tid]
        prompt = p["prompt"]
        try:
            completion_raw = generate(tok, model, prompt, max_new_tokens=args.max_new_tokens)
            completion = truncate_completion(completion_raw)
            r = run_test(prompt, completion, p["test"], p["entry_point"], timeout=args.timeout)
        except Exception as exc:
            r = {"passed": False, "stderr": f"GEN_ERROR: {type(exc).__name__}: {str(exc)[:200]}", "elapsed_s": 0, "timeout": False}
            completion = ""
        if r["passed"]:
            n_pass += 1
        elapsed = time.monotonic() - t_start
        rate = (i + 1) / max(elapsed, 1e-3)
        sample = {
            "task_id": tid,
            "completion": completion,
            "passed": r["passed"],
            "elapsed_s": r["elapsed_s"],
            "timeout": r["timeout"],
            "stderr_tail": r.get("stderr", "")[-150:],
        }
        samples.append(sample)
        print(
            f"  [{i+1:>3}/{len(task_ids)}] {tid:14} pass={r['passed']} "
            f"pass@1_so_far={n_pass}/{i+1}={n_pass*100/(i+1):.1f}% "
            f"({rate:.2f} task/s)",
            flush=True,
        )

    # Write samples.jsonl
    with (args.output / "samples.jsonl").open("w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    # Write summary
    summary = {
        "model": args.model,
        "dtype": args.dtype,
        "bench": "HumanEval",
        "tasks_total": len(task_ids),
        "tasks_passed": n_pass,
        "pass_at_1": round(n_pass / max(len(task_ids), 1), 4),
        "elapsed_total_s": round(time.monotonic() - t_start, 1),
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with (args.output / "humaneval.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
