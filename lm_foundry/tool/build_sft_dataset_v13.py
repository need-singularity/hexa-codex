#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v13.py — the careful round: keep only what r12 proved worked.

r12 (v11 + 330 pairs) was a tradeoff: T2 atlas 59->78 and T7 layering 55->67 went UP
(the "explicit prove-vs-explore" and "rule-explained" pairs worked), but T3 @grace
65->40, T8 refusal 79->64, and T5 25->16 went DOWN — the 200 narrow bare-code T5
pairs destabilized the model (degenerate repetition, family confusion) without
teaching the arbitrary HX map, and disturbed the other format-precise families.

r13 = v11 base (2,521, the best adapter so far at 63.5% Mk.I) + ONLY the two blocks
that helped: 30 T2-explicit + 40 T7-ruled. No bulk T5, no T4-declonly.
Total v13: ~2,591 rows. Expected: r11's strengths + the T2/T7 gains, ~66-68% Mk.I.

(After r13: the LoRA-r16 / Qwen-3B SFT line has plateaued ~63-68% on Mk.I — gate ③
≥80% needs a structural change: bigger base / full-FT / bigger canon corpus / more
epochs. See ROADMAP round 27.)

OUTPUT
    /home/summer/runs/sft-train-v13/train.jsonl
    /home/summer/runs/sft-train-v13/MANIFEST.json
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
# keep tool/ on path JUST long enough to import the v12 generators, then prune
_sys.path.insert(0, _THIS_DIR)
from build_sft_dataset_v12 import gen_t2, gen_t7  # noqa: E402
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json  # noqa: E402
import random  # noqa: E402
from pathlib import Path  # noqa: E402

random.seed(42)

V11_BASE = Path("/home/summer/runs/sft-train-v11/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v13")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def main() -> int:
    if not V11_BASE.exists():
        print(f"ERROR: v11 base not found at {V11_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V11_BASE.read_text().splitlines() if l.strip()]
    print(f"v11 base: {len(base)}")
    blocks = {"t2_atlas_explicit": gen_t2(30), "t7_layering_ruled": gen_t7(40)}
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:24s} {len(rows_):4d}")
        added.extend(rows_)
    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.2.0-r13",
        "base": str(V11_BASE),
        "base_rows": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": "keep only r12's working blocks (T2-explicit, T7-ruled) on the r11 base; no bulk T5",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
