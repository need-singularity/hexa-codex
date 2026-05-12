#!/bin/bash
# r40 — v0.4.0 self-aware delegation SFT.
# Continues SFT from v0.4.0-rl-t4-v3-t3patch with the v18 dataset (840 new
# delegation-aware pairs on top of v11 base). Per spec §11: 1 epoch × LR 5e-5
# × batch 1 grad_accum 8, max-seq 1024. Score Mk.I + 5-NL + DLG-mk0 in the
# same pod session and push as v0.4.0-delegate.
#
# Payload at /workspace/:
#   hexa_cc  manifest-mk1.jsonl  five-nl.jsonl  delegation-mk0.jsonl
#   score_bf16.py  score_delegation_mk0.py
#   train_sft_lora.py  build_sft_dataset_v18.py  sft-train-v11.jsonl
#   .env  (this script)
set -e
set -o pipefail
cd /workspace
[ -f /workspace/.env ] && source /workspace/.env
export HF_HOME=/workspace/.hf
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_PROGRESS_BARS=1
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1
HF_TOKEN="${HUGGING_FACE_HUB_TOKEN:?HUGGING_FACE_HUB_TOKEN must be set}"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
chmod +x /workspace/hexa_cc

echo "=== [1] pip — pinned SFT stack (no vllm needed) ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "accelerate==1.6.0" \
    "datasets==3.5.0" "trl==0.17.0" "huggingface_hub" "sentencepiece" "tiktoken" 2>&1 | tail -8
python3 -c "import torch, transformers, trl, peft, accelerate, datasets; print('torch', torch.__version__, '| transformers', transformers.__version__, '| trl', trl.__version__, '| peft', peft.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
python3 -c "from trl import SFTTrainer, SFTConfig; print('SFTTrainer import OK')"

echo "=== [2] build v18 dataset (v11 base + 840 delegation pairs) ==="
python3 build_sft_dataset_v18.py --in /workspace/sft-train-v11.jsonl --out-dir /workspace/v18
echo "--- v18 MANIFEST ---"; cat /workspace/v18/MANIFEST.json
DATASET=/workspace/v18/sft-train-v18.jsonl

echo "=== [3] SFT continue from v3-t3patch — LoRA r=64/α=128, 1 ep, LR 5e-5, max-seq 1024 ==="
ADAPTER_OUT=/workspace/adapter-v040-delegate
python3 train_sft_lora.py \
  --model "Qwen/Qwen2.5-Coder-7B" \
  --adapter-in "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch" \
  --dataset "$DATASET" \
  --output "$ADAPTER_OUT" \
  --lora-r 64 --lora-alpha 128 \
  --epochs 1 --batch-size 1 --grad-accum 8 --lr 5e-5 \
  --max-seq-length 1024 2>&1 | tee /workspace/train_v040.log | grep -vE "^\s*$" | tail -120
echo "--- training_summary.json ---"
cat "$ADAPTER_OUT/training_summary.json"

echo "=== [4] score Mk.I (665 tasks, r38-fixed manifest) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/manifest-mk1.jsonl --output /workspace/score-mk1-v040 2>&1 | tail -20
echo "--- scores_strict.json (Mk.I) ---"; cat /workspace/score-mk1-v040/scores_strict.json

echo "=== [5] score 5-NL ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/five-nl.jsonl --output /workspace/score-5nl-v040 2>&1 | tail -20
echo "--- scores_strict.json (5-NL) ---"; cat /workspace/score-5nl-v040/scores_strict.json

echo "=== [6] score DLG-mk0 (200-task routing eval — NEW) ==="
python3 score_delegation_mk0.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/delegation-mk0.jsonl --output /workspace/score-dlg-v040 2>&1 | tail -25
echo "--- scores_routing.json (DLG-mk0) ---"; cat /workspace/score-dlg-v040/scores_routing.json

echo "=== [7] HF push adapter + bench subdirs ==="
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
adapter_repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-delegate"
api.create_repo(adapter_repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/adapter-v040-delegate", repo_id=adapter_repo,
                  repo_type="model", ignore_patterns=["checkpoint-*"])
print("uploaded adapter:", adapter_repo)
bench_repo = "dancinlab/hexa-forge-bench-cold-v0.1.3"
api.create_repo(bench_repo, repo_type="dataset", exist_ok=True)
for subdir, path_in_repo in [
    ("/workspace/score-mk1-v040", "hexa-eval-mk1-7b-v040-delegate"),
    ("/workspace/score-5nl-v040", "five-nl-7b-v040-delegate"),
    ("/workspace/score-dlg-v040", "delegation-mk0-7b-v040-delegate"),
]:
    api.upload_folder(folder_path=subdir, repo_id=bench_repo, repo_type="dataset",
                      path_in_repo=path_in_repo)
    print("uploaded bench:", path_in_repo)
PY

echo "POD_R40_V040_DELEGATE_DONE"
