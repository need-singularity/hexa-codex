#!/usr/bin/env python3
"""
hexa-codex verify/release_ladder.py — v1.0.0 → v2.0.0 release-cadence audit.

Mirrors hexa-sscb's mk_ladder.py — confirms monotone progression of:
  - verbs_wired      strictly non-decreasing  (more wired over time)
  - eval_pipelines   strictly non-decreasing
  - year             strictly non-decreasing

And cross-references the release table in .roadmap.hexa_codex §A.2.

Run:
    python3 verify/release_ladder.py            # exit 0 = monotone
    python3 verify/release_ladder.py --json
    python3 verify/release_ladder.py --table    # summary table only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_params import RELEASE_PARAMS, get  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / ".roadmap.hexa_codex"


VERSION_ORDER = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v2.0.0"]


def _year_month_to_key(s: str) -> tuple[int, int]:
    """Convert '2026-05', '~2026-08', '2027-Q2' to a (year, month) tuple
    suitable for monotone comparison."""
    s = s.strip().lstrip("~")
    m = re.match(r"(\d{4})-Q(\d)", s)
    if m:
        y = int(m.group(1)); q = int(m.group(2))
        return (y, q * 3 - 2)   # Q1→Jan, Q2→Apr, Q3→Jul, Q4→Oct
    m = re.match(r"(\d{4})-(\d{1,2})", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def evaluate() -> dict:
    rows = []
    for v in VERSION_ORDER:
        p = get(v)
        in_roadmap = False
        if ROADMAP.exists():
            text = ROADMAP.read_text(encoding="utf-8")
            # The roadmap table uses several status idioms — RELEASED, TARGET,
            # ASPIRATIONAL (uppercase), and lowercase "planned" for in-between
            # rows. Accept any of them so v1.2.0/v1.3.0 (status=PLANNED in our
            # registry, "planned" in the table) match cleanly.
            tokens = {p["status"], p["status"].lower(),
                      "TARGET", "RELEASED", "ASPIRATIONAL", "planned"}
            in_roadmap = (v in text) and any(t in text for t in tokens)
        rows.append({
            "version":         v,
            "year_month":      p["year_month"],
            "year_month_key":  list(_year_month_to_key(p["year_month"])),
            "status":          p["status"],
            "group_focus":     p["group_focus"],
            "verbs_wired":     p["verbs_wired"],
            "eval_pipelines":  p["eval_pipelines"],
            "milestone":       p["milestone"],
            "in_roadmap":      in_roadmap,
        })

    # monotonicity
    yk = [tuple(r["year_month_key"]) for r in rows]
    vw = [r["verbs_wired"] for r in rows]
    ep = [r["eval_pipelines"] for r in rows]

    checks = {
        "year_strictly_non_decreasing":   all(yk[i] <= yk[i+1] for i in range(len(rows)-1)),
        "verbs_wired_non_decreasing":     all(vw[i] <= vw[i+1] for i in range(len(rows)-1)),
        "eval_pipelines_non_decreasing":  all(ep[i] <= ep[i+1] for i in range(len(rows)-1)),
        "v1_0_is_released":               rows[0]["status"] == "RELEASED",
        "v2_0_is_aspirational":           rows[-1]["status"] == "ASPIRATIONAL",
        "every_version_in_roadmap":       all(r["in_roadmap"] for r in rows),
        "v2_wires_all_17_verbs":          rows[-1]["verbs_wired"] == 17,
    }

    return {"rows": rows, "checks": checks, "all_ok": all(checks.values())}


def _print_table(rows: list[dict]) -> None:
    print(f"  {'version':<8}  {'date':<8}  {'status':<14}  {'group':<10}  {'wired':>5}  "
          f"{'eval':>4}  milestone")
    print(f"  {'-'*8}  {'-'*8}  {'-'*14}  {'-'*10}  {'-'*5}  {'-'*4}  {'-'*40}")
    for r in rows:
        ms = r["milestone"]
        if len(ms) > 50:
            ms = ms[:47] + "..."
        in_doc = "✓" if r["in_roadmap"] else "·"
        print(f"  {r['version']:<8}  {r['year_month']:<8}  {r['status']:<14}  "
              f"{r['group_focus']:<10}  {r['verbs_wired']:>5}  "
              f"{r['eval_pipelines']:>4}  {in_doc}  {ms}")


def _print_human(result: dict, table_only: bool) -> int:
    print("=" * 110)
    print("  hexa-codex release ladder — v1.0.0 → v2.0.0 monotonicity")
    print("=" * 110)
    _print_table(result["rows"])
    if table_only:
        return 0 if result["all_ok"] else 1
    print()
    for k, ok in result["checks"].items():
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {k}")
    print("=" * 110)
    if result["all_ok"]:
        print("  release ladder monotone — verbs_wired ↑, eval ↑, year ↑.")
        return 0
    print("  release ladder violation.")
    return 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex release-ladder verifier")
    p.add_argument("--json",  action="store_true")
    p.add_argument("--table", action="store_true")
    a = p.parse_args(argv[1:])
    r = evaluate()
    if a.json:
        print(json.dumps({
            "tool": "hexa-codex verify/release_ladder.py",
            "schema": "hexa-codex/release-ladder/v1",
            "ok": r["all_ok"], **r,
        }, indent=2, ensure_ascii=False))
        return 0 if r["all_ok"] else 1
    return _print_human(r, table_only=a.table)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
