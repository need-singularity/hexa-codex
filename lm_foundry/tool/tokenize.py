#!/usr/bin/env python3
"""tokenize.py — count real tokens per fetched corpus source.

Phase v0.1.2 deliverable per `papers/plan-domain-coverage.md §7` token
roll-up reconciliation. Walks every manifest entry with
`fetch_status = "fetched"`, finds the on-disk payload under
`corpus/<verb>/<stage>/<id>/`, tokenises it with the configured HF
tokenizer (default `Qwen/Qwen2.5-Coder-7B`), and:

1. Updates `tokens_actual` per entry (atomic manifest write).
2. Aggregates per-stage, per-tier, per-license totals into
   `runs/corpus_tokenize.<date>.json`.

PAYLOAD DISCOVERY
-----------------
For each fetched entry, the tool inspects the entry's corpus directory
and concatenates the relevant text files for tokenisation. Priority:

    - `text.md`           — preferred (HTML extraction output)
    - `repo/`             — git clone: walk all text-ish files
    - `*.md` / `*.txt`    — plain-text drops
    - `*.json`            — included verbatim

Binary (`raw.pdf`) and the original `raw.html` are NOT tokenised —
`raw.html` is kept for provenance only; `text.md` is its tokenisation
input. PDFs remain `pdf-pending` and are skipped.

TOKENIZER
---------
The default tokenizer is Qwen's coder tokenizer
(`Qwen/Qwen2.5-Coder-7B`). It is loaded via
`transformers.AutoTokenizer.from_pretrained(...)`. If the model gates
behind a HuggingFace login, set `HF_TOKEN` in your environment (see
`--help`). For self-test purposes a deterministic byte-based stub is
used (no network, no `transformers` import).

AGGREGATE OUTPUT
----------------
Written to `runs/corpus_tokenize.<date>.json`:

    {
      "tokenizer": "Qwen/Qwen2.5-Coder-7B",
      "generated_at": "...",
      "by_stage":   {<stage>:   {"files": N, "tokens": N}},
      "by_tier":    {<tier>:    {"files": N, "tokens": N}},
      "by_license": {<license>: {"files": N, "tokens": N}},
      "total":      {"files": N, "tokens": N}
    }

Manifest fields read:
    url, license, weight, tier, tokens_est, tokens_actual, fetch_status,
    sha256_corpus, stage (implicit), id (implicit), verb (implicit)

Manifest fields written (only with `--update-manifest`):
    tokens_actual

Dependencies: stdlib + `transformers` (for the real tokenizer). The
self-test path requires no third-party packages.
"""
from __future__ import annotations

# NOTE: this file's basename collides with the stdlib `tokenize` module. When
# launched as `python tool/tokenize.py`, Python inserts `tool/` at sys.path[0],
# which makes `linecache` (and anything else that imports stdlib `tokenize`)
# pick up THIS file and crash with a circular-import error. We defuse that by
# pruning the script directory from sys.path before any other imports, then
# loading our local `_common` helper explicitly via importlib.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Load _common.py by absolute path to avoid re-adding the script dir to
# sys.path (which would re-trigger the shadowing problem above).
def _load_common():
    mod_name = "_hexa_forge_common"
    spec = importlib.util.spec_from_file_location(
        mod_name, _os.path.join(_THIS_DIR, "_common.py"),
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load tool/_common.py")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so `@dataclass` (and anything else inspecting
    # `cls.__module__`) can resolve back to a real module object.
    _sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_common = _load_common()
DEFAULT_CORPUS_DIR = _common.DEFAULT_CORPUS_DIR
DEFAULT_MANIFEST = _common.DEFAULT_MANIFEST
DEFAULT_RUNS_DIR = _common.DEFAULT_RUNS_DIR
Entry = _common.Entry
apply_manifest_updates = _common.apply_manifest_updates
atomic_write_text = _common.atomic_write_text
ensure_dir = _common.ensure_dir
iter_entries = _common.iter_entries
load_manifest = _common.load_manifest
now_iso = _common.now_iso
today_iso = _common.today_iso


DEFAULT_TOKENIZER = "Qwen/Qwen2.5-Coder-7B"

# File extensions considered text and worth tokenising in a git clone.
TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".rs", ".go", ".c", ".h", ".cc", ".hh", ".cpp", ".hpp", ".cxx",
    ".java", ".kt", ".scala", ".swift", ".m", ".mm",
    ".rb", ".php", ".pl", ".lua", ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".prisma", ".graphql",
    ".md", ".rst", ".txt", ".markdown",
    ".toml", ".yaml", ".yml", ".json",
    ".hexa", ".hx",
})

# Files we never tokenise (binary or already accounted for).
EXCLUDED_NAMES: frozenset[str] = frozenset({
    "raw.html",
    "raw.pdf",
    "REPO_MANIFEST.tsv",
    "GIT_HEAD",
    "LICENSE.attribution",
})


# ---------------------------------------------------------------------------
# Tokenizer abstraction
# ---------------------------------------------------------------------------

TokenizeFn = Callable[[str], int]


def load_hf_tokenizer(name: str) -> TokenizeFn:
    """Return a callable that maps text -> token count, backed by HF.

    Raises ImportError if `transformers` is not installed.
    """
    try:
        from transformers import AutoTokenizer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "transformers is required for real tokenization. "
            "Install via `pip install transformers` and authenticate to "
            "HuggingFace (`huggingface-cli login` or set HF_TOKEN env var) "
            "if the model is gated."
        ) from exc

    tok = AutoTokenizer.from_pretrained(name, trust_remote_code=False)

    def _count(text: str) -> int:
        # `encode` returns input_ids; len() is the token count.
        return len(tok.encode(text, add_special_tokens=False))

    return _count


def stub_tokenizer(text: str) -> int:
    """Deterministic byte-based stub used in self-tests (no HF dep).

    Returns ceil(len(utf8_bytes) / 4) — a reasonable proxy where the
    self-test only needs aggregation math to be correct, not absolute
    numbers.
    """
    n = len(text.encode("utf-8"))
    return (n + 3) // 4


# ---------------------------------------------------------------------------
# Payload discovery
# ---------------------------------------------------------------------------

def gather_payload_text(target_dir: Path) -> tuple[str, int]:
    """Concatenate the tokenisable text under `target_dir`.

    Returns (combined_text, file_count). Returns ("", 0) if nothing
    suitable is found.
    """
    if not target_dir.is_dir():
        return "", 0

    chunks: list[str] = []
    file_count = 0

    # Preferred drop: a single text.md sitting at the entry root.
    text_md = target_dir / "text.md"
    if text_md.is_file():
        try:
            chunks.append(text_md.read_text(encoding="utf-8", errors="replace"))
            file_count += 1
        except OSError:
            pass

    # Loose text/markdown/json files at the root (NOT inside repo/).
    for child in sorted(target_dir.iterdir()):
        if not child.is_file():
            continue
        if child.name in EXCLUDED_NAMES:
            continue
        if child.name == "text.md":
            continue  # already read
        if child.suffix.lower() in TEXT_EXTENSIONS:
            try:
                chunks.append(child.read_text(encoding="utf-8", errors="replace"))
                file_count += 1
            except OSError:
                pass

    # Git clone payload.
    repo = target_dir / "repo"
    if repo.is_dir():
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d != ".git"]
            for fn in files:
                p = Path(root) / fn
                if p.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                try:
                    chunks.append(p.read_text(encoding="utf-8", errors="replace"))
                    file_count += 1
                except OSError:
                    continue

    return ("\n".join(chunks), file_count) if chunks else ("", 0)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class Bucket:
    files: int = 0
    tokens: int = 0

    def add(self, files: int, tokens: int) -> None:
        self.files += files
        self.tokens += tokens

    def to_dict(self) -> dict[str, int]:
        return {"files": self.files, "tokens": self.tokens}


@dataclass
class AggregateReport:
    tokenizer: str
    by_stage: dict[str, Bucket]
    by_tier: dict[str, Bucket]
    by_license: dict[str, Bucket]
    total: Bucket
    generated_at: str

    def to_dict(self) -> dict:
        return {
            "tokenizer": self.tokenizer,
            "generated_at": self.generated_at,
            "by_stage":   {k: v.to_dict() for k, v in sorted(self.by_stage.items())},
            "by_tier":    {k: v.to_dict() for k, v in sorted(self.by_tier.items())},
            "by_license": {k: v.to_dict() for k, v in sorted(self.by_license.items())},
            "total":      self.total.to_dict(),
        }


def _fmt_token_count(n: int) -> str:
    """Render an integer token count using a compact K/M/G suffix.

    The manifest's `tokens_est` follows this convention so we keep
    `tokens_actual` in the same family.
    """
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}G"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

@dataclass
class DriverStats:
    total_entries: int = 0
    fetched_entries: int = 0
    tokenised_entries: int = 0
    empty_payload: int = 0
    total_tokens: int = 0


def run(
    *,
    manifest_path: Path,
    corpus_dir: Path,
    runs_dir: Path,
    output_path: Optional[Path],
    tokenizer_name: str,
    tokenize_fn: TokenizeFn,
    update_manifest: bool,
    dry_run: bool,
) -> tuple[DriverStats, AggregateReport]:
    """Tokenise every fetched entry and write an aggregate report."""
    manifest = load_manifest(manifest_path)
    entries = list(iter_entries(manifest))

    report = AggregateReport(
        tokenizer=tokenizer_name,
        by_stage={},
        by_tier={},
        by_license={},
        total=Bucket(),
        generated_at=now_iso(),
    )
    stats = DriverStats()
    pending_updates: dict[str, dict[str, str]] = {}

    for entry in entries:
        stats.total_entries += 1
        if entry.fetch_status != "fetched":
            continue
        stats.fetched_entries += 1

        target_dir = entry.corpus_path(corpus_dir)
        text, file_count = gather_payload_text(target_dir)
        if not text:
            stats.empty_payload += 1
            continue

        token_count = tokenize_fn(text)

        stats.tokenised_entries += 1
        stats.total_tokens += token_count

        report.by_stage.setdefault(entry.stage, Bucket()).add(file_count, token_count)
        report.by_tier.setdefault(entry.tier, Bucket()).add(file_count, token_count)
        report.by_license.setdefault(entry.license, Bucket()).add(file_count, token_count)
        report.total.add(file_count, token_count)

        if update_manifest:
            pending_updates[entry.section_header] = {
                "tokens_actual": _fmt_token_count(token_count),
            }

    if not dry_run:
        out_path = output_path or (runs_dir / f"corpus_tokenize.{today_iso()}.json")
        ensure_dir(out_path.parent)
        atomic_write_text(out_path, json.dumps(report.to_dict(), indent=2) + "\n")
    if update_manifest and pending_updates and not dry_run:
        apply_manifest_updates(manifest_path, pending_updates)

    return stats, report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Tokenizer note:\n"
        "  Default tokenizer is `Qwen/Qwen2.5-Coder-7B`. If the model is\n"
        "  gated on HuggingFace, authenticate via `huggingface-cli login`\n"
        "  or set the `HF_TOKEN` environment variable before running.\n"
        "\n"
        "Dependencies: stdlib + `transformers`. No `transformers` import is\n"
        "performed when --selftest is set.\n"
    )
    ap = argparse.ArgumentParser(
        prog="tokenize.py",
        description="Count real tokens per fetched corpus source (hexa-forge v0.1.2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                    help=f"datasets.toml path (default: {DEFAULT_MANIFEST})")
    ap.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR,
                    help=f"corpus root (default: {DEFAULT_CORPUS_DIR})")
    ap.add_argument("--tokenizer", default=DEFAULT_TOKENIZER,
                    help=f"HF tokenizer id (default: {DEFAULT_TOKENIZER})")
    ap.add_argument("--output", type=Path, default=None,
                    help="aggregate report path (default: runs/corpus_tokenize.<date>.json)")
    ap.add_argument("--update-manifest", action="store_true",
                    help="write tokens_actual back into the manifest")
    ap.add_argument("--dry-run", action="store_true",
                    help="print plan only; do not write report or manifest")
    ap.add_argument("--selftest", action="store_true",
                    help="run inline tests with a stub tokenizer and exit")
    return ap


def run_cli(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.selftest:
        return _run_selftest()

    try:
        tokenize_fn = load_hf_tokenizer(args.tokenizer)
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    stats, report = run(
        manifest_path=args.manifest,
        corpus_dir=args.corpus_dir,
        runs_dir=DEFAULT_RUNS_DIR,
        output_path=args.output,
        tokenizer_name=args.tokenizer,
        tokenize_fn=tokenize_fn,
        update_manifest=args.update_manifest,
        dry_run=args.dry_run,
    )
    print(
        f"tokenize: entries={stats.total_entries} fetched={stats.fetched_entries} "
        f"tokenised={stats.tokenised_entries} empty={stats.empty_payload} "
        f"total_tokens={stats.total_tokens}"
    )
    return 0


# ---------------------------------------------------------------------------
# Self-test — synthetic corpus, stub tokenizer, no network or HF
# ---------------------------------------------------------------------------

_SAMPLE_MANIFEST = """\
[meta]
schema_version = "0.1.0"

[datasets.code.philosophy.alpha]
url           = "https://example.invalid/alpha"
license       = "MIT"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "aaaa"

[datasets.code.philosophy.beta]
url           = "https://example.invalid/beta"
license       = "MIT"
weight        = 1.0
tier          = "B"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "bbbb"

[datasets.code.repair.gamma]
url           = "https://example.invalid/gamma"
license       = "Apache-2.0"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "pending"
sha256_corpus = ""
"""


def _run_selftest() -> int:
    """Self-test: synthetic 3-entry corpus, deterministic stub tokenizer."""
    failures: list[str] = []

    # 1. stub_tokenizer is deterministic.
    if stub_tokenizer("abcd") != 1:
        failures.append(f"stub_tokenizer('abcd'): expected 1, got {stub_tokenizer('abcd')}")
    if stub_tokenizer("abcde") != 2:
        failures.append(f"stub_tokenizer('abcde'): expected 2, got {stub_tokenizer('abcde')}")
    if stub_tokenizer("") != 0:
        failures.append("stub_tokenizer(''): expected 0")

    # 2. _fmt_token_count.
    if not _fmt_token_count(1500).startswith("1.5K"):
        failures.append(f"_fmt_token_count(1500): {_fmt_token_count(1500)}")
    if not _fmt_token_count(2_000_000).startswith("2.00M"):
        failures.append(f"_fmt_token_count(2M): {_fmt_token_count(2_000_000)}")

    # 3. gather_payload_text picks up text.md + skips raw.html + walks repo/.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        d = root / "code" / "philosophy" / "alpha"
        d.mkdir(parents=True)
        (d / "text.md").write_text("hello world\n" * 10, encoding="utf-8")
        (d / "raw.html").write_text("<html>ignored</html>", encoding="utf-8")
        (d / "extra.md").write_text("more text\n", encoding="utf-8")
        (d / "repo").mkdir()
        (d / "repo" / "src.py").write_text("print('x')\n", encoding="utf-8")
        (d / "repo" / "binary.bin").write_text("nope", encoding="utf-8")

        text, count = gather_payload_text(d)
        if "ignored" in text:
            failures.append("gather: raw.html leaked into payload")
        if "hello world" not in text:
            failures.append("gather: text.md missing")
        if "print('x')" not in text:
            failures.append("gather: repo .py missing")
        if "nope" in text:
            failures.append("gather: binary.bin leaked")
        if count != 3:  # text.md + extra.md + src.py
            failures.append(f"gather: file count expected 3, got {count}")

    # 4. End-to-end run: synthetic manifest + matching corpus dir.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, _SAMPLE_MANIFEST)

        cdir = root / "corpus"
        # alpha: has text.md
        alpha = cdir / "code" / "philosophy" / "alpha"
        alpha.mkdir(parents=True)
        (alpha / "text.md").write_text("a" * 100, encoding="utf-8")
        # beta: has text.md (smaller)
        beta = cdir / "code" / "philosophy" / "beta"
        beta.mkdir(parents=True)
        (beta / "text.md").write_text("b" * 40, encoding="utf-8")
        # gamma: fetch_status pending -> must NOT be tokenised even if dir exists
        gamma = cdir / "code" / "repair" / "gamma"
        gamma.mkdir(parents=True)
        (gamma / "text.md").write_text("c" * 80, encoding="utf-8")

        rundir = root / "runs"
        stats, report = run(
            manifest_path=man,
            corpus_dir=cdir,
            runs_dir=rundir,
            output_path=None,
            tokenizer_name="stub",
            tokenize_fn=stub_tokenizer,
            update_manifest=True,
            dry_run=False,
        )

        # alpha = 100 bytes -> 25 tokens; beta = 40 -> 10; gamma skipped.
        if stats.total_entries != 3:
            failures.append(f"run total_entries: {stats.total_entries}")
        if stats.fetched_entries != 2:
            failures.append(f"run fetched_entries: {stats.fetched_entries}")
        if stats.tokenised_entries != 2:
            failures.append(f"run tokenised_entries: {stats.tokenised_entries}")
        if stats.total_tokens != 35:
            failures.append(f"run total_tokens: expected 35, got {stats.total_tokens}")

        # Aggregation correctness.
        if report.by_stage.get("philosophy", Bucket()).tokens != 35:
            failures.append("by_stage[philosophy] != 35")
        if "repair" in report.by_stage:
            failures.append("by_stage should not contain repair (status=pending)")
        if report.by_tier.get("A", Bucket()).tokens != 25:
            failures.append("by_tier[A] != 25")
        if report.by_tier.get("B", Bucket()).tokens != 10:
            failures.append("by_tier[B] != 10")
        if report.by_license.get("MIT", Bucket()).tokens != 35:
            failures.append("by_license[MIT] != 35")
        if report.total.tokens != 35:
            failures.append(f"total.tokens != 35 (got {report.total.tokens})")

        # Report file written.
        out_path = rundir / f"corpus_tokenize.{today_iso()}.json"
        if not out_path.is_file():
            failures.append("report file not written")
        else:
            parsed = json.loads(out_path.read_text(encoding="utf-8"))
            if parsed["total"]["tokens"] != 35:
                failures.append("report total mismatch")

        # Manifest updated only for fetched entries.
        man_text = man.read_text(encoding="utf-8")
        if "tokens_actual = \"25\"" not in man_text:
            failures.append("manifest alpha tokens_actual not written")
        if "tokens_actual = \"10\"" not in man_text:
            failures.append("manifest beta tokens_actual not written")
        # gamma must remain "" (status pending).
        # Find the gamma section and confirm tokens_actual is still empty.
        gamma_idx = man_text.find("[datasets.code.repair.gamma]")
        gamma_block = man_text[gamma_idx:gamma_idx + 600]
        if "tokens_actual = \"\"" not in gamma_block:
            failures.append("gamma tokens_actual should remain empty")

    # 5. Defensive schema lock: tokens_actual is mutable, but a stray
    #    tokenize call that tried to mutate `url` would raise. We exercise
    #    by injecting an illegal update into apply_manifest_updates.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, _SAMPLE_MANIFEST)
        try:
            apply_manifest_updates(
                man,
                {"[datasets.code.philosophy.alpha]": {"url": "bogus"}},
            )
            failures.append("schema lock: url mutation should have failed")
        except ValueError:
            pass

    if failures:
        print("tokenize.py SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("tokenize.py SELFTEST PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_cli())
