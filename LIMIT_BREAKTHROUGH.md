<!-- @created: 2026-05-12 -->
<!-- @scope: real-limits audit (Wave M) — AI knowledge substrate / code-gen / alignment / interpretability -->
<!-- @authority: applies LATTICE_POLICY.md §1.2 taxonomy verbatim -->
---
type: limit-breakthrough-audit
wave: M
session: 2026-05-12
parent_policy: LATTICE_POLICY.md §1.2
applies_to: hexa-codex — 17-verb AI knowledge substrate (SAFETY + ECONOMICS + OPS + SUBSTRATE)
---

# LIMIT_BREAKTHROUGH.md — hexa-codex real-limits audit (Wave M)

> **Question**: hexa-codex is a spec-first AI codex (safety probes,
> cost-curve fits, SLO checks, capability evals). Its limits live in
> **computability of semantic equivalence, Kolmogorov complexity of
> generated code, PAC-learning bounds on evaluation, and inference-cost
> floors**. Which are breakable?

---

## §1 Domain identification

| Group | Verbs (representative) | Concern |
|-------|------------------------|---------|
| SAFETY (6) | `alignment`, `interpret`, `adversarial`, `eval`, `red-team`, `unlearning` | Interp probes + capability evals |
| ECONOMICS | `infer_cost`, `quality_scale` | Cost-curve fits + scaling laws |
| OPS | `agent_serving`, `deploy`, `enterprise`, `multimodal` | SLO + production-ops envelopes |
| SUBSTRATE | `cog_arch`, `causal`, `consciousness`, `cognitive-social-psychology`, `formal`, `experiments`, `discovery` | Capability research + formal foundations |

Each verb is a **closed-form spec + falsifier preregister**, extracted
from canon `domains/cognitive/`. Lean 4 proves σ(6) = 12 in `formal/`.
17 verbs × 4 groups; 23 verify .hexa + 24 .hexa tests + 83 .py tests.

---

## §2 Real limits applicable to hexa-codex

### 2.1 Semantic equivalence of code — undecidable (MATHEMATICAL)

Two programs are *semantically equivalent* iff they compute the same
function on all inputs. This is **undecidable** (consequence of Rice
1953). Implication: any code-gen / repair / unlearning verb can only
verify *syntactic* or *test-suite-bounded* equivalence.

### 2.2 Kolmogorov complexity lower bound on code (MATHEMATICAL)

K(program) is uncomputable. Code-generation that produces "shortest
correct implementation" is **always upper-bounded**, never tight.
For benchmark suites with N test cases, the lower bound on
description length is K(N test cases) — itself uncomputable.

### 2.3 PAC-learning sample-complexity for capability evals (MATHEMATICAL)

`eval/` verb estimates "capability X" from N test instances. For
binary capability detection at ε = 0.01 error, δ = 0.01 confidence:
```
m  ≥  (1/ε²) · ( ln |H| + ln(1/δ) )  ≈  10⁴–10⁵ items
```
Major LLM evals (MMLU, GSM8K, HumanEval) sit at N=10³-10⁴ — **at
or below** the PAC floor for fine-grained capability differentiation.

### 2.4 Statistical power on alignment / red-team claims (MATHEMATICAL)

Detecting a 1% backdoor rate at α = 0.01, power = 0.9 requires
~1500 independent test prompts. Most red-team eval sets are
~100-300 prompts. **Underpowered for low-rate-failure claims.**

### 2.5 Inference-cost / Landauer-class floor (PHYSICAL)

Per-token inference at modern dense models: ~10¹² FLOPs/token at
70B params. At 10⁻¹⁵ J/FLOP (H100 datacentre, 2024), ~1 mJ/token.
**Landauer floor at 300 K** for the irreversible logic involved:
~10¹⁵ bit-erasures × 2.85 × 10⁻²¹ J ≈ 3 µJ/token. **~3 orders of
magnitude headroom** before Landauer binds.

### 2.6 Chinchilla scaling-law floor on data (ENGINEERING/MATHEMATICAL)

Hoffmann et al. (2022) Chinchilla optimum: ~20 tokens per parameter.
A 1 T-param model needs ~20 T high-quality tokens. **Total
high-quality public English text is estimated at 10-20 T tokens
(Villalobos et al. 2024).** The data wall arrives 2026-2028.

### 2.7 Interpretability circuit-extraction throughput (ENGINEERING)

Mechanistic-interp ("circuits") work currently extracts ~10-100
circuits per researcher-year (Anthropic, OpenAI, EleutherAI). A 70B
model has ~10⁵ attention heads × 10² layers ≈ 10⁷ candidate sites.
**Exhaustive circuit-mapping is engineering-impossible at current
throughput**; sampling-based interp is the only path.

### 2.8 Compute envelope per eval campaign (ENGINEERING)

Full HELM / BIG-bench / capability suite at 70B class: ~10⁴ GPU-hours,
~$30 k/campaign. Frontier models scale eval cost super-linearly
with capability surface area. **Eval cost is the binding economic
floor on red-team coverage.**

---

## §3 Per-limit breakthrough assessment

### 3.1 Semantic equivalence undecidability → **HARD_WALL**

Cannot break. **Mitigation**: contract-style differential testing
(QuickCheck-style property-based + LLM-generated boundary inputs)
gives high-confidence approximate equivalence without claiming
decidability. Honest framing should be "test-suite-bounded
equivalence", never "semantic equivalence".

### 3.2 Kolmogorov K(code) → **HARD_WALL**

Cannot break. `discovery/` and `formal/` verbs must publish *upper
bounds*, not claims of minimality. This is a documentation discipline
problem, not a research problem.

### 3.3 PAC sample-complexity on eval → **BREAKABLE_WITH_TECH (active eval)**

Active / adaptive evaluation (Lalor et al., IRT-style) cuts sample
complexity by O(log) factors via informative-item selection. Trigger:
ship an IRT-style adaptive harness in `eval/` that picks
next-instance to maximise capability-axis information gain. ~3-6
engineer-months. **High payoff.**

### 3.4 Red-team statistical power → **BREAKABLE_WITH_TECH (LLM-generated red-team)**

LLM-as-red-teamer (Perez et al. 2022, Anthropic's automated
adversarial generation) scales from ~100 hand-written prompts to
~10⁵-10⁶ machine-generated prompts — comfortably above the 1500
floor for 1% backdoor detection at α = 0.01.

### 3.5 Landauer / inference-cost → **SOFT_WALL** (reversible / analog / mixture-of-experts)

Three concurrent paths:
1. **MoE** — active params per token < 1/10 of dense → ~10× cost cut.
2. **Analog accelerators** (Mythic, IBM NorthPole, Rain.ai) — order-of-magnitude J/FLOP cut.
3. **Adiabatic / reversible logic** — long-horizon; multi-decade.

Trigger: `infer_cost/` verb integrating MoE + analog model card. Status:
**framework ready, integration pending.**

### 3.6 Chinchilla data wall → **SOFT_WALL** (synthetic + multimodal + curation)

Three approaches:
1. **Synthetic data** (LLM-generated training corpora; PHI-class).
2. **Multimodal expansion** — video / audio / code add ~50-100 T effective tokens.
3. **Quality-curation** — better filtering raises effective tokens-per-parameter.

Trigger: `quality_scale/` verb publishing measured "effective tokens
seen" vs. raw tokens. **All three are active research fronts.**

### 3.7 Interpretability throughput → **BREAKABLE_WITH_TECH (automated circuit-finding)**

Sparse-autoencoder feature dictionaries (Bricken et al. 2023, Templeton
et al. 2024) automate feature discovery, ~10⁶ features extracted per
model-week on a research cluster. Trigger: ship sparse-AE pipeline
in `interpret/`. **Already a research-stage tool; needs production-isation.**

### 3.8 Eval compute envelope → **SOFT_WALL** (subsampling + amortisation)

PAC-style coreset selection (Tukan et al. 2023) lets a subsample of
~10³ items approximate a full benchmark to within ε = 0.01. Trigger:
coreset-eval harness in `eval/`. ~2 engineer-months. Eval cost per
campaign cut by ~10×.

---

## §4 Top-3 breakthrough opportunities

### #1 — IRT-adaptive eval + sparse-AE interpretability (§3.3 + §3.7)

The two largest research-tractable levers. Adaptive eval lifts the
PAC ceiling on capability differentiation; sparse-AE pushes interp
throughput from 10² to 10⁶ features/model. Both are within
6-12 months for a small team. Together they upgrade hexa-codex from
"spec catalog" to "live measurement substrate".

### #2 — LLM-as-red-teamer in `adversarial/` (§3.4)

Closes the §2.4 statistical-power gap that today makes most
alignment claims rest on N=100-300 hand-prompts. ~1 engineer-month
to wire; near-immediate payoff in detection-power.

### #3 — `infer_cost/` MoE + analog model card (§3.5)

Quantitative cost-curve verb that respects Landauer floor + tracks
MoE/analog state-of-art. Lets enterprise consumers plan compute
budgets honestly. ~2 engineer-months.

---

## §5 Honest caveats

1. **HARD_WALLs (§3.1, §3.2) are foundational mathematics.** No
   imaginable tech breaks them. Mitigation is honest framing: never
   claim "semantically equivalent code" without bounding the
   equivalence to a test suite.

2. **Most current LLM evals are PAC-underpowered.** This is honest
   community knowledge but rarely acknowledged in benchmark papers.
   §2.3 says it explicitly.

3. **Landauer is not currently binding (§2.5)** — there's 3 orders of
   headroom. The binding cost wall is *economic*, not physical.

4. **Chinchilla data wall arrives 2026-2028** absent synthetic-data
   breakthrough. This is an industry-wide constraint, not specific
   to hexa-codex.

5. **n=6 lattice (17 verbs / 4 groups, σ(6) = 12 Lean4-proven) is
   organising vocabulary**, not a limit per LATTICE_POLICY.md.

6. **No NDA / proprietary content.** Eval costs and scaling-law
   numbers come from public papers (Hoffmann 2022, Villalobos 2024,
   Anthropic / OpenAI safety publications).

7. **Falsifier preregister (4/4 at 100%) is internal book-keeping**,
   not empirical capability validation. The audit treats spec
   parameters as the claim, not the falsifier-pass-count.

---

## §6 References

- `LATTICE_POLICY.md` §1.2 — taxonomy
- `README.md` — 17 verbs / 4 groups / spec-first framing
- `formal/` — Lean4 σ(6) = 12 proof
- `eval/`, `adversarial/`, `interpret/` — primary safety verbs
- `infer_cost/`, `quality_scale/` — economics verbs
- External: Rice (1953); Hoffmann et al. (2022) *Chinchilla*;
  Villalobos et al. (2024) *Will We Run Out of Data?*;
  Perez et al. (2022) *Red Teaming Language Models with Language Models*;
  Bricken et al. (2023) *Towards Monosemanticity (sparse AE)*;
  Templeton et al. (2024) *Scaling Monosemanticity*;
  Lalor et al. (2016) *IRT in NLP*;
  Tukan et al. (2023) *Provable Coreset Methods*.

---

*End of LIMIT_BREAKTHROUGH.md (hexa-codex, Wave M).*
