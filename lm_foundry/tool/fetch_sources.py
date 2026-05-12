#!/usr/bin/env python3
"""fetch_sources.py — license-respecting corpus fetcher for hexa-forge.

Phase v0.1.2 deliverable per `papers/plan-domain-coverage.md §7` token
roll-up reconciliation. Walks `datasets.toml`, fetches each non-blocked
entry into `corpus/<verb>/<stage>/<id>/`, computes a SHA-256 over the
normalised payload, and (optionally) writes `sha256_corpus` +
`fetch_status` back into the manifest.

Companion: `tool/tokenize.py` then counts real tokens against the
fetched payloads to fill `tokens_actual`.

CONTENT TYPE DISPATCH
---------------------
- GitHub repo URL (`*.git` or `github.com/<owner>/<repo>` form):
    `git clone --depth=1` into the target directory. The sha256 is
    computed over the sorted file listing + the HEAD commit, NOT over
    a single binary blob — this keeps the digest deterministic across
    clone runs as long as the upstream HEAD hasn't moved.
- HTML page:
    Download, extract the text via a minimal stdlib `html.parser`
    based node-walker, save both `raw.html` and `text.md`. SHA-256 is
    taken over `text.md`.
- Plain text / markdown / json:
    Saved verbatim under a sensible filename derived from the URL.
- PDF:
    Marked as `pdf-pending` (no extraction at v0.1.2; deferred to v0.2.0
    with a dedicated parser).

LICENSE RESPECT
---------------
- `license` ∈ {UNKNOWN, proprietary, QUOTE-ONLY} are skipped unless
  `--include-quote-only` is passed.
- `fetch_status` ∈ {blocked-by-license, url-broken, fetched} are skipped.
- For CC-BY-* entries with an `attribution` string, the attribution is
  written to `LICENSE.attribution` alongside the payload.

RATE LIMITING
-------------
- Default 1.0 req/sec/host (`--rate-host`).
- Concurrent host buckets capped via a simple per-host last-fetch clock;
  this tool fetches serially within a host but may interleave across
  hosts. (We deliberately do NOT spawn threads — fetches are I/O bound
  but the host count is small and a serial loop keeps logs orderly.)
- HTTP `Retry-After` (seconds or HTTP-date) is honoured.

LOG SCHEMA — `logs/fetch_sources.<date>.jsonl`
----------------------------------------------
One JSON object per line:
    {
      "ts":         "2026-05-11T12:34:56Z",
      "verb":       "code",
      "stage":      "philosophy",
      "id":         "pep-8",
      "url":        "https://...",
      "license":    "public-domain",
      "kind":       "html|git|text|pdf|skip",
      "bytes":      12345,
      "sha256":     "deadbeef...",
      "latency_ms": 412,
      "result":     "fetched|skipped|error|pdf-pending",
      "reason":     "<short string when result != fetched>"
    }

USAGE
-----
    python tool/fetch_sources.py --dry-run
    python tool/fetch_sources.py --tier A --stage philosophy
    python tool/fetch_sources.py --update-manifest

Dependencies: Python 3.11+ stdlib only (`urllib.request`, `html.parser`,
`tomllib`, `subprocess` for `git clone`). No third-party packages.

Manifest fields read:
    url, license, attribution, weight, tier, tokens_est, tokens_actual,
    fetch_status, notes, sha256_corpus

Manifest fields written (only with `--update-manifest`):
    fetch_status, sha256_corpus
"""
from __future__ import annotations

# `tool/tokenize.py` lives next to this file and shadows stdlib `tokenize`
# (used transitively by `linecache`). Prune the script directory from
# sys.path before any imports that might trigger that resolution chain.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import datetime as _dt
import email.utils
import hashlib
import html
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

# Load _common.py explicitly via importlib (we cannot put `tool/` back on
# sys.path without re-introducing the stdlib-shadow problem).
def _load_common():
    mod_name = "_hexa_forge_common"
    if mod_name in _sys.modules:
        return _sys.modules[mod_name]
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
DEFAULT_LOGS_DIR = _common.DEFAULT_LOGS_DIR
DEFAULT_MANIFEST = _common.DEFAULT_MANIFEST
Entry = _common.Entry
apply_manifest_updates = _common.apply_manifest_updates
atomic_write_bytes = _common.atomic_write_bytes
atomic_write_text = _common.atomic_write_text
ensure_dir = _common.ensure_dir
iter_entries = _common.iter_entries
load_manifest = _common.load_manifest
now_iso = _common.now_iso
today_iso = _common.today_iso


USER_AGENT = "hexa-forge-fetcher/0.1.2 (+https://github.com/hexa-forge)"
DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_RATE_HOST = 1.0
DEFAULT_TIMEOUT_S = 30.0

SKIP_LICENSES_DEFAULT: frozenset[str] = frozenset({
    "UNKNOWN",
    "proprietary",
    "Proprietary",
    "QUOTE-ONLY",
})
ATTRIBUTION_LICENSES: frozenset[str] = frozenset({
    "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-SA-2.0",
})


# ---------------------------------------------------------------------------
# Content type detection
# ---------------------------------------------------------------------------

def detect_kind_from_url(url: str) -> str:
    """Classify a URL into a fetch strategy: html | git | text | pdf | other."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    if path.endswith(".git"):
        return "git"
    # GitHub repo root pattern: github.com/<owner>/<repo>[/]
    if host == "github.com":
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) == 2:
            return "git"

    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith((".md", ".markdown", ".txt", ".rst", ".json")):
        return "text"
    # Default to HTML; refined after content-type is sniffed.
    return "html"


def refine_kind_from_content_type(kind: str, content_type: str) -> str:
    ct = (content_type or "").lower().split(";")[0].strip()
    if ct == "application/pdf":
        return "pdf"
    if ct in {"text/markdown", "text/plain", "application/json", "text/x-rst"}:
        return "text"
    if ct in {"text/html", "application/xhtml+xml"}:
        return "html"
    return kind


# ---------------------------------------------------------------------------
# HTML -> text via html.parser
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Walk an HTML document and emit a plain-text approximation.

    Strategy:
    - Skip the contents of <script>, <style>, <noscript>, <template>.
    - Insert one blank line at block-level boundaries (<p>, <div>, <li>,
      <h1>..<h6>, <pre>, <blockquote>, <table>, <tr>).
    - <br> -> single newline.
    - <a> text is kept; URLs are dropped (no markdown link round-trip).
    - <pre>/<code> contents are preserved verbatim.

    This is intentionally minimal — for high-fidelity extraction we will
    swap in a real HTML parser in v0.2.0. The output is good enough for
    token counting and license-clean scanning.
    """

    BLOCK_TAGS = {
        "p", "div", "li", "ul", "ol", "section", "article", "header",
        "footer", "nav", "main", "aside", "blockquote", "pre", "table",
        "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br",
    }
    SKIP_TAGS = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_pre = 0

    # ------ HTMLParser API ------
    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "pre":
            self._in_pre += 1
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n\n" if tag != "br" else "\n")

    def handle_endtag(self, tag: str):  # type: ignore[override]
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if tag == "pre" and self._in_pre > 0:
            self._in_pre -= 1
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n\n" if tag != "br" else "\n")

    def handle_data(self, data: str):  # type: ignore[override]
        if self._skip_depth > 0:
            return
        if self._in_pre > 0:
            self._chunks.append(data)
        else:
            self._chunks.append(data)

    # ------ exposed ------
    def get_text(self) -> str:
        joined = "".join(self._chunks)
        # Collapse 3+ newlines to exactly 2; strip trailing whitespace per line.
        lines = [ln.rstrip() for ln in joined.split("\n")]
        out: list[str] = []
        blank_run = 0
        for ln in lines:
            if not ln:
                blank_run += 1
                if blank_run <= 1:
                    out.append("")
            else:
                blank_run = 0
                out.append(ln)
        return "\n".join(out).strip() + "\n"


def html_to_text(raw_html: str) -> str:
    """Run the stdlib-only HTML extractor over `raw_html`."""
    ex = _TextExtractor()
    try:
        ex.feed(raw_html)
        ex.close()
    except Exception:
        # On any parse error fall back to a crude tag-strip via unescape.
        # This is best-effort; the digest will still be deterministic.
        return html.unescape(raw_html)
    return ex.get_text()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class HostRateLimiter:
    """Enforce N requests/sec per host with a simple monotonic clock."""

    def __init__(self, rate_per_sec: float) -> None:
        self.min_interval = 1.0 / rate_per_sec if rate_per_sec > 0 else 0.0
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        prev = self._last.get(host, 0.0)
        wait_s = (prev + self.min_interval) - now
        if wait_s > 0:
            time.sleep(wait_s)
        self._last[host] = time.monotonic()


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------

@dataclass
class HttpResult:
    body: bytes
    content_type: str
    final_url: str
    status: int


def http_get(
    url: str,
    *,
    max_bytes: int,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> HttpResult:
    """GET `url` with a User-Agent and a hard byte cap.

    Raises urllib.error.URLError / HTTPError on transport failure.
    Returns the body, content-type, final URL (after redirects), and
    HTTP status.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        ct = resp.headers.get("Content-Type", "")
        body = resp.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError(f"response exceeded max_bytes={max_bytes}")
        return HttpResult(
            body=body,
            content_type=ct,
            final_url=resp.geturl(),
            status=resp.status,
        )


def parse_retry_after(value: str) -> Optional[float]:
    """Parse an HTTP `Retry-After` header to seconds, or None."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    delta = (dt - _dt.datetime.now(_dt.timezone.utc)).total_seconds()
    return max(delta, 0.0)


# ---------------------------------------------------------------------------
# Per-strategy fetchers
# ---------------------------------------------------------------------------

@dataclass
class FetchOutcome:
    kind: str         # html | git | text | pdf | skip
    bytes: int        # payload byte count
    sha256: str       # digest over normalised payload
    result: str       # fetched | pdf-pending | skipped | error
    reason: str = ""  # short human-readable explanation


def fetch_html(
    entry: Entry,
    target_dir: Path,
    *,
    max_bytes: int,
    rate: HostRateLimiter,
) -> FetchOutcome:
    """Fetch an HTML document, extract text, persist both."""
    host = urllib.parse.urlparse(entry.url).netloc
    rate.wait(host)
    try:
        r = http_get(entry.url, max_bytes=max_bytes)
    except urllib.error.HTTPError as e:
        retry = parse_retry_after(e.headers.get("Retry-After", "") if e.headers else "")
        if retry is not None and retry < 60:
            time.sleep(retry)
            try:
                r = http_get(entry.url, max_bytes=max_bytes)
            except Exception as e2:
                return FetchOutcome("html", 0, "", "error", f"http retry failed: {e2}")
        else:
            return FetchOutcome("html", 0, "", "error", f"http {e.code}: {e.reason}")
    except Exception as e:
        return FetchOutcome("html", 0, "", "error", str(e))

    kind = refine_kind_from_content_type("html", r.content_type)
    if kind == "pdf":
        atomic_write_bytes(target_dir / "raw.pdf", r.body)
        return FetchOutcome("pdf", len(r.body), "", "pdf-pending", "content-type pdf; deferred")

    raw_html = r.body.decode("utf-8", errors="replace")
    text = html_to_text(raw_html) if kind == "html" else raw_html
    atomic_write_bytes(target_dir / "raw.html", r.body)
    text_bytes = text.encode("utf-8")
    atomic_write_bytes(target_dir / "text.md", text_bytes)
    digest = hashlib.sha256(text_bytes).hexdigest()
    return FetchOutcome(kind, len(text_bytes), digest, "fetched")


def fetch_text(
    entry: Entry,
    target_dir: Path,
    *,
    max_bytes: int,
    rate: HostRateLimiter,
) -> FetchOutcome:
    """Fetch a plain-text-ish resource; save verbatim."""
    host = urllib.parse.urlparse(entry.url).netloc
    rate.wait(host)
    try:
        r = http_get(entry.url, max_bytes=max_bytes)
    except Exception as e:
        return FetchOutcome("text", 0, "", "error", str(e))

    # Refine to PDF if server says so.
    if refine_kind_from_content_type("text", r.content_type) == "pdf":
        atomic_write_bytes(target_dir / "raw.pdf", r.body)
        return FetchOutcome("pdf", len(r.body), "", "pdf-pending", "content-type pdf; deferred")

    # Derive filename from URL path.
    path = urllib.parse.urlparse(entry.url).path
    name = os.path.basename(path) or "raw.txt"
    atomic_write_bytes(target_dir / name, r.body)
    digest = hashlib.sha256(r.body).hexdigest()
    return FetchOutcome("text", len(r.body), digest, "fetched")


def fetch_pdf(
    entry: Entry,
    target_dir: Path,
    *,
    max_bytes: int,
    rate: HostRateLimiter,
) -> FetchOutcome:
    """Download a PDF; mark pdf-pending (no extraction yet)."""
    host = urllib.parse.urlparse(entry.url).netloc
    rate.wait(host)
    try:
        r = http_get(entry.url, max_bytes=max_bytes)
    except Exception as e:
        return FetchOutcome("pdf", 0, "", "error", str(e))
    atomic_write_bytes(target_dir / "raw.pdf", r.body)
    return FetchOutcome("pdf", len(r.body), "", "pdf-pending", "deferred to v0.2.0")


def fetch_git(
    entry: Entry,
    target_dir: Path,
    *,
    rate: HostRateLimiter,
) -> FetchOutcome:
    """Shallow-clone a git repo. Digest = sha256 of sorted file listing.

    The digest is computed over a deterministic manifest line set:
        <relpath>\\t<size>\\n
    sorted by relpath. This gives a stable hash without slurping every
    file. We also capture HEAD into `GIT_HEAD` for provenance.
    """
    host = urllib.parse.urlparse(entry.url).netloc
    rate.wait(host)

    clone_dir = target_dir / "repo"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    cmd = ["git", "clone", "--depth=1", "--no-tags", entry.url, str(clone_dir)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        return FetchOutcome("git", 0, "", "error", "git binary not on PATH")
    except subprocess.TimeoutExpired:
        return FetchOutcome("git", 0, "", "error", "git clone timed out")

    if proc.returncode != 0:
        return FetchOutcome(
            "git", 0, "", "error",
            f"git clone exit {proc.returncode}: {proc.stderr.strip()[:200]}",
        )

    # Record HEAD for provenance.
    try:
        head = subprocess.check_output(
            ["git", "-C", str(clone_dir), "rev-parse", "HEAD"],
            text=True, timeout=10,
        ).strip()
    except Exception:
        head = ""
    atomic_write_text(target_dir / "GIT_HEAD", head + "\n")

    # Build deterministic manifest of files within the repo.
    entries: list[tuple[str, int]] = []
    total_bytes = 0
    for root, dirs, files in os.walk(clone_dir):
        # Skip the .git internals; they're irrelevant for corpus content.
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in files:
            full = Path(root) / fn
            try:
                size = full.stat().st_size
            except OSError:
                continue
            rel = str(full.relative_to(clone_dir))
            entries.append((rel, size))
            total_bytes += size

    entries.sort()
    manifest_text = "".join(f"{rel}\t{size}\n" for rel, size in entries)
    atomic_write_text(target_dir / "REPO_MANIFEST.tsv", manifest_text)
    digest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    return FetchOutcome("git", total_bytes, digest, "fetched", f"head={head[:10]}")


# ---------------------------------------------------------------------------
# Per-entry dispatcher
# ---------------------------------------------------------------------------

@dataclass
class FetchPlan:
    entry: Entry
    target_dir: Path
    decision: str          # "fetch" | "skip"
    skip_reason: str = ""  # populated when decision == "skip"


def plan_entry(
    entry: Entry,
    corpus_dir: Path,
    *,
    include_quote_only: bool,
    tier_filter: Optional[str],
    stage_filter: Optional[str],
) -> FetchPlan:
    """Decide whether to fetch this entry; produce a plan record."""
    target_dir = entry.corpus_path(corpus_dir)

    if tier_filter and tier_filter != "all" and entry.tier != tier_filter:
        return FetchPlan(entry, target_dir, "skip", f"tier!={tier_filter}")
    if stage_filter and stage_filter != "all" and entry.stage != stage_filter:
        return FetchPlan(entry, target_dir, "skip", f"stage!={stage_filter}")

    if entry.fetch_status in {"blocked-by-license", "url-broken", "fetched"}:
        return FetchPlan(entry, target_dir, "skip", f"fetch_status={entry.fetch_status}")

    if entry.license in SKIP_LICENSES_DEFAULT:
        if not include_quote_only:
            return FetchPlan(entry, target_dir, "skip", f"license={entry.license}")
        # Quote-only is allowed under the flag, but proprietary/UNKNOWN are
        # never auto-fetched even with the flag — we only relax QUOTE-ONLY.
        if entry.license != "QUOTE-ONLY":
            return FetchPlan(entry, target_dir, "skip", f"license={entry.license}")

    if not entry.url:
        return FetchPlan(entry, target_dir, "skip", "empty url")

    return FetchPlan(entry, target_dir, "fetch")


def write_attribution(entry: Entry, target_dir: Path) -> None:
    """Write `LICENSE.attribution` for CC-BY-* entries when present."""
    if entry.license not in ATTRIBUTION_LICENSES:
        return
    if not entry.attribution:
        return
    atomic_write_text(target_dir / "LICENSE.attribution", entry.attribution + "\n")


def execute_plan(
    plan: FetchPlan,
    *,
    max_bytes: int,
    rate: HostRateLimiter,
) -> FetchOutcome:
    """Dispatch on URL kind and run the matching fetcher."""
    ensure_dir(plan.target_dir)
    write_attribution(plan.entry, plan.target_dir)

    kind = detect_kind_from_url(plan.entry.url)
    if kind == "git":
        return fetch_git(plan.entry, plan.target_dir, rate=rate)
    if kind == "pdf":
        return fetch_pdf(plan.entry, plan.target_dir, max_bytes=max_bytes, rate=rate)
    if kind == "text":
        return fetch_text(plan.entry, plan.target_dir, max_bytes=max_bytes, rate=rate)
    return fetch_html(plan.entry, plan.target_dir, max_bytes=max_bytes, rate=rate)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

@dataclass
class DriverStats:
    planned: int = 0
    skipped: int = 0
    fetched: int = 0
    pdf_pending: int = 0
    errors: int = 0


def run(
    *,
    manifest_path: Path,
    corpus_dir: Path,
    logs_dir: Path,
    tier_filter: Optional[str],
    stage_filter: Optional[str],
    include_quote_only: bool,
    max_bytes: int,
    rate_host: float,
    dry_run: bool,
    update_manifest: bool,
) -> DriverStats:
    """Top-level execution loop."""
    manifest = load_manifest(manifest_path)
    entries = list(iter_entries(manifest))

    rate = HostRateLimiter(rate_host)
    stats = DriverStats()
    log_path = logs_dir / f"fetch_sources.{today_iso()}.jsonl"
    log_lines: list[str] = []
    pending_manifest_updates: dict[str, dict[str, str]] = {}

    for entry in entries:
        stats.planned += 1
        plan = plan_entry(
            entry, corpus_dir,
            include_quote_only=include_quote_only,
            tier_filter=tier_filter,
            stage_filter=stage_filter,
        )

        if plan.decision == "skip":
            stats.skipped += 1
            log_lines.append(json.dumps({
                "ts": now_iso(),
                "verb": entry.verb,
                "stage": entry.stage,
                "id": entry.id,
                "url": entry.url,
                "license": entry.license,
                "kind": "skip",
                "bytes": 0,
                "sha256": "",
                "latency_ms": 0,
                "result": "skipped",
                "reason": plan.skip_reason,
            }))
            continue

        if dry_run:
            log_lines.append(json.dumps({
                "ts": now_iso(),
                "verb": entry.verb,
                "stage": entry.stage,
                "id": entry.id,
                "url": entry.url,
                "license": entry.license,
                "kind": detect_kind_from_url(entry.url),
                "bytes": 0,
                "sha256": "",
                "latency_ms": 0,
                "result": "dry-run",
                "reason": "",
            }))
            continue

        t0 = time.monotonic()
        outcome = execute_plan(plan, max_bytes=max_bytes, rate=rate)
        latency_ms = int((time.monotonic() - t0) * 1000)

        log_lines.append(json.dumps({
            "ts": now_iso(),
            "verb": entry.verb,
            "stage": entry.stage,
            "id": entry.id,
            "url": entry.url,
            "license": entry.license,
            "kind": outcome.kind,
            "bytes": outcome.bytes,
            "sha256": outcome.sha256,
            "latency_ms": latency_ms,
            "result": outcome.result,
            "reason": outcome.reason,
        }))

        if outcome.result == "fetched":
            stats.fetched += 1
            pending_manifest_updates[entry.section_header] = {
                "fetch_status": "fetched",
                "sha256_corpus": outcome.sha256,
            }
        elif outcome.result == "pdf-pending":
            stats.pdf_pending += 1
            pending_manifest_updates[entry.section_header] = {
                "fetch_status": "pdf-pending",
            }
        else:
            stats.errors += 1

    # Persist log.
    if log_lines:
        ensure_dir(logs_dir)
        # Append-mode: a re-run on the same date adds more lines, preserving
        # the resume-safe behaviour.
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        atomic_write_text(log_path, existing + "\n".join(log_lines) + "\n")

    # Apply manifest mutations atomically.
    if update_manifest and pending_manifest_updates and not dry_run:
        apply_manifest_updates(manifest_path, pending_manifest_updates)

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "License notes:\n"
        "  - Entries with license in {UNKNOWN, proprietary, QUOTE-ONLY} are\n"
        "    skipped unless --include-quote-only is set (which relaxes only\n"
        "    QUOTE-ONLY — UNKNOWN/proprietary always stay blocked).\n"
        "  - CC-BY-* entries with an `attribution` field get a\n"
        "    LICENSE.attribution file written alongside the payload.\n"
        "\n"
        "Dependencies: Python 3.11+ stdlib only. No `pip install` required.\n"
        "Requires `git` on PATH for repo entries.\n"
    )
    ap = argparse.ArgumentParser(
        prog="fetch_sources.py",
        description="License-respecting corpus fetcher for hexa-forge v0.1.2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                    help=f"datasets.toml path (default: {DEFAULT_MANIFEST})")
    ap.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR,
                    help=f"output corpus root (default: {DEFAULT_CORPUS_DIR})")
    ap.add_argument("--logs-dir", type=Path, default=DEFAULT_LOGS_DIR,
                    help=f"log output directory (default: {DEFAULT_LOGS_DIR})")
    ap.add_argument("--tier",
                    choices=["A", "B", "C", "D", "E", "F1", "F2", "F3", "all"],
                    default="all",
                    help="filter by tier (default: all)")
    ap.add_argument("--stage", default="all",
                    help="filter by stage name (default: all)")
    ap.add_argument("--include-quote-only", action="store_true",
                    help="also fetch QUOTE-ONLY licensed sources (excerpts allowed)")
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                    help=f"per-source byte cap (default: {DEFAULT_MAX_BYTES})")
    ap.add_argument("--rate-host", type=float, default=DEFAULT_RATE_HOST,
                    help=f"requests/sec per host (default: {DEFAULT_RATE_HOST})")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; do not fetch")
    ap.add_argument("--update-manifest", action="store_true",
                    help="write sha256_corpus + fetch_status back into the manifest")
    ap.add_argument("--selftest", action="store_true",
                    help="run inline tests and exit (no network)")
    return ap


def run_cli(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.selftest:
        return _run_selftest()

    stats = run(
        manifest_path=args.manifest,
        corpus_dir=args.corpus_dir,
        logs_dir=args.logs_dir,
        tier_filter=args.tier,
        stage_filter=args.stage,
        include_quote_only=args.include_quote_only,
        max_bytes=args.max_bytes,
        rate_host=args.rate_host,
        dry_run=args.dry_run,
        update_manifest=args.update_manifest,
    )
    print(
        f"fetch_sources: planned={stats.planned} skipped={stats.skipped} "
        f"fetched={stats.fetched} pdf_pending={stats.pdf_pending} "
        f"errors={stats.errors}"
    )
    return 0 if stats.errors == 0 else 1


# ---------------------------------------------------------------------------
# Self-test — synthetic manifest, no network
# ---------------------------------------------------------------------------

_SAMPLE_MANIFEST = """\
[meta]
schema_version = "0.1.0"

[datasets.code.philosophy.fake-html]
url           = "https://example.invalid/page"
license       = "MIT"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "pending"
notes         = "synthetic"
sha256_corpus = ""

[datasets.code.philosophy.fake-text]
url           = "https://example.invalid/notes.md"
license       = "CC-BY-4.0"
attribution   = "(c) anon, CC-BY-4.0, https://example.invalid/notes.md"
weight        = 1.0
tier          = "B"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "pending"
sha256_corpus = ""

[datasets.code.philosophy.fake-blocked]
url           = "https://example.invalid/private"
license       = "QUOTE-ONLY"
weight        = 1.0
tier          = "A"
tokens_est    = "10K"
tokens_actual = ""
fetch_status  = "blocked-by-license"
sha256_corpus = ""
"""


def _run_selftest() -> int:
    """Self-test: dispatch logic, classification, html extraction. No network."""
    failures: list[str] = []

    # 1. HTML extractor smoke test.
    sample_html = (
        "<html><head><title>t</title><style>p{color:red}</style></head>"
        "<body><h1>Title</h1><p>Hello <b>world</b>.</p>"
        "<script>bad()</script>"
        "<pre>def f():\n    return 1\n</pre></body></html>"
    )
    text = html_to_text(sample_html)
    if "bad()" in text:
        failures.append("html_to_text: <script> body leaked")
    if "Title" not in text or "Hello world." not in text:
        failures.append("html_to_text: visible text missing")
    if "def f():" not in text:
        failures.append("html_to_text: <pre> content missing")

    # 2. URL kind detection.
    cases = [
        ("https://github.com/python/cpython", "git"),
        ("https://github.com/python/cpython.git", "git"),
        ("https://example.com/foo.pdf", "pdf"),
        ("https://example.com/readme.md", "text"),
        ("https://example.com/page", "html"),
        ("https://example.com/data.json", "text"),
    ]
    for url, want in cases:
        got = detect_kind_from_url(url)
        if got != want:
            failures.append(f"detect_kind_from_url({url!r}) = {got!r}, expected {want!r}")

    # 3. content-type refinement.
    if refine_kind_from_content_type("html", "application/pdf") != "pdf":
        failures.append("refine: pdf content-type ignored")
    if refine_kind_from_content_type("html", "text/html; charset=utf-8") != "html":
        failures.append("refine: html content-type with charset")

    # 4. plan_entry dispatch on the synthetic manifest.
    import tomllib as _tomllib
    parsed = _tomllib.loads(_SAMPLE_MANIFEST)
    entries = list(iter_entries(parsed))
    if len(entries) != 3:
        failures.append(f"iter_entries: expected 3 from sample, got {len(entries)}")

    with tempfile.TemporaryDirectory() as td:
        cdir = Path(td)
        plans = [
            plan_entry(e, cdir, include_quote_only=False,
                       tier_filter=None, stage_filter=None)
            for e in entries
        ]
        # fake-html: license MIT, status pending → fetch
        if plans[0].decision != "fetch":
            failures.append(f"plan fake-html: expected fetch, got {plans[0].decision} ({plans[0].skip_reason})")
        # fake-text: license CC-BY-4.0, status pending → fetch
        if plans[1].decision != "fetch":
            failures.append(f"plan fake-text: expected fetch, got {plans[1].decision} ({plans[1].skip_reason})")
        # fake-blocked: status blocked-by-license → skip
        if plans[2].decision != "skip":
            failures.append(f"plan fake-blocked: expected skip, got {plans[2].decision}")

        # --include-quote-only relaxes QUOTE-ONLY only when status is not
        # already blocked-by-license — here the blocked status wins.
        plan_relaxed = plan_entry(
            entries[2], cdir, include_quote_only=True,
            tier_filter=None, stage_filter=None,
        )
        if plan_relaxed.decision != "skip":
            failures.append("plan fake-blocked: blocked-by-license must always skip")

        # 5. Attribution side-effect for CC-BY-*.
        ensure_dir(entries[1].corpus_path(cdir))
        write_attribution(entries[1], entries[1].corpus_path(cdir))
        attr_path = entries[1].corpus_path(cdir) / "LICENSE.attribution"
        if not attr_path.is_file():
            failures.append("write_attribution: CC-BY-4.0 file not written")
        elif "anon" not in attr_path.read_text(encoding="utf-8"):
            failures.append("write_attribution: payload missing")

        # 6. tier/stage filter.
        plan_filtered = plan_entry(
            entries[0], cdir, include_quote_only=False,
            tier_filter="B", stage_filter=None,
        )
        if plan_filtered.decision != "skip" or "tier" not in plan_filtered.skip_reason:
            failures.append(f"plan tier-filter: expected skip-tier, got {plan_filtered}")

    # 7. parse_retry_after.
    if parse_retry_after("30") != 30.0:
        failures.append("parse_retry_after: numeric value")
    if parse_retry_after("") is not None:
        failures.append("parse_retry_after: empty should be None")

    # 8. End-to-end run with dry_run=True (no network).
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man = root / "datasets.toml"
        atomic_write_text(man, _SAMPLE_MANIFEST)
        stats = run(
            manifest_path=man,
            corpus_dir=root / "corpus",
            logs_dir=root / "logs",
            tier_filter="all",
            stage_filter="all",
            include_quote_only=False,
            max_bytes=DEFAULT_MAX_BYTES,
            rate_host=0.0,  # no waits
            dry_run=True,
            update_manifest=False,
        )
        if stats.planned != 3:
            failures.append(f"run: planned={stats.planned}, expected 3")
        if stats.fetched != 0:
            failures.append("run: dry-run should not fetch")
        # 1 entry is blocked-by-license -> skipped; other two are dry-run
        # (counted as planned but not skipped).
        if stats.skipped != 1:
            failures.append(f"run: expected 1 skip, got {stats.skipped}")
        log_path = root / "logs" / f"fetch_sources.{today_iso()}.jsonl"
        if not log_path.is_file():
            failures.append("run: log file missing")

    if failures:
        print("fetch_sources.py SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("fetch_sources.py SELFTEST PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_cli())
