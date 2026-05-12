# Session log — 2026-05-12 closure (rounds 16-23)

Continuation of `session_log_2026-05-11.md`. Picks up at v0.2.0-r3 in flight
and lands at full v0.2.0 production-complete with 18 hexa-forge dancinlab/*
repos LIVE.

## Roundtable

| round | commit  | summary |
|-------|---------|---------|
| r16   | 5906eb3 | session log + v3 SFT tools (build_sft_dataset_v3, hexa_s0_scorer) |
| r16   | 00e11c1 | v0.2.0-r3 milestone — hexa-eval 35.7%, 5-NL 100% |
| r16   | d43dff5 | real hexa-cc S0 scorer wired into score_mk0_eval (opt-in env) |
| r17   | 2bf4713 | v0.2.0-r4 gap-targeted SFT — hexa-eval STRICT 60.71% |
| r18   | dff655f | GGUF F16 + Q5_K_M for r4 (10th + 11th repos) |
| r19   | f353c56 | Apple/Swift addition — synth_apple_sft.py + Swift in DEFAULT_LANGS |
| r19   | f363d27 | v6 builder (apple Q/A only, no swift continuation drift) |
| r20   | eb3ff79 | rounds 19-20 ROADMAP — v5 regression + v6 fix |
| r21   | bc77261 | v7 boost — T2/T3/T8 targeted (320 new pairs) |
| r21   | 01baee1 | v7 closes hexa-eval gap WITH Apple (60.7% match r4) |
| r22   | 5337b0b | recover_hf_uploads.sh — replay pending uploads after token refresh |
| r22   | 0ae6af3 | round 22 ROADMAP — r7 GGUF local-ready, HF token-refresh blocker |
| r23   | 784c15b | 100% CLOSURE — all 18 hexa-forge dancinlab/* repos LIVE |
| r23+  | (push)  | 42 commits pushed to github.com/dancinlab/hexa-forge |

## Recipe-iteration ladder (real STRICT measurements)

| round | dataset rows | epochs | LR    | final loss | hexa-eval | 5-NL  |
|-------|--------------|--------|-------|------------|-----------|-------|
| r1    | 1,000        | 1      | 2e-4  | 1.728      | 0.0%      | 40.0% |
| r2    | 964          | 1      | 2e-4  | 1.703      | 14.3%     | 64.0% |
| r3    | 1,314        | 2      | 1e-4  | 1.629      | 39.3%     | 100%* |
| r4    | 1,589        | 2      | 1e-4  | 1.595      | **60.7%** | 92.0% |
| r5    | 1,735        | 2      | 1e-4  | 1.576      | 50.0%     | 80.0% |
| r6    | 1,665        | 2      | 1e-4  | 1.610      | 53.6%     | 92.0% |
| r7    | 1,985        | 2      | 1e-4  | **1.541**  | 60.7%     | 92.0% |

\* r3 was substring-fallback scorer (loose); the real strict score was 39.3%.

## What the data taught (encoded in ROADMAP §CHANGELOG)

1. **r1**: SFT 1.0 over-refusal is a real failure mode. The 200 refusal pairs
   used `### User:/### Assistant:` template while canon used `### Canon doc:`.
   Model learned "User-template = refuse." Cost: F1 0%, F2 0%.

2. **r2**: Unifying templates fixes the over-refusal; but raw canon dumps
   don't teach FACTS. T2/T3/T5 stayed at 0%.

3. **r3**: Semantic Q/A extraction from canon spec headings teaches FACTS.
   T2/T5/T6 jumped 0→33%. Refusal contract preserved. The "structured Q/A
   vs raw dump" insight is the load-bearing one.

4. **r4**: Gap-targeted pairs (60 @grace, 50 linker triples, 100 yes/no)
   lift exactly those families. T3 0→50, T6 33→67, T8 40→80. hexa-eval 61%.

5. **r5**: Apple/Swift addition w/ unstructured continuation pairs (~70 of
   1,735 = 4%) catastrophically regressed F3 100→20 and T8 80→40. Lesson:
   "continue this file" prompts directly oppose the refusal contract;
   even 4% of dataset is enough to break it.

6. **r6**: Apple Q/A only (no continuation) — 5-NL fully recovered to 92%,
   hexa-eval partial recovery to 53.6%.

7. **r7**: r6 + T2/T3/T8 boost — hexa-eval back to 60.7% WITH Apple coverage
   intact. Best-of-both-worlds.

## Production tier

`dancinlab/hexa-forge-code-3b-Q5_K_M-GGUF-v0.2.0-r7`
- 2.07 GB GGUF
- runs on 4 GB VRAM via llama.cpp / Ollama / LM Studio
- hexa-eval STRICT 60.7% / 5-NL STRICT 92%
- SwiftUI / UIKit / Combine / SwiftData / SPM
- canonical "out-of-domain: this is a code-only model" refusal contract

## Tooling shipped this session (cumulative ~25,500 lines)

- `tool/build_sft_dataset_v3..v7.py` — 5 dataset builders (recipe iteration)
- `tool/synth_apple_sft.py` — 76 Apple-app Q/A pairs (SwiftUI / UIKit / etc)
- `tool/hexa_s0_scorer.py` — real hexa-cc compile-test scorer
- `tool/score_with_adapter.py` — adapter-aware eval runner
- `tool/score_mk0_eval.py` — base manifest scorer (now strict-capable)
- `tool/bench_humaneval.py` — HumanEval cold bench runner
- `tool/pack_corpus_parquet.py` — corpus → parquet bundler
- `tool/stack_v2_sample.py` — Stack v1/v2 sampler (now 7 langs incl swift)
- `tool/extend_tokenizer.py` — Qwen tokenizer extender (136 hexa tokens)
- `tool/recover_hf_uploads.sh` — pending-uploads replay after token refresh
- `tool/hf_publish.py` — 8-target HF publisher
- `tool/mac-exec` + `tool/forge` — Mac→Linux HF auth bridge

## Pending for v0.3.0+ (next session)

- 7B fullft (needs multi-GPU; out of RTX 5070 12 GB scope)
- MLX export for Apple Silicon (Mac-side only)
- Real hexa-eval Mk.I (750 tasks, current is 28-task Mk.0.1 starter)
- Real 5-NL Mk.I (1000 tasks, current is 25-task Mk.0.1 starter)
- DB / firmware / frontend / safety evals (Mk.I production)
- Gate ③ hexa-eval ≥ 80% (currently 60.7%, gap 19 pp)
- T5 HX-codes recovery (regressed 33→0% in r7; v8 fix candidate)
- T4 enum recovery (stuck 33%; needs hexa-cc-validated enum exemplars)
- 5-NL F3 explanation back to 100% (stuck at 60% from r4 onward)

## Push state

```
remote:  github.com/dancinlab/hexa-forge.git
branch:  main
latest:  784c15b — docs(roadmap): round 23 — 100% CLOSURE
ahead:   0  /  behind: 0
```
