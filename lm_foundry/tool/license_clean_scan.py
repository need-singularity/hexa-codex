#!/usr/bin/env python3
"""
license_clean_scan.py — license-clean CI prototype for hexa-forge corpus audit.

Phase v0.1.2 deliverable per ROADMAP §1 / §4 (immediate next actions item 1).

PURPOSE
-------
Scan a directory tree (typically a fetched dataset shard, a docs subtree, or a
sampled Stack v2 / Tier A-E batch) and classify every leaf file by its license,
emit a JSON audit report, and fail CI if any non-permissive license is found.

The recipe SSOT (`docs/code-llm.md` §REQUIRES) restricts the pretrain mix to
"permissive-only (MIT / Apache / BSD / Unlicense / public domain)". This tool
is the mechanical enforcement gate behind v1.0.0 acceptance gate (1)
"license audit: zero GPL/AGPL/NC/SSPL in pretrain mix (CI green)".

LICENSE CATEGORIES
------------------
ALLOWLIST (full include, train-OK):
    MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0,
    PSF-2.0, PostgreSQL, SQLite (public domain), Zlib, BSL-1.0, MPL-2.0,
    Public Domain.

ATTRIBUTION-REQUIRED (train-OK but record attribution):
    CC-BY-3.0, CC-BY-4.0, CC-BY-SA-4.0.
    Note: CC-BY-SA-4.0 is permitted because the recipe outputs weights, not
    derived prose; attribution is still captured for downstream provenance.

DENY (blocked from pretrain; may be allowed as "quote-only" in a fenced subtree
when --quote-only-ok is passed):
    GPL-2.0, GPL-3.0, AGPL-3.0, LGPL-2.1, LGPL-3.0, GFDL-1.3,
    CC-BY-NC-*, CC-BY-NC-SA-*, CC-BY-NC-ND-*, CC-BY-ND-*,
    SSPL-1.0, Elastic-2.0, Commons-Clause, Confluent-Community,
    proprietary, EULA, and any custom "no LLM training" clauses.

DETECTION ORDER (first hit wins, per spec section 3)
----------------------------------------------------
1.  SPDX-License-Identifier header inside the file itself.
2.  Sibling/ancestor LICENSE / LICENSE.md / LICENSE.txt / COPYING content sniff.
3.  package.json   "license" field.
4.  Cargo.toml     [package] license = "...".
5.  pyproject.toml [project] license = "..." or license-expression.
6.  HTML/Markdown footer license string sniff (for fetched docs pages).
7.  UNKNOWN (warn unless --allow-unknown; fail under --strict).

EXIT CODES
----------
0  clean
1  warnings only (UNKNOWN, attribution-required without manifest)
2  failures (any denylisted license, or strict mode + warnings)
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
import datetime as _dt
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:  # Python 3.11+: stdlib tomllib
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - 3.10 and below
    try:
        import tomli as _tomllib  # type: ignore[import-not-found,no-redef]
    except ImportError:
        _tomllib = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# License taxonomy
# ---------------------------------------------------------------------------

ALLOWLIST: frozenset[str] = frozenset({
    "MIT", "MIT-0",
    "Apache-2.0", "Apache-1.1",
    "BSD-2-Clause", "BSD-3-Clause", "BSD-4-Clause",
    "ISC",
    "Unlicense",
    "CC0-1.0",
    "PSF-2.0", "Python-2.0",
    "PostgreSQL",
    "SQLite",
    "Zlib",
    "BSL-1.0", "Boost-1.0",
    "MPL-2.0",
    "Public-Domain",
})

ATTRIBUTION_REQUIRED: frozenset[str] = frozenset({
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
})

DENYLIST: frozenset[str] = frozenset({
    "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
    "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
    "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
    "LGPL-2.1", "LGPL-2.1-only", "LGPL-2.1-or-later",
    "LGPL-3.0", "LGPL-3.0-only", "LGPL-3.0-or-later",
    "GFDL-1.3", "GFDL-1.2", "GFDL-1.1",
    "CC-BY-NC-3.0", "CC-BY-NC-4.0",
    "CC-BY-NC-SA-3.0", "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-3.0", "CC-BY-NC-ND-4.0",
    "CC-BY-ND-3.0", "CC-BY-ND-4.0",
    "SSPL-1.0",
    "Elastic-2.0", "Elastic-1.0",
    "Commons-Clause",
    "Confluent-Community-1.0",
    "Proprietary", "EULA", "NoLLMTraining",
})

# Family that is "quote-only OK" when --quote-only-ok is set and the file is
# beneath a `quote-only/` segment in its path.
QUOTE_ONLY_FAMILY: frozenset[str] = frozenset({
    "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
    "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
    "LGPL-2.1", "LGPL-2.1-only", "LGPL-2.1-or-later",
    "LGPL-3.0", "LGPL-3.0-only", "LGPL-3.0-or-later",
    "GFDL-1.3", "GFDL-1.2", "GFDL-1.1",
})

# Patterns that sniff a LICENSE / COPYING file body when no SPDX is present.
# Order matters: most specific patterns first.
LICENSE_BODY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AGPL-3.0",       re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE\s+Version 3", re.I)),
    ("GPL-3.0",        re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 3", re.I)),
    ("GPL-2.0",        re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 2", re.I)),
    ("LGPL-3.0",       re.compile(r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 3", re.I)),
    ("LGPL-2.1",       re.compile(r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 2\.1", re.I)),
    ("GFDL-1.3",       re.compile(r"GNU Free Documentation License\s+Version 1\.3", re.I)),
    ("SSPL-1.0",       re.compile(r"Server Side Public License", re.I)),
    ("Elastic-2.0",    re.compile(r"Elastic License 2\.0", re.I)),
    ("Commons-Clause", re.compile(r"\bCommons Clause\b", re.I)),
    ("CC-BY-NC-SA-4.0",re.compile(r"Creative Commons Attribution-NonCommercial-ShareAlike 4\.0", re.I)),
    ("CC-BY-NC-4.0",   re.compile(r"Creative Commons Attribution-NonCommercial 4\.0", re.I)),
    ("CC-BY-ND-4.0",   re.compile(r"Creative Commons Attribution-NoDerivatives 4\.0", re.I)),
    ("CC-BY-SA-4.0",   re.compile(r"Creative Commons Attribution-ShareAlike 4\.0", re.I)),
    ("CC-BY-4.0",      re.compile(r"Creative Commons Attribution 4\.0", re.I)),
    ("CC-BY-3.0",      re.compile(r"Creative Commons Attribution 3\.0", re.I)),
    ("CC0-1.0",        re.compile(r"CC0 1\.0 Universal", re.I)),
    ("Apache-2.0",     re.compile(r"Apache License\s*,?\s*Version 2\.0", re.I)),
    ("BSD-3-Clause",   re.compile(r"Redistributions of source code.+Redistributions in binary form.+Neither the name", re.S | re.I)),
    ("BSD-2-Clause",   re.compile(r"Redistributions of source code.+Redistributions in binary form", re.S | re.I)),
    ("MPL-2.0",        re.compile(r"Mozilla Public License Version 2\.0", re.I)),
    ("BSL-1.0",        re.compile(r"Boost Software License - Version 1\.0", re.I)),
    ("ISC",            re.compile(r"Permission to use, copy, modify, and/or distribute this software", re.I)),
    ("Zlib",           re.compile(r"This software is provided 'as-is'.+altered from any source distribution", re.S | re.I)),
    ("Unlicense",      re.compile(r"This is free and unencumbered software released into the public domain", re.I)),
    ("PostgreSQL",     re.compile(r"PostgreSQL Database Management System", re.I)),
    ("Public-Domain",  re.compile(r"\bpublic domain\b", re.I)),
    # MIT is broad — keep last so more specific BSD/ISC patterns win first.
    ("MIT",            re.compile(r"Permission is hereby granted, free of charge, to any person obtaining a copy", re.I)),
]

# Path to the declarative source-of-truth allowlist TOML (resolved relative to
# this file so it works both from the repo root and from arbitrary cwd).
DEFAULT_ALLOWLIST_PATH: Path = Path(__file__).resolve().parent / "license_allowlist.toml"


SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9_.\-+]+(?:\s+(?:WITH|AND|OR)\s+[A-Za-z0-9_.\-+]+)*)")
PKG_JSON_LIC_RE = re.compile(r'"license"\s*:\s*"([^"]+)"')
CARGO_LIC_RE = re.compile(r'^\s*license\s*=\s*"([^"]+)"', re.M)
PYPROJECT_LIC_RE = re.compile(r'license\s*=\s*(?:"([^"]+)"|\{\s*text\s*=\s*"([^"]+)"\s*\})')
FOOTER_LIC_RE = re.compile(r"(?:licensed under|licen[sc]e[:\s]+)\s*(?:the\s+)?([A-Za-z0-9\-.+ ]{2,40}?)(?:\s+licen[sc]e)?[.,<\)\n]", re.I)

# Heuristic: file extensions we treat as "leaf content" for scanning.
SCAN_EXTS: frozenset[str] = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".rs", ".go", ".c", ".h", ".cc", ".hh", ".cpp", ".hpp", ".cxx",
    ".java", ".kt", ".scala", ".swift", ".m", ".mm",
    ".rb", ".php", ".pl", ".lua", ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".prisma", ".graphql",
    ".md", ".rst", ".txt", ".html", ".htm",
    ".toml", ".yaml", ".yml", ".json",
    ".hexa",
})

# Files we always inspect regardless of extension.
ALWAYS_SCAN_NAMES: frozenset[str] = frozenset({
    "LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md",
    "COPYING", "COPYING.md", "COPYING.txt", "COPYRIGHT", "NOTICE",
    "package.json", "Cargo.toml", "pyproject.toml",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    path: str
    license: str
    reason: str
    severity: str  # "WARN" | "FAIL"


@dataclass
class Attribution:
    path: str
    license: str
    attribution: str


@dataclass
class ScanResult:
    scan_root: str
    scan_time: str
    total_files: int = 0
    by_license: dict[str, int] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    attribution_required: list[Attribution] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=lambda: {"pass": 0, "warn": 0, "fail": 0})

    def to_dict(self) -> dict:
        return {
            "scan_root": self.scan_root,
            "scan_time": self.scan_time,
            "total_files": self.total_files,
            "by_license": dict(sorted(self.by_license.items())),
            "violations": [asdict(v) for v in self.violations],
            "attribution_required": [asdict(a) for a in self.attribution_required],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Declarative allowlist (tool/license_allowlist.toml)
# ---------------------------------------------------------------------------

@dataclass
class AllowlistConfig:
    """Resolved license taxonomy loaded from license_allowlist.toml.

    When `source_path` is None, the hardcoded fallback sets were used.
    """
    permissive: frozenset[str]
    attribution_required: frozenset[str]
    quote_only: frozenset[str]
    denylist: frozenset[str]
    or_picks_most_permissive: bool = True
    and_picks_strictest: bool = True
    plus_suffix_stripped: bool = True
    source_path: Optional[str] = None  # None = hardcoded fallback

    @classmethod
    def fallback(cls) -> "AllowlistConfig":
        """Return the hardcoded-constants fallback (back-compat behaviour)."""
        return cls(
            permissive=ALLOWLIST,
            attribution_required=ATTRIBUTION_REQUIRED,
            quote_only=QUOTE_ONLY_FAMILY,
            denylist=DENYLIST,
            or_picks_most_permissive=True,
            and_picks_strictest=True,
            plus_suffix_stripped=True,
            source_path=None,
        )


# Process-wide cache: load once, share across classify() calls.
_ALLOWLIST_CACHE: Optional[AllowlistConfig] = None


def load_allowlist(path: Optional[Path] = None) -> AllowlistConfig:
    """Read `license_allowlist.toml` and return an AllowlistConfig.

    - `path` defaults to `tool/license_allowlist.toml` next to this script.
    - If the file is missing or unparseable, prints a one-line warning to
      stderr and returns the hardcoded-constants fallback (does NOT exit).
    - The result is cached for subsequent calls with the same path.
    """
    global _ALLOWLIST_CACHE
    target = (path or DEFAULT_ALLOWLIST_PATH).resolve() if (path or DEFAULT_ALLOWLIST_PATH) else None

    # Re-use cache when the resolved path matches.
    if _ALLOWLIST_CACHE is not None and _ALLOWLIST_CACHE.source_path == (
        str(target) if target else None
    ):
        return _ALLOWLIST_CACHE

    if target is None or not target.is_file():
        print(
            f"warning: allowlist TOML not found ({target}); using hardcoded fallback",
            file=sys.stderr,
        )
        cfg = AllowlistConfig.fallback()
        _ALLOWLIST_CACHE = cfg
        return cfg

    if _tomllib is None:
        print(
            "warning: tomllib/tomli not available; using hardcoded fallback",
            file=sys.stderr,
        )
        cfg = AllowlistConfig.fallback()
        _ALLOWLIST_CACHE = cfg
        return cfg

    try:
        with open(target, "rb") as fh:
            data = _tomllib.load(fh)
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"warning: failed to parse {target} ({exc}); using hardcoded fallback",
            file=sys.stderr,
        )
        cfg = AllowlistConfig.fallback()
        _ALLOWLIST_CACHE = cfg
        return cfg

    def _gather(section_path: list[str]) -> list[str]:
        cur: object = data
        for key in section_path:
            if not isinstance(cur, dict) or key not in cur:
                return []
            cur = cur[key]
        if isinstance(cur, dict):
            spdx = cur.get("spdx", [])
            return list(spdx) if isinstance(spdx, list) else []
        return []

    permissive = set(_gather(["allowlist", "permissive"]))
    attribution = set(_gather(["allowlist", "attribution_required"]))
    quote_only = set(_gather(["allowlist", "quote_only"]))

    # denylist may have multiple sub-tables (commercial_block, proprietary, ...).
    deny: set[str] = set()
    deny_root = data.get("denylist", {}) if isinstance(data, dict) else {}
    if isinstance(deny_root, dict):
        for sub in deny_root.values():
            if isinstance(sub, dict):
                spdx = sub.get("spdx", [])
                if isinstance(spdx, list):
                    deny.update(spdx)

    compound = data.get("compound_handling", {}) if isinstance(data, dict) else {}
    or_perm = bool(compound.get("or_picks_most_permissive", True)) if isinstance(compound, dict) else True
    and_strict = bool(compound.get("and_picks_strictest", True)) if isinstance(compound, dict) else True
    plus_strip = bool(compound.get("plus_suffix_stripped", True)) if isinstance(compound, dict) else True

    cfg = AllowlistConfig(
        permissive=frozenset(permissive),
        attribution_required=frozenset(attribution),
        quote_only=frozenset(quote_only),
        denylist=frozenset(deny),
        or_picks_most_permissive=or_perm,
        and_picks_strictest=and_strict,
        plus_suffix_stripped=plus_strip,
        source_path=str(target),
    )
    _ALLOWLIST_CACHE = cfg
    return cfg


def _reset_allowlist_cache() -> None:
    """Test hook: clear the cached AllowlistConfig."""
    global _ALLOWLIST_CACHE
    _ALLOWLIST_CACHE = None


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _read_text(p: Path, max_bytes: int = 32_768) -> str:
    """Best-effort text read with a size cap; binary files yield ''."""
    try:
        with open(p, "rb") as fh:
            data = fh.read(max_bytes)
    except OSError:
        return ""
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def detect_spdx(text: str) -> Optional[str]:
    """Find an SPDX-License-Identifier line; return the raw expression or None."""
    m = SPDX_RE.search(text)
    if not m:
        return None
    expr = m.group(1).strip()
    # Compound expressions: take the first token for classification but keep
    # the full expression as the reported license string when it disambiguates.
    return expr


def detect_license_body(text: str) -> Optional[str]:
    """Sniff a LICENSE/COPYING file body for a known license signature."""
    for spdx, pat in LICENSE_BODY_PATTERNS:
        if pat.search(text):
            return spdx
    return None


def detect_package_json(text: str) -> Optional[str]:
    m = PKG_JSON_LIC_RE.search(text)
    return m.group(1).strip() if m else None


def detect_cargo_toml(text: str) -> Optional[str]:
    m = CARGO_LIC_RE.search(text)
    return m.group(1).strip() if m else None


def detect_pyproject(text: str) -> Optional[str]:
    m = PYPROJECT_LIC_RE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip() or None


def detect_html_footer(text: str) -> Optional[str]:
    """Sniff doc-page footer for 'licensed under ...' phrasing."""
    m = FOOTER_LIC_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    # Normalise common phrasings to SPDX-ish tokens.
    norm = raw.replace(" ", "-")
    lookup = norm.upper()
    aliases = {
        "MIT": "MIT",
        "APACHE-2.0": "Apache-2.0",
        "APACHE-2": "Apache-2.0",
        "BSD": "BSD-3-Clause",
        "BSD-3-CLAUSE": "BSD-3-Clause",
        "BSD-2-CLAUSE": "BSD-2-Clause",
        "ISC": "ISC",
        "CC-BY-4.0": "CC-BY-4.0",
        "CC-BY-SA-4.0": "CC-BY-SA-4.0",
        "CC0-1.0": "CC0-1.0",
        "CC0": "CC0-1.0",
        "UNLICENSE": "Unlicense",
        "MPL-2.0": "MPL-2.0",
    }
    return aliases.get(lookup)


def find_ancestor_license_file(path: Path, scan_root: Path) -> Optional[Path]:
    """Walk up from path to scan_root looking for a LICENSE/COPYING file."""
    cur = path.parent.resolve()
    root = scan_root.resolve()
    while True:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt",
                     "LICENCE", "LICENCE.md", "COPYING", "COPYING.md"):
            cand = cur / name
            if cand.is_file():
                return cand
        if cur == root or cur.parent == cur:
            return None
        cur = cur.parent


def classify(spdx: str, config: Optional[AllowlistConfig] = None) -> tuple[str, str]:
    """
    Return (category, normalised_spdx).

    category in {"allow", "attribution", "deny", "unknown"}.

    Consults the declarative allowlist from `tool/license_allowlist.toml`
    (loaded via `load_allowlist()`). When the TOML cannot be read, falls
    back to the hardcoded module-level constants. Pass an explicit
    `config` (an `AllowlistConfig`) to override resolution -- useful for
    tests or alternate allowlist files.
    """
    if not spdx:
        return ("unknown", "UNKNOWN")
    cfg = config if config is not None else load_allowlist()

    # Normalise simple aliases.
    norm = spdx.strip()
    aliases = {
        "BSD": "BSD-3-Clause",
        "Apache 2.0": "Apache-2.0",
        "Apache-2": "Apache-2.0",
        "GPLv3": "GPL-3.0",
        "GPLv2": "GPL-2.0",
        "AGPLv3": "AGPL-3.0",
        "LGPLv3": "LGPL-3.0",
        "LGPLv2.1": "LGPL-2.1",
        "Public Domain": "Public-Domain",
    }
    norm = aliases.get(norm, norm)

    # Compound SPDX expression: "A OR B" — pick the most permissive disjunct.
    if cfg.or_picks_most_permissive and " OR " in norm.upper():
        parts = [p.strip() for p in re.split(r"\s+OR\s+", norm, flags=re.I)]
        for p in parts:
            cat, n = classify(p, cfg)
            if cat == "allow":
                return (cat, n)
        for p in parts:
            cat, n = classify(p, cfg)
            if cat == "attribution":
                return (cat, n)
        # Fall through to deny/unknown on first part.
        return classify(parts[0], cfg)

    if cfg.and_picks_strictest and " AND " in norm.upper():
        # "A AND B" — must satisfy every component; strictest wins.
        parts = [p.strip() for p in re.split(r"\s+AND\s+", norm, flags=re.I)]
        worst = ("allow", norm)
        rank = {"allow": 0, "attribution": 1, "unknown": 2, "deny": 3}
        for p in parts:
            cat, n = classify(p, cfg)
            if rank[cat] > rank[worst[0]]:
                worst = (cat, n)
        return worst

    # Primary check: declarative TOML sets.
    if norm in cfg.permissive:
        return ("allow", norm)
    if norm in cfg.attribution_required:
        return ("attribution", norm)
    if norm in cfg.denylist:
        return ("deny", norm)

    # Suffix-tolerant denylist match (e.g. "GPL-3.0+").
    if cfg.plus_suffix_stripped:
        base = norm.rstrip("+")
        if base != norm:
            if base in cfg.permissive:
                return ("allow", base)
            if base in cfg.attribution_required:
                return ("attribution", base)
            if base in cfg.denylist:
                return ("deny", base)

    # Secondary check: hardcoded fallback constants (covers legacy aliases
    # such as "MIT-0", "BSD-4-Clause", "Apache-1.1", "Python-2.0",
    # "SQLite", "Boost-1.0", "Public-Domain" that may not appear verbatim
    # in the TOML). This preserves the pre-TOML behaviour as a safety net.
    if norm in ALLOWLIST:
        return ("allow", norm)
    if norm in ATTRIBUTION_REQUIRED:
        return ("attribution", norm)
    if norm in DENYLIST:
        return ("deny", norm)
    base = norm.rstrip("+")
    if base != norm and base in DENYLIST:
        return ("deny", base)

    return ("unknown", norm)


def detect_file_license(path: Path, scan_root: Path) -> tuple[str, str]:
    """
    Run the detection pipeline against a single file.

    Returns (license_spdx, source_of_detection). source_of_detection is one of
    {"spdx", "license-file", "package.json", "cargo.toml", "pyproject.toml",
    "footer", "none"}.
    """
    name = path.name
    text = _read_text(path)

    # 1. SPDX in the file itself.
    spdx = detect_spdx(text)
    if spdx:
        return (spdx, "spdx")

    # 2. Manifest hints from special filenames.
    if name == "package.json":
        lic = detect_package_json(text)
        if lic:
            return (lic, "package.json")
    if name == "Cargo.toml":
        lic = detect_cargo_toml(text)
        if lic:
            return (lic, "cargo.toml")
    if name == "pyproject.toml":
        lic = detect_pyproject(text)
        if lic:
            return (lic, "pyproject.toml")

    # 3. LICENSE/COPYING body sniff (if this file IS a license file).
    lower = name.lower()
    if lower.startswith(("license", "licence", "copying")):
        body_lic = detect_license_body(text)
        if body_lic:
            return (body_lic, "license-file")

    # 4. Walk up to find a sibling/ancestor LICENSE file.
    anc = find_ancestor_license_file(path, scan_root)
    if anc is not None:
        anc_text = _read_text(anc)
        anc_spdx = detect_spdx(anc_text)
        if anc_spdx:
            return (anc_spdx, "license-file")
        body_lic = detect_license_body(anc_text)
        if body_lic:
            return (body_lic, "license-file")

    # 5. HTML / markdown footer sniff (two-pass: full-name body patterns first,
    #    then short "licensed under X" phrasing).
    if path.suffix.lower() in {".html", ".htm", ".md", ".rst"}:
        body_lic = detect_license_body(text)
        if body_lic:
            return (body_lic, "footer")
        foot = detect_html_footer(text)
        if foot:
            return (foot, "footer")

    return ("UNKNOWN", "none")


# ---------------------------------------------------------------------------
# Manifest cross-check
# ---------------------------------------------------------------------------

_TOML_ENTRY_RE = re.compile(r"\[([^\]]+)\]\s*\n((?:[^\[]*\n)*)", re.M)
_TOML_KV_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+)\s*=\s*"([^"]*)"', re.M)


def load_manifest(path: Path) -> dict[str, str]:
    """
    Parse a minimal `datasets.toml`-style file. Only [section] tables with a
    `license = "..."` key are returned. The section name is the dataset id.
    """
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    text = _read_text(path, max_bytes=1_000_000)
    for m in _TOML_ENTRY_RE.finditer(text):
        section = m.group(1).strip()
        body = m.group(2)
        for kv in _TOML_KV_RE.finditer(body):
            if kv.group(1) == "license":
                out[section] = kv.group(2).strip()
    return out


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def should_scan(p: Path) -> bool:
    if not p.is_file():
        return False
    if p.name in ALWAYS_SCAN_NAMES:
        return True
    if p.suffix.lower() in SCAN_EXTS:
        return True
    # LICENSE / COPYING with arbitrary suffix.
    lower = p.name.lower()
    if lower.startswith(("license", "licence", "copying")):
        return True
    return False


def is_in_quote_only_subtree(path: Path, scan_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(scan_root.resolve())
    except ValueError:
        return False
    return "quote-only" in rel.parts


def extract_attribution(path: Path) -> str:
    """
    Pull a best-effort attribution line from a file. Looks for 'Copyright ...'
    or '(c) YYYY Holder'. Returns '' if nothing is found.
    """
    text = _read_text(path, max_bytes=8192)
    for line in text.splitlines()[:60]:
        m = re.search(r"(Copyright[^\n]*?\d{4}[^\n]*)", line)
        if m:
            return m.group(1).strip().strip("*").strip()
        m = re.search(r"\(c\)\s*\d{4}[^\n]*", line, re.I)
        if m:
            return m.group(0).strip()
    return ""


def scan_tree(
    scan_root: Path,
    manifest: dict[str, str],
    strict: bool,
    allow_unknown: bool,
    quote_only_ok: bool,
    config: Optional[AllowlistConfig] = None,
) -> ScanResult:
    cfg = config if config is not None else load_allowlist()
    # Quote-only family = union of the legacy hardcoded family and the TOML
    # `[allowlist.quote_only]` set, so newly declared SPDX ids in the TOML
    # are honoured immediately.
    quote_only_set = cfg.quote_only | QUOTE_ONLY_FAMILY

    result = ScanResult(
        scan_root=str(scan_root.resolve()),
        scan_time=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(scan_root):
        # Skip dot-dirs and common build/vendor noise.
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in {"node_modules", "__pycache__", "target", "dist", "build"}
        ]
        for fn in filenames:
            p = Path(dirpath) / fn
            if should_scan(p):
                files.append(p)

    for fp in files:
        result.total_files += 1
        spdx, _source = detect_file_license(fp, scan_root)
        category, norm = classify(spdx, cfg)
        result.by_license[norm] = result.by_license.get(norm, 0) + 1

        rel_path = str(fp.resolve())

        if category == "allow":
            result.summary["pass"] += 1
            continue

        if category == "attribution":
            result.summary["pass"] += 1
            result.attribution_required.append(Attribution(
                path=rel_path,
                license=norm,
                attribution=extract_attribution(fp) or "(none found)",
            ))
            continue

        if category == "deny":
            if quote_only_ok and norm in quote_only_set and is_in_quote_only_subtree(fp, scan_root):
                # Permitted as quote-only excerpt; track as warning, not fail.
                result.summary["warn"] += 1
                result.violations.append(Violation(
                    path=rel_path,
                    license=norm,
                    reason="quote-only subtree (allowed by --quote-only-ok)",
                    severity="WARN",
                ))
            else:
                result.summary["fail"] += 1
                result.violations.append(Violation(
                    path=rel_path,
                    license=norm,
                    reason="denylist",
                    severity="FAIL",
                ))
            continue

        # category == "unknown"
        if allow_unknown:
            result.summary["pass"] += 1
        else:
            sev = "FAIL" if strict else "WARN"
            if sev == "FAIL":
                result.summary["fail"] += 1
            else:
                result.summary["warn"] += 1
            result.violations.append(Violation(
                path=rel_path,
                license=norm,
                reason="no SPDX/no LICENSE",
                severity=sev,
            ))

    # Manifest cross-check: any manifest entry whose declared license does not
    # round-trip to an allowlisted category becomes a violation.
    for entry, declared in manifest.items():
        cat, norm = classify(declared, cfg)
        if cat in ("deny",):
            result.summary["fail"] += 1
            result.violations.append(Violation(
                path=f"manifest:{entry}",
                license=norm,
                reason="manifest declares denylisted license",
                severity="FAIL",
            ))
        elif cat == "unknown":
            sev = "FAIL" if strict else "WARN"
            if sev == "FAIL":
                result.summary["fail"] += 1
            else:
                result.summary["warn"] += 1
            result.violations.append(Violation(
                path=f"manifest:{entry}",
                license=norm,
                reason="manifest license not recognised",
                severity=sev,
            ))

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="license_clean_scan.py",
        description="License-clean CI prototype for the hexa-forge corpus audit.",
    )
    ap.add_argument("--path", default=".", help="directory to scan (default: cwd)")
    ap.add_argument("--manifest", default=None, help="optional datasets.toml manifest to cross-check")
    ap.add_argument("--strict", action="store_true", help="fail on ANY non-permissive license (UNKNOWN also fails)")
    ap.add_argument("--allow-unknown", action="store_true", help="treat UNKNOWN as pass instead of warn")
    ap.add_argument("--quote-only-ok", action="store_true",
                    help="permit GPL/LGPL/GFDL files beneath a 'quote-only/' subtree (still recorded as WARN)")
    ap.add_argument("--report", default=None, help="write JSON audit report to this path")
    ap.add_argument("--selftest", action="store_true", help="run inline unit tests and exit")
    return ap


def run_cli(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.selftest:
        return _run_selftest()

    scan_root = Path(args.path)
    if not scan_root.is_dir():
        print(f"error: --path is not a directory: {scan_root}", file=sys.stderr)
        return 2

    manifest = load_manifest(Path(args.manifest)) if args.manifest else {}

    result = scan_tree(
        scan_root=scan_root,
        manifest=manifest,
        strict=args.strict,
        allow_unknown=args.allow_unknown,
        quote_only_ok=args.quote_only_ok,
    )

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2, sort_keys=False)
        print(f"audit report written: {args.report}")

    # Brief stdout summary.
    s = result.summary
    print(f"scanned {result.total_files} files  pass={s['pass']} warn={s['warn']} fail={s['fail']}")
    if result.violations:
        print("violations:")
        for v in result.violations[:20]:
            print(f"  [{v.severity}] {v.license:<20} {v.path}  ({v.reason})")
        if len(result.violations) > 20:
            print(f"  ... and {len(result.violations) - 20} more")

    if s["fail"] > 0:
        return 2
    if s["warn"] > 0:
        return 2 if args.strict else 1
    return 0


# ---------------------------------------------------------------------------
# Inline self-tests
# ---------------------------------------------------------------------------

def _write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def _run_selftest() -> int:  # noqa: C901 - test driver, length is fine
    """Synthetic fixtures covering the six representative cases from the spec."""
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # 1. SPDX MIT pass.
        _write(root / "case_mit" / "mod.py",
               "# SPDX-License-Identifier: MIT\nprint('ok')\n")

        # 2. GPL-3.0 fail (LICENSE file body sniff).
        _write(root / "case_gpl" / "LICENSE",
               "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n")
        _write(root / "case_gpl" / "src.c", "int main(void){return 0;}\n")

        # 3. CC-BY-NC-SA-4.0 fail (footer sniff in markdown).
        _write(root / "case_cc_nc" / "page.md",
               "# Hello\n\nContent.\n\n"
               "<footer>This work is licensed under the "
               "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 "
               "International License.</footer>\n")

        # 4. UNKNOWN warn.
        _write(root / "case_unknown" / "foo.py", "x = 1\n")

        # 5. package.json MIT pass.
        _write(root / "case_pkg" / "package.json",
               '{\n  "name": "demo",\n  "version": "1.0.0",\n  "license": "MIT"\n}\n')

        # 6. CC-BY-4.0 attribution required.
        _write(root / "case_ccby" / "doc.md",
               "# Tailwind Snippet\n\n"
               "Copyright (c) 2025 Tailwind Labs\n\n"
               "<!-- SPDX-License-Identifier: CC-BY-4.0 -->\n"
               "Some snippet text.\n")

        # 7. Quote-only GPL fixture (controlled subtree).
        _write(root / "quote-only" / "gpl_excerpt" / "snippet.c",
               "// SPDX-License-Identifier: GPL-3.0\nint x;\n")

        # ---- default run (no strict, no quote-only-ok)
        result = scan_tree(root, manifest={}, strict=False,
                           allow_unknown=False, quote_only_ok=False)

        def find_violation(license_substr: str, path_substr: str) -> Optional[Violation]:
            for v in result.violations:
                if license_substr in v.license and path_substr in v.path:
                    return v
            return None

        if find_violation("MIT", "case_mit") is not None:
            failures.append("case_mit: MIT should not be a violation")

        v_gpl = find_violation("GPL-3.0", "case_gpl")
        if v_gpl is None or v_gpl.severity != "FAIL":
            failures.append("case_gpl: GPL-3.0 should FAIL")

        v_nc = find_violation("CC-BY-NC-SA-4.0", "case_cc_nc")
        if v_nc is None or v_nc.severity != "FAIL":
            failures.append("case_cc_nc: CC-BY-NC-SA-4.0 should FAIL")

        v_unk = find_violation("UNKNOWN", "case_unknown")
        if v_unk is None or v_unk.severity != "WARN":
            failures.append("case_unknown: UNKNOWN should WARN (default)")

        # package.json MIT pass.
        if result.by_license.get("MIT", 0) < 2:
            failures.append("case_pkg: package.json MIT not counted")

        # CC-BY-4.0 attribution recorded.
        attr_hits = [a for a in result.attribution_required if "case_ccby" in a.path]
        if not attr_hits or attr_hits[0].license != "CC-BY-4.0":
            failures.append("case_ccby: CC-BY-4.0 attribution not recorded")
        elif "Tailwind" not in attr_hits[0].attribution:
            failures.append("case_ccby: attribution string did not capture 'Tailwind'")

        # Quote-only GPL: without --quote-only-ok it should FAIL.
        v_qo = find_violation("GPL-3.0", "quote-only")
        if v_qo is None or v_qo.severity != "FAIL":
            failures.append("quote-only/: GPL-3.0 should FAIL without --quote-only-ok")

        # ---- with --quote-only-ok the quote-only GPL becomes WARN.
        result_qo = scan_tree(root, manifest={}, strict=False,
                              allow_unknown=False, quote_only_ok=True)
        qo_warns = [v for v in result_qo.violations
                    if "quote-only" in v.path and v.license.startswith("GPL")]
        if not qo_warns or qo_warns[0].severity != "WARN":
            failures.append("quote-only/: --quote-only-ok should downgrade GPL to WARN")

        # ---- strict mode promotes UNKNOWN to FAIL.
        result_strict = scan_tree(root, manifest={}, strict=True,
                                  allow_unknown=False, quote_only_ok=False)
        v_unk_s = None
        for v in result_strict.violations:
            if v.license == "UNKNOWN" and "case_unknown" in v.path:
                v_unk_s = v
                break
        if v_unk_s is None or v_unk_s.severity != "FAIL":
            failures.append("case_unknown: UNKNOWN should FAIL under --strict")

        # ---- manifest cross-check: a manifest with GPL must FAIL.
        manifest_path = root / "datasets.toml"
        _write(manifest_path,
               '[stack_v2_perm]\nlicense = "MIT"\n\n'
               '[bad_entry]\nlicense = "GPL-3.0"\n')
        manifest = load_manifest(manifest_path)
        if manifest.get("bad_entry") != "GPL-3.0":
            failures.append("manifest: GPL-3.0 entry not parsed")
        result_mf = scan_tree(root, manifest=manifest, strict=False,
                              allow_unknown=False, quote_only_ok=False)
        mf_hits = [v for v in result_mf.violations
                   if v.path == "manifest:bad_entry"]
        if not mf_hits or mf_hits[0].severity != "FAIL":
            failures.append("manifest: bad_entry GPL-3.0 should FAIL")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_cli())
