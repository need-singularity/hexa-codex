#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""hf_publish.py — single CLI for publishing hexa-forge artefacts to dancinlab/* on HuggingFace.

Phase v0.1.3 G-BASE deliverable. Implements the eight enumerated upload
targets in `papers/plan-runbook-v0.1.3.md §5` (the post-bench / post-SFT
table) using HF auth routed via `mac-exec` (token never lands on Linux
disk; injected into the child process env as `HUGGING_FACE_HUB_TOKEN`).

WHAT
----
A single CLI with five entry points:

  list-targets         pretty-print the 8 targets + per-target source ✓/✗
  dry-run    --target  show the upload plan (hf_repo, files, bytes, README)
                       — no auth check, no network
  verify     --target  same as dry-run + ping `HfApi.whoami()` to confirm
                       token validity + dancinlab org access (no upload)
  upload     --target  actual `HfApi.create_repo(exist_ok=False)` +
                       `upload_folder()` ; writes audit log under logs/
  --selftest           synthesise mock target with monkey-patched HfApi
                       and exercise all four subcommands

THE EIGHT TARGETS
-----------------
Per `papers/plan-runbook-v0.1.3.md §5`:

    stack-v2-sample  dancinlab/hexa-forge-corpus-stack-v2-sample-v0.1.3   dataset
    tokenizer        dancinlab/hexa-forge-tokenizer-qwen-hexa-v1          model
    cold-bench       dancinlab/hexa-forge-bench-cold-v0.1.3                dataset
    sft-lora-r16     dancinlab/hexa-forge-code-7b-qwen2.5-lora-r16-v0.2.0  model
    fullft           dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0    model
    gguf-q5          dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0       model
    mlx              dancinlab/hexa-forge-code-7b-MLX-v1.0.0               model
    eval-results     dancinlab/hexa-forge-eval-results-v1.0.0              dataset

AUTH FLOW (invariants from runbook §1)
--------------------------------------
1. Token sourced exclusively from `HUGGING_FACE_HUB_TOKEN` env var.
2. `verify` and `upload` resolve token + call `whoami()` ; refuse if the
   account is not a member of (or is not) `dancinlab`.
3. Token never written to logs / outbox / runs. The audit log records
   `token_hash_12 = sha256(token).hexdigest()[:12]` for cross-correlation.

WRITE-ONCE INVARIANT
--------------------
`upload` calls `create_repo(exist_ok=False)` first. If the repo already
exists, the tool errors out with a clear remediation hint and exits 2.
Pass `--force` to allow `upload_folder()` against the existing repo
(additive-only ; `delete_patterns=[]`).

AUDIT LOG SCHEMA
----------------
`logs/hf_publish.<YYYY-MM-DD>.jsonl` — one JSON line per subcommand
invocation that has externally observable effects (verify / upload).
Fields: ts_utc, subcommand, target, hf_repo, forge_commit, file_count,
total_bytes, token_hash_12, result, error_class, duration_ms.

TODO_v1_0_0
-----------
git-LFS handling is intentionally NOT in this round. Model-weight
targets (sft-lora-r16, fullft, gguf-q5, mlx) ship at v0.2.0+ ; LFS
configuration + Q5_K_M / MLX shard layout will land alongside the
serving handoff harness. See `papers/plan-runbook-v0.1.3.md §5` and
`tool/serving_handoff.py` (pending) for the v1.0.0 boundary.

USAGE
-----
    # All four entry points are designed to be wrapped by mac-exec:
    mac-exec --hf-passthrough python3 tool/hf_publish.py list-targets
    mac-exec --hf-passthrough python3 tool/hf_publish.py dry-run --target stack-v2-sample
    mac-exec --hf-passthrough python3 tool/hf_publish.py verify --target stack-v2-sample
    mac-exec --hf-passthrough python3 tool/hf_publish.py upload --target stack-v2-sample

    # selftest works without mac-exec / network / token:
    python3 tool/hf_publish.py --selftest

SEE ALSO
--------
- `papers/plan-runbook-v0.1.3.md` §1-§6 — auth routing, invariants, and
  the authoritative upload-target table.
- `ROADMAP.md` §3 — bidirectional loop with hexa-codex.
- `tool/license_clean_scan.py` — license provenance feeds README.md.
- `tool/stack_v2_sample.py` — produces the stack-v2-sample source path.
- `tool/extend_tokenizer.py` — produces the tokenizer source path.
- `tool/eval_lineage.py audit` — produces the eval-results rollup.
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
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LOGS_DIR: pathlib.Path = REPO_ROOT / "logs"
TOOL_NAME = "hf_publish.py"
TOOL_VERSION = "0.1.3"

DANCINLAB_ORG = "dancinlab"
HF_TOKEN_ENV = "HUGGING_FACE_HUB_TOKEN"

# Reasonable safety bar for any single target's upload. Override per-target
# below ; callers can also pass `--force-size` to ignore the bar at upload.
DEFAULT_MAX_SIZE_MB = 5_000  # 5 GB


# ---------------------------------------------------------------------------
# README templates (one per target ; brief required all 8)
#
# Each template is rendered with `.format(**fields)` against runtime
# fields (forge_commit, file_count, total_bytes_human, run_id_or_dash,
# license, hf_repo, source_path_display, date_iso, license_audit_block).
# The same set of keyword arguments is passed to every template — any
# template that does not need a given field simply ignores it.
# ---------------------------------------------------------------------------

README_TEMPLATE_STACK_V2_SAMPLE = """---
license: apache-2.0
language:
  - code
tags:
  - hexa-forge
  - the-stack-v2
  - permissive
  - code
  - python
  - rust
  - typescript
  - go
  - c
  - zig
size_categories:
  - 1M<n<10M
pretty_name: hexa-forge Stack v2 5% permissive sample (v0.1.3)
---

# hexa-forge — Stack v2 5% permissive sample (v0.1.3)

**Repository:** `{hf_repo}`
**Phase:** v0.1.3 G-BASE (`RESEARCH_FIRST`)
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

Deterministic 5% sample of the `bigcode/the-stack-v2` permissive subset
across the hexa-forge core languages: Python, Rust, TypeScript, Go, C,
Zig. Produced by `tool/stack_v2_sample.py` ; selection is by stable
BLAKE2b hash of `repo/path` (seed 42), so the sample is reproducible
from the same source snapshot.

Companion to `papers/datasets-source-manifest.md` STRUCT row
`pretrain-bias`. Used to validate the ~600B-token estimate by direct
measurement on the sampled subset and extrapolation to 100%.

## Files

- `{file_count}` payload files
- total size: `{total_bytes_human}`
- per-language directory layout: `python/`, `rust/`, `typescript/`,
  `go/`, `c/`, `zig/`
- `licenses.jsonl` sidecar per language (repo, path, license,
  permissive) for provenance
- `runs/stack_v2_sample.json` (when present) — aggregate token counts

## License

Each file inherits its upstream license tag from `the-stack-v2`'s
`permissive` config. The aggregate is permissive-only ; see
`licenses.jsonl` for the per-file tag.

This dataset card is `{license}`.

## Provenance

{license_audit_block}

## Cross-reference

- `papers/plan-runbook-v0.1.3.md` §4.1 — generation step
- `papers/datasets-source-manifest.md` — STRUCT row
- `tool/license_clean_scan.py` — gate that produced the audit block above

## RESEARCH_FIRST notice

This artefact is a v0.1.x research deliverable. The full corpus, the
final tokenizer, and any model weights derived from this sample will
land at v1.0.0 with `RELEASE` semantics.
"""

README_TEMPLATE_TOKENIZER = """---
license: apache-2.0
tags:
  - hexa-forge
  - tokenizer
  - qwen
  - extended
language:
  - en
  - code
pretty_name: hexa-forge Qwen2.5-Coder + hexa extension v1
---

# hexa-forge — extended tokenizer (Qwen2.5-Coder base + hexa-lang ext v1)

**Repository:** `{hf_repo}`
**Phase:** v0.1.3 G-BASE
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

The base `Qwen/Qwen2.5-Coder-7B` tokenizer with a hexa-lang token
extension applied per `tool/tokenizer_extension.toml`. Produced by
`tool/extend_tokenizer.py` ; round-trip verified to 100% and tuned to
≤ 0.5× compression ratio on the hexa source sample (per runbook §4.4 /
D-008 close criterion).

## Files

- `{file_count}` tokenizer artefacts (`tokenizer.json`, `tokenizer_config.json`, vocab + merges if applicable)
- total size: `{total_bytes_human}`
- extension manifest hash recorded in the `extension_manifest_hash`
  field of `tokenizer_config.json`

## License

This artefact is `{license}`. The base Qwen2.5-Coder tokenizer carries
Qwen's own license terms ; this extension does not redistribute the
base weights, only the tokenizer files derived from the base
tokenizer + the extension TOML.

## Provenance

{license_audit_block}

## Cross-reference

- `papers/plan-runbook-v0.1.3.md` §4.4 — generation step
- `tool/tokenizer_extension.toml` — the extension manifest (hexa-lang tokens)
- `tool/extend_tokenizer.py` — the tool that produced this artefact

## Compatibility

Loadable via `transformers.AutoTokenizer.from_pretrained("{hf_repo}")`
once the upload completes.
"""

README_TEMPLATE_COLD_BENCH = """---
license: apache-2.0
tags:
  - hexa-forge
  - benchmark
  - eval
  - cold-bench
pretty_name: hexa-forge cold benchmark (v0.1.3, 3 models × 6 specs)
---

# hexa-forge — cold benchmark (v0.1.3)

**Repository:** `{hf_repo}`
**Phase:** v0.1.3 G-BASE (`RESEARCH_FIRST`)
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

Cold-start benchmark of 3 candidate base models on the 6 hexa-forge
evaluation specs, run before any SFT. Closes D-007 (base-model
selection) per `papers/plan-decisions-pending.md`.

**Models evaluated:** Qwen2.5-Coder-7B, DeepSeek-Coder-V2-Lite,
StarCoder2-15B.

**Specs:** `hexa-eval`, `5nl-eval`, `db-eval`, `firmware-eval`,
`frontend-eval`, `safety-eval` (see `papers/spec-*-eval.md`).

## Files

- `{file_count}` artefact files (per-run JSON outputs + aggregate table)
- total size: `{total_bytes_human}`
- Layout: `runs/<spec>/<model-slug>/<run-id>/result.json` plus a
  top-level `aggregate.json` with the comparative table.

## License

This artefact is `{license}`. Benchmark task data licenses are tracked
in each spec doc and in `licenses.jsonl` per run.

## Provenance

{license_audit_block}

## Cross-reference

- `papers/plan-runbook-v0.1.3.md` §4.3 — generation step
- `papers/spec-{{hexa,five-nl,db,firmware,frontend,safety}}-eval.md` — task specs
- `tool/run_eval.py` — driver
- `tool/eval_lineage.py audit` — lineage rollup used to compose the aggregate

## RESEARCH_FIRST notice

These numbers are pre-SFT cold-bench. Comparative ranking informs D-007
but does not encode any production claim.
"""

README_TEMPLATE_SFT_LORA_R16 = """---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B
tags:
  - hexa-forge
  - sft
  - lora
  - peft
  - code
library_name: peft
pretty_name: hexa-forge code-7b Qwen2.5 LoRA r=16 (v0.2.0)
---

# hexa-forge — code-7b Qwen2.5 LoRA r=16 (v0.2.0)

**Repository:** `{hf_repo}`
**Phase:** v0.2.0 SFT
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

First-pass SFT checkpoint — LoRA adapter with r=16 (per D-NEW-TC-C
default) over `Qwen/Qwen2.5-Coder-7B`. Trained on the hexa-forge
permissive corpus (see `papers/datasets-source-manifest.md`).

## Files

- `{file_count}` adapter artefacts (`adapter_model.safetensors`,
  `adapter_config.json`, training config + metrics)
- total size: `{total_bytes_human}`
- LFS-tracked: yes (deferred TODO_v1_0_0 — see tool docstring)

## License

This adapter is `{license}`. The base model `Qwen/Qwen2.5-Coder-7B`
carries Qwen's license — see the upstream model card.

## Provenance

{license_audit_block}

## Cross-reference

- `docs/code-llm.md` §STRUCT — training recipe
- `papers/plan-decisions-pending.md` D-NEW-TC-C — LoRA rank choice
- `tool/run_eval.py` — companion eval driver

## RESEARCH_FIRST notice

v0.2.0 = first SFT checkpoint. v1.0.0 ships a full-FT reproducibility
checkpoint (separate repo, see `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`).
"""

README_TEMPLATE_FULLFT = """---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B
tags:
  - hexa-forge
  - fullft
  - code
pretty_name: hexa-forge code-7b Qwen2.5 full-FT (v1.0.0)
---

# hexa-forge — code-7b Qwen2.5 full-FT (v1.0.0)

**Repository:** `{hf_repo}`
**Phase:** v1.0.0 RELEASE
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

Full fine-tune reproducibility checkpoint, the v1.0.0 acceptance-gate
⑪ deliverable per `ROADMAP.md §2`. Base `Qwen/Qwen2.5-Coder-7B` ; full
weights (no LoRA).

## Files

- `{file_count}` weight + config artefacts
- total size: `{total_bytes_human}`
- LFS-tracked: yes (deferred TODO_v1_0_0 — see tool docstring)

## License

This weight set is `{license}`. The Qwen2.5-Coder base license applies
to the inherited weight components — see the upstream model card.

## Provenance

{license_audit_block}

## Cross-reference

- `ROADMAP.md` §2 gate ⑪ — full-FT reproducibility checkpoint
- `docs/code-llm.md` §STRUCT — training recipe
- `dancinlab/hexa-forge-eval-results-v1.0.0` — evaluation numbers

## RELEASE notice

This is a v1.0.0 release artefact. Pin to the forge commit + dataset
hash recorded above for reproducibility.
"""

README_TEMPLATE_GGUF_Q5 = """---
license: apache-2.0
base_model: dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0
tags:
  - hexa-forge
  - gguf
  - quantised
  - q5_k_m
  - llama.cpp
pretty_name: hexa-forge code-7b Q5_K_M GGUF (v1.0.0)
---

# hexa-forge — code-7b Q5_K_M GGUF (v1.0.0)

**Repository:** `{hf_repo}`
**Phase:** v1.0.0 RELEASE — quantised laptop tier
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

Q5_K_M-quantised GGUF build of the full-FT v1.0.0 checkpoint for
llama.cpp / Ollama / LM Studio. Targets the "laptop tier" per
`docs/code-llm.md §VERIFY`. Produced by `tool/serving_handoff.py`.

## Files

- `{file_count}` GGUF shard(s) + tokenizer
- total size: `{total_bytes_human}`
- LFS-tracked: yes (deferred TODO_v1_0_0 — see tool docstring)

## License

This artefact is `{license}`. Derived from
`dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0` via lossy
quantisation — semantics preserved up to Q5_K_M precision bounds.

## Provenance

{license_audit_block}

## Cross-reference

- `docs/code-llm.md` §VERIFY — laptop-tier deployment recipe
- `tool/serving_handoff.py` — quantisation driver
- Source weights: `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`

## RELEASE notice

Quantised. Use `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`
for full-precision evaluation parity.
"""

README_TEMPLATE_MLX = """---
license: apache-2.0
base_model: dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0
tags:
  - hexa-forge
  - mlx
  - apple-silicon
  - code
pretty_name: hexa-forge code-7b MLX (v1.0.0)
---

# hexa-forge — code-7b MLX (v1.0.0)

**Repository:** `{hf_repo}`
**Phase:** v1.0.0 RELEASE — Apple-silicon tier
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

MLX-converted build of the full-FT v1.0.0 checkpoint for Apple-silicon
laptops (M-series). Produced by `tool/serving_handoff.py` via the MLX
conversion path.

## Files

- `{file_count}` MLX shard(s) + tokenizer
- total size: `{total_bytes_human}`
- LFS-tracked: yes (deferred TODO_v1_0_0 — see tool docstring)

## License

This artefact is `{license}`. Derived from
`dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0` via the MLX
conversion path (no quantisation).

## Provenance

{license_audit_block}

## Cross-reference

- `tool/serving_handoff.py` — MLX conversion driver
- Source weights: `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`
- MLX runtime: https://github.com/ml-explore/mlx

## RELEASE notice

Apple-silicon target. Q5_K_M GGUF available at
`dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0` for non-Mac laptops.
"""

README_TEMPLATE_EVAL_RESULTS = """---
license: apache-2.0
tags:
  - hexa-forge
  - eval
  - results
  - benchmark
  - aggregate
pretty_name: hexa-forge evaluation results (v1.0.0 aggregate)
---

# hexa-forge — evaluation results (v1.0.0)

**Repository:** `{hf_repo}`
**Phase:** v1.0.0 RELEASE
**Forge commit:** `{forge_commit}`
**Generated:** {date_iso}

## What this is

Aggregated evaluation results across all 6 hexa-forge specs for the
v1.0.0 release. Produced by `tool/eval_lineage.py audit` ; satisfies
ROADMAP §2 acceptance gates that mention eval numbers.

**Specs aggregated:** `hexa-eval`, `5nl-eval`, `db-eval`,
`firmware-eval`, `frontend-eval`, `safety-eval`.

## Files

- `{file_count}` per-spec result JSONs + a top-level `aggregate.json`
  + a per-spec markdown summary
- total size: `{total_bytes_human}`

## License

This artefact is `{license}`. Benchmark task data licenses follow
their upstream sources ; see each spec doc.

## Provenance

{license_audit_block}

## Cross-reference

- `tool/eval_lineage.py` — lineage + audit tool
- `papers/spec-*-eval.md` — per-spec definitions
- Source weights evaluated:
  - `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`
  - `dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0`
  - `dancinlab/hexa-forge-code-7b-MLX-v1.0.0`

## RELEASE notice

Numbers in `aggregate.json` are the v1.0.0 reference set. Future
releases (v1.1+) append rather than overwrite.
"""


# ---------------------------------------------------------------------------
# Target definitions — the eight rows of papers/plan-runbook-v0.1.3.md §5
# ---------------------------------------------------------------------------

TARGETS: Dict[str, Dict[str, Any]] = {
    "stack-v2-sample": {
        "hf_repo": "dancinlab/hexa-forge-corpus-stack-v2-sample-v0.1.3",
        "source_path": "~/runs/corpus/stack-v2-v0.1.3/",
        "repo_type": "dataset",
        "version_phase": "v0.1.3",
        "readme_template": README_TEMPLATE_STACK_V2_SAMPLE,
        "manifest_glob": ["*.jsonl", "manifest.json", "**/*.json", "**/*.py",
                          "**/*.rs", "**/*.ts", "**/*.go", "**/*.c", "**/*.zig"],
        "expected_size_mb_max": 1_500,
        "license": "Apache-2.0",
        "produced_by": "tool/stack_v2_sample.py",
        "runbook_anchor": "§4.1 (step 1)",
    },
    "tokenizer": {
        "hf_repo": "dancinlab/hexa-forge-tokenizer-qwen-hexa-v1",
        "source_path": "~/runs/tokenizer-qwen-hexa-v1/",
        "repo_type": "model",
        "version_phase": "v0.1.3",
        "readme_template": README_TEMPLATE_TOKENIZER,
        "manifest_glob": ["tokenizer.json", "tokenizer_config.json",
                          "vocab.json", "merges.txt", "special_tokens_map.json",
                          "*.json", "*.txt"],
        "expected_size_mb_max": 100,
        "license": "Apache-2.0",
        "produced_by": "tool/extend_tokenizer.py --output",
        "runbook_anchor": "§4.4 (step 4)",
    },
    "cold-bench": {
        "hf_repo": "dancinlab/hexa-forge-bench-cold-v0.1.3",
        "source_path": "runs/cold-bench/",
        "repo_type": "dataset",
        "version_phase": "v0.1.3",
        "readme_template": README_TEMPLATE_COLD_BENCH,
        "manifest_glob": ["*.json", "*.md", "**/*.json", "**/*.md"],
        "expected_size_mb_max": 250,
        "license": "Apache-2.0",
        "produced_by": "tool/run_eval.py (rolled up by tool/eval_lineage.py)",
        "runbook_anchor": "§4.3 (step 3)",
    },
    "sft-lora-r16": {
        "hf_repo": "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r16-v0.2.0",
        "source_path": "~/runs/sft-lora-r16/",
        "repo_type": "model",
        "version_phase": "v0.2.0",
        "readme_template": README_TEMPLATE_SFT_LORA_R16,
        "manifest_glob": ["adapter_model.safetensors", "adapter_config.json",
                          "training_args.json", "*.json", "*.md"],
        "expected_size_mb_max": 2_000,
        "license": "Apache-2.0",
        "produced_by": "(v0.2.0 SFT pipeline ; pending)",
        "runbook_anchor": "§6 row 4 (v0.2.0)",
    },
    "fullft": {
        "hf_repo": "dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0",
        "source_path": "~/runs/fullft/",
        "repo_type": "model",
        "version_phase": "v1.0.0",
        "readme_template": README_TEMPLATE_FULLFT,
        "manifest_glob": ["*.safetensors", "config.json", "generation_config.json",
                          "tokenizer*", "*.json", "*.md"],
        "expected_size_mb_max": 30_000,
        "license": "Apache-2.0",
        "produced_by": "(v1.0.0 full-FT pipeline ; pending)",
        "runbook_anchor": "§6 row 5 (v1.0.0)",
    },
    "gguf-q5": {
        "hf_repo": "dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0",
        "source_path": "~/runs/serving/gguf-q5/",
        "repo_type": "model",
        "version_phase": "v1.0.0",
        "readme_template": README_TEMPLATE_GGUF_Q5,
        "manifest_glob": ["*.gguf", "*.json", "*.md"],
        "expected_size_mb_max": 8_000,
        "license": "Apache-2.0",
        "produced_by": "tool/serving_handoff.py (pending)",
        "runbook_anchor": "§6 row 6 (v1.0.0)",
    },
    "mlx": {
        "hf_repo": "dancinlab/hexa-forge-code-7b-MLX-v1.0.0",
        "source_path": "~/runs/serving/mlx/",
        "repo_type": "model",
        "version_phase": "v1.0.0",
        "readme_template": README_TEMPLATE_MLX,
        "manifest_glob": ["*.safetensors", "*.npz", "*.json", "tokenizer*",
                          "*.md"],
        "expected_size_mb_max": 20_000,
        "license": "Apache-2.0",
        "produced_by": "tool/serving_handoff.py (pending)",
        "runbook_anchor": "§6 row 7 (v1.0.0)",
    },
    "eval-results": {
        "hf_repo": "dancinlab/hexa-forge-eval-results-v1.0.0",
        "source_path": "runs/eval-aggregate/",
        "repo_type": "dataset",
        "version_phase": "v1.0.0",
        "readme_template": README_TEMPLATE_EVAL_RESULTS,
        "manifest_glob": ["*.json", "*.md", "**/*.json", "**/*.md"],
        "expected_size_mb_max": 500,
        "license": "Apache-2.0",
        "produced_by": "tool/eval_lineage.py audit",
        "runbook_anchor": "§6 row 8 (v1.0.0)",
    },
}


TARGET_ORDER: Tuple[str, ...] = (
    "stack-v2-sample",
    "tokenizer",
    "cold-bench",
    "sft-lora-r16",
    "fullft",
    "gguf-q5",
    "mlx",
    "eval-results",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TargetPlan:
    """Resolved upload plan for one target. Pure data ; no side effects."""

    name: str
    hf_repo: str
    repo_type: str
    version_phase: str
    source_path: pathlib.Path  # resolved (~ expanded ; not necessarily abs to repo)
    source_path_display: str   # original (~ NOT expanded) for human-readable output
    source_exists: bool
    file_count: int
    total_bytes: int
    expected_size_mb_max: int
    license: str
    produced_by: str
    runbook_anchor: str
    files_sampled: List[pathlib.Path] = field(default_factory=list)  # first ≤20 for preview
    truncated_files: bool = False

    def total_bytes_human(self) -> str:
        return human_bytes(self.total_bytes)

    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)


@dataclass
class AuditRow:
    ts_utc: str
    subcommand: str
    target: str
    hf_repo: str
    forge_commit: str
    file_count: int
    total_bytes: int
    token_hash_12: Optional[str]
    result: str               # "ok" | "error"
    error_class: Optional[str]
    duration_ms: int
    notes: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def human_bytes(n: int) -> str:
    """Render n as a short human-readable string (B / KB / MB / GB)."""
    if n < 1024:
        return f"{n} B"
    units = ("KB", "MB", "GB", "TB")
    value = float(n) / 1024.0
    for unit in units:
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str() -> str:
    return _dt.date.today().isoformat()


def discover_forge_commit() -> str:
    """Return the current forge git SHA (short) or '<unknown>'.

    Stdlib only ; reads `.git/HEAD` + the referenced ref file. Falls back
    cleanly when not inside a git tree.
    """
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
            # packed-refs fallback
            packed = REPO_ROOT / ".git" / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(f" {ref}"):
                        return line.split(" ", 1)[0][:10]
            return "<unknown>"
        return head[:10] if head else "<unknown>"
    except Exception:
        return "<unknown>"


def sha256_hex_12(value: str) -> str:
    """sha256(value).hexdigest()[:12] — used for token hashing in the audit log.

    Twelve hex chars (48 bits) is enough to cross-correlate two log lines
    written by the same token without enabling brute-force recovery.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def resolve_source_path(raw: str) -> pathlib.Path:
    """Expand ~ and return a Path. Does NOT require existence."""
    return pathlib.Path(_os.path.expanduser(raw)).resolve(strict=False)


def expand_glob_set(root: pathlib.Path, patterns: Iterable[str]) -> List[pathlib.Path]:
    """Collect a deduplicated, sorted list of files under `root` matching `patterns`.

    Patterns are evaluated via `pathlib.Path.glob`. Hidden files (leading
    `.`) are skipped except for explicit `.gitignore`/`.gitattributes`.
    Non-files (directories, symlinks-to-dirs) are skipped.
    """
    if not root.exists():
        return []
    seen: Dict[str, pathlib.Path] = {}
    for pattern in patterns:
        try:
            iterator: Iterable[pathlib.Path] = root.glob(pattern)
        except (NotImplementedError, ValueError):  # pragma: no cover
            continue
        for hit in iterator:
            if not hit.is_file():
                continue
            name = hit.name
            if name.startswith(".") and name not in {".gitignore", ".gitattributes"}:
                continue
            seen[str(hit)] = hit
    return sorted(seen.values(), key=lambda p: str(p))


def collect_target_files(source_path: pathlib.Path,
                         manifest_glob: Iterable[str],
                         sample_limit: int = 20) -> Tuple[int, int, List[pathlib.Path], bool]:
    """Walk source_path. Returns (file_count, total_bytes, sample_list, truncated_flag).

    The sample list is the first `sample_limit` files in sorted order, for
    preview/dry-run output. `truncated_flag` indicates the on-disk match
    set exceeded the sample limit.
    """
    if not source_path.exists():
        return 0, 0, [], False
    matches = expand_glob_set(source_path, manifest_glob)
    if not matches:
        # Fallback: walk every file under the source path.
        for entry in source_path.rglob("*"):
            if entry.is_file():
                matches.append(entry)
        matches.sort(key=lambda p: str(p))
    total_bytes = 0
    for path in matches:
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
    truncated = len(matches) > sample_limit
    sample = matches[:sample_limit]
    return len(matches), total_bytes, sample, truncated


# ---------------------------------------------------------------------------
# License-audit block (best-effort glue to tool/license_clean_scan.py output)
# ---------------------------------------------------------------------------

def maybe_read_local_license_audit(source_path: pathlib.Path) -> str:
    """Look for a sibling license-audit JSON and render a markdown block.

    Search order, first hit wins:
      <source_path>/license_audit.json
      <source_path>/licenses.jsonl  (aggregated)
      <source_path>/../runs/sample_license_audit.json  (legacy convention)

    On miss, returns a placeholder pointer to `tool/license_clean_scan.py`.
    """
    candidates = [
        source_path / "license_audit.json",
        source_path / "licenses.jsonl",
        source_path.parent / "runs" / "sample_license_audit.json",
    ]
    for cand in candidates:
        if not cand.exists():
            continue
        try:
            if cand.suffix == ".jsonl":
                tags: Dict[str, int] = {}
                with cand.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        rec = json.loads(line)
                        tag = rec.get("license", "UNKNOWN")
                        tags[tag] = tags.get(tag, 0) + 1
                rows = "\n".join(f"- `{lic}` × {count}" for lic, count in
                                 sorted(tags.items(), key=lambda kv: -kv[1]))
                return ("License tags inventoried from "
                        f"`{cand.name}` ({sum(tags.values())} entries):\n\n"
                        + rows)
            data = json.loads(cand.read_text(encoding="utf-8"))
            by = data.get("by_license") or {}
            summary = data.get("summary") or {}
            rows = "\n".join(f"- `{lic}` × {count}" for lic, count in
                             sorted(by.items(), key=lambda kv: -kv[1]))
            tail = (f"\n\nScan summary: pass={summary.get('pass', '?')}, "
                    f"warn={summary.get('warn', '?')}, "
                    f"fail={summary.get('fail', '?')}.")
            return (f"License audit (`{cand.name}`):\n\n" + rows + tail)
        except Exception as exc:  # pragma: no cover - best-effort
            return (f"License audit detected at `{cand}` but could not be "
                    f"parsed ({type(exc).__name__}: {exc}). "
                    "Re-run `tool/license_clean_scan.py` and retry upload.")
    return ("No local license audit was found alongside the source path.\n"
            "Run `tool/license_clean_scan.py --path " + str(source_path) +
            " --report " + str(source_path / "license_audit.json") +
            "` before publishing for a permissive-only attestation.")


# ---------------------------------------------------------------------------
# Plan construction + rendering
# ---------------------------------------------------------------------------

def get_target_spec(name: str) -> Dict[str, Any]:
    if name not in TARGETS:
        valid = ", ".join(TARGET_ORDER)
        raise SystemExit(
            f"ERROR: unknown target '{name}'.\n"
            f"       Valid targets: {valid}\n"
            f"       Run `python3 tool/hf_publish.py list-targets` for details."
        )
    return TARGETS[name]


def build_plan(name: str, sample_limit: int = 20) -> TargetPlan:
    spec = get_target_spec(name)
    src_display = spec["source_path"]
    src_resolved = resolve_source_path(src_display)
    file_count, total_bytes, sample, truncated = collect_target_files(
        src_resolved, spec["manifest_glob"], sample_limit=sample_limit,
    )
    return TargetPlan(
        name=name,
        hf_repo=spec["hf_repo"],
        repo_type=spec["repo_type"],
        version_phase=spec["version_phase"],
        source_path=src_resolved,
        source_path_display=src_display,
        source_exists=src_resolved.exists(),
        file_count=file_count,
        total_bytes=total_bytes,
        expected_size_mb_max=spec["expected_size_mb_max"],
        license=spec["license"],
        produced_by=spec["produced_by"],
        runbook_anchor=spec["runbook_anchor"],
        files_sampled=sample,
        truncated_files=truncated,
    )


def render_readme(plan: TargetPlan, run_id: Optional[str] = None) -> str:
    spec = TARGETS[plan.name]
    template: str = spec["readme_template"]
    license_block = maybe_read_local_license_audit(plan.source_path)
    fields = {
        "hf_repo": plan.hf_repo,
        "forge_commit": discover_forge_commit(),
        "file_count": plan.file_count,
        "total_bytes_human": plan.total_bytes_human(),
        "run_id_or_dash": run_id or "-",
        "license": plan.license,
        "source_path_display": plan.source_path_display,
        "date_iso": _dt.date.today().isoformat(),
        "license_audit_block": license_block,
    }
    return template.format(**fields)


def render_plan_for_human(plan: TargetPlan) -> str:
    """Pretty multi-line block for dry-run / verify stdout."""
    status = "OK" if plan.source_exists else "MISSING"
    size_warn = ""
    if plan.total_mb() > plan.expected_size_mb_max:
        size_warn = (f"\n  WARNING: total {plan.total_bytes_human()} exceeds "
                     f"the expected_size_mb_max of {plan.expected_size_mb_max} MB."
                     " Pass --force-size to override.")
    sample_lines = "\n    ".join(str(p) for p in plan.files_sampled) or "(none)"
    truncated_note = (
        f"\n    ... (+{plan.file_count - len(plan.files_sampled)} more)"
        if plan.truncated_files else ""
    )
    return (
        f"target          : {plan.name}\n"
        f"hf_repo         : {plan.hf_repo}\n"
        f"repo_type       : {plan.repo_type}\n"
        f"version_phase   : {plan.version_phase}\n"
        f"runbook_anchor  : {plan.runbook_anchor}\n"
        f"produced_by     : {plan.produced_by}\n"
        f"source_path     : {plan.source_path_display}\n"
        f"  resolved      : {plan.source_path}\n"
        f"  status        : {status}\n"
        f"file_count      : {plan.file_count}\n"
        f"total_bytes     : {plan.total_bytes} ({plan.total_bytes_human()})\n"
        f"license         : {plan.license}\n"
        f"sample (first {len(plan.files_sampled)}):\n    {sample_lines}{truncated_note}"
        f"{size_warn}"
    )


# ---------------------------------------------------------------------------
# Audit log writer
# ---------------------------------------------------------------------------

def append_audit_row(row: AuditRow, logs_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Append a single JSON line to `logs/hf_publish.<date>.jsonl`.

    Token never appears in the row ; only `token_hash_12`. The file is
    opened in append mode with line-buffered writes (the per-row payload
    is tiny ; atomic rename would be over-engineered for the volume).

    `logs_dir` defaults to the *module-level* `DEFAULT_LOGS_DIR` resolved
    at CALL time (not at function-definition time). This lets the selftest
    redirect logs into a tmpdir by mutating the module global.
    """
    target_dir = logs_dir if logs_dir is not None else DEFAULT_LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / f"hf_publish.{today_str()}.jsonl"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(row.to_json() + "\n")
        fh.flush()
    return log_path


# ---------------------------------------------------------------------------
# HF API binding (soft import + dependency-injectable for selftest)
# ---------------------------------------------------------------------------

class HfApiUnavailable(RuntimeError):
    """Raised when huggingface_hub is needed but not installed."""


def _import_hf_api():
    """Import huggingface_hub.HfApi. Raise HfApiUnavailable if not present."""
    try:
        from huggingface_hub import HfApi  # type: ignore
        from huggingface_hub.errors import HfHubHTTPError  # type: ignore
    except ImportError as exc:
        try:
            # huggingface_hub <0.20 placed errors under huggingface_hub.utils
            from huggingface_hub import HfApi  # type: ignore
            from huggingface_hub.utils import HfHubHTTPError  # type: ignore
        except ImportError:
            raise HfApiUnavailable(
                "huggingface_hub is required for `verify` and `upload`. Install with:\n"
                "    pip install huggingface_hub\n"
                f"(import error: {exc})"
            ) from exc
    return HfApi, HfHubHTTPError


# Module-level hook for selftest monkey-patching. When set, replaces
# `_import_hf_api()` ; the production code path is otherwise untouched.
_HF_API_FACTORY: Optional[Callable[[], Tuple[Any, Any]]] = None


def hf_api_factory() -> Tuple[Any, Any]:
    if _HF_API_FACTORY is not None:
        return _HF_API_FACTORY()
    return _import_hf_api()


def resolve_token_or_die() -> str:
    """Return the HF token from env, or exit 2 with a clear remediation hint."""
    token = _os.environ.get(HF_TOKEN_ENV)
    if not token:
        raise SystemExit(
            f"ERROR: {HF_TOKEN_ENV} missing; run via mac-exec --hf-passthrough.\n"
            "       See papers/plan-runbook-v0.1.3.md §1-§3 for the auth\n"
            "       routing pattern. The token MUST be injected into the\n"
            "       child process env from the Mac-side secret store ; it\n"
            "       MUST NOT be written to Linux disk."
        )
    return token


def check_org_access(api: Any, token: str) -> Tuple[bool, str]:
    """Confirm the token resolves to a `dancinlab` member (or is dancinlab).

    Returns (ok, who_repr). On failure, who_repr is a human-readable
    description of what we saw.
    """
    info = api.whoami(token=token)
    if not isinstance(info, dict):
        return False, f"unexpected whoami() return type: {type(info).__name__}"
    name = info.get("name") or info.get("fullname") or "<unknown>"
    if name == DANCINLAB_ORG:
        return True, f"name={name}"
    orgs = info.get("orgs") or []
    org_names: List[str] = []
    for org in orgs:
        if isinstance(org, dict):
            org_names.append(org.get("name") or org.get("fullname") or "")
        elif isinstance(org, str):
            org_names.append(org)
    if DANCINLAB_ORG in org_names:
        return True, f"name={name}, orgs include {DANCINLAB_ORG}"
    return False, (
        f"name={name}, orgs={org_names or '[]'} ; "
        f"not a member of {DANCINLAB_ORG}"
    )


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_list_targets(args: argparse.Namespace) -> int:
    """list-targets — print the 8 targets with source ✓/✗ status."""
    print(f"hf_publish.py v{TOOL_VERSION} — dancinlab/* upload targets")
    print(f"runbook: papers/plan-runbook-v0.1.3.md §5")
    print(f"forge_commit: {discover_forge_commit()}")
    print()
    header = f"  {'target':<18} {'phase':<8} {'src':<4} {'files':>7} {'bytes':>12}  hf_repo"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name in TARGET_ORDER:
        plan = build_plan(name, sample_limit=0)
        tick = "OK" if plan.source_exists else "--"
        size = plan.total_bytes_human() if plan.source_exists else "-"
        print(f"  {name:<18} {plan.version_phase:<8} {tick:<4} "
              f"{plan.file_count:>7} {size:>12}  {plan.hf_repo}")
    print()
    missing = sum(1 for n in TARGET_ORDER if not build_plan(n, 0).source_exists)
    if missing:
        print(f"  Note: {missing}/{len(TARGET_ORDER)} targets have no source on disk yet.")
        print("        At v0.1.3 fresh checkout this is expected — the source")
        print("        directories are populated as the runbook §4 steps land.")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    """dry-run — show the plan ; no auth ; no network."""
    plan = build_plan(args.target)
    print(f"hf_publish.py — DRY RUN (no auth check, no network)")
    print()
    print(render_plan_for_human(plan))
    print()
    print("--- README.md preview ---")
    readme = render_readme(plan, run_id=args.run_id)
    print(readme)
    print("--- end README.md preview ---")
    if not plan.source_exists:
        print(f"\nNOTE: source path does not exist — upload would refuse.")
        print(f"      Produce it first via: {plan.produced_by}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """verify — resolve token + ping whoami() ; no upload."""
    start = time.monotonic()
    plan = build_plan(args.target)
    token = resolve_token_or_die()
    token_hash = sha256_hex_12(token)
    try:
        HfApi, _err_cls = hf_api_factory()
    except HfApiUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _audit("verify", plan, token_hash, "error", "HfApiUnavailable",
               int((time.monotonic() - start) * 1000))
        return 2

    api = HfApi()
    try:
        ok, who = check_org_access(api, token)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        print(f"ERROR: whoami() failed: {msg}", file=sys.stderr)
        _audit("verify", plan, token_hash, "error", type(exc).__name__,
               int((time.monotonic() - start) * 1000), notes=msg)
        return 2

    if not ok:
        print(f"ERROR: token does not have access to {DANCINLAB_ORG}: {who}",
              file=sys.stderr)
        _audit("verify", plan, token_hash, "error", "OrgAccessDenied",
               int((time.monotonic() - start) * 1000), notes=who)
        return 2

    print(f"hf_publish.py — VERIFY OK")
    print(f"  token_hash_12 : {token_hash}")
    print(f"  whoami        : {who}")
    print()
    print(render_plan_for_human(plan))
    _audit("verify", plan, token_hash, "ok", None,
           int((time.monotonic() - start) * 1000))
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    """upload — create_repo(exist_ok=False) + upload_folder(); audit on success/fail."""
    start = time.monotonic()
    plan = build_plan(args.target)
    if not plan.source_exists:
        print(f"ERROR: source_path missing: {plan.source_path}", file=sys.stderr)
        print(f"       Run `{plan.produced_by}` first.", file=sys.stderr)
        _audit("upload", plan, None, "error", "SourceMissing",
               int((time.monotonic() - start) * 1000))
        return 2

    if plan.file_count == 0:
        print(f"ERROR: source_path has 0 matching files: {plan.source_path}",
              file=sys.stderr)
        _audit("upload", plan, None, "error", "EmptySource",
               int((time.monotonic() - start) * 1000))
        return 2

    if plan.total_mb() > plan.expected_size_mb_max and not args.force_size:
        print(f"ERROR: total {plan.total_bytes_human()} exceeds the bar "
              f"({plan.expected_size_mb_max} MB) for target '{plan.name}'.",
              file=sys.stderr)
        print("       Pass --force-size to override.", file=sys.stderr)
        _audit("upload", plan, None, "error", "SizeBarExceeded",
               int((time.monotonic() - start) * 1000))
        return 2

    token = resolve_token_or_die()
    token_hash = sha256_hex_12(token)

    try:
        HfApi, HfHubHTTPError = hf_api_factory()
    except HfApiUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _audit("upload", plan, token_hash, "error", "HfApiUnavailable",
               int((time.monotonic() - start) * 1000))
        return 2

    api = HfApi()
    try:
        ok, who = check_org_access(api, token)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        print(f"ERROR: whoami() failed: {msg}", file=sys.stderr)
        _audit("upload", plan, token_hash, "error", type(exc).__name__,
               int((time.monotonic() - start) * 1000), notes=msg)
        return 2
    if not ok:
        print(f"ERROR: token does not have access to {DANCINLAB_ORG}: {who}",
              file=sys.stderr)
        _audit("upload", plan, token_hash, "error", "OrgAccessDenied",
               int((time.monotonic() - start) * 1000), notes=who)
        return 2

    # Write-once invariant: create_repo(exist_ok=False). With --force we
    # tolerate the "already exists" path (still no implicit deletes).
    repo_existed = False
    try:
        api.create_repo(
            repo_id=plan.hf_repo,
            repo_type=plan.repo_type,
            private=False,
            token=token,
            exist_ok=False,
        )
    except Exception as exc:
        msg = str(exc)
        is_exists = (
            "exists" in msg.lower() or "409" in msg
            or type(exc).__name__ in {"HfHubHTTPError", "RepositoryNotFoundError"}
            and "409" in msg
        )
        if is_exists and args.force:
            repo_existed = True
            print(f"NOTE: repo exists ; --force given, proceeding with upload_folder (additive only).")
        elif is_exists:
            print(
                f"ERROR: Repo {plan.hf_repo} exists; pass --force to overwrite "
                "existing files (will NOT delete unrelated files in the repo).",
                file=sys.stderr,
            )
            _audit("upload", plan, token_hash, "error", "RepoExists",
                   int((time.monotonic() - start) * 1000), notes=msg)
            return 2
        else:
            print(f"ERROR: create_repo failed: {type(exc).__name__}: {msg}",
                  file=sys.stderr)
            _audit("upload", plan, token_hash, "error", type(exc).__name__,
                   int((time.monotonic() - start) * 1000), notes=msg)
            return 2

    # Stage README.md alongside the source files. We materialise the
    # README into the source directory itself (write-once: error if a
    # README.md is already there with different contents, unless --force).
    readme_body = render_readme(plan, run_id=args.run_id)
    readme_path = plan.source_path / "README.md"
    if readme_path.exists():
        existing = readme_path.read_text(encoding="utf-8")
        if existing != readme_body and not args.force:
            print(f"ERROR: README.md already exists at {readme_path} with "
                  "different contents. Pass --force to overwrite.",
                  file=sys.stderr)
            _audit("upload", plan, token_hash, "error", "ReadmeConflict",
                   int((time.monotonic() - start) * 1000))
            return 2
    readme_path.write_text(readme_body, encoding="utf-8")

    # upload_folder — additive only (delete_patterns=[]).
    try:
        api.upload_folder(
            repo_id=plan.hf_repo,
            repo_type=plan.repo_type,
            folder_path=str(plan.source_path),
            token=token,
            commit_message=(
                f"hexa-forge {plan.name} ({plan.version_phase}) "
                f"forge_commit={discover_forge_commit()}"
            ),
            delete_patterns=[],
        )
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        print(f"ERROR: upload_folder failed: {msg}", file=sys.stderr)
        _audit("upload", plan, token_hash, "error", type(exc).__name__,
               int((time.monotonic() - start) * 1000), notes=msg)
        return 2

    duration_ms = int((time.monotonic() - start) * 1000)
    log_path = _audit("upload", plan, token_hash, "ok", None, duration_ms,
                      notes="repo_existed" if repo_existed else None)
    print(f"__HF_PUBLISH_UPLOAD__ {plan.name} -> {plan.hf_repo}  "
          f"files={plan.file_count} bytes={plan.total_bytes} "
          f"duration_ms={duration_ms}")
    print(f"audit: {log_path}")
    return 0


def _audit(subcommand: str,
           plan: TargetPlan,
           token_hash: Optional[str],
           result: str,
           error_class: Optional[str],
           duration_ms: int,
           notes: Optional[str] = None) -> pathlib.Path:
    """Compose + append one audit row. Internal helper."""
    row = AuditRow(
        ts_utc=utc_now_iso(),
        subcommand=subcommand,
        target=plan.name,
        hf_repo=plan.hf_repo,
        forge_commit=discover_forge_commit(),
        file_count=plan.file_count,
        total_bytes=plan.total_bytes,
        token_hash_12=token_hash,
        result=result,
        error_class=error_class,
        duration_ms=duration_ms,
        notes=notes,
    )
    return append_audit_row(row)


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

class _MockHfApi:
    """Minimal HfApi stand-in for selftest. Records calls ; never networks."""

    def __init__(self, *,
                 whoami_orgs: Tuple[str, ...] = (DANCINLAB_ORG,),
                 whoami_name: str = "selftest-user",
                 create_raises: Optional[Exception] = None,
                 upload_raises: Optional[Exception] = None) -> None:
        self.whoami_orgs = whoami_orgs
        self.whoami_name = whoami_name
        self.create_raises = create_raises
        self.upload_raises = upload_raises
        self.whoami_calls: List[Dict[str, Any]] = []
        self.create_calls: List[Dict[str, Any]] = []
        self.upload_calls: List[Dict[str, Any]] = []

    def whoami(self, token: str = "") -> Dict[str, Any]:
        self.whoami_calls.append({"token_len": len(token)})
        return {
            "name": self.whoami_name,
            "orgs": [{"name": o} for o in self.whoami_orgs],
        }

    def create_repo(self, **kwargs: Any) -> Dict[str, Any]:
        self.create_calls.append(kwargs)
        if self.create_raises:
            raise self.create_raises
        return {"url": f"https://huggingface.co/{kwargs.get('repo_id')}"}

    def upload_folder(self, **kwargs: Any) -> Dict[str, Any]:
        self.upload_calls.append(kwargs)
        if self.upload_raises:
            raise self.upload_raises
        return {"commit_url": f"https://huggingface.co/{kwargs.get('repo_id')}/commit/deadbeef"}


class _MockHfHubHTTPError(Exception):
    """Stand-in for huggingface_hub.errors.HfHubHTTPError in selftest."""


def _selftest() -> int:
    """Synthesise mock targets + exercise all four subcommands.

    The mock substitutes the entire `huggingface_hub.HfApi` surface via
    `_HF_API_FACTORY`. Source paths are tmpdirs. The audit log is also
    redirected to a tmpdir so the production logs/ tree is untouched.
    """
    global _HF_API_FACTORY
    print("hf_publish.py selftest")

    # 1) Sanity: TARGETS has all 8 enumerated names.
    expected = {
        "stack-v2-sample", "tokenizer", "cold-bench",
        "sft-lora-r16", "fullft", "gguf-q5", "mlx", "eval-results",
    }
    if set(TARGETS.keys()) != expected:
        print(f"  [FAIL] TARGETS mismatch: have={set(TARGETS)} want={expected}")
        return 1
    print(f"  [PASS] TARGETS contains all 8 enumerated names")

    # 2) Render every README template against a synthetic plan. None may
    #    raise KeyError (template-field drift).
    for name in TARGET_ORDER:
        try:
            plan = TargetPlan(
                name=name,
                hf_repo=TARGETS[name]["hf_repo"],
                repo_type=TARGETS[name]["repo_type"],
                version_phase=TARGETS[name]["version_phase"],
                source_path=pathlib.Path("/nonexistent"),
                source_path_display=TARGETS[name]["source_path"],
                source_exists=False,
                file_count=0,
                total_bytes=0,
                expected_size_mb_max=TARGETS[name]["expected_size_mb_max"],
                license=TARGETS[name]["license"],
                produced_by=TARGETS[name]["produced_by"],
                runbook_anchor=TARGETS[name]["runbook_anchor"],
            )
            body = render_readme(plan)
            if "{" in body and "}" in body and "format" not in body:
                # crude check: unrendered placeholders left over
                stray = [tok for tok in ("{hf_repo}", "{file_count}",
                                         "{date_iso}", "{license}")
                         if tok in body]
                if stray:
                    print(f"  [FAIL] {name} README still has placeholders {stray}")
                    return 1
            if "hexa-forge" not in body:
                print(f"  [FAIL] {name} README missing brand string")
                return 1
        except Exception as exc:
            print(f"  [FAIL] {name} render: {type(exc).__name__}: {exc}")
            return 1
    print(f"  [PASS] all 8 README templates render without KeyError")

    # 3) Build a tmpdir-backed mock target. Patch TARGETS in place + use a
    #    custom logs dir for the audit log.
    with tempfile.TemporaryDirectory(prefix="hf_publish_selftest_") as td:
        tmp_root = pathlib.Path(td)
        src = tmp_root / "mock_source"
        src.mkdir(parents=True)
        (src / "manifest.json").write_text('{"mock": true}\n', encoding="utf-8")
        (src / "data.jsonl").write_text(
            '{"row": 1}\n{"row": 2}\n{"row": 3}\n', encoding="utf-8",
        )
        # A sibling license audit so the README's audit block is exercised.
        (src / "license_audit.json").write_text(json.dumps({
            "by_license": {"MIT": 2, "Apache-2.0": 1},
            "summary": {"pass": 3, "warn": 0, "fail": 0},
        }), encoding="utf-8")

        mock_name = "stack-v2-sample"
        original = dict(TARGETS[mock_name])
        TARGETS[mock_name] = {**original,
                              "source_path": str(src),
                              "expected_size_mb_max": 1}

        logs_dir = tmp_root / "logs"
        try:
            # 3a) list-targets
            args = argparse.Namespace()
            rc = cmd_list_targets(args)
            if rc != 0:
                print(f"  [FAIL] list-targets rc={rc}")
                return 1
            print("  [PASS] list-targets exit 0")

            # 3b) dry-run (no auth needed)
            args = argparse.Namespace(target=mock_name, run_id="0000-selftest")
            rc = cmd_dry_run(args)
            if rc != 0:
                print(f"  [FAIL] dry-run rc={rc}")
                return 1
            print("  [PASS] dry-run exit 0")

            # 3c) verify — no token => clean SystemExit
            os.environ.pop(HF_TOKEN_ENV, None)
            args = argparse.Namespace(target=mock_name, run_id=None)
            try:
                cmd_verify(args)
                print("  [FAIL] verify did not exit on missing token")
                return 1
            except SystemExit as exit_exc:
                if "HUGGING_FACE_HUB_TOKEN missing" not in str(exit_exc):
                    print(f"  [FAIL] verify wrong error: {exit_exc}")
                    return 1
            print("  [PASS] verify errors cleanly without token")

            # 3d) verify — with token + mocked HfApi
            mock = _MockHfApi()
            _HF_API_FACTORY = lambda: (lambda: mock, _MockHfHubHTTPError)  # noqa: E731

            # `HfApi` is normally a class ; the factory returns (cls, err).
            # We adapt: produce a callable that returns the mock when called.
            class _MockHfApiClass:
                def __call__(self_inner):
                    return mock
            _HF_API_FACTORY = lambda: (_MockHfApiClass(), _MockHfHubHTTPError)  # noqa: E731

            # Redirect audit log to tmp + monkey-patch default logs dir.
            global DEFAULT_LOGS_DIR
            orig_logs = DEFAULT_LOGS_DIR
            DEFAULT_LOGS_DIR = logs_dir

            os.environ[HF_TOKEN_ENV] = "hf_selftest_FAKE_TOKEN_xxxxxxxxxxxxxxxxx"
            try:
                rc = cmd_verify(argparse.Namespace(target=mock_name, run_id=None))
                if rc != 0:
                    print(f"  [FAIL] verify rc={rc}")
                    return 1
                if not mock.whoami_calls:
                    print("  [FAIL] verify did not call whoami")
                    return 1
            finally:
                pass
            print("  [PASS] verify passes with mocked HfApi + valid token")

            # 3e) verify — token with no dancinlab org => OrgAccessDenied
            mock_no_org = _MockHfApi(whoami_orgs=("other-org",))
            _HF_API_FACTORY = lambda: ((lambda: mock_no_org), _MockHfHubHTTPError)  # noqa: E731
            rc = cmd_verify(argparse.Namespace(target=mock_name, run_id=None))
            if rc == 0:
                print("  [FAIL] verify accepted token without dancinlab org")
                return 1
            print("  [PASS] verify rejects token without dancinlab org access")

            # 3f) upload — happy path
            mock_up = _MockHfApi()
            _HF_API_FACTORY = lambda: ((lambda: mock_up), _MockHfHubHTTPError)  # noqa: E731
            rc = cmd_upload(argparse.Namespace(
                target=mock_name, run_id="0000-selftest",
                force=False, force_size=False,
            ))
            if rc != 0:
                print(f"  [FAIL] upload rc={rc}")
                return 1
            if not mock_up.create_calls:
                print("  [FAIL] upload skipped create_repo")
                return 1
            if mock_up.create_calls[0].get("exist_ok") is not False:
                print("  [FAIL] upload did not set exist_ok=False (write-once)")
                return 1
            if not mock_up.upload_calls:
                print("  [FAIL] upload skipped upload_folder")
                return 1
            if mock_up.upload_calls[0].get("delete_patterns") != []:
                print("  [FAIL] upload_folder delete_patterns != []")
                return 1
            print("  [PASS] upload happy path (write-once + additive)")

            # 3g) upload — repo exists, no --force => RepoExists
            mock_dup = _MockHfApi(create_raises=RuntimeError("Repo already exists (409)"))
            _HF_API_FACTORY = lambda: ((lambda: mock_dup), _MockHfHubHTTPError)  # noqa: E731
            rc = cmd_upload(argparse.Namespace(
                target=mock_name, run_id=None,
                force=False, force_size=False,
            ))
            if rc == 0:
                print("  [FAIL] upload accepted already-exists without --force")
                return 1
            print("  [PASS] upload refuses already-exists without --force")

            # 3h) upload — repo exists + --force => proceed
            mock_force = _MockHfApi(create_raises=RuntimeError("Repo already exists (409)"))
            _HF_API_FACTORY = lambda: ((lambda: mock_force), _MockHfHubHTTPError)  # noqa: E731
            rc = cmd_upload(argparse.Namespace(
                target=mock_name, run_id=None,
                force=True, force_size=False,
            ))
            if rc != 0:
                print(f"  [FAIL] upload --force on existing repo rc={rc}")
                return 1
            if not mock_force.upload_calls:
                print("  [FAIL] upload --force did not call upload_folder")
                return 1
            print("  [PASS] upload --force proceeds against existing repo")

            # 3i) audit log assertions
            log_files = sorted(logs_dir.glob("hf_publish.*.jsonl"))
            if not log_files:
                print(f"  [FAIL] no audit log produced in {logs_dir}")
                return 1
            log_lines = log_files[0].read_text(encoding="utf-8").splitlines()
            if len(log_lines) < 4:
                print(f"  [FAIL] expected ≥4 audit rows, got {len(log_lines)}")
                return 1
            for line in log_lines:
                obj = json.loads(line)
                if obj.get("token_hash_12") and len(obj["token_hash_12"]) != 12:
                    print(f"  [FAIL] token_hash_12 wrong length: {obj}")
                    return 1
                # Token must not appear ANYWHERE in the row.
                if "hf_selftest_FAKE_TOKEN" in json.dumps(obj):
                    print(f"  [FAIL] raw token leaked into audit log: {obj}")
                    return 1
            print(f"  [PASS] audit log has {len(log_lines)} rows ; no token leak")

        finally:
            # Restore globals
            TARGETS[mock_name] = original
            _HF_API_FACTORY = None
            DEFAULT_LOGS_DIR = orig_logs
            os.environ.pop(HF_TOKEN_ENV, None)

    # 4) human_bytes round-trip
    cases = [(0, "0 B"), (1023, "1023 B"), (1024, "1.00 KB"),
             (1024 * 1024, "1.00 MB"), (5 * 1024 ** 3, "5.00 GB")]
    for n, want in cases:
        got = human_bytes(n)
        if got != want:
            print(f"  [FAIL] human_bytes({n}) = {got!r} (want {want!r})")
            return 1
    print("  [PASS] human_bytes cases")

    # 5) sha256_hex_12 determinism + length
    h1 = sha256_hex_12("hf_test_abc")
    h2 = sha256_hex_12("hf_test_abc")
    h3 = sha256_hex_12("hf_test_xyz")
    if h1 != h2 or h1 == h3 or len(h1) != 12:
        print(f"  [FAIL] sha256_hex_12 sanity: {h1} {h2} {h3}")
        return 1
    print("  [PASS] sha256_hex_12 sanity")

    print("__HF_PUBLISH_SELFTEST__ PASS")
    return 0


# ---------------------------------------------------------------------------
# argparse + dispatch
# ---------------------------------------------------------------------------

_EPILOG = """\
Authoritative spec:
    papers/plan-runbook-v0.1.3.md §5  — eight upload targets table
    papers/plan-runbook-v0.1.3.md §1-§3 — auth routing (mac-exec, env-only token)
    ROADMAP.md §3                     — bidirectional loop with hexa-codex
    HuggingFace org: dancinlab (https://huggingface.co/dancinlab)

Auth flow:
    The HF token MUST come from the HUGGING_FACE_HUB_TOKEN env var,
    injected by `mac-exec --hf-passthrough` from the Mac-side secret
    store. It MUST NOT be written to Linux disk. Audit log only records
    a 12-char SHA-256 prefix of the token (`token_hash_12`).

Subcommands:
    list-targets     pretty-print all 8 targets + source ✓/✗ status
    dry-run --target NAME    show upload plan + README preview (no net)
    verify --target NAME     resolve token + whoami(), confirm org access
    upload --target NAME     create_repo(exist_ok=False) + upload_folder
    --selftest               synthetic-target unit test, no network

Examples:
    python3 tool/hf_publish.py list-targets
    python3 tool/hf_publish.py dry-run --target stack-v2-sample
    mac-exec --hf-passthrough python3 tool/hf_publish.py verify --target stack-v2-sample
    mac-exec --hf-passthrough python3 tool/hf_publish.py upload --target stack-v2-sample

TODO_v1_0_0:
    git-LFS handling is intentionally OUT OF SCOPE for v0.1.3. The
    four model-weight targets (sft-lora-r16, fullft, gguf-q5, mlx)
    will need .gitattributes LFS configuration at their upload time ;
    that lands alongside tool/serving_handoff.py at v0.2.0+ / v1.0.0.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(__doc__ or "").split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    parser.add_argument("--selftest", action="store_true",
                        help="run the inline selftest (no network) and exit")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {TOOL_VERSION}")

    sub = parser.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")

    p_list = sub.add_parser("list-targets",
                            help="print the 8 targets + per-target source status")
    p_list.set_defaults(func=cmd_list_targets)

    p_dry = sub.add_parser("dry-run",
                           help="show the upload plan (no auth check, no network)")
    p_dry.add_argument("--target", required=True, choices=list(TARGET_ORDER),
                       help="upload target (see list-targets)")
    p_dry.add_argument("--run-id", default=None,
                       help="optional forge run identifier for the README")
    p_dry.set_defaults(func=cmd_dry_run)

    p_ver = sub.add_parser("verify",
                           help="resolve token + whoami() ; no upload")
    p_ver.add_argument("--target", required=True, choices=list(TARGET_ORDER),
                       help="upload target (see list-targets)")
    p_ver.add_argument("--run-id", default=None,
                       help="optional forge run identifier for the README")
    p_ver.set_defaults(func=cmd_verify)

    p_up = sub.add_parser("upload",
                          help="upload the target to dancinlab/* via huggingface_hub")
    p_up.add_argument("--target", required=True, choices=list(TARGET_ORDER),
                      help="upload target (see list-targets)")
    p_up.add_argument("--run-id", default=None,
                      help="optional forge run identifier for the README")
    p_up.add_argument("--force", action="store_true",
                      help="allow upload against an already-existing repo "
                           "(additive; NEVER deletes unrelated files)")
    p_up.add_argument("--force-size", action="store_true",
                      help="override the expected_size_mb_max sanity bar")
    p_up.set_defaults(func=cmd_upload)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # --selftest is a top-level flag that supersedes subcommand parsing.
    if "--selftest" in argv:
        return _selftest()

    # No args at all => selftest (matches sibling tool/emit_t4.py convention).
    if not argv:
        return _selftest()

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "subcommand", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
