#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# runpod_launch_7b_sft.sh — fire a RunPod H100 SXM pod and run the v0.3.0 7B SFT.
#
# This is Lever 1 (+ Lever 3) of `papers/plan-v0.3.0-structural.md`: the 3B base
# has plateaued hexa-eval Mk.I at ~63-65%; a 7B base (Qwen2.5-Coder-7B) with the
# same recipe — and a higher LoRA rank or full-FT — should lift the floor toward
# the gate-③ 80% bar. 7B LoRA training needs >12 GB VRAM, so it runs on a rented
# H100 (the local RTX 5070 can't).
#
# COST: ~$3/hr per H100 SXM 80GB. One SFT run ≈ 1.5-2.5 h ≈ $4-8. Auto-charge is
# enabled (~/core/anima/config/runpod_auto_charge.json) but this script does NOT
# self-fire — it requires you to run it (or pass --yes). A paid cloud pod is the
# one step in the v0.3.0 plan that wants an explicit go-ahead.
#
# PREREQS (the operator's machine):
#   - runpodctl installed + logged in (`runpodctl config --apiKey ...`)
#   - ~/.runpod/ssh/<key> present (the key referenced in anima/config/runpod.json)
#   - HF token retrievable: `ssh mac /Users/ghost/core/secret/bin/secret get HF_TOKEN`
#   - the hexa-forge repo reachable (this script's repo)
#
# WHAT IT DOES (encodes LEARNING_PROGRAMMING.md §6 RunPod rules):
#   1. `runpodctl pod list`  — reuse an existing pod; don't duplicate (R16)
#   2. create pod: image runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04,
#      1x H100 SXM 80GB  (SSH ready ~30 s; R-image rule)
#   3. on the pod: set HF_TOKEN immediately (R13), pip install peft trl, sync repo
#      + the v11 SFT dataset (or rebuild it), full dep import-verify (R15)
#   4. train: tool/train_sft_lora.py --model Qwen/Qwen2.5-Coder-7B --lora-r 64
#      --epochs 3  (sequential — no concurrent downloads, R01)
#   5. score on eval/hexa-eval/manifest-mk1.jsonl + eval/five-nl-eval/manifest.jsonl
#   6. push adapter + (optionally) GGUF f16/Q5_K_M to dancinlab/hexa-forge-code-7b-*
#   7. STOP the pod (so it stops billing) — unless --keep-pod
#
# This file is the SPEC + scaffold. The pod-side steps are emitted as a heredoc
# the operator can review before firing. Fill in the TODOs (api key path, pod id
# format) on first real run, then it's reusable.

set -euo pipefail

YES=0
LORA_R=64
EPOCHS=3
FULL_FT=0
KEEP_POD=0
for a in "$@"; do case "$a" in
  --yes) YES=1 ;;
  --full-ft) FULL_FT=1 ;;
  --keep-pod) KEEP_POD=1 ;;
  --lora-r=*) LORA_R="${a#*=}" ;;
  --epochs=*) EPOCHS="${a#*=}" ;;
  *) echo "unknown arg: $a"; exit 2 ;;
esac; done

IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
GPU="NVIDIA H100 SXM 80GB"
HF_TOKEN_CMD='ssh mac /Users/ghost/core/secret/bin/secret get HF_TOKEN'

echo "=== runpod_launch_7b_sft.sh — v0.3.0 Lever 1 (+3) ==="
echo "  base model : Qwen/Qwen2.5-Coder-7B"
if [ "$FULL_FT" = 1 ]; then echo "  mode       : FULL fine-tune"; else echo "  mode       : LoRA r=$LORA_R"; fi
echo "  epochs     : $EPOCHS"
echo "  image      : $IMAGE"
echo "  gpu        : $GPU  (~\$3/hr; one run ≈ \$4-8)"
echo

# ---- R16: check for an existing pod first ----------------------------------
echo "[1/7] runpodctl pod list (R16 — reuse, don't duplicate):"
if command -v runpodctl >/dev/null 2>&1; then
  runpodctl pod list || true
else
  echo "  (runpodctl not installed — install + 'runpodctl config --apiKey ...' first)"
fi
echo

if [ "$YES" != 1 ]; then
  cat <<'EOF'
This script will create a paid H100 pod (~$3/hr) and run a 7B SFT.
It is intentionally NOT self-firing. To proceed, re-run with --yes:

    bash tool/runpod_launch_7b_sft.sh --yes [--lora-r=64 | --full-ft] [--epochs=3] [--keep-pod]

Below is the pod-side script that will run (review it):
EOF
fi

# ---- the pod-side script (emitted; runs after pod creation) ----------------
cat <<'PODSCRIPT'
# ===== runs ON the RunPod pod =====
set -euo pipefail
# R13: HF token first
export HF_TOKEN="$(cat /workspace/.hf_token)"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
mkdir -p ~/.cache/huggingface && echo "$HF_TOKEN" > ~/.cache/huggingface/token
export HF_HOME=/workspace/.cache/huggingface
export TOKENIZERS_PARALLELISM=false

# deps
pip install -q peft trl pyarrow zstandard sentencepiece
# repo + dataset (synced into /workspace/hexa-forge and /workspace/sft-train-v11)
cd /workspace/hexa-forge

# R15: full dep import-verify before launch
python3 - <<'PY'
import importlib
for m in ("torch","transformers","peft","trl","datasets","pyarrow","huggingface_hub"):
    importlib.import_module(m); print("ok", m)
import torch; print("cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
PY

# R01: sequential — base model download happens INSIDE train_sft_lora.py's
# from_pretrained, with NOTHING else running. (Don't kick off other downloads.)

# train (the v11 dataset = best of the 3B line; --lora-r / --full-ft via env)
LORA_R="${LORA_R:-64}" python3 tool/train_sft_lora.py \
    --model Qwen/Qwen2.5-Coder-7B \
    --output /workspace/runs/sft-7b-v0.3.0 \
    --dataset /workspace/sft-train-v11/train.jsonl \
    --epochs "${EPOCHS:-3}" --lr 1e-4

# score on the stable Mk.I set + 5-NL
python3 /workspace/score_strict.py --base Qwen/Qwen2.5-Coder-7B \
    --adapter /workspace/runs/sft-7b-v0.3.0 \
    --manifest /workspace/hexa-forge/eval/hexa-eval/manifest-mk1.jsonl \
    --output /workspace/runs/hexa-eval-mk1-7b
python3 /workspace/score_strict.py --base Qwen/Qwen2.5-Coder-7B \
    --adapter /workspace/runs/sft-7b-v0.3.0 \
    --manifest /workspace/hexa-forge/eval/five-nl-eval/manifest.jsonl \
    --output /workspace/runs/five-nl-7b

# push to HF
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r%s-v0.3.0" % os.environ.get("LORA_R","64")
api.create_repo(repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/runs/sft-7b-v0.3.0", repo_id=repo, repo_type="model",
                  ignore_patterns=["checkpoint-*"])
print("pushed", repo)
PY
echo POD_SFT_DONE
# ===== end pod-side =====
PODSCRIPT

if [ "$YES" != 1 ]; then
  echo
  echo "(not firing — re-run with --yes)"
  exit 0
fi

# ---- ACTUAL launch (only with --yes) ---------------------------------------
echo "[2/7] creating pod ($GPU, $IMAGE) ..."
# TODO on first real run: confirm the runpodctl create flags + how to capture POD_ID.
#   POD_ID=$(runpodctl create pod --name hexa-forge-7b-sft --imageName "$IMAGE" \
#       --gpuType "$GPU" --gpuCount 1 --volumeSize 100 --ports "22/tcp" | grep -oE 'pod "[^"]+"' | ...)
echo "  TODO: wire 'runpodctl create pod ...' here; then scp the heredoc above + repo + dataset + score_strict.py,"
echo "        run it, fetch results, and (unless --keep-pod) 'runpodctl stop pod \$POD_ID'."
echo "  Until then, do the create+ssh steps manually using the pod-side script printed above."
exit 0
