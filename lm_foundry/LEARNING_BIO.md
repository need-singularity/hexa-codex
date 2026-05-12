# LEARNING_BIO.md — what the (planned) hexa-forge **bio** model must know

> Master record for the **bio / molecular / medical** sibling model — the
> counterpart to `LEARNING_PROGRAMMING.md` (the `code` verb). The bio model
> does **not exist yet**; this file is the scaffold so when it's built the
> corpus + SFT scope is already decided. Source repos: `hexa-bio` (5-axis
> molecular toolkit, ~50 domain docs), `hexa-medic` (24-verb medicine rollup),
> `airgenome` (host-vitals genome scanner — borderline, kept for the
> "genome → forecast" pattern).
>
> ⚠️ **Hard caveat, applies to everything below — encode it into the model's
> refusal contract:** every bio/medical capability is **in-silico simulation +
> spec knowledge only**. It is **NOT** therapeutic, clinical, regulatory,
> diagnostic, immunogenic, dosing, or efficacy advice. The model must refuse
> "should I take / what dose / is this safe for a patient" prompts and redirect
> to a licensed professional. C3+ (wet-lab → IND → phase I) is out of scope.
> No medical claim is made or implied. This mirrors `hexa-bio`'s own posture.

Last updated: 2026-05-12 (scaffold; bio model not yet trained).

---

## 0. Planned model identity

| field | value (planned) |
| --- | --- |
| base | TBD — likely same family as hexa-forge code model (`Qwen2.5` or a Bio-LLM base if one exists) |
| name (planned) | `dancinlab/hexa-forge-bio-3b-…` |
| scope | molecular biology, biochemistry, pharmacology, oncology, virology, genetics, ecology/agriculture/food science — at **spec + in-silico-sim** level only |
| refusal contract | non-bio prompt → `out-of-domain: this is a bio-only model`; clinical/dosing prompt → refuse + "consult a licensed professional" |
| n=6 lattice | the bio substrate is organized around the **n=6 invariant lattice** (σ(6)=12, τ(6)=4, φ(6)=2, σ·φ = n·τ = 24, J₂(6)=24). The model should know this framing — it's the structural backbone of `hexa-bio` / `hexa-medic`. |
| NL coverage | same 5-NL plan as the code model (EN lingua franca + KR/CN/RU/JA) — terminology may stay English (Latin binomials, gene symbols, drug INNs) |

---

## 1. hexa-bio — 5-axis molecular substrate (the core)

`hexa-bio` v1.1.0 — "Molecular Toolkit (HEXA family)". 5 axes around the n=6 lattice; 4 are write-side bio sandboxes (the τ-quartet tetrahedron), the 5th is the external quantum-compute bridge.

| axis | what | maturity | model should know |
| --- | --- | --- | --- |
| **WEAVE** (hexa-weave) | viral-capsid assembly: Caspar–Klug geometry, Zlotnick cage-assembly ODE, Bayesian σ(6)=12 STRUCTURAL-EXACT audit (posterior 0.97) | full numerical empirical sandbox | T-number / quasi-equivalence, nucleation–elongation kinetics, the σ(6)=12 audit |
| **NANOBOT** (hexa-nanobot) | therapeutic nanobot design / simulation | C0b skeleton sim + σ(6)=12 verification + falsifier preregister | DNA-origami / protein-cage carriers, payload + targeting logic, in-silico only |
| **RIBOZYME** (hexa-ribozyme) | catalytic RNA design | C0b skeleton sim + verification + falsifier | hammerhead / hairpin / HDV ribozymes, cleavage-site logic, secondary structure |
| **VIROCAPSID** (hexa-virocapsid) | engineered viral capsid scaffolds | C0b skeleton sim + verification + falsifier | AAV / phage display capsids, surface display, packaging limits |
| **QUANTUM** (quantum/) | external compute bridge — VQE / qpu_bridge over `qmirror` | Phase 1+ (H₂/LiH VQE chemical & spectroscopic accuracy; F-Q-1…5 PASS; pocket-VQE F-Q-6 open) | VQE for small-molecule ground states, ansätze (UCCSD), active-space reduction, when to bridge to a real QPU |

Cross-axis: cycle 25 closed a 16-cell C2 matrix (4 bio axes × 4 disease classes) at IN-SILICO grade (16/16 PASS internal consistency). The model should know **C0b → C1 → C2 → C3** maturity grading and that C2 ≠ clinical.

---

## 2. hexa-bio — applied domain catalog (~50 docs)

Each is a domain MD in `~/core/hexa-bio/*.md`. These are the **breadth** the bio model covers — agriculture/food/ecology heavy, plus medical, plus exotic.

| cluster | domains (one row per `.md`) |
| --- | --- |
| 🧬 core biology | BIOLOGY, BIOLOGY-MEDICAL, GENETICS, IMMUNOLOGY, NEURO, NEUROSCIENCE, NEUROPHARMACOLOGY, VIROLOGY, RADIATION-BIOLOGY, SYNBIO (synthetic biology), MYCOLOGY, ENTOMOLOGY, ECOLOGY |
| ✂️ gene editing | CRISPR-GENE-EDITING, CRISPR-CAS13-POC-DIAGNOSTIC |
| 💊 medicine / therapy | CANCER-THERAPY, HIV, HIV-TREATMENT, HAIR-REGENERATION, GASTROINTESTINAL-MEDICINE, SLEEP-MEDICINE, MUSIC-THERAPY, NUCLEAR-MEDICINE, MEDICAL-DEVICE, COSMETIC-SURGERY, TATTOO-REMOVAL, TIBETAN-MEDICINE, HERBALISM, VACCINE, MICROPLASTICS (health) |
| 🦠 therapeutic nanotech | THERAPEUTIC-NANOBOT, HEXA-NANOBOT, HEXA-RIBOZYME, HEXA-VIROCAPSID, HEXA-WEAVE, HEXA-LIMB, HEXA-SKIN |
| 🌾 agriculture / food | AGRICULTURE, URBAN-FARMING, HORTICULTURE, VITICULTURE, APICULTURE (bees), AQUACULTURE, VETERINARY, BIOCHAR-DRYLAND-RESTORATION, ECOLOGY-AGRICULTURE-FOOD, FOOD-SCIENCE |
| 🧀 fermentation / artisanal | FERMENTATION, CHEESE-DAIRY, BAKING, WINE-ENOLOGY, COFFEE, COFFEE-SCIENCE, PERFUMERY |
| 🐬 bioacoustics / animal | DOLPHIN, DOLPHIN-BIOACOUSTICS, DOG-ROBOT-TEST |
| 💄 cosmetic / personal-care | MENS-INTIMATE-CLEANSER, WOMENS-INTIMATE-CLEANSER (formulation chemistry) |
| 💊 bio-pharma | BIO-PHARMA (drug pipeline, formulation, biologics) |

→ **SFT plan:** semantic Q/A extracted from each domain's spec headings (the
same recipe that worked for hexa-canon in the code model — see
`LEARNING_PROGRAMMING.md §8 rule 1`). Refusal pairs scoped to the
clinical/dosing carve-out above.

---

## 3. hexa-medic — 24-verb medicine·pharmacology·oncology·virology·cosmetic catalog

`hexa-medic` v0.1.0 — closed-form spec catalog, each verb a directory of canonical specs (migrated from `canon@ded52144`, 2026-05-10). 24 verbs:

`cancer_therapy` · `cosmetic_surgery` · `gastrointestinal_medicine` · `hair_regeneration` · `herbalism` · `hiv` · `hiv_treatment` · `immunology` · `medical_device` · `mens_intimate_cleanser` · `microplastics` · `music_therapy` · `neuropharmacology` · `nuclear_medicine` · `perfumery` · `pharmacology` · `radiation_biology` · `sleep_medicine` · `tattoo_removal` · `therapeutic_nanobot` · `tibetan_medicine` · `vaccine` · `virology` · `womens_intimate_cleanser`

n=6 master identity here: σ·φ = n·τ = 24 — the 24-verb count is not arbitrary. The model should know the verb→spec mapping (`hexa-medic/<verb>/<verb>.md`) and the "spec / sim / verified" status ladder.

---

## 4. airgenome — host-vitals genome (the "genome → forecast" pattern)

Not biology — `airgenome` is an **OS genome scanner**: project Mac / Ubuntu / Hetzner host vitals onto a 6-axis hexagon (cpu / mem / io / net / gpu / fs), 60 bytes per genome. Accumulate per-process samples → ring buffer → label anomalies → forecast 1 h ahead with Holt's double-exponential smoothing. 100% self-hosted in hexa.

Why it's in the bio file: it teaches the **"condense state into a fixed-size genome, accumulate, diff, forecast"** pattern that generalizes to actual biological time-series (a patient's vitals, a culture's growth curve, a soil panel). The model should know: the 6-axis hexagon encoding, sigdiff, ring-buffer accumulation, Holt forecasting (level + trend), and the menubar-daemon delivery shape (`airgenome.app`, single CGEventTap, `@snippets`).

---

## 5. Cross-cutting knowledge the bio model needs

| topic | why |
| --- | --- |
| n=6 invariant lattice (σ=12, τ=4, φ=2, J₂=24, σ·φ=n·τ=24) | structural backbone of every hexa-* repo |
| C0b → C1 → C2 → C3 maturity grading | so it never overclaims (C2 in-silico ≠ clinical) |
| falsifier preregistration | every hexa-bio axis ships a preregistered falsifier — the model should propose falsifiable hypotheses, not just assertions |
| VQE / quantum chemistry basics | the QUANTUM axis bridge (UCCSD ansatz, active space, chemical accuracy = 1 kcal/mol) |
| ODE modeling (Zlotnick cage assembly, growth curves) | numerical bio sandboxes |
| Bayesian posterior audits (σ(6)=12 STRUCTURAL-EXACT, posterior 0.97) | how hexa-bio validates structure |
| Caspar–Klug / quasi-equivalence | capsid geometry |
| package distribution: `hx install hexa-bio` (hexa-lang registry, GitHub-canonical — **not** HF Hub; HF Hub mirror retired 2026-05-04 because it's for ML weights/datasets not CLI tooling) | so it gives the right install instructions |
| **the clinical refusal carve-out** (see top caveat) | non-negotiable |

---

## 6. Open questions before the bio model can be built

1. **Base model.** Reuse Qwen2.5-Coder-3B (it's a code base, not ideal for bio prose) vs. a science/bio base vs. a general 7B+. Decision needed.
2. **Corpus.** hexa-bio + hexa-medic docs ≈ tens of MB of `.md` + `.hexa`. Pack to parquet like the code-canon corpus. Plus: should we pull a permissive slice of PubMed abstracts / bioRxiv / a protein-sequence corpus? (license-clean only, like the Stack v1 gate ①).
3. **Eval.** Need a `bio-eval` manifest analogous to `hexa-eval` — families for: n=6 lattice facts, axis/verb mapping, in-silico-sim recipes, the clinical refusal carve-out, domain-fact Q/A across the ~50 hexa-bio domains.
4. **Refusal scope.** Exact boundary between "explain the pharmacology of X" (allowed — textbook knowledge) and "tell me my dose of X" (refuse). Needs a written contract like the code model's `out-of-domain` rule.
5. **Repo.** Does this ship as a new `hexa-bioforge` repo, or as a second model line inside `hexa-forge`? (Probably its own repo — different corpus, different gates.)

---

## 7. Status

**Bio model: NOT STARTED.** This file is a scaffold. The code model
(`LEARNING_PROGRAMMING.md`) is at v0.2.0-r9 with 21 dancinlab/* repos LIVE; the
bio model is the next major line once the §6 questions are answered.

When work starts, mirror the code model's structure: corpus parquet →
tokenizer (if domain tokens needed) → cold bench → SFT iteration (canon Q/A +
refusal carve-out, balanced format) → GGUF → eval-results, all under
`dancinlab/hexa-forge-bio-*`.
