# lm_foundry — domain-LLM foundry

> Absorbed from the standalone `hexa-forge` repo on **2026-05-13**.
> The research + recipe + training substrate for **domain-specialised
> LLMs** in the dancinlab stack. Where the rest of `hexa-codex`
> serves and analyses, `lm_foundry/` *trains*.

## What this is

A narrow-and-deep approach to LLMs: a 7B–14B model that only knows
**code** (or only knows **biology**) beats a 70B generalist on its
home turf for less compute, less hallucination, and a smaller laptop.

Two seed verbs:

| verb   | what it is                          | knowledge doc                |
|--------|-------------------------------------|------------------------------|
| `code` | programming-only LLM for hexa-lang  | `LEARNING_PROGRAMMING.md`    |
| `bio`  | HEXA-BIO domain LLM (seq + prose)   | `LEARNING_BIO.md`            |

## Status (2026-05-13)

- **`code` verb — v0.4.0 GA candidate at 94.29% Mk.I strict** (627/665, 96% 5-NL).
  Path: Qwen2.5-Coder-7B + LoRA r=64 SFT (r1–r34) → Phase-A manifest
  fixes (r33, r37, r38) → **compile-feedback RL (Lever 4, GRPO)** which
  lifted T4 enum 55→100% (+45pp across r36/r38, first decisive RL win)
  → **T3 quote-fragility patch (r39) recovered T3 58.8→100%**. Gates ③
  ④ closed with double-digit headroom. **v0.4.x delegation line opened**:
  spec `papers/spec-delegation-v0.4.0.md` (r39, 354 lines, token grammar
  + runtime contract + redaction + streaming UX + routing-eval) + scaffolding
  (`eval/delegation-mk0/manifest.jsonl` 200-task, `tool/score_delegation_mk0.py`
  5-subscore, `tool/forge_runtime.py` 580-line stub) all landed. Two SFT
  delegation attempts (r40 25% mix, r41 9% mix) confirmed **SFT-only can't
  install routing without erasing specialist** — **v0.4.2 routing-RL**
  (GRPO with binary route-correctness reward) queued. Full ladder + per-round
  results in `ROADMAP.md`.
- **`bio` verb** — recipe spec landed (`LEARNING_BIO.md`); training
  pending. Paired with the `hexa-bio` data repo.

## Layout

| path | what |
|------|------|
| `LEARNING_PROGRAMMING.md` | the SSOT for "what the code-LLM must know" — 14 sections incl. hexa-canon, operator skills (RunPod/Vast/HF/R2/Docker), Claude/OpenAI/Gemini API surfaces, Wilson, the self-aware-delegation v0.4.x architecture line |
| `LEARNING_BIO.md` | same, for the bio verb |
| `ROADMAP.md` | per-round narrative — r1 through **r41**; the complete documented recipe with every failure mode preserved |
| `papers/` | design docs (`spec-lever4-compile-rl.md`, `plan-v0.3.0-structural.md`, …) |
| `tool/` | dataset builders (`build_sft_dataset_v*.py`, `build_rl_t4_prompts.py`), trainers (`train_sft_lora.py`, `train_rl_grpo_t4.py`), scorers |
| `eval/` | `hexa-eval/manifest-mk1.jsonl` (665-task Mk.I) + `five-nl-eval/` (25-task 5-NL i18n) |
| `cli/` | the `hexa-forge` verb-table CLI (`status` / `selftest` / `code` / `bio`) |
| `docs/` | per-verb recipe docs (`code-llm.md`, `bio-llm.md`) |
| `bench-cold/` | local per-round bench pulls — **gitignored**; SoT is HF `dancinlab/hexa-forge-bench-cold-v0.1.3` |
| `datasets.toml` | dataset registry |
| `IDEA.md` | local idea memo on LLM-UX pain points + learning-based fixes — **gitignored** |

## Hugging Face artifacts

**40 repos** under `dancinlab/hexa-forge-*` (adapters, GGUFs, the bench-cold
dataset). The `hexa-forge` prefix is retained as **artifact identity** —
renaming would break `from_pretrained` references in published recipes.
**GA candidate adapter:** `dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch`
(r39, 94.29% Mk.I, 96% 5-NL — pure hexa-canon specialist; delegation
queued for v0.4.2 routing-RL).
Labeled experiments (NOT GA): `…-rl-t4-v3-t3patch` is preceded by the
Lever-4 line (`…-rl-t4`, `…-rl-t4-v2`, `…-rl-t4-v3`) and followed by the
v0.4.x SFT line (`…-v0.4.0-delegate` r40, `…-v0.4.1-delegate` r41).

## Operating notes

- Cloud GPU: **Vast.ai is the primary platform** (A100 SXM4 80GB ≈ $0.87–1.07/hr,
  ~80 s ready) after RunPod's 2026-05-12 platform-wide stuck-pod incident.
  Onboarding + CLI surface in `LEARNING_PROGRAMMING.md §6`.
- Pod-side work ships a self-contained `run_pod.sh` via scp — never inline
  ssh heredocs (the "rm-disaster" rule).
- This component follows the dancinlab-wide `LATTICE_POLICY.md` (real-limits-first).
