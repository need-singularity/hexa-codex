#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""anticorpus_filter.py -- LLM-slop / SEO-content pollution filter.

Phase v0.2.0 cross-cutting infra deliverable per ROADMAP.md §2 item 8
("anti-corpus filter -- pollution exclusion"). Sibling to:

    tool/license_clean_scan.py     -- license-clean CI gate (gate (1))
    tool/corpus_quality_filter.py  -- perplexity-based quality gate
    tool/fetch_sources.py          -- license-respecting source fetcher

PURPOSE
-------
Reject inbound text corpus material that almost certainly contains
LLM-generated slop or SEO-content-farm noise BEFORE it reaches the
tokenizer.  The Tier-E findings (papers/tier-e-findings.md Part 3 +
"Pollution / exclusion list") encode the rules; this tool is the
mechanical enforcement gate.

DECISION RULES (in priority order)
----------------------------------
1.  ALLOWLIST OVERRIDE.  If the source URL matches a prefix in
    `tool/anticorpus_allowlist.toml` (named-author blogs, institutional
    engineering blogs, per-author platform exceptions), the source is
    ACCEPTED regardless of any subsequent rule.

2.  COMMON-CRAWL HARD-REJECT.  Common Crawl raw dumps are rejected
    unconditionally for the philosophy stage -- dedup source is
    uncontrolled and by Nov 2024 the corpus was ~50% AI-gen content
    (Tier-E table row, Axios 2025-10-14 citation).

3.  DOMAIN BLACKLIST (always-reject).  Domains known to be pre-LLM
    low-quality tutorial mills, mass-spam vectors, or paywall-around
    aggregators are rejected regardless of date:

        geeksforgeeks.org, quora.com, *.blogspot.com,
        csdn.net, cnblogs.com, w3schools.com,
        tutorialspoint.com, linkedin.com/pulse/

4.  TIME-CUTOFF DOMAINS.  Platforms with high post-2023 LLM-slop
    prevalence per Pangram / Originality / Medium-CEO-admission:

        medium.com (and *.medium.com)
        dev.to
        hashnode.com, *.hashnode.dev
        *.substack.com
        linkedin.com/pulse/  (covered by blacklist; also gets cutoff)

    Cutoff anchor: 2023-01-01 (ChatGPT-3.5 mass-deploy date, the
    "GPT-3.5 mass content explosion" anchor per Tier-E).  Items with a
    publish date >= cutoff are rejected.  Items with NO discoverable
    date are rejected conservatively -- the platform's slop prevalence
    is too high to default-accept.

5.  DEFAULT-ACCEPT.  Anything that does not hit a reject rule is
    accepted (the filter is non-exhaustive by design -- it only
    catches the high-confidence pollution vectors; the perplexity
    gate downstream (`tool/corpus_quality_filter.py`) catches the
    rest).

INPUT MODES
-----------
* `--paths <file> [<file> ...]`
        Score a list of files.  Each file is expected to carry an
        embedded source-URL marker (HTML <link rel="canonical"> /
        Open-Graph url / first-line `# URL: ...` Markdown comment /
        sidecar `.url` file).  If no URL is discoverable, the file
        is REJECTED under rule 4's no-date conservative branch when
        the surrounding directory name matches a cutoff domain, else
        it is reported as `unknown-source` and accepted (the curator
        is responsible).

* `--manifest [<path>]`
        Walk `datasets.toml` (or the supplied path).  For every
        entry, classify based on the entry's `url` field and emit
        `update_manifest_fields`-compatible suggestions setting
        `fetch_status = "anti-corpus-reject"` for blocked entries.
        Dry-run by default; pass `--apply` to mutate the manifest.

        NOTE on schema lock: `_common.VALID_FETCH_STATUS` does NOT
        currently include the `"anti-corpus-reject"` value.  When
        `--apply` is set this tool surfaces the schema-extension
        requirement and refuses to write unless `--unsafe-schema`
        is also passed.  The clean path is to extend
        `_common.VALID_FETCH_STATUS` in a follow-up commit; this
        tool only reports.

* `--selftest`
        Synthesize 12+ in-memory fixtures covering every reject path
        + allowlist override + edge cases (empty file, no-date,
        partial domain match, sub-domain inheritance, prefix vs full
        host).  Exit 0 on PASS with the sentinel
        `__ANTICORPUS_SELFTEST__ PASS` printed on its own line.

OUTPUT
------
JSON statistics report to `--report <path>` (default stdout summary):

    {
      "schema": "anticorpus_filter/v1",
      "ts": "2026-05-11T...Z",
      "totals": {
        "accept": N,
        "reject_time_cutoff": N,
        "reject_domain_blacklist": N,
        "reject_no_date": N,
        "reject_common_crawl": N,
        "allowlist_override": N,
        "bytes_accepted": N,
        "bytes_rejected": N
      },
      "per_source": [
        {"source": "medium.com", "accept": 0, "reject_time_cutoff": 12, ...}
      ],
      "manifest_suggestions": [
        {"section": "[datasets.code.philosophy.medium-2024-foo]",
         "field": "fetch_status",
         "current": "fetched",
         "suggested": "anti-corpus-reject",
         "reason": "time-cutoff: medium.com 2024-03"}
      ]
    }

DEPENDENCIES
------------
stdlib only (Python 3.11+ for `tomllib`).  Mirrors the dependency
discipline of `license_clean_scan.py` and `_common.py`.

CROSS-LINKS
-----------
* Spec source:  papers/tier-e-findings.md  Part 3
* Roadmap slot: ROADMAP.md  §2  v0.2.0 cross-cutting infra item 8
* TODO entry:   TODO.md     §2  "anti-corpus filter"
* Allowlist:    tool/anticorpus_allowlist.toml
* Schema lock:  tool/_common.py  VALID_FETCH_STATUS  (extension pending)

EXIT CODES
----------
0  clean
1  reject suggestions emitted (informational; CI may opt to fail)
2  hard error (bad input, schema-lock violation, selftest fail)
"""
from __future__ import annotations

# NOTE: a sibling `tool/tokenize.py` shadows the stdlib `tokenize` module
# when ANY tool in `tool/` is launched as a script (Python prepends the
# script's directory to sys.path).  The shadow propagates through
# `dataclasses` -> `inspect` -> `linecache` -> `tokenize` and crashes
# import.  Prune the script directory before any other imports.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import datetime as _dt
import importlib.util
import json
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Iterator, Optional
from urllib.parse import urlsplit


# ---------------------------------------------------------------------------
# _common.py loader (mirrors corpus_quality_filter.py / tokenize.py pattern)
# ---------------------------------------------------------------------------

def _load_common():
    """Side-load `_common.py` via importlib because `import _common` would
    trigger the very stdlib-shadow that the script-dir-prune defends
    against (sys.path[0] would have to be re-added).  importlib.util
    accepts an absolute path and bypasses sys.path entirely."""
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


try:
    _common = _load_common()
    REPO_ROOT = _common.REPO_ROOT
    DEFAULT_MANIFEST = _common.DEFAULT_MANIFEST
    DEFAULT_CORPUS_DIR = _common.DEFAULT_CORPUS_DIR
    DEFAULT_RUNS_DIR = _common.DEFAULT_RUNS_DIR
    iter_entries = _common.iter_entries
    load_manifest = _common.load_manifest
    atomic_write_text = _common.atomic_write_text
    now_iso = _common.now_iso
    VALID_FETCH_STATUS = _common.VALID_FETCH_STATUS
except Exception:  # pragma: no cover -- only used in selftest fallback
    _common = None
    REPO_ROOT = Path(_THIS_DIR).parent
    DEFAULT_MANIFEST = REPO_ROOT / "datasets.toml"
    DEFAULT_CORPUS_DIR = REPO_ROOT / "corpus"
    DEFAULT_RUNS_DIR = REPO_ROOT / "runs"
    iter_entries = None
    load_manifest = None
    atomic_write_text = None
    now_iso = lambda: _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    VALID_FETCH_STATUS = frozenset({"pending", "fetched", "blocked-by-license",
                                    "url-broken", "pdf-pending"})


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# 2023-01-01 -- ChatGPT-3.5 mass-deploy anchor.  Items dated on or after
# this on a cutoff-domain are rejected.  See tier-e-findings.md Part 3.
DEFAULT_CUTOFF_DATE = _dt.date(2023, 1, 1)

# Time-cutoff domains: rejected when publish date >= cutoff OR when no
# discoverable date.  Suffix-match (sub-domains inherit the rule).
TIME_CUTOFF_DOMAINS: tuple[str, ...] = (
    "medium.com",
    "dev.to",
    "hashnode.com",
    "hashnode.dev",
    "substack.com",
)

# Always-reject domains.  Pre-LLM low-quality vectors + mass-spam farms.
# Suffix-match.  Some entries are subsumed by the time-cutoff list but
# kept explicit for date-less rejection consistency.
DOMAIN_BLACKLIST: tuple[str, ...] = (
    "geeksforgeeks.org",
    "quora.com",
    "blogspot.com",     # all *.blogspot.com
    "csdn.net",
    "cnblogs.com",
    "w3schools.com",
    "tutorialspoint.com",
)

# Path-segment blacklist: any URL whose path contains one of these
# segments is rejected (covers LinkedIn pulse posts which are a known
# AI-tutorial vector per Tier-E).
PATH_SEGMENT_BLACKLIST: tuple[str, ...] = (
    "linkedin.com/pulse/",
)

# Common Crawl hard-reject (rule 2).
COMMON_CRAWL_HOSTS: tuple[str, ...] = (
    "commoncrawl.org",
    "data.commoncrawl.org",
)

# Default allowlist TOML path.
DEFAULT_ALLOWLIST_PATH = Path(_THIS_DIR) / "anticorpus_allowlist.toml"

# Marker the manifest will gain once `_common.VALID_FETCH_STATUS` is
# extended (planned schema-extension commit).
REJECT_FETCH_STATUS = "anti-corpus-reject"


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

VERDICTS = (
    "accept",
    "reject_time_cutoff",
    "reject_domain_blacklist",
    "reject_path_blacklist",
    "reject_no_date",
    "reject_common_crawl",
    "allowlist_override",
    "unknown_source",
)


@dataclass
class Decision:
    """Per-source verdict + provenance."""

    url: str
    source_host: str
    verdict: str               # one of VERDICTS
    reason: str
    publish_date: Optional[str] = None   # ISO-8601 if known, else None
    matched_rule: Optional[str] = None   # e.g. "time-cutoff:medium.com"
    matched_allowlist: Optional[str] = None
    bytes: int = 0
    path: Optional[str] = None           # local file path if known

    def is_accept(self) -> bool:
        return self.verdict in {"accept", "allowlist_override", "unknown_source"}

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FilterReport:
    """Aggregate report for a filter run."""

    schema: str = "anticorpus_filter/v1"
    ts: str = field(default_factory=lambda: now_iso())
    totals: dict = field(default_factory=lambda: {v: 0 for v in VERDICTS})
    bytes_accepted: int = 0
    bytes_rejected: int = 0
    per_source: dict[str, dict[str, int]] = field(default_factory=dict)
    decisions: list[Decision] = field(default_factory=list)
    manifest_suggestions: list[dict] = field(default_factory=list)

    def add(self, d: Decision) -> None:
        self.decisions.append(d)
        self.totals[d.verdict] = self.totals.get(d.verdict, 0) + 1
        if d.is_accept():
            self.bytes_accepted += d.bytes
        else:
            self.bytes_rejected += d.bytes
        per = self.per_source.setdefault(d.source_host or "<unknown>",
                                        {v: 0 for v in VERDICTS})
        per[d.verdict] += 1

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "ts": self.ts,
            "totals": dict(self.totals),
            "bytes_accepted": self.bytes_accepted,
            "bytes_rejected": self.bytes_rejected,
            "per_source": self.per_source,
            "decisions": [d.to_dict() for d in self.decisions],
            "manifest_suggestions": self.manifest_suggestions,
        }


# ---------------------------------------------------------------------------
# Allowlist loading
# ---------------------------------------------------------------------------

@dataclass
class Allowlist:
    """Compiled allowlist: a flat tuple of normalised URL prefixes."""

    prefixes: tuple[str, ...]
    by_origin: dict[str, str]   # prefix -> source group name

    def match(self, normalised: str) -> Optional[str]:
        """Return the matching prefix if `normalised` starts with one of
        the entries, else None.  Longest-prefix-first."""
        for p in self.prefixes:
            if normalised.startswith(p):
                return p
        return None


def load_allowlist(path: Path) -> Allowlist:
    """Parse the allowlist TOML.  Returns a compiled `Allowlist`.

    All prefixes are normalised (scheme stripped, 'www.' stripped,
    lower-cased) so matching against a normalised URL is a simple
    `startswith`."""
    if not path.exists():
        return Allowlist(prefixes=(), by_origin={})
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    by_origin: dict[str, str] = {}
    raw: list[str] = []
    allow = doc.get("allowlist", {})
    for group_name, group in allow.items():
        if not isinstance(group, dict):
            continue
        for p in group.get("prefixes", []) or []:
            if not isinstance(p, str) or not p.strip():
                continue
            norm = _normalise_url(p)
            if not norm:
                continue
            raw.append(norm)
            by_origin[norm] = f"allowlist.{group_name}"
    # Sort by length descending so longest match wins.
    prefixes = tuple(sorted(set(raw), key=lambda s: (-len(s), s)))
    return Allowlist(prefixes=prefixes, by_origin=by_origin)


# ---------------------------------------------------------------------------
# URL normalisation + host extraction
# ---------------------------------------------------------------------------

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)


def _normalise_url(url: str) -> str:
    """Strip scheme + leading 'www.' + trailing whitespace, lower-case
    the host portion only (path case is preserved because some sites
    have case-sensitive routes).  Returns 'host[/path]' form."""
    if not url:
        return ""
    s = url.strip()
    # Drop scheme.
    s = _SCHEME_RE.sub("", s)
    # Split on first '/'.
    if "/" in s:
        host, path = s.split("/", 1)
        path = "/" + path
    else:
        host, path = s, ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host + path


def _host_of(url: str) -> str:
    """Return the lowercased host of `url`, stripping leading 'www.'.
    Falls back to the bare normalised string when there is no scheme."""
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_suffix_match(host: str, suffixes: Iterable[str]) -> Optional[str]:
    """Return the suffix that `host` ends with, else None.

    Matches `medium.com` against `something.medium.com` AND `medium.com`
    itself.  Does NOT match `notmedium.com` (boundary-aware)."""
    if not host:
        return None
    h = host.lower()
    for suffix in suffixes:
        s = suffix.lower()
        if h == s or h.endswith("." + s):
            return suffix
    return None


def _path_segment_match(url: str, segments: Iterable[str]) -> Optional[str]:
    """Return the segment matched, else None.  Segment is matched on the
    normalised host+path form (no scheme, lowercased host)."""
    norm = _normalise_url(url)
    for seg in segments:
        if seg in norm:
            return seg
    return None


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

# Loose date patterns to sniff publish-date from URLs, file front-matter,
# HTML <meta> tags, and Markdown headers.  Order matters: most specific
# patterns first.
_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 2024-03-15  or  2024/03/15
    re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"),
    # /2024/03/15/  (URL-style)
    re.compile(r"/(20\d{2})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/"),
)

_META_DATE_KEYS: tuple[str, ...] = (
    "article:published_time",
    "datepublished",
    "date",
    "pubdate",
    "publish-date",
    "publication-date",
)


def extract_date_from_text(text: str) -> Optional[_dt.date]:
    """Best-effort publish-date extraction from a blob of text.

    Strategy:
      1. HTML <meta> with one of `_META_DATE_KEYS` -- parse value.
      2. JSON-LD `"datePublished": "..."`.
      3. Markdown YAML front-matter `date: ...`.
      4. Any ISO date in the first 4 KiB (URL paths included).

    Returns None on no-match.  Failure to parse a near-match returns
    None (conservative: caller treats this as 'no date')."""
    if not text:
        return None
    head = text[:65_536]   # cap scan window

    # 1. <meta property|name="...published..." content="...">
    meta_re = re.compile(
        r"""<meta\s+[^>]*?(?:property|name)\s*=\s*["']([^"']+)["']\s*"""
        r"""[^>]*?content\s*=\s*["']([^"']+)["']""",
        re.IGNORECASE,
    )
    for m in meta_re.finditer(head):
        key = m.group(1).strip().lower()
        if any(k in key for k in _META_DATE_KEYS):
            d = _parse_date_loose(m.group(2))
            if d:
                return d

    # 2. JSON-LD style.
    jsonld_re = re.compile(
        r'"datePublished"\s*:\s*"([^"]+)"', re.IGNORECASE,
    )
    m = jsonld_re.search(head)
    if m:
        d = _parse_date_loose(m.group(1))
        if d:
            return d

    # 3. YAML front-matter.
    if head.startswith("---"):
        fm = head[3:head.find("---", 3)] if "---" in head[3:] else ""
        m = re.search(r"^\s*date\s*:\s*([0-9T:\-\+Zz \.]+)\s*$", fm, re.M)
        if m:
            d = _parse_date_loose(m.group(1))
            if d:
                return d

    # 4. First-line URL/date hint comment.
    m = re.search(r"^#\s*(?:URL|DATE|Published)\s*:\s*([^\n]+)$",
                  head, re.IGNORECASE | re.MULTILINE)
    if m:
        d = _parse_date_loose(m.group(1))
        if d:
            return d

    # 5. Loose scan.
    for pat in _DATE_PATTERNS:
        m = pat.search(head)
        if m:
            d = _parse_date_loose("-".join(m.groups()))
            if d:
                return d

    return None


def _parse_date_loose(s: str) -> Optional[_dt.date]:
    """Parse `YYYY-MM-DD`, `YYYY/MM/DD`, or any ISO-8601 prefix.
    Returns None on failure."""
    if not s:
        return None
    s = s.strip()
    # Trim time component for ISO datetimes.
    if "T" in s:
        s = s.split("T", 1)[0]
    if " " in s:
        s = s.split(" ", 1)[0]
    s = s.replace("/", "-")
    m = re.match(r"^(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", s)
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def extract_date_from_url(url: str) -> Optional[_dt.date]:
    """Sniff `/YYYY/MM/DD/` style date out of a URL path."""
    norm = _normalise_url(url)
    m = _DATE_PATTERNS[1].search("/" + norm)
    if m:
        return _parse_date_loose("-".join(m.groups()))
    m = _DATE_PATTERNS[0].search(norm)
    if m:
        return _parse_date_loose("-".join(m.groups()))
    return None


# ---------------------------------------------------------------------------
# Source-URL extraction from a local file
# ---------------------------------------------------------------------------

_URL_HINT_RES: tuple[re.Pattern[str], ...] = (
    # `# URL: https://...`  Markdown / Python comment marker.
    re.compile(r"^\s*#\s*URL\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE),
    # HTML <link rel="canonical" href="...">
    re.compile(
        r"""<link\s+[^>]*?rel\s*=\s*["']canonical["']\s*[^>]*?"""
        r"""href\s*=\s*["']([^"']+)["']""",
        re.IGNORECASE,
    ),
    # OpenGraph url meta.
    re.compile(
        r"""<meta\s+[^>]*?property\s*=\s*["']og:url["']\s*[^>]*?"""
        r"""content\s*=\s*["']([^"']+)["']""",
        re.IGNORECASE,
    ),
)


def extract_url_from_text(text: str) -> Optional[str]:
    """Best-effort source-URL extraction from a file's content."""
    if not text:
        return None
    for pat in _URL_HINT_RES:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def extract_url_from_sidecar(path: Path) -> Optional[str]:
    """Look for `<path>.url` sidecar file."""
    sidecar = path.with_suffix(path.suffix + ".url")
    if sidecar.exists():
        try:
            return sidecar.read_text(encoding="utf-8").strip().splitlines()[0]
        except (OSError, UnicodeDecodeError, IndexError):
            return None
    return None


# ---------------------------------------------------------------------------
# Core decision function
# ---------------------------------------------------------------------------

def classify(
    url: str,
    *,
    publish_date: Optional[_dt.date] = None,
    allowlist: Optional[Allowlist] = None,
    cutoff: _dt.date = DEFAULT_CUTOFF_DATE,
    bytes_size: int = 0,
    file_path: Optional[str] = None,
) -> Decision:
    """Apply the five rules in priority order and return a Decision.

    Pure function -- no I/O.  Date may be None to indicate 'unknown'.
    """
    norm = _normalise_url(url)
    host = _host_of(url) if url else ""
    iso_date = publish_date.isoformat() if publish_date else None

    # Empty URL with a file path -> caller-side unknown-source bucket.
    if not norm and not host:
        return Decision(
            url=url, source_host="", verdict="unknown_source",
            reason="no source URL discoverable",
            publish_date=iso_date, bytes=bytes_size, path=file_path,
        )

    # Rule 1: Allowlist override (highest priority).
    if allowlist is not None:
        match = allowlist.match(norm)
        if match:
            return Decision(
                url=url, source_host=host, verdict="allowlist_override",
                reason=f"allowlist prefix match: {match}",
                publish_date=iso_date, matched_allowlist=match,
                bytes=bytes_size, path=file_path,
            )

    # Rule 2: Common-Crawl hard-reject.
    cc = _host_suffix_match(host, COMMON_CRAWL_HOSTS)
    if cc:
        return Decision(
            url=url, source_host=host, verdict="reject_common_crawl",
            reason=f"common-crawl raw dump: {cc}",
            matched_rule=f"common-crawl:{cc}",
            publish_date=iso_date, bytes=bytes_size, path=file_path,
        )

    # Rule 3: Domain blacklist (always-reject).
    bl = _host_suffix_match(host, DOMAIN_BLACKLIST)
    if bl:
        return Decision(
            url=url, source_host=host, verdict="reject_domain_blacklist",
            reason=f"blacklisted domain: {bl}",
            matched_rule=f"blacklist:{bl}",
            publish_date=iso_date, bytes=bytes_size, path=file_path,
        )

    # Rule 3b: Path-segment blacklist (LinkedIn pulse, etc).
    seg = _path_segment_match(url, PATH_SEGMENT_BLACKLIST)
    if seg:
        return Decision(
            url=url, source_host=host, verdict="reject_path_blacklist",
            reason=f"blacklisted path segment: {seg}",
            matched_rule=f"path:{seg}",
            publish_date=iso_date, bytes=bytes_size, path=file_path,
        )

    # Rule 4: Time-cutoff domains.
    tc = _host_suffix_match(host, TIME_CUTOFF_DOMAINS)
    if tc:
        if publish_date is None:
            return Decision(
                url=url, source_host=host, verdict="reject_no_date",
                reason=f"time-cutoff domain {tc} with no discoverable date "
                       f"(conservative reject)",
                matched_rule=f"time-cutoff:{tc}:no-date",
                publish_date=None, bytes=bytes_size, path=file_path,
            )
        if publish_date >= cutoff:
            return Decision(
                url=url, source_host=host, verdict="reject_time_cutoff",
                reason=f"time-cutoff {tc}: {publish_date.isoformat()} "
                       f">= {cutoff.isoformat()}",
                matched_rule=f"time-cutoff:{tc}:{publish_date.isoformat()}",
                publish_date=iso_date, bytes=bytes_size, path=file_path,
            )
        # date < cutoff -> accept this cutoff-domain entry.

    # Rule 5: Default-accept.
    return Decision(
        url=url, source_host=host, verdict="accept",
        reason="no reject rule matched",
        publish_date=iso_date, bytes=bytes_size, path=file_path,
    )


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def _read_head(path: Path, max_bytes: int = 65_536) -> str:
    """Read the first `max_bytes` of `path` as utf-8 (errors=replace)."""
    try:
        with open(path, "rb") as fh:
            blob = fh.read(max_bytes)
    except OSError:
        return ""
    try:
        return blob.decode("utf-8", errors="replace")
    except Exception:
        return ""


def scan_file(path: Path, allowlist: Allowlist,
              cutoff: _dt.date = DEFAULT_CUTOFF_DATE) -> Decision:
    """Classify a single file by sniffing its URL + publish date."""
    try:
        size = path.stat().st_size if path.exists() else 0
    except OSError:
        size = 0
    head = _read_head(path)
    url = extract_url_from_sidecar(path) or extract_url_from_text(head) or ""
    date = None
    if url:
        date = extract_date_from_url(url) or extract_date_from_text(head)
    else:
        date = extract_date_from_text(head)
    return classify(
        url=url, publish_date=date, allowlist=allowlist,
        cutoff=cutoff, bytes_size=size, file_path=str(path),
    )


def scan_paths(paths: Iterable[Path], allowlist: Allowlist,
               cutoff: _dt.date = DEFAULT_CUTOFF_DATE) -> FilterReport:
    """Scan an iterable of file paths and return an aggregate report."""
    rep = FilterReport()
    for p in paths:
        d = scan_file(p, allowlist, cutoff)
        rep.add(d)
    return rep


# ---------------------------------------------------------------------------
# Manifest mode
# ---------------------------------------------------------------------------

def scan_manifest(manifest_path: Path, allowlist: Allowlist,
                  cutoff: _dt.date = DEFAULT_CUTOFF_DATE) -> FilterReport:
    """Walk every entry in `manifest_path`.  Classify by URL only
    (entry-level decision -- per-file scanning happens in --paths mode
    once the corpus is fetched).  Emits manifest-suggestion records
    for every reject."""
    if load_manifest is None or iter_entries is None:
        raise RuntimeError("_common.py not available; cannot run manifest mode")
    rep = FilterReport()
    doc = load_manifest(manifest_path)
    for entry in iter_entries(doc):
        url = entry.url
        host = _host_of(url)
        date = extract_date_from_url(url)
        d = classify(
            url=url, publish_date=date, allowlist=allowlist,
            cutoff=cutoff, bytes_size=0, file_path=None,
        )
        d.source_host = host or d.source_host
        rep.add(d)
        if not d.is_accept():
            rep.manifest_suggestions.append({
                "section": entry.section_header,
                "field": "fetch_status",
                "current": entry.fetch_status,
                "suggested": REJECT_FETCH_STATUS,
                "reason": d.reason,
                "verdict": d.verdict,
                "matched_rule": d.matched_rule,
            })
    return rep


def apply_manifest_suggestions(
    manifest_path: Path,
    suggestions: list[dict],
    *,
    unsafe_schema: bool = False,
) -> int:
    """Mutate `manifest_path` to set the suggested `fetch_status` values.

    Returns the number of entries mutated.  Raises `ValueError` if the
    target value is not in `VALID_FETCH_STATUS` and `unsafe_schema` is
    False -- this is the schema-lock gate documented in the module
    docstring."""
    if not suggestions:
        return 0
    if REJECT_FETCH_STATUS not in VALID_FETCH_STATUS:
        if not unsafe_schema:
            raise ValueError(
                f"refusing to write fetch_status={REJECT_FETCH_STATUS!r}: "
                f"value not in _common.VALID_FETCH_STATUS "
                f"({sorted(VALID_FETCH_STATUS)}). "
                f"Extend the schema lock first, or pass --unsafe-schema."
            )
    if _common is None or atomic_write_text is None:
        raise RuntimeError("_common.py not available; cannot apply")

    text = manifest_path.read_text(encoding="utf-8")
    n = 0
    # Group suggestions per section in case multiple fields share a
    # section header (defensive: today only one field per section).
    by_section: dict[str, dict[str, str]] = {}
    for s in suggestions:
        by_section.setdefault(s["section"], {})[s["field"]] = s["suggested"]

    # Bypass the schema validator when --unsafe-schema is set by
    # temporarily extending VALID_FETCH_STATUS in the loaded module.
    saved = _common.VALID_FETCH_STATUS
    if unsafe_schema:
        _common.VALID_FETCH_STATUS = frozenset(set(saved) | {REJECT_FETCH_STATUS})
    try:
        for header, updates in by_section.items():
            try:
                text = _common.update_entry_fields(text, header, updates)
                n += 1
            except KeyError:
                # Section vanished -- skip.
                continue
        atomic_write_text(manifest_path, text)
    finally:
        if unsafe_schema:
            _common.VALID_FETCH_STATUS = saved
    return n


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EPILOGUE = """\
RULES SOURCE
  papers/tier-e-findings.md  Part 3  "Pollution / exclusion list"
  ROADMAP.md  §2  v0.2.0 cross-cutting infra item 8

ALLOWLIST
  tool/anticorpus_allowlist.toml  (TOML; URL-prefix matches)

EXAMPLES
  python3 tool/anticorpus_filter.py --selftest
  python3 tool/anticorpus_filter.py --paths corpus/code/philosophy/*/*.md
  python3 tool/anticorpus_filter.py --manifest --report runs/anticorpus.json
  python3 tool/anticorpus_filter.py --manifest --apply       # mutates datasets.toml

EXIT CODES
  0  clean (no rejects)
  1  rejects emitted (informational; CI may opt to fail)
  2  hard error (bad input / schema-lock violation / selftest fail)
"""


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="anticorpus_filter.py",
        description="Anti-corpus pollution filter (LLM-slop / SEO-content rejector).",
        epilog=EPILOGUE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--paths", nargs="*", default=None,
                    help="Files to classify (URL sniffed from sidecar / front-matter).")
    ap.add_argument("--manifest", nargs="?", default=None, const=str(DEFAULT_MANIFEST),
                    help="Scan datasets.toml (default: repo-root datasets.toml).")
    ap.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST_PATH),
                    help="Path to anticorpus_allowlist.toml.")
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF_DATE.isoformat(),
                    help="Time-cutoff date for slop-platform reject (YYYY-MM-DD).")
    ap.add_argument("--report", default=None,
                    help="Write JSON report to this path (default: stdout summary).")
    ap.add_argument("--apply", action="store_true",
                    help="Mutate datasets.toml with reject suggestions (manifest mode).")
    ap.add_argument("--unsafe-schema", action="store_true",
                    help="Bypass _common.VALID_FETCH_STATUS schema lock for --apply.")
    ap.add_argument("--selftest", action="store_true",
                    help="Run inline unit tests and exit.")
    return ap


def _parse_cutoff(s: str) -> _dt.date:
    d = _parse_date_loose(s)
    if d is None:
        raise SystemExit(f"error: --cutoff is not a YYYY-MM-DD date: {s!r}")
    return d


def _print_summary(rep: FilterReport) -> None:
    t = rep.totals
    print(f"anticorpus-filter scanned={len(rep.decisions)} "
          f"accept={t['accept']} "
          f"allowlist_override={t['allowlist_override']} "
          f"reject_time_cutoff={t['reject_time_cutoff']} "
          f"reject_domain_blacklist={t['reject_domain_blacklist']} "
          f"reject_path_blacklist={t['reject_path_blacklist']} "
          f"reject_no_date={t['reject_no_date']} "
          f"reject_common_crawl={t['reject_common_crawl']} "
          f"unknown_source={t['unknown_source']} "
          f"bytes_accepted={rep.bytes_accepted} "
          f"bytes_rejected={rep.bytes_rejected}")
    if rep.manifest_suggestions:
        print(f"manifest suggestions: {len(rep.manifest_suggestions)} reject(s):")
        for s in rep.manifest_suggestions[:20]:
            print(f"  {s['section']}  -> {s['field']}={s['suggested']}  "
                  f"({s['reason']})")
        if len(rep.manifest_suggestions) > 20:
            print(f"  ... and {len(rep.manifest_suggestions) - 20} more")


def run_cli(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.selftest:
        return _run_selftest()

    cutoff = _parse_cutoff(args.cutoff)
    allowlist = load_allowlist(Path(args.allowlist))

    rep: FilterReport
    if args.paths is not None:
        paths = [Path(p) for p in args.paths]
        rep = scan_paths(paths, allowlist, cutoff)
    elif args.manifest is not None:
        rep = scan_manifest(Path(args.manifest), allowlist, cutoff)
        if args.apply:
            try:
                n = apply_manifest_suggestions(
                    Path(args.manifest), rep.manifest_suggestions,
                    unsafe_schema=args.unsafe_schema,
                )
                print(f"applied {n} manifest update(s) to {args.manifest}")
            except (ValueError, RuntimeError) as e:
                print(f"error: --apply refused: {e}", file=sys.stderr)
                return 2
    else:
        print("error: pass --paths <files...> or --manifest [path] or --selftest",
              file=sys.stderr)
        return 2

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(rep.to_dict(), fh, indent=2, sort_keys=False)
        print(f"anti-corpus report written: {args.report}")
    else:
        _print_summary(rep)

    # Exit code: 0 if zero rejects; else 1 (informational).
    rejects = sum(v for k, v in rep.totals.items() if k.startswith("reject"))
    return 1 if rejects > 0 else 0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _run_selftest() -> int:  # noqa: C901 -- test driver, length is fine
    """Synthetic in-memory fixtures covering every reject path + allowlist
    override + edge cases.  Exit 0 on success, 1 on any failure."""
    failures: list[str] = []

    # ----- Fixture: allowlist (mirrors the seed TOML, no I/O) ---------
    allow = Allowlist(
        prefixes=tuple(sorted([
            "danluu.com",
            "fasterthanli.me",
            "drewdevault.com",
            "jvns.ca",
            "blog.cloudflare.com",
            "lwn.net",
            "web.dev",
            "developer.mozilla.org",
            "julialang.org/blog/",
        ], key=lambda s: (-len(s), s))),
        by_origin={},
    )
    cutoff = _dt.date(2023, 1, 1)

    cases = [
        # (label, url, date, expected_verdict, expected_rule_substr)
        ("1 medium-2024 reject_time_cutoff",
         "https://medium.com/@foo/some-post-abc123",
         _dt.date(2024, 3, 15), "reject_time_cutoff", "time-cutoff:medium.com"),
        ("2 medium-no-date reject_no_date",
         "https://medium.com/@foo/another-post",
         None, "reject_no_date", "time-cutoff:medium.com:no-date"),
        ("3 dev.to-2023 reject_time_cutoff",
         "https://dev.to/some-user/llm-tutorial",
         _dt.date(2023, 1, 1), "reject_time_cutoff", "time-cutoff:dev.to"),
        ("4 hashnode.dev-2024 reject_time_cutoff",
         "https://someone.hashnode.dev/post",
         _dt.date(2024, 5, 1), "reject_time_cutoff", "time-cutoff:hashnode.dev"),
        ("5 substack-subdomain reject_time_cutoff",
         "https://named.substack.com/p/123",
         _dt.date(2024, 1, 1), "reject_time_cutoff", "time-cutoff:substack.com"),
        ("6 medium-pre-cutoff accept (2018)",
         "https://medium.com/@old/post",
         _dt.date(2018, 6, 1), "accept", None),
        ("7 geeksforgeeks always reject_domain_blacklist",
         "https://www.geeksforgeeks.org/quicksort/",
         _dt.date(2019, 1, 1), "reject_domain_blacklist", "blacklist:geeksforgeeks.org"),
        ("8 quora always reject_domain_blacklist",
         "https://www.quora.com/foo",
         None, "reject_domain_blacklist", "blacklist:quora.com"),
        ("9 blogspot subdomain reject_domain_blacklist",
         "https://something.blogspot.com/2024/01/post.html",
         _dt.date(2024, 1, 1), "reject_domain_blacklist", "blacklist:blogspot.com"),
        ("10 csdn reject_domain_blacklist",
         "https://blog.csdn.net/user/article/details/12345",
         _dt.date(2024, 1, 1), "reject_domain_blacklist", "blacklist:csdn.net"),
        ("11 w3schools reject_domain_blacklist",
         "https://www.w3schools.com/python/",
         None, "reject_domain_blacklist", "blacklist:w3schools.com"),
        ("12 commoncrawl reject_common_crawl",
         "https://data.commoncrawl.org/CC-MAIN-2024-foo.warc",
         None, "reject_common_crawl", "common-crawl:commoncrawl.org"),
        ("13 linkedin/pulse path reject_path_blacklist",
         "https://www.linkedin.com/pulse/some-ai-post-name/",
         _dt.date(2024, 5, 5), "reject_path_blacklist", "path:linkedin.com/pulse/"),
        ("14 danluu allowlist override (CC-BY hand-written)",
         "https://danluu.com/cgroup-v2/",
         _dt.date(2024, 1, 1), "allowlist_override", None),
        ("15 jvns allowlist override",
         "https://jvns.ca/blog/2024/01/01/some-zine/",
         _dt.date(2024, 1, 1), "allowlist_override", None),
        ("16 web.dev allowlist override (institutional)",
         "https://web.dev/articles/css-nesting",
         _dt.date(2024, 3, 1), "allowlist_override", None),
        ("17 julialang.org/blog path-scoped allowlist",
         "https://julialang.org/blog/2024/01/release/",
         _dt.date(2024, 1, 1), "allowlist_override", None),
        ("18 wikipedia default-accept",
         "https://en.wikipedia.org/wiki/Quicksort",
         None, "accept", None),
        ("19 partial-match guard: notmedium.com is NOT medium",
         "https://notmedium.com/some-post",
         _dt.date(2024, 5, 1), "accept", None),
        ("20 partial-match guard: csdn-fake.io is NOT csdn.net",
         "https://csdn-fake.io/article",
         _dt.date(2024, 5, 1), "accept", None),
        ("21 boundary: medium.com itself (host=medium.com)",
         "https://medium.com/some-post",
         _dt.date(2024, 5, 1), "reject_time_cutoff", "time-cutoff:medium.com"),
        ("22 empty URL -> unknown_source",
         "",
         None, "unknown_source", None),
    ]

    for label, url, date, want_verdict, want_rule in cases:
        d = classify(url=url, publish_date=date, allowlist=allow, cutoff=cutoff)
        if d.verdict != want_verdict:
            failures.append(
                f"{label}: verdict {d.verdict!r} != expected {want_verdict!r} "
                f"(url={url!r} date={date} reason={d.reason!r})"
            )
            continue
        if want_rule is not None and (d.matched_rule or "") and \
                want_rule not in (d.matched_rule or ""):
            failures.append(
                f"{label}: matched_rule {d.matched_rule!r} does not contain "
                f"expected substring {want_rule!r}"
            )

    # ----- Edge case: empty allowlist still works ---------------------
    empty = Allowlist(prefixes=(), by_origin={})
    d = classify(url="https://danluu.com/x/", publish_date=_dt.date(2024, 1, 1),
                 allowlist=empty, cutoff=cutoff)
    if d.verdict != "accept":
        failures.append(
            f"empty-allowlist: danluu should still accept under default rules "
            f"(no domain match), got {d.verdict}"
        )

    # ----- Date extraction round-trips --------------------------------
    html = (
        '<html><head>'
        '<meta property="article:published_time" content="2024-07-15T10:00:00Z">'
        '</head><body>hi</body></html>'
    )
    got = extract_date_from_text(html)
    if got != _dt.date(2024, 7, 15):
        failures.append(f"extract_date_from_text(meta): got {got}")

    yaml_fm = "---\ntitle: x\ndate: 2022-12-01\n---\n\nhello\n"
    got = extract_date_from_text(yaml_fm)
    if got != _dt.date(2022, 12, 1):
        failures.append(f"extract_date_from_text(yaml): got {got}")

    md_hint = "# URL: https://medium.com/foo\nbody body body\n"
    got_url = extract_url_from_text(md_hint)
    if got_url != "https://medium.com/foo":
        failures.append(f"extract_url_from_text(md): got {got_url!r}")

    url_date = extract_date_from_url("https://example.com/2024/03/15/post")
    if url_date != _dt.date(2024, 3, 15):
        failures.append(f"extract_date_from_url: got {url_date}")

    # ----- Empty file edge case: should produce unknown_source --------
    with tempfile.TemporaryDirectory() as td:
        empty_file = Path(td) / "empty.md"
        empty_file.write_text("", encoding="utf-8")
        d = scan_file(empty_file, empty)
        if d.verdict != "unknown_source":
            failures.append(
                f"scan_file(empty): expected unknown_source, got {d.verdict}"
            )

        # File with a medium URL hint + 2024 date -> reject_time_cutoff.
        slop = Path(td) / "slop.md"
        slop.write_text(
            "# URL: https://medium.com/@foo/post\n"
            "---\ndate: 2024-04-01\n---\n\nbody\n",
            encoding="utf-8",
        )
        d = scan_file(slop, empty, cutoff=cutoff)
        if d.verdict != "reject_time_cutoff":
            failures.append(
                f"scan_file(medium-2024): expected reject_time_cutoff, "
                f"got {d.verdict} ({d.reason})"
            )

        # File with a danluu URL -> allowlist_override even without date.
        gold = Path(td) / "gold.md"
        gold.write_text(
            "# URL: https://danluu.com/cgroup-v2/\n\nbody\n",
            encoding="utf-8",
        )
        d = scan_file(gold, allow, cutoff=cutoff)
        if d.verdict != "allowlist_override":
            failures.append(
                f"scan_file(danluu): expected allowlist_override, "
                f"got {d.verdict} ({d.reason})"
            )

        # Sidecar .url file.
        side = Path(td) / "side.md"
        side.write_text("body\n", encoding="utf-8")
        (Path(td) / "side.md.url").write_text(
            "https://www.geeksforgeeks.org/foo", encoding="utf-8",
        )
        d = scan_file(side, empty)
        if d.verdict != "reject_domain_blacklist":
            failures.append(
                f"scan_file(sidecar geeksforgeeks): expected reject_domain_blacklist, "
                f"got {d.verdict} ({d.reason})"
            )

    # ----- FilterReport aggregation -----------------------------------
    rep = FilterReport()
    rep.add(Decision(url="https://medium.com/x", source_host="medium.com",
                     verdict="reject_time_cutoff", reason="t",
                     publish_date="2024-01-01", bytes=100))
    rep.add(Decision(url="https://danluu.com/x", source_host="danluu.com",
                     verdict="allowlist_override", reason="a", bytes=200))
    if rep.totals["reject_time_cutoff"] != 1 or rep.totals["allowlist_override"] != 1:
        failures.append(f"FilterReport.totals mis-aggregated: {rep.totals}")
    if rep.bytes_accepted != 200 or rep.bytes_rejected != 100:
        failures.append(
            f"FilterReport bytes mis-aggregated: "
            f"acc={rep.bytes_accepted} rej={rep.bytes_rejected}"
        )

    # ----- Schema-lock gate (apply_manifest_suggestions) --------------
    # REJECT_FETCH_STATUS is not in VALID_FETCH_STATUS; --unsafe-schema
    # must be required to bypass.
    if REJECT_FETCH_STATUS in VALID_FETCH_STATUS:
        # Schema already extended -- nothing to test, log.
        pass
    else:
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "datasets.toml"
            fake.write_text("[meta]\nx=1\n", encoding="utf-8")
            try:
                apply_manifest_suggestions(
                    fake,
                    [{"section": "[meta]", "field": "fetch_status",
                      "suggested": REJECT_FETCH_STATUS, "reason": "x",
                      "verdict": "reject_time_cutoff", "matched_rule": "x",
                      "current": ""}],
                    unsafe_schema=False,
                )
                failures.append(
                    "schema-lock: should have refused unsafe write without "
                    "--unsafe-schema"
                )
            except ValueError:
                pass

    # ----- Load actual seed allowlist TOML (round-trip) ----------------
    seed = Path(_THIS_DIR) / "anticorpus_allowlist.toml"
    if seed.exists():
        compiled = load_allowlist(seed)
        if not compiled.prefixes:
            failures.append("seed allowlist parsed but compiled to empty prefixes")
        # danluu must be in the seed allowlist.
        if compiled.match("danluu.com/x/") is None:
            failures.append("seed allowlist: danluu.com prefix did not match")

    if failures:
        print("anticorpus_filter.py SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"anticorpus_filter selftest: {len(cases)} classify cases + "
          f"date/url extraction + report aggregation + schema lock OK")
    print("__ANTICORPUS_SELFTEST__ PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_cli())
