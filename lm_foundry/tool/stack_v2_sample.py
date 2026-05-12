"""Stack v2 permissive subset 5% sampler for hexa-forge v0.1.2 corpus audit.

Implements ROADMAP.md §4 item 2 and closes decision D-009 (license-clean
Stack v2 perm volume) by measuring real token counts on a deterministic
5% sample. Extrapolates to validate the docs/code-llm.md STRUCT
pretrain-bias row claim of ~600B tokens for the permissive subset.

Only rows with `permissive == True` are included; the per-sample
`license` field is recorded to a sidecar JSONL for downstream audit.

Dependencies (install before live use):
    pip install huggingface-hub datasets transformers

Authentication for live runs:
    export HUGGING_FACE_HUB_TOKEN=hf_xxx   # required for gated bigcode org

This file is self-contained: the embedded __main__ block runs a
dry-run + extrapolation-math unit test against a synthetic mock
dataset and prints PASS / FAIL. No network is required for the test.
"""

from __future__ import annotations

# NOTE: a sibling `tool/tokenize.py` shadows the stdlib `tokenize` module
# when ANY tool in `tool/` is launched as a script (Python prepends the
# script's directory to sys.path). The shadow propagates through
# `dataclasses` → `inspect` → `linecache` → `tokenize` and crashes import.
# Prune the script directory before any other imports.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import dataclasses
import datetime as _dt
import hashlib
import json
import logging
import os
import pathlib
import sys
import typing as _t

LOGGER = logging.getLogger("stack_v2_sample")

# hexa-forge core langs per docs/code-llm.md STRUCT row.
# sql excluded (ships from db-native), hexa excluded (ships from hexa-native).
# swift added 2026-05-12 for Apple-app stack coverage (SwiftUI / UIKit / etc).
DEFAULT_LANGS: _t.Tuple[str, ...] = (
    "python",
    "rust",
    "typescript",
    "go",
    "c",
    "zig",
    "swift",
)

# v0.1.3 default: Stack v1 (inline content + permissive-filtered upstream).
# v2 has metadata-only rows that require Software Heritage resolution;
# SWH support lands in v0.2.0 — see stream_dataset() for details.
DEFAULT_DATASET = "bigcode/the-stack"
DEFAULT_CONFIG = "default"  # ignored for Stack v1 (uses data_dir per language)
DEFAULT_TOKENIZER = "Qwen/Qwen2.5-Coder-7B"  # D-007 proposed base
DEFAULT_SAMPLE_PCT = 5.0
DEFAULT_SEED = 42
DEFAULT_MAX_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB cap per language
# Canonical paths align with `tool/hf_publish.py` stack-v2-sample target
# (`~/runs/corpus/stack-v2-v0.1.3/`) and runbook §4.1. Absolute paths
# so the defaults work regardless of cwd at invocation time.
DEFAULT_OUTPUT = _os.path.expanduser("~/runs/corpus/stack-v2-v0.1.3/")
DEFAULT_STATS = _os.path.expanduser("~/runs/stack_v2_sample.json")

# Stable modulus for deterministic 5% selection.
HASH_MOD = 100_000


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class LangStats:
    """Per-language aggregate counters."""

    files: int = 0
    bytes: int = 0
    tokens: int = 0
    truncated: bool = False

    def tokens_per_byte(self) -> float:
        return (self.tokens / self.bytes) if self.bytes else 0.0

    def to_dict(self) -> _t.Dict[str, _t.Any]:
        return {
            "files": self.files,
            "bytes": self.bytes,
            "tokens": self.tokens,
            "tokens_per_byte": round(self.tokens_per_byte(), 6),
            "truncated": self.truncated,
        }


@dataclasses.dataclass
class SampleRow:
    """A single dataset row as we care about it."""

    repo: str
    path: str
    content: str
    language: str
    permissive: bool
    license: str

    @property
    def key(self) -> str:
        return f"{self.repo}/{self.path}"


# ---------------------------------------------------------------------------
# Deterministic sampling
# ---------------------------------------------------------------------------


def stable_bucket(key: str, seed: int) -> int:
    """Return a stable integer in [0, HASH_MOD) for a row key + seed.

    Uses BLAKE2b for determinism across Python versions and platforms.
    """

    digest = hashlib.blake2b(
        f"{seed}:{key}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % HASH_MOD


def should_sample(key: str, seed: int, sample_pct: float) -> bool:
    """Return True if this key is selected by the (seed, pct) plan."""

    if sample_pct <= 0.0:
        return False
    if sample_pct >= 100.0:
        return True
    threshold = int(round(HASH_MOD * (sample_pct / 100.0)))
    return stable_bucket(key, seed) < threshold


# ---------------------------------------------------------------------------
# Tokenizer wrapper (lazy import so --help / --dry-run work without deps)
# ---------------------------------------------------------------------------


class TokenizerWrapper:
    """Thin wrapper around an HF tokenizer with a byte-count fallback."""

    def __init__(self, hf_id: str, dry_run: bool = False) -> None:
        self.hf_id = hf_id
        self.dry_run = dry_run
        self._tok: _t.Any = None
        if not dry_run:
            self._load()

    def _load(self) -> None:
        try:
            from transformers import AutoTokenizer  # type: ignore
        except ImportError as exc:  # pragma: no cover - import-time error path
            raise SystemExit(
                "transformers is required for live runs. Install with:\n"
                "    pip install transformers\n"
                f"(import error: {exc})"
            ) from exc
        self._tok = AutoTokenizer.from_pretrained(self.hf_id, use_fast=True)

    def count(self, text: str) -> int:
        if self._tok is None:
            # Dry-run / mock path: deterministic proxy ~ 1 token / 4 bytes.
            return max(1, len(text.encode("utf-8")) // 4)
        ids = self._tok.encode(text, add_special_tokens=False)
        return len(ids)


# ---------------------------------------------------------------------------
# Output + checkpoint helpers
# ---------------------------------------------------------------------------


def _safe_relpath(repo: str, path: str) -> str:
    """Sanitize repo/path into a filesystem-safe relative path."""

    parts = [p for p in f"{repo}/{path}".split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "unnamed"


def write_sample(
    out_root: pathlib.Path, lang: str, row: SampleRow
) -> pathlib.Path:
    rel = _safe_relpath(row.repo, row.path)
    dest = out_root / lang / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(row.content, encoding="utf-8", errors="replace")
    return dest


def append_sidecar(
    out_root: pathlib.Path,
    lang: str,
    row: SampleRow,
    token_count: int,
) -> None:
    sidecar = out_root / lang / "licenses.jsonl"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "repo": row.repo,
        "path": row.path,
        "license": row.license,
        "permissive": row.permissive,
        "bytes": len(row.content.encode("utf-8")),
        "tokens": token_count,
    }
    with sidecar.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def checkpoint_path(out_root: pathlib.Path, lang: str) -> pathlib.Path:
    return out_root / lang / ".checkpoint.jsonl"


def load_checkpoint(out_root: pathlib.Path, lang: str) -> _t.Set[str]:
    ck = checkpoint_path(out_root, lang)
    if not ck.exists():
        return set()
    keys: _t.Set[str] = set()
    with ck.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                keys.add(json.loads(line)["key"])
            except (KeyError, json.JSONDecodeError):
                continue
    return keys


def append_checkpoint(out_root: pathlib.Path, lang: str, key: str) -> None:
    ck = checkpoint_path(out_root, lang)
    ck.parent.mkdir(parents=True, exist_ok=True)
    with ck.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": key}) + "\n")


# ---------------------------------------------------------------------------
# Dataset streaming
# ---------------------------------------------------------------------------


def stream_dataset(
    dataset: str,
    config: str,
    language: str,
) -> _t.Iterator[SampleRow]:
    """Stream rows for a single language from HuggingFace.

    Two dataset shapes supported:

    1. **Stack v1** (`bigcode/the-stack`, `bigcode/the-stack-dedup`,
       `bigcode/the-stack-smol`) — inline `content` column +
       permissive-only filter applied upstream. Per-language slicing
       via `data_dir=data/<language>`. **Default at v0.1.3** since v2
       requires SWH content resolution (deferred to v0.2.0).
    2. **Stack v2** (`bigcode/the-stack-v2`) — metadata-only rows
       (blob_id + content_id pointing at Software Heritage). Content
       fetch via SWH is NOT YET implemented; v2 path will raise a
       clear error directing operators to v1 or to v0.2.0 SWH support.
       Per-language slicing via `name=<Language>` (capitalised).
    """

    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "datasets is required for live runs. Install with:\n"
            "    pip install datasets huggingface-hub\n"
            f"(import error: {exc})"
        ) from exc

    if not os.environ.get("HUGGING_FACE_HUB_TOKEN"):
        raise SystemExit(
            "HUGGING_FACE_HUB_TOKEN is not set. Stack v1/v2 (bigcode/*)\n"
            "is gated; you must:\n"
            "  1. Accept the dataset license at\n"
            f"     https://huggingface.co/datasets/{dataset}\n"
            "  2. export HUGGING_FACE_HUB_TOKEN=hf_xxx\n"
            "  3. Re-run this script."
        )

    # Detect dataset shape from the dataset name.
    is_stack_v1 = dataset in {
        "bigcode/the-stack",
        "bigcode/the-stack-dedup",
        "bigcode/the-stack-smol",
    }
    is_stack_v2 = dataset.startswith("bigcode/the-stack-v2")

    if is_stack_v2:
        raise SystemExit(
            "bigcode/the-stack-v2 is metadata-only (rows carry "
            "blob_id/content_id pointing at Software Heritage; no "
            "inline `content` column). SWH content resolution lands "
            "in v0.2.0. For v0.1.3 use --dataset bigcode/the-stack "
            "(permissive-filtered + inline content)."
        )

    if is_stack_v1:
        # Stack v1: per-language via data_dir, config param ignored.
        ds = load_dataset(
            dataset,
            data_dir=f"data/{language.lower()}",
            split="train",
            streaming=True,
        )
    else:
        # Generic / custom dataset: pass `config` as the `name` kwarg.
        ds = load_dataset(
            dataset,
            name=config,
            split="train",
            streaming=True,
        )

    for raw in ds:
        # Stack v1 already filters by language via data_dir; defensive
        # check is cheap and handles custom datasets that mix languages.
        row_lang = str(raw.get("language") or raw.get("lang") or "").lower()
        if row_lang and row_lang != language.lower():
            continue
        # Stack v1 field names: `max_stars_repo_*` (preferred) or
        # `max_issues_repo_*` / `max_forks_repo_*` as fallbacks. Stack v2
        # would use `repo_name` / `path` directly. We try the v2 names
        # first (cheap), then the v1 fallbacks.
        repo = (
            raw.get("repo_name")
            or raw.get("repo")
            or raw.get("max_stars_repo_name")
            or raw.get("max_issues_repo_name")
            or raw.get("max_forks_repo_name")
            or "unknown"
        )
        path = (
            raw.get("path")
            or raw.get("blob_path")
            or raw.get("max_stars_repo_path")
            or raw.get("max_issues_repo_path")
            or raw.get("max_forks_repo_path")
            or "unknown"
        )
        # Stack v1: `max_stars_repo_licenses` is a list of SPDX strings.
        # Stack v2 (if ever wired): `detected_licenses` similar shape.
        licenses_raw = (
            raw.get("max_stars_repo_licenses")
            or raw.get("max_issues_repo_licenses")
            or raw.get("max_forks_repo_licenses")
            or raw.get("detected_licenses")
            or []
        )
        if isinstance(licenses_raw, list) and licenses_raw:
            license_value = ",".join(str(x) for x in licenses_raw)
        else:
            license_value = str(raw.get("license") or "UNKNOWN")
        # Stack v1 in `data/<lang>/` is upstream-permissive-filtered, so
        # `permissive=True` is the default. Custom datasets that opt out
        # can set a per-row `permissive` field explicitly.
        permissive = bool(raw.get("permissive", True))
        yield SampleRow(
            repo=str(repo),
            path=str(path),
            content=str(raw.get("content") or ""),
            language=language,
            permissive=permissive,
            license=license_value,
        )


# ---------------------------------------------------------------------------
# Core sampling loop
# ---------------------------------------------------------------------------


def sample_language(
    *,
    language: str,
    row_iter: _t.Iterable[SampleRow],
    tokenizer: TokenizerWrapper,
    out_root: pathlib.Path,
    seed: int,
    sample_pct: float,
    max_bytes: int,
    dry_run: bool,
    max_files_per_lang: int = 0,
) -> LangStats:
    """Run the sample loop for a single language.

    `max_files_per_lang = 0` (default) means no per-language file cap;
    otherwise the loop stops after that many files have been kept.
    Useful for fast micro-fetches (the deterministic sampler still
    iterates row-by-row over the upstream stream, so very low
    sample-pct values can take a long time without an early-stop cap).
    """

    stats = LangStats()
    seen = set() if dry_run else load_checkpoint(out_root, language)

    for row in row_iter:
        if not row.permissive:
            continue
        key = row.key
        if key in seen:
            continue
        if not should_sample(key, seed, sample_pct):
            continue

        content_bytes = row.content.encode("utf-8")
        size = len(content_bytes)
        if stats.bytes + size > max_bytes:
            LOGGER.info(
                "language %s: max-bytes cap (%d) reached, truncating",
                language,
                max_bytes,
            )
            stats.truncated = True
            break

        tokens = tokenizer.count(row.content)
        stats.files += 1
        stats.bytes += size
        stats.tokens += tokens

        if not dry_run:
            write_sample(out_root, language, row)
            append_sidecar(out_root, language, row, tokens)
            append_checkpoint(out_root, language, key)
            seen.add(key)  # in-memory dedup for the rest of this run

        if max_files_per_lang and stats.files >= max_files_per_lang:
            LOGGER.info(
                "language %s: max-files-per-lang cap (%d) reached",
                language,
                max_files_per_lang,
            )
            stats.truncated = True
            break

    return stats


# ---------------------------------------------------------------------------
# Aggregation + stats
# ---------------------------------------------------------------------------


def extrapolate(tokens: int, sample_pct: float) -> int:
    """Linear extrapolation: sample_tokens / sample_pct * 100."""

    if sample_pct <= 0.0:
        return 0
    return int(round(tokens / sample_pct * 100.0))


def build_stats_blob(
    *,
    dataset: str,
    config: str,
    sample_pct: float,
    tokenizer_id: str,
    seed: int,
    started_at: str,
    finished_at: str,
    by_language: _t.Dict[str, LangStats],
) -> _t.Dict[str, _t.Any]:
    total_files = sum(s.files for s in by_language.values())
    total_bytes = sum(s.bytes for s in by_language.values())
    total_tokens = sum(s.tokens for s in by_language.values())

    extrapolated_per_lang = {
        lang: extrapolate(s.tokens, sample_pct)
        for lang, s in by_language.items()
    }

    return {
        "dataset": dataset,
        "config": config,
        "sample_pct": sample_pct,
        "tokenizer": tokenizer_id,
        "seed": seed,
        "started_at": started_at,
        "finished_at": finished_at,
        "by_language": {
            lang: s.to_dict() for lang, s in by_language.items()
        },
        "total": {
            "files": total_files,
            "bytes": total_bytes,
            "tokens": total_tokens,
        },
        "extrapolated_full_corpus_tokens": extrapolate(
            total_tokens, sample_pct
        ),
        "extrapolated_per_language": extrapolated_per_lang,
    }


def write_stats(stats_path: pathlib.Path, blob: _t.Dict[str, _t.Any]) -> None:
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(
        json.dumps(blob, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stack_v2_sample",
        description=(
            "Stack v2 permissive subset 5% sampler for hexa-forge v0.1.2 "
            "corpus audit. Only rows with permissive == True are included "
            "(license-clean), per ROADMAP.md D-009. Tokenizes via the "
            "Qwen2.5-Coder tokenizer (D-007 proposed base) and extrapolates "
            "the full-corpus token count for the docs/code-llm.md "
            "~600B-token claim."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGS),
        help="comma-separated language list; defaults to hexa-forge core langs",
    )
    parser.add_argument("--sample-pct", type=float, default=DEFAULT_SAMPLE_PCT)
    parser.add_argument("--tokenizer", default=DEFAULT_TOKENIZER)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--stats", default=DEFAULT_STATS)
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="safety cap per language in bytes",
    )
    parser.add_argument(
        "--max-files-per-lang",
        type=int,
        default=0,
        help="0 (default) = no cap; >0 = stop after N files per language. "
        "Useful for fast micro-fetches; deterministic sampler still "
        "iterates row-by-row over the upstream stream.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse args + print plan; do not fetch dataset or write files",
    )
    return parser


def parse_languages(raw: str) -> _t.List[str]:
    return [tok.strip().lower() for tok in raw.split(",") if tok.strip()]


def main(argv: _t.Optional[_t.Sequence[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_arg_parser().parse_args(argv)
    languages = parse_languages(args.languages)
    out_root = pathlib.Path(args.output)
    stats_path = pathlib.Path(args.stats)

    LOGGER.info("plan: dataset=%s config=%s", args.dataset, args.config)
    LOGGER.info("plan: languages=%s sample_pct=%.3f seed=%d",
                languages, args.sample_pct, args.seed)
    LOGGER.info("plan: tokenizer=%s", args.tokenizer)
    LOGGER.info("plan: output=%s stats=%s max_bytes=%d",
                out_root, stats_path, args.max_bytes)

    if args.dry_run:
        LOGGER.info("--dry-run: skipping fetch + writes")

    tokenizer = TokenizerWrapper(args.tokenizer, dry_run=args.dry_run)

    started_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    by_language: _t.Dict[str, LangStats] = {}

    for lang in languages:
        LOGGER.info("language=%s: starting", lang)
        if args.dry_run:
            row_iter: _t.Iterable[SampleRow] = iter(())  # empty in dry-run
        else:
            row_iter = stream_dataset(args.dataset, args.config, lang)
        stats = sample_language(
            language=lang,
            row_iter=row_iter,
            tokenizer=tokenizer,
            out_root=out_root,
            seed=args.seed,
            sample_pct=args.sample_pct,
            max_bytes=args.max_bytes,
            dry_run=args.dry_run,
            max_files_per_lang=args.max_files_per_lang,
        )
        by_language[lang] = stats
        LOGGER.info(
            "language=%s: files=%d bytes=%d tokens=%d truncated=%s",
            lang, stats.files, stats.bytes, stats.tokens, stats.truncated,
        )

    finished_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    blob = build_stats_blob(
        dataset=args.dataset,
        config=args.config,
        sample_pct=args.sample_pct,
        tokenizer_id=args.tokenizer,
        seed=args.seed,
        started_at=started_at,
        finished_at=finished_at,
        by_language=by_language,
    )

    if args.dry_run:
        LOGGER.info("--dry-run: would write stats to %s", stats_path)
        LOGGER.info("--dry-run: stats blob preview:\n%s",
                    json.dumps(blob, indent=2))
    else:
        write_stats(stats_path, blob)
        LOGGER.info("wrote stats to %s", stats_path)

    return 0


# ---------------------------------------------------------------------------
# Self-test (synthetic mock dataset)
# ---------------------------------------------------------------------------


def _mock_rows(language: str) -> _t.List[SampleRow]:
    """Return 5 deterministic fake rows for self-test."""

    rows: _t.List[SampleRow] = []
    for i in range(5):
        content = f"// {language} sample {i}\n" + ("x" * (40 * (i + 1)))
        rows.append(
            SampleRow(
                repo=f"acme/{language}-demo-{i}",
                path=f"src/file_{i}.{language[:2]}",
                content=content,
                language=language,
                # Mark one row non-permissive to verify the filter.
                permissive=(i != 0),
                license="MIT" if i != 0 else "GPL-3.0",
            )
        )
    return rows


def _run_self_test() -> bool:
    """Run dry-run-style self-test. Return True on PASS."""

    tokenizer = TokenizerWrapper("mock", dry_run=True)
    out_root = pathlib.Path("/tmp/stack_v2_sample_selftest_unused")
    sample_pct = 100.0  # take everything that survives the permissive filter
    seed = 42

    by_lang: _t.Dict[str, LangStats] = {}
    for lang in ("python", "rust"):
        stats = sample_language(
            language=lang,
            row_iter=iter(_mock_rows(lang)),
            tokenizer=tokenizer,
            out_root=out_root,
            seed=seed,
            sample_pct=sample_pct,
            max_bytes=10**12,
            dry_run=True,
        )
        by_lang[lang] = stats

    # Each lang has 5 rows, 1 is non-permissive -> 4 kept.
    expected_files = 4
    for lang, stats in by_lang.items():
        if stats.files != expected_files:
            print(f"FAIL: {lang} files={stats.files} expected={expected_files}")
            return False
        if stats.tokens <= 0 or stats.bytes <= 0:
            print(f"FAIL: {lang} tokens/bytes non-positive")
            return False

    # Extrapolation math: at sample_pct=10, extrapolate(100, 10) == 1000.
    if extrapolate(100, 10.0) != 1000:
        print("FAIL: extrapolate(100, 10) != 1000")
        return False
    # At sample_pct=5, extrapolate(50, 5) == 1000.
    if extrapolate(50, 5.0) != 1000:
        print("FAIL: extrapolate(50, 5) != 1000")
        return False
    # Zero-pct guard.
    if extrapolate(123, 0.0) != 0:
        print("FAIL: extrapolate with 0 pct should be 0")
        return False

    # Determinism: same key/seed → same bucket.
    if stable_bucket("a/b", 42) != stable_bucket("a/b", 42):
        print("FAIL: stable_bucket non-deterministic")
        return False
    # Different seed → (almost certainly) different bucket.
    if stable_bucket("a/b", 42) == stable_bucket("a/b", 43):
        print("FAIL: stable_bucket seed has no effect")
        return False

    # Sampling fraction sanity: at pct=100 every key should be selected.
    if not should_sample("any/key", 1, 100.0):
        print("FAIL: should_sample(100) returned False")
        return False
    if should_sample("any/key", 1, 0.0):
        print("FAIL: should_sample(0) returned True")
        return False

    # stats blob shape.
    blob = build_stats_blob(
        dataset="mock", config="permissive",
        sample_pct=5.0, tokenizer_id="mock",
        seed=42, started_at="t0", finished_at="t1",
        by_language=by_lang,
    )
    required_keys = {
        "dataset", "config", "sample_pct", "tokenizer", "seed",
        "started_at", "finished_at", "by_language", "total",
        "extrapolated_full_corpus_tokens", "extrapolated_per_language",
    }
    if not required_keys.issubset(blob.keys()):
        print(f"FAIL: missing stats keys {required_keys - set(blob.keys())}")
        return False

    # Extrapolation in real blob: sample_pct=5 -> total*20.
    if blob["extrapolated_full_corpus_tokens"] != extrapolate(
        blob["total"]["tokens"], 5.0
    ):
        print("FAIL: extrapolated_full_corpus_tokens mismatch")
        return False

    print("PASS: self-test ok "
          f"(per-lang files={expected_files}, "
          f"extrapolation math verified, determinism verified)")
    return True


if __name__ == "__main__":
    # If invoked with no args, run the self-test. Otherwise act as a CLI.
    if len(sys.argv) == 1:
        ok = _run_self_test()
        sys.exit(0 if ok else 1)
    sys.exit(main())
