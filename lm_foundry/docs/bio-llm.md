# `bio` — HEXA-BIO domain LLM recipe

> **Foundry verb.** Research recipe for a biology-domain LLM paired with
> [`hexa-bio`](https://github.com/dancinlab/hexa-bio) — genomic
> sequences, structural biology, pharmacology, and the wet-lab protocol
> language we actually run.

| field        | value                                                  |
| ------------ | ------------------------------------------------------ |
| verb         | `bio`                                                  |
| family       | `hexa-forge`                                           |
| status       | `RESEARCH_FIRST` (spec only, no weights)               |
| dispatch     | `hexa-forge bio`                                       |
| sibling CLIs | `hexa-bio` (data + assays), `hexa-codex serve`          |

---

## §WHY

Biology is **multi-modal sequence land** (DNA / RNA / protein) wrapped
in a thick layer of natural-language papers, protocols, and clinical
notes. A general LLM treats sequences as gibberish; a sequence-only
model (ESM, RNA-FM, Evo) can't read a protocol PDF or reason about a
patient note.

`hexa-forge bio` is the recipe for a **bilingual** model — fluent in
both biological **sequence tokens** and biomedical **prose** — that
can:

- read a paper and propose a CRISPR-Cas13 guide, then call out to
  `hexa-bio crispr` for off-target scoring
- annotate a ribozyme catalytic core from a raw RNA sequence
- translate a wet-lab protocol into a `hexa-bio` automation script
- flag pharmacovigilance signals from FDA AERS prose + drug labels

## §COMPARE

| approach                                  | strength                                | weakness                                       |
| ----------------------------------------- | --------------------------------------- | ---------------------------------------------- |
| sequence-only (ESM-2, RNA-FM, Evo, AlphaFold-LM) | best-in-class structure / function    | can't read prose / protocols                   |
| biomedical LLM (BioGPT, Med-PaLM, MedLM)  | strong clinical text                    | can't ingest raw sequences as first-class tokens |
| general FM + retrieval                    | flexible                                | hallucinates assays, unsafe dosing             |
| **hexa-forge `bio`**                      | **bilingual** — seq + prose first-class | smaller than general FM; narrow                |

## §REQUIRES

- base model: open-weights mid-size (target **7B–13B**)
- tokenizer: **dual vocab** — natural-language BPE + sequence k-mer
  tokens (`<DNA>`, `<RNA>`, `<AA>` modality switches)
- compute: 8× H100 for pretrain; 1× H100 + Mac Studio for SFT/LoRA
- ethics review board sign-off for any clinical evals

## §STRUCT — dataset

| stage      | corpus                                                                 | size target | filter                                              |
| ---------- | ---------------------------------------------------------------------- | ----------- | --------------------------------------------------- |
| seq-pretrain | RefSeq + UniRef90 + Rfam + ENA (DNA + protein + RNA family)           | ~400B tok   | dedup ≤ 90% identity; modality tags injected       |
| lit-pretrain | PubMed Central OA + bioRxiv + medRxiv (full text, OA only)            | ~80B tok    | OA license only; figure captions retained          |
| protocol     | protocols.io OA + Bio-Protocol OA + Nature Protocols (citation only)  | ~3B tok     | OA license; structured into step lists             |
| pharma       | DailyMed (FDA labels) + DrugBank OA + ChEMBL                          | ~5B tok     | public-domain / OA only                            |
| clinical     | MIMIC-IV (DUA), UK Biobank summary stats                              | ~10B tok    | DUA-gated; never commit raw                         |
| hexa-bio     | every doc under `~/core/hexa-bio/{biology,genetics,nanobot,...}/`     | ~0.5B tok   | full repo; weighted ×10                             |

## §FLOW — training stages

1. **Stage 0 — base.** Take open-weights base; extend tokenizer with
   sequence k-mer vocab (~8k new tokens for codons + AA k-mers).
2. **Stage 1 — interleaved pretrain.** `seq-pretrain` and `lit-pretrain`
   interleaved at 4:1 ratio. Modality switch tokens enforced.
3. **Stage 2 — SFT.** `protocol + pharma + hexa-bio` formatted as
   `<question><answer-with-citations>`.
4. **Stage 3 — RLHF/DPO.** Preference signal from:
   - sequence-task ground truth (e.g., known guide vs. random)
   - hallucination penalty on un-cited factual claims
5. **Stage 4 — alignment guard.** Refuse: bioweapon synthesis routes,
   gain-of-function uplift, unsafe dosing prescription, PHI extraction.

## §EVOLVE — eval harness

| benchmark                         | what it measures                          | acceptance bar               |
| --------------------------------- | ----------------------------------------- | ---------------------------- |
| MedQA (USMLE)                     | clinical reasoning                        | ≥ Med-PaLM 2 small-class     |
| PubMedQA                          | literature QA                             | ≥ BioGPT-Large               |
| BC5CDR / NCBI-disease (NER)       | biomedical entity recognition             | ≥ SciSpacy baseline + 5pts   |
| ProteinGym (zero-shot)            | protein fitness                           | ≥ ESM-2-650M                 |
| **hexa-bio-eval** (custom)        | hexa-bio CLI verb intent classification   | ≥ 90% top-1                  |
| **bioweapon-refusal** (custom)    | safety — must refuse uplift queries       | ≥ 99% refusal rate           |
| protocol-replication              | regenerate a known protocol from abstract | judged by 3 domain experts   |

## §VERIFY — serving contract

- **inference**: handed off to `hexa-codex serve` (NOT served here).
- **paired-call contract**: model emits structured intents that
  `hexa-bio` CLI dispatches:
  ```
  <tool_use name="hexa-bio">
    <verb>crispr</verb>
    <args>{"target": "<seq>", "system": "cas13"}</args>
  </tool_use>
  ```
- **citation contract**: every factual claim about a paper, drug, or
  assay MUST cite. Uncited factual sentences are penalized in DPO.
- **refusal contract**: hard-refuse bioweapon/gain-of-function/PHI
  queries with explicit policy text. **No jailbreak escape.**
- **clinical disclaimer**: every clinical-adjacent answer prefixed with
  `not a medical diagnosis` boilerplate.

---

## Cross-link policy

| concern                           | sibling                                  |
| --------------------------------- | ---------------------------------------- |
| genomics & wet-lab data           | `hexa-bio` CLI                           |
| inference / serving               | `hexa-codex serve`                       |
| training fabric                   | `hexa-chip` (neuromorphic)               |
| federated training transport      | `hexa-grid`                              |
| cognitive verbs (general reasoning) | `hexa-mind` (pending)                  |

## Open questions (v0.1.0)

- [ ] base weights — Llama-3.1-8B vs Qwen2.5-7B vs domain base (BioGPT-7B)
- [ ] tokenizer extension — k-mer (k=3 codon) vs character vs BPE-on-seq
- [ ] **safety stack** — primary defence: training-time refusal vs
      inference-time classifier vs both
- [ ] data DUA management — MIMIC-IV / UK Biobank pipelines (separate repo?)
- [ ] paired-call schema — JSON tool-use vs hexa-lang AST emission
- [ ] eval governance — IRB process for any eval involving real patient text
