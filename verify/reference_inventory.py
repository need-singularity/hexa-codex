#!/usr/bin/env python3
"""
hexa-codex verify/reference_inventory.py — papers/ + formal/ reference annex audit.

Confirms that the cross-cutting references absorbed 2026-05-07
(P1 + P2 papers, P3 Lean proof) are present, carry a @canonical
provenance header, and have an md5 that matches the recorded digest.

If a file's md5 drifts away from the recorded value, this verifier
flags it WARN — the upstream may have evolved and the absorption
needs a refresh from canon.

Run:
    python3 verify/reference_inventory.py
    python3 verify/reference_inventory.py --json
    python3 verify/reference_inventory.py --strict   # md5 drift = FAIL
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# (relative_path, recorded_md5, kind, what_it_proves)
REFERENCES = [
    (
        "papers/n6-ai-17-techniques-experimental-paper.md",
        "145b8b294b396289bdba6a1e6502e290",
        "paper",
        "P1: maps the 17 verbs onto the n=6 σ·φ=n·τ=24 coordinate space",
    ),
    (
        "papers/n6-ai-techniques-68-integrated-paper.md",
        "f4d5616226515ce24baf60b6c280b072",
        "paper",
        "P2: situates 17 verbs inside the wider 68-AI-technique atlas",
    ),
    (
        "formal/lean4/N6/InvariantLattice/Sigma.lean",
        "77da6c22ccd0d2d27782e1fdd26afe42",
        "lean",
        "P3a: σ(n) computable Nat definition (consumer of SigmaLatticeCard)",
    ),
    (
        "formal/lean4/N6/InvariantLattice/SigmaLatticeCard.lean",
        "c8ed2f17322e1e4f9ded8afa697e0317",
        "lean",
        "P3b: F-CL-FORMAL-1 — σ(6)=12 PROVEN (rfl, no sorry)",
    ),
    (
        "papers/n6-ai-ethics-governance-paper.md",
        "8cb6ae2ddbf503aa5597b1e853cf3258",
        "paper",
        "P4: ai-ethics+governance σ·φ=24 overlay (atlas.n6 0/24 EXACT, MATURITY=LOW)",
    ),
    (
        "papers/n6-governance-safety-urban-paper.md",
        "cf976a760eb0128f19372060ce57960f",
        "paper",
        "P5: governance+safety+urban σ·φ=24 overlay (atlas.n6 58/58 EXACT, MATURITY=HIGH)",
    ),
    (
        "consciousness/measurement-protocol.md",
        "89486e86358b5896a78508328b13e1b1",
        "verb-deepdive",
        "consciousness deep-dive — BT-19 α_IIT·α_GWT=1 reproducible EEG/fMRI protocol (PAPER-P8-2)",
    ),
    (
        "consciousness/red-team-failure.md",
        "3fe1ec4b5b8d4a92a2772aa4e2b423cf",
        "verb-deepdive",
        "consciousness deep-dive — BT-19 red-team refutation (verdict MISS, [7?]→[5] downgrade, falsifier discipline demo)",
    ),
]


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _has_canonical(path: Path) -> bool:
    head = path.read_text(encoding="utf-8")[:1024]
    return "@canonical" in head and "canon@" in head


def _has_md5_at_extraction(path: Path) -> bool:
    head = path.read_text(encoding="utf-8")[:1024]
    return bool(re.search(r"@md5_at_extraction:\s*[0-9a-f]{32}", head))


def evaluate() -> dict:
    rows = []
    for relpath, recorded_md5, kind, what in REFERENCES:
        path = ROOT / relpath
        present = path.exists()
        if not present:
            rows.append({
                "path": relpath, "kind": kind, "what": what,
                "present": False, "current_md5": None,
                "recorded_md5": recorded_md5,
                "drift": None, "has_canonical": False,
                "has_md5_recorded": False,
                "status": "MISSING",
            })
            continue
        cur = _md5(path)
        # Note: recorded_md5 is the digest of the *upstream* file at extraction.
        # After we inject the @canonical header, the local file's md5 will
        # differ — that is expected. We compare AFTER stripping the local
        # 4-line header block (`<!-- @canonical|@extracted|@md5|@absorbed -->`
        # for .md, or `-- @...` for .lean).
        stripped = _strip_local_header(path)
        stripped_md5 = hashlib.md5(stripped.encode("utf-8")).hexdigest()
        drift = stripped_md5 != recorded_md5
        rows.append({
            "path": relpath, "kind": kind, "what": what,
            "present": True,
            "current_md5":          cur,
            "stripped_md5":         stripped_md5,
            "recorded_md5":         recorded_md5,
            "drift":                drift,
            "has_canonical":        _has_canonical(path),
            "has_md5_recorded":     _has_md5_at_extraction(path),
            "status": "DRIFT" if drift else "OK",
        })
    checks = {
        "all_present":        all(r["present"] for r in rows),
        "all_have_canonical": all(r["has_canonical"] for r in rows if r["present"]),
        "all_have_md5":       all(r["has_md5_recorded"] for r in rows if r["present"]),
        "no_drift":           all(not r.get("drift") for r in rows if r["present"]),
    }
    return {"rows": rows, "checks": checks, "all_ok": all(checks.values())}


def _strip_local_header(path: Path) -> str:
    """Strip the 4-line @canonical / @extracted / @md5_at_extraction /
    @absorbed_into header block we inject on absorption, plus the optional
    blank/closing line. Returns the upstream-equivalent text."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        # HTML-comment headers: skip leading lines that start with `<!-- @`
        out = []
        for ln in text.splitlines(keepends=True):
            if ln.startswith("<!-- @canonical") or ln.startswith("<!-- @extracted") \
               or ln.startswith("<!-- @md5_at_extraction") \
               or ln.startswith("<!-- @absorbed_into"):
                continue
            out.append(ln)
        return "".join(out)
    if path.suffix == ".lean":
        out = []
        for ln in text.splitlines(keepends=True):
            if ln.startswith("-- @canonical") or ln.startswith("-- @extracted") \
               or ln.startswith("-- @md5_at_extraction") \
               or ln.startswith("-- @absorbed_into"):
                continue
            out.append(ln)
        # also collapse leading "--\n" inserted as separator
        joined = "".join(out)
        return joined.replace("-- \n--\n", "--\n", 1) if joined.startswith("-- \n") else joined
    return text


def _print_human(r: dict, strict: bool) -> int:
    print("=" * 78)
    print("  hexa-codex — reference-annex inventory (papers/ + formal/)")
    print("=" * 78)
    for row in r["rows"]:
        mark = {
            "OK":      "ok ",
            "DRIFT":   "WARN",
            "MISSING": "FAIL",
        }.get(row["status"], "??")
        print(f"  [{mark}] {row['path']}")
        print(f"         · kind:        {row['kind']}")
        print(f"         · what:        {row['what']}")
        print(f"         · present:     {row['present']}")
        if row["present"]:
            print(f"         · canonical:   {row['has_canonical']}")
            print(f"         · md5_record:  {row['has_md5_recorded']}")
            print(f"         · stripped:    {row['stripped_md5']}")
            print(f"         · recorded:    {row['recorded_md5']}")
            if row["drift"]:
                print(f"         · drift:       upstream changed since 2026-05-07 — refresh")
    print("=" * 78)
    for k, ok in r["checks"].items():
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {k}")
    drifted = [row for row in r["rows"] if row.get("drift")]
    if drifted:
        if strict:
            print("  --strict: drift treated as FAIL")
            return 1
        print("  drift markers — upstream may have evolved; refresh when ready")
    return 0 if r["all_ok"] else 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex reference-annex inventory")
    p.add_argument("--json",   action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="treat md5 drift as FAIL (default WARN)")
    a = p.parse_args(argv[1:])
    r = evaluate()
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["all_ok"] else 1
    return _print_human(r, strict=a.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
