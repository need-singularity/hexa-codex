#!/usr/bin/env python3
"""_common.py — shared helpers for the hexa-forge corpus pipeline tools.

Used by:
    tool/fetch_sources.py
    tool/tokenize.py

Responsibilities
----------------
- Locate the repo root and standard sub-trees (corpus/, logs/, runs/).
- Parse the `datasets.toml` manifest via `tomllib`.
- Iterate (verb, stage, id, entry) tuples in a stable order.
- Compute the deterministic on-disk path for a fetched source:
    corpus/<verb>/<stage>/<id>/
- Atomic in-place mutation of `datasets.toml` by surgical text edits
  (we deliberately do NOT round-trip via a TOML writer because there is
  no stdlib TOML emitter and we want to preserve comments, ordering, and
  formatting exactly).
- Defensive schema lock — refuse to write a field that is not in the
  declared schema set (`KNOWN_FIELDS`).

Schema
------
The known per-entry fields, per the header of `datasets.toml`:

    url, license, attribution, weight, tier, tokens_est, tokens_actual,
    fetch_status, notes, sha256_corpus

This module reads the full set and only ever mutates:
    - sha256_corpus    (by fetch_sources)
    - fetch_status     (by fetch_sources)
    - tokens_actual    (by tokenize)

Mutation policy
---------------
- `update_entry_fields()` rewrites a `key = "value"` line in place when
  the field already exists in the entry. If the field does NOT exist in
  the entry, it is appended just before the next section boundary.
- All writes go through `atomic_write_text()` which writes to
  `<path>.tmp` then `os.replace()` for crash-safety.

This module is Python 3.11+ stdlib only. No third-party deps.
"""
from __future__ import annotations

# `tool/tokenize.py` lives next to this file and shadows the stdlib
# `tokenize` module that `linecache` imports. When this file is launched
# directly (`python tool/_common.py --selftest`), Python adds `tool/` to
# sys.path[0] and the shadowing fires inside `dataclasses` -> `inspect`.
# Pre-emptively prune the script directory before importing anything that
# transitively walks that chain.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import os
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

DEFAULT_MANIFEST: Path = REPO_ROOT / "datasets.toml"
DEFAULT_CORPUS_DIR: Path = REPO_ROOT / "corpus"
DEFAULT_LOGS_DIR: Path = REPO_ROOT / "logs"
DEFAULT_RUNS_DIR: Path = REPO_ROOT / "runs"


# ---------------------------------------------------------------------------
# Schema lock
# ---------------------------------------------------------------------------

KNOWN_FIELDS: frozenset[str] = frozenset({
    "url",
    "license",
    "attribution",
    "weight",
    "tier",
    "tokens_est",
    "tokens_actual",
    "fetch_status",
    "notes",
    "sha256_corpus",
})

# Fields the pipeline tools are permitted to mutate. Anything outside this
# set is curator-owned and may not be touched by automation.
MUTABLE_FIELDS: frozenset[str] = frozenset({
    "tokens_actual",
    "fetch_status",
    "sha256_corpus",
})

VALID_FETCH_STATUS: frozenset[str] = frozenset({
    "pending",
    "fetched",
    "blocked-by-license",
    "url-broken",
    "pdf-pending",
})


# ---------------------------------------------------------------------------
# Manifest entry model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Entry:
    """A single dataset entry as resolved from `datasets.toml`."""

    verb: str
    stage: str
    id: str
    url: str
    license: str
    attribution: Optional[str]
    weight: float
    tier: str
    tokens_est: str
    tokens_actual: str
    fetch_status: str
    notes: Optional[str]
    sha256_corpus: str

    @property
    def section_header(self) -> str:
        """`[datasets.<verb>.<stage>.<id>]` — the TOML section line."""
        return f"[datasets.{self.verb}.{self.stage}.{self.id}]"

    def corpus_path(self, corpus_dir: Path) -> Path:
        """Deterministic on-disk path for this entry's fetched payload."""
        return corpus_dir / self.verb / self.stage / self.id


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> dict:
    """Parse the TOML manifest via stdlib `tomllib`. Returns the raw dict."""
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def iter_entries(manifest: dict) -> Iterator[Entry]:
    """Yield Entry objects in source-file order (TOML preserves insertion).

    Iterates `manifest["datasets"][verb][stage][id]` for every leaf table.
    """
    datasets = manifest.get("datasets", {})
    for verb, by_stage in datasets.items():
        if not isinstance(by_stage, dict):
            continue
        for stage, by_id in by_stage.items():
            if not isinstance(by_id, dict):
                continue
            for entry_id, fields in by_id.items():
                if not isinstance(fields, dict):
                    continue
                yield _entry_from_fields(verb, stage, entry_id, fields)


def _entry_from_fields(verb: str, stage: str, entry_id: str, f: dict) -> Entry:
    """Coerce a raw TOML table into an `Entry`, supplying defaults."""
    return Entry(
        verb=verb,
        stage=stage,
        id=entry_id,
        url=str(f.get("url", "")),
        license=str(f.get("license", "UNKNOWN")),
        attribution=f.get("attribution"),
        weight=float(f.get("weight", 1.0)),
        tier=str(f.get("tier", "")),
        tokens_est=str(f.get("tokens_est", "")),
        tokens_actual=str(f.get("tokens_actual", "")),
        fetch_status=str(f.get("fetch_status", "pending")),
        notes=f.get("notes"),
        sha256_corpus=str(f.get("sha256_corpus", "")),
    )


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------

def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write `text` to `path` atomically via tmp + os.replace.

    Creates the parent directory if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Surgical manifest mutation
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$", re.M)


def _section_bounds(text: str, header: str) -> tuple[int, int]:
    """Return (start, end) byte offsets for the named section's body.

    `header` is the bare bracketed line (e.g. `[datasets.code.philosophy.x]`).
    `start` is the offset of the first character after the header newline.
    `end` is the offset of the first character of the *next* section (or
    end-of-file). Raises KeyError if the header is not present.
    """
    needle = header + "\n"
    idx = text.find(needle)
    if idx < 0:
        # Try without trailing newline (e.g. last line of file with no \n).
        idx = text.find(header)
        if idx < 0 or (idx + len(header) < len(text) and text[idx + len(header)] != "\n"):
            raise KeyError(header)
    start = idx + len(needle) if needle in text else idx + len(header) + 1
    # Find the next section header after start.
    m = _SECTION_RE.search(text, pos=start)
    end = m.start() if m else len(text)
    return start, end


def _kv_line_re(key: str) -> re.Pattern[str]:
    """Match `key = ...` (whitespace-tolerant) at line start, single line."""
    return re.compile(
        r"^(?P<indent>[ \t]*)" + re.escape(key) + r"(?P<gap>[ \t]*=[ \t]*).*$",
        re.M,
    )


def _toml_quote(value: str) -> str:
    """Quote a string value for TOML. Uses double quotes; escapes \\ and \"."""
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


def update_entry_fields(
    manifest_text: str,
    section_header: str,
    updates: dict[str, str],
) -> str:
    """Return a new manifest text with the entry's fields updated in place.

    Rules:
    - Every key in `updates` must be in `MUTABLE_FIELDS`. Anything else
      raises `ValueError` (defensive schema lock).
    - If the field already exists in the section, the line is rewritten
      preserving indentation and the `=` gap.
    - If the field does not exist, it is appended at the end of the
      section (just before the next section header or EOF).

    The `updates` dict maps field name -> raw string value. Values are
    wrapped in double quotes per TOML string conventions. Numbers (e.g.
    weight) are NOT in MUTABLE_FIELDS so this is fine.
    """
    bad = sorted(set(updates) - MUTABLE_FIELDS)
    if bad:
        raise ValueError(
            f"refusing to mutate non-mutable fields: {bad} "
            f"(allowed: {sorted(MUTABLE_FIELDS)})"
        )
    # Validate fetch_status value if present.
    if "fetch_status" in updates:
        fs = updates["fetch_status"]
        if fs not in VALID_FETCH_STATUS:
            raise ValueError(
                f"invalid fetch_status {fs!r}; expected one of {sorted(VALID_FETCH_STATUS)}"
            )

    try:
        start, end = _section_bounds(manifest_text, section_header)
    except KeyError as exc:
        raise KeyError(f"section not found in manifest: {section_header}") from exc

    body = manifest_text[start:end]
    new_body = body

    # Determine an indent / gap convention from any existing line in the
    # section (fall back to the conventional alignment used in the file).
    indent = ""
    gap = " = "
    sample = re.search(r"^([ \t]*)([A-Za-z0-9_.\-]+)([ \t]*=[ \t]*)", body, re.M)
    if sample:
        indent = sample.group(1)
        gap = sample.group(3)

    for key, value in updates.items():
        pat = _kv_line_re(key)
        m = pat.search(new_body)
        if m:
            # Preserve the existing line's own indent and gap exactly so we
            # do not reflow the curator's alignment.
            existing_indent = m.group("indent")
            existing_gap = m.group("gap")
            line = f"{existing_indent}{key}{existing_gap}{_toml_quote(value)}"
            new_body = new_body[:m.start()] + line + new_body[m.end():]
        else:
            # Append at end of section body using the section's sniffed
            # indent/gap convention.
            line = f"{indent}{key}{gap}{_toml_quote(value)}"
            tail = new_body.rstrip("\n")
            if new_body.endswith("\n\n"):
                new_body = tail + "\n" + line + "\n\n"
            else:
                new_body = tail + "\n" + line + "\n"

    return manifest_text[:start] + new_body + manifest_text[end:]


def apply_manifest_updates(
    manifest_path: Path,
    updates_by_section: dict[str, dict[str, str]],
) -> None:
    """Apply `{section_header: {field: value}}` updates atomically.

    All sections must already exist. The whole batch is applied in one
    in-memory pass, then written atomically.
    """
    text = manifest_path.read_text(encoding="utf-8")
    for header, updates in updates_by_section.items():
        text = update_entry_fields(text, header, updates)
    atomic_write_text(manifest_path, text)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def today_iso() -> str:
    """`YYYY-MM-DD` for log/run filenames."""
    import datetime as _dt
    return _dt.date.today().isoformat()


def now_iso() -> str:
    """Timezone-aware UTC ISO-8601 timestamp."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """Inline self-test: round-trip a tiny manifest and check field rewrite."""
    import tempfile

    sample = (
        "[meta]\n"
        "schema_version = \"0.1.0\"\n"
        "\n"
        "[datasets.code.philosophy.alpha]\n"
        "url           = \"https://example.com/alpha\"\n"
        "license       = \"MIT\"\n"
        "weight        = 1.0\n"
        "tier          = \"A\"\n"
        "tokens_est    = \"10K\"\n"
        "tokens_actual = \"\"\n"
        "fetch_status  = \"pending\"\n"
        "sha256_corpus = \"\"\n"
        "\n"
        "[datasets.code.philosophy.beta]\n"
        "url           = \"https://example.com/beta\"\n"
        "license       = \"Apache-2.0\"\n"
        "weight        = 1.0\n"
        "tier          = \"A\"\n"
        "tokens_est    = \"100K\"\n"
        "tokens_actual = \"\"\n"
        "fetch_status  = \"pending\"\n"
        "sha256_corpus = \"\"\n"
    )

    failures: list[str] = []

    # 1. tomllib parses the sample.
    parsed = tomllib.loads(sample)
    entries = list(iter_entries(parsed))
    if len(entries) != 2:
        failures.append(f"iter_entries: expected 2, got {len(entries)}")
    if entries and entries[0].id != "alpha":
        failures.append(f"iter_entries order: expected alpha first, got {entries[0].id}")

    # 2. update_entry_fields rewrites an existing line.
    out = update_entry_fields(
        sample,
        "[datasets.code.philosophy.alpha]",
        {"fetch_status": "fetched", "sha256_corpus": "deadbeef"},
    )
    if "fetch_status  = \"fetched\"" not in out:
        failures.append("update_entry_fields: fetch_status not rewritten")
    if "sha256_corpus = \"deadbeef\"" not in out:
        failures.append("update_entry_fields: sha256_corpus not rewritten")
    # Beta untouched.
    if "[datasets.code.philosophy.beta]" not in out:
        failures.append("update_entry_fields: beta section dropped")
    if out.count("fetch_status  = \"pending\"") != 1:
        failures.append("update_entry_fields: bled into beta or duplicated")

    # 3. defensive schema lock: refuse mutating url.
    try:
        update_entry_fields(
            sample, "[datasets.code.philosophy.alpha]", {"url": "evil"},
        )
        failures.append("schema lock: should have rejected url mutation")
    except ValueError:
        pass

    # 4. defensive fetch_status value check.
    try:
        update_entry_fields(
            sample, "[datasets.code.philosophy.alpha]",
            {"fetch_status": "not-a-real-status"},
        )
        failures.append("status validation: should have rejected bogus value")
    except ValueError:
        pass

    # 5. missing section raises KeyError.
    try:
        update_entry_fields(sample, "[datasets.code.philosophy.missing]", {"sha256_corpus": "x"})
        failures.append("missing section: should have raised KeyError")
    except KeyError:
        pass

    # 6. atomic_write_text round-trip.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.toml"
        atomic_write_text(p, sample)
        if p.read_text(encoding="utf-8") != sample:
            failures.append("atomic_write_text: round-trip mismatch")

    if failures:
        print("_common.py SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("_common.py SELFTEST PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_selftest())
