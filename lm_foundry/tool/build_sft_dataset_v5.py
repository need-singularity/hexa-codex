#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v5.py — v4 + Apple/Swift (SwiftUI / UIKit / Combine).

User explicitly requested Swift / Apple-app knowledge after r4.
Per `tool/synth_apple_sft.py` we have 76 hand-crafted Apple SFT pairs.
Add ~100 Swift completion pairs sampled from the freshly-fetched
`bigcode/the-stack` swift partition for code-style diversity.

Mix:
- v4 base (1,589 rows)
- Apple SFT (76 hand-crafted pairs)
- Swift code samples (100 pairs from stack-v1-swift)

Total: ~1,765 rows.

OUTPUT
    /home/summer/runs/sft-train-v5/train.jsonl
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json, random
from pathlib import Path

random.seed(42)

V4_BASE = Path("/home/summer/runs/sft-train-v4/train.jsonl")
APPLE_PAIRS = Path("/home/summer/runs/sft-apple/apple_pairs.jsonl")
SWIFT_CORPUS = Path("/home/summer/runs/corpus/stack-v1-swift/swift")
OUT = Path("/home/summer/runs/sft-train-v5/train.jsonl")


def fmt(prompt, completion):
    return {"text": f"### User:\n{prompt}\n### Assistant:\n{completion}"}


SWIFT_PROMPT_TEMPLATES = [
    "Write a Swift function similar in shape to this:\n```swift\n{snippet}\n```",
    "Refactor or extend this Swift code:\n```swift\n{snippet}\n```",
    "Explain (briefly) what this Swift snippet does:\n```swift\n{snippet}\n```",
    "Continue this Swift file:\n```swift\n{snippet}\n```",
]


def gen_swift_pairs(n: int = 100) -> list[dict]:
    """Pull short swift snippets from the corpus + frame as Q/A."""
    out = []
    if not SWIFT_CORPUS.exists():
        return out
    files = list(SWIFT_CORPUS.rglob("*.swift"))
    random.shuffle(files)
    for f in files[: n * 3]:
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        # only short snippets (< 800 chars) — keeps SFT input length tame
        if len(text) > 800 or len(text) < 80:
            continue
        if "import" not in text and "func" not in text:
            continue
        # split into a "head" (first ~40% of file) used as the prompt context
        # and a "completion" (rest). This teaches the model to continue.
        cut = max(80, len(text) // 3)
        head = text[:cut].rstrip()
        completion = text[cut:].lstrip()
        if not completion:
            continue
        prompt = (
            "Continue this Swift file:\n```swift\n" + head + "\n```"
        )
        out.append(fmt(prompt, completion))
        if len(out) >= n:
            break
    return out


def main():
    rows = []
    # 1. v4 base
    if V4_BASE.exists():
        with V4_BASE.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        print(f"v4 base rows:  {len(rows)}")
    # 2. apple hand-crafted pairs
    if APPLE_PAIRS.exists():
        with APPLE_PAIRS.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        print(f"after apple:   {len(rows)}")
    # 3. swift corpus continuation pairs
    swift_pairs = gen_swift_pairs(100)
    print(f"swift code pairs: {len(swift_pairs)}")
    rows.extend(swift_pairs)
    print(f"total v5:      {len(rows)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()
