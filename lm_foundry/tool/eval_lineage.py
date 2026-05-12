#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""eval_lineage.py — DuckDB-backed lineage store for hexa-forge eval runs.

Phase v0.2.0 cross-cutting infra deliverable. Persists every
`tool/run_eval.py` invocation as an auditable row keyed on
(model_sha, eval_set_sha, config_sha) so cold-bench / SFT-checkpoint /
DPO-run / hexa-codex T4-PR contributions are reproducible end-to-end.

CONTRACT (cross-link)
    - Storage backend:    DuckDB (per plan-decisions-pending.md D-010)
    - Run-eval emitter:   tool/run_eval.py — produces plan.json /
                          scores.json / tasks.jsonl / summary.md per run.
    - PR emitter:         tool/emit_t4.py — writes outbox/hexa-codex/<verb>/.
                          Each emitted PR draft links back to a run_id via
                          `link-pr`.
    - Upstream gate:      ROADMAP.md §2 — v1.0.0 acceptance gate ⑬
                          (≥ 5 PRs landed in hexa-codex; the `gate-check`
                          subcommand reports this directly).
    - Feedback routing:   papers/plan-feedback-channel-ops.md (M-005).

SCHEMA (4 tables — DuckDB DDL stored as a single string constant below)
    forge_runs           one row per run_eval invocation
    forge_run_scores     per-family pass-rates rolled up from scores.json
    forge_run_tasks      per-task verdicts (sparse: FAIL/ERROR + 10% PASS)
    forge_upstream_prs   link from a forge run to an outbox/hexa-codex PR

SUBCOMMANDS
    init           create the DB file and apply schema (idempotent)
    ingest         read a runs/<spec>/<run_id>/ directory and upsert rows
    link-pr        link a hexa-codex PR draft to a run_id
    query          pretty-print matching forge_runs rows + linked scores
    gate-check     emit JSON {landed_pr_count, v1.0.0_gate_13_met, ...}
    audit          emit a Markdown audit report for a single run
    --selftest     in-memory round-trip across the full surface

OUT OF SCOPE (per v0.2.0 brief)
    - No bulk dedup / compression (defer to v0.2.1).
    - No alternative backends (D-010 is DuckDB only).
    - Pass-rate on `forge_runs` is write-once: ingest does NOT overwrite
      a non-NULL value (idempotent re-ingest after edits is safe).

DEPENDENCIES
    Python 3.11+ stdlib + duckdb. The duckdb module is soft-imported;
    every command handler returns a helpful error if it is missing.
"""
from __future__ import annotations

# NOTE: a sibling `tool/tokenize.py` shadows the stdlib `tokenize` module
# when ANY tool in `tool/` is launched as a script (Python prepends the
# script's directory to sys.path). The shadow propagates through
# `dataclasses` -> `inspect` -> `linecache` -> `tokenize` and crashes import.
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
import random
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import duckdb  # type: ignore
except ImportError:  # pragma: no cover - duckdb is a hard dep at v0.2.0
    duckdb = None  # type: ignore[assignment]


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH: Path = REPO_ROOT / "runs" / "eval_lineage.duckdb"

# Sparse-storage sampling rate for PASS verdicts in forge_run_tasks. FAIL +
# ERROR are always retained; PASS is sampled at this fraction. Rationale:
# a 1000-task spec at 80% PASS would otherwise persist 800 redundant
# success rows; FAIL rows are the audit signal worth keeping verbatim.
PASS_SAMPLE_RATE: float = 0.10

# Canonical spec / verb / verdict / status enums. Validated at ingest time
# so a stray scores.json with a typo does not silently insert garbage.
KNOWN_SPECS: frozenset[str] = frozenset({
    "hexa-eval", "5nl-eval", "db-eval",
    "firmware-eval", "frontend-eval", "safety-eval",
})

KNOWN_VERBS: frozenset[str] = frozenset({
    "train_cost", "infer_cost", "quality_scale", "safety",
    "alignment", "adversarial", "interpret", "rlhf",
    "eval", "agent_serving", "deploy",
})

KNOWN_FALSIFIERS: frozenset[str] = frozenset({
    "F-CODEX-1", "F-CODEX-2", "F-CODEX-3", "F-CODEX-4", "cross-cutter",
})

KNOWN_RUN_STATUS: frozenset[str] = frozenset({
    "pending", "running", "completed", "failed", "aborted",
})

KNOWN_VERDICTS: frozenset[str] = frozenset({
    "pass", "fail", "error", "skipped",
})

# v1.0.0 forge gate ⑬: ≥ 5 PRs landed in hexa-codex.
GATE_13_MIN_LANDED_PRS: int = 5


# ---------------------------------------------------------------------------
# Schema (single source of truth)
# ---------------------------------------------------------------------------

SCHEMA_SQL: str = """
-- forge_runs: one row per `tool/run_eval.py` invocation.
CREATE TABLE IF NOT EXISTS forge_runs (
    run_id          VARCHAR PRIMARY KEY,
    spec            VARCHAR NOT NULL,
    model_name      VARCHAR NOT NULL,
    model_sha       VARCHAR,
    eval_set_sha    VARCHAR NOT NULL,
    config_sha      VARCHAR NOT NULL,
    forge_commit    VARCHAR NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    pass_rate       DOUBLE,
    status          VARCHAR NOT NULL,
    notes           VARCHAR
);

-- forge_run_scores: per-family pass-rates.
CREATE TABLE IF NOT EXISTS forge_run_scores (
    run_id      VARCHAR REFERENCES forge_runs(run_id),
    family      VARCHAR NOT NULL,
    pass_rate   DOUBLE NOT NULL,
    task_count  INTEGER NOT NULL,
    pass_count  INTEGER NOT NULL,
    bar         DOUBLE,
    bar_met     BOOLEAN,
    PRIMARY KEY (run_id, family)
);

-- forge_run_tasks: per-task verdicts (sparse — all FAIL/ERROR + 10% PASS).
CREATE TABLE IF NOT EXISTS forge_run_tasks (
    run_id      VARCHAR REFERENCES forge_runs(run_id),
    task_id     VARCHAR NOT NULL,
    family      VARCHAR NOT NULL,
    verdict     VARCHAR NOT NULL,
    score       DOUBLE,
    output_sha  VARCHAR,
    error_class VARCHAR,
    PRIMARY KEY (run_id, task_id)
);

-- forge_upstream_prs: link table — forge run -> hexa-codex PR draft.
CREATE TABLE IF NOT EXISTS forge_upstream_prs (
    pr_id         VARCHAR PRIMARY KEY,
    run_id        VARCHAR REFERENCES forge_runs(run_id),
    verb          VARCHAR NOT NULL,
    outbox_path   VARCHAR NOT NULL,
    falsifier     VARCHAR,
    submitted_at  TIMESTAMP,
    landed_at     TIMESTAMP,
    notes         VARCHAR
);
"""


# ---------------------------------------------------------------------------
# Atomic helpers (mirror tool/_common.py — duplicated to keep this script
# importable on its own without cross-module import resolution.)
# ---------------------------------------------------------------------------

def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write `text` to `path` atomically via tmp + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def utc_now_iso() -> str:
    """Timezone-aware UTC ISO-8601 timestamp."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_ts(s: str) -> _dt.datetime:
    """Parse an ISO-8601 string into a naive UTC datetime (DuckDB-friendly).

    Accepts trailing `Z` (treat as UTC), explicit offset, or no tz (assume UTC).
    DuckDB's `TIMESTAMP` is naive; we normalise everything to UTC and strip
    the tzinfo so the column compares cleanly across runs.
    """
    raw = s.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt_obj = _dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {s!r}") from exc
    if dt_obj.tzinfo is not None:
        dt_obj = dt_obj.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return dt_obj


def sha256_of_text(text: str) -> str:
    """Hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of_file(path: Path) -> str:
    """Hex SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_obj(obj: Any) -> str:
    """Hex SHA-256 of a JSON-canonical serialisation of `obj`.

    Sort keys + no whitespace so logically-equal configs hash to the same
    digest regardless of dict iteration order.
    """
    return sha256_of_text(json.dumps(obj, sort_keys=True, separators=(",", ":")))


# ---------------------------------------------------------------------------
# DuckDB connection helpers
# ---------------------------------------------------------------------------

def _require_duckdb() -> int:
    """Return 2 with an install hint if duckdb is missing; 0 otherwise."""
    if duckdb is None:
        sys.stderr.write(
            "ERROR: duckdb module not installed.\n"
            "       Install with: pip install duckdb\n"
            "       Backend choice ratified by plan-decisions-pending.md D-010.\n"
        )
        return 2
    return 0


def open_db(db_path: Path) -> Any:
    """Open (or create) a DuckDB connection at `db_path`. Schema applied.

    The DB file's parent directory is created if missing. Schema DDL is
    idempotent (`CREATE TABLE IF NOT EXISTS`), so reopening an existing DB
    is a no-op.
    """
    assert duckdb is not None, "open_db requires duckdb; call _require_duckdb first"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    conn.execute(SCHEMA_SQL)
    return conn


def open_memory_db() -> Any:
    """Open an in-memory DuckDB (for --selftest)."""
    assert duckdb is not None, "open_memory_db requires duckdb"
    conn = duckdb.connect(":memory:")
    conn.execute(SCHEMA_SQL)
    return conn


# ---------------------------------------------------------------------------
# Forge git SHA discovery (same pattern as emit_t4.py / run_eval.py)
# ---------------------------------------------------------------------------

def discover_forge_commit() -> str:
    """Return the current forge git SHA (short) or '<unknown>'."""
    try:
        head_file = REPO_ROOT / ".git" / "HEAD"
        if not head_file.exists():
            return "<unknown>"
        head = head_file.read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[len("ref: "):]
            ref_file = REPO_ROOT / ".git" / ref
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8").strip()[:10]
        return head[:10] if head else "<unknown>"
    except Exception:
        return "<unknown>"


# ---------------------------------------------------------------------------
# Run-dir ingest model
# ---------------------------------------------------------------------------

@dataclass
class RunRecord:
    """In-memory shape of a forge_runs row prior to DB upsert."""
    run_id: str
    spec: str
    model_name: str
    model_sha: Optional[str]
    eval_set_sha: str
    config_sha: str
    forge_commit: str
    started_at: _dt.datetime
    finished_at: Optional[_dt.datetime]
    pass_rate: Optional[float]
    status: str
    notes: Optional[str] = None


@dataclass
class ScoreRecord:
    """One row for forge_run_scores."""
    run_id: str
    family: str
    pass_rate: float
    task_count: int
    pass_count: int
    bar: Optional[float] = None
    bar_met: Optional[bool] = None


@dataclass
class TaskRecord:
    """One row for forge_run_tasks (sparse)."""
    run_id: str
    task_id: str
    family: str
    verdict: str
    score: Optional[float] = None
    output_sha: Optional[str] = None
    error_class: Optional[str] = None


def _validate_run(record: RunRecord) -> list[str]:
    """Return a list of validation errors for a RunRecord (empty == OK)."""
    errs: list[str] = []
    if record.spec not in KNOWN_SPECS:
        errs.append(
            f"spec {record.spec!r} not in KNOWN_SPECS {sorted(KNOWN_SPECS)}"
        )
    if record.status not in KNOWN_RUN_STATUS:
        errs.append(
            f"status {record.status!r} not in KNOWN_RUN_STATUS "
            f"{sorted(KNOWN_RUN_STATUS)}"
        )
    if not record.run_id:
        errs.append("run_id is empty")
    if not record.eval_set_sha:
        errs.append("eval_set_sha is empty")
    if not record.config_sha:
        errs.append("config_sha is empty")
    if not record.forge_commit:
        errs.append("forge_commit is empty")
    if record.pass_rate is not None and not 0.0 <= record.pass_rate <= 1.0:
        errs.append(f"pass_rate {record.pass_rate} outside [0,1]")
    return errs


def _validate_task(record: TaskRecord) -> list[str]:
    errs: list[str] = []
    if record.verdict not in KNOWN_VERDICTS:
        errs.append(
            f"verdict {record.verdict!r} not in KNOWN_VERDICTS "
            f"{sorted(KNOWN_VERDICTS)}"
        )
    if record.score is not None and not 0.0 <= record.score <= 1.0:
        errs.append(f"score {record.score} outside [0,1]")
    return errs


# ---------------------------------------------------------------------------
# Run-dir reader — extracts the 4-file output of tool/run_eval.py
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _resolve_bar_for_family(spec: str, family: str, spec_config: dict) -> Optional[float]:
    """Resolve the SPECS bar that applies to a given family, if any.

    The dispatch table in `tool/run_eval.py` exposes both per-family bars
    (e.g. `t3_bar`) and aggregate bars. Heuristic: try `<family-lower>_bar`
    first (e.g. T3 -> t3_bar), then fall through to aggregate. Returns
    None when no bar is declared.
    """
    if not isinstance(spec_config, dict):
        return None
    candidate_keys = (
        f"{family.lower()}_bar",
        f"{family}_bar",
    )
    for k in candidate_keys:
        if k in spec_config:
            v = spec_config[k]
            if isinstance(v, (int, float)):
                return float(v)
    return None


def _compute_eval_set_sha(spec: str, spec_doc_path: Optional[Path],
                          tasks_jsonl_path: Path) -> str:
    """SHA-256 of (spec doc bytes + tasks.jsonl bytes). Stable across re-ingest.

    If the spec doc is not on disk (e.g. ephemeral test env), fall back
    to hashing the tasks file alone — still reproducible across re-runs
    of the same task manifest.
    """
    h = hashlib.sha256()
    h.update(spec.encode("utf-8"))
    h.update(b"\0")
    if spec_doc_path is not None and spec_doc_path.exists():
        with open(spec_doc_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    h.update(b"\0")
    if tasks_jsonl_path.exists():
        with open(tasks_jsonl_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()


def _compute_config_sha(plan: dict) -> str:
    """SHA-256 over the reproducibility-bearing fields of plan.json.

    The hash deliberately excludes timestamps and `output_dir` so two
    invocations with identical inputs at different times collide on
    config_sha — supports the v1.0.0 reproducibility gate.
    """
    payload = {
        "spec": plan.get("spec"),
        "model": plan.get("model"),
        "seed": plan.get("seed"),
        "limit": plan.get("limit"),
        "spec_config": plan.get("spec_config"),
    }
    return sha256_of_obj(payload)


def read_run_dir(run_dir: Path, *,
                 pass_sample_rate: float = PASS_SAMPLE_RATE,
                 sample_seed: int = 0) -> tuple[RunRecord, list[ScoreRecord], list[TaskRecord]]:
    """Load a `runs/<spec>/<run_id>/` directory into typed records.

    Sparse storage for tasks: all FAIL/ERROR/SKIPPED rows are retained;
    PASS rows are subsampled at `pass_sample_rate`. `sample_seed` makes
    the subsample deterministic per (run_id, dir contents).
    """
    plan_path = run_dir / "plan.json"
    scores_path = run_dir / "scores.json"
    tasks_path = run_dir / "tasks.jsonl"

    if not plan_path.exists():
        raise FileNotFoundError(f"plan.json missing in {run_dir}")
    if not scores_path.exists():
        raise FileNotFoundError(f"scores.json missing in {run_dir}")
    if not tasks_path.exists():
        raise FileNotFoundError(f"tasks.jsonl missing in {run_dir}")

    plan = _read_json(plan_path)
    scores = _read_json(scores_path)
    tasks = _read_jsonl(tasks_path)

    spec = str(plan.get("spec", ""))
    run_id = str(plan.get("run_id", "")) or run_dir.name
    model_name = str(plan.get("model", "<unknown>"))
    forge_commit = str(plan.get("forge_commit", "<unknown>"))

    # eval_set_sha = spec_doc + tasks.jsonl bytes
    spec_doc_rel = (plan.get("spec_config") or {}).get("doc")
    spec_doc_path = (REPO_ROOT / spec_doc_rel) if spec_doc_rel else None
    eval_set_sha = _compute_eval_set_sha(spec, spec_doc_path, tasks_path)
    config_sha = _compute_config_sha(plan)

    # Aggregate pass-rate from scores.json (None when all stubs).
    aggregate_rate = scores.get("aggregate_pass_rate")
    pass_rate: Optional[float] = (
        float(aggregate_rate) if isinstance(aggregate_rate, (int, float)) else None
    )

    # Optional manifest.json — author-supplied side-band metadata.
    manifest_path = run_dir / "manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.exists() else {}

    started_at_raw = manifest.get("started_at") or plan.get("started_at") or utc_now_iso()
    finished_at_raw = manifest.get("finished_at") or plan.get("finished_at") or utc_now_iso()
    model_sha = manifest.get("model_sha") or plan.get("model_sha")
    status_raw = manifest.get("status") or plan.get("status") or "completed"
    notes = manifest.get("notes") or plan.get("notes")

    record = RunRecord(
        run_id=run_id,
        spec=spec,
        model_name=model_name,
        model_sha=str(model_sha) if model_sha else None,
        eval_set_sha=eval_set_sha,
        config_sha=config_sha,
        forge_commit=forge_commit,
        started_at=parse_iso_ts(started_at_raw),
        finished_at=parse_iso_ts(finished_at_raw),
        pass_rate=pass_rate,
        status=str(status_raw),
        notes=str(notes) if notes else None,
    )

    # Per-family score rows.
    score_rows: list[ScoreRecord] = []
    per_family = scores.get("per_family", {}) or {}
    spec_config = plan.get("spec_config", {}) or {}
    for family, family_stats in per_family.items():
        task_count = int(family_stats.get("n", 0))
        pass_count = int(family_stats.get("pass", 0))
        # Per-family pass_rate may be None when the family is fully stubbed;
        # the schema requires NOT NULL DOUBLE so we coerce stub to 0.0 and
        # mark bar_met=False explicitly (a fully-stub family has not met
        # any bar by construction).
        rate_raw = family_stats.get("pass_rate")
        rate = float(rate_raw) if isinstance(rate_raw, (int, float)) else 0.0
        bar = _resolve_bar_for_family(spec, family, spec_config)
        bar_met: Optional[bool] = None
        if bar is not None and isinstance(rate_raw, (int, float)):
            bar_met = rate >= bar
        elif bar is not None:
            bar_met = False  # stub vs declared bar
        score_rows.append(ScoreRecord(
            run_id=run_id,
            family=family,
            pass_rate=rate,
            task_count=task_count,
            pass_count=pass_count,
            bar=bar,
            bar_met=bar_met,
        ))

    # Sparse task rows: retain all FAIL/ERROR/SKIPPED + sampled PASS.
    rng = random.Random((run_id, sample_seed).__hash__() & 0xFFFFFFFF)
    task_rows: list[TaskRecord] = []
    for t in tasks:
        task_id = str(t.get("task_id", ""))
        family = str(t.get("family", ""))
        score_block = t.get("score") or {}
        passed = score_block.get("pass")
        if passed is True:
            verdict = "pass"
        elif passed is False:
            verdict = "fail"
        elif passed is None:
            # Stub rows under v0.1.2 — record as skipped (auditable, but not
            # billed against any bar).
            verdict = "skipped"
        else:
            verdict = "error"

        if verdict == "pass" and rng.random() > pass_sample_rate:
            continue  # subsampled out

        response = t.get("response", "")
        output_sha = sha256_of_text(response) if response else None
        error_class = score_block.get("reason") if verdict in ("fail", "error") else None
        score_num = score_block.get("score")
        score_val: Optional[float]
        if isinstance(score_num, (int, float)):
            score_val = float(score_num)
        else:
            score_val = None

        task_rows.append(TaskRecord(
            run_id=run_id,
            task_id=task_id or f"<unnamed-{len(task_rows)}>",
            family=family,
            verdict=verdict,
            score=score_val,
            output_sha=output_sha,
            error_class=str(error_class) if error_class else None,
        ))

    return record, score_rows, task_rows


# ---------------------------------------------------------------------------
# Insert / upsert helpers
# ---------------------------------------------------------------------------

def _row_exists(conn: Any, table: str, key_cols: dict[str, Any]) -> bool:
    where = " AND ".join(f"{c} = ?" for c in key_cols)
    sql = f"SELECT 1 FROM {table} WHERE {where} LIMIT 1"
    res = conn.execute(sql, list(key_cols.values())).fetchone()
    return res is not None


def upsert_run(conn: Any, record: RunRecord, *, overwrite: bool = False) -> str:
    """Insert or upsert a forge_runs row. Returns a status string.

    Idempotency rule (per brief): if a row already exists and `pass_rate`
    is non-NULL, DO NOT overwrite it. We do allow status/finished_at to
    promote (pending -> completed) when the existing row is in flight.
    """
    errs = _validate_run(record)
    if errs:
        raise ValueError("RunRecord validation failed: " + "; ".join(errs))

    existing = conn.execute(
        "SELECT pass_rate, status FROM forge_runs WHERE run_id = ?",
        [record.run_id],
    ).fetchone()

    if existing is None:
        conn.execute(
            """
            INSERT INTO forge_runs (
                run_id, spec, model_name, model_sha, eval_set_sha,
                config_sha, forge_commit, started_at, finished_at,
                pass_rate, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.run_id, record.spec, record.model_name,
                record.model_sha, record.eval_set_sha, record.config_sha,
                record.forge_commit, record.started_at, record.finished_at,
                record.pass_rate, record.status, record.notes,
            ],
        )
        return "inserted"

    existing_rate, existing_status = existing
    if existing_rate is not None and not overwrite:
        # Idempotent re-ingest: only refresh status if it advanced from a
        # transient state. Otherwise leave the row alone.
        if existing_status in ("pending", "running") and record.status == "completed":
            conn.execute(
                "UPDATE forge_runs SET status = ?, finished_at = ? WHERE run_id = ?",
                [record.status, record.finished_at, record.run_id],
            )
            return "status-advanced"
        return "kept"

    # Existing row but pass_rate is NULL (run was registered before scoring
    # completed) — fill in the scored fields.
    conn.execute(
        """
        UPDATE forge_runs SET
            spec = ?, model_name = ?, model_sha = ?, eval_set_sha = ?,
            config_sha = ?, forge_commit = ?, started_at = ?,
            finished_at = ?, pass_rate = ?, status = ?, notes = ?
        WHERE run_id = ?
        """,
        [
            record.spec, record.model_name, record.model_sha,
            record.eval_set_sha, record.config_sha, record.forge_commit,
            record.started_at, record.finished_at, record.pass_rate,
            record.status, record.notes, record.run_id,
        ],
    )
    return "updated"


def upsert_scores(conn: Any, rows: Iterable[ScoreRecord]) -> int:
    """Replace per-family score rows for a run (idempotent)."""
    rows = list(rows)
    if not rows:
        return 0
    run_id = rows[0].run_id
    conn.execute("DELETE FROM forge_run_scores WHERE run_id = ?", [run_id])
    for r in rows:
        if r.pass_rate < 0.0 or r.pass_rate > 1.0:
            raise ValueError(
                f"ScoreRecord pass_rate {r.pass_rate} outside [0,1] for "
                f"family {r.family}"
            )
        conn.execute(
            """
            INSERT INTO forge_run_scores (
                run_id, family, pass_rate, task_count, pass_count,
                bar, bar_met
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [r.run_id, r.family, r.pass_rate, r.task_count, r.pass_count,
             r.bar, r.bar_met],
        )
    return len(rows)


def upsert_tasks(conn: Any, rows: Iterable[TaskRecord]) -> int:
    """Replace per-task rows for a run (idempotent, sparse)."""
    rows = list(rows)
    if not rows:
        return 0
    run_id = rows[0].run_id
    conn.execute("DELETE FROM forge_run_tasks WHERE run_id = ?", [run_id])
    for r in rows:
        errs = _validate_task(r)
        if errs:
            raise ValueError(
                f"TaskRecord validation failed for {r.task_id}: "
                + "; ".join(errs)
            )
        conn.execute(
            """
            INSERT INTO forge_run_tasks (
                run_id, task_id, family, verdict, score,
                output_sha, error_class
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [r.run_id, r.task_id, r.family, r.verdict, r.score,
             r.output_sha, r.error_class],
        )
    return len(rows)


def insert_upstream_pr(conn: Any, *, pr_id: str, run_id: str, verb: str,
                       outbox_path: str, falsifier: Optional[str] = None,
                       submitted_at: Optional[_dt.datetime] = None,
                       landed_at: Optional[_dt.datetime] = None,
                       notes: Optional[str] = None) -> str:
    """Insert a forge_upstream_prs row. Errors if pr_id already exists.

    `submitted_at` / `landed_at` are nullable: a brand-new PR draft has
    both NULL; once a curator pushes it upstream they set `submitted_at`;
    once hexa-codex merges, they set `landed_at`. The v1.0.0 gate ⑬
    counts rows with `landed_at IS NOT NULL`.
    """
    if verb not in KNOWN_VERBS:
        raise ValueError(
            f"verb {verb!r} not in KNOWN_VERBS {sorted(KNOWN_VERBS)}"
        )
    if falsifier is not None and falsifier not in KNOWN_FALSIFIERS:
        raise ValueError(
            f"falsifier {falsifier!r} not in KNOWN_FALSIFIERS "
            f"{sorted(KNOWN_FALSIFIERS)}"
        )
    # FK guard: refuse to link a PR to a non-existent run_id.
    if not _row_exists(conn, "forge_runs", {"run_id": run_id}):
        raise KeyError(
            f"run_id {run_id!r} not in forge_runs — ingest the run first"
        )
    if _row_exists(conn, "forge_upstream_prs", {"pr_id": pr_id}):
        raise KeyError(
            f"pr_id {pr_id!r} already exists in forge_upstream_prs "
            "(PRs are write-once; allocate a new pr_id)"
        )
    conn.execute(
        """
        INSERT INTO forge_upstream_prs (
            pr_id, run_id, verb, outbox_path, falsifier,
            submitted_at, landed_at, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [pr_id, run_id, verb, outbox_path, falsifier,
         submitted_at, landed_at, notes],
    )
    return "inserted"


def mark_pr_landed(conn: Any, pr_id: str,
                   landed_at: Optional[_dt.datetime] = None) -> None:
    """Set landed_at on an existing PR row (curator action)."""
    when = landed_at or parse_iso_ts(utc_now_iso())
    if not _row_exists(conn, "forge_upstream_prs", {"pr_id": pr_id}):
        raise KeyError(f"pr_id {pr_id!r} not in forge_upstream_prs")
    conn.execute(
        "UPDATE forge_upstream_prs SET landed_at = ? WHERE pr_id = ?",
        [when, pr_id],
    )


# ---------------------------------------------------------------------------
# Gate check
# ---------------------------------------------------------------------------

def gate_check(conn: Any) -> dict:
    """Compute v1.0.0 forge gate ⑬ status.

    The gate text (ROADMAP.md §2 line 81): "≥ 5 PRs landed in hexa-codex;
    T4 empirical floor for ≥ 2 F-CODEX-N falsifiers (default F-CODEX-1
    train_cost + F-CODEX-2 infer_cost)".

    We compute landed_pr_count as `COUNT(DISTINCT pr_id) WHERE
    landed_at IS NOT NULL`. The by_verb / by_falsifier breakdowns let
    callers see which falsifiers are still uncovered (specifically
    F-CODEX-1 and F-CODEX-2 must both be > 0 for the second clause).
    """
    landed = conn.execute(
        "SELECT COUNT(DISTINCT pr_id) FROM forge_upstream_prs "
        "WHERE landed_at IS NOT NULL"
    ).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(DISTINCT pr_id) FROM forge_upstream_prs"
    ).fetchone()[0]

    by_verb_rows = conn.execute(
        "SELECT verb, COUNT(*) FROM forge_upstream_prs "
        "WHERE landed_at IS NOT NULL GROUP BY verb ORDER BY verb"
    ).fetchall()
    by_falsifier_rows = conn.execute(
        "SELECT COALESCE(falsifier, '<none>'), COUNT(*) "
        "FROM forge_upstream_prs WHERE landed_at IS NOT NULL "
        "GROUP BY 1 ORDER BY 1"
    ).fetchall()
    by_verb = {row[0]: row[1] for row in by_verb_rows}
    by_falsifier = {row[0]: row[1] for row in by_falsifier_rows}

    # Second clause: T4 empirical floor for ≥ 2 F-CODEX-N falsifiers.
    distinct_falsifiers_covered = sum(
        1 for f, n in by_falsifier.items()
        if n > 0 and f in ("F-CODEX-1", "F-CODEX-2", "F-CODEX-3", "F-CODEX-4")
    )

    quorum_met = bool(landed >= GATE_13_MIN_LANDED_PRS)
    falsifier_floor_met = bool(distinct_falsifiers_covered >= 2)
    return {
        "landed_pr_count": int(landed),
        "total_pr_count": int(total),
        "min_required": GATE_13_MIN_LANDED_PRS,
        "v1.0.0_gate_13_met": bool(quorum_met and falsifier_floor_met),
        "quorum_met": quorum_met,
        "falsifier_floor_met": falsifier_floor_met,
        "distinct_falsifiers_landed": distinct_falsifiers_covered,
        "by_verb": by_verb,
        "by_falsifier": by_falsifier,
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_runs(conn: Any, *, run_id: Optional[str] = None,
               spec: Optional[str] = None,
               model: Optional[str] = None,
               status: Optional[str] = None) -> list[dict]:
    """Return forge_runs rows matching the filter set, enriched with linked
    PR counts and per-family score summaries.
    """
    where: list[str] = []
    params: list[Any] = []
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)
    if spec:
        where.append("spec = ?")
        params.append(spec)
    if model:
        where.append("model_name = ?")
        params.append(model)
    if status:
        where.append("status = ?")
        params.append(status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    rows = conn.execute(
        "SELECT run_id, spec, model_name, model_sha, eval_set_sha, "
        "config_sha, forge_commit, started_at, finished_at, "
        "pass_rate, status, notes "
        f"FROM forge_runs{where_sql} ORDER BY started_at DESC, run_id",
        params,
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        rid = r[0]
        scores = conn.execute(
            "SELECT family, pass_rate, task_count, pass_count, bar, bar_met "
            "FROM forge_run_scores WHERE run_id = ? ORDER BY family",
            [rid],
        ).fetchall()
        pr_total, pr_landed = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN landed_at IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM forge_upstream_prs WHERE run_id = ?",
            [rid],
        ).fetchone()
        out.append({
            "run_id": r[0],
            "spec": r[1],
            "model_name": r[2],
            "model_sha": r[3],
            "eval_set_sha": r[4],
            "config_sha": r[5],
            "forge_commit": r[6],
            "started_at": r[7].isoformat() if r[7] is not None else None,
            "finished_at": r[8].isoformat() if r[8] is not None else None,
            "pass_rate": r[9],
            "status": r[10],
            "notes": r[11],
            "scores": [
                {
                    "family": s[0],
                    "pass_rate": s[1],
                    "task_count": s[2],
                    "pass_count": s[3],
                    "bar": s[4],
                    "bar_met": s[5],
                }
                for s in scores
            ],
            "pr_count_total": int(pr_total or 0),
            "pr_count_landed": int(pr_landed or 0),
        })
    return out


def render_query_table(rows: list[dict]) -> str:
    """Pretty-print query_runs output as a Markdown table + per-row scores."""
    if not rows:
        return "(no matching runs)\n"
    lines: list[str] = []
    lines.append("| run_id | spec | model | status | pass_rate | PRs (landed/total) |")
    lines.append("| ------ | ---- | ----- | ------ | --------- | ------------------ |")
    for r in rows:
        rate = r["pass_rate"]
        rate_s = f"{rate:.3f}" if isinstance(rate, (int, float)) else "—"
        lines.append(
            f"| {r['run_id']} | {r['spec']} | {r['model_name']} | "
            f"{r['status']} | {rate_s} | "
            f"{r['pr_count_landed']}/{r['pr_count_total']} |"
        )
    lines.append("")
    for r in rows:
        if not r["scores"]:
            continue
        lines.append(f"### {r['run_id']} per-family")
        lines.append("")
        lines.append("| family | n | pass | pass_rate | bar | bar_met |")
        lines.append("| ------ | - | ---- | --------- | --- | ------- |")
        for s in r["scores"]:
            bar_s = f"{s['bar']:.3f}" if s["bar"] is not None else "—"
            met_s = "" if s["bar_met"] is None else ("YES" if s["bar_met"] else "no")
            lines.append(
                f"| {s['family']} | {s['task_count']} | {s['pass_count']} | "
                f"{s['pass_rate']:.3f} | {bar_s} | {met_s} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Audit report
# ---------------------------------------------------------------------------

def render_audit(conn: Any, run_id: Optional[str] = None) -> str:
    """Markdown audit report for one run (or all runs when run_id is None)."""
    if run_id:
        rows = query_runs(conn, run_id=run_id)
        if not rows:
            return f"# audit — {run_id}\n\n(no such run)\n"
    else:
        rows = query_runs(conn)

    parts: list[str] = []
    parts.append(f"# forge eval lineage audit ({utc_now_iso()})")
    parts.append("")
    parts.append("Spec: `papers/plan-feedback-channel-ops.md` (M-005).")
    parts.append("Backend: DuckDB (D-010). Gate: ROADMAP §2 ⑬.")
    parts.append("")
    gate = gate_check(conn)
    parts.append("## Gate ⑬ status")
    parts.append("")
    parts.append(f"- landed PRs: **{gate['landed_pr_count']}** / required {gate['min_required']}")
    parts.append(f"- gate met: **{gate['v1.0.0_gate_13_met']}**")
    parts.append(f"- distinct F-CODEX-N landed: {gate['distinct_falsifiers_landed']}")
    parts.append(f"- by verb: {gate['by_verb']}")
    parts.append(f"- by falsifier: {gate['by_falsifier']}")
    parts.append("")

    for r in rows:
        parts.append(f"## run `{r['run_id']}`")
        parts.append("")
        parts.append(f"- spec: `{r['spec']}`")
        parts.append(f"- model: `{r['model_name']}`")
        parts.append(f"- model_sha: `{r['model_sha'] or '<not pinned>'}`")
        parts.append(f"- eval_set_sha: `{r['eval_set_sha']}`")
        parts.append(f"- config_sha: `{r['config_sha']}`")
        parts.append(f"- forge_commit: `{r['forge_commit']}`")
        parts.append(f"- started_at: `{r['started_at']}`")
        parts.append(f"- finished_at: `{r['finished_at']}`")
        rate = r["pass_rate"]
        rate_s = f"{rate:.3f}" if isinstance(rate, (int, float)) else "—"
        parts.append(f"- pass_rate: **{rate_s}**")
        parts.append(f"- status: `{r['status']}`")
        if r["notes"]:
            parts.append(f"- notes: {r['notes']}")
        parts.append("")
        if r["scores"]:
            parts.append("### Per-family scores")
            parts.append("")
            parts.append("| family | n | pass | pass_rate | bar | bar_met |")
            parts.append("| ------ | - | ---- | --------- | --- | ------- |")
            for s in r["scores"]:
                bar_s = f"{s['bar']:.3f}" if s["bar"] is not None else "—"
                met_s = "" if s["bar_met"] is None else ("YES" if s["bar_met"] else "no")
                parts.append(
                    f"| {s['family']} | {s['task_count']} | {s['pass_count']} | "
                    f"{s['pass_rate']:.3f} | {bar_s} | {met_s} |"
                )
            parts.append("")
        # PR linkage table.
        pr_rows = conn.execute(
            "SELECT pr_id, verb, outbox_path, falsifier, submitted_at, "
            "landed_at, notes FROM forge_upstream_prs WHERE run_id = ? "
            "ORDER BY pr_id",
            [r["run_id"]],
        ).fetchall()
        if pr_rows:
            parts.append("### Linked hexa-codex PRs")
            parts.append("")
            parts.append("| pr_id | verb | falsifier | submitted_at | landed_at |")
            parts.append("| ----- | ---- | --------- | ------------ | --------- |")
            for p in pr_rows:
                sub_s = p[4].isoformat() if p[4] is not None else "—"
                land_s = p[5].isoformat() if p[5] is not None else "—"
                parts.append(
                    f"| {p[0]} | {p[1]} | {p[3] or '—'} | {sub_s} | {land_s} |"
                )
            parts.append("")

    if not rows:
        parts.append("(no runs ingested)")
        parts.append("")

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    db_path = Path(args.db)
    conn = open_db(db_path)
    # Sanity probe: confirm every table is present.
    tables = {row[0] for row in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).fetchall()}
    required = {"forge_runs", "forge_run_scores",
                "forge_run_tasks", "forge_upstream_prs"}
    missing = required - tables
    if missing:
        sys.stderr.write(f"ERROR: schema apply failed; missing tables: {sorted(missing)}\n")
        return 2
    conn.close()
    sys.stdout.write(f"__EVAL_LINEAGE_INIT__ OK {db_path}\n")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        sys.stderr.write(f"ERROR: run-dir not found: {run_dir}\n")
        return 1
    db_path = Path(args.db)
    conn = open_db(db_path)
    try:
        record, scores, tasks = read_run_dir(run_dir)
    except FileNotFoundError as exc:
        sys.stderr.write(f"ERROR: incomplete run-dir: {exc}\n")
        return 1
    except (ValueError, KeyError) as exc:
        sys.stderr.write(f"ERROR: ingest failed: {exc}\n")
        return 2
    status = upsert_run(conn, record, overwrite=args.overwrite)
    n_scores = upsert_scores(conn, scores)
    n_tasks = upsert_tasks(conn, tasks)
    conn.close()
    sys.stdout.write(
        f"__EVAL_LINEAGE_INGEST__ run={record.run_id} status={status} "
        f"scores={n_scores} tasks={n_tasks}\n"
    )
    return 0


def cmd_link_pr(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    db_path = Path(args.db)
    conn = open_db(db_path)
    try:
        insert_upstream_pr(
            conn,
            pr_id=args.pr_id,
            run_id=args.run_id,
            verb=args.verb,
            outbox_path=args.outbox_path,
            falsifier=args.falsifier,
            submitted_at=parse_iso_ts(args.submitted_at) if args.submitted_at else None,
            landed_at=parse_iso_ts(args.landed_at) if args.landed_at else None,
            notes=args.notes,
        )
    except (ValueError, KeyError) as exc:
        sys.stderr.write(f"ERROR: link-pr failed: {exc}\n")
        return 2
    conn.close()
    sys.stdout.write(
        f"__EVAL_LINEAGE_LINK_PR__ pr_id={args.pr_id} run_id={args.run_id} "
        f"verb={args.verb}\n"
    )
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    db_path = Path(args.db)
    if not db_path.exists() and not args.allow_empty:
        sys.stderr.write(
            f"ERROR: DB not initialised at {db_path}. Run `init` first.\n"
        )
        return 1
    conn = open_db(db_path)
    rows = query_runs(
        conn,
        run_id=args.run_id,
        spec=args.spec,
        model=args.model,
        status=args.status,
    )
    if args.json:
        sys.stdout.write(json.dumps(rows, indent=2, sort_keys=True, default=str) + "\n")
    else:
        sys.stdout.write(render_query_table(rows))
    conn.close()
    return 0


def cmd_gate_check(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    db_path = Path(args.db)
    conn = open_db(db_path)
    result = gate_check(conn)
    conn.close()
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["v1.0.0_gate_13_met"] else 1


def cmd_audit(args: argparse.Namespace) -> int:
    rc = _require_duckdb()
    if rc != 0:
        return rc
    db_path = Path(args.db)
    conn = open_db(db_path)
    body = render_audit(conn, run_id=args.run_id)
    if args.output:
        atomic_write_text(Path(args.output), body)
        sys.stdout.write(f"__EVAL_LINEAGE_AUDIT__ wrote {args.output}\n")
    else:
        sys.stdout.write(body)
    conn.close()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_EPILOG = """\
cross-link:
  decision:    papers/plan-decisions-pending.md  — D-010 DuckDB default
  routing:     papers/plan-feedback-channel-ops.md (M-005)
  gate:        ROADMAP.md §2 — v1.0.0 acceptance gate ⑬ (>= 5 PRs landed)

surface:
  init        create DuckDB file + schema at --db (default: runs/eval_lineage.duckdb)
  ingest      pull plan.json / scores.json / tasks.jsonl from a runs/ dir
  link-pr     link a hexa-codex outbox PR to a forge run_id
  query       list forge_runs rows + per-family scores + PR counts
  gate-check  JSON {landed_pr_count, v1.0.0_gate_13_met, by_verb, by_falsifier}
  audit       Markdown audit report (run id, model, evals, scores, PRs, SHAs)
  --selftest  in-memory round-trip across the full surface (no disk required)
"""


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval_lineage.py",
        description="DuckDB-backed eval-run lineage store for hexa-forge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="run in-memory selftest and exit (no disk side effects)",
    )
    sub = parser.add_subparsers(dest="cmd")

    # init
    p_init = sub.add_parser("init", help="create DuckDB file + schema")
    p_init.add_argument("--db", default=str(DEFAULT_DB_PATH),
                        help="DB file path (default: runs/eval_lineage.duckdb)")
    p_init.set_defaults(handler=cmd_init)

    # ingest
    p_ing = sub.add_parser("ingest", help="ingest a runs/<spec>/<run_id>/ directory")
    p_ing.add_argument("--run-dir", required=True,
                       help="path to runs/<spec>/<run_id>/")
    p_ing.add_argument("--db", default=str(DEFAULT_DB_PATH),
                       help="DB file path (default: runs/eval_lineage.duckdb)")
    p_ing.add_argument("--overwrite", action="store_true",
                       help="force overwrite of an existing scored row "
                            "(default: idempotent — preserve non-NULL pass_rate)")
    p_ing.set_defaults(handler=cmd_ingest)

    # link-pr
    p_pr = sub.add_parser("link-pr", help="link a hexa-codex PR to a run")
    p_pr.add_argument("--pr-id", required=True,
                      help="PR identifier (e.g. 2026-05-11-train-cost-001)")
    p_pr.add_argument("--run-id", required=True,
                      help="forge_runs.run_id to link the PR to")
    p_pr.add_argument("--verb", required=True, choices=sorted(KNOWN_VERBS),
                      help="hexa-codex verb (e.g. train_cost)")
    p_pr.add_argument("--outbox-path", required=True,
                      help="outbox/hexa-codex/<verb>/<pr_id>.md path")
    p_pr.add_argument("--falsifier", default=None,
                      choices=sorted(KNOWN_FALSIFIERS),
                      help="optional F-CODEX-N tag (or 'cross-cutter')")
    p_pr.add_argument("--submitted-at", default=None,
                      help="ISO-8601 timestamp when PR was opened upstream")
    p_pr.add_argument("--landed-at", default=None,
                      help="ISO-8601 timestamp when PR was merged upstream")
    p_pr.add_argument("--notes", default=None, help="free-form notes")
    p_pr.add_argument("--db", default=str(DEFAULT_DB_PATH),
                      help="DB file path (default: runs/eval_lineage.duckdb)")
    p_pr.set_defaults(handler=cmd_link_pr)

    # query
    p_q = sub.add_parser("query", help="list forge_runs rows")
    p_q.add_argument("--run-id", default=None)
    p_q.add_argument("--spec", default=None, choices=sorted(KNOWN_SPECS))
    p_q.add_argument("--model", default=None)
    p_q.add_argument("--status", default=None, choices=sorted(KNOWN_RUN_STATUS))
    p_q.add_argument("--json", action="store_true",
                     help="emit JSON instead of a Markdown table")
    p_q.add_argument("--allow-empty", action="store_true",
                     help="auto-create empty DB if missing")
    p_q.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p_q.set_defaults(handler=cmd_query)

    # gate-check
    p_g = sub.add_parser("gate-check", help="v1.0.0 forge gate ⑬ status (JSON)")
    p_g.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p_g.set_defaults(handler=cmd_gate_check)

    # audit
    p_a = sub.add_parser("audit", help="emit a Markdown audit report")
    p_a.add_argument("--run-id", default=None,
                     help="run_id to audit (omit to audit all runs)")
    p_a.add_argument("--output", default=None,
                     help="write report to this path (default: stdout)")
    p_a.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p_a.set_defaults(handler=cmd_audit)

    return parser


def main(argv: list[str]) -> int:
    parser = build_argparser()
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    return args.handler(args)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _make_mock_run_dir(td: Path, *, spec: str = "hexa-eval",
                       run_id: str = "selftest-2026-05-11-aaaa") -> Path:
    """Synthesise a runs/<spec>/<run_id>/ directory that mirrors run_eval.py."""
    run_dir = td / "runs" / spec / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "spec": spec,
        "run_id": run_id,
        "model": "Qwen2.5-Coder-7B",
        "seed": 42,
        "limit": None,
        "dry_run": False,
        "score_only": False,
        "task_manifest": str(run_dir / "manifest.jsonl"),
        "forge_commit": "selftest0",
        "spec_config": {
            "task_total": 4,
            "families": ["T1", "T8"],
            "family_counts": {"T1": 3, "T8": 1},
            "aggregate_bar": 0.80,
            "feedback_verbs": ["quality_scale", "eval"],
            "doc": "papers/spec-hexa-eval.md",
        },
    }
    scores = {
        "spec": spec,
        "task_count": 4,
        "stub_count": 0,
        "evaluated_count": 4,
        "aggregate_pass_rate": 0.75,
        "per_family": {
            "T1": {"n": 3, "pass": 2, "stub": 0, "pass_rate": 2 / 3},
            "T8": {"n": 1, "pass": 1, "stub": 0, "pass_rate": 1.0},
        },
        "bars": {"aggregate_bar": 0.80},
        "verdict": "FAIL",
    }
    tasks = [
        {"task_id": "h1", "family": "T1", "prompt": "p1", "response": "r1",
         "score": {"pass": True, "reason": "ok", "score": 1.0}},
        {"task_id": "h2", "family": "T1", "prompt": "p2", "response": "r2",
         "score": {"pass": False, "reason": "compile-error", "score": 0.0}},
        {"task_id": "h3", "family": "T1", "prompt": "p3", "response": "r3",
         "score": {"pass": True, "reason": "ok", "score": 1.0}},
        {"task_id": "h4", "family": "T8", "prompt": "p4", "response": "r4",
         "score": {"pass": True, "reason": "refusal-ok", "score": 1.0}},
    ]
    manifest = {
        "started_at": "2026-05-11T09:00:00Z",
        "finished_at": "2026-05-11T09:42:00Z",
        "model_sha": "deadbeefcafebabe1234567890abcdef",
        "status": "completed",
        "notes": "selftest synthetic run",
    }
    atomic_write_text(run_dir / "plan.json",
                      json.dumps(plan, indent=2, sort_keys=True) + "\n")
    atomic_write_text(run_dir / "scores.json",
                      json.dumps(scores, indent=2, sort_keys=True) + "\n")
    atomic_write_text(
        run_dir / "tasks.jsonl",
        "".join(json.dumps(t, sort_keys=True) + "\n" for t in tasks),
    )
    atomic_write_text(run_dir / "manifest.json",
                      json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return run_dir


def _selftest() -> int:
    """In-memory round-trip across the full surface. Exits 0 on success."""
    failures: list[str] = []

    if duckdb is None:
        sys.stderr.write(
            "ERROR: duckdb module not installed; selftest cannot run.\n"
            "       Install with: pip install duckdb\n"
        )
        return 2

    # Schema constant sanity.
    for table in ("forge_runs", "forge_run_scores",
                  "forge_run_tasks", "forge_upstream_prs"):
        if table not in SCHEMA_SQL:
            failures.append(f"schema missing table: {table}")
    if "CREATE TABLE IF NOT EXISTS" not in SCHEMA_SQL:
        failures.append("schema is not idempotent (missing IF NOT EXISTS)")

    # Enum exposure sanity.
    if len(KNOWN_VERBS) != 11:
        failures.append(f"KNOWN_VERBS size {len(KNOWN_VERBS)} != 11")
    if len(KNOWN_SPECS) != 6:
        failures.append(f"KNOWN_SPECS size {len(KNOWN_SPECS)} != 6")

    # Hash helpers.
    if sha256_of_text("hello") != hashlib.sha256(b"hello").hexdigest():
        failures.append("sha256_of_text mismatch")
    if sha256_of_obj({"a": 1, "b": 2}) != sha256_of_obj({"b": 2, "a": 1}):
        failures.append("sha256_of_obj is not key-order stable")

    # In-memory DB lifecycle.
    conn = open_memory_db()
    tables = {row[0] for row in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).fetchall()}
    required = {"forge_runs", "forge_run_scores",
                "forge_run_tasks", "forge_upstream_prs"}
    if not required.issubset(tables):
        failures.append(f"schema apply missing tables: {sorted(required - tables)}")

    # Fresh-DB gate-check: nothing landed.
    fresh = gate_check(conn)
    if fresh["landed_pr_count"] != 0:
        failures.append(f"fresh landed_pr_count {fresh['landed_pr_count']} != 0")
    if fresh["v1.0.0_gate_13_met"] is not False:
        failures.append("fresh gate-check should be False")

    # Ingest a mock run.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        run_dir = _make_mock_run_dir(td_path)
        record, scores, tasks = read_run_dir(run_dir)
        if record.spec != "hexa-eval":
            failures.append(f"read_run_dir spec {record.spec} != hexa-eval")
        if record.pass_rate is None or abs(record.pass_rate - 0.75) > 1e-9:
            failures.append(f"read_run_dir pass_rate {record.pass_rate} != 0.75")
        if record.status != "completed":
            failures.append(f"read_run_dir status {record.status} != completed")
        # Sparse-task semantics: all FAIL retained.
        fail_rows = [t for t in tasks if t.verdict == "fail"]
        if len(fail_rows) != 1:
            failures.append(f"expected 1 fail row, got {len(fail_rows)}")
        if fail_rows and fail_rows[0].task_id != "h2":
            failures.append(f"expected fail task h2, got {fail_rows[0].task_id}")

        ins_status = upsert_run(conn, record)
        if ins_status != "inserted":
            failures.append(f"first upsert_run returned {ins_status} != inserted")
        upsert_scores(conn, scores)
        upsert_tasks(conn, tasks)

        # Idempotency: re-ingest, pass_rate non-NULL, must keep old value.
        re_status = upsert_run(conn, record)
        if re_status != "kept":
            failures.append(f"re-ingest returned {re_status} != kept")

        # query_runs: one row, with correct score rollup.
        runs = query_runs(conn, spec="hexa-eval")
        if len(runs) != 1:
            failures.append(f"query_runs len {len(runs)} != 1")
        if runs and runs[0]["pass_rate"] != 0.75:
            failures.append(f"query_runs pass_rate {runs[0]['pass_rate']} != 0.75")
        # 2 families ingested.
        if runs and len(runs[0]["scores"]) != 2:
            failures.append(f"query_runs scores len {len(runs[0]['scores'])} != 2")

        # link-pr: tie 5 PRs to this run, with 2 distinct F-CODEX-N falsifiers,
        # so the gate ⑬ should flip to True after we mark all 5 landed.
        for i, (verb, falsifier) in enumerate([
            ("train_cost", "F-CODEX-1"),
            ("infer_cost", "F-CODEX-2"),
            ("quality_scale", "cross-cutter"),
            ("safety", "F-CODEX-3"),
            ("eval", None),
        ]):
            insert_upstream_pr(
                conn,
                pr_id=f"selftest-pr-{i:03d}",
                run_id=record.run_id,
                verb=verb,
                outbox_path=f"outbox/hexa-codex/{verb}/selftest-pr-{i:03d}.md",
                falsifier=falsifier,
            )

        # link-pr FK guard.
        try:
            insert_upstream_pr(
                conn,
                pr_id="orphan-pr",
                run_id="no-such-run",
                verb="train_cost",
                outbox_path="outbox/hexa-codex/train_cost/orphan.md",
            )
            failures.append("FK guard: orphan link-pr should have raised")
        except KeyError:
            pass

        # Duplicate pr_id guard.
        try:
            insert_upstream_pr(
                conn,
                pr_id="selftest-pr-000",
                run_id=record.run_id,
                verb="train_cost",
                outbox_path="outbox/hexa-codex/train_cost/dup.md",
            )
            failures.append("duplicate pr_id guard did not fire")
        except KeyError:
            pass

        # Bad verb / bad falsifier guards.
        for kwargs in (
            {"verb": "not_a_verb", "falsifier": None},
            {"verb": "train_cost", "falsifier": "F-CODEX-99"},
        ):
            try:
                insert_upstream_pr(
                    conn,
                    pr_id=f"bad-{kwargs['verb']}-{kwargs['falsifier']}",
                    run_id=record.run_id,
                    outbox_path="outbox/hexa-codex/x/y.md",
                    **kwargs,
                )
                failures.append(f"validation guard missed: {kwargs}")
            except ValueError:
                pass

        # Gate-check before landing: should remain False.
        before = gate_check(conn)
        if before["landed_pr_count"] != 0:
            failures.append(
                f"pre-land landed_pr_count {before['landed_pr_count']} != 0"
            )
        if before["v1.0.0_gate_13_met"] is not False:
            failures.append("pre-land gate should be False")

        # Land all 5 -> gate flips to True.
        for i in range(5):
            mark_pr_landed(conn, f"selftest-pr-{i:03d}",
                           parse_iso_ts("2026-05-12T10:00:00Z"))
        after = gate_check(conn)
        if after["landed_pr_count"] != 5:
            failures.append(
                f"post-land landed_pr_count {after['landed_pr_count']} != 5"
            )
        if not after["v1.0.0_gate_13_met"]:
            failures.append("post-land gate should be True")
        if after["distinct_falsifiers_landed"] < 2:
            failures.append(
                f"post-land distinct F-CODEX-N {after['distinct_falsifiers_landed']} < 2"
            )

        # Audit renders for the ingested run.
        audit_md = render_audit(conn, run_id=record.run_id)
        if record.run_id not in audit_md:
            failures.append("audit report missing run_id")
        if "Gate ⑬ status" not in audit_md:
            failures.append("audit report missing gate header")
        if "config_sha" not in audit_md:
            failures.append("audit report missing config_sha")

        # query_runs JSON serialisation round-trip survives timestamps.
        rendered = render_query_table(query_runs(conn, run_id=record.run_id))
        if record.run_id not in rendered:
            failures.append("render_query_table missing run_id")

        # Ingest CLI: build a real argparse and run cmd_ingest against
        # a fresh temp DB on disk to exercise open_db's file branch.
        # Silence stdout for the duration so the selftest output stays
        # clean (handlers normally print a status banner on success).
        import contextlib
        import io as _io
        disk_db = td_path / "lineage.duckdb"
        ns = argparse.Namespace(run_dir=str(run_dir), db=str(disk_db),
                                overwrite=False)
        with contextlib.redirect_stdout(_io.StringIO()):
            rc = cmd_ingest(ns)
        if rc != 0:
            failures.append(f"cmd_ingest returned {rc} != 0")
        if not disk_db.exists():
            failures.append("cmd_ingest did not create DB file on disk")

        # init handler on a separate path.
        init_db = td_path / "init.duckdb"
        with contextlib.redirect_stdout(_io.StringIO()):
            rc = cmd_init(argparse.Namespace(db=str(init_db)))
        if rc != 0:
            failures.append(f"cmd_init returned {rc} != 0")
        if not init_db.exists():
            failures.append("cmd_init did not create init DB on disk")

        # gate-check on a fresh DB returns exit code 1 (gate not met).
        with contextlib.redirect_stdout(_io.StringIO()) as gate_buf:
            rc = cmd_gate_check(argparse.Namespace(db=str(init_db)))
        if rc != 1:
            failures.append(f"fresh gate-check exit {rc} != 1")
        # Sanity-check the JSON envelope shape on a fresh DB.
        try:
            fresh_payload = json.loads(gate_buf.getvalue())
        except json.JSONDecodeError:
            failures.append("cmd_gate_check did not emit valid JSON")
            fresh_payload = {}
        if fresh_payload.get("landed_pr_count") != 0:
            failures.append("cmd_gate_check fresh landed_pr_count != 0")
        if fresh_payload.get("v1.0.0_gate_13_met") is not False:
            failures.append("cmd_gate_check fresh gate should be False")

    conn.close()

    if failures:
        sys.stderr.write("eval_lineage.py SELFTEST FAILED:\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        sys.stdout.write("__EVAL_LINEAGE_SELFTEST__ FAIL\n")
        return 1
    sys.stdout.write("__EVAL_LINEAGE_SELFTEST__ PASS\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Bare invocation: print help, do not run selftest implicitly.
        build_argparser().print_help()
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
