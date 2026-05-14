#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""serve_openai.py — OpenAI-compatible HTTP shim for hexa-forge-code GA adapter.

Loads Qwen2.5-Coder-7B (base) + dancinlab LoRA adapter via transformers + peft,
exposes `/v1/models` and `/v1/chat/completions` (with streaming SSE) compatible
with wilson's `provider-openai-compat` plugin.

The adapter (`v0.4.0-rl-t4-v3`, RL-on-LoRA r64) was trained against an
**Alpaca-style** prompt template (`### User:\n…\n### Assistant:\n`), NOT
Qwen2's native `tokenizer.chat_template`. This shim converts OpenAI
`messages[]` into that format. See `papers/spec-lever4-compile-rl.md` and the
RL GA card (`README.md` of the adapter repo).

GGUF NOT available for v0.4.0 (RL-on-LoRA doesn't cleanly GGUF-pack —
spec-lever4 §11). Only the HF safetensors path is supported.

Usage:
  python tool/serve_openai.py --host 127.0.0.1 --port 8000              # local
  python tool/serve_openai.py --host 0.0.0.0   --port 8000              # LAN serve
  python tool/serve_openai.py --no-4bit                                  # bf16 (needs 16+ GB VRAM)

Defaults to 4-bit NF4 quantization (bitsandbytes) — fits in 12 GB VRAM
(RTX 5070 etc.). bf16 needs ~16 GB VRAM (A100/3090/4090).

Deps: torch transformers peft accelerate bitsandbytes fastapi uvicorn sse-starlette
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

BASE = "Qwen/Qwen2.5-Coder-7B"
ADAPTER = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3"
MODEL_ID = "hexa-forge-code-v0.4.0-rl-t4-v3"


def load(use_4bit: bool):
    """Load base + adapter. 4-bit NF4 by default (fits 12 GB VRAM)."""
    tok = AutoTokenizer.from_pretrained(BASE)
    kwargs: dict[str, Any] = {"device_map": "auto"}
    if use_4bit:
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        kwargs["torch_dtype"] = torch.bfloat16

    base = AutoModelForCausalLM.from_pretrained(BASE, **kwargs)
    m = PeftModel.from_pretrained(base, ADAPTER).eval()
    return tok, m


def messages_to_alpaca(messages: list[dict]) -> str:
    """OpenAI `messages[]` → Alpaca `### User:\n…\n### Assistant:\n` template.

    System messages are prepended as bare text (the adapter wasn't trained on
    a separate system slot). Multi-turn alternates User/Assistant; a trailing
    `### Assistant:\n` invites the next generation.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(content)
        elif role == "user":
            parts.append(f"### User:\n{content}")
        elif role == "assistant":
            parts.append(f"### Assistant:\n{content}")
    parts.append("### Assistant:\n")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-4bit", action="store_true", help="disable 4-bit quant; load bf16 (needs ~16 GB VRAM)")
    args = ap.parse_args()

    use_4bit = not args.no_4bit
    print(f"[serve_openai] loading base={BASE} adapter={ADAPTER} 4bit={use_4bit}")
    tok, model = load(use_4bit)
    print(f"[serve_openai] model loaded on {model.device}")

    app = FastAPI()

    @app.get("/v1/models")
    def models():
        return {
            "object": "list",
            "data": [
                {
                    "id": MODEL_ID,
                    "object": "model",
                    "owned_by": "dancinlab",
                    "base": BASE,
                    "adapter": ADAPTER,
                }
            ],
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "model": MODEL_ID}

    @app.post("/v1/chat/completions")
    async def chat(req: dict):
        messages = req.get("messages", [])
        max_new = int(req.get("max_tokens", 512))
        temp = float(req.get("temperature", 0.0))
        stream = bool(req.get("stream", False))

        prompt = messages_to_alpaca(messages)
        ids = tok(prompt, return_tensors="pt").to(model.device)

        gen_kwargs: dict[str, Any] = dict(
            input_ids=ids.input_ids,
            attention_mask=ids.attention_mask,
            max_new_tokens=max_new,
            do_sample=(temp > 0.0),
            pad_token_id=tok.eos_token_id,
        )
        if temp > 0.0:
            gen_kwargs["temperature"] = temp

        if not stream:
            with torch.no_grad():
                out = model.generate(**gen_kwargs)
            text = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": MODEL_ID,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
            }

        streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
        gen_kwargs["streamer"] = streamer
        threading.Thread(target=model.generate, kwargs=gen_kwargs, daemon=True).start()

        def sse():
            created = int(time.time())
            for piece in streamer:
                chunk = {
                    "id": f"chatcmpl-{created}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": MODEL_ID,
                    "choices": [
                        {"index": 0, "delta": {"content": piece}, "finish_reason": None}
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            done = {
                "id": f"chatcmpl-{created}",
                "object": "chat.completion.chunk",
                "created": created,
                "model": MODEL_ID,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    print(f"[serve_openai] listening on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
