#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v6.py — v4 + Apple Q/A (NO swift code continuation).

v5 added Swift-file-continuation pairs (~70) which trained the model to
prefer continuation over refusal/canon. Result: hexa-eval STRICT regressed
50% (vs r4 60.7%) and F3 explanation dropped 100→20.

v6 restores the structured-only diet: v4 base + 76 apple hand-crafted
Q/A pairs. SwiftUI / UIKit / Combine knowledge stays; no continuation drift.

OUTPUT
    /home/summer/runs/sft-train-v6/train.jsonl
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
from pathlib import Path

V4_BASE = Path("/home/summer/runs/sft-train-v4/train.jsonl")
APPLE = Path("/home/summer/runs/sft-apple/apple_pairs.jsonl")
OUT = Path("/home/summer/runs/sft-train-v6/train.jsonl")


def main():
    rows = []
    with V4_BASE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"v4 base: {len(rows)}")
    with APPLE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"+ apple: {len(rows)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()
