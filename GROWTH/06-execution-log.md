# 06 — Execution Log (anchor case: dancinlab/uncensored)

Real shipping records and reusable operational lessons from executing the
`04-uncensored.md` ladder. Append-only, newest at bottom. English only.
`[fact]` = directly observed this run / `[inference]` = generalization.

---

## 2026-05-16 — GGUF full quant ladder shipped

**Outcome:** `dancinlab/supergemma4-e4b-abliterated-GGUF` is **public, non-gated,
11-quant ladder + imatrix**. Ladder steps 0–1 of `04 §8` executed.

- Repo: https://huggingface.co/dancinlab/supergemma4-e4b-abliterated-GGUF
- Quants: BF16 · Q8_0 · Q6_K · Q5_K_M · Q4_K_M · Q3_K_M · Q3_K_L · Q2_K +
  imatrix IQ3_M · IQ4_XS · imat-Q4_K_M (11 `.gguf`, each a separate file so
  HF counts per-file downloads — see `01 §3`, `02 §1`).
- Shipped alongside: model card with embedded Gemma license + Prohibited Use
  Policy link, 3-runtime copy-paste quickstart (llama.cpp / Ollama / LM Studio),
  Korean quickstart, `base_model` link to upstream, SHA256SUMS, ladder.json,
  imatrix.dat.
- Old single-file repo `…-Q4_K_M-GGUF` deprecated → README replaced with a
  "moved to" redirect (kept, not deleted, so existing inbound links survive).

### Ladder progress vs `04 §8`

| Step | Item | Status |
|---|---|---|
| 0 | Gemma license + use policy embedded in card | ✅ done |
| 0 | Chat template / GGUF metadata sanity | ✅ verified (gemma4 arch, 16k chat_template embedded, 16.9 tok/s gen) |
| 1 | Full quant ladder Q2_K–Q8_0 + IQ (imatrix) | ✅ shipped (11 files) |
| 1 | Copy-paste quickstart ×3 in card | ✅ done |
| 1 | `base_model` Model Tree link | ✅ `Jiunsong/supergemma4-e4b-abliterated`, `base_model_relation: quantized` |
| 1 | Ollama library listing + Modelfile | ⏳ next |
| 2 | KL + refusal + MMLU/IFEval table | ⏳ pending (need measured numbers — do not fabricate, `05`/anti-H4) |
| 2 | r/LocalLLaMA release post | ⏳ pending |
| 2 | ZeroGPU Space demo | ⏳ pending |
| 3 | Working MLX build | ✅ rebuilt + verified (bf16/4bit/8bit, stock mlx-lm 0.31.3, KO coherent) — upload pending |

### Reusable operational lessons `[fact]`

1. **Mirror build artifacts to a second host before they are the only copy.**
   Mac scratch (`~/scratch/sg4-quant`, `~/scratch/sg4-mlx`) was wiped
   mid-session. GGUF survived only because an `rsync` copy already sat on a
   second host (ubu1) — zero-loss recovery. MLX was Mac-only (not mirrored,
   Apple-Silicon-only) → total loss, full rebuild required. `[inference]`
   Any artifact that takes >10 min to regenerate should be pushed off-box the
   moment it exists, not after the whole batch finishes.

2. **`hf upload` can silently stall on large files.** The last 5 GB file hung
   **82 min at 0 KB/s tx** while the process stayed alive. Fix: kill + single-
   file re-upload; HF content-dedup re-sent only the new ~134 MB. `[inference]`
   Upload large GGUFs **one file per `hf upload` call** with a tx-rate
   watchdog, never a single long batch script — and monitor by polling a
   flag file written host-side, since long-held SSH monitor sessions die
   (exit 144) and the inline-ssh quoting trap (`feedback_pod_quoting`) applies.

3. **`llama.cpp` b9174 deprecated `-no-cnv`.** It now silently falls into
   interactive mode and hangs on stdin EOF — looked like a 27-min model/arch
   failure, was actually a CLI-flag artifact. Use `llama-completion`, or feed
   stdin, or just send one line. The model (gemma4 arch) was fine all along
   (78 tok/s prefill, 17 tok/s gen).

4. **`llama-imatrix` is not streaming — it full-loads the model into RAM.**
   A 14 GB BF16 OOM-killed a 24 GB Mac. Compute imatrix on a Q8_0 base
   (~10 GB) or a larger host; quality is effectively unchanged and this is
   the standard memory-constrained fallback.

5. **MLX "Missing 963 parameters" root cause + the exact working fix.**
   `Gemma4ForConditionalGeneration` is multimodal (text+vision+audio). The
   abliterated release is text-only (719 tensors) vs `mlx-vlm`'s always-built
   1682 (missing = audio 751 + vision 210 + embed 2). Plus 54 KV-shared
   residue tensors (layers 24–41 `k_proj`/`v_proj`/`k_norm`) the upstream
   safetensors physically carry → strict-load failure. **Precise toolchain
   facts (verified this run, correcting an earlier guess):**
   - `mlx-lm` **0.29.1 has no `gemma4` arch at all** (only gemma/2/3/3n).
     Gemma-4 ≠ Gemma-3n (different tensor layout, `rope_parameters`,
     `global_head_dim`, no altup/laurel). "monkey-patch gemma4 in 0.29.1" is
     impossible — that path is a dead end.
   - Stock pip **`mlx-lm==0.31.3`** ships native `gemma4` + `gemma4_text`.
     Its `sanitize` already fixes problem #1 (strips vision/audio/embed,
     remaps `model.language_model.*`) — **no patch needed for the 963**.
   - The **54-tensor KV-shared fix is NOT in the 0.31.3 release**; it landed
     on `main` post-tag as `df1d3f3c9` / PR `ml-explore/mlx-lm#1240`
     ("Fix Gemma 4 sanitize() not stripping KV projections for shared
     layers"). Fix = runtime monkey-patch `gemma4_text.Model.sanitize` with
     the verbatim #1240 body — no mlx-lm/transformers/mlx-vlm fork.
   - Python 3.9 (system mlx-lm 0.29.1) caps mlx wheels at ≤0.29.3 → must use
     an isolated `python3.13` venv with `mlx-lm==0.31.3`.
   - Effect confirmed: 719 → 665 tensors (exactly 54 stripped); layer 24
     retains only `q_proj`/`q_norm`/`o_proj`. Patch needed at **convert
     time only**, not load time → shipped builds load on stock mlx-lm.
   The exact patch body + scripts are preserved at `~/scratch/sg4-mlx/`
   (`convert.py`, `verify.py`, `venv/`). This load-failure gap in community
   MLX uploads is a real differentiation lever, not a commodity re-quant.

### Next actions (smallest viable next step)

- Ollama library listing + Modelfile (lowest-friction discovery hook, `02 §5`).
- Add new GGUF repo to the `dancinlab/uncensored` collection; drop the
  deprecated `…-Q4_K_M-GGUF` from the collection (consolidate discovery,
  anti-H8).
- SEO pass on card + collection title/description (search-magnet terms:
  "Uncensored Gemma 4", "abliterated", "no refusal", GGUF/MLX, `ko`).
- Finish MLX rebuild → ship as 3 separate repos (`-MLX-bf16/4bit/8bit`) so
  per-quant download counts accrue; add all three to the collection.
