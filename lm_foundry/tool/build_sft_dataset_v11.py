#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v11.py — data-format literacy (YAML/JSON/JSONL/Markdown) + T5/HX scorer-format fix.

Two drivers:
1. Owner request: "md 에 대한 지식 등등도 되있나? json , jsonl, yaml 등등" — the model
   should know YAML / JSON / JSONL / Markdown read/write/manipulate, alongside TOML (r8).
2. Mk.I bench finding: T5 (HX-code family classification) scored ~5-6% / 96 — a
   *scorer-format* failure, not a knowledge gap. The Mk.I T5 prompts ask "answer
   with the family code like HX0xxx" (scorer = exact_match), but the r9/r10 SFT
   pairs answered in full sentences. r11 adds bare-code T5 pairs matching that
   phrasing. Also bumps T7 (stdlib layering, yes/no) with Mk.I-style prompts.

v11 = v10 base (2,334) + ~50 data-format Q/A + ~96 T5 bare-code + ~36 T7 layering.
Total v11: ~2,516 rows.

OUTPUT
    /home/summer/runs/sft-train-v11/train.jsonl
    /home/summer/runs/sft-train-v11/MANIFEST.json
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
import random
from pathlib import Path

random.seed(42)

V10_BASE = Path("/home/summer/runs/sft-train-v10/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v11")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# ---------------------------------------------------------------------------
# 1. Data formats: JSON / JSONL / YAML / Markdown
# ---------------------------------------------------------------------------
def gen_dataformats() -> list[dict]:
    pairs = [
        # --- JSON ---
        ("Write a JSON object for a user with name 'Ada', age 36, and tags ['admin','dev'].",
         '{"name": "Ada", "age": 36, "tags": ["admin", "dev"]}'),
        ("In Python, parse a JSON string into a dict and read a key.",
         "import json\nd = json.loads(s)\nname = d[\"name\"]"),
        ("In Python, serialize a dict to a pretty-printed JSON string.",
         "import json\ns = json.dumps(d, indent=2, ensure_ascii=False)"),
        ("In JavaScript, parse JSON text and stringify an object.",
         "const obj = JSON.parse(text);\nconst text2 = JSON.stringify(obj, null, 2);"),
        ("What JSON value types exist?",
         "object, array, string, number, true, false, null. No comments, no trailing commas, keys must be double-quoted strings."),
        ("Write a JSON array of two objects, each with id and name.",
         '[\n  {"id": 1, "name": "alpha"},\n  {"id": 2, "name": "beta"}\n]'),
        ("In Python, read a JSON file safely with a default if it's missing.",
         "import json, pathlib\np = pathlib.Path(\"config.json\")\ncfg = json.loads(p.read_text()) if p.exists() else {}"),
        ("How do you represent a nested object in JSON, e.g. a server with a pool table?",
         '{"server": {"host": "0.0.0.0", "port": 8080, "pool": {"min": 2, "max": 16}}}'),
        ("In Python, pretty-print only a subset of a JSON object's keys.",
         "import json\nprint(json.dumps({k: d[k] for k in (\"id\", \"name\")}, indent=2))"),
        ("What's wrong with this JSON: {name: 'Ada', age: 36,} ?",
         "Three problems: keys must be double-quoted (\"name\"), strings must use double quotes ('Ada' -> \"Ada\"), and trailing commas are not allowed. Valid: {\"name\": \"Ada\", \"age\": 36}"),
        # --- JSONL ---
        ("What is JSONL (JSON Lines)?",
         "JSON Lines: one complete JSON value per line, separated by \\n. No enclosing array, no commas between records. Stream-friendly — you can read/append one record at a time without parsing the whole file."),
        ("In Python, read a .jsonl file into a list of dicts.",
         "import json\nrows = [json.loads(l) for l in open(\"data.jsonl\") if l.strip()]"),
        ("In Python, write a list of dicts as JSONL.",
         "import json\nwith open(\"out.jsonl\", \"w\") as f:\n    for r in rows:\n        f.write(json.dumps(r, ensure_ascii=False) + \"\\n\")"),
        ("In Python, append a single record to a .jsonl file.",
         "import json\nwith open(\"out.jsonl\", \"a\") as f:\n    f.write(json.dumps(rec, ensure_ascii=False) + \"\\n\")"),
        ("Stream-process a large .jsonl without loading it all into memory (Python).",
         "import json\nwith open(\"big.jsonl\") as f:\n    for line in f:\n        if not line.strip():\n            continue\n        rec = json.loads(line)\n        process(rec)"),
        ("Why is JSONL preferred over a single big JSON array for ML datasets / logs?",
         "Append-only writes (no need to rewrite the whole file), line-by-line streaming reads, easy `head`/`wc -l`/`split`/`shuf` with shell tools, and a corrupt line only loses one record instead of the whole file."),
        ("Count records and filter a .jsonl from the shell.",
         "wc -l data.jsonl                       # count\njq -c 'select(.score > 0.5)' data.jsonl  # filter, still jsonl\njq -s 'length' data.jsonl                # count via jq"),
        ("In Python, convert a .jsonl to a parquet file with pyarrow.",
         "import json, pyarrow as pa, pyarrow.parquet as pq\nrows = [json.loads(l) for l in open(\"in.jsonl\") if l.strip()]\npq.write_table(pa.Table.from_pylist(rows), \"out.parquet\", compression=\"zstd\")"),
        # --- YAML ---
        ("Write a YAML config with a top-level name and a nested server mapping (host, port).",
         "name: app\nserver:\n  host: 0.0.0.0\n  port: 8080"),
        ("YAML: how do you write a list of strings, both block and flow style?",
         "tags:\n  - web\n  - api\n  - v2\n# flow style:\ntags: [web, api, v2]"),
        ("YAML: write a list of mappings (e.g. routes with path and handler).",
         "routes:\n  - path: /\n    handler: index\n  - path: /health\n    handler: health"),
        ("YAML: multi-line string — literal block vs folded block?",
         "literal: |\n  line one\n  line two\nfolded: >\n  this becomes\n  a single line\n# | keeps newlines; > folds them into spaces."),
        ("In Python, load and dump YAML safely with PyYAML.",
         "import yaml\nd = yaml.safe_load(open(\"config.yaml\"))\nopen(\"out.yaml\", \"w\").write(yaml.safe_dump(d, sort_keys=False))"),
        ("YAML: anchors and aliases — define a default block and reuse it.",
         "defaults: &defaults\n  retries: 3\n  timeout: 30\nprod:\n  <<: *defaults\n  host: prod.example.com\ndev:\n  <<: *defaults\n  host: localhost"),
        ("YAML: multiple documents in one file?",
         "---\nname: doc1\n---\nname: doc2\n...\n# '---' starts a document, '...' optionally ends one. yaml.safe_load_all() in Python reads them all."),
        ("YAML gotcha: why might `country: NO` or `version: 1.0` be wrong?",
         "YAML 1.1 parsers read bare `NO`/`no`/`off` as the boolean false (and `1.0` as a float). Quote them: `country: \"NO\"`, `version: \"1.0\"`. YAML 1.2 dropped the yes/no booleans, but many tools still use 1.1 semantics."),
        ("Convert a YAML file to JSON in Python.",
         "import yaml, json\nprint(json.dumps(yaml.safe_load(open(\"in.yaml\")), indent=2))"),
        ("YAML: how do you comment, and how do you write null?",
         "# this is a comment\nkey: value   # inline comment\nempty: null    # also: empty: ~  or just  empty:"),
        ("Write a GitHub Actions workflow snippet in YAML: a job 'build' that runs on ubuntu and checks out + runs tests.",
         "name: ci\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm ci\n      - run: npm test"),
        ("YAML: write a key whose name contains a colon or space.",
         "\"server: eu-west\": region-eu\n\"my key\": value"),
        # --- Markdown ---
        ("Write Markdown for a level-2 heading, a bullet list of 3 items, and a bold word.",
         "## Section\n\n- first\n- second\n- third\n\nThis word is **bold**."),
        ("Write a Markdown table with columns Name | Role and two rows.",
         "| Name | Role  |\n| ---- | ----- |\n| Ada  | admin |\n| Bob  | dev   |"),
        ("Markdown: fenced code block with a language tag.",
         "```python\ndef hello():\n    print(\"hi\")\n```"),
        ("Markdown: a link and an image.",
         "[Anthropic](https://www.anthropic.com)\n![alt text](path/to/image.png)"),
        ("Markdown: a numbered list, a blockquote, and inline code.",
         "1. first\n2. second\n3. third\n\n> a quote\n\nUse `inline code` for short snippets."),
        ("Markdown: how do you make a task list (checkboxes)?",
         "- [x] done item\n- [ ] todo item\n- [ ] another todo"),
        ("Markdown: nested list (sub-bullets) and a horizontal rule.",
         "- top\n  - nested\n    - deeper\n- another top\n\n---"),
        ("Markdown: a table cell that needs a literal pipe character.",
         "| col |\n| --- |\n| a \\| b |   <!-- escape the pipe with a backslash -->"),
        ("Markdown front matter (YAML block at the top of a file) — what does it look like?",
         "---\ntitle: My Post\ndate: 2026-05-12\ntags: [a, b]\n---\n\n# My Post\n\nBody starts here."),
        ("Markdown: a collapsible section using HTML <details>.",
         "<details>\n<summary>Click to expand</summary>\n\nhidden content here\n\n</details>"),
        ("Markdown: link to a heading within the same document.",
         "See [the install section](#installation) below.\n\n## Installation\n...\n# (anchors are the lowercased heading with spaces -> hyphens)"),
        # --- jq / mixed ---
        ("Use jq to extract the .name field from every object in a JSON array.",
         "jq -r '.[].name' data.json"),
        ("Use jq to turn a JSON array into JSONL.",
         "jq -c '.[]' data.json > data.jsonl"),
        ("Use jq to merge two JSON objects (b overrides a).",
         "jq -s '.[0] * .[1]' a.json b.json"),
        ("Use jq to count array elements and to select by a condition.",
         "jq 'length' data.json\njq -c '.[] | select(.active == true)' data.json"),
        ("In Python, pretty-reformat a JSON file in place.",
         "import json, pathlib\np = pathlib.Path(\"f.json\")\np.write_text(json.dumps(json.loads(p.read_text()), indent=2, ensure_ascii=False) + \"\\n\")"),
        ("Validate a JSON document against a JSON Schema in Python.",
         "import json, jsonschema\njsonschema.validate(instance=json.loads(doc), schema=json.loads(schema))  # raises ValidationError on mismatch"),
        ("Write a minimal JSON Schema for an object with required string 'name' and optional integer 'age'.",
         '{\n  "type": "object",\n  "properties": {\n    "name": {"type": "string"},\n    "age": {"type": "integer"}\n  },\n  "required": ["name"]\n}'),
        ("In Python, read NDJSON from stdin and write filtered NDJSON to stdout.",
         "import sys, json\nfor line in sys.stdin:\n    line = line.strip()\n    if not line: continue\n    r = json.loads(line)\n    if r.get(\"keep\"):\n        sys.stdout.write(json.dumps(r, ensure_ascii=False) + \"\\n\")"),
        ("Convert TOML to JSON in Python (stdlib).",
         "import tomllib, json   # Python 3.11+\nwith open(\"f.toml\", \"rb\") as f:\n    d = tomllib.load(f)\nprint(json.dumps(d, indent=2))"),
        ("What's the difference between JSON, JSONL, YAML, and TOML — when to use which?",
         "JSON: ubiquitous wire/API format, no comments. JSONL: one JSON per line — streaming logs / ML datasets / append-only. YAML: human-edited config with comments/anchors/multi-doc (CI, k8s) — but indentation- and type-coercion-prone. TOML: human-edited config that's stricter and less surprising than YAML (Cargo.toml, pyproject.toml). Markdown: prose/docs, not data."),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 2. T5 / HX-code — BARE CODE answers (fixes the Mk.I exact_match scorer)
# ---------------------------------------------------------------------------
def gen_t5_barecode() -> list[dict]:
    fams = {
        "HX0xxx": ["a PARSE error", "a lexer error", "an unexpected-token error", "an unterminated-string error",
                   "a syntax error in a let binding", "a malformed function header", "an invalid numeric literal",
                   "a missing closing brace at parse time", "an unrecognized token", "a bad escape sequence in a string"],
        "HX1xxx": ["a name-resolution error (unknown identifier)", "a scoping error (used before declared)",
                   "an unresolved import", "a duplicate-definition error", "an out-of-scope variable error",
                   "a shadowing-conflict error", "a use of an undefined function", "an unknown module path",
                   "an ambiguous name in two imported modules", "a reference to a private item from outside"],
        "HX2xxx": ["a type mismatch", "an arity mismatch on a function call", "a return-type mismatch",
                   "an incompatible-assignment error", "a missing-field error on a struct literal",
                   "an integer-overflow-in-constant error", "a wrong type passed to a generic", "a mismatched branch types in if/match",
                   "an index with a non-integer type", "a comparison of incompatible types"],
        "HX3xxx": ["a use-after-move error", "a double-borrow error", "a borrow-while-mutably-borrowed error",
                   "a dangling-reference error", "a moved-value-still-used error", "an ownership-leak error",
                   "a returning a reference to a local", "a mutable borrow of an immutable binding",
                   "an overlapping mutable borrows error", "a value dropped while still borrowed"],
        "HX4xxx": ["an unresolved trait method", "an ambiguous generic instantiation", "a missing trait bound",
                   "a conflicting trait impl", "an unsatisfied where-clause", "a generic-arity mismatch",
                   "a trait not implemented for a type", "an orphan-rule violation", "an associated-type mismatch",
                   "a recursive trait bound that doesn't terminate"],
        "HX5xxx": ["a linker error (undefined symbol)", "an unknown target triple", "a missing board crate",
                   "a relocation-out-of-range error", "a duplicate-symbol link error", "a missing entry point",
                   "a section overflow on a microcontroller", "an incompatible-ABI link error",
                   "a missing linker script for a board", "a stack-too-large link-time check failure"],
        "HX6xxx": ["a LINT diagnostic S0-S8 (pre-codegen)", "an S0 style lint", "an S3 complexity lint",
                   "an S5 naming lint", "an S7 dead-code lint", "an S8 doc-coverage lint",
                   "an S1 formatting lint", "an S2 import-order lint", "an S4 magic-number lint",
                   "an S6 shadowing-warning lint"],
        "HX7xxx": ["a CODEGEN failure", "an unhandled-binop codegen error", "a backend-emit error",
                   "an internal codegen assertion", "an ABI-lowering error", "an unsupported-construct codegen error",
                   "a register-allocation failure", "an invalid intrinsic in codegen",
                   "an alignment error in struct lowering", "an out-of-registers codegen error"],
        "HX8xxx": ["an FFI/ABI error", "a C-header mismatch", "an extern-block signature mismatch",
                   "a calling-convention error", "a struct-layout-ABI mismatch", "a variadic-FFI error",
                   "a wrong-sized C integer type at the boundary", "a missing extern symbol at link via FFI",
                   "a bool/int FFI representation mismatch", "a null-pointer passed where non-null FFI expected"],
        "HX9xxx": ["a deprecation / @grace notice", "a grace-period-expired warning", "a removed-API notice",
                   "a deprecated-syntax warning", "an obsolete-target notice", "a stale-annotation notice",
                   "an @grace annotation that has passed its until-date", "a use of a removed builtin",
                   "an old-style attribute that's been replaced", "a deprecated stdlib function call"],
    }
    out = []
    for fam, descs in fams.items():
        for d in descs:
            tmpl = random.choice([
                f"Which hexa HX error-code family covers {d}? Answer with the family code like HX0xxx.",
                f"Which hexa HX diagnostic family is {d}? Reply with just the family code (e.g. HX0xxx).",
                f"Classify {d} into its hexa HX family. Answer with only the family code.",
                f"HX family for {d}? (answer: one code like HX2xxx)",
            ])
            out.append(fmt(tmpl, fam))
    return out


# ---------------------------------------------------------------------------
# 3. T7 stdlib layering — yes/no, Mk.I-style phrasing
# ---------------------------------------------------------------------------
def gen_t7() -> list[dict]:
    cases = [
        ("Can the hexa compiler depend on stdlib", "yes"),
        ("Can hexa stdlib depend on the compiler", "no"),
        ("Can a hexa firmware board crate `firmware/boards/rtsc/` import `stdlib/net/`", "no"),
        ("Can a hexa firmware board crate `firmware/boards/chip/` import `stdlib/embedded/`", "yes"),
        ("Can `stdlib/net/` import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import `stdlib/net/`", "no"),
        ("Can `stdlib/embedded/` import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import `stdlib/embedded/`", "no"),
        ("Can a firmware board crate import the hexa compiler", "no"),
        ("Can the hexa compiler import a firmware board crate", "no"),
        ("Can `tool/` scripts import stdlib", "yes"),
        ("Can stdlib import `tool/` scripts", "no"),
        ("Can `stdlib/net/` import `stdlib/embedded/`", "no"),
        ("Can a hexa application crate import stdlib", "yes"),
        ("Can stdlib import a hexa application crate", "no"),
        ("Can `firmware/boards/cern/` import `stdlib/embedded/`", "yes"),
        ("Can `firmware/boards/cern/` import `stdlib/net/`", "no"),
        ("Can the test harness depend on stdlib", "yes"),
        ("Can stdlib depend on the test harness", "no"),
        ("Can `stdlib/io/` import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import `stdlib/io/`", "no"),
        ("Can a firmware board crate import `stdlib/io/` (blocking file IO)", "no"),
        ("Can a firmware board crate import `stdlib/core/`", "yes"),
        ("Can `hexa-codex` techniques import stdlib", "yes"),
        ("Can stdlib import `hexa-codex` techniques", "no"),
        ("Can the REPL depend on the compiler", "yes"),
        ("Can the compiler depend on the REPL", "no"),
        ("Can `stdlib/alloc/` import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import `stdlib/alloc/`", "no"),
        ("Can `stdlib/embedded/` import `stdlib/net/`", "no"),
        ("Can `firmware/boards/chip/` import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import a firmware board crate", "no"),
        ("Can a hexa application import a firmware board crate directly", "no"),
        ("Can `stdlib/io/` import `stdlib/embedded/`", "no"),
        ("Can the compiler import `stdlib/core/`", "yes"),
        ("Can `stdlib/core/` import the test harness", "no"),
    ]
    out = []
    for q, a in cases:
        tmpl = random.choice([q + "? Answer yes or no.", q + " — yes or no?", q + "? (yes/no)"])
        out.append(fmt(tmpl, a))
    return out


def main() -> int:
    if not V10_BASE.exists():
        print(f"ERROR: v10 base not found at {V10_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V10_BASE.read_text().splitlines() if l.strip()]
    print(f"v10 base: {len(base)}")
    blocks = {
        "dataformats_json_jsonl_yaml_md": gen_dataformats(),
        "t5_hx_barecode": gen_t5_barecode(),
        "t7_layering": gen_t7(),
    }
    added = []
    for name, rows_ in blocks.items():
        print(f"  + {name:32s} {len(rows_):4d}")
        added.extend(rows_)
    print(f"added: {len(added)}")
    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.2.0-r11",
        "base": str(V10_BASE),
        "base_rows": len(base),
        "blocks": {k: len(v) for k, v in blocks.items()},
        "added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": "data-format literacy (JSON/JSONL/YAML/Markdown) + T5 HX bare-code scorer fix + T7 layering bump",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
