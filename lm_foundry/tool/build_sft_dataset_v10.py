#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v10.py — add the RunPod / cloud-GPU operations block.

Owner request: "RUNPOD 안정적인 구동에 대해서도 학습필요" — the model should know
how to drive cloud GPU jobs without the failure modes already hit in `anima`
(`~/core/anima/config/runpod.json`, schema 2.1, 16 incidents -> 12 absolute
rules). Also serves as a re-score of v9: if r10's hexa-eval comes back to ~60%
that confirms r9's 46% was Mk.0.1 (n=28) generation variance, not a regression.

v10 = v9 base (2,303) + ~70 RunPod / cloud-GPU ops Q/A pairs.

OUTPUT
    /home/summer/runs/sft-train-v10/train.jsonl
    /home/summer/runs/sft-train-v10/MANIFEST.json
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
import random
from pathlib import Path

random.seed(42)

V9_BASE = Path("/home/summer/runs/sft-train-v9/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v10")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


def gen_runpod() -> list[dict]:
    pairs = [
        ("What's the first thing to do after creating a RunPod GPU pod, and why?",
         "Set the HuggingFace token immediately: `echo $HF_TOKEN > ~/.cache/huggingface/token && export HUGGING_FACE_HUB_TOKEN=$HF_TOKEN`. Unauthenticated HF downloads are ~10x slower."),
        ("Can I download a model while a training job is running on the same pod?",
         "No. A download (e.g. huggingface-cli download) during a training step silently kills the training process — no error, just gone, because of shared NFS/disk I/O contention. Run downloads and training strictly sequentially."),
        ("How big can a corpus be before I should chunk-tokenize it on a pod?",
         "About 500 MB. A single `tokenizer(corpus)` call on ~1.2 GB blew up to ~119 GB RAM and took 15+ minutes. For anything over ~500 MB, tokenize in <=500-line chunks or pre-split the corpus into shards."),
        ("Why does my bf16 training crash with AdamW?",
         "AdamW with `foreach=True` (the default) crashes on mixed-dtype parameters in bf16. Fix: pass `foreach=False` to the optimizer, and re-cast parameters to the target dtype every step."),
        ("How should I run a long training job on a RunPod pod so it survives SSH disconnect?",
         "`setsid nohup python3 train.py > train.log 2>&1 < /dev/null &` — RunPod base images usually don't have tmux (`tmux: command not found`), so use setsid+nohup. The job reparents to init and keeps running."),
        ("How many checkpoints should I keep on a pod, and why?",
         "At most 2 (the latest + one fallback). Disk quotas are tight; `torch.save` fails *silently* when the quota is hit, so delete old checkpoints before saving a new one."),
        ("What should I check before creating a new RunPod pod?",
         "Run `runpodctl pod list` first. A pod may already be running — a duplicate pod wastes money and burns GPU quota. Reuse an existing pod if there is one; only create when none exist."),
        ("My training watchdog keeps restarting forever with empty logs. What's wrong?",
         "The watchdog is blindly restarting a missing or broken script. Add: (1) a check that the target script actually exists, and (2) a failure counter that gives up after N consecutive failures instead of looping."),
        ("What RunPod base image should I use for a PyTorch training pod?",
         "An official RunPod PyTorch image, e.g. `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` — SSH is ready in ~30 s and the CUDA stack is pre-wired. Custom images are slower to boot and flakier."),
        ("How do I verify dependencies before launching a training job on a fresh pod?",
         "Set `PYTHONPATH` and run `python3 -c \"from X import Y\"` for every module the training script imports. Missing import chains have repeatedly failed runs *after* launch — verify first, fire second."),
        ("What's the H100 quota on RunPod (per the anima config), and the cost?",
         "Account limit is 2x H100 SXM 80GB. Roughly $2.99/hr per GPU. Use the official `runpod/pytorch:2.4.0-...` image."),
        ("Two crashes happened when I ran a 72B download alongside training — why?",
         "Shared NFS I/O. The download and the training job were both hammering the network filesystem, so both crashed. Always serialize: download fully, then train."),
        ("Write the canonical pod pre-flight checklist.",
         "1) `runpodctl pod list` — is a pod already up? reuse it.\n2) GPU free? `nvidia-smi`.\n3) Disk free? `df -h` (need room for ckpts).\n4) `HUGGING_FACE_HUB_TOKEN` exported + in ~/.cache/huggingface/token?\n5) deps import-verify: `python3 -c \"from X import Y\"` for each module, `PYTHONPATH` set.\n6) launch detached: `setsid nohup ... > log 2>&1 < /dev/null &`."),
        ("How do I detach a job on a RunPod pod when tmux isn't installed?",
         "Use setsid + nohup: `setsid nohup python3 train.py > ~/train.log 2>&1 < /dev/null & disown`. Then `tail -f ~/train.log` to follow it. The job survives the SSH session closing."),
        ("What's the rule about downloading model weights and training on RunPod?",
         "They must never overlap. A download during training silently kills the training process. Pipeline: (1) download all weights/data, (2) verify, (3) train. Never step 1 and step 3 concurrently."),
        ("How do I keep a RunPod credit alert from blocking an automated launch?",
         "If auto-charge is enabled, ignore balance alerts (set the credit-check to alert=false / `RUNPOD_AUTO_CHARGE=1`). To restore threshold behaviour, set `RUNPOD_AUTO_CHARGE=0` or `auto_charge_enabled=false`."),
        ("Summarize the top 5 RunPod stability rules.",
         "1) Never download while training (silent kill).\n2) Set HF_TOKEN on pod create (10x download speed).\n3) Chunk-tokenize corpora > 500 MB (RAM blowup).\n4) Full dep import-verify before launch.\n5) `runpodctl pod list` before creating — reuse, don't duplicate."),
        ("How do I follow a detached training run's progress on a pod?",
         "`tail -f ~/train.log` (or `tail -c 2000 ~/train.log | tr '\\r' '\\n' | tail` to see the latest progress-bar line). To check it's alive: `pgrep -f train.py`."),
        ("What happens if I save a checkpoint when the pod disk quota is full?",
         "`torch.save` fails silently — you get a partial/zero-byte file or `PytorchStreamWriter failed` with no clean error. Always free space (delete the oldest checkpoint) before saving a new one; keep <=2."),
        ("Why is `tokenizer(big_corpus)` dangerous on a pod?",
         "It materializes the whole tokenized corpus in RAM at once — a ~1.2 GB text corpus became ~119 GB RAM and 15+ min. Iterate in chunks (<=500 lines) and write tokenized shards incrementally instead."),
        ("How should an automated 'keep going to goal' instruction handle GPU launches on RunPod?",
         "With pre-authorized quota (e.g. up to 2x H100 SXM), auto-fire without a confirmation prompt — but still run the pre-flight checklist (pod-list, GPU free, disk free, token set, deps verified) before each launch."),
        ("What's the difference between a RunPod 'pod' and a 'serverless endpoint' for training?",
         "A pod is a persistent container with SSH — you provision it, run jobs, and pay per hour until you stop it (good for iterative training). Serverless scales to zero between requests (good for inference, not multi-hour training)."),
        ("Give the env vars to set at the top of a RunPod training session.",
         "export HUGGING_FACE_HUB_TOKEN=hf_...\nexport HF_HOME=/workspace/.cache/huggingface   # put cache on the big volume, not /\nexport TOKENIZERS_PARALLELISM=false\nexport PYTHONPATH=/workspace/repo:$PYTHONPATH"),
        ("How do I copy a trained adapter off a RunPod pod?",
         "`runpodctl send <file>` (gives a one-time code), or `scp -i ~/.runpod/ssh/<key> -P <port> root@<ip>:/workspace/out/adapter.safetensors .`, or push straight to HF Hub from the pod (`huggingface-cli upload`). Push-to-HF is usually cleanest — no local round trip."),
        ("What's a safe restart policy for a training watchdog?",
         "Check the script file exists; cap consecutive restarts at e.g. 3; back off between restarts; and log the exit code each time. A blind `while true; restart` loop with no counter burns hours producing empty logs."),
    ]
    # a few short-form drills on the absolute rules
    drills = [
        ("RunPod rule R13?", "Set HF_TOKEN immediately on pod create — unauthenticated downloads are ~10x slower (incident TS-017)."),
        ("RunPod rule R14?", "Chunk-tokenize any corpus > 500 MB — a single tokenizer() call on 1.2 GB hit 119 GB RAM (incident TS-018)."),
        ("RunPod rule R15?", "Full dependency import-verify (`python3 -c \"from X import Y\"` + PYTHONPATH) before launching a training job (incident TS-021)."),
        ("RunPod rule R16?", "Run `runpodctl pod list` before creating a pod — reuse an existing one; duplicates waste cost and GPU quota."),
        ("RunPod rule R01 / R04?", "R01: never download while training (silent kill, TS-004). R04: AdamW `foreach=False` + per-step dtype fix for bf16 (TS-002)."),
        ("RunPod rules R02 / R03 / R09?", "Disk-quota discipline: delete old checkpoints before saving; `torch.save` fails silently when full; keep <=2 checkpoints (TS-003, TS-006)."),
    ]
    return [fmt(p, c) for p, c in pairs] + [fmt(p, c) for p, c in drills]


def main() -> int:
    if not V9_BASE.exists():
        print(f"ERROR: v9 base not found at {V9_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V9_BASE.read_text().splitlines() if l.strip()]
    print(f"v9 base: {len(base)}")
    runpod = gen_runpod()
    print(f"  + runpod_ops {len(runpod)}")
    rows = base + runpod
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.2.0-r10",
        "base": str(V9_BASE),
        "base_rows": len(base),
        "runpod_added": len(runpod),
        "total_rows": len(rows),
        "seed": 42,
        "source": "owner request + ~/core/anima/config/runpod.json (schema 2.1, 12 absolute rules)",
        "purpose": "RunPod/cloud-GPU ops block; also re-scores whether r9's 46% hexa-eval was variance",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
