#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge_audit.py — production observability for forge runtime telemetry (r58).

Reads `state/delegation_log.jsonl` (or any DelegationCall JSONL) and emits an
aggregated health report: cache hit rate, vendor/tier distribution, error
breakdown, latency percentiles, cost attribution, and optional health-gate
alerting via non-zero exit code.

INPUT FORMAT
- One JSON line per `DelegationCall` (see tool/forge_runtime.py @dataclass).
- Required fields: tool, model, ok, error, cost_usd, latency_ms, cache_hit,
  timestamp_utc. Optional: tokens_in, tokens_out, conv_id, turn_id.

USAGE
    # Human-readable summary
    python3 tool/forge_audit.py --input state/delegation_log.jsonl

    # Last 24 hours, JSON output
    python3 tool/forge_audit.py --input state/delegation_log.jsonl \
        --since-hours 24 --output json

    # Health gate (exit 2 on threshold breach)
    python3 tool/forge_audit.py --input state/delegation_log.jsonl \
        --alert-cache-hit-min 0.20 --alert-error-rate-max 0.05 \
        --alert-cost-day-max 50.00

    # CSV row-per-aggregation (for dashboards)
    python3 tool/forge_audit.py --input state/delegation_log.jsonl --output csv

    # Self-test (no external file needed)
    python3 tool/forge_audit.py --smoke
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any


# ============================================================================
# Schema + helpers
# ============================================================================

# DelegationCall field names we read (subset; other fields ignored).
_REQUIRED_FIELDS = ("tool", "model", "ok", "error", "cost_usd", "latency_ms",
                    "cache_hit", "timestamp_utc")


def _parse_iso(ts: str) -> datetime | None:
    """Parse an ISO-8601 timestamp like '2026-05-14T15:23:45Z'. Returns None
    on parse failure (so corrupt rows don't break the aggregator)."""
    if not ts:
        return None
    try:
        # Accept trailing Z or +00:00
        ts = ts.rstrip("Z")
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def _percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile, p in [0, 1]. Returns 0 on empty."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    idx = p * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _model_tier(model: str) -> str:
    """Coarse tier name for a model id. Mirrors select_vendor_tier's
    _MODEL_TO_TIER_NAME but duplicated here to avoid sys.path coupling."""
    table = {
        "claude-haiku-4-5-20251001": "haiku",
        "claude-sonnet-4-6":         "sonnet",
        "claude-opus-4-7":           "opus",
        "gpt-5-nano":                "nano",
        "gpt-5-mini":                "mini",
        "gpt-4o-mini":               "mini",
        "o4-mini":                   "mini",
        "o3-mini":                   "mini",
        "gpt-5":                     "flagship",
        "gemini-2.5-flash-lite":     "nano",
        "gemini-2.5-flash":          "mini",
        "gemini-2.5-pro":            "flagship",
    }
    return table.get(model, "unknown")


# ============================================================================
# Aggregation
# ============================================================================

def aggregate(rows: list[dict]) -> dict[str, Any]:
    """Build the full audit summary from a list of DelegationCall rows."""
    n = len(rows)
    if n == 0:
        return {"n_turns": 0, "note": "no rows in window"}

    # Time window
    timestamps = [_parse_iso(r.get("timestamp_utc", "")) for r in rows]
    valid_ts = [t for t in timestamps if t is not None]
    t_min = min(valid_ts) if valid_ts else None
    t_max = max(valid_ts) if valid_ts else None
    window_hours = ((t_max - t_min).total_seconds() / 3600.0) if (t_min and t_max) else 0.0

    # Cache metrics
    cache_hits = sum(1 for r in rows if r.get("cache_hit"))
    cache_misses = n - cache_hits
    cache_hit_rate = cache_hits / n if n else 0.0
    # Cost-saved estimate: for each cache hit, use the avg cost of the same
    # (tool, model) misses as the would-have-been cost.
    avg_cost_per_miss_by_model: dict[tuple, float] = {}
    miss_costs_by_model: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        if not r.get("cache_hit") and r.get("ok"):
            miss_costs_by_model[(r.get("tool"), r.get("model"))].append(
                float(r.get("cost_usd", 0.0) or 0.0)
            )
    for k, costs in miss_costs_by_model.items():
        if costs:
            avg_cost_per_miss_by_model[k] = sum(costs) / len(costs)
    cost_saved_est = 0.0
    for r in rows:
        if r.get("cache_hit"):
            avg = avg_cost_per_miss_by_model.get((r.get("tool"), r.get("model")), 0.0)
            cost_saved_est += avg

    # Vendor + tier distribution
    by_tool = Counter(r.get("tool") for r in rows if r.get("tool"))
    by_model = Counter(r.get("model") for r in rows if r.get("model"))
    by_tier = Counter(_model_tier(r.get("model", "")) for r in rows if r.get("model"))

    # Error breakdown
    n_ok = sum(1 for r in rows if r.get("ok"))
    n_err = n - n_ok
    err_codes = Counter(r.get("error") for r in rows if not r.get("ok") and r.get("error"))
    error_rate = n_err / n if n else 0.0

    # Latency percentiles (on REAL vendor calls only — exclude cache hits)
    real_latencies = [float(r.get("latency_ms", 0) or 0)
                      for r in rows if not r.get("cache_hit") and r.get("ok")]
    p50 = _percentile(real_latencies, 0.50)
    p95 = _percentile(real_latencies, 0.95)
    p99 = _percentile(real_latencies, 0.99)
    median_lat = median(real_latencies) if real_latencies else 0.0

    # Cost attribution
    total_cost = sum(float(r.get("cost_usd", 0) or 0) for r in rows)
    cost_by_tool = defaultdict(float)
    cost_by_model = defaultdict(float)
    cost_by_tier = defaultdict(float)
    for r in rows:
        c = float(r.get("cost_usd", 0) or 0)
        if r.get("tool"):
            cost_by_tool[r["tool"]] += c
        if r.get("model"):
            cost_by_model[r["model"]] += c
            cost_by_tier[_model_tier(r["model"])] += c

    # Top-10 most expensive turns
    expensive = sorted(rows, key=lambda r: float(r.get("cost_usd", 0) or 0), reverse=True)[:10]
    top_expensive = [
        {
            "timestamp_utc": r.get("timestamp_utc"),
            "tool": r.get("tool"),
            "model": r.get("model"),
            "cost_usd": float(r.get("cost_usd", 0) or 0),
            "tokens_in": int(r.get("tokens_in", 0) or 0),
            "tokens_out": int(r.get("tokens_out", 0) or 0),
        }
        for r in expensive if float(r.get("cost_usd", 0) or 0) > 0
    ]

    # Classifier-label distribution (if forge_runtime adds it to telemetry;
    # currently DelegationCall doesn't carry classifier_label so this is
    # forward-compat — if absent, the count is zero)
    by_classifier = Counter(r.get("classifier_label") for r in rows
                             if r.get("classifier_label"))

    return {
        "n_turns": n,
        "n_ok": n_ok,
        "n_err": n_err,
        "error_rate": round(error_rate, 4),
        "window_start": t_min.isoformat() if t_min else None,
        "window_end": t_max.isoformat() if t_max else None,
        "window_hours": round(window_hours, 2),
        "cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate": round(cache_hit_rate, 4),
            "cost_saved_usd_estimate": round(cost_saved_est, 6),
        },
        "by_tool": dict(by_tool),
        "by_model": dict(by_model),
        "by_tier": dict(by_tier),
        "by_classifier_label": dict(by_classifier) if by_classifier else {},
        "error_codes": dict(err_codes),
        "latency_ms": {
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
            "median": round(median_lat, 1),
            "n_real_calls_excluded_cache": len(real_latencies),
        },
        "cost_usd": {
            "total": round(total_cost, 6),
            "by_tool": {k: round(v, 6) for k, v in sorted(cost_by_tool.items())},
            "by_model": {k: round(v, 6) for k, v in sorted(cost_by_model.items())},
            "by_tier": {k: round(v, 6) for k, v in sorted(cost_by_tier.items())},
        },
        "top_expensive": top_expensive,
    }


# ============================================================================
# Renderers
# ============================================================================

def render_text(summary: dict[str, Any]) -> str:
    """Human-readable text report."""
    if summary.get("n_turns", 0) == 0:
        return "=== FORGE AUDIT ===\n  (no rows in window)\n"

    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("FORGE RUNTIME AUDIT — production observability report")
    lines.append("=" * 78)
    n = summary["n_turns"]
    lines.append(f"n_turns:            {n}  ({summary['n_ok']} ok, {summary['n_err']} errors, "
                 f"error_rate {summary['error_rate']:.2%})")
    lines.append(f"window:             {summary['window_start']} → {summary['window_end']}")
    lines.append(f"                    span = {summary['window_hours']:.2f} hours")
    lines.append("")

    c = summary["cache"]
    lines.append("─── CACHE ───")
    lines.append(f"  hits:             {c['hits']}  ({c['hit_rate']:.2%} of turns)")
    lines.append(f"  misses:           {c['misses']}")
    lines.append(f"  cost saved est:   ${c['cost_saved_usd_estimate']:.6f}")
    lines.append("")

    lines.append("─── BY TOOL ───")
    for tool, n_ in sorted(summary["by_tool"].items(), key=lambda kv: -kv[1]):
        cost = summary["cost_usd"]["by_tool"].get(tool, 0.0)
        lines.append(f"  {tool:<14} {n_:>5}  cost=${cost:.4f}")
    lines.append("")

    lines.append("─── BY MODEL ───")
    for model, n_ in sorted(summary["by_model"].items(), key=lambda kv: -kv[1]):
        cost = summary["cost_usd"]["by_model"].get(model, 0.0)
        lines.append(f"  {model:<30} {n_:>5}  cost=${cost:.4f}")
    lines.append("")

    lines.append("─── BY TIER (cost-band) ───")
    for tier, n_ in sorted(summary["by_tier"].items(), key=lambda kv: -kv[1]):
        cost = summary["cost_usd"]["by_tier"].get(tier, 0.0)
        lines.append(f"  {tier:<10} {n_:>5}  cost=${cost:.4f}")
    lines.append("")

    if summary["error_codes"]:
        lines.append("─── ERRORS ───")
        for err, n_ in sorted(summary["error_codes"].items(), key=lambda kv: -kv[1]):
            pct = (n_ / n) * 100 if n else 0
            lines.append(f"  {err:<24} {n_:>5}  ({pct:.1f}% of turns)")
        lines.append("")

    if summary.get("by_classifier_label"):
        lines.append("─── BY CLASSIFIER LABEL ───")
        for lab, n_ in sorted(summary["by_classifier_label"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  {lab:<10} {n_:>5}")
        lines.append("")

    lat = summary["latency_ms"]
    lines.append(f"─── LATENCY (ms, real calls only, n={lat['n_real_calls_excluded_cache']}) ───")
    lines.append(f"  median:           {lat['median']:>8.1f} ms")
    lines.append(f"  p50:              {lat['p50']:>8.1f} ms")
    lines.append(f"  p95:              {lat['p95']:>8.1f} ms")
    lines.append(f"  p99:              {lat['p99']:>8.1f} ms")
    lines.append("")

    lines.append(f"─── TOTAL COST ───")
    lines.append(f"  ${summary['cost_usd']['total']:.6f}")
    lines.append("")

    if summary["top_expensive"]:
        lines.append(f"─── TOP {min(10, len(summary['top_expensive']))} MOST EXPENSIVE TURNS ───")
        for t in summary["top_expensive"]:
            lines.append(f"  ${t['cost_usd']:.6f}  {t['tool']}/{t['model']}  "
                         f"in={t['tokens_in']} out={t['tokens_out']}  {t['timestamp_utc']}")
    return "\n".join(lines) + "\n"


def render_csv(summary: dict[str, Any]) -> str:
    """Compact CSV of headline metrics — one row, easy to pipe to a dashboard."""
    if summary.get("n_turns", 0) == 0:
        return "n_turns,note\n0,no rows\n"
    fields = [
        ("n_turns", summary["n_turns"]),
        ("n_ok", summary["n_ok"]),
        ("n_err", summary["n_err"]),
        ("error_rate", summary["error_rate"]),
        ("cache_hit_rate", summary["cache"]["hit_rate"]),
        ("cache_hits", summary["cache"]["hits"]),
        ("cache_misses", summary["cache"]["misses"]),
        ("cost_saved_est_usd", summary["cache"]["cost_saved_usd_estimate"]),
        ("total_cost_usd", summary["cost_usd"]["total"]),
        ("latency_p50_ms", summary["latency_ms"]["p50"]),
        ("latency_p95_ms", summary["latency_ms"]["p95"]),
        ("latency_p99_ms", summary["latency_ms"]["p99"]),
        ("window_hours", summary["window_hours"]),
    ]
    header = ",".join(k for k, _ in fields)
    row = ",".join(str(v) for _, v in fields)
    return f"{header}\n{row}\n"


# ============================================================================
# Health gate
# ============================================================================

def evaluate_alerts(summary: dict[str, Any], args) -> list[str]:
    """Return a list of breach messages; empty if all gates pass."""
    if summary.get("n_turns", 0) == 0:
        return []
    breaches: list[str] = []

    if args.alert_cache_hit_min is not None:
        hr = summary["cache"]["hit_rate"]
        if hr < args.alert_cache_hit_min:
            breaches.append(f"cache hit rate {hr:.2%} < threshold {args.alert_cache_hit_min:.2%}")

    if args.alert_error_rate_max is not None:
        er = summary["error_rate"]
        if er > args.alert_error_rate_max:
            breaches.append(f"error rate {er:.2%} > threshold {args.alert_error_rate_max:.2%}")

    if args.alert_cost_day_max is not None:
        # If window > 24h, scale to last-24h cost rate; otherwise use total.
        if summary["window_hours"] >= 24:
            cost_per_24h = summary["cost_usd"]["total"] * (24.0 / summary["window_hours"])
        else:
            cost_per_24h = summary["cost_usd"]["total"]
        if cost_per_24h > args.alert_cost_day_max:
            breaches.append(f"24h cost ${cost_per_24h:.4f} > threshold ${args.alert_cost_day_max:.4f}")

    return breaches


# ============================================================================
# I/O + filtering
# ============================================================================

def load_rows(path: Path, since: datetime | None, until: datetime | None) -> list[dict]:
    rows: list[dict] = []
    n_malformed = 0
    n_missing_required = 0
    n_filtered_out = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            n_malformed += 1
            continue
        if not all(k in r for k in _REQUIRED_FIELDS):
            n_missing_required += 1
            continue
        if since or until:
            ts = _parse_iso(r.get("timestamp_utc", ""))
            if ts is None:
                n_filtered_out += 1
                continue
            if since and ts < since:
                n_filtered_out += 1
                continue
            if until and ts > until:
                n_filtered_out += 1
                continue
        rows.append(r)
    if n_malformed:
        print(f"[forge_audit] skipped {n_malformed} malformed JSON lines", file=sys.stderr)
    if n_missing_required:
        print(f"[forge_audit] skipped {n_missing_required} rows missing required fields",
              file=sys.stderr)
    return rows


# ============================================================================
# Self-test (--smoke)
# ============================================================================

def _smoke_test() -> int:
    """Write 20 synthetic DelegationCall rows + run audit + verify aggregations."""
    import tempfile
    print("=== forge_audit self-test ===")
    fixtures = []
    base_ts = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    # 10 anthropic sonnet successes
    for i in range(10):
        fixtures.append({
            "conv_id": f"c{i}", "turn_id": f"t{i}", "iteration": 1,
            "tool": "claude-api", "model": "claude-sonnet-4-6",
            "prompt_chars": 200, "prompt_redacted_classes": [],
            "max_tokens": 2048, "reason": "general",
            "ok": True, "error": None, "text": "answer",
            "tokens_in": 200, "tokens_out": 100, "cached_tokens": 0,
            "cost_usd": 0.0090, "latency_ms": 5000 + i*200,
            "filler_emitted": True, "cache_hit": False,
            "timestamp_utc": (base_ts + timedelta(minutes=i*5)).isoformat() + "Z",
        })
    # 3 opus successes (more expensive)
    for i in range(3):
        fixtures.append({
            "conv_id": f"o{i}", "turn_id": f"to{i}", "iteration": 1,
            "tool": "claude-api", "model": "claude-opus-4-7",
            "prompt_chars": 300, "prompt_redacted_classes": [],
            "max_tokens": 4096, "reason": "reason-deep",
            "ok": True, "error": None, "text": "deep answer",
            "tokens_in": 300, "tokens_out": 200, "cached_tokens": 0,
            "cost_usd": 0.0195, "latency_ms": 12000 + i*500,
            "filler_emitted": True, "cache_hit": False,
            "timestamp_utc": (base_ts + timedelta(minutes=50 + i*5)).isoformat() + "Z",
        })
    # 3 cache hits (same prompt re-issued)
    for i in range(3):
        fixtures.append({
            "conv_id": f"h{i}", "turn_id": f"th{i}", "iteration": 1,
            "tool": "claude-api", "model": "claude-sonnet-4-6",
            "prompt_chars": 200, "prompt_redacted_classes": [],
            "max_tokens": 2048, "reason": "general",
            "ok": True, "error": None, "text": "answer",
            "tokens_in": 200, "tokens_out": 100, "cached_tokens": 0,
            "cost_usd": 0.0, "latency_ms": 0,
            "filler_emitted": False, "cache_hit": True,
            "timestamp_utc": (base_ts + timedelta(minutes=65 + i)).isoformat() + "Z",
        })
    # 2 auth_fail (openai, no key)
    for i in range(2):
        fixtures.append({
            "conv_id": f"e{i}", "turn_id": f"te{i}", "iteration": 1,
            "tool": "openai-api", "model": "gpt-5-mini",
            "prompt_chars": 100, "prompt_redacted_classes": [],
            "max_tokens": 2048, "reason": "struct",
            "ok": False, "error": "auth_fail", "text": "",
            "tokens_in": 0, "tokens_out": 0, "cached_tokens": 0,
            "cost_usd": 0.0, "latency_ms": 1,
            "filler_emitted": False, "cache_hit": False,
            "timestamp_utc": (base_ts + timedelta(minutes=70 + i)).isoformat() + "Z",
        })
    # 2 upstream_quota (gemini-pro free tier)
    for i in range(2):
        fixtures.append({
            "conv_id": f"q{i}", "turn_id": f"tq{i}", "iteration": 1,
            "tool": "gemini-api", "model": "gemini-2.5-pro",
            "prompt_chars": 400, "prompt_redacted_classes": [],
            "max_tokens": 8192, "reason": "longctx",
            "ok": False, "error": "upstream_quota", "text": "",
            "tokens_in": 0, "tokens_out": 0, "cached_tokens": 0,
            "cost_usd": 0.0, "latency_ms": 800,
            "filler_emitted": True, "cache_hit": False,
            "timestamp_utc": (base_ts + timedelta(minutes=72 + i)).isoformat() + "Z",
        })

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in fixtures:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        tmp_path = Path(f.name)

    try:
        rows = load_rows(tmp_path, since=None, until=None)
        assert len(rows) == 20, f"expected 20 rows, got {len(rows)}"
        s = aggregate(rows)
        # n_turns
        assert s["n_turns"] == 20, s["n_turns"]
        # n_ok / n_err
        assert s["n_ok"] == 16, s["n_ok"]
        assert s["n_err"] == 4, s["n_err"]
        # error rate
        assert s["error_rate"] == 0.2, s["error_rate"]
        # cache hit rate
        assert s["cache"]["hits"] == 3
        assert s["cache"]["hit_rate"] == 0.15, s["cache"]["hit_rate"]
        # cost-saved estimate: 3 cache hits × avg sonnet miss cost ($0.0090)
        assert abs(s["cache"]["cost_saved_usd_estimate"] - (3 * 0.0090)) < 0.0001, \
            s["cache"]["cost_saved_usd_estimate"]
        # by_tool
        assert s["by_tool"] == {"claude-api": 16, "openai-api": 2, "gemini-api": 2}
        # by_tier
        assert s["by_tier"]["sonnet"] == 13  # 10 + 3 cache
        assert s["by_tier"]["opus"] == 3
        # error codes
        assert s["error_codes"] == {"auth_fail": 2, "upstream_quota": 2}
        # total cost (10×0.0090 + 3×0.0195 + 3×0 + 2×0 + 2×0)
        expected_cost = 10 * 0.0090 + 3 * 0.0195
        assert abs(s["cost_usd"]["total"] - expected_cost) < 0.0001, s["cost_usd"]["total"]
        # latency percentiles
        assert s["latency_ms"]["n_real_calls_excluded_cache"] == 13  # 10 sonnet + 3 opus
        assert s["latency_ms"]["p50"] > 0
        assert s["latency_ms"]["p95"] >= s["latency_ms"]["p50"]
        print(f"  ✓ aggregations on 20 fixtures match expected values")

        # Text render
        text = render_text(s)
        assert "FORGE RUNTIME AUDIT" in text
        assert "cache_hit_rate" not in text  # text uses % not field name
        assert "${:.4f}".format(expected_cost) in text or "0.1485" in text
        print(f"  ✓ text renderer produces valid report")

        # CSV render
        csv = render_csv(s)
        assert csv.startswith("n_turns,n_ok,")
        assert csv.split("\n")[1].startswith("20,"), csv.split("\n")[1][:60]
        print(f"  ✓ csv renderer produces valid output")

        # JSON render
        js = json.dumps(s, indent=2)
        assert "n_turns" in js
        print(f"  ✓ json renderer produces valid output")

        # Health gates
        class _Args: pass
        args = _Args()
        args.alert_cache_hit_min = 0.20  # threshold 20%; actual 15% → BREACH
        args.alert_error_rate_max = 0.10  # threshold 10%; actual 20% → BREACH
        args.alert_cost_day_max = None
        breaches = evaluate_alerts(s, args)
        assert len(breaches) == 2, f"expected 2 breaches, got {breaches}"
        print(f"  ✓ health gate detects 2 threshold breaches as expected")

        # No-breach case
        args.alert_cache_hit_min = 0.10  # 15% > 10% — pass
        args.alert_error_rate_max = 0.30  # 20% < 30% — pass
        breaches = evaluate_alerts(s, args)
        assert len(breaches) == 0, f"expected no breaches, got {breaches}"
        print(f"  ✓ health gate passes when thresholds relaxed")

        # Time-window filter — cutoff at base+60min. Rows after cutoff:
        # opus2 (at +60min) + 3 cache hits (+65,66,67) + 2 auth_fail (+70,71)
        # + 2 quota (+72,73) = 8 rows.
        cutoff = base_ts + timedelta(minutes=60)
        windowed = load_rows(tmp_path, since=cutoff, until=None)
        assert len(windowed) == 8, f"expected 8 rows >= +60min, got {len(windowed)}"
        print(f"  ✓ time-window filter: {len(windowed)} rows after cutoff (expected 8)")

    finally:
        tmp_path.unlink()

    print("\n=== forge_audit self-test PASSED ===")
    return 0


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path,
                    help="Path to delegation_log.jsonl (default: state/delegation_log.jsonl)")
    ap.add_argument("--output", choices=["text", "json", "csv"], default="text",
                    help="Output format (default: text)")
    ap.add_argument("--since-hours", type=float, default=None,
                    help="Only include turns from last N hours")
    ap.add_argument("--since", type=str, default=None,
                    help="Only include turns at or after this ISO-8601 timestamp")
    ap.add_argument("--until", type=str, default=None,
                    help="Only include turns before this ISO-8601 timestamp")
    ap.add_argument("--alert-cache-hit-min", type=float, default=None,
                    help="Exit 2 if cache hit rate < threshold (e.g. 0.20)")
    ap.add_argument("--alert-error-rate-max", type=float, default=None,
                    help="Exit 2 if error rate > threshold (e.g. 0.05)")
    ap.add_argument("--alert-cost-day-max", type=float, default=None,
                    help="Exit 2 if 24h-equivalent cost > threshold USD (e.g. 50.00)")
    ap.add_argument("--smoke", action="store_true",
                    help="Run inline self-test on synthetic fixtures (no external file)")
    args = ap.parse_args()

    if args.smoke:
        return _smoke_test()

    if args.input is None:
        args.input = Path("state/delegation_log.jsonl")

    if not args.input.exists():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    # Resolve --since-hours into --since
    if args.since_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
        since_dt = cutoff
    elif args.since:
        since_dt = _parse_iso(args.since)
        if since_dt is None:
            print(f"ERROR: invalid --since timestamp: {args.since}", file=sys.stderr)
            return 1
    else:
        since_dt = None

    until_dt = _parse_iso(args.until) if args.until else None
    if args.until and until_dt is None:
        print(f"ERROR: invalid --until timestamp: {args.until}", file=sys.stderr)
        return 1

    rows = load_rows(args.input, since=since_dt, until=until_dt)
    summary = aggregate(rows)

    # Render
    if args.output == "json":
        print(json.dumps(summary, indent=2))
    elif args.output == "csv":
        print(render_csv(summary), end="")
    else:
        print(render_text(summary), end="")

    # Alerts
    breaches = evaluate_alerts(summary, args)
    if breaches:
        print("", file=sys.stderr)
        print("=== HEALTH GATE BREACHES ===", file=sys.stderr)
        for b in breaches:
            print(f"  ✗ {b}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
