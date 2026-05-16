---
license: gemma
license_link: https://ai.google.dev/gemma/terms
library_name: mlx
pipeline_tag: text-generation
base_model: Jiunsong/supergemma4-e4b-abliterated
base_model_relation: quantized
language:
- en
- ko
tags:
- gemma
- gemma-4
- gemma4
- abliterated
- uncensored
- uncensored-llm
- no-refusal
- mlx
- apple-silicon
- m-series
- mac
- quantized
- conversational
- roleplay
- text-generation
quantized_by: dancinlab
inference: false
---

# Uncensored Gemma 4 (SuperGemma4 E4B Abliterated) — MLX for Apple Silicon

**Uncensored / abliterated Gemma-4** for Apple Silicon — MLX builds that
**actually load on stock `mlx-lm`**. Most community MLX uploads of this base
fail with `Missing 963 parameters`; this repo's conversion fixes both root
causes so it loads and generates on a clean `pip install mlx-lm`.

```bash
pip install -U mlx-lm   # needs mlx-lm >= 0.31.3 (native gemma4 arch)

# 4-bit — recommended for 16 GB / 24 GB Macs
mlx_lm.generate --model dancinlab/supergemma4-e4b-abliterated-MLX-4bit \
  --prompt "Who are you?" --max-tokens 60

# interactive chat
mlx_lm.chat --model dancinlab/supergemma4-e4b-abliterated-MLX-4bit
```

## Builds (3 separate repos)

| Repo | Size | Peak RAM | tok/s (M-series) | Use |
|---|---:|---:|---:|---|
| **`-MLX-4bit`** | 3.9 GB | 5.4 GB | ~11 | **recommended** — 16 GB / 24 GB Mac |
| `-MLX-8bit`     | 7.4 GB | 9.1 GB | ~6  | 32 GB+ Mac, higher fidelity |
| `-MLX-bf16`     | 14 GB  | 8.6 GB | ~3  | reference, full precision |

Verified on stock `mlx-lm==0.31.3`: coherent multilingual output (English +
Korean) and correct arithmetic (`2+2=` → 4). **Text-only** — the upstream abliterated safetensors
contain no vision/audio tower weights, so multimodal MLX is upstream-blocked,
not a tooling limitation.

## Why community MLX builds fail (and how this one is fixed)

`Gemma4ForConditionalGeneration` is multimodal (text + vision + audio). Two
independent problems break naive conversion:

1. **963-tensor multimodal/text mismatch.** `mlx-vlm` always instantiates all
   three towers (1682 tensors); the abliterated text-only release has 719
   (missing = audio 751 + vision 210 + embed 2). **Fixed by stock code** —
   `mlx-lm >= 0.31.3` ships a native `gemma4`/`gemma4_text` arch whose
   `sanitize` strips vision/audio/embed and remaps `model.language_model.*`.
   No patch needed for this part.

2. **54-tensor KV-shared residue.** Gemma-4 e4b shares K/V across the last 18
   layers (24–41), but the upstream safetensors physically still carry the
   dropped `k_proj`/`v_proj`/`k_norm` for those layers → strict-load failure.
   This fix landed on `mlx-lm` `main` **after** the 0.31.3 tag
   (`ml-explore/mlx-lm#1240`), so it is **not in any pip release yet**. This
   repo applies the #1240 `sanitize` logic as a **convert-time monkey-patch**
   (no mlx-lm / mlx-vlm / transformers fork). Effect: 719 → 665 tensors
   (exactly 54 stripped).

The patch is needed **only at conversion time**. The shipped weights here
load on plain stock `mlx-lm>=0.31.3` with no patch on your side — that is the
gap that makes other MLX uploads of this model unusable.

> Note: `mlx-lm` 0.29.1 (common on Python 3.9) has **no gemma4 arch at all** —
> you need 0.31.3+. On Python 3.9 mlx wheels cap at 0.29.3, so use a
> Python 3.11+/3.13 environment.

## Why abliterated

Upstream `Jiunsong/supergemma4-e4b-abliterated` removes refusal directions
from the residual stream of `google/gemma-4-E4B-it`. Upstream release-card
numbers (vs Google base):

| Metric | Google base | SuperGemma4 E4B Abliterated |
|---|---:|---:|
| Release quality | 77.46 | 92.34 |
| Exact overall  | 83.50 | 98.50 |
| JSON exact     | 50.0  | 100.0 |

Source: [`Jiunsong/supergemma4-e4b-abliterated`](https://huggingface.co/Jiunsong/supergemma4-e4b-abliterated) model card.

## What "abliterated" means and doesn't mean

- **Does:** reduces reflexive refusals; answers borderline-but-legal requests directly.
- **Does not:** remove confabulation; alter base knowledge / biases; replace
  your own safety layer at the application boundary.

## License — Gemma Terms of Use (must read)

Derivative of `google/gemma-4-E4B-it`, governed by the **Gemma Terms of Use**
(`license: gemma`):

- License: https://ai.google.dev/gemma/terms
- Prohibited use policy: https://ai.google.dev/gemma/prohibited_use_policy

By downloading or using these MLX builds you agree to the Gemma Terms of Use
and Prohibited Use Policy. Redistribution must include the same license terms.

## Lineage

```
google/gemma-4-E4B-it
  └── Jiunsong/supergemma4-e4b-abliterated   (abliteration + tuning)
        └── dancinlab/supergemma4-e4b-abliterated-MLX-{bf16,4bit,8bit}
```

Conversion: stock `mlx-lm==0.31.3` on Apple Silicon + a convert-time
`gemma4_text.sanitize` monkey-patch (verbatim `ml-explore/mlx-lm#1240`).
No mlx-lm / mlx-vlm / transformers fork.

## Credits

- Upstream model: [`Jiunsong`](https://huggingface.co/Jiunsong)
- Original base: [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it)
- MLX conversion + packaging: [`dancinlab`](https://huggingface.co/dancinlab)

Everywhere else (llama.cpp / Ollama / LM Studio): [`dancinlab/supergemma4-e4b-abliterated-GGUF`](https://huggingface.co/dancinlab/supergemma4-e4b-abliterated-GGUF) — Q2_K → BF16 + imatrix IQ.

Collection: [`dancinlab/uncensored`](https://huggingface.co/collections/dancinlab/uncensored-6a080743e6774450ba77a427).
