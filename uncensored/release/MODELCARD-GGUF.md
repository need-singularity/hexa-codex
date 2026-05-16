---
license: gemma
license_link: https://ai.google.dev/gemma/terms
library_name: gguf
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
- gguf
- llama.cpp
- ollama
- lm-studio
- quantized
- imatrix
- conversational
- roleplay
- text-generation
- mac
- cpu
- local
quantized_by: dancinlab
inference: false
---

# Uncensored Gemma 4 (SuperGemma4 E4B Abliterated) — GGUF · full quant ladder + imatrix

**Uncensored / abliterated Gemma-4** that runs locally on llama.cpp, Ollama and
LM Studio. Q4_K_M fits in **~6 GB RAM** on any modern laptop or an 8 GB GPU.
11-quant ladder (Q2_K → BF16) plus imatrix-calibrated IQ quants for the
low-bit tier.

GGUF conversions of [`Jiunsong/supergemma4-e4b-abliterated`](https://huggingface.co/Jiunsong/supergemma4-e4b-abliterated)
— an abliterated (refusal-removed) derivative of
[`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it),
4B-active MoE. Apple Silicon? See the sibling MLX repos (link at bottom).

```bash
# llama.cpp (server, OpenAI-compatible) — chat template requires --jinja
llama-server -hf dancinlab/supergemma4-e4b-abliterated-GGUF:Q4_K_M --jinja -c 8192

# llama.cpp (one-shot CLI)
llama-cli   -hf dancinlab/supergemma4-e4b-abliterated-GGUF:Q4_K_M --jinja -p "Hello"

# Ollama
ollama run hf.co/dancinlab/supergemma4-e4b-abliterated-GGUF:Q4_K_M

# LM Studio — search "supergemma4 dancinlab" in the model browser
```

## What's in this repo

Single-file quants (download just the one you need — HF counts each `.gguf` separately):

| File | Bits | Size | RAM (typical) | Use |
|---|---:|---:|---:|---|
| `supergemma4-e4b-abliterated-Q2_K.gguf`     | ~2.6 | 4.1 GB | ~5 GB  | smallest, weakest |
| `supergemma4-e4b-abliterated-Q3_K_M.gguf`   | ~3.4 | 4.5 GB | ~5 GB  | small, fair quality |
| `supergemma4-e4b-abliterated-Q3_K_L.gguf`   | ~3.6 | 2.2 GB | ~3 GB  | tighter Q3 variant |
| `supergemma4-e4b-abliterated-imat-IQ3_M.gguf` | ~3.7 | 4.4 GB | ~5 GB  | imatrix IQ — beats Q3_K_M at same size |
| `supergemma4-e4b-abliterated-imat-IQ4_XS.gguf`| ~4.3 | 2.7 GB | ~3 GB  | imatrix IQ — punches above its weight |
| **`supergemma4-e4b-abliterated-Q4_K_M.gguf`** | ~4.8 | 5.0 GB | ~6 GB  | **recommended default** — best size/quality tradeoff |
| `supergemma4-e4b-abliterated-imat-Q4_K_M.gguf`| ~4.8 | 5.0 GB | ~6 GB  | Q4_K_M with imatrix calibration |
| `supergemma4-e4b-abliterated-Q5_K_M.gguf`   | ~5.7 | 5.4 GB | ~6 GB  | near-Q8 quality, slightly bigger |
| `supergemma4-e4b-abliterated-Q6_K.gguf`     | ~6.6 | 5.8 GB | ~7 GB  | very close to BF16 |
| `supergemma4-e4b-abliterated-Q8_0.gguf`     | 8.5  | 7.5 GB | ~9 GB  | effectively lossless |
| `supergemma4-e4b-abliterated-BF16.gguf`     | 16   | 14 GB  | ~16 GB | original precision (reference) |

> imatrix was computed on a 4 GiB English+code calibration set (group 8, ctx 512).
> Chat template is embedded in the GGUF metadata (`gemma-3` family chat template,
> Gemma-4 is template-compatible) — pass `--jinja` to `llama-server`/`llama-cli`.

## Why abliterated

The upstream `Jiunsong/supergemma4-e4b-abliterated` is an *abliterated* derivative
of `google/gemma-4-E4B-it` — refusal directions are removed from the residual
stream, reducing reflexive refusals without retraining. Quality on the upstream
release card:

| Metric (upstream) | Google base | SuperGemma4 E4B Abliterated |
|---|---:|---:|
| Release quality | 77.46 | 92.34 |
| Exact overall  | 83.50 | 98.50 |
| JSON exact     | 50.0  | 100.0 |
| Tool-call      | 90.0  | 90.0  |
| TTFT (ms)      | 4827  | 2291  |

Source: [`Jiunsong/supergemma4-e4b-abliterated`](https://huggingface.co/Jiunsong/supergemma4-e4b-abliterated) model card.

## Hardware fit

| Setup | Q4_K_M | Q6_K | Q8_0 | BF16 |
|---|:-:|:-:|:-:|:-:|
| Phone / 4 GB GPU       | ❌ | ❌ | ❌ | ❌ |
| 8 GB GPU / 16 GB CPU   | ✅ | ✅ | ❌ | ❌ |
| 12–16 GB GPU / 32 GB CPU | ✅ | ✅ | ✅ | ❌ |
| 24 GB+ GPU             | ✅ | ✅ | ✅ | ✅ |

Pick **Q4_K_M** unless you have a reason not to.

## Quickstart — three runtimes

### llama.cpp (recommended)

```bash
# Build / install (Mac): brew install llama.cpp
# Build / install (Linux): see https://github.com/ggml-org/llama.cpp/releases

# OpenAI-compatible server on http://localhost:8080
llama-server -hf dancinlab/supergemma4-e4b-abliterated-GGUF:Q4_K_M \
  --jinja -c 8192 --host 0.0.0.0
```

### Ollama

```bash
ollama run hf.co/dancinlab/supergemma4-e4b-abliterated-GGUF:Q4_K_M
```

Ollama auto-pulls GGUF directly from HF. Pick a tag from the quant table above.

### LM Studio

Open the model browser, search `supergemma4 dancinlab`, pick the quant you want.
LM Studio indexes HF GGUF repos automatically.

## Multilingual

Works in English and Korean (한국어) out of the box — Gemma-4 is natively
multilingual, and abliteration only removes refusal directions, so language
ability is unaffected.

## Chat template

Gemma-4 chat template (`<start_of_turn>...<end_of_turn>`) is baked into the GGUF
metadata. Required flag:

- `llama-server` / `llama-cli`: pass `--jinja`
- Ollama / LM Studio: auto-applied
- Manual prompt: don't — always go through the chat template

## What "abliterated" means and doesn't mean

- **Does:** reduces reflexive refusals; lets the model answer borderline-but-legal
  requests directly.
- **Does not:** make the model unsafe to deploy without your own safety layer;
  remove its tendency to confabulate; alter its base knowledge or biases.

You are responsible for the safety layer at your application boundary. Don't
ship this without one for a public service.

## License — Gemma Terms of Use (must read)

This model is a derivative of `google/gemma-4-E4B-it`, governed by the
**Gemma Terms of Use** (`license: gemma`):

- License text: https://ai.google.dev/gemma/terms
- Prohibited use policy: https://ai.google.dev/gemma/prohibited_use_policy

By downloading or using these GGUFs, you agree to the Gemma Terms of Use and
the Prohibited Use Policy. Redistribution must include the same license terms.

## Lineage

```
google/gemma-4-E4B-it
  └── Jiunsong/supergemma4-e4b-abliterated   (abliteration + tuning, BF16 safetensors)
        └── dancinlab/supergemma4-e4b-abliterated-GGUF   (this repo — quantization)
```

Conversions performed on Ubuntu 24.04 with `llama.cpp` b9174
(`convert_hf_to_gguf.py` → BF16 → `llama-quantize`; imatrix computed with
`llama-imatrix` on a 4 GiB calibration set).

## Verification

Each file is SHA256-hashed in `SHA256SUMS`. Reproducibility:

```bash
# Reconvert from upstream
hf download Jiunsong/supergemma4-e4b-abliterated --local-dir ./src
python3 convert_hf_to_gguf.py ./src --outfile bf16.gguf --outtype bf16

# Static ladder (any quant type)
llama-quantize bf16.gguf out-Q4_K_M.gguf Q4_K_M

# Imatrix
llama-imatrix -m bf16.gguf -f calibration.txt -o imatrix.dat
llama-quantize --imatrix imatrix.dat bf16.gguf out-imat-Q4_K_M.gguf Q4_K_M
```

## Credits

- Upstream model: [`Jiunsong`](https://huggingface.co/Jiunsong)
- Original base: [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it)
- Quantization, imatrix, and packaging: [`dancinlab`](https://huggingface.co/dancinlab)

Sibling repo (Apple Silicon): [`dancinlab/supergemma4-e4b-abliterated-MLX`](https://huggingface.co/dancinlab/supergemma4-e4b-abliterated-MLX) — bf16 / 4bit / 8bit.

Collection: [`dancinlab/uncensored`](https://huggingface.co/collections/dancinlab/uncensored-6a080743e6774450ba77a427).
