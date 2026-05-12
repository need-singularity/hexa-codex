# plan — v0.1.3 G-BASE runbook (mac-exec HF bridge + cold-bench sequence)

> **Operational runbook** for entering v0.1.3 G-BASE. Closes the gap
> between v0.1.2 paper-layer (`ROADMAP.md §3.2 = DONE`) and actual
> compute. **HF auth and secret retrieval routed through `mac-exec`**
> — the Mac side holds the HF CLI + secret CLI; the Linux forge host
> never sees the bare token on disk.

| field        | value                                            |
| ------------ | ------------------------------------------------ |
| status       | `OPS_LIVE`                                       |
| entered      | v0.1.3 G-BASE prep                               |
| HF org       | [`dancinlab`](https://huggingface.co/dancinlab)  |
| last updated | 2026-05-11                                       |

---

## §1 Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────────┐
│  Mac (operator side)        │         │  Linux forge host                │
│                             │         │                                  │
│  - HF CLI installed         │         │  - hexa-forge repo (this repo)   │
│  - secret CLI installed     │         │  - tool/*.py + treesitter_pack   │
│  - HF token in secret store │         │  - corpus_filtered/ + samples/   │
│                             │         │                                  │
│  ┌──────────────────────┐   │         │   ┌────────────────────────┐     │
│  │ mac-exec dispatcher  │───┼─SSH────►│   │ tool/stack_v2_sample.py│     │
│  │   1. secret get hf-* │   │   +env: │   │ tool/tokenize.py       │     │
│  │   2. hf whoami       │   │   HF_*  │   │ tool/extend_tokenizer  │     │
│  │   3. exec remote cmd │   │         │   │ tool/corpus_quality... │     │
│  └──────────────────────┘   │         │   │ tool/run_eval.py       │     │
│                             │         │   └────────────────────────┘     │
└─────────────────────────────┘         └──────────────────────────────────┘
       token never lands on                token visible only inside the
       Linux disk; expires with             child process env; not written
       the mac-exec subshell                to logs / runs / outbox
```

**Key invariants:**

1. **No token on Linux disk** — `HUGGING_FACE_HUB_TOKEN` is exported
   only into the child process env via `mac-exec`. Forge tools accept it
   from env; they MUST NOT write it to logs / `runs/*.json` / outbox.
2. **Mac-exec is the ONLY auth conduit** — even if HF CLI exists on
   Linux, do not run `hf login` directly there. The 2026-04-29 nexus
   directive (`mac 실행 옵션 모두 폐기`) applies to **nexus's
   compute-on-Mac fallback**, NOT to this HF-bridge use; HF auth via
   mac-exec is a separate carve-out.
3. **Audit trail** — every mac-exec invocation logs to
   `logs/mac_exec.<date>.jsonl` (timestamp / actor / forge tool /
   bytes-fetched / not the token itself).

## §2 mac-exec invocation pattern

**Resolution (2026-05-11):** the `mac-exec` binary did not pre-exist;
operator's `command -v mac-exec` returned empty. Implemented as a
**bash shim** at [`tool/mac-exec`](../tool/mac-exec) that implements
**shape B** (the higher-level `--hf-passthrough` alias) — shape A's
explicit env-routing is not needed for the v0.1.3 G-BASE scope. The
shim wraps `secret get HF_TOKEN` + `ssh "$FORGE_HOST"` with env-var
injection. M-008 closed by this implementation. See
[`docs/mac_exec_cheatsheet.md §0`](../docs/mac_exec_cheatsheet.md)
for the symlink-install one-liner.

Historical context — the runbook had originally described two
hypothetical shapes:

### §2.1 Shape A — explicit env injection

```bash
# Mac side
mac-exec --inject-secret HF_TOKEN --to-host linux-forge \
    "cd ~/core/hexa-forge && python3 tool/stack_v2_sample.py \
       --languages python,rust,typescript,go,c,zig \
       --sample-pct 5 \
       --tokenizer Qwen/Qwen2.5-Coder-7B \
       --output samples/stack_v2/ \
       --stats runs/stack_v2_sample.json"
```

`mac-exec`:
1. `secret get hf-token` → fetches token from Mac secret store
2. SSH to `linux-forge` exporting `HUGGING_FACE_HUB_TOKEN=<value>` into
   the remote shell env
3. Runs the command; stdout streams back
4. Token is cleared from the SSH subshell when the command exits

### §2.2 Shape B — wrap the whole tool

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/stack_v2_sample.py [args...]
```

Functionally identical; `--hf-passthrough` is the high-level alias for
"resolve HF token from secret store + inject as env var".

> **Verification at v0.1.3 entry:** confirm which shape the actual
> `mac-exec` binary supports before the first sampling run. Both shapes
> compose with the existing tool CLIs unchanged.

## §3 Per-tool mac-exec routing (5 HF-needing forge tools)

| Forge tool                          | What it needs from HF                          | Mac-exec routing                              |
| ----------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| `tool/stack_v2_sample.py`           | `bigcode/the-stack-v2` dataset streaming       | `mac-exec --hf-passthrough python3 tool/stack_v2_sample.py ...` |
| `tool/tokenize.py`                  | `Qwen/Qwen2.5-Coder-7B` tokenizer download     | same                                          |
| `tool/extend_tokenizer.py`          | `Qwen/Qwen2.5-Coder-7B` tokenizer download     | same                                          |
| `tool/corpus_quality_filter.py`     | `Qwen/Qwen2.5-Coder-7B` reference model (PPL)  | same                                          |
| `tool/run_eval.py`                  | Base-model weights (Qwen / DeepSeek / StarCoder) | same                                        |

**Non-HF tools (no mac-exec needed):**

- `tool/license_clean_scan.py` — stdlib only
- `tool/emit_t4.py` — stdlib only
- `tool/_common.py` — stdlib only
- `tool/fetch_sources.py` — fetches from generic web URLs (no HF auth)

## §4 v0.1.3 G-BASE execution sequence

Run on Mac side; output lands on Linux forge.

### §4.1 Step 1 — close D-009 (corpus volume)

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/stack_v2_sample.py \
    --sample-pct 5 \
    --tokenizer Qwen/Qwen2.5-Coder-7B \
    --output samples/stack_v2/ \
    --stats runs/stack_v2_sample.json
```

**Expected output:**

- `samples/stack_v2/{python,rust,typescript,go,c,zig}/...` — 5% subset
- `runs/stack_v2_sample.json` — per-lang token counts + extrapolation
  to full corpus
- Updates `datasets.toml` `tokens_actual` for `pretrain-bias` row

**D-009 close criterion:** measured tokens ≥ 600 B (forge §STRUCT
target) OR the actual number replaces the estimate.

### §4.2 Step 2 — close D-009 sub (license-clean verification)

```bash
python3 ~/core/hexa-forge/tool/license_clean_scan.py \
    --manifest datasets.toml \
    --path samples/stack_v2/ \
    --strict \
    --report runs/sample_license_audit.json
```

No mac-exec needed (no HF). Must report 0 FAILs.

### §4.3 Step 3 — close D-007 (base-model bench)

For each of 3 candidates (Qwen2.5-Coder-7B / DeepSeek-Coder-V2-Lite /
StarCoder2-15B):

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/run_eval.py \
    --spec hexa-eval \
    --model <model-id> \
    --task-manifest eval/hexa-eval/manifest.jsonl \
    --output-dir runs/base-bench/<model-slug>/hexa-eval/ \
    --run-id 2026-05-11-cold-bench

# repeat for: 5nl-eval, db-eval, firmware-eval, frontend-eval, safety-eval
```

**D-007 close criterion:** comparative table across the 3 candidates
on the 6 specs. Expected winner per `papers/plan-decisions-pending.md`
D-007 proposed: **Qwen2.5-Coder-7B** (CJK + multilingual + M4 Mini fit).

### §4.4 Step 4 — close D-008 (tokenizer extension)

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/extend_tokenizer.py \
    --base <chosen-base-model> \
    --extension tool/tokenizer_extension.toml \
    --output runs/tokenizer_<base-slug>_hexa_v1/ \
    --corpus-sample samples/stack_v2/rust/ \
    --target-compression 0.5
```

**D-008 close criterion:** round-trip verification 100% + compression
ratio ≤ 0.5× on the hexa source sample.

## §5 HF upload targets (post-bench, post-SFT)

Once forge produces artefacts, upload to `dancinlab/*` namespace:

| Forge artefact                                          | HF repo (proposed naming)                                       | Visibility |
| ------------------------------------------------------- | --------------------------------------------------------------- | ---------- |
| Stack v2 5% sample (filtered + tokenized stats)         | `dancinlab/hexa-forge-corpus-stack-v2-sample-v0.1.3`            | public     |
| `tool/tokenizer_extension.toml` → extended tokenizer    | `dancinlab/hexa-forge-tokenizer-qwen-hexa-v1`                   | public     |
| Cold-bench results (3 models × 6 specs)                 | `dancinlab/hexa-forge-bench-cold-v0.1.3`                        | public     |
| First SFT checkpoint (LoRA r=16 default — D-NEW-TC-C)   | `dancinlab/hexa-forge-code-7b-qwen2.5-lora-r16-v0.2.0`          | public     |
| Full-FT reproducibility checkpoint (v1.0.0 gate ⑪)      | `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`            | public     |
| Quantised laptop tier (Q5_K_M, GGUF — `docs/code-llm.md §VERIFY`) | `dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0`     | public     |
| MLX-converted (M-series laptop)                         | `dancinlab/hexa-forge-code-7b-MLX-v1.0.0`                       | public     |
| Eval result aggregation                                 | `dancinlab/hexa-forge-eval-results-v1.0.0`                      | public     |

**Naming convention:**

```
dancinlab/hexa-forge-<artefact-class>-<base-or-config>-<version>
```

- All MIT-licensed (forge repo license).
- All include `LICENSE` + `README.md` + provenance (forge commit SHA +
  `datasets.toml@<hash>` + `tokenizer_extension.toml@<hash>`).
- v0.1.x artefacts marked `RESEARCH_FIRST` in their README.

## §6 Mac-exec audit log schema

`logs/mac_exec.<date>.jsonl` — one JSON line per invocation:

```json
{
  "ts": "ISO 8601 UTC",
  "actor": "<mac user>",
  "forge_tool": "tool/stack_v2_sample.py",
  "forge_commit_sha": "<sha>",
  "args": "<argv array — token never present>",
  "hf_passthrough": true,
  "bytes_fetched": N,
  "duration_sec": F,
  "exit_code": 0,
  "result": "ok|hf-auth-missing|net-error|...",
  "token_redacted": "[REDACTED]"
}
```

- The `token_redacted` field is literal "[REDACTED]" — the token's
  presence is never logged in any form.
- Per-tool sub-logs continue to live in `logs/<tool>.<date>.jsonl`
  (e.g. `logs/fetch_sources.<date>.jsonl`). The mac-exec log is
  the upper layer's audit trail.

## §7 Failure modes

| Failure                                                   | Detection                                | Recovery                                                  |
| --------------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------- |
| Mac secret store missing `hf-token`                       | `secret get hf-token` non-zero exit       | `secret set hf-token <token>` on Mac, retry               |
| HF token expired                                          | `hf whoami` 401 response                  | refresh in HF web UI, `secret set hf-token <new>`         |
| Linux forge host unreachable                              | SSH timeout                              | check VPN / network; do NOT fallback to compute-on-Mac    |
| `mac-exec` binary missing on Mac                          | `command -v mac-exec` empty               | reinstall / verify Mac-side toolchain                     |
| Token leaked to a log file (any log file)                 | grep `hf_[A-Za-z0-9]{20,}` on logs/      | rotate Mac secret immediately + audit downstream uploads |
| `stack_v2_sample.py` token consumed but tool exits early  | exit code != 0, no `samples/` output     | re-run; token re-injected on each mac-exec invocation     |

## §8 Cross-link

- HF org: [https://huggingface.co/dancinlab](https://huggingface.co/dancinlab)
- v0.1.3 entry per ROADMAP: [`../ROADMAP.md`](../ROADMAP.md) §4 next-actions items 9-10
- Open decisions this runbook unblocks: D-007 / D-008 / D-009 (compute-dependent triad)
- Tool docstrings — HF auth instructions to be updated per §3 routing on next tool edit pass (deferred to v0.1.3 entry; tools currently print a 3-step instruction that's compatible with the env-var protocol)
- Nexus 2026-04-29 directive: applies to nexus's compute-on-Mac fallback, NOT to this HF-bridge use (carve-out documented above)
- Decision ledger: a follow-up `M-008` should land in `papers/plan-decisions-pending.md` to track mac-exec routing acceptance once the binary's exact shape is confirmed
