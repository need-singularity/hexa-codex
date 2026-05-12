#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset.py — combine canon corpus + refusal pairs into a single SFT-ready jsonl.

Phase v0.2.0 entry. Mixes 80% canon (hexa-codex + hexa-* repos) + 20%
refusal pairs into the SFT input format expected by trl.SFTTrainer.

INPUT
    ~/runs/corpus/hexa-canon-v1/canon-docs.parquet
    ~/runs/corpus/hexa-canon-v1/canon-source.parquet
    ~/runs/sft-refusal-v1/refusal_pairs.jsonl

OUTPUT
    ~/runs/sft-train-v1/train.jsonl       — one row per training example
    ~/runs/sft-train-v1/MANIFEST.json     — sourcing stats + provenance

SCHEMA (per row):
    text   string   — full training example (canon = prepend "### Canon doc:\\n",
                      refusal = "### User:\\n<prompt>\\n### Assistant:\\n<completion>")
    source string   — "canon-md" / "canon-hexa" / "refusal-refuse" / "refusal-accept"
    tokens int64    — approximate token count (char/4)

For Qwen 3B Coder context window 32K, we truncate canon docs > 4K chars
to keep training tractable.
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
DEFAULT_OUTPUT = Path.home() / "runs" / "sft-train-v1"

MAX_CANON_CHARS = 4000  # truncate canon docs to keep per-example tokens manageable
CANON_MIX_RATIO = 0.80
REFUSAL_MIX_RATIO = 0.20


def truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + "\n...[truncated]"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_sft_dataset", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--canon-dir", type=Path, default=DEFAULT_INPUT_CANON)
    parser.add_argument("--refusal-jsonl", type=Path, default=DEFAULT_INPUT_REFUSAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--canon-cap", type=int, default=1500,
                        help="max canon examples (md + hexa combined)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    random.seed(args.seed)

    import pyarrow.parquet as pq  # type: ignore

    # Load canon
    canon_docs = pq.read_table(args.canon_dir / "canon-docs.parquet").to_pylist()
    canon_src = pq.read_table(args.canon_dir / "canon-source.parquet").to_pylist()
    print(f"canon docs:   {len(canon_docs)}")
    print(f"canon source: {len(canon_src)}")

    # Format canon rows
    canon_rows = []
    for r in canon_docs:
        text = truncate(r["content"], MAX_CANON_CHARS)
        canon_rows.append({
            "text": f"### Canon doc ({r['repo']}/{r['path']}):\n{text}",
            "source": "canon-md",
            "tokens": len(text) // 4,
        })
    for r in canon_src:
        text = truncate(r["content"], MAX_CANON_CHARS)
        canon_rows.append({
            "text": f"### Canon source ({r['repo']}/{r['path']}):\n{text}",
            "source": "canon-hexa",
            "tokens": len(text) // 4,
        })

    # Sample canon
    random.shuffle(canon_rows)
    canon_rows = canon_rows[:args.canon_cap]

    # Load refusal
    refusal_rows = []
    with args.refusal_jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            # skip accept pairs without completion
            if not r.get("completion") or "needs_completion" in r.get("tags", []):
                continue
            refusal_rows.append({
                "text": f"### User:\n{r['prompt']}\n### Assistant:\n{r['completion']}",
                "source": "refusal-refuse",
                "tokens": (len(r['prompt']) + len(r['completion'])) // 4,
            })
    print(f"refusal pairs (refuse): {len(refusal_rows)}")

    # Mix at 80/20
    n_refusal = len(refusal_rows)
    n_canon_target = int(n_refusal * CANON_MIX_RATIO / REFUSAL_MIX_RATIO)
    canon_kept = canon_rows[:n_canon_target] if n_canon_target < len(canon_rows) else canon_rows

    # If we have fewer canon than target, oversample (with replacement)
    if len(canon_kept) < n_canon_target:
        extra = random.choices(canon_rows, k=n_canon_target - len(canon_kept))
        canon_kept = canon_kept + extra

    combined = canon_kept + refusal_rows
    random.shuffle(combined)

    args.output.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.output / "train.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "input_canon": str(args.canon_dir),
        "input_refusal": str(args.refusal_jsonl),
        "rows_total": len(combined),
        "rows_canon": len(canon_kept),
        "rows_refusal": len(refusal_rows),
        "ratio_canon": round(len(canon_kept) / max(len(combined), 1), 2),
        "ratio_refusal": round(len(refusal_rows) / max(len(combined), 1), 2),
        "max_canon_chars": MAX_CANON_CHARS,
        "approx_total_tokens": sum(r["tokens"] for r in combined),
    }
    with (args.output / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)

    print()
    print("=== SUMMARY ===")
    for k, v in manifest.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
