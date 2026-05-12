# mac-exec cheatsheet — v0.1.3 G-BASE 🔥

> One-page operator cheatsheet for invoking the hexa-forge tooling from
> the Mac side via `mac-exec` with HuggingFace token passthrough.
> Defers to `papers/plan-runbook-v0.1.3.md` for the full spec.

| field        | value                              |
| ------------ | ---------------------------------- |
| target gate  | v0.1.3 G-BASE entry                |
| HF org       | `dancinlab`                        |
| forge host   | `linux-forge` (SSH)                |
| last updated | 2026-05-11                         |

---

## 0. Path conventions + first-time install

**Two paths, one repo.** The forge repo is mounted on both sides:

| side  | repo path                       | used in                                  |
| ----- | ------------------------------- | ---------------------------------------- |
| Mac   | `~/core/hexa-forge/`            | local commands, shim install             |
| Linux | `~/mac_home/core/hexa-forge/`   | inside `mac-exec --hf-passthrough` commands (since they execute over SSH) |

**First-time install on Mac** (`mac-exec` is a small bash shim shipped
with the repo at `tool/mac-exec`; symlink it onto your PATH):

```bash
mkdir -p ~/bin && ln -sf ~/core/hexa-forge/tool/mac-exec ~/bin/mac-exec && grep -q 'HOME/bin' ~/.zshrc || (echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc)
```

Verify:

```bash
mac-exec --help | head -5
```

If you see the `mac-exec — Mac→Linux HF auth bridge` banner, install is good.

---

## 1. Pre-flight check

Run these four on the Mac before any forge invocation. If any fails, stop
and resolve before proceeding to section 3.

```bash
command -v mac-exec
```

```bash
mac-exec --help | head -20
```

```bash
secret get HF_TOKEN > /dev/null && echo ok || echo MISSING
```

```bash
ssh linux-forge "ls ~/mac_home/core/hexa-forge/tool/hf_publish.py"
```

---

## 2. Shape A vs Shape B selector

After step 1 confirms binary support, USE ONLY ONE COLUMN below. Runbook
§2 cites Shape B (`--hf-passthrough`) as the higher-level alias and it is
the default in sections 3–4 of this cheatsheet.

| purpose          | Shape A (explicit env)                                                                                       | Shape B (passthrough alias) — DEFAULT                                                                |
| ---------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| dry-run a tool   | `mac-exec --inject-secret HF_TOKEN --to-host linux-forge "cd ~/core/hexa-forge && python3 tool/stack_v2_sample.py --dry-run"` | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/stack_v2_sample.py --dry-run`              |
| verify HF target | `mac-exec --inject-secret HF_TOKEN --to-host linux-forge "python3 ~/core/hexa-forge/tool/hf_publish.py verify --target stack-v2-sample"` | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py verify --target stack-v2-sample` |
| upload artefact  | `mac-exec --inject-secret HF_TOKEN --to-host linux-forge "python3 ~/core/hexa-forge/tool/hf_publish.py upload --target tokenizer"` | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target tokenizer` |
| stack-v2 fetch   | `mac-exec --inject-secret HF_TOKEN --to-host linux-forge "python3 ~/core/hexa-forge/tool/stack_v2_sample.py --sample-pct 5 --output samples/stack_v2/ --stats runs/stack_v2_sample.json"` | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/stack_v2_sample.py --sample-pct 5 --output samples/stack_v2/ --stats runs/stack_v2_sample.json` |

---

## 3. v0.1.3 G-BASE 4-step sequence

The critical path. Runbook §4. Run in order; do not parallelise.

### Step 1 — Stack v2 5% sample (closes D-009)

- **Goal:** materialise the 5% permissive subset of Stack v2 + measure token count.
- **Pre-condition:** `datasets.toml` present, `samples/` and `runs/` writable on forge host.
- **Command:**

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/stack_v2_sample.py --sample-pct 5 --tokenizer Qwen/Qwen2.5-Coder-7B --output samples/stack_v2/ --stats runs/stack_v2_sample.json
```

- **Success signal:** `runs/stack_v2_sample.json` written, per-lang token counts logged, extrapolation >= 600 B tokens.
- **Audit log:** `logs/mac_exec.<date>.jsonl` + `logs/stack_v2_sample.<date>.jsonl`.
- **Unblocks:** D-009 (corpus volume measurement).

### Step 2 — License-clean verification (closes D-009 sub)

- **Goal:** confirm the sampled subset is 100% permissive-licensed.
- **Pre-condition:** Step 1 produced `samples/stack_v2/`.
- **Command:** (no HF auth needed — stdlib only)

```bash
ssh linux-forge "python3 ~/core/hexa-forge/tool/license_clean_scan.py --manifest datasets.toml --path samples/stack_v2/ --strict --report runs/sample_license_audit.json"
```

- **Success signal:** report JSON shows 0 FAILs, 0 UNKNOWNs under `--strict`.
- **Audit log:** `logs/license_clean_scan.<date>.jsonl`.
- **Unblocks:** D-009 sub (license verification).

### Step 3 — Cold-bench across 3 candidate bases (closes D-007)

- **Goal:** comparative scores on 6 hexa specs across Qwen2.5-Coder-7B / DeepSeek-Coder-V2-Lite / StarCoder2-15B.
- **Pre-condition:** `eval/<spec>/manifest.jsonl` for all 6 specs present.
- **Command (one model × one spec; loop over 3 × 6):**

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/run_eval.py --spec hexa-eval --model Qwen/Qwen2.5-Coder-7B --task-manifest eval/hexa-eval/manifest.jsonl --output-dir runs/base-bench/qwen2.5-coder-7b/hexa-eval/ --run-id 2026-05-11-cold-bench
```

- **Success signal:** 18 `runs/base-bench/<slug>/<spec>/scores.json` files, all with `status == "ok"`.
- **Audit log:** `logs/run_eval.<date>.jsonl`.
- **Unblocks:** D-007 (base-model selection); expected winner per runbook §4.3 is Qwen2.5-Coder-7B.

### Step 4 — Tokenizer extension (closes D-008)

- **Goal:** materialise the hexa-extended tokenizer atop the D-007 winner.
- **Pre-condition:** Step 3 selected a base model; `tool/tokenizer_extension.toml` present; Step 1 produced a corpus sample.
- **Command:**

```bash
mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/extend_tokenizer.py --base Qwen/Qwen2.5-Coder-7B --extension tool/tokenizer_extension.toml --output runs/tokenizer_qwen2.5-coder-7b_hexa_v1/ --corpus-sample samples/stack_v2/rust/ --target-compression 0.5
```

- **Success signal:** round-trip verification 100%, compression ratio <= 0.5×, output dir contains `tokenizer.json` + `merges.txt`.
- **Audit log:** `logs/extend_tokenizer.<date>.jsonl`.
- **Unblocks:** D-008 (tokenizer extension acceptance).

---

## 4. HF upload targets

From runbook §5. All targets land under `dancinlab/*` (public, MIT).

Target names match `tool/hf_publish.py` canonical short form (see
`python3 tool/hf_publish.py list-targets` for live status).

| target          | phase    | hf_repo                                                | command (shape B)                                                                                          |
| --------------- | -------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| stack-v2-sample | v0.1.3   | `dancinlab/hexa-forge-corpus-stack-v2-sample-v0.1.3`   | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target stack-v2-sample`   |
| tokenizer       | v0.1.3   | `dancinlab/hexa-forge-tokenizer-qwen-hexa-v1`          | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target tokenizer`         |
| cold-bench      | v0.1.3   | `dancinlab/hexa-forge-bench-cold-v0.1.3`               | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target cold-bench`        |
| sft-lora-r16    | v0.2.0   | `dancinlab/hexa-forge-code-7b-qwen2.5-lora-r16-v0.2.0` | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target sft-lora-r16`      |
| fullft          | v1.0.0   | `dancinlab/hexa-forge-code-7b-qwen2.5-fullft-v1.0.0`   | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target fullft`            |
| gguf-q5         | v1.0.0   | `dancinlab/hexa-forge-code-7b-Q5_K_M-GGUF-v1.0.0`      | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target gguf-q5`           |
| mlx             | v1.0.0   | `dancinlab/hexa-forge-code-7b-MLX-v1.0.0`              | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target mlx`               |
| eval-results    | v1.0.0   | `dancinlab/hexa-forge-eval-results-v1.0.0`             | `mac-exec --hf-passthrough python3 ~/core/hexa-forge/tool/hf_publish.py upload --target eval-results`      |

Pre-flight any target with `... hf_publish.py dry-run --target <name>` or
`... hf_publish.py verify --target <name>` before `upload`.

---

## 5. Failure modes

From runbook §7. Recovery commands are Mac-side unless noted.

| symptom                                                | likely cause                                | recovery command                                                                                  |
| ------------------------------------------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `secret get hf-token` non-zero exit                    | Mac secret store missing the token          | `secret set HF_TOKEN <token>` then retry the failed mac-exec                                      |
| `hf whoami` 401 (run via passthrough)                  | HF token expired or revoked                 | refresh token at https://huggingface.co/settings/tokens then `secret set HF_TOKEN <new>`          |
| SSH timeout / forge unreachable                        | VPN down or forge host offline              | `ping linux-forge` and check VPN; DO NOT fallback to compute-on-Mac (runbook §1 invariant)        |
| `command -v mac-exec` empty                            | mac-exec binary not installed on Mac        | reinstall mac-exec; verify with `mac-exec --version`                                              |
| `hf_[A-Za-z0-9]{20,}` matches in any `logs/*`          | token leaked to log file                    | `secret rotate HF_TOKEN` immediately, then audit recent `dancinlab/*` HF uploads for unintended commits |
| `stack_v2_sample.py` exits non-zero, no `samples/` out | token consumed but tool aborted early       | re-run the Step 1 command verbatim; token re-injected on each mac-exec invocation                 |

---

## 6. Audit log inspection

Logs live on the forge host under `~/core/hexa-forge/logs/`:

- `logs/hf_publish.<date>.jsonl` — per-upload structured log
- `logs/mac_exec.<date>.jsonl` — upper-layer mac-exec audit trail
- `logs/<tool>.<date>.jsonl` — per-forge-tool sub-logs

```bash
ssh linux-forge "jq '.error_class' ~/core/hexa-forge/logs/hf_publish.*.jsonl | sort | uniq -c | sort -rn"
```

```bash
ssh linux-forge "jq -s 'group_by(.target) | map({target: .[0].target, last: .[-1].ts_utc, success: map(select(.result==\"ok\")) | length, total: length})' ~/core/hexa-forge/logs/hf_publish.*.jsonl"
```

---

## 7. Token hygiene rules

- Token lives in Mac-side `secret` CLI only. Never typed at prompt. Never echoed.
- `mac-exec` injects `HUGGING_FACE_HUB_TOKEN` into the SSH child process env. It evaporates when the child exits.
- Linux forge logs MAY contain `token_hash_12 = sha256(token)[:12]` (12 hex chars) for correlation only. Bare token never logged.
- Token rotation: `secret rotate HF_TOKEN` on Mac side → next `mac-exec` invocation picks up the new value automatically.

---

## 8. Cross-link to deeper specs

- Full runbook: [`../papers/plan-runbook-v0.1.3.md`](../papers/plan-runbook-v0.1.3.md)
- HF upload target list: `papers/plan-runbook-v0.1.3.md` §5
- mac-exec architecture invariants: `papers/plan-runbook-v0.1.3.md` §1
- ROADMAP bidirectional loop: `ROADMAP.md` §3
- M-008 mac-exec routing acceptance: `papers/plan-decisions-pending.md`
