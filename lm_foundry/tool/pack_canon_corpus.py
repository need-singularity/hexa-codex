#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""pack_canon_corpus.py — pack hexa-canon docs + sources into SFT-ready parquet.

Phase v0.1.3-r12 deliverable. Walks `~/core/hexa-*/` repos and packs:
- *.md  : hexa-canon docs (specs, ROADMAPs, READMEs)
- *.hexa: hexa-lang source (compiler / stdlib / firmware / verifiers / canon)

Skip patterns:
- legacy/  archive/  .git/  build/  __pycache__/  node_modules/
- *.deprecated.*  *_OLD_*  *.tmp.*
- Files > 200 KB (unusual for canon, likely test fixtures or build artefacts)

OUTPUT
    <output>/canon-docs.parquet   - one row per .md file (~2000 rows expected)
    <output>/canon-source.parquet - one row per .hexa file (~5000 rows expected)
    <output>/MANIFEST.json        - summary + provenance
    <output>/README.md            - dataset card

SCHEMA (both parquet)
    repo          string    e.g. "hexa-codex"
    path          string    rel path under repo
    kind          string    "md" or "hexa"
    content       string    full UTF-8 text
    bytes         int64
    tokens        int64     Qwen2.5-Coder-7B tokenizer count (when --tokenizer given)
    sha256        string    content sha256[:16]

CROSS-LINKS
    papers/plan-runbook-v0.1.3.md §4.5 (SFT data prep, deferred to v0.2.0)
    tool/pack_corpus_parquet.py — sister tool (Stack v1 corpus)
    tool/hf_publish.py target=stack-v2-sample is the public-Stack flavour;
        this one would publish to dancinlab/hexa-forge-corpus-hexa-canon-v1
        (target reservation — not yet wired into hf_publish.py).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Iterator, Optional

DEFAULT_CORE_ROOT = Path.home() / "mac_home" / "core"
DEFAULT_OUTPUT = Path.home() / "runs" / "corpus" / "hexa-canon-v1"
DEFAULT_TOKENIZER = "Qwen/Qwen2.5-Coder-7B"
MAX_FILE_BYTES = 200 * 1024  # 200 KB cap per file (overridable via --max-bytes)
# v1 packed only md+hexa; v2 (corpus-hexa-canon-v2) adds py/toml/json for the
# bigger spec-grounded corpus lever (v0.3.0). The `kind` column distinguishes them.
DEFAULT_KINDS = "md,hexa"

SKIP_DIR_NAMES = {
    ".git", "build", "__pycache__", "node_modules",
    "legacy", "archive", "raw_archive", ".cache",
    ".pytest_cache", "venv", ".venv", "dist", "target",
}
SKIP_NAME_PATTERNS = (".deprecated.", "_OLD_", ".tmp.")


def _category(ext: str) -> str:
    """Coarse bucket for the output parquet split."""
    if ext == "md":
        return "docs"
    if ext == "hexa":
        return "source"
    return "aux"  # py / toml / json / yaml / ... (v2+)


def walk_repo(repo_root: Path, kinds=("md", "hexa"), max_bytes: int = MAX_FILE_BYTES) -> Iterator[tuple]:
    """Yield (ext, repo_name, path) for each non-skipped file under repo_root."""
    repo_name = repo_root.name
    kset = set(kinds)
    for root, dirs, files in _os.walk(repo_root):
        # prune
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        rp = Path(root)
        for f in files:
            full = rp / f
            ext = full.suffix.lstrip(".")
            if ext not in kset:
                continue
            if any(pat in f for pat in SKIP_NAME_PATTERNS):
                continue
            try:
                sz = full.stat().st_size
            except OSError:
                continue
            if sz > max_bytes or sz == 0:
                continue
            yield (ext, repo_name, full)


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pack_canon_corpus", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--core-root", type=Path, default=DEFAULT_CORE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tokenizer", default=DEFAULT_TOKENIZER, help="HF tokenizer id (or 'none' to skip)")
    parser.add_argument("--repos", default="", help="comma-list of repos; default = all hexa-*")
    parser.add_argument("--kinds", default=DEFAULT_KINDS, help="comma-list of extensions to pack (default: md,hexa; v2: md,hexa,py,toml,json)")
    parser.add_argument("--max-bytes", type=int, default=MAX_FILE_BYTES, help="per-file byte cap (default 200 KB; v2 often uses 500 KB)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())

    if args.repos:
        repo_paths = [args.core_root / r for r in args.repos.split(",")]
    else:
        repo_paths = sorted(p for p in args.core_root.glob("hexa-*") if p.is_dir())

    args.output.mkdir(parents=True, exist_ok=True)
    print(f"core-root: {args.core_root}", flush=True)
    print(f"output   : {args.output}", flush=True)
    print(f"repos    : {len(repo_paths)} ({', '.join(p.name for p in repo_paths[:5])} ... )", flush=True)

    print(f"kinds    : {kinds}  max_bytes={args.max_bytes}", flush=True)

    if args.dry_run:
        from collections import Counter
        c = Counter()
        for rp in repo_paths:
            for ext, _, _ in walk_repo(rp, kinds=kinds, max_bytes=args.max_bytes):
                c[ext] += 1
        print(f"dry-run: would pack {sum(c.values())} files: {dict(c)}")
        return 0

    # Tokenizer (lazy)
    tok = None
    if args.tokenizer.lower() != "none":
        try:
            from transformers import AutoTokenizer  # type: ignore
            tok = AutoTokenizer.from_pretrained(args.tokenizer)
            print(f"tokenizer: {args.tokenizer} (vocab={tok.vocab_size})", flush=True)
        except Exception as exc:
            print(f"tokenizer load failed; falling back to char/4 estimate: {exc}", flush=True)
            tok = None

    buckets: dict[str, list] = {"docs": [], "source": [], "aux": []}
    t_start = time.monotonic()
    for rp in repo_paths:
        from collections import Counter
        per = Counter()
        for ext, repo_name, full in walk_repo(rp, kinds=kinds, max_bytes=args.max_bytes):
            content = read_text(full)
            if content is None:
                continue
            rel = str(full.relative_to(rp))
            n_bytes = len(content.encode("utf-8"))
            n_tokens = (
                len(tok.encode(content, add_special_tokens=False))
                if tok is not None
                else (n_bytes // 4)
            )
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            row = {
                "repo": repo_name,
                "path": rel,
                "kind": ext,
                "content": content,
                "bytes": n_bytes,
                "tokens": n_tokens,
                "sha256": sha,
            }
            buckets[_category(ext)].append(row)
            per[ext] += 1
        print(f"  {repo_name:20s}: {dict(per)}", flush=True)

    # Write parquet (3 files: docs / source / aux)
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore

    out_files = {}
    for cat, rows_ in buckets.items():
        if not rows_:
            continue
        fpath = args.output / f"canon-{cat}.parquet"
        pq.write_table(pa.Table.from_pylist(rows_), fpath, compression="zstd", compression_level=3)
        out_files[cat] = fpath

    manifest = {
        "core_root": str(args.core_root),
        "repos_scanned": len(repo_paths),
        "kinds": list(kinds),
        "max_file_bytes": args.max_bytes,
        "rows": {cat: len(r) for cat, r in buckets.items()},
        "rows_total": sum(len(r) for r in buckets.values()),
        "bytes_total": sum(r["bytes"] for rs in buckets.values() for r in rs),
        "tokens_total": sum(r["tokens"] for rs in buckets.values() for r in rs),
        "out_mb": {cat: round(f.stat().st_size / 1024 / 1024, 2) for cat, f in out_files.items()},
        "tokenizer": args.tokenizer,
        "elapsed_s": round(time.monotonic() - t_start, 1),
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
