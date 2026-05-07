#!/usr/bin/env python3
"""
hexa-codex verify/verb_query.py — verb info / spec lookup tool.

Convenient query surface over the 17-verb table. Mirrors hexa-sscb's
verify/atlas_query.py (different domain — verbs instead of atlas anchors).

Examples:
    python3 verify/verb_query.py                 # tabular list of all 17
    python3 verify/verb_query.py alignment       # single verb info
    python3 verify/verb_query.py --group safety  # group filter
    python3 verify/verb_query.py --json --group economics
    python3 verify/verb_query.py --path safety/ai-safety.md  # reverse lookup
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_inventory import VERB_TABLE, GROUP_EXPECTED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def info(group: str, verb: str, relpath: str) -> dict:
    path = ROOT / relpath
    out: dict = {"group": group, "verb": verb, "path": relpath, "present": path.exists()}
    if path.exists():
        text = path.read_text(encoding="utf-8")
        out["lines"] = text.count("\n")
        out["size_bytes"] = len(text.encode("utf-8"))
        # find first H1
        h1 = re.search(r"(?m)^#\s+(\S.*)$", text)
        out["title"] = h1.group(1).strip() if h1 else None
        # canonical provenance
        canon = re.search(r"@canonical:\s*(\S+)", text[:1024])
        out["canonical"] = canon.group(1) if canon else None
        # falsifier mention count (rough proxy for spec maturity)
        out["falsifier_mentions"] = text.lower().count("falsifier")
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="hexa-codex verb info/lookup")
    p.add_argument("verb", nargs="?", help="single verb to inspect")
    p.add_argument("--group", help="filter by group (safety/economics/ops/substrate)")
    p.add_argument("--path",  help="reverse lookup by relative path")
    p.add_argument("--json",  action="store_true")
    a = p.parse_args(argv[1:])

    rows = [(g, v, rp) for g, v, rp in VERB_TABLE]
    if a.group:
        rows = [r for r in rows if r[0] == a.group]
        if not rows:
            print(f"unknown group: {a.group!r} (valid: {list(GROUP_EXPECTED)})", file=sys.stderr)
            return 2
    if a.path:
        rows = [r for r in rows if r[2] == a.path]
        if not rows:
            print(f"no verb found at path {a.path!r}", file=sys.stderr)
            return 2
    if a.verb:
        rows = [r for r in rows if r[1] == a.verb]
        if not rows:
            print(f"unknown verb: {a.verb!r}", file=sys.stderr)
            return 2

    detailed = [info(*r) for r in rows]

    if a.json:
        print(json.dumps(detailed, indent=2, ensure_ascii=False))
        return 0

    if a.verb or len(detailed) == 1:
        for d in detailed:
            print(f"  verb:        {d['verb']}")
            print(f"  group:       {d['group']}")
            print(f"  path:        {d['path']}")
            print(f"  present:     {d['present']}")
            if d.get("title"):
                print(f"  title:       {d['title']}")
            if d.get("canonical"):
                print(f"  canonical:   {d['canonical']}")
            if d.get("lines") is not None:
                print(f"  lines:       {d['lines']}")
                print(f"  size:        {d['size_bytes']} bytes")
                print(f"  falsifiers:  {d['falsifier_mentions']} mention(s)")
        return 0

    print("=" * 90)
    print(f"  hexa-codex — verb table")
    print("=" * 90)
    print(f"  {'group':<10}  {'verb':<14}  {'lines':>6}  title")
    print(f"  {'-'*10}  {'-'*14}  {'-'*6}  {'-'*40}")
    for d in detailed:
        title = d.get("title") or "(no H1)"
        if len(title) > 60:
            title = title[:57] + "..."
        lines = d.get("lines", 0) if d["present"] else "MISS"
        print(f"  {d['group']:<10}  {d['verb']:<14}  {lines:>6}  {title}")
    print("=" * 90)
    print(f"  {len(detailed)} verb(s) shown")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
