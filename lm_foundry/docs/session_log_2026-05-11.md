# Session log — 2026-05-11

Hexa-forge v0.1.2 → v0.2.0-r3 marathon session. Driven from Mac terminal
through `cl` to `ubu-2`, with HF auth bridged via `mac-exec`.

## Summary

- **15 rounds executed** in one session
- **7 dancinlab/* HF repos LIVE** (out of 8 planned)
- **5 hexa-codex T4 PRs landed** (forge v1.0.0 gate ⑬ ACHIEVED)
- **v0.1.3 G-BASE entry: COMPLETE**
- **v0.2.0-r2: over-refusal failure FIXED**
- **v0.2.0-r3: training in progress (PID 17525, PPID 1)**

## Cumulative commits this session

| round | sha       | summary                                                         |
|-------|-----------|-----------------------------------------------------------------|
| r1    | (earlier) | spec consolidation                                              |
| r2    | 019b0c6   | 5 bench specs + tree-sitter pack + tokenizer ext + corpus pipe  |
| r3    | 2bdb2fd   | universal runner + PPL gate + CI workflow + tooling closeout    |
| r4    | 3d16c06   | anticorpus + DPO pairs + eval lineage (DuckDB)                  |
| r5    | 100ae2f   | HF publisher (8 dancinlab/* targets) + Mac-side cheatsheet      |
| —     | b05ae29   | mac-exec bash shim (M-008 closed)                               |
| —     | a4d323e   | forge short wrapper                                             |
| —     | bb675fe   | HF auth bridge LIVE (first end-to-end success)                  |
| —     | 71c16f1   | stack_v2_sample + emit_t4 stdlib-shadow preamble                |
| —     | c6ac841   | stack_v2_sample default output path realign                     |
| —     | 3ee5b4b   | Stack v1 default + v2 SWH defer + --max-files-per-lang          |
| r7    | 6197ea4   | FIRST dancinlab/* repo (microtest, 60 files)                    |
| r8    | 2684893   | pack_corpus_parquet.py + Stack v1 field-fix                     |
| r8    | 942d5c6   | BIG CORPUS LIVE (42K rows / 81M tokens parquet)                 |
| r9    | b2d0fe7   | D-009 CLOSED — 180K rows / 653M tokens                          |
| r10   | a0401a4   | tool/bench_humaneval.py                                         |
| r10   | d68c27e   | Qwen 1.5B HumanEval 41.46% cold bench LIVE                      |
| r11   | 80f38a4   | Qwen 3B 48.78% + Mk.0.1 manifests                               |
| r12   | c1bc29a   | tool/score_mk0_eval.py                                          |
| r12   | 1cee4b4   | 5 T4 PRs landed in hexa-codex/t4_empirical/                     |
| r12   | 6b4fbb8   | v0.1.3 G-BASE COMPLETE                                          |
| r13   | b20f117   | SFT prep — canon corpus + refusal pairs                         |
| r14   | 0777625   | score_with_adapter.py + v0.2.0-r1 over-refusal demo             |
| r14   | 8cc640e   | v0.2.0-r1 SFT over-refusal documented                           |
| r15   | dea46e6   | v0.2.0-r2 format-balanced SFT (F6 0→100% fixed)                 |
| r15   | ccff635   | round 15 v0.2.0-r2 over-refusal FIXED                           |

## dancinlab/* HF repos (7 LIVE)

1. **corpus-stack-v2-sample-v0.1.3** — 180K rows / 653M tokens / 423 MB (parquet)
2. **tokenizer-qwen-hexa-v1** — 136 hexa tokens / 11.4 MB
3. **bench-cold-v0.1.3** — 8 subdirs (1.5B / 3B / Mk.0.1 hexa-eval / Mk.0.1 5-NL / r1 adapter scores / r2 adapter scores)
4. **corpus-hexa-canon-v1** — 35 repos / 2,797 rows / 8.5 MB
5. **sft-refusal-v1** — 225 pairs / 40 KB
6. **code-3b-qwen2.5-lora-r16-v0.2.0-r1** — over-refusal failure mode demo (kept honest)
7. **code-3b-qwen2.5-lora-r16-v0.2.0-r2** — over-refusal FIXED, F6 100%
8. (pending) GGUF / MLX / fullft

## Key real measurements

| metric                | base 1.5B | base 3B | r1 (broken) | r2 (fixed) |
|-----------------------|-----------|---------|-------------|------------|
| HumanEval pass@1      | 41.46%    | 48.78%  | —           | —          |
| hexa-eval Mk.0.1      | —         | 25.0%   | 0.0%        | 14.3%      |
| 5-NL Mk.0.1 overall   | —         | 72.0%   | 40.0%       | 64.0%      |
| 5-NL F1 (code synth)  | —         | 80%     | 0%          | 20%        |
| 5-NL F2 (bug fix)     | —         | 100%    | 0%          | 80%        |
| 5-NL F3 (explanation) | —         | 100%    | 100%        | 100%       |
| **5-NL F6 (refusal)** | —         | **0%**  | **100%**    | **100%** ★ |

## v0.2.0-r3 in flight (PID 17525)

- Dataset: 1,314 rows (refusal 7.6%) — see `/home/summer/runs/sft-train-v3/`
- Refusal lowered to ≤ 10% to recover F1 code synth
- Semantic hexa-canon Q/A (extract Q from spec headings, not raw dumps)
- MBPP + Stack v1 sample accept pairs
- 2 epochs × 658 steps, LR 1e-4
- Output: `/home/summer/runs/sft-lora-r16-v3/`
- Log: `/home/summer/logs/sft_train_v3b.log`

Restarted with `setsid` after the original `nohup` train run was killed by
SSH disconnect at step 263/658 (~40% complete). PPID=1 confirmed — the new
process is fully detached from any terminal session.

## Real hexa-cc S0 scorer (round 15.5)

- `tool/hexa_s0_scorer.py` (94 lines) — compile-test via `hexa_v2_linux_x86_64`
- Detects error patterns in stdout/stderr (hexa-cc returns 0 even on parse failure)
- Tested against garbage / prose / valid code — all correctly classified
- Ready to replace substring-fallback `s0_s1_exit_0` scorer in `score_mk0_eval.py`

## Pending after v3 SFT completes

1. Eval v3 adapter on hexa-eval + 5-NL (compare to r2)
2. Upload v3 adapter to `dancinlab/hexa-forge-code-3b-qwen2.5-lora-r16-v0.2.0-r3`
3. ROADMAP §CHANGELOG round 16 entry
4. Commit `tool/build_sft_dataset_v3.py` + `tool/hexa_s0_scorer.py`
5. Integrate real hexa-cc scorer into `score_mk0_eval.py` (replace fallback)
6. Compute resume signals — what's next:
   - 8th dancinlab repo: GGUF/MLX export
   - Real hexa-eval rescore with hexa-cc (gate ③ ≥ 80% bar)
   - Bigger SFT (7B + full corpus + 4-8 epochs)
