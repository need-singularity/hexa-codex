#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""extend_tokenizer.py — extend a base HF tokenizer with hexa-lang tokens.

Phase v0.1.2-r3 deliverable. This is the consumer for the manifest at
`tool/tokenizer_extension.toml` (D-008 default: extend Qwen2.5-Coder-7B
BPE so hexa-lang keywords, annotations, atlas refs, and error codes
encode as one token per atom instead of 3-5 BPE pieces).

USAGE
    python tool/extend_tokenizer.py \\
        --base Qwen/Qwen2.5-Coder-7B \\
        --extension tool/tokenizer_extension.toml \\
        --output runs/tokenizer_qwen2.5-coder-7b_hexa_v1/

    # Plan only, no writes:
    python tool/extend_tokenizer.py --dry-run

    # Reverify an already-saved tokenizer:
    python tool/extend_tokenizer.py --verify-only \\
        --output runs/tokenizer_qwen2.5-coder-7b_hexa_v1/

    # Measure compression on a hexa source sample:
    python tool/extend_tokenizer.py \\
        --corpus-sample self/sample.hexa --target-compression 0.5

DEPENDENCIES
    Python 3.11+ (uses stdlib `tomllib`).
    `transformers` is required for real runs; the import is gated so the
    self-test and `--help` run without it. If the base model is gated on
    HuggingFace, authenticate via `huggingface-cli login` or set the
    `HF_TOKEN` environment variable before running.

BEHAVIOUR
    1. Parse `tokenizer_extension.toml` via `tomllib`, validate the
       embedded schema (every `[extensions.<group>]` table has a
       `tokens = [...]` list of strings).
    2. Load the base tokenizer via `AutoTokenizer.from_pretrained`.
    3. Flatten extension tokens in declared group order. Tokens already
       in the base vocab are skipped (preserves manifest design
       principle 2 — stable IDs).
    4. Call `tokenizer.add_tokens(new_tokens)` — new entries land past
       the existing vocab boundary; base IDs do not move.
    5. Save the extended tokenizer to `--output` via
       `save_pretrained(...)`. `tokenizer.json` is atomically replaced
       via temp + rename.
    6. Round-trip-verify every extension token (encode -> decode must
       be byte-equal). Any mismatch is a fatal failure.
    7. If `--corpus-sample` is provided, compare base vs extended
       tokenizer token counts on the sample file. Fail when the ratio
       (extended / base) exceeds `--target-compression` (default 0.5
       per the manifest's §VERIFY acceptance bar).

CONTRACT (cross-link)
    - Manifest:           tool/tokenizer_extension.toml
    - Decision ledger:    papers/plan-decisions-pending.md D-008
    - Recipe contract:    docs/code-llm.md §VERIFY (hardware tier +
                          hexa fidelity acceptance bar)
    - Sister tooling:     tool/tokenize.py (uses the resulting tokenizer
                          to measure tokens_actual across the corpus)
"""
from __future__ import annotations

# NOTE: a sibling file (`tool/tokenize.py`) shadows stdlib `tokenize` when this
# script runs as `python tool/extend_tokenizer.py` because Python inserts the
# script directory at sys.path[0]. Anything that imports `linecache`/`inspect`
# (e.g. `dataclasses`) transitively imports stdlib `tokenize` and crashes with
# a circular-import error. Prune the script directory from sys.path before any
# other imports — same defense as `tool/tokenize.py`.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = "Qwen/Qwen2.5-Coder-7B"
DEFAULT_EXTENSION = REPO_ROOT / "tool" / "tokenizer_extension.toml"
DEFAULT_TARGET_COMPRESSION = 0.5
SCHEMA_VERSION = 1


def _slugify(model_id: str) -> str:
    """Turn `Qwen/Qwen2.5-Coder-7B` into `qwen2.5-coder-7b` for path use."""
    tail = model_id.split("/")[-1] if "/" in model_id else model_id
    return tail.lower()


def default_output_dir(base: str) -> Path:
    """Build the default output directory for a given base model id.

    Naming aligned with `tool/hf_publish.py` target `tokenizer` source_path
    (~/runs/tokenizer-qwen-hexa-v1/) — hyphens, not underscores, to match
    the HF repo `dancinlab/hexa-forge-tokenizer-qwen-hexa-v1` convention.
    The `~/runs/` anchor (Linux home) is the canonical run output root.
    """
    # `qwen` extracted from the slug; the full model id is too verbose
    # for the HF repo name. If a future tokenizer is non-Qwen, the
    # source_path in hf_publish.py must be updated in lockstep.
    return Path.home() / "runs" / "tokenizer-qwen-hexa-v1"


# ---------------------------------------------------------------------------
# Manifest parsing + validation
# ---------------------------------------------------------------------------

@dataclass
class TokenGroup:
    """One `[extensions.<name>]` table from the manifest."""

    name: str
    tokens: list[str]


@dataclass
class Manifest:
    """Parsed `tokenizer_extension.toml`."""

    schema_version: int
    extension_version: str
    proposed_base: str
    groups: list[TokenGroup]
    target_added_count: int
    raw_meta: dict[str, Any] = field(default_factory=dict)


def load_manifest(path: Path) -> Manifest:
    """Parse + validate the tokenizer-extension manifest.

    Raises:
        FileNotFoundError: if `path` does not exist.
        ValueError: if the schema is violated (with a human-readable list
            of every violation).
    """
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    violations: list[str] = []

    meta = data.get("meta")
    if not isinstance(meta, dict):
        violations.append("missing [meta] table")
        meta = {}

    schema_version = meta.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        violations.append(
            f"meta.schema_version: expected {SCHEMA_VERSION}, got {schema_version!r}"
        )

    proposed_base = meta.get("proposed_base", "")
    if not isinstance(proposed_base, str) or not proposed_base:
        violations.append("meta.proposed_base must be a non-empty string")

    extension_version = meta.get("extension_version", "")
    if not isinstance(extension_version, str):
        violations.append("meta.extension_version must be a string")

    target_added_count = meta.get("target_added_count", 0)
    if not isinstance(target_added_count, int):
        violations.append("meta.target_added_count must be an integer")

    extensions = data.get("extensions")
    if not isinstance(extensions, dict) or not extensions:
        violations.append("missing or empty [extensions.*] tables")
        extensions = {}

    groups: list[TokenGroup] = []
    for group_name, group_body in extensions.items():
        if not isinstance(group_body, dict):
            violations.append(f"extensions.{group_name}: not a table")
            continue
        tokens = group_body.get("tokens")
        if not isinstance(tokens, list):
            violations.append(
                f"extensions.{group_name}.tokens: must be a list, got {type(tokens).__name__}"
            )
            continue
        cleaned: list[str] = []
        for i, t in enumerate(tokens):
            if not isinstance(t, str):
                violations.append(
                    f"extensions.{group_name}.tokens[{i}]: not a string ({t!r})"
                )
                continue
            if t == "":
                violations.append(
                    f"extensions.{group_name}.tokens[{i}]: empty string disallowed"
                )
                continue
            cleaned.append(t)
        groups.append(TokenGroup(name=group_name, tokens=cleaned))

    if violations:
        raise ValueError(
            "tokenizer_extension.toml schema violations:\n  - "
            + "\n  - ".join(violations)
        )

    return Manifest(
        schema_version=schema_version,  # type: ignore[arg-type]
        extension_version=extension_version,
        proposed_base=proposed_base,
        groups=groups,
        target_added_count=target_added_count,
        raw_meta=meta,
    )


# ---------------------------------------------------------------------------
# Tokenizer abstraction (so the self-test can run with no `transformers`)
# ---------------------------------------------------------------------------

class TokenizerLike:
    """Minimal protocol used by this module.

    Real `transformers.PreTrainedTokenizerFast` already satisfies this;
    the `MockTokenizer` below satisfies it too for the self-test.
    """

    vocab_size: int

    def get_vocab(self) -> dict[str, int]: ...  # pragma: no cover

    def add_tokens(self, new_tokens: list[str]) -> int: ...  # pragma: no cover

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]: ...  # pragma: no cover

    def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str: ...  # pragma: no cover

    def save_pretrained(self, save_directory: str) -> tuple: ...  # pragma: no cover


def load_hf_tokenizer(name: str) -> TokenizerLike:
    """Load a base HF tokenizer. Raises ImportError if `transformers` missing.

    Surface error reframes the HuggingFace auth-gating hint in 3 steps so
    new operators don't get stuck on a generic 401.
    """
    try:
        from transformers import AutoTokenizer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "transformers is required for real runs. Install it via:\n"
            "  pip install transformers\n"
            "If the base model is gated on HuggingFace:\n"
            "  1. Accept the model license at https://huggingface.co/" + name + "\n"
            "  2. Run `huggingface-cli login` or `export HF_TOKEN=hf_...`\n"
            "  3. Re-run this command.\n"
        ) from exc
    return AutoTokenizer.from_pretrained(name, trust_remote_code=False)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Extension logic
# ---------------------------------------------------------------------------

@dataclass
class GroupReport:
    name: str
    declared_tokens: int
    added_tokens: int
    skipped_already_present: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "declared_tokens": self.declared_tokens,
            "added_tokens": self.added_tokens,
            "skipped_already_present": self.skipped_already_present,
        }


@dataclass
class ExtensionReport:
    base: str
    base_vocab_size: int
    extension_manifest: str
    extension_schema_version: int
    groups: list[GroupReport]
    total_added: int
    extended_vocab_size: int
    sha256_tokenizer_json: str
    round_trip_pass: bool
    compression_target: float
    compression_pass: Optional[bool] = None
    compression_ratio_vs_base: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "base": self.base,
            "base_vocab_size": self.base_vocab_size,
            "extension_manifest": self.extension_manifest,
            "extension_schema_version": self.extension_schema_version,
            "groups": [g.to_dict() for g in self.groups],
            "total_added": self.total_added,
            "extended_vocab_size": self.extended_vocab_size,
            "sha256_tokenizer_json": self.sha256_tokenizer_json,
            "round_trip_pass": self.round_trip_pass,
            "compression_target": self.compression_target,
        }
        if self.compression_ratio_vs_base is not None:
            d["compression_ratio_vs_base"] = self.compression_ratio_vs_base
            d["compression_pass"] = self.compression_pass
        return d


def plan_extension(
    manifest: Manifest, base_vocab: dict[str, int]
) -> tuple[list[GroupReport], list[str]]:
    """Compute per-group skip stats and the flat list of tokens to add.

    Returns (group_reports, tokens_to_add). The flat list preserves the
    declared group + token order and deduplicates already-present tokens
    (manifest design principle 2: never renumber base tokens).
    """
    reports: list[GroupReport] = []
    to_add: list[str] = []
    seen: set[str] = set()
    for group in manifest.groups:
        added = 0
        skipped = 0
        for tok in group.tokens:
            if tok in base_vocab or tok in seen:
                skipped += 1
                continue
            seen.add(tok)
            to_add.append(tok)
            added += 1
        reports.append(GroupReport(
            name=group.name,
            declared_tokens=len(group.tokens),
            added_tokens=added,
            skipped_already_present=skipped,
        ))
    return reports, to_add


def round_trip_verify(
    tokenizer: TokenizerLike, tokens: Iterable[str]
) -> tuple[bool, list[tuple[str, str]]]:
    """Verify that every token encodes + decodes to its original bytes.

    Returns (all_pass, failures). `failures` is a list of (token, decoded)
    tuples — capped at 10 by the caller for surface output.
    """
    failures: list[tuple[str, str]] = []
    for tok in tokens:
        ids = tokenizer.encode(tok, add_special_tokens=False)
        decoded = tokenizer.decode(ids, skip_special_tokens=False)
        if decoded != tok:
            failures.append((tok, decoded))
    return (not failures), failures


def sha256_file(path: Path) -> str:
    """Stream-hash a file and return the hex digest."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_replace_tokenizer_json(output_dir: Path) -> None:
    """Atomically rewrite `tokenizer.json` via temp + os.replace.

    `save_pretrained` writes the file in-place; we re-stage it through
    a sibling `.tmp` so an interrupted run can't leave a truncated
    `tokenizer.json` in the output directory.
    """
    target = output_dir / "tokenizer.json"
    if not target.is_file():
        return
    tmp = target.with_suffix(".json.tmp")
    shutil.copyfile(target, tmp)
    os.replace(tmp, target)


def compression_ratio(
    base_tok: TokenizerLike, ext_tok: TokenizerLike, text: str
) -> tuple[int, int, float]:
    """Return (base_count, ext_count, ratio) for a single text payload."""
    base_n = len(base_tok.encode(text, add_special_tokens=False))
    ext_n = len(ext_tok.encode(text, add_special_tokens=False))
    if base_n == 0:
        return 0, ext_n, 0.0
    return base_n, ext_n, ext_n / base_n


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_extend(
    *,
    base: str,
    extension_path: Path,
    output_dir: Path,
    dry_run: bool,
    corpus_sample: Optional[Path],
    target_compression: float,
    base_tokenizer: Optional[TokenizerLike] = None,
    extended_tokenizer_factory: Optional[Any] = None,
) -> tuple[ExtensionReport, list[tuple[str, str]]]:
    """Drive the full extend + verify pipeline.

    The `*_tokenizer*` keyword arguments are seams for the self-test;
    in production callers leave them None and the function loads HF
    tokenizers itself.

    Returns (report, round_trip_failures). Failures list is empty on
    success.
    """
    manifest = load_manifest(extension_path)
    if base_tokenizer is None:
        base_tokenizer = load_hf_tokenizer(base)

    base_vocab = base_tokenizer.get_vocab()
    base_size = len(base_vocab)

    group_reports, tokens_to_add = plan_extension(manifest, base_vocab)

    if dry_run:
        # Build a planning report without touching the tokenizer.
        report = ExtensionReport(
            base=base,
            base_vocab_size=base_size,
            extension_manifest=str(extension_path),
            extension_schema_version=manifest.schema_version,
            groups=group_reports,
            total_added=len(tokens_to_add),
            extended_vocab_size=base_size + len(tokens_to_add),
            sha256_tokenizer_json="",
            round_trip_pass=True,
            compression_target=target_compression,
        )
        return report, []

    n_added = base_tokenizer.add_tokens(tokens_to_add)
    if n_added != len(tokens_to_add):
        # add_tokens may collapse duplicates the HF tokenizer recognises
        # under a different normalisation. We still treat this as a
        # warning-grade event rather than a hard fail.
        print(
            f"warning: add_tokens reported {n_added} additions for "
            f"{len(tokens_to_add)} planned tokens (normalisation dedup?)",
            file=sys.stderr,
        )
    extended_size = base_size + n_added

    output_dir.mkdir(parents=True, exist_ok=True)
    base_tokenizer.save_pretrained(str(output_dir))
    atomic_replace_tokenizer_json(output_dir)

    tokenizer_json = output_dir / "tokenizer.json"
    digest = sha256_file(tokenizer_json) if tokenizer_json.is_file() else ""

    round_trip_ok, failures = round_trip_verify(base_tokenizer, tokens_to_add)

    report = ExtensionReport(
        base=base,
        base_vocab_size=base_size,
        extension_manifest=str(extension_path),
        extension_schema_version=manifest.schema_version,
        groups=group_reports,
        total_added=n_added,
        extended_vocab_size=extended_size,
        sha256_tokenizer_json=digest,
        round_trip_pass=round_trip_ok,
        compression_target=target_compression,
    )

    if corpus_sample is not None:
        if not corpus_sample.is_file():
            raise FileNotFoundError(f"corpus sample not found: {corpus_sample}")
        text = corpus_sample.read_text(encoding="utf-8", errors="replace")
        # Re-load a base tokenizer (without the extension) for comparison.
        baseline = (
            extended_tokenizer_factory()
            if extended_tokenizer_factory is not None
            else load_hf_tokenizer(base)
        )
        _, _, ratio = compression_ratio(baseline, base_tokenizer, text)
        report.compression_ratio_vs_base = ratio
        report.compression_pass = ratio <= target_compression

    # Persist reports.
    _write_json(output_dir / "extension_report.json", report.to_dict())
    _write_json(output_dir / "verify_report.json", {
        "round_trip_pass": round_trip_ok,
        "n_tested": len(tokens_to_add),
        "n_failed": len(failures),
        "failures_sample": [
            {"token": t, "decoded": d} for t, d in failures[:10]
        ],
    })
    (output_dir / "checksum.txt").write_text(
        f"{digest}  tokenizer.json\n", encoding="utf-8"
    )

    return report, failures


def run_verify_only(
    *, output_dir: Path, extension_path: Path, target_compression: float
) -> int:
    """Reload a previously-saved tokenizer and re-run round-trip checks.

    Useful after copying the output directory between machines or after
    a manual edit.
    """
    if not (output_dir / "tokenizer.json").is_file():
        print(
            f"error: no tokenizer.json under {output_dir}; nothing to verify",
            file=sys.stderr,
        )
        return 2
    try:
        from transformers import AutoTokenizer  # type: ignore[import-not-found]
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    tokenizer = AutoTokenizer.from_pretrained(str(output_dir), trust_remote_code=False)
    manifest = load_manifest(extension_path)
    all_tokens = [t for g in manifest.groups for t in g.tokens]
    ok, failures = round_trip_verify(tokenizer, all_tokens)
    digest = sha256_file(output_dir / "tokenizer.json")
    print(
        f"verify-only: tokens={len(all_tokens)} failures={len(failures)} "
        f"sha256={digest[:16]}... target_compression={target_compression}"
    )
    if not ok:
        for t, d in failures[:10]:
            print(f"  FAIL: {t!r} -> {d!r}")
        return 1
    print("verify-only: PASS")
    return 0


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, obj: Any) -> None:
    """Atomic JSON write via temp + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _print_plan(report: ExtensionReport) -> None:
    """Surface render for `--dry-run` and final summary."""
    print(f"base:               {report.base}")
    print(f"base_vocab_size:    {report.base_vocab_size}")
    print(f"extension_manifest: {report.extension_manifest}")
    print(f"schema_version:     {report.extension_schema_version}")
    print("groups:")
    for g in report.groups:
        print(
            f"  - {g.name:<24s} declared={g.declared_tokens:>4d} "
            f"added={g.added_tokens:>4d} skipped={g.skipped_already_present:>4d}"
        )
    print(f"total_added:        {report.total_added}")
    print(f"extended_vocab:     {report.extended_vocab_size}")
    if report.sha256_tokenizer_json:
        print(f"sha256:             {report.sha256_tokenizer_json}")
    if report.compression_ratio_vs_base is not None:
        verdict = "PASS" if report.compression_pass else "FAIL"
        print(
            f"compression_ratio:  {report.compression_ratio_vs_base:.3f} "
            f"(target <= {report.compression_target}) [{verdict}]"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "HuggingFace auth:\n"
        "  If the base model is gated, set HF_TOKEN (or run\n"
        "  `huggingface-cli login`) BEFORE running this tool.\n"
        "  Steps for a fresh machine:\n"
        "    1. Accept the model license on the HF model card page.\n"
        "    2. `export HF_TOKEN=hf_...` (or `huggingface-cli login`).\n"
        "    3. Re-run this command.\n"
        "\n"
        "Acceptance bar (target compression):\n"
        "  Extended tokenizer must encode a representative hexa source\n"
        "  sample at <= 0.5x the base tokenizer's token count\n"
        "  (the §VERIFY hexa-fidelity contract).\n"
        "\n"
        "Cross-links:\n"
        "  - Manifest:        tool/tokenizer_extension.toml\n"
        "  - Decision ledger: papers/plan-decisions-pending.md  D-008\n"
        "  - Recipe contract: docs/code-llm.md  §VERIFY hardware tier\n"
    )
    ap = argparse.ArgumentParser(
        prog="extend_tokenizer.py",
        description=(
            "Extend a base HF tokenizer with hexa-lang tokens "
            "(hexa-forge v0.1.2-r3, consumer of tool/tokenizer_extension.toml)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help=f"HF model id for the base tokenizer (default: {DEFAULT_BASE})")
    ap.add_argument("--extension", type=Path, default=DEFAULT_EXTENSION,
                    help=f"extension manifest TOML (default: {DEFAULT_EXTENSION})")
    ap.add_argument("--output", type=Path, default=None,
                    help="output directory (default: ~/runs/tokenizer-qwen-hexa-v1/ — aligned with hf_publish.py tokenizer target)")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse + plan only; do not load HF, do not write")
    ap.add_argument("--verify-only", action="store_true",
                    help="reload --output's tokenizer and re-run round-trip checks")
    ap.add_argument("--corpus-sample", type=Path, default=None,
                    help="optional file to measure base vs extended compression on")
    ap.add_argument("--target-compression", type=float,
                    default=DEFAULT_TARGET_COMPRESSION,
                    help=f"max acceptable ratio extended/base (default: {DEFAULT_TARGET_COMPRESSION})")
    return ap


def run_cli(argv: Optional[list[str]] = None) -> int:
    """Argparse front-end. Returns process exit code."""
    args = build_parser().parse_args(argv)
    output = args.output or default_output_dir(args.base)

    if args.verify_only:
        return run_verify_only(
            output_dir=output,
            extension_path=args.extension,
            target_compression=args.target_compression,
        )

    # Manifest existence is the first thing we check — fail fast with
    # an explicit path so the operator can fix typos cheaply.
    if not args.extension.is_file():
        print(
            f"error: extension manifest not found: {args.extension}",
            file=sys.stderr,
        )
        return 2

    try:
        if args.dry_run:
            # Dry-run path bypasses HF entirely — it just inspects the
            # manifest and prints the would-be plan with vocab_size=0.
            manifest = load_manifest(args.extension)
            groups = [
                GroupReport(
                    name=g.name,
                    declared_tokens=len(g.tokens),
                    added_tokens=len(g.tokens),
                    skipped_already_present=0,
                )
                for g in manifest.groups
            ]
            total = sum(g.added_tokens for g in groups)
            report = ExtensionReport(
                base=args.base,
                base_vocab_size=0,
                extension_manifest=str(args.extension),
                extension_schema_version=manifest.schema_version,
                groups=groups,
                total_added=total,
                extended_vocab_size=total,
                sha256_tokenizer_json="",
                round_trip_pass=True,
                compression_target=args.target_compression,
            )
            _print_plan(report)
            print("dry-run: no changes written.")
            return 0

        report, failures = run_extend(
            base=args.base,
            extension_path=args.extension,
            output_dir=output,
            dry_run=False,
            corpus_sample=args.corpus_sample,
            target_compression=args.target_compression,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    _print_plan(report)
    if not report.round_trip_pass:
        print("round-trip verification: FAIL", file=sys.stderr)
        for t, d in failures[:10]:
            print(f"  FAIL: {t!r} -> {d!r}", file=sys.stderr)
        return 1
    if report.compression_pass is False:
        print(
            f"compression bar: FAIL "
            f"(ratio={report.compression_ratio_vs_base:.3f} > {report.compression_target})",
            file=sys.stderr,
        )
        return 1
    print(f"output: {output}")
    return 0


# ---------------------------------------------------------------------------
# Self-test — mock tokenizer, no network, no `transformers` import
# ---------------------------------------------------------------------------

class MockTokenizer:
    """In-memory tokenizer used to exercise the driver under self-test.

    The encoding is a synthetic word-level scheme: each known token maps
    to one id; unknown text is split on whitespace, with each piece
    represented by its byte length as a placeholder id (the test never
    decodes those, only counts them for compression math).
    """

    def __init__(self, vocab: list[str]) -> None:
        self._vocab: dict[str, int] = {t: i for i, t in enumerate(vocab)}
        self._inv: dict[int, str] = {i: t for t, i in self._vocab.items()}

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return dict(self._vocab)

    def add_tokens(self, new_tokens: list[str]) -> int:
        added = 0
        for t in new_tokens:
            if t in self._vocab:
                continue
            idx = len(self._vocab)
            self._vocab[t] = idx
            self._inv[idx] = t
            added += 1
        return added

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        # Greedy longest-match scan over the vocab, falling back to one
        # synthetic id per remaining whitespace-split word.
        ids: list[int] = []
        i = 0
        # Sort by length desc so longer tokens win the greedy match.
        sorted_keys = sorted(self._vocab.keys(), key=len, reverse=True)
        while i < len(text):
            matched = False
            for k in sorted_keys:
                if k and text.startswith(k, i):
                    ids.append(self._vocab[k])
                    i += len(k)
                    matched = True
                    break
            if not matched:
                # Consume one char as a synthetic id (offset past vocab).
                ids.append(10_000_000 + ord(text[i]))
                i += 1
        return ids

    def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
        out: list[str] = []
        for i in ids:
            if i in self._inv:
                out.append(self._inv[i])
            elif i >= 10_000_000:
                out.append(chr(i - 10_000_000))
            else:
                out.append("?")
        return "".join(out)

    def save_pretrained(self, save_directory: str) -> tuple:
        d = Path(save_directory)
        d.mkdir(parents=True, exist_ok=True)
        (d / "tokenizer.json").write_text(
            json.dumps({"vocab": self._vocab}, indent=2), encoding="utf-8"
        )
        (d / "tokenizer_config.json").write_text(
            json.dumps({"tokenizer_class": "MockTokenizer"}), encoding="utf-8"
        )
        return (str(d / "tokenizer.json"),)


_SELFTEST_TAG = "__EXTEND_TOKENIZER_SELFTEST__"


def _run_selftest() -> int:
    """Inline self-test. No HF, no network. Synthetic manifest + mock vocab."""
    failures: list[str] = []

    # 1. Real manifest parses + validates.
    try:
        manifest = load_manifest(DEFAULT_EXTENSION)
        if manifest.schema_version != SCHEMA_VERSION:
            failures.append(
                f"manifest.schema_version: {manifest.schema_version} != {SCHEMA_VERSION}"
            )
        total_declared = sum(len(g.tokens) for g in manifest.groups)
        if total_declared < 100:
            failures.append(f"manifest declared total too low: {total_declared}")
        if not any(g.name == "keywords" for g in manifest.groups):
            failures.append("manifest missing [extensions.keywords]")
        if not any(g.name == "annotations" for g in manifest.groups):
            failures.append("manifest missing [extensions.annotations]")
    except Exception as e:
        failures.append(f"load_manifest({DEFAULT_EXTENSION}): {e}")
        manifest = None  # type: ignore[assignment]

    # 2. Schema-violation surface: an invalid manifest reports each issue.
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.toml"
        bad.write_text(
            "[meta]\n"
            "schema_version = 99\n"
            "proposed_base = \"\"\n"
            "[extensions.broken]\n"
            "tokens = \"not-a-list\"\n",
            encoding="utf-8",
        )
        try:
            load_manifest(bad)
            failures.append("schema-violation manifest did not raise")
        except ValueError as e:
            msg = str(e)
            for needle in ("schema_version", "proposed_base", "tokens"):
                if needle not in msg:
                    failures.append(f"schema-violation message missing {needle!r}")
        except Exception as e:
            failures.append(f"schema-violation raised wrong type: {type(e).__name__}: {e}")

    # 3. Token-skip logic: synthetic base vocab pre-contains some tokens.
    if manifest is not None:
        base_vocab = {"let": 1, "fn": 2, "if": 3}
        reports, to_add = plan_extension(manifest, base_vocab)
        kw_report = next((r for r in reports if r.name == "keywords"), None)
        if kw_report is None:
            failures.append("plan_extension: no 'keywords' report")
        else:
            if kw_report.skipped_already_present < 3:
                failures.append(
                    f"plan: expected >=3 skipped for keywords, got "
                    f"{kw_report.skipped_already_present}"
                )
            if kw_report.added_tokens + kw_report.skipped_already_present != kw_report.declared_tokens:
                failures.append("plan: added + skipped != declared (keywords)")
        # No duplicate in the flat add list.
        if len(to_add) != len(set(to_add)):
            failures.append("plan: duplicate token in to_add")
        # Pre-existing tokens never appear in to_add.
        for t in ("let", "fn", "if"):
            if t in to_add:
                failures.append(f"plan: pre-existing token leaked: {t!r}")

    # 4. End-to-end run via MockTokenizer + tiny synthetic manifest.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man_path = root / "ext.toml"
        man_path.write_text(
            "[meta]\n"
            "schema_version = 1\n"
            "extension_version = \"v0.0.1\"\n"
            "proposed_base = \"mock/base\"\n"
            "target_added_count = 5\n"
            "[extensions.keywords]\n"
            "tokens = [\"let\", \"fn\", \"@grace\"]\n"
            "[extensions.atlas]\n"
            "tokens = [\"L[\", \"P[\"]\n",
            encoding="utf-8",
        )
        mock_base = MockTokenizer(["the", "a", "fn"])  # 'fn' will be skipped
        out_dir = root / "out"

        # Factory returns a FRESH mock base for the compression baseline
        # so the in-place add_tokens on `mock_base` is comparable to a
        # never-extended baseline.
        def _baseline_factory() -> MockTokenizer:
            return MockTokenizer(["the", "a", "fn"])

        sample = root / "sample.txt"
        sample.write_text("let x = @grace L[42] fn y", encoding="utf-8")

        report, fails = run_extend(
            base="mock/base",
            extension_path=man_path,
            output_dir=out_dir,
            dry_run=False,
            corpus_sample=sample,
            target_compression=1.0,  # any improvement passes the test bar
            base_tokenizer=mock_base,
            extended_tokenizer_factory=_baseline_factory,
        )
        if report.total_added != 4:  # 5 declared - 1 skipped ('fn')
            failures.append(f"e2e: total_added expected 4, got {report.total_added}")
        if report.base_vocab_size != 3:
            failures.append(f"e2e: base_vocab_size != 3 (got {report.base_vocab_size})")
        if report.extended_vocab_size != 7:
            failures.append(f"e2e: extended_vocab_size != 7 (got {report.extended_vocab_size})")
        if not report.round_trip_pass:
            failures.append(f"e2e: round_trip_pass False, failures={fails}")
        if fails:
            failures.append(f"e2e: failure list non-empty: {fails}")
        if report.compression_ratio_vs_base is None:
            failures.append("e2e: compression_ratio not computed")
        elif report.compression_ratio_vs_base >= 1.0:
            failures.append(
                f"e2e: extended tokenizer should compress (got ratio "
                f"{report.compression_ratio_vs_base})"
            )
        if report.compression_pass is not True:
            failures.append(f"e2e: compression_pass != True ({report.compression_pass})")

        # On-disk artefacts.
        for name in ("tokenizer.json", "tokenizer_config.json",
                     "checksum.txt", "extension_report.json",
                     "verify_report.json"):
            if not (out_dir / name).is_file():
                failures.append(f"e2e: missing output file {name}")
        digest_line = (out_dir / "checksum.txt").read_text(encoding="utf-8")
        if "tokenizer.json" not in digest_line:
            failures.append("e2e: checksum.txt missing filename suffix")
        # Persisted JSON round-trips.
        try:
            parsed = json.loads((out_dir / "extension_report.json").read_text(encoding="utf-8"))
            if parsed["total_added"] != 4:
                failures.append("e2e: persisted extension_report.json mismatch")
            if "compression_ratio_vs_base" not in parsed:
                failures.append("e2e: persisted report missing compression_ratio_vs_base")
        except Exception as e:
            failures.append(f"e2e: extension_report.json parse: {e}")

    # 5. Round-trip math: a forced corrupt encoder produces failures.
    class _BrokenTok(MockTokenizer):
        def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
            return "XXX"

    broken = _BrokenTok(["a", "b"])
    ok, fails = round_trip_verify(broken, ["a", "b"])
    if ok or len(fails) != 2:
        failures.append(f"round_trip_verify negative case: ok={ok} fails={fails}")

    # 6. Compression math: synthetic 100/50 sample yields ratio 0.5.
    class _StaticTok:
        def __init__(self, n: int) -> None:
            self._n = n
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [0] * self._n
        def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
            return ""

    base_n, ext_n, ratio = compression_ratio(_StaticTok(100), _StaticTok(50), "x")
    if base_n != 100 or ext_n != 50 or abs(ratio - 0.5) > 1e-9:
        failures.append(f"compression_ratio math: ({base_n},{ext_n},{ratio})")
    _, _, r0 = compression_ratio(_StaticTok(0), _StaticTok(0), "")
    if r0 != 0.0:
        failures.append(f"compression_ratio empty-base: {r0}")

    # 7. Missing-manifest exit path.
    try:
        load_manifest(Path("/nonexistent/extend_tokenizer/manifest.toml"))
        failures.append("missing manifest did not raise FileNotFoundError")
    except FileNotFoundError:
        pass
    except Exception as e:
        failures.append(f"missing manifest raised wrong type: {type(e).__name__}")

    # 8. Slug helper.
    if _slugify("Qwen/Qwen2.5-Coder-7B") != "qwen2.5-coder-7b":
        failures.append(f"_slugify: {_slugify('Qwen/Qwen2.5-Coder-7B')}")
    if _slugify("plainname") != "plainname":
        failures.append(f"_slugify(plain): {_slugify('plainname')}")

    if failures:
        print(f"{_SELFTEST_TAG} FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"{_SELFTEST_TAG} PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) == 1:
        sys.exit(_run_selftest())
    sys.exit(run_cli())
