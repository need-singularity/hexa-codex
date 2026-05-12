#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v2.py — format-balanced v0.2.0-r2 SFT dataset.

Fixes the v0.2.0-r1 over-refusal failure (RUN_NOTES.md). Three changes:

1. All examples wrapped in unified `### User:\\n<prompt>\\n### Assistant:\\n<completion>`
2. Accept pairs sourced from HumanEval canonical solutions (164 rows)
3. Canon corpus re-templated as Q/A pairs (rather than raw dumps)

INPUT
    ~/runs/corpus/hexa-canon-v1/canon-docs.parquet
    ~/runs/corpus/hexa-canon-v1/canon-source.parquet
    ~/runs/sft-refusal-v1/refusal_pairs.jsonl
    + HumanEval canonical solutions via `human_eval.data.read_problems()`

OUTPUT
    ~/runs/sft-train-v2/train.jsonl
    ~/runs/sft-train-v2/MANIFEST.json

MIX TARGET (format-balanced):
    refuse pairs    : 200 (5 NLs x 8 categories)
    code accept     : 164 (HumanEval canonical)
    canon doc Q/A   : 400 (re-templated md)
    canon source Q/A: 200 (re-templated hexa)
    total           : ~964 rows (vs 1000 in r1, balance > size at this scale)
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import random
import sys
from pathlib import Path

DEFAULT_INPUT_CANON = Path.home() / "runs" / "corpus" / "hexa-canon-v1"
DEFAULT_INPUT_REFUSAL = Path.home() / "runs" / "sft-refusal-v1" / "refusal_pairs.jsonl"
DEFAULT_OUTPUT = Path.home() / "runs" / "sft-train-v2"

MAX_COMPLETION_CHARS = 3000
TEMPLATE = "### User:\n{prompt}\n### Assistant:\n{completion}"


def fmt(prompt: str, completion: str) -> str:
    if len(completion) > MAX_COMPLETION_CHARS:
        completion = completion[:MAX_COMPLETION_CHARS] + "\n...[truncated]"
    return TEMPLATE.format(prompt=prompt, completion=completion)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_sft_dataset_v2")
    parser.add_argument("--canon-dir", type=Path, default=DEFAULT_INPUT_CANON)
    parser.add_argument("--refusal-jsonl", type=Path, default=DEFAULT_INPUT_REFUSAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-canon-md", type=int, default=400)
    parser.add_argument("--n-canon-hexa", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    random.seed(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)

    rows = []

    # --- 1. Refusal pairs (200) ---
    n_refuse = 0
    with args.refusal_jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not r.get("completion") or "needs_completion" in r.get("tags", []):
                continue
            rows.append({
                "text": fmt(r["prompt"], r["completion"]),
                "source": "refusal",
                "tokens_est": (len(r["prompt"]) + len(r["completion"])) // 4,
            })
            n_refuse += 1
    print(f"refusal pairs   : {n_refuse}")

    # --- 2. HumanEval accept pairs (164) ---
    try:
        from human_eval.data import read_problems  # type: ignore
    except ImportError as exc:
        raise SystemExit("human-eval required: pip install human-eval") from exc
    problems = read_problems()
    n_accept = 0
    for tid, p in problems.items():
        prompt = p["prompt"].rstrip() + "\n    # Complete the function."
        completion = p["prompt"] + p["canonical_solution"]
        rows.append({
            "text": fmt(prompt, completion),
            "source": "humaneval-accept",
            "tokens_est": (len(prompt) + len(completion)) // 4,
        })
        n_accept += 1
    print(f"humaneval accept: {n_accept}")

    # --- 3. Canon md Q/A re-templated ---
    import pyarrow.parquet as pq  # type: ignore
    docs = pq.read_table(args.canon_dir / "canon-docs.parquet").to_pylist()
    random.shuffle(docs)
    n_md = 0
    for r in docs[:args.n_canon_md]:
        prompt = f"Show me the canonical doc at {r['repo']}/{r['path']}."
        completion = r["content"]
        rows.append({
            "text": fmt(prompt, completion),
            "source": "canon-md",
            "tokens_est": (len(prompt) + len(completion)) // 4,
        })
        n_md += 1
    print(f"canon md Q/A    : {n_md}")

    # --- 4. Canon hexa Q/A re-templated ---
    src = pq.read_table(args.canon_dir / "canon-source.parquet").to_pylist()
    random.shuffle(src)
    n_hexa = 0
    for r in src[:args.n_canon_hexa]:
        prompt = f"Show me the canonical hexa source at {r['repo']}/{r['path']}."
        completion = r["content"]
        rows.append({
            "text": fmt(prompt, completion),
            "source": "canon-hexa",
            "tokens_est": (len(prompt) + len(completion)) // 4,
        })
        n_hexa += 1
    print(f"canon hexa Q/A  : {n_hexa}")

    # Shuffle final
    random.shuffle(rows)
    print(f"\ntotal           : {len(rows)} rows / ~{sum(r['tokens_est'] for r in rows)} tokens")

    # Write
    out_jsonl = args.output / "train.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "n_refusal": n_refuse,
        "n_humaneval_accept": n_accept,
        "n_canon_md": n_md,
        "n_canon_hexa": n_hexa,
        "n_total": len(rows),
        "n_tokens_est": sum(r["tokens_est"] for r in rows),
        "template": "### User:\\n{prompt}\\n### Assistant:\\n{completion}",
        "max_completion_chars": MAX_COMPLETION_CHARS,
    }
    with (args.output / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
