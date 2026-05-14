#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge_vacuum.py — periodic SQLite cache maintenance for forge_db_path (r62).

r61 introduced the SQLite WAL backend (`forge_db_path`). Cache LRU eviction
is LAZY in DB (no immediate DELETE to avoid write amplification under load),
so over time the `vendor_cache` table accumulates expired rows. r62 ships
the cron-friendly cleanup script that:

1. DELETEs expired vendor_cache rows (`expires <= now()`).
2. Optionally caps vendor_cache to `--keep-recent N` rows (most-recent by
   `inserted_at`), dropping the rest.
3. Optionally DELETEs old conv_turns rows beyond `--conv-days N` retention.
4. Runs `VACUUM` to reclaim disk space from the freelist.
5. Runs `PRAGMA optimize` to update query planner stats.

OUTPUT
- Single text report to stdout: rows removed per table + db file size before/after.
- Exit 0 on success, 1 on input errors, 2 on SQLite errors.

USAGE
    # Cron pattern (daily 03:00, conservative retention):
    python3 tool/forge_vacuum.py --db /var/lib/forge/forge.sqlite3 \
        --keep-recent 1024 --conv-days 30

    # Aggressive (clear expired only, no row cap):
    python3 tool/forge_vacuum.py --db /var/lib/forge/forge.sqlite3

    # Dry-run (report counts but don't DELETE/VACUUM):
    python3 tool/forge_vacuum.py --db /var/lib/forge/forge.sqlite3 --dry-run

    # Self-test:
    python3 tool/forge_vacuum.py --smoke

SAFETY
- Multi-process safe with the runtime (SQLite WAL handles concurrent
  readers during VACUUM; vacuum-into is the operation that locks writes).
- Idempotent: running twice in a row is fine (second run finds 0 expired).
- Best-effort: SQLite errors are reported but don't propagate; partial
  success is possible (e.g. cache cleanup OK, VACUUM blocked → exit 2
  with detail).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def _db_size_bytes(path: Path) -> int:
    """Sum forge.sqlite3 + WAL + SHM file sizes (the real on-disk footprint)."""
    total = 0
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def vacuum_db(db_path: Path, keep_recent: int | None,
                conv_days: int | None, dry_run: bool) -> dict:
    """Run the maintenance steps. Returns a report dict."""
    report: dict = {
        "db_path": str(db_path),
        "size_before_bytes": _db_size_bytes(db_path),
        "expired_removed": 0,
        "lru_removed": 0,
        "old_conv_removed": 0,
        "vacuumed": False,
        "optimized": False,
        "errors": [],
        "dry_run": dry_run,
    }
    if not db_path.exists():
        report["errors"].append(f"db not found: {db_path}")
        return report

    try:
        conn = sqlite3.connect(str(db_path), isolation_level=None,
                                 check_same_thread=False, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error as e:
        report["errors"].append(f"connect failed: {e!r}")
        return report

    now = time.time()

    # 1) Expired vendor_cache rows.
    try:
        n_expired = conn.execute(
            "SELECT COUNT(*) FROM vendor_cache WHERE expires <= ?", (now,)
        ).fetchone()[0]
        if not dry_run and n_expired:
            conn.execute("DELETE FROM vendor_cache WHERE expires <= ?", (now,))
        report["expired_removed"] = int(n_expired)
    except sqlite3.Error as e:
        report["errors"].append(f"expired cleanup failed: {e!r}")

    # 2) LRU cap on vendor_cache.
    if keep_recent is not None and keep_recent > 0:
        try:
            n_total = conn.execute(
                "SELECT COUNT(*) FROM vendor_cache"
            ).fetchone()[0]
            n_excess = max(0, n_total - keep_recent)
            if n_excess > 0:
                if not dry_run:
                    conn.execute(
                        "DELETE FROM vendor_cache WHERE cache_key IN ("
                        "  SELECT cache_key FROM vendor_cache "
                        "  ORDER BY inserted_at ASC LIMIT ?"
                        ")", (n_excess,)
                    )
                report["lru_removed"] = n_excess
        except sqlite3.Error as e:
            report["errors"].append(f"LRU cap failed: {e!r}")

    # 3) Old conv_turns beyond retention.
    if conv_days is not None and conv_days > 0:
        cutoff = now - (conv_days * 86400)
        try:
            n_old = conn.execute(
                "SELECT COUNT(*) FROM conv_turns WHERE recorded_at < ?",
                (cutoff,)
            ).fetchone()[0]
            if not dry_run and n_old:
                conn.execute(
                    "DELETE FROM conv_turns WHERE recorded_at < ?", (cutoff,)
                )
            report["old_conv_removed"] = int(n_old)
        except sqlite3.Error as e:
            report["errors"].append(f"old-conv cleanup failed: {e!r}")

    # 4) VACUUM (reclaim freelist pages). Requires no other writers.
    if not dry_run:
        try:
            conn.execute("VACUUM")
            report["vacuumed"] = True
        except sqlite3.Error as e:
            report["errors"].append(f"VACUUM failed: {e!r}")

    # 5) PRAGMA optimize (analyze stats for query planner).
    if not dry_run:
        try:
            conn.execute("PRAGMA optimize")
            report["optimized"] = True
        except sqlite3.Error as e:
            report["errors"].append(f"optimize failed: {e!r}")

    conn.close()
    report["size_after_bytes"] = _db_size_bytes(db_path)
    report["size_reclaimed_bytes"] = (
        report["size_before_bytes"] - report["size_after_bytes"]
    )
    return report


def render_text(report: dict) -> str:
    """Human-readable report."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"forge_vacuum — {report['db_path']}")
    if report.get("dry_run"):
        lines.append("DRY-RUN MODE — no changes written")
    lines.append("=" * 70)
    lines.append(f"size_before:        {report['size_before_bytes']:>12,} bytes")
    lines.append(f"expired_removed:    {report['expired_removed']:>12,} rows (vendor_cache)")
    lines.append(f"lru_removed:        {report['lru_removed']:>12,} rows (vendor_cache, --keep-recent cap)")
    lines.append(f"old_conv_removed:   {report['old_conv_removed']:>12,} rows (conv_turns, --conv-days retention)")
    lines.append(f"vacuumed:           {report['vacuumed']!s:>12}")
    lines.append(f"optimized:          {report['optimized']!s:>12}")
    if "size_after_bytes" in report:
        lines.append(f"size_after:         {report['size_after_bytes']:>12,} bytes")
        lines.append(f"size_reclaimed:     {report['size_reclaimed_bytes']:>12,} bytes")
    if report.get("errors"):
        lines.append("")
        lines.append("ERRORS:")
        for e in report["errors"]:
            lines.append(f"  ✗ {e}")
    return "\n".join(lines) + "\n"


# ============================================================================
# Self-test
# ============================================================================

def _smoke_test() -> int:
    """Writes synthetic vendor_cache + conv_turns rows, runs vacuum, verifies."""
    print("=== forge_vacuum self-test ===")
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)
    try:
        # Build a DB matching r61's schema, populated with synthetic rows.
        conn = sqlite3.connect(str(db_path), isolation_level=None,
                                 check_same_thread=False, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE vendor_cache (
                cache_key TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                model TEXT NOT NULL,
                max_tokens INTEGER NOT NULL,
                text TEXT NOT NULL,
                usage_json TEXT NOT NULL,
                expires REAL NOT NULL,
                inserted_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE conv_turns (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT NOT NULL,
                turn_id TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                assistant_text TEXT NOT NULL,
                classifier_label TEXT NOT NULL,
                tool TEXT, model TEXT,
                recorded_at REAL NOT NULL
            )
        """)
        now = time.time()
        # 5 expired + 10 fresh cache rows
        for i in range(5):
            conn.execute(
                "INSERT INTO vendor_cache VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"expired-{i}", "claude-api", "claude-sonnet-4-6", 2048,
                 "stale", "{}", now - 1, now - 600 + i),
            )
        for i in range(10):
            conn.execute(
                "INSERT INTO vendor_cache VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"fresh-{i}", "claude-api", "claude-sonnet-4-6", 2048,
                 "current", "{}", now + 300, now - 100 + i),
            )
        # 3 recent + 7 old conv turns (old = >35 days ago)
        for i in range(3):
            conn.execute(
                "INSERT INTO conv_turns "
                "(conv_id, turn_id, timestamp_utc, user_prompt, assistant_text, "
                " classifier_label, tool, model, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("c1", f"t{i}", "now", f"q{i}", f"a{i}", "ood",
                 "claude-api", "claude-sonnet-4-6", now - 86400 * i),
            )
        for i in range(7):
            conn.execute(
                "INSERT INTO conv_turns "
                "(conv_id, turn_id, timestamp_utc, user_prompt, assistant_text, "
                " classifier_label, tool, model, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("c-old", f"t{i}", "old", f"q{i}", f"a{i}", "ood",
                 "claude-api", "claude-sonnet-4-6", now - 86400 * (35 + i)),
            )
        conn.close()

        # Dry-run first: counts visible, nothing deleted
        rep_dry = vacuum_db(db_path, keep_recent=8, conv_days=30, dry_run=True)
        assert rep_dry["expired_removed"] == 5, f"dry: {rep_dry}"
        # 5 expired + 10 fresh = 15 total; keep_recent=8 → 7 to evict
        assert rep_dry["lru_removed"] == 7, f"dry: {rep_dry}"
        assert rep_dry["old_conv_removed"] == 7, f"dry: {rep_dry}"
        assert not rep_dry["vacuumed"]
        # Verify rows still present (dry-run)
        conn = sqlite3.connect(str(db_path))
        n = conn.execute("SELECT COUNT(*) FROM vendor_cache").fetchone()[0]
        assert n == 15, f"dry-run should not delete; got {n} cache rows"
        conn.close()
        print(f"  ✓ dry-run: {rep_dry['expired_removed']} expired, "
              f"{rep_dry['lru_removed']} LRU-excess, "
              f"{rep_dry['old_conv_removed']} old-conv (no changes written)")

        # Real run
        rep = vacuum_db(db_path, keep_recent=8, conv_days=30, dry_run=False)
        assert rep["expired_removed"] == 5
        # After expired removed: 10 left, keep 8 → 2 excess removed
        assert rep["lru_removed"] == 2, f"real: {rep}"
        assert rep["old_conv_removed"] == 7
        assert rep["vacuumed"] is True
        assert rep["optimized"] is True
        # Verify final state
        conn = sqlite3.connect(str(db_path))
        n_cache = conn.execute("SELECT COUNT(*) FROM vendor_cache").fetchone()[0]
        n_conv = conn.execute("SELECT COUNT(*) FROM conv_turns").fetchone()[0]
        assert n_cache == 8, f"expected 8 fresh kept, got {n_cache}"
        assert n_conv == 3, f"expected 3 recent kept, got {n_conv}"
        conn.close()
        print(f"  ✓ real run: removed {rep['expired_removed']+rep['lru_removed']} "
              f"cache rows + {rep['old_conv_removed']} conv rows, vacuumed, optimized")

        # Idempotent re-run finds nothing
        rep2 = vacuum_db(db_path, keep_recent=8, conv_days=30, dry_run=False)
        assert rep2["expired_removed"] == 0
        assert rep2["lru_removed"] == 0
        assert rep2["old_conv_removed"] == 0
        print(f"  ✓ idempotent re-run: 0 rows to remove (already clean)")

        # Rendering
        text = render_text(rep)
        assert "forge_vacuum" in text and "expired_removed" in text
        print(f"  ✓ text renderer produces valid report")
    finally:
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
    print("\n=== forge_vacuum self-test PASSED ===")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path,
                    help="Path to forge SQLite db (r61 forge_db_path target)")
    ap.add_argument("--keep-recent", type=int, default=None,
                    help="Cap vendor_cache to N most-recent rows (drop older)")
    ap.add_argument("--conv-days", type=int, default=None,
                    help="Drop conv_turns rows older than N days (retention)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report counts; do NOT delete or VACUUM")
    ap.add_argument("--smoke", action="store_true",
                    help="Run inline self-test on a synthetic temp DB")
    args = ap.parse_args()

    if args.smoke:
        return _smoke_test()

    if args.db is None:
        print("ERROR: --db is required (or use --smoke)", file=sys.stderr)
        return 1

    report = vacuum_db(args.db, keep_recent=args.keep_recent,
                       conv_days=args.conv_days, dry_run=args.dry_run)
    print(render_text(report), end="")

    if report["errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
