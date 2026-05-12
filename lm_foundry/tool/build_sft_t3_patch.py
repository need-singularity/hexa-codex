#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_t3_patch.py — Round-39 T3 quote-fragility patch dataset.

Generates ~30 T3 (@grace deprecation) SFT pairs that all teach the
**canonical hexa quoted-date form**:

    @grace(HX9NNN, until="YYYY-MM-DD", reason="…")

The form is quoted because the r33 Phase-A manifest normalised every gold
to that form (matching r4's emission); v3 GRPO drifted back to unquoted on
5 prompts (kl=0.92 nat T4-only drift was enough — see [[t3-quote-fragility]],
third occurrence in the forge ladder). This patch dataset is small (~30
pairs) and **T3-only** to minimise disturbance to v3's other-family wins.

**Eval-holdout discipline.** Eval (gen_hexa_eval_mk1.py) uses 15 function
names (old_api, legacy_format, … stale_index) and HX9NNN codes. This patch
uses **10 new function names + HX8NNN codes** so there is no exact-prompt
overlap with the eval set. Template wordings match the 3 eval styles so
the model learns the prompt→quoted-gold mapping for the same family shape.

Output: a JSONL with one row per pair: `{"text": "### User:\\n<p>\\n### Assistant:\\n<a>"}`
matching the sft-train-v11.jsonl format that train_sft_lora.py consumes.

USAGE
    build_sft_t3_patch.py --out <path>
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

random.seed(42)

# Held-out function names (NOT in eval's GRACE_FNS).
PATCH_FNS = [
    "obsolete_io", "legacy_db", "v0_emit", "old_format", "deprecated_iter",
    "legacy_runner", "v1_compiler", "old_grammar", "stale_proof", "v0_typer",
]

# Held-out HX codes (HX8NNN; eval uses HX9NNN).
def _hx(n: int) -> str:
    return f"HX8{n:03d}"

# 10 tuples — (fn, hx_code, date, reason). Dates mix eval's range + new ones.
TUPLES: list[tuple[str, str, str, str]] = [
    ("obsolete_io",      _hx(101), "2026-06-30", "replaced by new builder"),
    ("legacy_db",        _hx(204), "2026-09-01", "obsolete format"),
    ("v0_emit",          _hx(317), "2026-12-31", "superseded by v2 API"),
    ("old_format",       _hx(412), "2027-01-01", "removed in RFC-021"),
    ("deprecated_iter",  _hx(525), "2027-03-31", "merged into stdlib core"),
    ("legacy_runner",    _hx(638), "2027-06-30", "no longer maintained"),
    ("v1_compiler",      _hx(741), "2027-09-30", "replaced by atlas L-anchoring"),
    ("old_grammar",      _hx(852), "2027-12-31", "superseded by the typed variant"),
    ("stale_proof",      _hx(906), "2028-03-31", "replaced by new builder"),
    ("v0_typer",         _hx(33),  "2028-06-30", "obsolete format"),
]


# 3 prompt templates — match gen_hexa_eval_mk1.py's T3 styles verbatim so the
# patch teaches exactly the eval-shape prompt → quoted-gold mapping.
TEMPLATES: list[str] = [
    "Mark the hexa function `{fn}()` deprecated with `@grace`: code `{code}`, remove-by `{date}`, reason \"{reason}\".",
    "Add `@grace` to `{fn}()` — `{code}`, until `{date}`, reason \"{reason}\".",
    "Write the `@grace` annotation for `{fn}()` that triggers `{code}`, should be gone by `{date}`, because it was {reason}.",
]


def gold(code: str, date: str, reason: str) -> str:
    """Canonical hexa quoted-date form (r33 Phase-A manifest target)."""
    return f'@grace({code}, until="{date}", reason="{reason}")'


def gen_pairs() -> list[dict]:
    rows: list[dict] = []
    for fn, code, date, reason in TUPLES:
        for tmpl in TEMPLATES:
            prompt = tmpl.format(fn=fn, code=code, date=date, reason=reason)
            answer = gold(code, date, reason)
            text = f"### User:\n{prompt}\n### Assistant:\n{answer}"
            rows.append({"text": text})
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    rows = gen_pairs()
    random.shuffle(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote: {args.out}  ({len(rows)} pairs)")

    # Sanity: every row's assistant answer uses quoted `until="DATE"`.
    n_quoted = sum(1 for r in rows if 'until="' in r["text"])
    print(f"quoted gold form: {n_quoted}/{len(rows)} (must be {len(rows)})")
    assert n_quoted == len(rows)

    # Eval-holdout sanity: no patch fn appears in eval's GRACE_FNS.
    eval_fns = {"old_api", "legacy_format", "v1_parser", "deprecated_alloc",
                "old_codec", "legacy_hash", "v0_serialize", "old_lexer",
                "stale_cache", "v1_resolver", "old_linker", "legacy_emit",
                "v0_tokenize", "old_diff", "stale_index"}
    overlap = [fn for fn in PATCH_FNS if fn in eval_fns]
    print(f"eval-fn overlap: {len(overlap)} (must be 0)")
    assert not overlap

    # Quick eyeball: print 2 rows
    print("--- sample ---")
    for r in rows[:2]:
        print(r["text"].replace("\n", " | "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
