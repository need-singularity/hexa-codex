# hexa-codex techniques → forge applied mapping

> **Resolves the technical-content mining gap** (user steer 2026-05-11).
> Linkage was already in place (per `docs/code-llm.md` Cross-link policy);
> this doc closes the loop by extracting the concrete techniques each
> consumed hexa-codex verb prescribes and mapping them into forge surfaces.
>
> **Scope.** 5 hexa-codex verb specs (read-only inputs):
> `train_cost`, `infer_cost`, `quality_scale`, `eval`, `deploy`. Citations
> point to file + §-anchor; **no inline copy** of hexa-codex content
> (1-line snippets only when load-bearing). Forge surfaces named here
> are **proposals** — actual edits happen at integration time and are
> tracked via §7 spec-edit queue.

| field        | value                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------- |
| status       | DESIGN_LOCKED                                                                               |
| last regen   | 2026-05-11                                                                                  |
| inputs       | 5 hexa-codex verb specs (train_cost / infer_cost / quality_scale / eval / deploy)            |
| outputs      | 63 applied rows + 11 new D-NEW decisions                                                    |
| convention   | priority = **must** (blocks v1.0.0 gate) / **should** (raises gate ceiling) / **could** (v1.1.0+) |

---

## §1 Training-cost reduction (A) — mined from `train_cost` + `quality_scale`

> Forge's 7B-class target sits **below** hexa-codex's 70B/300B reference
> setpoint, so the techniques translate as *qualitative recipes* rather
> than as billion-dollar scaling re-derivations. Where hexa-codex sets a
> ratio (e.g. D/N≈20, FP8 30% memory cut), forge inherits the *ratio*,
> not the *absolute value*.

| # | technique | hexa-codex source | forge surface | priority |
| -- | ----------- | ---------------- | ------------- | -------- |
| A1 | **Chinchilla-optimal D/N ≈ 20** (token:param ratio) | `train_cost/ai-training-cost.md` §S7.0 CONSTANTS (`CHINCHILLA_RATIO=20`), §S7.2 CROSS (3 estimator cross-check) | `docs/code-llm.md §STRUCT` — `pretrain-bias` row size target (currently `~600B tok`) sanity-checked against `D = 20 × N_base`. For Qwen2.5-Coder-7B → target ≈ 140B tok continued-pretrain; forge over-shoots at 600B → flag as **deliberate over-training** like LLaMA (inference-cost-driven, see A2). | must · **APPLIED** |
| A2 | **Deliberate Chinchilla violation** (LLaMA-style D/N ≫ 20 to reduce inference cost) | `train_cost/ai-training-cost.md` §S7.10 COUNTER ("LLaMA: deliberate over-training (D/N=140) — inference-cost reduction objective") | `papers/plan-execution-roadmap.md` v1.0.0 gate — document forge's D/N as an **intentional over-train** (inference-cost dominant for laptop tier). New row in `outbox/hexa-codex/train_cost/<run_id>.md` Numbers field: `D_over_N_actual` so the violation is auditable. | must · **APPLIED** |
| A3 | **Mixed precision (BF16 default, FP8 QAT pilot)** | `train_cost/ai-training-cost.md` §S2 COMPARE ("FP8 QAT memory 40% reduction"), §S10 PREDICTIONS #4 (`FP8 QAT cuts memory ≥35% with <0.5% loss drop`) | `docs/code-llm.md §FLOW` — Stage 2 (SFT) detail: declare BF16 as default, FP8 QAT as **D-NEW-A** decision (see §6). Adds `precision` field to `outbox/hexa-codex/train_cost/<run_id>.md` Numbers. | must · **APPLIED** |
| A4 | **FSDP / ZeRO sharding for 8×H100 SFT** | `train_cost/ai-training-cost.md` §S2 COMPARE (FSDP/DeepSpeed ZeRO-3 60% MFU target), §S11 PERF | `docs/code-llm.md §REQUIRES` — already mentions `8×H100`; add MFU target ≥ 50% as **secondary acceptance bar** (§EVOLVE eval-time check). | should · **APPLIED** |
| A5 | **Gradient accumulation = J₂(6)=24 micro-steps** | `train_cost/ai-training-cost.md` §V2-5 P-TRN-6 ("J₂(6)=24 grad-accum steps"), §V3-1 T-2 breakthrough (`accum = J₂(6)/τ(6) = 6` comm-cost reduction) | `docs/code-llm.md §FLOW` Stage 2 SFT detail row: `grad_accum_steps = 24` as proposed default; `comm_step_ratio = 1/6`. | should · **APPLIED** |
| A6 | **Curriculum learning** (easy→hard, general→specialized) | `train_cost/ai-training-cost.md` §S6 EVOLVE Mk.II + §S7.6 CHI2 (curriculum t-test, Cohen's d "medium"), §S10 PREDICTIONS #1 (20-30% convergence-step reduction) | `docs/code-llm.md §FLOW` Stage 1 (domain-pretrain): order = `pretrain-bias → domain-bias → hexa-native (last)`. Already implicit; promote to explicit ordering rule. | should · **APPLIED** |
| A7 | **Synthetic data ≤ τ(6):1 ratio of real with 5-gen variance monitor** | `train_cost/ai-training-cost.md` §V2-2 BT-385 (synthetic:real = 4:1), §S10 PREDICTIONS #7 ("30% synthetic safe", collapse within 5 generations is failure trigger) | `docs/code-llm.md §STRUCT` `philosophy` row already does ×5-10 synth expansion. Add **D-NEW-B** to cap synth share at 80% of stage and require Shumailov-style variance monitor across regen cycles. | must · **APPLIED** |
| A8 | **LoRA / QLoRA for stage 2 SFT** (rank r=16 default) | `quality_scale/ai-quality-scale.md` §S7.0 CONSTANTS (`LORA_RANK=16`), §V2-2 BT-388 (LoRA hot-swap), §S7.0 ratio `2r/d=1/128` | `docs/code-llm.md §FLOW` — Stage 2 (SFT) is currently silent on full-FT vs LoRA. **D-NEW-C**: full-FT vs LoRA (r=16) vs QLoRA (NF4 + r=16). Affects `§REQUIRES` compute (LoRA fits 1×H100 vs full-FT 8×H100). **CONFLICTS with current D-007 implicit assumption of full-FT** when sizing compute. | must · **APPLIED** |
| A9 | **AdamW with n=6 hyperparameter cluster** (lr=3e-4, β=(0.9, 0.999), wd=0.1) | `train_cost/ai-training-cost.md` Appendix ("AdamW 5-fold convergence pattern (BT-54)"), §S7.4 SENSITIVITY (LR schedules) | `docs/code-llm.md §FLOW` Stage 2 SFT hyperparameters block (new): adopt lr=3e-4, β₁=0.9, β₂=0.999, ε=1e-8, wd=0.1 as proposed defaults; document the BT-54 lineage. | should · **APPLIED** |
| A10 | **WSD (Warmup-Stable-Decay) LR schedule** | `train_cost/ai-training-cost.md` §S7.4 SENSITIVITY (cosine vs linear vs WSD), §S10 PREDICTIONS #9 ("WSD beats cosine 1-3% final loss") | `docs/code-llm.md §FLOW` Stage 1 + Stage 2: prescribe WSD with `stable_frac=0.8`, `warmup=2000`. **D-NEW-D**: cosine (safe default) vs WSD (better, less validated at 7B). | could · **APPLIED** |
| A11 | **MoE σ(6)=12 experts / τ(6)=4 active** | `train_cost/ai-training-cost.md` §V2-2 BT-384, §V3-1 T-1 breakthrough; `quality_scale/ai-quality-scale.md` §S7.0 (`MOE_EXPERTS=8`, `MOE_TOP_K=2`) | **Out-of-scope for v1.0.0** (forge §REQUIRES specifies dense 7B-14B). Logged as **could-priority** for v1.1.0+ when a MoE-capable base appears (e.g. DeepSeek-MoE-Lite). | could · PENDING |
| A12 | **Distillation 14B → 7B** | `quality_scale/ai-quality-scale.md` §S6 EVOLVE Mk.I (teacher-student), §S7.1 DIMENSIONS (KD loss + temperature), §V2-2 BT-386 (88% quality retention, T=4.0) | `docs/code-llm.md §FLOW` Stage 4 already lists `distillation (optional). 14B → 7B for laptop serve` — promote from optional to **must** for laptop tier with proposed `KD_TEMPERATURE=4.0`, per-layer KD loss weighting. Add Stage-4 acceptance bar: ≥85% MMLU/HumanEval retention vs teacher. | should · **APPLIED** |
| A13 | **Per-layer importance scoring for selective pruning** | `quality_scale/ai-quality-scale.md` §S6 EVOLVE Mk.II ("structured pruning + QAT integration"), §S7.4 SENSITIVITY (cliff at ρ≈0.6) | Not adopted in v1.0.0 — distillation handles size reduction. Logged as **could** for a v1.1.0 prune pass on the 14B (if 14B path activates). | could · PENDING |
| A14 | **Dedup (MinHash + semantic similarity)** | `train_cost/ai-training-cost.md` §S13 DATAFLOW (Dedup MinHash+semantic), §S8 IDEAS #4 (MinHash++ semantic dedup → 30% corpus compression) | `datasets.toml` — already declares "near-dup removal" for pretrain-bias. Promote to explicit two-stage: MinHash exact-dedup → embedding-based semantic dedup. Affects `tool/license_clean_scan.py` neighbour to add `tool/dedup_pipeline.py`. | should · **APPLIED** |
| A15 | **Quality filter (perplexity + toxicity + informativeness)** | `train_cost/ai-training-cost.md` §S13 DATAFLOW (quality filter ladder), §S8 IDEAS #11 | New `tool/corpus_quality_filter.py` proposed; forge's anti-corpus filter (per `papers/plan-execution-roadmap.md §5`) covers toxicity-like rejects but not perplexity/informativeness scoring. **D-NEW-E**: do we add perplexity gate to v0.1.2 sampling pipeline? | could · **APPLIED** |
| A16 | **Asynchronous checkpoints (P₂=28 min interval)** | `train_cost/ai-training-cost.md` §V2-5 P-TRN-2 (P₂=28 checkpoint), §S8 IDEAS #15 | `docs/code-llm.md §VERIFY hardware tier` — out-of-band ops detail; recommend 28-minute async checkpoint cadence for the 8×H100 SFT window. Goes into `papers/plan-execution-roadmap.md §6 v1.0.0` ops notes. | could · PENDING |
| A17 | **Chinchilla violation detector (real-time D/N monitor)** | `train_cost/ai-training-cost.md` §V2-2 BT-383, §S10 PREDICTIONS #6 (F1 ≥ 0.9) | New `tool/chinchilla_monitor.py` — reads `runs/<id>/loss.parquet` mid-run, alerts if D/N drifts outside target band. Feeds `outbox/hexa-codex/train_cost/<run_id>.md` Numbers field `D_over_N_actual` (see A2). | could · PENDING |
| A18 | **Effective FLOP estimate** (cost ∝ N^24 falsifier hook) | `train_cost/ai-training-cost.md` §S7.1 DIMENSIONS (`training_cost(N, D, mfu, …)`) | Forge's F-CODEX-1 T4 emit script (`tool/emit_t4_train_cost.hexa` per `plan-feedback-channel-ops.md §3`) — Numbers field must include: `N`, `D`, `total_flops`, `gpu_hours`, `cost_usd`, `mfu_observed`. This is the empirical T4 datapoint the falsifier wants. | must · PENDING |

**§1 sparse-section note.** `train_cost` §S6 EVOLVE Mk.I–Mk.V is dense
(11 stages × multiple techniques each). `quality_scale` §S6 EVOLVE is
also dense. Both surfaced more techniques than forge can absorb at
v1.0.0; the **could**-priority rows above are pre-staged for v1.1.0
revisits rather than dropped.

---

## §2 Inference-cost reduction (B) — mined from `infer_cost` + `deploy`

> Forge's hardware tier ladder (`docs/code-llm.md §VERIFY hardware tier`)
> already prescribes Q5_K_M / Q6_K / Q8_0 / Q4_K_M by tier; this section
> mines hexa-codex for the *underlying quality-vs-size theory* that
> justifies those choices, plus serving-time techniques not yet named.

| # | technique | hexa-codex source | forge surface | priority |
| -- | ----------- | ---------------- | ------------- | -------- |
| B1 | **INT4 (GQA) group quantisation, group_size=128** | `infer_cost/ai-inference-cost.md` §S2 COMPARE (`INT4 (GPTQ/AWQ) 3.2-3.5x throughput`), §V2-2 BT-382 (`SNR_int4_group = 46.9dB`, group=128) | `docs/code-llm.md §VERIFY hardware tier` — current M4 Mini row says `Q5_K_M / Q6_K`; align with GGUF naming. Add a note: Q4_K_M corresponds to AWQ-style INT4 group=128, justified by 25.84+21.07 dB SNR. | must · PENDING |
| B2 | **Quantisation quality floor at INT3** (`SNR < 19.82dB`, MMLU drops > 1%) | `infer_cost/ai-inference-cost.md` §S7.10 COUNTER ("INT3 below infeasible without specialized techniques"), §V2-3 I-3 (`Quantization Noise Floor`) | `docs/code-llm.md §VERIFY hardware tier` — explicitly forbid Q3/Q2 from the ladder; refusal note: "M4 Mini 8GB ⇒ refuse to serve, do not down-tier to Q2/Q3" (currently flagged loosely as "do NOT fit"). | should · **APPLIED** |
| B3 | **PagedAttention (vLLM-style)** | `infer_cost/ai-inference-cost.md` §S6 EVOLVE Mk.II, §S2 COMPARE (4.2x batching gain), §S8 KEY #1 | `docs/code-llm.md §VERIFY` serving handoff: `vLLM` already named as third-tier; document that vLLM = PagedAttention. Per D-011 (resolved), GGUF first, MLX next, vLLM last. No new decision; just annotate. | should · **APPLIED** |
| B4 | **Continuous batching** (95% GPU util target) | `infer_cost/ai-inference-cost.md` §V2-2 BT-381 (`utilization = 1 - sopfr(6)/100`), §S8 KEY #24, §S10 PREDICTIONS #4 (2-3x vs static) | `outbox/hexa-codex/infer_cost/<run_id>.md` Numbers schema — must include `batching_mode` (static / continuous), `gpu_utilization_pct`. Feeds F-CODEX-2 T4. | must · PENDING |
| B5 | **Speculative decoding (γ=5, acceptance≥0.8 target)** | `infer_cost/ai-inference-cost.md` §S7.2 CROSS (acceptance prob `min(1, q/p)`), §S10 PREDICTIONS #3 (3x speedup on code, low-entropy) | `docs/code-llm.md §VERIFY` serving contract — add **D-NEW-F**: for code generation (low entropy), enable speculative decoding when serving 14B with a 7B draft. Speedup expected 2-3x. | should · **APPLIED** |
| B6 | **FlashAttention-2/3** | `infer_cost/ai-inference-cost.md` §S2 COMPARE (4x memory, 1000ms TTFT), §S6 EVOLVE Mk.II, §S8 KEY #13 | `docs/code-llm.md §VERIFY` serving handoff — vLLM and llama.cpp Q*_K* paths inherit FlashAttention by default; add note that GGUF + llama.cpp on Apple Silicon uses Metal-flavored equivalents (no native FA-3). Pure documentation. | could · **APPLIED** |
| B7 | **Prefix / prompt caching (90% TTFT cut on system-prompt hit)** | `infer_cost/ai-inference-cost.md` §S7.7 OEIS (LRU hit-rate, Zipf 50%+ on cache=10), §S8 KEY #4 | `docs/code-llm.md §VERIFY` agent-loop — forge tool surface (`read_file`, `apply_patch`, …) implies long stable system prompts → prefix cache big win. **D-NEW-G**: declare prefix-cache requirement in serving handoff doc and surface it as an F-CODEX-2 T4 measurement (`cache_hit_rate` field). | should · **APPLIED** |
| B8 | **KV-cache INT4 quantisation** | `infer_cost/ai-inference-cost.md` §S7.1 DIMENSIONS (`kv_cache_bytes`), §S8 KEY #2, §V2-2 BT-380 (10x compression triple = `INT4 + H2O eviction + low-rank`) | At M4 Mini 16GB with 16-32k context the bare KV cache (FP16) bites; recommend KV-cache INT4 as a serving option. Adds `kv_quant_bits` to `outbox/hexa-codex/infer_cost/<run_id>.md`. | could · **APPLIED** |
| B9 | **Context^4 cost scaling (F-CODEX-2)** | `infer_cost/ai-inference-cost.md` §S7.4 SENSITIVITY (`O(n²)` standard, `O(n)` linear/FlashAttention), §V2-3 I-1 memory-BW wall | `docs/code-llm.md §VERIFY hardware tier` — the laptop tier's `16-32k KV` headroom comment is the operational form of context^4. F-CODEX-2 T4 PR template (`plan-feedback-channel-ops.md §2`) must include a context-sweep table: `(context_len, ttft_ms, tps, kv_cache_gb)` at 1k / 4k / 16k / 32k. | must · **APPLIED** |
| B10 | **TTFT vs TPS bound decomposition** (prefill compute-bound, decode memory-bound) | `infer_cost/ai-inference-cost.md` §S7.6 CHI2 (`prefill_time_ms` vs `decode_time_ms`), §S7.9 SYMBOLIC (`token_latency_model`) | `outbox/hexa-codex/infer_cost/<run_id>.md` Numbers schema — split `ttft_ms` and `tps` reporting; do NOT collapse to single "latency". Per-hardware: M4 Mini / M4 Pro / Mac Studio / 1× H100. | must · PENDING |
| B11 | **Memory-bandwidth wall lower bound** | `infer_cost/ai-inference-cost.md` §V2-3 I-1 (`T_decode ≥ W / BW_HBM`; 70B INT4 → TPS ≤ 96) | `docs/code-llm.md §VERIFY hardware tier` — for 7B Q5/Q6 on M4 Mini, the analog: `decode_TPS ≤ HBM_BW_M4 / model_bytes`. Useful as a sanity ceiling for the F-CODEX-2 T4 number; do not over-claim. | should · PENDING |
| B12 | **GQA / MQA conversion for KV-cache reduction** | `infer_cost/ai-inference-cost.md` §S7.0 (`N_KV_HEADS=8` vs `N_HEADS=64`), §S8 KEY #9 | Inherited from Qwen2.5-Coder-7B base (already GQA). No new action; documented in **D-007** rationale. | (n/a — already in base) |
| B13 | **Egyptian-fraction infer time split: prefill 1/2 + decode 1/3 + overhead 1/6** | `infer_cost/ai-inference-cost.md` §V2-5 P-INF-1 | F-CODEX-2 T4 Numbers field: `time_split_prefill_pct`, `time_split_decode_pct`, `time_split_overhead_pct`. Sanity check against the 50/33/17 reference. | could · PENDING |
| B14 | **Hardware tier ladder (M4 Mini / Pro / Studio / H100)** | `deploy/ai-deployment.md` §6 EVOLVE roadmap (4-stage rollout), §S2 COMPARE, plus `infer_cost/ai-inference-cost.md` §V2-1 DSE | **Already in `docs/code-llm.md §VERIFY hardware tier`** — D-003 resolved. This row exists to formalise that forge's tier recipe **is** the hexa-codex/deploy hardware-tier T4 PR target (per `plan-feedback-channel-ops.md §1`). | must · **APPLIED** |
| B15 | **Cost target $/1M tokens** (F-CODEX-2 quantitative) | `infer_cost/ai-inference-cost.md` §S11 PERF ($15→$1.5→$1.0/1M tok target), §V2-1 DSE rank-1 ($0.95 INT4-AWQ + H100-SXM + bs=64) | F-CODEX-2 T4 Numbers field: `cost_per_1m_output_tokens_usd` at each tier. Hard to compute on Mac silicon (no $/hour clean comp); for H100 tier use $3.50/GPU-hr per hexa-codex §S7 constants. | should · PENDING |

**§2 sparse-section note.** `deploy/ai-deployment.md` is **the sparsest of
the five** — only 364 lines, no §V2/V3 breakthrough scaffold, §S6 EVOLVE
collapses to a 4-row table without Mk.I→Mk.V tier ladder. Most of the
inference-cost techniques have to be mined from `infer_cost` instead.
Deploy's value-add is the **incident / rollout / SLA** axis (see §5
Deployment patterns), not inference optimisation.

---

## §3 Quality-scaling (C) — mined from `quality_scale`

| # | technique | hexa-codex source | forge surface | priority |
| -- | ----------- | ---------------- | ------------- | -------- |
| C1 | **Chinchilla scaling exponents** (α=0.34, β=0.28, E=1.69) | `quality_scale/ai-quality-scale.md` §S7.3 SCALING (`quality(n_params)` curve); shared with `train_cost` §S7.0 | F-CODEX-1 T4 emit script — when reporting loss vs FLOPs, fit `L = E + A·N^-α + B·D^-β`; report `(A, B, α, β, E)` so hexa-codex can compare against canon constants. | should · PENDING |
| C2 | **Compression headroom thesis** (70B can hit ~93% of 400B quality) | `quality_scale/ai-quality-scale.md` §S7.3 SCALING (final print: `compression headroom exists -- 70B can reach 93% of 400B`) | `docs/code-llm.md §EVOLVE` acceptance bars — the bar `≥ DeepSeek-Coder-V2-7B` on HumanEval+ is *forge-relative*; add hexa-codex-relative bar: target ≥ 90% retention of teacher-class on hexa-eval (if a teacher run exists). | could · PENDING |
| C3 | **Quality retention triple cross-check (MMLU + HumanEval + MT-Bench, harmonic mean)** | `quality_scale/ai-quality-scale.md` §S7.2 CROSS (3-metric retention) | `docs/code-llm.md §EVOLVE` — already has multi-bench rows. Add a **harmonic-mean retention** computed across HumanEval+ / SWE-bench Lite / hexa-eval to one row of `outbox/hexa-codex/quality_scale/<run_id>.md`. | should · PENDING |
| C4 | **Compression Pareto frontier (prune × quant × distill × LoRA × MoE)** | `quality_scale/ai-quality-scale.md` §V2-1 DSE top-5 (rank-1 = `prune 0.3, INT4, T=4, LoRA r=16, MoE 8/2 → 9.5x compression, q=0.886`) | Hint for future 7B distillation experiments; logged in **D-NEW-H** (see §6) but **not v1.0.0 blocking** — forge's v1.0.0 is single base + SFT + optional Stage-4 distill, not a multi-axis compression sweep. | could · PENDING |
| C5 | **LLM-judge for quality scoring** vs **rule-based fallback** | `quality_scale/ai-quality-scale.md` §S6 EVOLVE Mk.IV ("real-world A/B tests"), §S14 TOOLING (`lm-eval-harness`) — *and* `train_cost/ai-training-cost.md` §S7.10 COUNTER (model-collapse limits on iterated synth) | **CONFLICT with forge D-013 (resolved).** D-013 already deferred LLM-judge to v2 (Shumailov 2024 model-collapse risk). This row records that the conflict is **acknowledged** — hexa-codex describes LLM-judge as part of the methodology stack; forge has chosen rule-based v1 for explicit risk reasons. The 80/20 calibration ratio mentioned in the task prompt (D-015 default) is **not yet stated** anywhere I found; this is a gap in the source documents. See **D-NEW-H** for "LLM-judge calibration ratio" as a new decision. | must · **APPLIED** (conflict resolved via §FLOW Stage 3 + §EVOLVE blockquotes) |
| C6 | **Information-theoretic ceiling (Shannon H(D))** | `quality_scale/ai-quality-scale.md` §V2-3 V2-3-1 (`I(T;S) ≤ N_s · log₂(Q)`), §V2-3 V2-3-4 (quant-quality floor) | Documentation only; informs the **acceptance ceiling** in `docs/code-llm.md §EVOLVE` — bars cannot exceed `H(corpus) / N_params`. No code action. | could · PENDING |
| C7 | **Test-time compute scaling** (sampling N + CoT + tree-of-thought) | **GAP — not explicitly covered** in `quality_scale` (the spec emphasises *parameter scaling*, not inference-time scaling). Adjacent in `eval` §S8 KEY #15 (pairwise) and `infer_cost` §S8 KEY #16 (Medusa) but no dedicated test-time-compute treatment. | Logged as **D-NEW-I** for forge to decide independently: do we enable `best-of-N` sampling or self-consistency at serving time? Not yet specified by hexa-codex. | could · **APPLIED** (Stage 5 placeholder in §FLOW) |

**§3 sparse-section note.** `quality_scale` is rich on **compression**
techniques but thin on **test-time compute scaling** (CoT, ToT,
best-of-N, self-consistency). This is an honest gap in the upstream
spec; forge cannot mine what isn't there. C7 above logs the gap rather
than inventing content.

---

## §4 Evaluation methodology (D) — mined from `eval`

| # | technique | hexa-codex source | forge surface | priority |
| -- | ----------- | ---------------- | ------------- | -------- |
| D1 | **Dynamic item generation (vs fixed benchmark)** | `eval/ai-eval-pipeline.md` §S6 EVOLVE Mk.II, §S8 KEY #1, §V2-2 BT-395 (`1/τ(6)=4x CAT efficiency`), §S10 PREDICTIONS #1 (`40%+ discrim boost`) | `docs/code-llm.md §EVOLVE` — currently lists **fixed** benchmarks (HumanEval+, SWE-bench Lite, hexa-eval, …). Add a **could-row**: `dynamic-hexa-eval` that regenerates items per release. Logged as **D-NEW-J**. | could · **APPLIED** (deferred to v0.2.0 via §EVOLVE blockquote) |
| D2 | **Adaptive testing (CAT / IRT 3PL)** | `eval/ai-eval-pipeline.md` §S7.1 DIMENSIONS (3PL: `P(θ) = c + (1-c)/(1+exp(-a(θ-b)))`), §S8 KEY #12, §S10 PREDICTIONS #2 (1/3 items for SE<0.3) | Out-of-scope for v1.0.0 (forge benches are fixed-budget). Logged for v1.1.0+ once hexa-eval has ≥ 200 calibrated items. | could · **APPLIED** (deferred to v0.2.0 via §EVOLVE blockquote) |
| D3 | **Contamination detection: n-gram overlap (≥30% = suspected)** | `eval/ai-eval-pipeline.md` §S7.0 CONSTANTS (`CONTAMINATION_NGRAM_THRESHOLD = 0.30`), §S8 KEY #5 | `tool/contamination_scan.py` (new) — runs on every `outbox/hexa-codex/quality_scale/<run_id>.md` emit; rejects PRs where train corpus n-gram overlap with eval set ≥ 30%. Affects `papers/plan-execution-roadmap.md §5 v0.2.0` infra list. | must · **APPLIED** (deferred to v0.2.0 via §EVOLVE blockquote) |
| D4 | **Contamination detection: embedding similarity (≥0.90 = confirmed)** | `eval/ai-eval-pipeline.md` §S7.0 CONSTANTS (`CONTAMINATION_EMBEDDING_THRESHOLD = 0.90`), §S8 KEY #5 | Companion to D3; same `tool/contamination_scan.py`. Uses a lightweight embedding model (sentence-transformers MiniLM or equivalent). | must · **APPLIED** (deferred to v0.2.0 via §EVOLVE blockquote) |
| D5 | **Contamination detection: membership inference** | `eval/ai-eval-pipeline.md` §V2-2 BT-397 (`triple defense; Π = 0.30 × 0.90 × 0.95 ≈ 1/τ(6)`) | Companion to D3+D4 — the third leg of the "triple defense". Higher engineering cost; v1.1.0+ as `should`. | should · PENDING |
| D6 | **LLM-as-judge with human calibration anchor (5-10% human)** | `eval/ai-eval-pipeline.md` §S7.0 CONSTANTS (`HUMAN_LLM_CORRELATION_MIN = 0.85`), §S6 EVOLVE Mk.III, §V2-2 BT-396 (φ(6)=2 axes × τ(6)=4 calibration steps), §S10 PREDICTIONS #3 (κ ≥ 0.90 target) | **CONFLICT with D-013 (resolved):** forge defers LLM-judge to v2 (model-collapse risk per Shumailov 2024). hexa-codex/eval treats LLM-judge as core methodology assuming calibration controls the bias. Decision **D-NEW-H** (LLM-judge calibration ratio, default 80% LLM / 20% human anchor per task prompt) makes the trade-off explicit. The 80/20 ratio is **not** stated in hexa-codex/eval; it's a forge-side proposal awaiting upstream alignment. | must · **APPLIED** (conflict resolved via §FLOW Stage 3 + §EVOLVE blockquotes) |
| D7 | **Multi-LLM panel (3+ judges, λ(6)=2 minimum consensus)** | `eval/ai-eval-pipeline.md` §S8 KEY #13, §V2-5 EP-4 (`λ(6)=2 minimum, 3-panel practical optimum`), §S10 PREDICTIONS #5 | When v2 LLM-judge eventually lands (post-D-013 re-open), default to 3-panel. Logged as **could** under same D-NEW-H umbrella. | could · PENDING |
| D8 | **Adversarial test generation** | `eval/ai-eval-pipeline.md` §S8 KEY #2 (`weakness-targeted item gen`), §S6 EVOLVE Mk.III | `tool/adversarial_eval_gen.py` (new) — produces probe items targeting forge's known weak spots (e.g. obscure firmware peripheral init, rare CJK comment patterns). v0.2.0+. | could · PENDING |
| D9 | **Multilingual eval design (balanced, native-designed not translated)** | `eval/ai-eval-pipeline.md` §S6 EVOLVE Mk.II ("multilingual eval set design"), §S10 PREDICTIONS #8 ("translation-based has 15%+ bias") | **Aligns with forge `5-NL eval` (custom).** `docs/code-llm.md §EVOLVE` already lists 5-NL eval with `≥70% pass cross-lang`. Add to `papers/spec-five-nl-eval.md`: require **native-designed** items per language (not English-translated). Per-lang attribution to hexa-codex eval Mk.II. | must · PENDING (spec-five-nl-eval.md edit is in §7 queue) |
| D10 | **IRT 3-parameter difficulty calibration** | `eval/ai-eval-pipeline.md` §S7.1 DIMENSIONS (`a, b, c` parameters), §S8 KEY #6 | Per-item `(a, b, c)` triples stored in `papers/spec-hexa-eval.md` item bank. Future work — v0.2.0+ when item bank grows past ~50. | could · PENDING |
| D11 | **Saturation detector** (top-3 spread < 0.05, mean > 0.95) | `eval/ai-eval-pipeline.md` §S7.0 CONSTANTS (`SATURATION_CEILING = 0.95`, `SATURATION_SPREAD = 0.05`), §S7.3 SCALING, §S8 KEY #21 | `outbox/hexa-codex/eval/<run_id>.md` Numbers field — when reporting bench scores, compute `(mean, spread)` against the top-3 reference models on each bench. If saturation triggers, raise to **D-NEW-J** (regen items). | should · PENDING |
| D12 | **Goodhart limit (metric-gaming half-life ≈ σ(6)=12 rounds)** | `eval/ai-eval-pipeline.md` §V2-3 V2-3-1 (`Corr(A, M_t) ≤ Corr(A, M_0) · exp(-γt)`), §S7.5 LIMITS (Goodhart sim) | Documentation only; `papers/plan-decisions-pending.md` rule: any single bench that forge optimises against directly must be retired after σ(6)=12 forge releases without an external (out-of-distribution) sanity check. No code action. | could · PENDING |
| D13 | **Triple-contamination Pareto: n-gram(0.30) × embed(0.90) × member-inf(0.95) ≈ 1/τ(6)** | `eval/ai-eval-pipeline.md` §V2-2 BT-397, §V2-3 V2-3-4 (`Recall ≤ 1 - 0.7^(1/3) ≈ 0.113`) | Adds an upper-bound caveat to D3+D4+D5: even triple defense only reaches ~11% recall on paraphrase-attack contamination. Documented in `papers/plan-execution-roadmap.md §5 v0.2.0` license-clean CI gate (the same gate that runs contamination scan). | could · PENDING |
| D14 | **Pearson + Spearman + Kendall human↔LLM-judge cross-validation** | `eval/ai-eval-pipeline.md` §S7.2 CROSS (triple correlation) | When v2 LLM-judge lands, every release must report `(r, ρ, τ)` triplet for the judge-vs-human anchor sample. Goes into `outbox/hexa-codex/quality_scale/<run_id>.md` Numbers. | could · PENDING |
| D15 | **Lost-in-the-middle (LITM) long-context degradation** | `eval/ai-eval-pipeline.md` §S10 PREDICTIONS #9 ("100K+ context: mid-position accuracy 20%+ lower") | At 7B / M4 Mini, forge's serving context is 16-32k — mostly under LITM threshold. Documented as a v1.1.0+ concern when 14B + longer context lands. | could · PENDING |

**§4 sparse-section note.** `eval` §S6 EVOLVE Mk.I is honestly thin —
the entry literally reads "existing-bench audit + saturation analysis +
LLM-judge baseline + human-eval correlation analysis". The substance
lives in §S7 (VERIFY constants) and §S8 KEY (30 ideas) and §V2-2 BT
breakthroughs. The mapping above pulls from those sections, not Mk.I.

---

## §5 Deployment patterns (E) — mined from `deploy`

> `deploy/ai-deployment.md` is the **sparsest** of the five specs:
> 364 lines, no §V2/V3 breakthrough scaffold, no Mk.I→Mk.V roadmap (just
> a 4-stage table in §6 EVOLVE). The verb is genuinely shallower than the
> others. Honest mapping below — half the rows note "no concrete forge
> action yet because forge is RESEARCH_FIRST with no serving fleet".

| # | technique | hexa-codex source | forge surface | priority |
| -- | ----------- | ---------------- | ------------- | -------- |
| E1 | **4-stage rollout: canary 1% → staging 10% → limited GA 50% → full GA** | `deploy/ai-deployment.md` §S5 FLOW, §S8 IDEAS C1, §S7.0 CONSTANTS (`STAGES = [0.01, 0.10, 0.50, 1.00]`) | Forge has **no serving fleet** (per `docs/code-llm.md §VERIFY` "inference handed off to hexa-codex serve"). Logged as a recommendation for `hexa-codex serve` downstream, not for forge directly. **Hardware-tier deployment recipe** in `outbox/hexa-codex/deploy/<run_id>.md` is the forge → codex PR direction (per `plan-feedback-channel-ops.md §1`). | (n/a for v1.0.0) |
| E2 | **Auto-rollback within 5 min on SLA breach** | `deploy/ai-deployment.md` §S1 WHY (`Rollback time < 5min`), §S8 IDEAS C3 | Same: downstream of forge. Not actioned. | (n/a) |
| E3 | **Safety SLA targets**: reject<2%, hallucination<1%, p99<500ms, injection-block>95% | `deploy/ai-deployment.md` §S7.0 CONSTANTS, §S9 METRICS | `docs/code-llm.md §EVOLVE` already has a `safety: off-domain refusal ≥ 95%` row — this aligns with the injection-block bar. Add to **acceptance bars**: `reject < 2%` (false-refusal on legitimate code requests), `hallucination < 1%` on the build-trace subset. Latency (`p99 < 500ms`) is per-hardware-tier, lives in F-CODEX-2 T4 contract. | should · **APPLIED** (cross-link annotation in §VERIFY deployment patterns) |
| E4 | **A/B chi-square significance test (p<0.05, n≥400)** | `deploy/ai-deployment.md` §S7.6 CHI2 (`chi2_ab` 2×2 contingency) | When forge ships v0.1 → v0.2 → v1.0, A/B compare on the **fixed eval bank** with χ² test. New `tool/ab_significance.py`. v0.2.0+. | could · PENDING |
| E5 | **Canary risk-boundary computation** `R = p × q × N` | `deploy/ai-deployment.md` §S7.9 SYMBOLIC | Downstream of forge (no fleet). Documented for `hexa-codex serve`. | (n/a) |
| E6 | **Layered prompt-injection defense (5-stage)** | `deploy/ai-deployment.md` §S8 IDEAS D1-D8 (sysprompt-robust / injection-classifier / safe-prompt / de-obfuscate / multi-turn / indirect-injection / risk-score / context-defense) | **Aligns with forge `refusal contract`** in `docs/code-llm.md §VERIFY`. Off-domain refusal already covered; injection (D2) is *not* covered. **D-NEW-K**: add an injection-classifier eval as a v1.1.0 safety bench row (English-canonical refusal text). | should · PENDING |
| E7 | **Falsifier (production trip-wires)**: `scaling O(n²)+`, `injection F1 < 0.7`, `A/B flipped`, `canary miss > 10%` | `deploy/ai-deployment.md` §S7.10 COUNTER (FALSIFIERS list) | `papers/plan-execution-roadmap.md §6 v1.0.0` gate — add a tripwire row: if forge's eval slate ever produces `O(n²)` scaling on context (i.e. violates F-CODEX-2 spec), block the v1.0.0 release. | should · PENDING (roadmap edit is in §7 queue) |
| E8 | **Streaming safety check (token-wise classifier)** | `deploy/ai-deployment.md` §S8 IDEAS B4 ("token-wise realtime safety eval, stop on unsafe sequence") | Out of scope for v1.0.0; v1.1.0+ if streaming-toxicity becomes a measured failure mode. | could · PENDING |

**§5 honest assessment.** Most of `deploy/ai-deployment.md`'s techniques
are *downstream of forge* — they apply to the `hexa-codex serve` runtime,
not to the forge training pipeline. Forge's contribution upstream is
the **hardware-tier deployment recipe** (M4 / Mac Studio / H100) per
the existing feedback-channel mapping; the rest stays on the codex side.

---

## §6 New decisions (D-NEW)

> Final integer IDs are assigned at integration time. Internal letters
> A..K used here for cross-reference; they do **not** collide with the
> existing D-001..D-031 in `papers/plan-decisions-pending.md` §3-§4.

| ID       | proposed                                                                                              | rationale                                                                                                                                                | blocks                                       | blocked by             |
| -------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------- |
| D-NEW-A  | Precision policy for SFT — *BF16 default; FP8 QAT pilot deferred to v1.1.0*                            | hexa-codex §S2 COMPARE promises 40% memory cut for FP8 QAT but flags long-horizon stability risk (§S7.10). 7B-class is small enough that BF16 fits.       | A3 (mixed precision applied)                 | v0.2.0 hardware audit  |
| D-NEW-B  | Synthetic data ceiling — *cap synth share at 80% of any stage; require 5-gen variance monitor*         | Inherits hexa-codex BT-385 ratio (τ(6):1) + S7.10 COUNTER (collapse within sopfr(6)=5 generations). Mirrors forge D-013 model-collapse caution.            | A7 (synth ratio bound); `philosophy` stage   | D-013 (resolved)       |
| D-NEW-C  | Stage-2 SFT regime — *LoRA (r=16) default; full-FT only if LoRA underperforms by >3% on hexa-eval*    | hexa-codex BT-388 (LoRA hot-swap, 0.24% trainable). **CONFLICTS with `§REQUIRES` 8×H100 sizing** — LoRA only needs 1×H100. Compute-budget downsizing.    | A8 (LoRA stage); `§REQUIRES` compute row    | v0.1.3 base decision   |
| D-NEW-D  | LR schedule — *WSD (stable_frac=0.8) over cosine on v0.2.0 SFT*                                         | hexa-codex S7.4 SENSITIVITY + S10 PREDICTIONS #9. 1-3% final-loss advantage; safe to default once WSD is empirically replicated on 7B-class.              | A10 (LR schedule applied)                    | A9 (AdamW cluster)     |
| D-NEW-E  | Corpus quality filter — *add perplexity gate (`PPL_threshold` per source) to v0.1.2 sampling*           | hexa-codex S13 DATAFLOW + S8 IDEAS #11. Currently forge gates by license + anti-corpus only; perplexity adds a quality axis.                              | A15 (quality filter); `datasets.toml` schema | v0.1.2 audit completes |
| D-NEW-F  | Serving speculative decoding — *enable γ=5 spec-decode on 14B tier (7B draft) at v1.1.0*               | hexa-codex S7.2 + S10 PREDICTIONS #3 (3x code-gen speedup, low entropy). 14B tier currently lacks a draft model; resolve when v1.1.0 ships 14B.            | B5 (spec-decode)                             | v1.0.0 ships 14B path  |
| D-NEW-G  | Prefix cache mandate — *require prefix cache + report `cache_hit_rate` in F-CODEX-2 T4 PRs*            | hexa-codex S7.7 OEIS (Zipf 50%+ hit even at cache=10). Forge's agent-loop has long stable system prompts → very high hit rates expected.                  | B7 (prefix cache)                            | v0.2.0 serving infra   |
| D-NEW-H  | LLM-judge calibration ratio — *80% LLM-judge / 20% human anchor when v2 judging lands (post-D-013 reopen)* | Task prompt cited an existing forge default `80/20`; this ratio is **not yet anywhere in forge papers** (verified by grep). hexa-codex §S7.0 only sets `HUMAN_LLM_CORRELATION_MIN = 0.85` and §S6 Mk.III prescribes "human anchor 5-10%". 80/20 is *stricter than* hexa-codex baseline → forge proposal awaits upstream alignment. | C5, D6, D7 (LLM-judge methodology)           | D-013 v2 re-opening    |
| D-NEW-I  | Test-time compute scaling — *enable best-of-N sampling (N=4) on hexa-eval at serving time*             | **Gap-fill**: hexa-codex `quality_scale` does not cover test-time scaling. Forge can experiment independently and feed back as hexa-codex/quality_scale §S6 EVOLVE Mk.III input. | C7 (test-time compute)                       | v0.2.0 eval infra      |
| D-NEW-J  | Dynamic hexa-eval — *regenerate 20% of items per release (LLM-gen + IRT calibration)*                  | hexa-codex BT-395 + §S10 PREDICTIONS #1. **Conflicts internally with D-013** (no LLM-judge ⇒ no LLM-gen either, same Shumailov risk). Deferred to v1.1.0. | D1, D11 (dynamic generation, saturation)     | D-NEW-H resolution     |
| D-NEW-K  | Prompt-injection refusal bench — *add `injection-eval` (5-NL × adversarial probes) at v1.1.0*          | hexa-codex `deploy` §S8 D1-D8 + §S9 METRICS (`injection F1 > 0.95` target). Distinct from off-domain refusal (which is in v1.0.0 bar).                    | E6 (injection defense)                       | v1.0.0 baseline ships  |

**D-NEW summary:** 11 new decisions (A–K), of which:
- **2 are must-priority** (D-NEW-B, D-NEW-C) — these affect v1.0.0 cost/compute sizing.
- **5 are should-priority** (D-NEW-A, D, E, G, H) — these raise the v1.0.0 ceiling without gating it.
- **4 are could-priority** (D-NEW-F, I, J, K) — slip-window to v1.1.0+.

---

## §7 Spec-edit queue

> **DO NOT apply these edits in this task.** This queue is the *batch input*
> for a follow-up M-NNN consolidation (similar to M-001 which folded D-014
> through D-031 into the recipe). Each item below references its source row
> from §§1-5 above.

### `docs/code-llm.md` §STRUCT — weight / size adjustments
- pretrain-bias size sanity check vs Chinchilla D/N ≈ 20 (A1) — annotate the `~600B tok` row with "deliberate over-train per A2".
- `philosophy` row — explicit 80%-cap on synthetic share + 5-gen variance monitor (A7 / D-NEW-B).
- New row anchor for "quality-filter ladder" (perplexity + toxicity + informativeness) per A15 / D-NEW-E.

### `docs/code-llm.md` §FLOW — stage detail additions
- **Stage 1 (domain-pretrain)**: explicit ordering `pretrain-bias → domain-bias → hexa-native` (A6 curriculum).
- **Stage 2 (SFT)**: precision = BF16 (A3 / D-NEW-A); grad_accum_steps = 24 (A5); LR schedule = WSD (A10 / D-NEW-D); LR/optimizer = AdamW @ 3e-4 / β=(0.9, 0.999) / wd=0.1 (A9).
- **Stage 2 (SFT) regime**: LoRA r=16 default, full-FT contingent (A8 / D-NEW-C) — this resizes §REQUIRES compute.
- **Stage 4 (distill)**: promote from `optional` to **must for laptop tier**; T=4.0; per-layer KD loss (A12).

### `docs/code-llm.md` §VERIFY hardware tier — quantisation tier updates
- Annotate M4 Mini row with "Q5_K_M / Q6_K = INT4/INT5 group=128 per AWQ, SNR 46.9 dB" (B1).
- Explicit refusal: M4 Mini 8 GB ⇒ refuse-serve, no down-tiering to Q2/Q3 (B2).
- New row in `outbox/hexa-codex/infer_cost/<run_id>.md` schema: context sweep at 1k / 4k / 16k / 32k for F-CODEX-2 T4 (B9 / B10).

### `docs/code-llm.md` §EVOLVE — bench design / acceptance bars
- Harmonic-mean retention across HumanEval+ / SWE-bench Lite / hexa-eval (C3).
- Triple contamination scan on every eval slate (D3 + D4 + D5).
- Saturation detector emits warning when top-3 spread < 0.05 (D11).
- New v1.1.0 bench rows (logged, not applied at v1.0.0): `dynamic-hexa-eval` (D-NEW-J), `injection-eval` (D-NEW-K).
- Safety SLA additions: reject < 2%, hallucination < 1% on build-trace subset (E3).

### `papers/plan-execution-roadmap.md` — new exit-bar items
- **v0.1.2 exit bar:** add license-clean CI + contamination scanner (D3 + D4) co-deployment.
- **v0.2.0 §5 infra list:** add `tool/dedup_pipeline.py` (A14), `tool/contamination_scan.py` (D3+D4), `tool/chinchilla_monitor.py` (A17), `tool/corpus_quality_filter.py` (A15 / D-NEW-E).
- **v1.0.0 gate:** add tripwire row — F-CODEX-2 context-cost scaling must not exceed `O(n²·⁵)` (E7 falsifier-bound).
- **v1.0.0 gate:** add metric — MFU observed ≥ 50% for SFT window (A4).

### `papers/plan-decisions-pending.md` §3 — D-NEW row insertions
- Append all 11 D-NEW rows from §6 above, renumbered to next available D-NNN integers (D-032..D-042 expected).

### `datasets.toml` — schema / weight / tier adjustments
- Add `quality_score` field per entry (perplexity output of A15 / D-NEW-E pipeline).
- Add `n_gram_overlap_with_eval` field, populated by contamination scan (D3).
- Tier flag adjustment: `synth_share_cap = 0.80` is a per-stage field, populated at sampling time (D-NEW-B).
- New schema_version bump required (per `datasets.toml` header rule).

### `outbox/hexa-codex/<verb>/<run_id>.md` — Numbers schema
- **train_cost**: `N`, `D`, `total_flops`, `gpu_hours`, `cost_usd`, `mfu_observed`, `precision`, `D_over_N_actual`, scaling-fit coefs `(A, B, α, β, E)` (A2, A3, A18, C1).
- **infer_cost**: `ttft_ms`, `tps`, `kv_cache_gb`, `cache_hit_rate`, `batching_mode`, `gpu_utilization_pct`, `kv_quant_bits`, `time_split_{prefill,decode,overhead}_pct`, `cost_per_1m_output_tokens_usd`, **per-context-length** rows (B4, B7, B8, B10, B13, B15, B9).
- **quality_scale**: harmonic retention across 3+ benches, `(r, ρ, τ)` for any judge calibration (C3, D14).
- **eval**: `(top_3_mean, top_3_spread)` saturation pair per bench; contamination scan results `(ngram_overlap, embed_sim, member_inf_score)` triple (D11, D3, D4, D5).
- **deploy**: hardware-tier recipe row (already covered by feedback-channel mapping; no new fields needed).

---

## §8 Conflicts surfaced

| # | conflict                                                                                  | hexa-codex side                                                                          | forge side                                                                                              | resolution                                                                                         |
| - | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1 | LoRA vs full fine-tune sizing                                                             | `quality_scale` BT-388 favors LoRA r=16 (0.24% trainable, 1×H100 sufficient)             | `docs/code-llm.md §REQUIRES` sizes for 8×H100 SFT (implies full-FT)                                     | **D-NEW-C**: default LoRA, escalate to full-FT only if hexa-eval underperforms by >3%.            |
| 2 | LLM-judge for quality scoring                                                             | `quality_scale` Mk.IV + `eval` §S6 Mk.III treat LLM-judge as core methodology            | **D-013 (resolved)** defers LLM-judge to v2, model-collapse risk per Shumailov 2024                     | Acknowledged disagreement. **D-NEW-H** specifies an 80/20 calibration ratio for when v2 reopens.   |
| 3 | Dynamic item generation requires LLM-gen                                                  | `eval` BT-395 prescribes dynamic items (regen per evaluation)                            | D-013 also bars LLM-judge **and by extension LLM-generation** for synth corpus                          | **D-NEW-J** defers dynamic hexa-eval to v1.1.0+, contingent on D-NEW-H reopening.                  |
| 4 | MoE architecture                                                                          | `train_cost` BT-384 + `quality_scale` §S7.0 (`MOE_EXPERTS=8`, top_k=2) assume MoE        | Forge `§REQUIRES` is dense 7B-14B (Qwen2.5-Coder-7B base candidate per D-007)                           | No active conflict — forge is dense-only at v1.0.0. MoE is a v1.1.0+ path if a MoE base emerges.   |
| 5 | Chinchilla D/N target                                                                     | `train_cost` §S7.0 prescribes D/N ≈ 20 (Chinchilla optimum)                              | Forge `pretrain-bias = ~600B tok` on a 7B base ⇒ D/N ≈ 85 (4x over-trained)                             | Documented as **deliberate violation** per A2 / hexa-codex S7.10 COUNTER ("LLaMA-style 140").     |
| 6 | Calibration ratio 80/20                                                                   | Not stated in hexa-codex/eval (which uses `human_correlation_min=0.85` + "5-10% anchor") | Task prompt asserts "forge's D-015 default = 80/20"                                                     | **D-NEW-H** registers 80/20 as a forge proposal **awaiting upstream alignment** — currently a gap. |
| 7 | Test-time compute scaling                                                                 | Not covered in any of the 5 specs (gap in upstream)                                      | Forge has no current policy                                                                             | **D-NEW-I** logged as forge-initiated; feed back to hexa-codex/quality_scale Mk.III.               |

---

## §9 Sparse-section honesty notes

Per the task constraint ("if a hexa-codex spec is sparse on technique, say so honestly"):

- **`deploy/ai-deployment.md`** is the sparsest verb sampled (364 lines vs ~1600-1900 for the others). No §V2/V3 breakthrough scaffold; no Mk.I→Mk.V tier ladder (just §6 EVOLVE 4-row month-1/2/3/4 table). Its richest content is in §S8 IDEAS (26 ideas across 4 pillars) and the §S7 verification stub — but most of these techniques are *downstream of forge* (SLA, rollback, canary). Hardware-tier deployment recipes are the only forge-actionable surface, and those flow upstream via the existing feedback-channel mapping. **Half of §5's mapping rows above are honestly marked "(n/a for v1.0.0)" or "(n/a)".**
- **`eval/ai-eval-pipeline.md` §S6 EVOLVE Mk.I** is genuinely thin (single-sentence: "existing-bench audit + saturation analysis + LLM-judge baseline + human-eval correlation analysis"). The technique substance lives in §S7 VERIFY constants and §S8 KEY's 30 ideas — that's where §4 above sources from.
- **`quality_scale/ai-quality-scale.md`** is **rich on compression** (distill / prune / quant / LoRA / MoE) and **thin on test-time compute scaling** (CoT, ToT, best-of-N, self-consistency). C7 logs this as an honest gap rather than fabricating content.
- **`train_cost/ai-training-cost.md` §V2/§V3** are extensive but operate at the 70B/300B scale; forge's 7B-class translates the *ratios* (D/N, MFU, MoE active%) but not the *absolute dollar figures*. A1, A2 explicitly document this re-scaling.
- **`infer_cost/ai-inference-cost.md`** is the most directly forge-applicable of the five — its TTFT/TPS decomposition, KV-cache math, and quantisation theory map cleanly to forge's existing hardware-tier ladder.

---

## §10 Row-count summary

| section | bucket                          | rows | of which `must` | `should` | `could` | n/a |
| ------- | ------------------------------- | ---- | --------------- | -------- | ------- | --- |
| §1      | Training-cost reduction (A)     | 18   | 5               | 7        | 6       | 0   |
| §2      | Inference-cost reduction (B)    | 15   | 5               | 5        | 4       | 1   |
| §3      | Quality-scaling (C)             | 7    | 1               | 2        | 4       | 0   |
| §4      | Evaluation methodology (D)      | 15   | 4               | 2        | 9       | 0   |
| §5      | Deployment patterns (E)         | 8    | 0               | 3        | 2       | 3   |
| **total** | **mapped techniques**         | **63** | **15**        | **19**   | **25**  | **4** |

D-NEW count: **11** (A through K).
Conflicts surfaced: **7**.
Sparse-section caveats: **3** (deploy / eval-Mk.I / quality_scale-test-time).

---

## §11 Cross-link

- Recipe spec: [`../docs/code-llm.md`](../docs/code-llm.md)
- Sister specs (live): see `docs/code-llm.md` Cross-link policy
- Decision ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
- Upstream contract: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md)
- Roadmap exit bars: [`plan-execution-roadmap.md`](plan-execution-roadmap.md)
- Source specs (read-only inputs):
  - `~/core/hexa-codex/train_cost/ai-training-cost.md`
  - `~/core/hexa-codex/infer_cost/ai-inference-cost.md`
  - `~/core/hexa-codex/quality_scale/ai-quality-scale.md`
  - `~/core/hexa-codex/eval/ai-eval-pipeline.md`
  - `~/core/hexa-codex/deploy/ai-deployment.md`
