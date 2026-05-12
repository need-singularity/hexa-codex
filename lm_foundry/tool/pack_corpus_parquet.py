#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""pack_corpus_parquet.py — pack a tree of source files into 1-parquet-per-language.

Phase v0.1.3 deliverable per `papers/plan-runbook-v0.1.3.md §4.1`. The
`tool/stack_v2_sample.py` fetcher writes the corpus as 27K+ individual
files; uploading those 1-by-1 to HF hits the 128 commits/hour rate
limit. This script bundles each language into a single parquet file
with content + license metadata so the whole corpus uploads in 1
commit (6 files, ~60 MB total).

INPUT  : `~/runs/corpus/<run_id>/<lang>/<repo_user>/<repo_name>/<path>`
OUTPUT : `~/runs/corpus-parquet/<run_id>/<lang>.parquet`

SCHEMA (per parquet row):
    language    string
    repo        string         # `<user>/<repo_name>`
    path        string         # rel path under repo
    content     string         # full UTF-8 source
    license     string         # SPDX tag from sidecar licenses.jsonl
    permissive  bool
    bytes       int64
    tokens      int64

USAGE:
    python3 tool/pack_corpus_parquet.py \\
        --input  ~/runs/corpus/stack-v2-v0.1.3/ \\
        --output ~/runs/corpus-parquet/stack-v2-v0.1.3/

    # then upload:
    python3 -c "from huggingface_hub import HfApi; \\
        HfApi().upload_folder( \\
            folder_path='~/runs/corpus-parquet/stack-v2-v0.1.3/', \\
            path_in_repo='data', \\
            repo_id='dancinlab/hexa-forge-corpus-stack-v2-sample-v0.1.3', \\
            repo_type='dataset')"

CROSS-LINKS:
    papers/plan-runbook-v0.1.3.md §4.1 — corpus produce step
    tool/stack_v2_sample.py             — upstream producer
    tool/hf_publish.py                  — sister uploader (per-file)
"""
from __future__ import annotations

# NOTE: a sibling `tool/tokenize.py` shadows the stdlib `tokenize` module
# when ANY tool in `tool/` is launched as a script. Defuse before any
# other imports (sees: dataclasses → inspect → linecache → tokenize).
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

DEFAULT_LANGS = ["python", "rust", "typescript", "go", "c", "zig"]
DEFAULT_INPUT = Path.home() / "runs" / "corpus" / "stack-v2-v0.1.3"
DEFAULT_OUTPUT = Path.home() / "runs" / "corpus-parquet" / "stack-v2-v0.1.3"

EXCLUDE_NAMES = {".checkpoint.jsonl", "licenses.jsonl"}


def load_sidecar(lang_root: Path) -> Dict[Tuple[str, str], dict]:
    """Load `licenses.jsonl` produced by tool/stack_v2_sample.py."""
    lookup: Dict[Tuple[str, str], dict] = {}
    sc = lang_root / "licenses.jsonl"
    if not sc.exists():
        return lookup
    for line in sc.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        lookup[(rec.get("repo", ""), rec.get("path", ""))] = rec
    return lookup


def pack_language(lang: str, lang_root: Path, out_dir: Path) -> dict:
    """Pack one language directory into a single parquet file."""
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "pyarrow is required. Install with:\n"
            "    pip install pyarrow\n"
            f"(import error: {exc})"
        ) from exc

    sidecar = load_sidecar(lang_root)
    records = []
    for f in lang_root.rglob("*"):
        if not f.is_file():
            continue
        if f.name in EXCLUDE_NAMES:
            continue
        rel = f.relative_to(lang_root)
        parts = rel.parts
        if len(parts) < 2:
            # files directly under lang_root with no <repo>/<path> shape
            continue
        repo = f"{parts[0]}/{parts[1]}"
        path = "/".join(parts[2:])
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        sc = sidecar.get((repo, path), {})
        records.append({
            "language": lang,
            "repo": repo,
            "path": path,
            "content": content,
            "license": sc.get("license", "UNKNOWN"),
            "permissive": bool(sc.get("permissive", True)),
            "bytes": int(sc.get("bytes", len(content.encode("utf-8")))),
            "tokens": int(sc.get("tokens", 0)),
        })
    if not records:
        return {"language": lang, "rows": 0, "in_bytes": 0, "out_bytes": 0}
    table = pa.Table.from_pylist(records)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{lang}.parquet"
    pq.write_table(table, out_file, compression="zstd", compression_level=3)
    in_bytes = sum(r["bytes"] for r in records)
    out_bytes = out_file.stat().st_size
    return {
        "language": lang,
        "rows": len(records),
        "in_bytes": in_bytes,
        "out_bytes": out_bytes,
        "compression_ratio": (out_bytes / in_bytes) if in_bytes else 1.0,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pack_corpus_parquet",
        description=__doc__.strip().splitlines()[0],
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--languages", default=",".join(DEFAULT_LANGS),
        help=f"comma-separated language list (default: {','.join(DEFAULT_LANGS)})",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    langs = [s.strip() for s in args.languages.split(",") if s.strip()]
    print(f"input : {args.input}")
    print(f"output: {args.output}")
    print(f"langs : {langs}")
    print()
    stats = []
    for lang in langs:
        lang_root = args.input / lang
        if not lang_root.exists():
            print(f"  {lang}: SKIP (missing: {lang_root})")
            continue
        s = pack_language(lang, lang_root, args.output)
        stats.append(s)
        if s["rows"]:
            print(
                f"  {lang:11s}: {s['rows']:>6,} rows / "
                f"in {s['in_bytes']/1024/1024:>5.1f} MB / "
                f"out {s['out_bytes']/1024/1024:>5.1f} MB / "
                f"ratio {s['compression_ratio']:.2f}"
            )
        else:
            print(f"  {lang}: 0 rows")
    print()
    total_rows = sum(s["rows"] for s in stats)
    total_in = sum(s["in_bytes"] for s in stats)
    total_out = sum(s["out_bytes"] for s in stats)
    print(
        f"TOTAL      : {total_rows:>6,} rows / "
        f"in {total_in/1024/1024:>5.1f} MB / "
        f"out {total_out/1024/1024:>5.1f} MB / "
        f"ratio {(total_out/max(total_in,1)):.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
