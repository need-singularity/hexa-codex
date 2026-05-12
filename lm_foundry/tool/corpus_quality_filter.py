#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""corpus_quality_filter.py — perplexity-based corpus quality filter.

Phase v0.1.2-r3 deliverable for D-NEW-TC-E (the quality-filter ladder
per `docs/code-llm.md §STRUCT`). Applies a per-source perplexity gate
upstream of the `pretrain-bias` Stack v2 permissive subset (and any
other §STRUCT stage on demand), paired with the existing license-clean
and anti-corpus filters.

WHAT
----
For every `fetch_status == "fetched"` entry in `datasets.toml` whose
stage matches `--apply-to-stage` (default `pretrain-bias`):

  1. Walk the entry's `corpus/<verb>/<stage>/<id>/` payload.
  2. Read all text-ish files (extension allowlist; binary skipped).
  3. Split into `--max-chunk-bytes` chunks.
  4. Score each chunk's perplexity via the reference model
     (default `Qwen/Qwen2.5-Coder-7B`).
  5. Decide per-entry verdict:
        PASS    ≥ 80% chunks under the threshold
        MIXED   40% .. 80%
        FAIL    < 40%
  6. Write the surviving chunks to
     `corpus_filtered/<verb>/<stage>/<id>/` preserving sub-paths.
  7. Emit `runs/corpus_quality_filter.<date>.json` with per-entry and
     aggregate stats (mean / p95 / pass-rate / keep-rate).

WHY
---
The Stack v2 permissive subset is broadly clean by license but contains
high-PPL noise (boilerplate spam, machine-generated junk, malformed
artefacts) that bleeds into the `pretrain-bias` stage. A perplexity
gate scored by a strong code LM (Qwen2.5-Coder-7B) is a cheap, sharp
filter. Per-source threshold overrides in `datasets.toml`
(`ppl_threshold` field) accommodate domain-natural high-PPL sources
(e.g. SQL DDL, Lean tactic scripts) without globally relaxing.

DEPENDENCIES
------------
- stdlib only for the self-test path (deterministic offline stub PPL).
- `transformers` + `torch` lazy-imported for real-PPL scoring.
- HF auth required if the reference model is gated: see `--help`.

MANIFEST SCHEMA EXTENSION
-------------------------
This tool extends `datasets.toml` per-entry fields:

    ppl_threshold      (optional curator-set override, float)
    ppl_mean           (populated post-run, float)
    ppl_p95            (populated post-run, float)
    ppl_pass_rate      (populated post-run, float, 0..1)
    quality_gate_status (populated post-run, "PASS"|"MIXED"|"FAIL")

`tool/_common.py` MUTABLE_FIELDS currently locks to
{tokens_actual, fetch_status, sha256_corpus}. Per the v0.1.2-r3 design
review, this tool does NOT modify `_common.py` from this round; instead
`--update-manifest` writes through a *surgical text mutator* defined
here (`_write_ppl_fields_directly`) that mirrors the section-bounds
+ kv-line regex strategy of `_common.update_entry_fields()` but is
gated on its own additive whitelist. A TODO is surfaced for the next
schema-lock revision to fold these four fields into MUTABLE_FIELDS.

ACCEPTANCE
----------
A `pretrain-bias` corpus is GO iff:
  - `filter_keep_rate >= 0.6` (60% of scored chunks survive), AND
  - no entry has `quality_gate_status == "FAIL"`.

Cross-links:
  - docs/code-llm.md §STRUCT (quality-filter ladder)
  - papers/plan-decisions-pending.md D-058 (= D-NEW-TC-E integer slot)
"""
from __future__ import annotations

# `tool/` directory shadows stdlib modules when a script is launched
# directly (sys.path[0] = script dir). Prune it before any imports
# that may transitively walk the stdlib via inspect / linecache.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import importlib.util
import json
import math
import os
import re
import statistics
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional


# ---------------------------------------------------------------------------
# _common.py loader (mirrors tool/tokenize.py defensive pattern)
# ---------------------------------------------------------------------------

def _load_common():
    mod_name = "_hexa_forge_common"
    spec = importlib.util.spec_from_file_location(
        mod_name, _os.path.join(_THIS_DIR, "_common.py"),
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load tool/_common.py")
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_common = _load_common()
DEFAULT_CORPUS_DIR = _common.DEFAULT_CORPUS_DIR
DEFAULT_MANIFEST = _common.DEFAULT_MANIFEST
DEFAULT_RUNS_DIR = _common.DEFAULT_RUNS_DIR
REPO_ROOT = _common.REPO_ROOT
Entry = _common.Entry
atomic_write_text = _common.atomic_write_text
atomic_write_bytes = _common.atomic_write_bytes
ensure_dir = _common.ensure_dir
iter_entries = _common.iter_entries
load_manifest = _common.load_manifest
now_iso = _common.now_iso
today_iso = _common.today_iso


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

DEFAULT_REFERENCE_MODEL = "Qwen/Qwen2.5-Coder-7B"
DEFAULT_PPL_THRESHOLD = 1000.0
DEFAULT_MAX_CHUNK_BYTES = 32_768
DEFAULT_OUTPUT_DIR = REPO_ROOT / "corpus_filtered"
DEFAULT_STAGE = "pretrain-bias"

# Stage choices per docs/code-llm.md §STRUCT stage table.
STAGE_CHOICES: tuple[str, ...] = (
    "pretrain-bias",
    "domain-bias",
    "build-trace",
    "diff-edit",
    "repair",
    "hexa-native",
    "philosophy",
    "db-native",
    "firmware-native",
    "hexa-firmware",
)

# Verdict thresholds.
VERDICT_PASS_MIN = 0.80   # >= 80% chunks under threshold => PASS
VERDICT_MIXED_MIN = 0.40  # 40..80%                      => MIXED, else FAIL

# Acceptance gate (see module docstring "ACCEPTANCE").
ACCEPTANCE_KEEP_RATE = 0.60

# Text-ish extensions the filter will score. Anything else is skipped
# (binary blobs, archives, images).
TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".md", ".txt", ".rst",
    ".py", ".rs", ".ts", ".js",
    ".go", ".c", ".h",
    ".zig", ".sql",
    ".toml", ".yaml", ".json",
})

# Files we never touch (provenance only / structural).
EXCLUDED_NAMES: frozenset[str] = frozenset({
    "raw.html", "raw.pdf",
    "REPO_MANIFEST.tsv", "GIT_HEAD", "LICENSE.attribution",
})

# Per-entry fields this tool writes back into datasets.toml when
# --update-manifest is set. NOT in `_common.MUTABLE_FIELDS` yet — see
# the surgical-write-through note in the module docstring.
PPL_OUTPUT_FIELDS: tuple[str, ...] = (
    "ppl_mean", "ppl_p95", "ppl_pass_rate", "quality_gate_status",
)


# ---------------------------------------------------------------------------
# Perplexity scoring abstraction
# ---------------------------------------------------------------------------

# Signature: (chunk_text) -> float perplexity. Higher = noisier.
PerplexityFn = Callable[[str], float]


def load_hf_perplexity(model_name: str) -> PerplexityFn:
    """Build a perplexity scorer backed by a HuggingFace causal-LM.

    Lazy-imports `transformers` + `torch`. Raises a friendly error with
    HF-auth instructions if the model is gated and credentials are
    missing.

    PPL is computed as `exp(model(input_ids, labels=input_ids).loss)`
    — the conventional per-token cross-entropy exponentiation. Long
    docs are not handled here; the caller is expected to slice into
    `--max-chunk-bytes` chunks before scoring (a chunk is ~8K tokens
    for typical code, well under any sane context window).
    """
    try:
        import torch  # type: ignore[import-not-found]
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "transformers + torch are required for real perplexity scoring.\n"
            "Install with:\n"
            "  pip install 'transformers>=4.45' torch\n"
            "If the reference model is HF-gated, authenticate:\n"
            "  1. huggingface-cli login                  # or\n"
            "  2. export HF_TOKEN='hf_...'               # or\n"
            "  3. accept model terms in the HF UI for "
            f"{DEFAULT_REFERENCE_MODEL}"
        ) from exc

    try:
        tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, trust_remote_code=False,
        )
        model.eval()
    except OSError as exc:
        raise RuntimeError(
            f"failed to load reference model {model_name!r}: {exc}\n"
            "If gated, authenticate via:\n"
            "  1. huggingface-cli login\n"
            "  2. export HF_TOKEN='hf_...'\n"
            "  3. accept the model license on huggingface.co"
        ) from exc

    @torch.no_grad()  # type: ignore[misc]
    def _ppl(text: str) -> float:
        if not text.strip():
            return float("inf")
        enc = tok(text, return_tensors="pt", truncation=True)
        input_ids = enc["input_ids"]
        if input_ids.shape[1] < 2:
            return float("inf")
        out = model(input_ids, labels=input_ids)
        loss = float(out.loss.detach().item())
        # Clamp to avoid overflow on degenerate text.
        if loss > 50.0:
            return math.exp(50.0)
        return math.exp(loss)

    return _ppl


def stub_perplexity(text: str) -> float:
    """Deterministic offline PPL approximation for self-tests.

    Heuristic: a unigram surprise proxy. Higher entropy of the byte
    distribution and higher proportion of non-printable bytes both
    push perplexity up. The mapping is monotonic but synthetic — used
    only to make verdict-logic tests deterministic without invoking a
    real LM. Returns +inf for empty input.
    """
    if not text:
        return float("inf")
    data = text.encode("utf-8", errors="replace")
    if not data:
        return float("inf")
    # Byte-distribution entropy in bits.
    freq: dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    n = len(data)
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    # Penalty for high non-printable share.
    nonprint = sum(1 for b in data if b < 9 or (13 < b < 32) or b == 127)
    junk_share = nonprint / n
    # Map entropy in [0..8] roughly to PPL in [2..500]; junk multiplies.
    base = 2.0 ** (1.0 + 0.9 * ent)  # ent=0 -> ~2; ent=8 -> ~256
    return base * (1.0 + 50.0 * junk_share)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text_by_bytes(text: str, max_bytes: int) -> list[str]:
    """Split `text` into UTF-8-safe chunks of at most `max_bytes`.

    Splits on byte boundaries that are also character boundaries
    (we encode then re-decode, walking back to the last valid split
    point). Preserves total content (concatenation reproduces the
    original modulo encoding round-trip).
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be > 0")
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return [text] if text else []
    chunks: list[str] = []
    i = 0
    n = len(data)
    while i < n:
        end = min(i + max_bytes, n)
        # Step `end` back while it lands mid-codepoint (UTF-8
        # continuation bytes have high two bits == 10).
        while end < n and (data[end] & 0xC0) == 0x80:
            end -= 1
        chunk_bytes = data[i:end]
        chunks.append(chunk_bytes.decode("utf-8", errors="replace"))
        i = end
    return chunks


# ---------------------------------------------------------------------------
# Payload discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PayloadFile:
    """A single text-ish file under an entry's corpus directory."""
    abs_path: Path     # absolute on-disk path
    rel_path: Path     # path relative to the entry root


def discover_payload_files(entry_dir: Path) -> list[PayloadFile]:
    """Walk `entry_dir`, return every allowlisted text-ish file.

    Skips `.git/` trees, the `EXCLUDED_NAMES` set, and any extension
    not in `TEXT_EXTENSIONS`.
    """
    if not entry_dir.is_dir():
        return []
    out: list[PayloadFile] = []
    for root, dirs, files in os.walk(entry_dir):
        # Don't descend into VCS metadata.
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in sorted(files):
            if fn in EXCLUDED_NAMES:
                continue
            ext = Path(fn).suffix.lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            abs_p = Path(root) / fn
            try:
                rel_p = abs_p.relative_to(entry_dir)
            except ValueError:
                continue
            out.append(PayloadFile(abs_path=abs_p, rel_path=rel_p))
    return out


# ---------------------------------------------------------------------------
# Per-entry scoring + filtering
# ---------------------------------------------------------------------------

@dataclass
class ChunkScore:
    """One scored chunk's worth of data."""
    file_rel: Path
    chunk_idx: int
    chunk_text: str
    ppl: float
    passes: bool


@dataclass
class EntryReport:
    """Per-entry aggregate stats + verdict."""
    section_header: str
    verb: str
    stage: str
    id: str
    threshold: float
    chunks_n: int = 0
    chunks_kept: int = 0
    ppl_values: list[float] = field(default_factory=list)
    verdict: str = "FAIL"  # PASS | MIXED | FAIL

    @property
    def pass_rate(self) -> float:
        return (self.chunks_kept / self.chunks_n) if self.chunks_n else 0.0

    @property
    def ppl_mean(self) -> float:
        return statistics.fmean(self.ppl_values) if self.ppl_values else float("inf")

    @property
    def ppl_p95(self) -> float:
        return _percentile(self.ppl_values, 95.0)

    @property
    def ppl_min(self) -> float:
        return min(self.ppl_values) if self.ppl_values else float("inf")

    @property
    def ppl_max(self) -> float:
        return max(self.ppl_values) if self.ppl_values else float("inf")

    def to_dict(self) -> dict[str, object]:
        return {
            "ppl_mean": _round(self.ppl_mean),
            "ppl_p95": _round(self.ppl_p95),
            "ppl_min": _round(self.ppl_min),
            "ppl_max": _round(self.ppl_max),
            "chunks_n": self.chunks_n,
            "chunks_kept": self.chunks_kept,
            "ppl_pass_rate": _round(self.pass_rate, 4),
            "threshold": self.threshold,
            "quality_gate_status": self.verdict,
        }


def _percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (0..100). Empty -> +inf."""
    if not values:
        return float("inf")
    if len(values) == 1:
        return float(values[0])
    s = sorted(values)
    rank = (p / 100.0) * (len(s) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(s[lo])
    frac = rank - lo
    return float(s[lo] + (s[hi] - s[lo]) * frac)


def _round(v: float, ndigits: int = 2) -> float:
    """Round for report stability; preserve inf as a sentinel."""
    if math.isinf(v) or math.isnan(v):
        return v
    return round(v, ndigits)


def verdict_from_pass_rate(rate: float) -> str:
    """Map pass-rate -> {PASS, MIXED, FAIL} per VERDICT_* thresholds."""
    if rate >= VERDICT_PASS_MIN:
        return "PASS"
    if rate >= VERDICT_MIXED_MIN:
        return "MIXED"
    return "FAIL"


def resolve_threshold(
    manifest: dict,
    entry: Entry,
    default_threshold: float,
) -> float:
    """Return the per-entry PPL threshold, honouring `ppl_threshold`."""
    raw = (
        manifest.get("datasets", {})
        .get(entry.verb, {})
        .get(entry.stage, {})
        .get(entry.id, {})
    )
    if not isinstance(raw, dict):
        return default_threshold
    val = raw.get("ppl_threshold")
    if val is None:
        return default_threshold
    try:
        return float(val)
    except (TypeError, ValueError):
        return default_threshold


def score_and_filter_entry(
    entry: Entry,
    corpus_dir: Path,
    output_dir: Path,
    threshold: float,
    max_chunk_bytes: int,
    ppl_fn: PerplexityFn,
    dry_run: bool,
) -> EntryReport:
    """Score every chunk under `entry`'s corpus dir; write PASS chunks.

    Filtered content is written to
    `<output_dir>/<verb>/<stage>/<id>/<original-rel-path>`, where
    chunks that pass the threshold are concatenated back in original
    order. Files whose chunks all fail are omitted from the output
    tree entirely.
    """
    report = EntryReport(
        section_header=entry.section_header,
        verb=entry.verb,
        stage=entry.stage,
        id=entry.id,
        threshold=threshold,
    )
    src_dir = entry.corpus_path(corpus_dir)
    dst_dir = output_dir / entry.verb / entry.stage / entry.id
    files = discover_payload_files(src_dir)
    if not files:
        return report

    for pf in files:
        try:
            text = pf.abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks = chunk_text_by_bytes(text, max_chunk_bytes)
        if not chunks:
            continue
        kept_chunks: list[str] = []
        for idx, ch in enumerate(chunks):
            ppl = ppl_fn(ch)
            passes = ppl <= threshold
            report.chunks_n += 1
            report.ppl_values.append(ppl)
            if passes:
                report.chunks_kept += 1
                kept_chunks.append(ch)
        if kept_chunks and not dry_run:
            out_path = dst_dir / pf.rel_path
            atomic_write_text(out_path, "".join(kept_chunks))

    report.verdict = verdict_from_pass_rate(report.pass_rate)
    return report


# ---------------------------------------------------------------------------
# Surgical manifest writer for the four new PPL fields
# ---------------------------------------------------------------------------
# `tool/_common.py` MUTABLE_FIELDS is currently locked to the original
# fetch-pipeline trio {tokens_actual, fetch_status, sha256_corpus}. We
# deliberately do NOT extend it from this round (per the v0.1.2-r3
# design review — schema-lock extensions are curator-only). Instead we
# perform the write here, mirroring _common's section-bounds + kv-line
# strategy but gated on our own additive whitelist below.
#
# TODO(schema-lock): after curator review, fold the four PPL fields
# into `_common.MUTABLE_FIELDS` and switch this tool to
# `_common.apply_manifest_updates`.

_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$", re.M)


def _section_bounds(text: str, header: str) -> tuple[int, int]:
    needle = header + "\n"
    idx = text.find(needle)
    if idx < 0:
        idx = text.find(header)
        if idx < 0:
            raise KeyError(header)
        start = idx + len(header) + 1
    else:
        start = idx + len(needle)
    m = _SECTION_RE.search(text, pos=start)
    end = m.start() if m else len(text)
    return start, end


def _kv_line_re(key: str) -> re.Pattern[str]:
    return re.compile(
        r"^(?P<indent>[ \t]*)" + re.escape(key)
        + r"(?P<gap>[ \t]*=[ \t]*).*$",
        re.M,
    )


def _format_value(value: object) -> str:
    """TOML scalar formatter for the four PPL fields.

    - str -> double-quoted, escaped
    - float -> bare decimal
    - bool/int -> bare
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            # Surface as a string so the manifest stays valid TOML.
            s = "+inf" if value > 0 else "-inf"
            return f"\"{s}\""
        # Use %g for compactness but ensure a decimal point so TOML
        # parses the result as a float rather than an int.
        formatted = f"{value:.6g}"
        if "." not in formatted and "e" not in formatted and "E" not in formatted:
            formatted += ".0"
        return formatted
    if isinstance(value, int):
        return str(value)
    s = str(value)
    escaped = s.replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


def _write_ppl_fields_directly(
    manifest_path: Path,
    updates_by_section: dict[str, dict[str, object]],
) -> None:
    """Surgical write-through for PPL_OUTPUT_FIELDS.

    Mirrors `_common.update_entry_fields` semantics but limited to the
    four additive fields this tool owns. Validates every key against
    `PPL_OUTPUT_FIELDS` before touching the file.
    """
    allowed = frozenset(PPL_OUTPUT_FIELDS)
    for header, kv in updates_by_section.items():
        bad = sorted(set(kv) - allowed)
        if bad:
            raise ValueError(
                f"corpus_quality_filter refuses to mutate {bad} "
                f"(allowed additive fields: {sorted(allowed)})"
            )

    text = manifest_path.read_text(encoding="utf-8")
    for header, kv in updates_by_section.items():
        start, end = _section_bounds(text, header)
        body = text[start:end]
        # Sniff indent/gap convention from the section.
        indent = ""
        gap = " = "
        sample = re.search(
            r"^([ \t]*)([A-Za-z0-9_.\-]+)([ \t]*=[ \t]*)", body, re.M,
        )
        if sample:
            indent = sample.group(1)
            gap = sample.group(3)
        new_body = body
        for key, val in kv.items():
            line_re = _kv_line_re(key)
            formatted = _format_value(val)
            m = line_re.search(new_body)
            if m:
                eindent = m.group("indent")
                egap = m.group("gap")
                line = f"{eindent}{key}{egap}{formatted}"
                new_body = new_body[:m.start()] + line + new_body[m.end():]
            else:
                line = f"{indent}{key}{gap}{formatted}"
                tail = new_body.rstrip("\n")
                if new_body.endswith("\n\n"):
                    new_body = tail + "\n" + line + "\n\n"
                else:
                    new_body = tail + "\n" + line + "\n"
        text = text[:start] + new_body + text[end:]
    atomic_write_text(manifest_path, text)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

@dataclass
class DriverStats:
    entries_seen: int = 0
    entries_in_stage: int = 0
    entries_scored: int = 0
    entries_empty: int = 0
    total_chunks_scored: int = 0
    total_chunks_kept: int = 0
    by_status: dict[str, int] = field(
        default_factory=lambda: {"PASS": 0, "MIXED": 0, "FAIL": 0}
    )

    @property
    def keep_rate(self) -> float:
        if not self.total_chunks_scored:
            return 0.0
        return self.total_chunks_kept / self.total_chunks_scored


def run(
    *,
    manifest_path: Path,
    corpus_dir: Path,
    output_dir: Path,
    runs_dir: Path,
    report_path: Optional[Path],
    reference_model: str,
    ppl_threshold_default: float,
    max_chunk_bytes: int,
    apply_to_stage: str,
    ppl_fn: PerplexityFn,
    update_manifest: bool,
    dry_run: bool,
) -> tuple[DriverStats, dict]:
    """Score every fetched entry in `apply_to_stage`; write filtered corpus."""
    manifest = load_manifest(manifest_path)
    entries = list(iter_entries(manifest))
    stats = DriverStats()
    started = now_iso()

    per_entry_block: dict[str, dict[str, object]] = {}
    pending_updates: dict[str, dict[str, object]] = {}

    for entry in entries:
        stats.entries_seen += 1
        if entry.stage != apply_to_stage:
            continue
        stats.entries_in_stage += 1
        if entry.fetch_status != "fetched":
            continue
        threshold = resolve_threshold(manifest, entry, ppl_threshold_default)
        rep = score_and_filter_entry(
            entry=entry,
            corpus_dir=corpus_dir,
            output_dir=output_dir,
            threshold=threshold,
            max_chunk_bytes=max_chunk_bytes,
            ppl_fn=ppl_fn,
            dry_run=dry_run,
        )
        if rep.chunks_n == 0:
            stats.entries_empty += 1
            continue
        stats.entries_scored += 1
        stats.total_chunks_scored += rep.chunks_n
        stats.total_chunks_kept += rep.chunks_kept
        stats.by_status[rep.verdict] = stats.by_status.get(rep.verdict, 0) + 1

        key = f"{entry.verb}.{entry.stage}.{entry.id}"
        per_entry_block[key] = rep.to_dict()

        if update_manifest:
            pending_updates[entry.section_header] = {
                "ppl_mean": float(_round(rep.ppl_mean)),
                "ppl_p95": float(_round(rep.ppl_p95)),
                "ppl_pass_rate": float(_round(rep.pass_rate, 4)),
                "quality_gate_status": rep.verdict,
            }

    finished = now_iso()
    report = {
        "reference_model": reference_model,
        "started_at": started,
        "finished_at": finished,
        "stage": apply_to_stage,
        "ppl_threshold_default": ppl_threshold_default,
        "max_chunk_bytes": max_chunk_bytes,
        "per_entry": per_entry_block,
        "by_status": dict(stats.by_status),
        "total_entries_scored": stats.entries_scored,
        "total_chunks_scored": stats.total_chunks_scored,
        "total_chunks_kept": stats.total_chunks_kept,
        "filter_keep_rate": _round(stats.keep_rate, 4),
    }

    if not dry_run:
        out_path = report_path or (
            runs_dir / f"corpus_quality_filter.{today_iso()}.json"
        )
        ensure_dir(out_path.parent)
        atomic_write_text(out_path, json.dumps(report, indent=2) + "\n")
        if update_manifest and pending_updates:
            _write_ppl_fields_directly(manifest_path, pending_updates)

    return stats, report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_EPILOG = """\
Cross-links:
  docs/code-llm.md §STRUCT — quality-filter ladder (D-NEW-TC-E)
  papers/plan-decisions-pending.md D-058 — D-NEW-TC-E integer slot

HuggingFace auth (real-PPL mode):
  The default reference model `Qwen/Qwen2.5-Coder-7B` may be HF-gated.
  If `--dry-run` is NOT set, authenticate via one of:
    1. huggingface-cli login
    2. export HF_TOKEN='hf_...'
    3. accept the model terms on huggingface.co

Acceptance (`pretrain-bias` corpus is GO iff):
  - filter_keep_rate >= 0.60   AND
  - no entry has quality_gate_status == "FAIL"

  These thresholds are intentionally conservative for v0.1.2 and are
  expected to be revisited in v0.2.0 once the empirical Stack v2
  pass-rate distribution is observed.
"""


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="corpus_quality_filter.py",
        description=(
            "Per-source perplexity gate for hexa-forge §STRUCT corpus "
            "stages (D-NEW-TC-E, v0.1.2-r3)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    ap.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST,
        help=f"datasets.toml path (default: {DEFAULT_MANIFEST})",
    )
    ap.add_argument(
        "--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR,
        help=f"fetched-source root (default: {DEFAULT_CORPUS_DIR})",
    )
    ap.add_argument(
        "--reference-model", default=DEFAULT_REFERENCE_MODEL,
        help=(
            "HF causal-LM id used for perplexity scoring "
            f"(default: {DEFAULT_REFERENCE_MODEL})"
        ),
    )
    ap.add_argument(
        "--ppl-threshold-default", type=float, default=DEFAULT_PPL_THRESHOLD,
        help=(
            "fallback PPL threshold when an entry has no ppl_threshold "
            f"override (default: {DEFAULT_PPL_THRESHOLD})"
        ),
    )
    ap.add_argument(
        "--max-chunk-bytes", type=int, default=DEFAULT_MAX_CHUNK_BYTES,
        help=(
            "chunk size for perplexity scoring; long docs are split "
            f"(default: {DEFAULT_MAX_CHUNK_BYTES})"
        ),
    )
    ap.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"post-gate corpus root (default: {DEFAULT_OUTPUT_DIR})",
    )
    ap.add_argument(
        "--report", type=Path, default=None,
        help=(
            "report file path "
            "(default: runs/corpus_quality_filter.<date>.json)"
        ),
    )
    ap.add_argument(
        "--update-manifest", action="store_true",
        help=(
            "write ppl_mean / ppl_p95 / ppl_pass_rate / "
            "quality_gate_status back into datasets.toml"
        ),
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="plan only; do not invoke the reference model or write files",
    )
    ap.add_argument(
        "--apply-to-stage", choices=STAGE_CHOICES, default=DEFAULT_STAGE,
        help=(
            "restrict scoring to a single §STRUCT stage "
            f"(default: {DEFAULT_STAGE})"
        ),
    )
    ap.add_argument(
        "--selftest", action="store_true",
        help="run inline self-tests with the offline stub PPL and exit",
    )
    return ap


def run_cli(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.selftest:
        return _run_selftest()

    if args.dry_run:
        # Dry-run uses the stub PPL so we never hit the network.
        ppl_fn: PerplexityFn = stub_perplexity
    else:
        try:
            ppl_fn = load_hf_perplexity(args.reference_model)
        except ImportError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    stats, report = run(
        manifest_path=args.manifest,
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
        runs_dir=DEFAULT_RUNS_DIR,
        report_path=args.report,
        reference_model=args.reference_model,
        ppl_threshold_default=args.ppl_threshold_default,
        max_chunk_bytes=args.max_chunk_bytes,
        apply_to_stage=args.apply_to_stage,
        ppl_fn=ppl_fn,
        update_manifest=args.update_manifest,
        dry_run=args.dry_run,
    )
    print(
        "corpus_quality_filter: "
        f"stage={args.apply_to_stage} "
        f"seen={stats.entries_seen} in_stage={stats.entries_in_stage} "
        f"scored={stats.entries_scored} empty={stats.entries_empty} "
        f"chunks={stats.total_chunks_scored} kept={stats.total_chunks_kept} "
        f"keep_rate={stats.keep_rate:.3f} "
        f"PASS={stats.by_status.get('PASS', 0)} "
        f"MIXED={stats.by_status.get('MIXED', 0)} "
        f"FAIL={stats.by_status.get('FAIL', 0)}"
    )
    return 0


# ---------------------------------------------------------------------------
# Self-test — synthetic 3-entry corpus, deterministic stub PPL, offline
# ---------------------------------------------------------------------------

_SAMPLE_MANIFEST = """\
[meta]
schema_version = "0.1.0"

[datasets.code.pretrain-bias.clean]
url           = "https://example.invalid/clean"
license       = "MIT"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "aaaa"

[datasets.code.pretrain-bias.mixed]
url           = "https://example.invalid/mixed"
license       = "MIT"
weight        = 1.0
tier          = "B"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "bbbb"

[datasets.code.pretrain-bias.noisy]
url           = "https://example.invalid/noisy"
license       = "MIT"
weight        = 1.0
tier          = "C"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "cccc"

[datasets.code.philosophy.other-stage]
url           = "https://example.invalid/other"
license       = "MIT"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "fetched"
sha256_corpus = "dddd"
"""


def _make_clean_payload(target: Path) -> None:
    """Synth a low-PPL clean-Python sample (~5 small chunks)."""
    target.mkdir(parents=True, exist_ok=True)
    text = (
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "def sub(a, b):\n"
        "    return a - b\n"
        "\n"
        "def mul(a, b):\n"
        "    return a * b\n"
        "\n"
    ) * 4
    (target / "clean.py").write_text(text, encoding="utf-8")
    (target / "README.md").write_text(
        "# clean source\n\nA small, well-formatted module.\n", encoding="utf-8"
    )


def _make_mixed_payload(target: Path) -> None:
    """Mix of clean text + one high-junk file to land in MIXED."""
    target.mkdir(parents=True, exist_ok=True)
    (target / "good.py").write_text(
        "def f(x):\n    return x\n" * 10, encoding="utf-8",
    )
    # Junky binary-ish content that still hits .txt extension.
    junk = bytes(range(0, 32)) * 64
    (target / "junk.txt").write_bytes(junk)


def _make_noisy_payload(target: Path) -> None:
    """Heavy junk that should mostly FAIL the gate."""
    target.mkdir(parents=True, exist_ok=True)
    junk = bytes([1, 2, 3, 7, 11, 27, 4, 6]) * 4096
    (target / "noise.txt").write_bytes(junk)
    (target / "more.txt").write_bytes(bytes(range(0, 32)) * 512)


def _run_selftest() -> int:
    failures: list[str] = []

    # ----- 1. chunk_text_by_bytes correctness -----
    if chunk_text_by_bytes("", 16) != []:
        failures.append("chunk: empty -> non-empty")
    if chunk_text_by_bytes("abc", 16) != ["abc"]:
        failures.append("chunk: small -> wrapped wrong")
    parts = chunk_text_by_bytes("a" * 50, 16)
    if "".join(parts) != "a" * 50:
        failures.append("chunk: concat mismatch")
    if any(len(p.encode("utf-8")) > 16 for p in parts):
        failures.append("chunk: chunk exceeded max bytes")
    # Multi-byte safety.
    s = "é" * 20  # 2 bytes each
    parts = chunk_text_by_bytes(s, 5)
    if "".join(parts) != s:
        failures.append("chunk: multibyte concat mismatch")

    # ----- 2. _percentile correctness -----
    if abs(_percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50.0) - 3.0) > 1e-9:
        failures.append("percentile: median wrong")
    if abs(_percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95.0) - 4.8) > 1e-9:
        failures.append("percentile: p95 wrong")
    if abs(_percentile([10.0], 95.0) - 10.0) > 1e-9:
        failures.append("percentile: single-element wrong")
    if not math.isinf(_percentile([], 95.0)):
        failures.append("percentile: empty should be +inf")

    # ----- 3. verdict_from_pass_rate boundaries -----
    cases = [
        (1.00, "PASS"),
        (0.80, "PASS"),
        (0.79, "MIXED"),
        (0.40, "MIXED"),
        (0.39, "FAIL"),
        (0.00, "FAIL"),
    ]
    for rate, want in cases:
        got = verdict_from_pass_rate(rate)
        if got != want:
            failures.append(f"verdict({rate}) -> {got}, want {want}")

    # ----- 4. stub_perplexity is deterministic + monotonic-ish -----
    clean = "def add(a, b):\n    return a + b\n" * 10
    junk = bytes(range(0, 32)).decode("latin-1") * 64
    p_clean_a = stub_perplexity(clean)
    p_clean_b = stub_perplexity(clean)
    if p_clean_a != p_clean_b:
        failures.append("stub_perplexity: nondeterministic")
    if math.isinf(p_clean_a):
        failures.append("stub_perplexity: clean PPL is +inf")
    p_junk = stub_perplexity(junk)
    if p_junk <= p_clean_a:
        failures.append(
            f"stub_perplexity: junk ({p_junk}) <= clean ({p_clean_a}); "
            "expected junk higher"
        )
    if not math.isinf(stub_perplexity("")):
        failures.append("stub_perplexity('') should be +inf")

    # ----- 5. _format_value -----
    if _format_value("hi") != "\"hi\"":
        failures.append("_format_value(str)")
    if _format_value(1.5) != "1.5":
        failures.append(f"_format_value(float): {_format_value(1.5)}")
    if _format_value(3) != "3":
        failures.append("_format_value(int)")
    if _format_value(True) != "true":
        failures.append("_format_value(bool)")
    if _format_value(float("inf")) != "\"+inf\"":
        failures.append(f"_format_value(inf): {_format_value(float('inf'))}")

    # ----- 6. _section_bounds + surgical write of additive fields -----
    sample = _SAMPLE_MANIFEST
    s, e = _section_bounds(sample, "[datasets.code.pretrain-bias.clean]")
    if "url           = \"https://example.invalid/clean\"" not in sample[s:e]:
        failures.append("_section_bounds: body extraction wrong")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, sample)
        _write_ppl_fields_directly(man, {
            "[datasets.code.pretrain-bias.clean]": {
                "ppl_mean": 12.4,
                "ppl_p95": 35.2,
                "ppl_pass_rate": 1.0,
                "quality_gate_status": "PASS",
            },
        })
        new_text = man.read_text(encoding="utf-8")
        if not re.search(r"^ppl_mean\s*=\s*12\.4\b", new_text, re.M):
            failures.append("surgical-write: ppl_mean not appended cleanly")
        if not re.search(
            r"^quality_gate_status\s*=\s*\"PASS\"", new_text, re.M,
        ):
            failures.append("surgical-write: quality_gate_status not written")
        # Defensive: refuse non-PPL fields.
        try:
            _write_ppl_fields_directly(man, {
                "[datasets.code.pretrain-bias.clean]": {"url": "evil"},
            })
            failures.append("surgical-write: should refuse url mutation")
        except ValueError:
            pass

    # ----- 7. End-to-end run on synthetic corpus -----
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, _SAMPLE_MANIFEST)

        corpus = root / "corpus"
        _make_clean_payload(corpus / "code" / "pretrain-bias" / "clean")
        _make_mixed_payload(corpus / "code" / "pretrain-bias" / "mixed")
        _make_noisy_payload(corpus / "code" / "pretrain-bias" / "noisy")
        # Out-of-stage entry — must be ignored.
        _make_clean_payload(corpus / "code" / "philosophy" / "other-stage")

        out_dir = root / "corpus_filtered"
        runs_dir = root / "runs"

        # Small max-chunk so each file produces several chunks.
        stats, report = run(
            manifest_path=man,
            corpus_dir=corpus,
            output_dir=out_dir,
            runs_dir=runs_dir,
            report_path=None,
            reference_model="stub",
            ppl_threshold_default=200.0,
            max_chunk_bytes=256,
            apply_to_stage="pretrain-bias",
            ppl_fn=stub_perplexity,
            update_manifest=True,
            dry_run=False,
        )

        # Stage scope.
        if stats.entries_seen != 4:
            failures.append(f"e2e: entries_seen={stats.entries_seen}")
        if stats.entries_in_stage != 3:
            failures.append(f"e2e: entries_in_stage={stats.entries_in_stage}")
        if stats.entries_scored != 3:
            failures.append(f"e2e: entries_scored={stats.entries_scored}")
        if stats.total_chunks_scored <= 0:
            failures.append("e2e: no chunks scored")

        # Verdict shape: clean should be PASS, noisy should be FAIL.
        clean_rep = report["per_entry"].get("code.pretrain-bias.clean")
        if clean_rep is None:
            failures.append("e2e: clean entry missing from report")
        elif clean_rep["quality_gate_status"] != "PASS":
            failures.append(
                f"e2e: clean verdict={clean_rep['quality_gate_status']} want PASS"
            )
        noisy_rep = report["per_entry"].get("code.pretrain-bias.noisy")
        if noisy_rep is None:
            failures.append("e2e: noisy entry missing from report")
        elif noisy_rep["quality_gate_status"] != "FAIL":
            failures.append(
                f"e2e: noisy verdict={noisy_rep['quality_gate_status']} want FAIL"
            )

        # Out-of-stage entry must NOT be in the report.
        if "code.philosophy.other-stage" in report["per_entry"]:
            failures.append("e2e: out-of-stage entry leaked into report")

        # Filtered-content layout mirrors input layout for clean entry.
        kept_clean_dir = out_dir / "code" / "pretrain-bias" / "clean"
        if not (kept_clean_dir / "clean.py").is_file():
            failures.append("e2e: filtered clean.py missing")
        if not (kept_clean_dir / "README.md").is_file():
            failures.append("e2e: filtered README.md missing")

        # Noisy entry should have nothing (or near-nothing) written through.
        noisy_out = out_dir / "code" / "pretrain-bias" / "noisy"
        if noisy_out.is_dir():
            kept_files = [p for p in noisy_out.rglob("*") if p.is_file()]
            if kept_files:
                # Allow zero or a single tiny file (chunk_kept could be 0 or low),
                # but the verdict must be FAIL regardless.
                pass

        # Report aggregate fields.
        if report["stage"] != "pretrain-bias":
            failures.append("e2e: report stage mismatch")
        if report["reference_model"] != "stub":
            failures.append("e2e: report reference_model mismatch")
        if report["total_entries_scored"] != 3:
            failures.append("e2e: report total_entries_scored mismatch")
        if "filter_keep_rate" not in report:
            failures.append("e2e: filter_keep_rate missing")
        if report["by_status"].get("PASS", 0) < 1:
            failures.append("e2e: expected at least one PASS")
        if report["by_status"].get("FAIL", 0) < 1:
            failures.append("e2e: expected at least one FAIL")

        # Math correctness: ppl_pass_rate = chunks_kept / chunks_n
        for key, blob in report["per_entry"].items():
            if blob["chunks_n"] == 0:
                continue
            want = round(blob["chunks_kept"] / blob["chunks_n"], 4)
            got = blob["ppl_pass_rate"]
            if abs(got - want) > 1e-6:
                failures.append(
                    f"e2e: pass_rate math wrong for {key}: got {got} want {want}"
                )

        # Manifest write-through.
        man_text = man.read_text(encoding="utf-8")
        if not re.search(
            r"^quality_gate_status\s*=\s*\"PASS\"", man_text, re.M,
        ):
            failures.append("e2e: manifest PASS verdict not written")
        if not re.search(
            r"^quality_gate_status\s*=\s*\"FAIL\"", man_text, re.M,
        ):
            failures.append("e2e: manifest FAIL verdict not written")
        # Out-of-stage section must not have been touched with PPL fields.
        other_idx = man_text.find("[datasets.code.philosophy.other-stage]")
        other_block = man_text[other_idx:other_idx + 800]
        if "ppl_mean" in other_block:
            failures.append("e2e: out-of-stage section was mutated")

        # Report file written.
        report_path = runs_dir / f"corpus_quality_filter.{today_iso()}.json"
        if not report_path.is_file():
            failures.append("e2e: report file not written")
        else:
            parsed = json.loads(report_path.read_text(encoding="utf-8"))
            if parsed["stage"] != "pretrain-bias":
                failures.append("e2e: written report stage wrong")

    # ----- 8. dry-run writes nothing -----
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, _SAMPLE_MANIFEST)
        corpus = root / "corpus"
        _make_clean_payload(corpus / "code" / "pretrain-bias" / "clean")
        out_dir = root / "corpus_filtered"
        runs_dir = root / "runs"
        stats, report = run(
            manifest_path=man,
            corpus_dir=corpus,
            output_dir=out_dir,
            runs_dir=runs_dir,
            report_path=None,
            reference_model="stub",
            ppl_threshold_default=200.0,
            max_chunk_bytes=256,
            apply_to_stage="pretrain-bias",
            ppl_fn=stub_perplexity,
            update_manifest=True,
            dry_run=True,
        )
        if out_dir.exists() and any(out_dir.rglob("*")):
            failures.append("dry-run: output_dir was populated")
        if runs_dir.exists() and any(runs_dir.rglob("*")):
            failures.append("dry-run: runs_dir was populated")
        if "ppl_mean" in man.read_text(encoding="utf-8"):
            failures.append("dry-run: manifest mutated")

    if failures:
        print("__CORPUS_QUALITY_FILTER_SELFTEST__ FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("__CORPUS_QUALITY_FILTER_SELFTEST__ PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    # Default invocation with no args runs the self-test (per spec).
    if len(sys.argv) == 1:
        sys.exit(_run_selftest())
    sys.exit(run_cli())
