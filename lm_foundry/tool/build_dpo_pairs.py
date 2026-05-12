#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_dpo_pairs.py — DPO preference-pair pipeline driver for the `code` verb.

Phase v0.2.0 cross-cutting infra deliverable per ROADMAP §2 / TODO.md §2
"DPO data pipeline" item. Builds (preferred, dispreferred) code patch pairs
at the 2-5M scale from linter-autofix runs and tree-sitter rule-pack queries
over the Stack v2 permissive subset.

WHAT THIS TOOL IS (Phase 1, v0.2.0)
-----------------------------------
The DPO *driver* + dispatcher + manifest schema + stub source enumeration +
self-test mocks. It is the structural skeleton that lands NOW; the actual
linter invocations (clippy/ruff/golangci-lint/clang-tidy) land in Phase 2
when the Stack v2 corpus fetch completes (HF auth via mac-exec — see
`papers/plan-runbook-v0.1.3.md`).

In Phase 1, all four linter dispatchers are mocked: each one reads a fixture
that mirrors the real `(before, after, rule_id, severity)` shape so that the
build / dedup / stats pipeline below it is fully exercised. Phase 2 simply
swaps the mock body for a `subprocess.run(...)` call against the real linter.

SUBCOMMANDS
-----------
enumerate   walk a Stack v2 (or sample) dir; emit per-language file list
            with size + SHA-256, gated by the file-extension policy below.
lint        for each enumerated file, dispatch to the language's linter
            in `--fix` mode (in a sandbox copy); produce per-file records
            of (before, after, rule_id, severity, citation). All linter
            invocations gated behind `--apply-real`; default = mock.
treesitter  feed files through `tool/treesitter_rule_pack/rules.toml` and
            extract idiom-violation pairs (positive idiom + negative
            anti-pattern). All 50 rules contribute; severity comes from
            the rule's `severity` field.
build       combine `lint` + `treesitter` outputs → emit canonical DPO
            JSONL of `{"chosen": ..., "rejected": ..., "rule": ...,
            "severity": "block|warn|info", "lang": ..., "source_sha": ...,
            "weight": float, "citation": ...}`.
dedup       MinHash + exact-dup removal across the JSONL. MinHash uses the
            `datasketch` library if importable; falls back to stdlib SHA-256
            exact-match and emits a `__MINHASH_FOLLOWUP__` advisory.
stats       aggregate by (lang, severity, rule); emit `<jsonl>.stats.json`
            including `__NO_LLM_JUDGE__: true` sentinel.

ANTI-CORPUS INTEGRATION
-----------------------
Before `lint` / `treesitter` consume any file, this tool invokes
`tool/anticorpus_filter.py --check-path <path>` as a subprocess. If the
filter rejects the path (non-zero exit code OR "REJECT" verdict on stdout),
the file is skipped and a `_PRUNED_BY_ANTICORPUS_` reason recorded in the
enumerate manifest. The anti-corpus tool is a sister deliverable being
built in parallel — this module DOES NOT TOUCH ITS FILES and gracefully
degrades when the binary is absent (skips the check and emits an advisory).

NO LLM-JUDGE DISCIPLINE
-----------------------
Per `papers/plan-decisions-pending.md` D-013 (resolved 중도): this tool
NEVER prompts a generative model to score, rewrite, or judge a pair. The
positive form is ALWAYS one of:
  (a) the deterministic linter `--fix` output (clippy/ruff/golangci-lint
      autofix, safe-only tier), or
  (b) the tree-sitter rule pack's `.positive.scm` match inside the same
      file (or a curated `inline` positive sketch).

Rationale: Shumailov et al. 2024 ("The Curse of Recursion: Training on
Generated Data Makes Models Forget") shows that model-output-of-model-
output causes irreversible distributional collapse. The deterministic
rule pack + canonical linter output is the only judge for v1.0.

This invariant is asserted at runtime: every `stats` JSON output
contains `"__NO_LLM_JUDGE__": true`. CI parses this sentinel as part
of the gate-① license-clean adjacency check (planned).

SEVERITY → DPO WEIGHT POLICY
----------------------------
Per `papers/spec-treesitter-rule-pack.md` §6.1:
    block (anti-pattern hard fails)  → weight 1.0
    warn  (style issues)             → weight 0.5
    info  (idiom suggestions)        → weight 0.2

The weight column lands in each JSONL row and feeds the DPO loss scaling
at training time. Unrecognised severities default to 0.0 and are recorded
as a defect in `stats.defects[]`.

OUTPUT FORMAT
-------------
    runs/dpo_pairs.<YYYY-MM-DD>.jsonl       — one DPO pair per line
    runs/dpo_pairs.<YYYY-MM-DD>.stats.json  — aggregate counts + sentinels

Each JSONL row:
    {
      "chosen":      "<idiomatic code hunk>",
      "rejected":    "<anti-idiomatic code hunk>",
      "rule":        "R-PY-001" | "ruff:B006" | "clippy:unwrap_used",
      "severity":    "block" | "warn" | "info",
      "lang":        "python" | "rust" | "typescript" | "go" | "c",
      "source_sha":  "<sha256 of originating file>",
      "source":      "treesitter:R-PY-001+ruff:B006",
      "weight":      1.0 | 0.5 | 0.2,
      "citation":    "tier-e-findings.md / Python / mutable default arg",
      "applicability": "safe" | "unsafe"
    }

YIELD TARGET
------------
2-5M dedup-survived pairs per `papers/tier-e-findings.md` Part 2 §"linter-
driven (clippy/ruff/golangci/clang-tidy autofix)" estimate. At Phase 1
the dispatcher emits a handful per mock fixture; Phase 2 hits the real
target when Stack v2 lands.

USAGE
-----
    # self-test (no corpus, no linters, no model)
    python tool/build_dpo_pairs.py --selftest

    # enumerate a Stack v2 sample dir
    python tool/build_dpo_pairs.py enumerate \\
        --corpus-root corpus/code/pretrain-bias/stack-v2-sample/

    # mock lint pass (default at v0.2.0)
    python tool/build_dpo_pairs.py lint \\
        --enumerated runs/enumerate.<date>.json \\
        --out runs/lint.<date>.jsonl

    # tree-sitter rule-pack pass
    python tool/build_dpo_pairs.py treesitter \\
        --enumerated runs/enumerate.<date>.json \\
        --rules tool/treesitter_rule_pack/rules.toml \\
        --out runs/treesitter.<date>.jsonl

    # combine + canonicalise
    python tool/build_dpo_pairs.py build \\
        --lint runs/lint.<date>.jsonl \\
        --treesitter runs/treesitter.<date>.jsonl \\
        --out runs/dpo_pairs.<date>.jsonl

    # dedup
    python tool/build_dpo_pairs.py dedup \\
        --in runs/dpo_pairs.<date>.jsonl \\
        --out runs/dpo_pairs.<date>.dedup.jsonl

    # stats
    python tool/build_dpo_pairs.py stats \\
        --in runs/dpo_pairs.<date>.dedup.jsonl \\
        --out runs/dpo_pairs.<date>.stats.json

CROSS-LINKS
-----------
- Spec:           papers/spec-treesitter-rule-pack.md (severity model, §6.1
                  DPO weight policy, citation back-refs to Tier E findings)
- Sourcing:       papers/tier-e-findings.md Part 2 (linter coverage,
                  ~2-5M yield estimate); Part 3 (anti-corpus exclusions)
- Decisions:      D-013 (tree-sitter rule pack default, no LLM judge —
                  Shumailov 2024); D-016 (pre-2024-07 SE torrents only)
- Runbook:        papers/plan-runbook-v0.1.3.md (Stack v2 fetch via
                  mac-exec HF bridge)
- ROADMAP:        §2 cross-cutting infra (v0.2.0)
- Sister tool:    tool/anticorpus_filter.py (parallel build)
- Rule pack:      tool/treesitter_rule_pack/rules.toml (50 rules × 5 langs)
- DPO target:     2-5M pairs (Tier E Part 2 HIGH-confidence row)

LICENSE
-------
Apache-2.0 OR MIT — repo dual-license. SPDX header at top.

DEPENDENCIES
------------
Python 3.11+ stdlib only. `datasketch` soft-imported for MinHash
(graceful fallback to exact-SHA dedup with `__MINHASH_FOLLOWUP__`
advisory).
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
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional

try:  # Python 3.11+: stdlib tomllib
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        import tomli as _tomllib  # type: ignore[import-not-found,no-redef]
    except ImportError:
        _tomllib = None  # type: ignore[assignment]

# Soft-import datasketch; fall back to exact-SHA dedup if absent.
try:
    from datasketch import MinHash, MinHashLSH  # type: ignore[import-not-found]
    _HAS_DATASKETCH: bool = True
except Exception:  # pragma: no cover - optional dep
    MinHash = None  # type: ignore[assignment]
    MinHashLSH = None  # type: ignore[assignment]
    _HAS_DATASKETCH = False


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_RULES_TOML: Path = REPO_ROOT / "tool" / "treesitter_rule_pack" / "rules.toml"
DEFAULT_RUNS_DIR: Path = REPO_ROOT / "runs"
DEFAULT_ANTICORPUS_TOOL: Path = REPO_ROOT / "tool" / "anticorpus_filter.py"


# ---------------------------------------------------------------------------
# Static taxonomy
# ---------------------------------------------------------------------------

# Stack v2 supported languages for this driver. Tree-sitter rule pack v1
# covers these five; other Stack v2 langs are out of scope for v0.2.0.
SUPPORTED_LANGS: tuple[str, ...] = ("python", "rust", "typescript", "go", "c")

# Per-language file extensions used by `enumerate`. Mirrors the SCAN_EXTS
# convention from `tool/license_clean_scan.py` but narrowed to the langs
# the rule pack covers.
LANG_EXTS: dict[str, frozenset[str]] = {
    "python":     frozenset({".py", ".pyi"}),
    "rust":       frozenset({".rs"}),
    "typescript": frozenset({".ts", ".tsx", ".mts", ".cts"}),
    "go":         frozenset({".go"}),
    "c":          frozenset({".c", ".h"}),
}

# Reverse map: extension → lang. The first matching lang wins; collisions
# (e.g. `.h` is C-only here — C++ is out of scope for v1).
EXT_TO_LANG: dict[str, str] = {
    ext: lang for lang, exts in LANG_EXTS.items() for ext in exts
}

# Per-language linter command + invocation policy. The `cmd` template is
# what Phase 2 would execute; v0.2.0 errors out with a stable message
# when `--apply-real` is set. Each entry's `safe_fixes_only` flag flips
# the linter into "safe autofix" mode where supported (matches Tier E
# Part 2 §"linter-driven autofix" cons column).
LINTER_DISPATCH: dict[str, dict[str, Any]] = {
    "python": {
        "tool":   "ruff",
        "cmd":    ["ruff", "check", "--fix", "--no-cache", "--exit-zero"],
        "safe_fixes_only": True,
        "rule_prefix": "ruff:",
        "citation": "tier-e-findings.md Part 2 / ruff",
    },
    "rust": {
        "tool":   "clippy",
        # cargo clippy --fix --allow-dirty --allow-staged
        "cmd":    ["cargo", "clippy", "--fix", "--allow-dirty",
                   "--allow-staged"],
        "safe_fixes_only": True,
        "rule_prefix": "clippy:",
        "citation": "tier-e-findings.md Part 2 / clippy",
    },
    "typescript": {
        # eslint with @typescript-eslint plugin is the conventional driver,
        # but the spec doc and rule pack reference both eslint and tsc.
        # Phase 2 wires eslint --fix; treat the linter row as a TS-only
        # row for now.
        "tool":   "eslint",
        "cmd":    ["eslint", "--fix"],
        "safe_fixes_only": True,
        "rule_prefix": "@typescript-eslint/",
        "citation": "tier-e-findings.md Part 2 / @typescript-eslint",
    },
    "go": {
        "tool":   "golangci-lint",
        "cmd":    ["golangci-lint", "run", "--fix"],
        "safe_fixes_only": False,  # golangci has no granular safe-tier flag
        "rule_prefix": "golangci:",
        "citation": "tier-e-findings.md Part 2 / golangci-lint",
    },
    "c": {
        "tool":   "clang-tidy",
        "cmd":    ["clang-tidy", "--fix"],
        "safe_fixes_only": False,
        "rule_prefix": "clang-tidy:",
        "citation": "tier-e-findings.md Part 2 / clang-tidy",
    },
}

# Severity → DPO loss weight per spec-treesitter-rule-pack.md §6.1.
SEVERITY_WEIGHTS: dict[str, float] = {
    "block": 1.0,
    "warn":  0.5,
    "info":  0.2,
}

# Sentinels written into stats JSON to make CI assertions cheap.
SENTINEL_NO_LLM_JUDGE: str = "__NO_LLM_JUDGE__"
SENTINEL_MINHASH_FOLLOWUP: str = "__MINHASH_FOLLOWUP__"
SENTINEL_PHASE: str = "__BUILD_DPO_PAIRS_PHASE__"
SELFTEST_PASS_TAG: str = "__BUILD_DPO_PAIRS_SELFTEST__ PASS"
SELFTEST_FAIL_TAG: str = "__BUILD_DPO_PAIRS_SELFTEST__ FAIL"

# Phase tag. Phase 1 = mocks only. Phase 2 lights up when --apply-real
# is allowed by the dispatcher.
TOOL_PHASE: str = "v0.2.0-phase1-mocks"

# Phase 2 unavailable message — referenced from CLI, selftest, AND error path.
PHASE2_NOT_READY_MSG: str = (
    "Phase 2 — corpus required: real linter invocation is gated on the "
    "Stack v2 fetch landing per papers/plan-runbook-v0.1.3.md. Re-run "
    "without --apply-real to use the v0.2.0 mock dispatcher."
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class FileEntry:
    """One enumerated source file."""
    path: str          # absolute path
    rel_path: str      # path relative to the corpus root (for stable IDs)
    lang: str          # one of SUPPORTED_LANGS
    size_bytes: int
    sha256: str
    anticorpus_status: str = "OK"   # OK | PRUNED | SKIPPED-NO-FILTER
    anticorpus_reason: str = ""


@dataclass
class LintRecord:
    """One linter rewrite pair."""
    rel_path: str
    lang: str
    rule_id: str          # e.g. "ruff:B006", "clippy:unwrap_used"
    severity: str         # block | warn | info
    before: str           # the rejected hunk
    after: str            # the chosen (autofix) hunk
    citation: str         # source attribution
    applicability: str    # "safe" | "unsafe"
    source_sha: str       # sha256 of originating file


@dataclass
class TreesitterRecord:
    """One tree-sitter rule-pack match (anti) + paired positive."""
    rel_path: str
    lang: str
    rule_id: str          # canonical "R-XX-NNN"
    severity: str
    anti_hunk: str        # the rejected hunk
    positive_hunk: str    # the chosen hunk (from positive.scm or curated)
    citation: str
    source_sha: str
    positive_kind: str    # "query" | "inline" | "curated"


@dataclass
class DPOPair:
    """Canonical output row."""
    chosen: str
    rejected: str
    rule: str
    severity: str
    lang: str
    source_sha: str
    source: str           # provenance string (e.g. "treesitter:R-PY-001+ruff:B006")
    weight: float
    citation: str
    applicability: str    # "safe" | "unsafe"


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path: Path) -> str:
    """Stream-hash a file; identical algorithm to license_clean_scan."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1 << 16)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically via .tmp + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Write `rows` as JSONL atomically. Returns row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    n = 0
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")
            n += 1
    os.replace(tmp, path)
    return n


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file; skip blank lines; raise on malformed JSON."""
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{lineno}: malformed JSONL: {exc}"
                ) from exc
    return out


def _today_iso() -> str:
    return _dt.date.today().isoformat()


def _classify_lang(path: Path) -> Optional[str]:
    """Return the lang label for a given file extension, or None."""
    return EXT_TO_LANG.get(path.suffix.lower())


# ---------------------------------------------------------------------------
# rules.toml loader
# ---------------------------------------------------------------------------

def load_rules(rules_toml: Path) -> dict[str, Any]:
    """Load and validate `tool/treesitter_rule_pack/rules.toml`.

    Returns the parsed document. Raises if tomllib is unavailable or
    the file's schema deviates from the v1 contract.
    """
    if _tomllib is None:
        raise RuntimeError(
            "tomllib unavailable (need Python 3.11+ or `tomli`); "
            "cannot load rules.toml"
        )
    if not rules_toml.exists():
        raise FileNotFoundError(f"rules.toml not found at: {rules_toml}")
    with rules_toml.open("rb") as f:
        doc = _tomllib.load(f)
    if "rule" not in doc:
        raise ValueError(f"{rules_toml}: no [[rule]] tables present")
    rules = doc["rule"]
    if not isinstance(rules, list):
        raise ValueError(f"{rules_toml}: [[rule]] must be a table array")
    # Per-rule schema check.
    required = {"id", "lang", "severity", "anti_query", "positive_query"}
    for r in rules:
        missing = required - set(r.keys())
        if missing:
            raise ValueError(
                f"{rules_toml}: rule {r.get('id', '<unknown>')} "
                f"missing fields: {sorted(missing)}"
            )
        if r["severity"] not in SEVERITY_WEIGHTS:
            raise ValueError(
                f"{rules_toml}: rule {r['id']} severity "
                f"{r['severity']!r} not in {sorted(SEVERITY_WEIGHTS)}"
            )
        if r["lang"] not in SUPPORTED_LANGS:
            raise ValueError(
                f"{rules_toml}: rule {r['id']} lang {r['lang']!r} "
                f"not in {sorted(SUPPORTED_LANGS)}"
            )
    return doc


# ---------------------------------------------------------------------------
# Anti-corpus integration
# ---------------------------------------------------------------------------

def _anticorpus_check_path(
    path: Path,
    *,
    tool_path: Path = DEFAULT_ANTICORPUS_TOOL,
    timeout: float = 5.0,
) -> tuple[str, str]:
    """Invoke `tool/anticorpus_filter.py --check-path <path>`.

    Returns `(status, reason)` where status is one of:
        "OK"                 — file is clean
        "PRUNED"             — anti-corpus rejected the path
        "SKIPPED-NO-FILTER"  — anti-corpus tool not present (graceful)
        "SKIPPED-ERROR"      — tool errored unexpectedly (graceful)

    The contract with the sister `anticorpus_filter.py` tool:
      - exit code 0 + stdout containing "OK"     → clean
      - exit code 0 + stdout containing "REJECT" → pruned
      - exit code non-zero                       → pruned (reason = stderr)
    """
    if not tool_path.exists():
        return ("SKIPPED-NO-FILTER",
                f"anticorpus tool not yet at {tool_path}")
    try:
        result = subprocess.run(
            [sys.executable, str(tool_path), "--check-path", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ("SKIPPED-ERROR", "anticorpus tool timeout")
    except Exception as exc:  # noqa: BLE001 — graceful degrade
        return ("SKIPPED-ERROR", f"anticorpus invoke failed: {exc}")
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if result.returncode != 0:
        return ("PRUNED", f"exit={result.returncode}: {err or out}")
    upper = out.upper()
    if "REJECT" in upper:
        return ("PRUNED", out)
    return ("OK", "")


# ---------------------------------------------------------------------------
# Subcommand: enumerate
# ---------------------------------------------------------------------------

def enumerate_corpus(
    corpus_root: Path,
    *,
    langs: Optional[Iterable[str]] = None,
    max_files: Optional[int] = None,
    anticorpus_tool: Path = DEFAULT_ANTICORPUS_TOOL,
    skip_anticorpus: bool = False,
) -> list[FileEntry]:
    """Walk `corpus_root` and yield FileEntry rows per language.

    Filters:
      - by extension via LANG_EXTS
      - by `langs` allowlist (default: all SUPPORTED_LANGS)
      - by anti-corpus filter (subprocess) unless `skip_anticorpus` is set

    Stable order: lexical by relative path.
    """
    if not corpus_root.exists():
        raise FileNotFoundError(f"corpus root not found: {corpus_root}")
    allow = set(langs) if langs is not None else set(SUPPORTED_LANGS)
    for lang in allow:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"unknown lang in --lang allowlist: {lang!r}")

    entries: list[FileEntry] = []
    # Collect candidate paths first so order is stable + we can budget.
    candidates: list[Path] = []
    for root, dirs, files in os.walk(corpus_root):
        # Skip dot-dirs and common scaffold dirs deterministically.
        dirs[:] = sorted(d for d in dirs
                         if not d.startswith(".")
                         and d not in ("__pycache__", "node_modules",
                                       "target", "vendor", "build", "dist"))
        for fn in sorted(files):
            p = Path(root) / fn
            lang = _classify_lang(p)
            if lang is None or lang not in allow:
                continue
            candidates.append(p)
    candidates.sort()

    for p in candidates:
        if max_files is not None and len(entries) >= max_files:
            break
        lang = _classify_lang(p)
        if lang is None:
            continue  # should not happen given the filter above
        try:
            size = p.stat().st_size
            sha = _sha256_file(p)
        except OSError as exc:
            # Treat as pruned-by-IO, but record the reason so triage is fast.
            entries.append(FileEntry(
                path=str(p),
                rel_path=str(p.relative_to(corpus_root)),
                lang=lang,
                size_bytes=-1,
                sha256="",
                anticorpus_status="SKIPPED-ERROR",
                anticorpus_reason=f"stat/sha failed: {exc}",
            ))
            continue

        if skip_anticorpus:
            ac_status, ac_reason = ("SKIPPED-NO-FILTER", "--skip-anticorpus")
        else:
            ac_status, ac_reason = _anticorpus_check_path(
                p, tool_path=anticorpus_tool
            )

        entries.append(FileEntry(
            path=str(p),
            rel_path=str(p.relative_to(corpus_root)),
            lang=lang,
            size_bytes=size,
            sha256=sha,
            anticorpus_status=ac_status,
            anticorpus_reason=ac_reason,
        ))
    return entries


def write_enumerate_manifest(
    entries: list[FileEntry],
    out_path: Path,
    *,
    corpus_root: Path,
) -> None:
    """Emit a JSON manifest in the schema:

        {"corpus_root": "...",
         "generated_at": "<iso8601>",
         "phase": "v0.2.0-phase1-mocks",
         "total": N,
         "pruned_by_anticorpus": M,
         "entries": [FileEntry asdict, ...]}
    """
    pruned = sum(1 for e in entries if e.anticorpus_status == "PRUNED")
    payload = {
        "corpus_root": str(corpus_root),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        SENTINEL_PHASE: TOOL_PHASE,
        "total": len(entries),
        "pruned_by_anticorpus": pruned,
        "entries": [asdict(e) for e in entries],
    }
    _atomic_write_text(out_path, json.dumps(payload, indent=2, sort_keys=True))


def load_enumerate_manifest(path: Path) -> tuple[Path, list[FileEntry]]:
    """Inverse of write_enumerate_manifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    corpus_root = Path(data["corpus_root"])
    entries = [FileEntry(**e) for e in data["entries"]]
    return corpus_root, entries


# ---------------------------------------------------------------------------
# Subcommand: lint  (Phase 1 = mock dispatcher)
# ---------------------------------------------------------------------------

# Each mock fixture mimics what the real linter autofix loop produces:
# the pre-fix hunk, the post-fix hunk, the rule that triggered, and the
# rule's severity. Realistic enough that the downstream JSONL+dedup+stats
# pipeline exercises every branch. Phase 2 swaps these for subprocess
# captures of the real linter's `--fix` diff.
MOCK_LINTER_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "python": [
        {
            "rule_id": "ruff:B006",
            "severity": "warn",
            "before": "def f(items=[]):\n    items.append(1)\n    return items\n",
            "after":  "def f(items=None):\n    if items is None:\n        items = []\n    items.append(1)\n    return items\n",
            "applicability": "safe",
        },
        {
            "rule_id": "ruff:E722",
            "severity": "block",
            "before": "try:\n    do()\nexcept:\n    pass\n",
            "after":  "try:\n    do()\nexcept Exception as e:\n    log.exception(e)\n    raise\n",
            "applicability": "unsafe",
        },
    ],
    "rust": [
        {
            "rule_id": "clippy:unwrap_used",
            "severity": "block",
            "before": "let v = x.parse::<u32>().unwrap();\n",
            "after":  "let v = x.parse::<u32>()?;\n",
            "applicability": "safe",
        },
    ],
    "typescript": [
        {
            "rule_id": "@typescript-eslint/no-explicit-any",
            "severity": "warn",
            "before": "function f(x: any): any { return x.toString(); }\n",
            "after":  "function f(x: unknown): string { return String(x); }\n",
            "applicability": "unsafe",
        },
    ],
    "go": [
        {
            "rule_id": "golangci:errcheck",
            "severity": "warn",
            "before": "result, _ := loadConfig(path)\nuse(result)\n",
            "after":  "result, err := loadConfig(path)\nif err != nil {\n    return fmt.Errorf(\"loading %s: %w\", path, err)\n}\nuse(result)\n",
            "applicability": "safe",
        },
    ],
    "c": [
        {
            "rule_id": "clang-tidy:cert-str34-c",
            "severity": "block",
            "before": "strcpy(dst, src);\n",
            "after":  "snprintf(dst, sizeof dst, \"%s\", src);\n",
            "applicability": "safe",
        },
    ],
}


def _mock_lint_one_file(entry: FileEntry) -> list[LintRecord]:
    """Return the mock fixtures for a file's language.

    Phase 1: every file in lang L emits len(MOCK_LINTER_FIXTURES[L]) pairs.
    Phase 2 will run the real linter; the function signature is stable.
    """
    cfg = LINTER_DISPATCH[entry.lang]
    citation = cfg["citation"]
    fixtures = MOCK_LINTER_FIXTURES.get(entry.lang, [])
    out: list[LintRecord] = []
    for fx in fixtures:
        out.append(LintRecord(
            rel_path=entry.rel_path,
            lang=entry.lang,
            rule_id=fx["rule_id"],
            severity=fx["severity"],
            before=fx["before"],
            after=fx["after"],
            citation=citation,
            applicability=fx["applicability"],
            source_sha=entry.sha256,
        ))
    return out


def _real_lint_one_file(entry: FileEntry) -> list[LintRecord]:
    """Phase 2 stub. Will subprocess clippy / ruff / golangci / clang-tidy."""
    raise RuntimeError(PHASE2_NOT_READY_MSG)


def run_lint(
    entries: list[FileEntry],
    *,
    apply_real: bool = False,
    safe_only: bool = True,
) -> list[LintRecord]:
    """Drive the per-language linter dispatcher across enumerate entries.

    Skips entries that anti-corpus pruned, or that errored during sha/stat.
    """
    if apply_real:
        # Honour the Phase 2 invariant: error early with a stable message.
        raise RuntimeError(PHASE2_NOT_READY_MSG)
    records: list[LintRecord] = []
    for e in entries:
        if e.anticorpus_status == "PRUNED":
            continue
        if not e.sha256:
            continue
        if e.lang not in LINTER_DISPATCH:
            continue
        recs = _mock_lint_one_file(e)
        if safe_only:
            recs = [r for r in recs if r.applicability == "safe"]
        records.extend(recs)
    return records


def write_lint_jsonl(records: list[LintRecord], out_path: Path) -> int:
    return _atomic_write_jsonl(out_path, (asdict(r) for r in records))


# ---------------------------------------------------------------------------
# Subcommand: treesitter
# ---------------------------------------------------------------------------

# Mock body for the tree-sitter pass. Phase 2 wires py-tree-sitter and
# compiles each rule's .scm; Phase 1 emits a synthetic match per file per
# rule whose `lang` matches. The mock pair embeds the rule's id, severity,
# citation, and a `positive_kind` derived from `positive_query`:
#   "inline"  → rules.toml flagged the positive form as inline-curated
#   "query"   → rules.toml points at a .scm positive query
#   "curated" → fallback when neither file exists (rare; v0.1.3 fills in)
def _positive_kind_for(rule: dict[str, Any], pack_root: Path) -> str:
    pq = rule.get("positive_query", "")
    if pq == "inline":
        return "inline"
    if isinstance(pq, str) and pq.endswith(".scm"):
        candidate = pack_root / pq
        if candidate.exists():
            return "query"
    return "curated"


def _synthetic_anti_hunk(rule: dict[str, Any]) -> str:
    """Phase 1 placeholder for an `.anti.scm` match's source text."""
    return (
        f"// MOCK ANTI MATCH: rule={rule['id']} "
        f"anti_name={rule.get('anti_name', '?')}\n"
    )


def _synthetic_positive_hunk(rule: dict[str, Any]) -> str:
    return (
        f"// MOCK POSITIVE: rule={rule['id']} "
        f"positive_name={rule.get('positive_name', '?')}\n"
    )


def run_treesitter(
    entries: list[FileEntry],
    rules_doc: dict[str, Any],
    *,
    pack_root: Path,
    apply_real: bool = False,
) -> list[TreesitterRecord]:
    """Drive the tree-sitter rule-pack pass over enumerate entries.

    Phase 1: for each (entry, rule) where lang matches, emit one synthetic
    record. Phase 2: load the .scm via py-tree-sitter, parse the file
    bytes, and emit one record per match.
    """
    if apply_real:
        raise RuntimeError(PHASE2_NOT_READY_MSG)
    rules = rules_doc.get("rule", [])
    # Index rules by language for O(1) per-file lookup.
    by_lang: dict[str, list[dict[str, Any]]] = {l: [] for l in SUPPORTED_LANGS}
    for r in rules:
        by_lang[r["lang"]].append(r)

    out: list[TreesitterRecord] = []
    for e in entries:
        if e.anticorpus_status == "PRUNED":
            continue
        if not e.sha256:
            continue
        for r in by_lang.get(e.lang, []):
            citation = r.get("citation", "tier-e-findings.md / (no citation)")
            out.append(TreesitterRecord(
                rel_path=e.rel_path,
                lang=e.lang,
                rule_id=r["id"],
                severity=r["severity"],
                anti_hunk=_synthetic_anti_hunk(r),
                positive_hunk=_synthetic_positive_hunk(r),
                citation=citation,
                source_sha=e.sha256,
                positive_kind=_positive_kind_for(r, pack_root),
            ))
    return out


def write_treesitter_jsonl(records: list[TreesitterRecord],
                           out_path: Path) -> int:
    return _atomic_write_jsonl(out_path, (asdict(r) for r in records))


# ---------------------------------------------------------------------------
# Subcommand: build
# ---------------------------------------------------------------------------

def _weight_for(severity: str) -> float:
    """Return the DPO loss weight for a severity. Unknown → 0.0."""
    return SEVERITY_WEIGHTS.get(severity, 0.0)


def _provenance_for_lint(rec: LintRecord) -> str:
    return f"linter:{rec.rule_id}"


def _provenance_for_treesitter(rec: TreesitterRecord) -> str:
    # If the rule has a linter_equivalent recorded elsewhere we'd surface
    # it here. The rules.toml row carries it; we annotate downstream via
    # combine_with_lint() if the same (lang, source_sha) shows up in
    # both lists.
    return f"treesitter:{rec.rule_id}"


def build_pairs(
    lint_records: list[LintRecord],
    ts_records: list[TreesitterRecord],
) -> list[DPOPair]:
    """Combine lint + tree-sitter records into canonical DPOPair rows.

    Each input record becomes one DPOPair. When a lint record and a
    tree-sitter record share (source_sha, lang) and the tree-sitter rule
    declares the same linter_equivalent, we treat them as cross-validated
    and concatenate provenance tags. For Phase 1 we keep them separate
    rows but mark `source` to capture the join when present.
    """
    out: list[DPOPair] = []

    # Index tree-sitter records by source_sha for cheap cross-ref.
    ts_by_sha: dict[str, list[TreesitterRecord]] = {}
    for r in ts_records:
        ts_by_sha.setdefault(r.source_sha, []).append(r)

    # 1) Emit one DPOPair per lint record.
    for lr in lint_records:
        # If a tree-sitter rule on the same file shares the linter id,
        # tag the provenance accordingly.
        joined = [
            tr.rule_id for tr in ts_by_sha.get(lr.source_sha, [])
            if lr.lang == tr.lang
            # tree-sitter rule id format "R-XX-NNN"; we just record both ids
        ]
        provenance = _provenance_for_lint(lr)
        if joined:
            provenance = (
                f"{provenance}+treesitter:" + "|".join(sorted(set(joined)))
            )
        out.append(DPOPair(
            chosen=lr.after,
            rejected=lr.before,
            rule=lr.rule_id,
            severity=lr.severity,
            lang=lr.lang,
            source_sha=lr.source_sha,
            source=provenance,
            weight=_weight_for(lr.severity),
            citation=lr.citation,
            applicability=lr.applicability,
        ))

    # 2) Emit one DPOPair per tree-sitter record.
    for tr in ts_records:
        out.append(DPOPair(
            chosen=tr.positive_hunk,
            rejected=tr.anti_hunk,
            rule=tr.rule_id,
            severity=tr.severity,
            lang=tr.lang,
            source_sha=tr.source_sha,
            source=_provenance_for_treesitter(tr),
            weight=_weight_for(tr.severity),
            citation=tr.citation,
            applicability="safe" if tr.positive_kind != "curated" else "unsafe",
        ))
    return out


def write_pairs_jsonl(pairs: list[DPOPair], out_path: Path) -> int:
    return _atomic_write_jsonl(out_path, (asdict(p) for p in pairs))


def load_lint_jsonl(path: Path) -> list[LintRecord]:
    rows = _load_jsonl(path)
    out: list[LintRecord] = []
    for r in rows:
        out.append(LintRecord(**r))
    return out


def load_treesitter_jsonl(path: Path) -> list[TreesitterRecord]:
    rows = _load_jsonl(path)
    out: list[TreesitterRecord] = []
    for r in rows:
        out.append(TreesitterRecord(**r))
    return out


def load_pairs_jsonl(path: Path) -> list[DPOPair]:
    rows = _load_jsonl(path)
    out: list[DPOPair] = []
    for r in rows:
        out.append(DPOPair(**r))
    return out


# ---------------------------------------------------------------------------
# Subcommand: dedup
# ---------------------------------------------------------------------------

def _exact_pair_key(p: DPOPair) -> str:
    """Stable SHA-256 fingerprint of (lang, rule, rejected, chosen)."""
    h = hashlib.sha256()
    h.update(p.lang.encode("utf-8"))
    h.update(b"\x00")
    h.update(p.rule.encode("utf-8"))
    h.update(b"\x00")
    h.update(p.rejected.encode("utf-8"))
    h.update(b"\x00")
    h.update(p.chosen.encode("utf-8"))
    return h.hexdigest()


def _minhash_signature(text: str, num_perm: int = 64) -> Any:
    """Build a 64-shingle MinHash signature for `text`. Caller must check
    `_HAS_DATASKETCH` first; this function assumes datasketch is present."""
    assert _HAS_DATASKETCH and MinHash is not None
    m = MinHash(num_perm=num_perm)
    # 5-gram shingles over UTF-8 bytes; works for code identifiers.
    raw = text.encode("utf-8")
    if len(raw) < 5:
        m.update(raw)
    else:
        for i in range(0, len(raw) - 4):
            m.update(raw[i:i + 5])
    return m


def dedup_pairs(
    pairs: list[DPOPair],
    *,
    enable_minhash: bool = True,
    minhash_threshold: float = 0.85,
) -> tuple[list[DPOPair], dict[str, Any]]:
    """Return (kept_pairs, stats). Exact dedup always runs; MinHash runs
    when `datasketch` is importable AND `enable_minhash` is True.

    stats keys:
        input_count, exact_dupes_removed, minhash_dupes_removed,
        kept_count, minhash_enabled, minhash_threshold, advisories[]
    """
    stats: dict[str, Any] = {
        "input_count": len(pairs),
        "exact_dupes_removed": 0,
        "minhash_dupes_removed": 0,
        "kept_count": 0,
        "minhash_enabled": False,
        "minhash_threshold": minhash_threshold,
        "advisories": [],
    }

    # 1) Exact dedup by stable fingerprint.
    seen: set[str] = set()
    after_exact: list[DPOPair] = []
    for p in pairs:
        key = _exact_pair_key(p)
        if key in seen:
            stats["exact_dupes_removed"] += 1
            continue
        seen.add(key)
        after_exact.append(p)

    # 2) MinHash near-dup removal (within same lang+rule cohort).
    if enable_minhash and _HAS_DATASKETCH:
        stats["minhash_enabled"] = True
        kept: list[DPOPair] = []
        # bucket by (lang, rule) — only candidates within a bucket can be
        # near-dupes for our purposes; this caps LSH cost.
        buckets: dict[tuple[str, str], list[DPOPair]] = {}
        for p in after_exact:
            buckets.setdefault((p.lang, p.rule), []).append(p)
        for _, bucket in buckets.items():
            lsh = MinHashLSH(threshold=minhash_threshold, num_perm=64)
            survivors: list[DPOPair] = []
            for idx, p in enumerate(bucket):
                key = f"{idx}"
                sig = _minhash_signature(p.rejected + "\n" + p.chosen)
                # Query before insert — if anything hits, treat as dup.
                hits = lsh.query(sig)
                if hits:
                    stats["minhash_dupes_removed"] += 1
                    continue
                lsh.insert(key, sig)
                survivors.append(p)
            kept.extend(survivors)
        out = kept
    else:
        if enable_minhash and not _HAS_DATASKETCH:
            stats["advisories"].append(
                f"{SENTINEL_MINHASH_FOLLOWUP}: datasketch not installed; "
                "exact-SHA dedup only. Install `datasketch` for MinHash."
            )
        out = after_exact

    stats["kept_count"] = len(out)
    return out, stats


# ---------------------------------------------------------------------------
# Subcommand: stats
# ---------------------------------------------------------------------------

def compute_stats(pairs: list[DPOPair]) -> dict[str, Any]:
    """Aggregate counts by lang × severity × rule. Embeds the no-LLM-judge
    sentinel and severity-weight policy reference.
    """
    by_lang: dict[str, int] = {}
    by_severity: dict[str, int] = {"block": 0, "warn": 0, "info": 0}
    by_rule: dict[str, int] = {}
    by_lang_severity: dict[str, dict[str, int]] = {}
    weight_sum: float = 0.0
    defects: list[str] = []

    for p in pairs:
        by_lang[p.lang] = by_lang.get(p.lang, 0) + 1
        if p.severity in by_severity:
            by_severity[p.severity] += 1
        else:
            defects.append(f"unknown severity in row: {p.severity!r}")
        by_rule[p.rule] = by_rule.get(p.rule, 0) + 1
        by_lang_severity.setdefault(p.lang, {"block": 0, "warn": 0, "info": 0})
        if p.severity in by_lang_severity[p.lang]:
            by_lang_severity[p.lang][p.severity] += 1
        weight_sum += p.weight
        if p.weight == 0.0:
            defects.append(
                f"zero-weight row (severity={p.severity!r}, rule={p.rule})"
            )

    return {
        "total_pairs": len(pairs),
        "by_lang": by_lang,
        "by_severity": by_severity,
        "by_lang_severity": by_lang_severity,
        "by_rule": by_rule,
        "weight_sum": weight_sum,
        "weight_policy": dict(SEVERITY_WEIGHTS),
        "weight_policy_spec": "papers/spec-treesitter-rule-pack.md §6.1",
        "defects": sorted(set(defects)),
        SENTINEL_NO_LLM_JUDGE: True,
        SENTINEL_PHASE: TOOL_PHASE,
        "decision_anchor": "D-013 (tree-sitter rule pack default, no LLM judge)",
        "yield_target": "2-5M pairs per tier-e-findings.md Part 2 §linter-driven",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }


def write_stats_json(stats: dict[str, Any], out_path: Path) -> None:
    _atomic_write_text(out_path, json.dumps(stats, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------

EPILOG = """\
Cross-links
-----------
- papers/spec-treesitter-rule-pack.md   — severity model + §6.1 DPO weight policy
- papers/tier-e-findings.md Part 2      — linter coverage + ~2-5M yield estimate
- papers/tier-e-findings.md Part 3      — anti-corpus exclusion list
- papers/plan-decisions-pending.md      — D-013 (no LLM judge); D-016 (SE torrent cutoff)
- papers/plan-runbook-v0.1.3.md         — Stack v2 fetch via mac-exec HF bridge
- ROADMAP.md §2                         — v0.2.0 cross-cutting infra (this tool)
- tool/treesitter_rule_pack/rules.toml  — 50 rules × 5 langs (v1 pack)
- tool/anticorpus_filter.py             — sister tool (parallel build)

Decision default: D-013 — tree-sitter rule pack v1 is the deterministic judge.
LLM-as-judge is forever-blocked for v1.0 (Shumailov 2024 model collapse).

Yield target: 2-5M dedup-survived pairs (HIGH confidence per Tier E Part 2).

Phase 1 (v0.2.0): mocks only. Run --selftest to verify the pipeline shape.
Phase 2: real linter invocation lights up when Stack v2 corpus lands.
"""


def _add_common_args(p: argparse.ArgumentParser) -> None:
    """Args that any subcommand may take."""
    p.add_argument(
        "--apply-real",
        action="store_true",
        help=("Phase 2 only — invoke real linters / tree-sitter. "
              "Errors at v0.2.0 with a stable message."),
    )


def _cmd_enumerate(args: argparse.Namespace) -> int:
    corpus_root = Path(args.corpus_root).resolve()
    out_path = Path(args.out) if args.out else (
        DEFAULT_RUNS_DIR / f"enumerate.{_today_iso()}.json"
    )
    langs = args.lang.split(",") if args.lang else None
    entries = enumerate_corpus(
        corpus_root,
        langs=langs,
        max_files=args.max_files,
        anticorpus_tool=Path(args.anticorpus_tool) if args.anticorpus_tool
                        else DEFAULT_ANTICORPUS_TOOL,
        skip_anticorpus=args.skip_anticorpus,
    )
    write_enumerate_manifest(entries, out_path, corpus_root=corpus_root)
    pruned = sum(1 for e in entries if e.anticorpus_status == "PRUNED")
    sys.stdout.write(
        f"enumerate: {len(entries)} files ({pruned} pruned by anti-corpus) "
        f"-> {out_path}\n"
    )
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    enum_path = Path(args.enumerated)
    _, entries = load_enumerate_manifest(enum_path)
    out_path = Path(args.out) if args.out else (
        DEFAULT_RUNS_DIR / f"lint.{_today_iso()}.jsonl"
    )
    try:
        records = run_lint(
            entries,
            apply_real=args.apply_real,
            safe_only=not args.include_unsafe_fixes,
        )
    except RuntimeError as exc:
        sys.stderr.write(f"lint: {exc}\n")
        return 2
    n = write_lint_jsonl(records, out_path)
    sys.stdout.write(f"lint: {n} records -> {out_path}\n")
    return 0


def _cmd_treesitter(args: argparse.Namespace) -> int:
    enum_path = Path(args.enumerated)
    _, entries = load_enumerate_manifest(enum_path)
    rules_path = Path(args.rules) if args.rules else DEFAULT_RULES_TOML
    rules_doc = load_rules(rules_path)
    out_path = Path(args.out) if args.out else (
        DEFAULT_RUNS_DIR / f"treesitter.{_today_iso()}.jsonl"
    )
    try:
        records = run_treesitter(
            entries,
            rules_doc,
            pack_root=rules_path.parent,
            apply_real=args.apply_real,
        )
    except RuntimeError as exc:
        sys.stderr.write(f"treesitter: {exc}\n")
        return 2
    n = write_treesitter_jsonl(records, out_path)
    sys.stdout.write(f"treesitter: {n} records -> {out_path}\n")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    lint_path = Path(args.lint)
    ts_path = Path(args.treesitter)
    lint_records = load_lint_jsonl(lint_path)
    ts_records = load_treesitter_jsonl(ts_path)
    pairs = build_pairs(lint_records, ts_records)
    out_path = Path(args.out) if args.out else (
        DEFAULT_RUNS_DIR / f"dpo_pairs.{_today_iso()}.jsonl"
    )
    n = write_pairs_jsonl(pairs, out_path)
    sys.stdout.write(f"build: {n} pairs -> {out_path}\n")
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    in_path = Path(args.input)
    pairs = load_pairs_jsonl(in_path)
    kept, stats = dedup_pairs(
        pairs,
        enable_minhash=not args.no_minhash,
        minhash_threshold=args.minhash_threshold,
    )
    out_path = Path(args.out) if args.out else (
        in_path.with_suffix(".dedup.jsonl")
    )
    n = write_pairs_jsonl(kept, out_path)
    sys.stdout.write(
        f"dedup: input={stats['input_count']} "
        f"exact_dropped={stats['exact_dupes_removed']} "
        f"minhash_dropped={stats['minhash_dupes_removed']} "
        f"kept={n} -> {out_path}\n"
    )
    if stats["advisories"]:
        for adv in stats["advisories"]:
            sys.stderr.write(f"[advisory] {adv}\n")
    # Drop a sidecar stats file for the dedup pass for triage.
    sidecar = out_path.with_suffix(".dedupstats.json")
    _atomic_write_text(sidecar, json.dumps(stats, indent=2, sort_keys=True))
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    in_path = Path(args.input)
    pairs = load_pairs_jsonl(in_path)
    stats = compute_stats(pairs)
    out_path = Path(args.out) if args.out else (
        in_path.with_suffix(".stats.json")
    )
    write_stats_json(stats, out_path)
    sys.stdout.write(
        f"stats: total_pairs={stats['total_pairs']} "
        f"weight_sum={stats['weight_sum']:.2f} -> {out_path}\n"
    )
    if stats["defects"]:
        sys.stderr.write(
            f"[stats] {len(stats['defects'])} defects logged in {out_path}\n"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_dpo_pairs.py",
        description=(
            "DPO preference-pair pipeline driver for the hexa-forge `code` "
            "verb (v0.2.0 cross-cutting infra). Tree-sitter rule pack + "
            "linter-autofix → DPO pairs. NO LLM judge (D-013 / Shumailov "
            "2024)."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--selftest",
        action="store_true",
        help="Run the inline self-test suite and exit.",
    )

    sub = p.add_subparsers(dest="cmd", metavar="<subcommand>")

    pe = sub.add_parser(
        "enumerate",
        help="Walk a corpus root and emit a per-language file manifest.",
        description=(
            "Walk `corpus/<verb>/pretrain-bias/stack-v2/` (or a sample dir) "
            "and emit (path, lang, size, sha256, anticorpus_status) rows."
        ),
    )
    pe.add_argument("--corpus-root", required=True,
                    help="root directory to walk")
    pe.add_argument("--out", default=None,
                    help="output JSON manifest path "
                         "(default: runs/enumerate.<date>.json)")
    pe.add_argument("--lang", default=None,
                    help=("comma-separated subset of "
                          + ",".join(SUPPORTED_LANGS)))
    pe.add_argument("--max-files", type=int, default=None,
                    help="cap the enumerated file count (testing)")
    pe.add_argument("--anticorpus-tool", default=None,
                    help="path to tool/anticorpus_filter.py "
                         "(default: repo-local)")
    pe.add_argument("--skip-anticorpus", action="store_true",
                    help="bypass the anti-corpus filter (testing only)")
    pe.set_defaults(func=_cmd_enumerate)

    pl = sub.add_parser(
        "lint",
        help="Dispatch the per-language linter (mock at Phase 1).",
        description=(
            "For each entry in the enumerate manifest, invoke the "
            "language's linter in --fix mode. Phase 1 = mocked from "
            "MOCK_LINTER_FIXTURES; Phase 2 = real subprocess."
        ),
    )
    pl.add_argument("--enumerated", required=True,
                    help="enumerate manifest JSON path")
    pl.add_argument("--out", default=None,
                    help="output JSONL (default: runs/lint.<date>.jsonl)")
    pl.add_argument("--include-unsafe-fixes", action="store_true",
                    help="include unsafe-tier autofixes (default: safe only)")
    _add_common_args(pl)
    pl.set_defaults(func=_cmd_lint)

    pt = sub.add_parser(
        "treesitter",
        help="Run the tree-sitter rule pack over enumerated files.",
        description=(
            "Load `tool/treesitter_rule_pack/rules.toml` and run each "
            "rule's anti.scm query. Pair each match with the rule's "
            "positive.scm match (or curated `inline` positive). Phase 1 "
            "= synthetic mock match per (file, rule); Phase 2 = real "
            "py-tree-sitter parse."
        ),
    )
    pt.add_argument("--enumerated", required=True)
    pt.add_argument("--rules", default=None,
                    help=f"rules.toml path (default: {DEFAULT_RULES_TOML})")
    pt.add_argument("--out", default=None,
                    help="output JSONL "
                         "(default: runs/treesitter.<date>.jsonl)")
    _add_common_args(pt)
    pt.set_defaults(func=_cmd_treesitter)

    pb = sub.add_parser(
        "build",
        help="Combine lint + treesitter outputs into canonical DPO JSONL.",
        description=(
            "Read the lint.jsonl and treesitter.jsonl outputs, attach "
            "severity-weight per spec §6.1, and emit one canonical row "
            "per pair with provenance + citation."
        ),
    )
    pb.add_argument("--lint", required=True,
                    help="lint JSONL from the `lint` subcommand")
    pb.add_argument("--treesitter", required=True,
                    help="treesitter JSONL from the `treesitter` subcommand")
    pb.add_argument("--out", default=None,
                    help="output JSONL "
                         "(default: runs/dpo_pairs.<date>.jsonl)")
    pb.set_defaults(func=_cmd_build)

    pd = sub.add_parser(
        "dedup",
        help="Remove exact + near duplicate DPO pairs.",
        description=(
            "Exact dedup via SHA-256(lang|rule|rejected|chosen) always "
            "runs. MinHash near-dedup runs when `datasketch` is "
            "importable; otherwise emits a __MINHASH_FOLLOWUP__ advisory."
        ),
    )
    pd.add_argument("--in", dest="input", required=True,
                    help="input JSONL of DPO pairs")
    pd.add_argument("--out", default=None,
                    help="output JSONL (default: <input>.dedup.jsonl)")
    pd.add_argument("--no-minhash", action="store_true",
                    help="disable MinHash near-dedup")
    pd.add_argument("--minhash-threshold", type=float, default=0.85,
                    help="MinHash Jaccard threshold (default 0.85)")
    pd.set_defaults(func=_cmd_dedup)

    ps = sub.add_parser(
        "stats",
        help="Aggregate pair counts by lang × severity × rule.",
        description=(
            "Emit a JSON stats file containing the no-LLM-judge sentinel, "
            "the severity-weight policy, per-(lang, severity, rule) "
            "counts, and any schema defects detected in the input."
        ),
    )
    ps.add_argument("--in", dest="input", required=True,
                    help="input JSONL of DPO pairs")
    ps.add_argument("--out", default=None,
                    help="output JSON (default: <input>.stats.json)")
    ps.set_defaults(func=_cmd_stats)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    return int(args.func(args))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _build_mock_corpus(td: Path) -> Path:
    """Synthesise a 6-file mock corpus covering all 5 langs + 1 anti-corpus
    decoy. Returns the corpus root path."""
    root = td / "mock_corpus"
    (root / "py").mkdir(parents=True)
    (root / "rs").mkdir()
    (root / "ts").mkdir()
    (root / "go").mkdir()
    (root / "c").mkdir()
    (root / "py" / "demo.py").write_text(
        "def f(items=[]):\n    items.append(1)\n    return items\n",
        encoding="utf-8",
    )
    (root / "py" / "another.py").write_text(
        "x = 1\n",
        encoding="utf-8",
    )
    (root / "rs" / "demo.rs").write_text(
        "fn main() { let v = \"3\".parse::<u32>().unwrap(); }\n",
        encoding="utf-8",
    )
    (root / "ts" / "demo.ts").write_text(
        "function f(x: any): any { return x; }\n",
        encoding="utf-8",
    )
    (root / "go" / "demo.go").write_text(
        "package main\nfunc main() { result, _ := load() ; _ = result }\n",
        encoding="utf-8",
    )
    (root / "c" / "demo.c").write_text(
        "#include <string.h>\nvoid copy(char* d, char* s){ strcpy(d, s); }\n",
        encoding="utf-8",
    )
    return root


def _make_fake_anticorpus(td: Path, *, reject_path_substr: str) -> Path:
    """Write a tiny stand-in for `tool/anticorpus_filter.py` that rejects
    paths whose string contains `reject_path_substr` and accepts the rest.
    """
    p = td / "fake_anticorpus.py"
    body = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "p = sys.argv[sys.argv.index('--check-path') + 1] "
        "if '--check-path' in sys.argv else ''\n"
        f"sub = {reject_path_substr!r}\n"
        "if sub and sub in p:\n"
        "    print('REJECT: matches anti-corpus rule')\n"
        "    sys.exit(0)\n"
        "print('OK')\n"
        "sys.exit(0)\n"
    )
    p.write_text(body, encoding="utf-8")
    return p


def _selftest() -> int:  # noqa: C901 — long-but-straight-line test
    """Inline self-test. Verifies all six subcommands on mock fixtures.

    Suite (per acceptance bars in the build prompt):
      1. enumerate returns the right schema + anti-corpus integration works
      2. lint produces (before, after, rule_id, severity) tuples
      3. treesitter pulls positive + negative .scm pairings from rules.toml
      4. build emits valid JSONL with chosen/rejected/rule keys
      5. dedup removes exact dups + reports MinHash status
      6. stats produces correct counts + embeds __NO_LLM_JUDGE__ sentinel
    """
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        runs = td / "runs"
        runs.mkdir()
        corpus = _build_mock_corpus(td)
        fake_ac = _make_fake_anticorpus(td, reject_path_substr="another.py")

        # --- 1. enumerate ---------------------------------------------------
        entries = enumerate_corpus(
            corpus,
            langs=SUPPORTED_LANGS,
            anticorpus_tool=fake_ac,
        )
        # Expected: 6 entries total; 1 pruned by anti-corpus (another.py).
        if len(entries) != 6:
            failures.append(
                f"enumerate count {len(entries)} != 6 expected"
            )
        langs_seen = {e.lang for e in entries}
        if langs_seen != set(SUPPORTED_LANGS):
            failures.append(
                f"enumerate did not cover all langs; saw {langs_seen}"
            )
        pruned = [e for e in entries if e.anticorpus_status == "PRUNED"]
        if len(pruned) != 1:
            failures.append(
                f"enumerate pruned count {len(pruned)} != 1 expected"
            )
        elif "another.py" not in pruned[0].rel_path:
            failures.append(
                f"enumerate pruned wrong file: {pruned[0].rel_path}"
            )
        # Every kept entry must have a non-empty sha256 + matching size > 0.
        for e in entries:
            if e.anticorpus_status == "OK":
                if not e.sha256:
                    failures.append(f"enumerate row missing sha: {e.rel_path}")
                if e.size_bytes <= 0:
                    failures.append(
                        f"enumerate row missing size: {e.rel_path}"
                    )
        # Anti-corpus graceful-degrade path: missing tool → SKIPPED-NO-FILTER.
        ghost_entries = enumerate_corpus(
            corpus,
            anticorpus_tool=td / "nonexistent.py",
        )
        if not all(g.anticorpus_status == "SKIPPED-NO-FILTER"
                   for g in ghost_entries):
            failures.append(
                "anticorpus graceful-degrade path did not fire; "
                "expected all rows SKIPPED-NO-FILTER"
            )
        # Manifest round-trip.
        enum_path = runs / "enumerate.json"
        write_enumerate_manifest(entries, enum_path, corpus_root=corpus)
        _, round_trip = load_enumerate_manifest(enum_path)
        if [e.sha256 for e in round_trip] != [e.sha256 for e in entries]:
            failures.append("enumerate manifest round-trip lost data")

        # --- 2. lint --------------------------------------------------------
        lint_records = run_lint(entries, apply_real=False, safe_only=False)
        # 5 kept-good entries (anti-corpus pruned 'another.py'); per-lang
        # mock fixture counts: py=2, rs=1, ts=1, go=1, c=1 → 6 records.
        # We have 1 .py file kept (demo.py) → 2 mock records;
        # rs=1 (1 rec), ts=1 (1 rec), go=1 (1 rec), c=1 (1 rec) → 6 total.
        if len(lint_records) != 6:
            failures.append(
                f"lint records {len(lint_records)} != 6 expected"
            )
        # Each lint record has the four schema fields.
        for r in lint_records:
            if not r.before or not r.after:
                failures.append(
                    f"lint record missing before/after for rule {r.rule_id}"
                )
            if r.rule_id == "":
                failures.append("lint record missing rule_id")
            if r.severity not in SEVERITY_WEIGHTS:
                failures.append(
                    f"lint record bad severity: {r.severity}"
                )
        # safe_only filter test: re-run with safe_only=True; unsafe rows drop.
        lint_safe = run_lint(entries, apply_real=False, safe_only=True)
        if len(lint_safe) >= len(lint_records):
            failures.append(
                "safe_only=True did not drop any unsafe rows; "
                "fixture coverage likely regressed"
            )
        # --apply-real path errors cleanly.
        try:
            run_lint(entries, apply_real=True)
            failures.append("lint --apply-real should have raised")
        except RuntimeError as exc:
            if "Phase 2" not in str(exc):
                failures.append(
                    f"lint --apply-real raised wrong message: {exc}"
                )

        lint_jsonl = runs / "lint.jsonl"
        write_lint_jsonl(lint_records, lint_jsonl)
        if not lint_jsonl.exists():
            failures.append("lint JSONL not written")

        # --- 3. treesitter --------------------------------------------------
        if not DEFAULT_RULES_TOML.exists():
            failures.append(
                f"rules.toml missing at {DEFAULT_RULES_TOML}; "
                "rule-pack tree-sitter integration cannot self-test"
            )
            rules_doc = {"rule": []}
        else:
            rules_doc = load_rules(DEFAULT_RULES_TOML)
            if len(rules_doc.get("rule", [])) != 50:
                failures.append(
                    f"rules.toml has {len(rules_doc.get('rule', []))} "
                    f"rules; expected 50 (v1 pack)"
                )

        ts_records = run_treesitter(
            entries, rules_doc,
            pack_root=DEFAULT_RULES_TOML.parent,
            apply_real=False,
        )
        # 5 kept files × (10 rules per language) = 50 ts records (each file
        # only joins on rules whose lang matches). The mock corpus has one
        # file per supported lang (after anti-corpus pruning), so:
        #   demo.py * 10 PY rules = 10
        #   demo.rs * 10 RS rules = 10
        #   demo.ts * 10 TS rules = 10
        #   demo.go * 10 GO rules = 10
        #   demo.c  * 10 C rules  = 10
        # = 50 total.
        if rules_doc.get("rule"):
            if len(ts_records) != 50:
                failures.append(
                    f"treesitter records {len(ts_records)} != 50 expected "
                    "(5 langs × 10 rules each, one mock file per lang)"
                )
        # Severity coverage: all three severities must appear in the output.
        severities_seen = {r.severity for r in ts_records}
        if severities_seen and severities_seen != {"block", "warn", "info"}:
            failures.append(
                f"treesitter did not surface all severities; "
                f"saw {severities_seen}"
            )
        # positive_kind coverage: at least "inline" should appear given
        # the rules.toml has many positive_query = "inline" rows.
        positive_kinds = {r.positive_kind for r in ts_records}
        if ts_records and "inline" not in positive_kinds:
            failures.append(
                f"treesitter positive_kind never 'inline'; saw {positive_kinds}"
            )
        # --apply-real errors cleanly here too.
        try:
            run_treesitter(entries, rules_doc,
                           pack_root=DEFAULT_RULES_TOML.parent,
                           apply_real=True)
            failures.append("treesitter --apply-real should have raised")
        except RuntimeError as exc:
            if "Phase 2" not in str(exc):
                failures.append(
                    f"treesitter --apply-real raised wrong message: {exc}"
                )

        ts_jsonl = runs / "treesitter.jsonl"
        write_treesitter_jsonl(ts_records, ts_jsonl)

        # --- 4. build -------------------------------------------------------
        pairs = build_pairs(lint_records, ts_records)
        if len(pairs) != len(lint_records) + len(ts_records):
            failures.append(
                f"build pairs {len(pairs)} != "
                f"{len(lint_records) + len(ts_records)} expected"
            )
        for p in pairs:
            for required_key in ("chosen", "rejected", "rule",
                                 "severity", "lang"):
                val = getattr(p, required_key, None)
                if val in (None, ""):
                    failures.append(
                        f"build pair missing key {required_key}"
                    )
            if p.weight != SEVERITY_WEIGHTS.get(p.severity, 0.0):
                failures.append(
                    f"build pair weight {p.weight} != "
                    f"{SEVERITY_WEIGHTS.get(p.severity)} for severity "
                    f"{p.severity!r}"
                )
        pairs_jsonl = runs / "dpo_pairs.jsonl"
        write_pairs_jsonl(pairs, pairs_jsonl)
        # Round-trip: load_pairs_jsonl returns the same shape.
        reread = load_pairs_jsonl(pairs_jsonl)
        if len(reread) != len(pairs):
            failures.append(
                f"build round-trip lost rows: "
                f"{len(reread)} vs {len(pairs)}"
            )
        # Provenance: cross-validated rows should mention 'treesitter'
        # joined to a linter rule. At least one lint row's source field
        # should contain '+treesitter:' because the mock corpus shares
        # SHAs across the lint+treesitter passes.
        joined_rows = [p for p in pairs if "+treesitter:" in p.source]
        if not joined_rows:
            failures.append(
                "build did not cross-join any lint↔treesitter rows "
                "(provenance test)"
            )

        # --- 5. dedup -------------------------------------------------------
        # Inject one exact duplicate of the first pair.
        dup_pairs = list(pairs) + [pairs[0]]
        kept, dedup_stats = dedup_pairs(dup_pairs, enable_minhash=True)
        if dedup_stats["exact_dupes_removed"] != 1:
            failures.append(
                f"dedup exact removed {dedup_stats['exact_dupes_removed']} "
                "!= 1 expected"
            )
        if dedup_stats["kept_count"] != len(pairs):
            failures.append(
                f"dedup kept_count {dedup_stats['kept_count']} != "
                f"{len(pairs)} expected"
            )
        # MinHash status reporting: when datasketch is absent, an advisory
        # MUST mention the SENTINEL_MINHASH_FOLLOWUP tag. When present, no
        # advisory is required (but `minhash_enabled` should be True).
        if _HAS_DATASKETCH:
            if not dedup_stats["minhash_enabled"]:
                failures.append(
                    "dedup minhash_enabled False but datasketch present"
                )
        else:
            if dedup_stats["minhash_enabled"]:
                failures.append(
                    "dedup minhash_enabled True but datasketch absent"
                )
            joined = " ".join(dedup_stats["advisories"])
            if SENTINEL_MINHASH_FOLLOWUP not in joined:
                failures.append(
                    f"dedup missing {SENTINEL_MINHASH_FOLLOWUP} advisory "
                    f"when datasketch absent; advisories={dedup_stats['advisories']}"
                )

        # --- 6. stats -------------------------------------------------------
        stats = compute_stats(pairs)
        if stats["total_pairs"] != len(pairs):
            failures.append(
                f"stats total_pairs {stats['total_pairs']} != "
                f"{len(pairs)} expected"
            )
        if stats.get(SENTINEL_NO_LLM_JUDGE) is not True:
            failures.append(
                f"stats missing or wrong {SENTINEL_NO_LLM_JUDGE} sentinel"
            )
        if stats.get(SENTINEL_PHASE) != TOOL_PHASE:
            failures.append(
                f"stats missing {SENTINEL_PHASE}={TOOL_PHASE} sentinel"
            )
        # by_lang totals must sum to total_pairs.
        if sum(stats["by_lang"].values()) != stats["total_pairs"]:
            failures.append("stats by_lang sum mismatch")
        # severity weight policy must match the canonical map.
        if stats["weight_policy"] != SEVERITY_WEIGHTS:
            failures.append(
                f"stats weight_policy {stats['weight_policy']} != "
                f"{SEVERITY_WEIGHTS}"
            )
        # Round-trip stats JSON write/read.
        stats_path = runs / "dpo_pairs.stats.json"
        write_stats_json(stats, stats_path)
        try:
            reloaded = json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"stats JSON write produced invalid JSON: {exc}")
            reloaded = {}
        if reloaded.get(SENTINEL_NO_LLM_JUDGE) is not True:
            failures.append(
                f"stats round-trip lost {SENTINEL_NO_LLM_JUDGE} sentinel"
            )

        # --- 7. CLI surface smoke checks -----------------------------------
        parser = build_parser()
        # Help renders + epilog mentions key cross-links.
        help_text = parser.format_help()
        for needle in (
            "spec-treesitter-rule-pack.md",
            "tier-e-findings.md Part 2",
            "ROADMAP.md §2",
            "D-013",
        ):
            if needle not in help_text:
                failures.append(f"--help epilogue missing: {needle}")

    if failures:
        sys.stderr.write("build_dpo_pairs.py SELFTEST FAILED:\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        sys.stdout.write(f"{SELFTEST_FAIL_TAG}\n")
        return 1
    sys.stdout.write(f"{SELFTEST_PASS_TAG}\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit(_selftest())
    sys.exit(main())
