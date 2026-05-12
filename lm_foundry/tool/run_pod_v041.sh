#!/bin/bash
# r41 — v0.4.1 rebalanced delegation SFT.
# Continues from r39 v3-t3patch (NOT r40 — r40 drifted from RL gains).
# v19 dataset (6052 rows; delegation 9.1%) + gentler params per
# [[lever4-rl-sft-conflict]] safe recipe: LR 2e-5 (half r40), 2 epochs,
# batch 1 grad_accum 8, max-seq 1024.
#
# Payload at /workspace/:
#   hexa_cc  manifest-mk1.jsonl  five-nl.jsonl  delegation-mk0.jsonl
#   score_bf16.py  score_delegation_mk0.py
#   train_sft_lora.py  build_sft_dataset_v18.py  build_sft_dataset_v19.py
#   sft-train-v11.jsonl  .env  (this script)
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

echo "=== [1] pip — pinned SFT stack ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "accelerate==1.6.0" \
    "datasets==3.5.0" "trl==0.17.0" "huggingface_hub" "sentencepiece" "tiktoken" 2>&1 | tail -8
python3 -c "import torch, transformers, trl, peft, accelerate, datasets; print('torch', torch.__version__, '| transformers', transformers.__version__, '| trl', trl.__version__, '| peft', peft.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
python3 -c "from trl import SFTTrainer, SFTConfig; print('SFTTrainer import OK')"

echo "=== [2] build v19 dataset (v11×2 dilution + v18 blocks + I+J+K+B-extension) ==="
python3 build_sft_dataset_v19.py --in /workspace/sft-train-v11.jsonl --out-dir /workspace/v19
echo "--- v19 MANIFEST ---"; cat /workspace/v19/MANIFEST.json
DATASET=/workspace/v19/sft-train-v19.jsonl

echo "=== [3] SFT continue from r39 v3-t3patch — LoRA r=64/α=128, 2 ep, LR 2e-5 (half r40), max-seq 1024 ==="
ADAPTER_OUT=/workspace/adapter-v041-delegate
python3 train_sft_lora.py \
  --model "Qwen/Qwen2.5-Coder-7B" \
  --adapter-in "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch" \
  --dataset "$DATASET" \
  --output "$ADAPTER_OUT" \
  --lora-r 64 --lora-alpha 128 \
  --epochs 2 --batch-size 1 --grad-accum 8 --lr 2e-5 \
  --max-seq-length 1024 2>&1 | tee /workspace/train_v041.log | grep -vE "^\s*$" | tail -120
echo "--- training_summary.json ---"
cat "$ADAPTER_OUT/training_summary.json"

echo "=== [4] score Mk.I (665) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/manifest-mk1.jsonl --output /workspace/score-mk1-v041 2>&1 | tail -20
echo "--- scores_strict.json (Mk.I) ---"; cat /workspace/score-mk1-v041/scores_strict.json

echo "=== [5] score 5-NL ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/five-nl.jsonl --output /workspace/score-5nl-v041 2>&1 | tail -20
echo "--- scores_strict.json (5-NL) ---"; cat /workspace/score-5nl-v041/scores_strict.json

echo "=== [6] score DLG-mk0 (200-task routing eval) ==="
python3 score_delegation_mk0.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/delegation-mk0.jsonl --output /workspace/score-dlg-v041 2>&1 | tail -30
echo "--- scores_routing.json (DLG-mk0) ---"; cat /workspace/score-dlg-v041/scores_routing.json

echo "=== [7] Acceptance gate check vs spec-delegation §11 ==="
python3 - <<'PY'
import json
mk1 = json.load(open("/workspace/score-mk1-v041/scores_strict.json"))
nl  = json.load(open("/workspace/score-5nl-v041/scores_strict.json"))
dlg = json.load(open("/workspace/score-dlg-v041/scores_routing.json"))
t4 = float(mk1["per_family"]["T4"].split("=")[-1].strip().rstrip("%"))
gates = {
    "Mk.I ≥ 88% strict":         mk1["pass_at_1"] >= 0.88,
    "5-NL ≥ 95%":                nl["pass_at_1"] >= 0.95,
    "DLG-mk0 route ≥ 0.90":      dlg["s_route"] >= 0.90,
    "DLG-mk0 schema ≥ 0.98":     dlg["s_schema"] >= 0.98,
    "DLG-mk0 overall ≥ 0.85":    dlg["overall"] >= 0.85,
    "T4 ≥ 95%":                  t4 >= 95.0,
}
print("--- acceptance gates (spec-delegation §11) ---")
all_pass = True
for name, ok in gates.items():
    flag = "✓" if ok else "✗"
    print(f"  {flag} {name}")
    if not ok: all_pass = False
print(f"--- VERDICT: {'GA' if all_pass else 'NOT GA — labeled experiment'} ---")
print(f"Mk.I={mk1['pass_at_1']:.4f}  5-NL={nl['pass_at_1']:.4f}  DLG.overall={dlg['overall']:.4f}  T4={t4:.1f}%")
PY

echo "=== [8] HF push ==="
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
adapter_repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.1-delegate"
api.create_repo(adapter_repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/adapter-v041-delegate", repo_id=adapter_repo,
                  repo_type="model", ignore_patterns=["checkpoint-*"])
print("uploaded adapter:", adapter_repo)
bench_repo = "dancinlab/hexa-forge-bench-cold-v0.1.3"
api.create_repo(bench_repo, repo_type="dataset", exist_ok=True)
for subdir, path_in_repo in [
    ("/workspace/score-mk1-v041", "hexa-eval-mk1-7b-v041-delegate"),
    ("/workspace/score-5nl-v041", "five-nl-7b-v041-delegate"),
    ("/workspace/score-dlg-v041", "delegation-mk0-7b-v041-delegate"),
]:
    api.upload_folder(folder_path=subdir, repo_id=bench_repo, repo_type="dataset",
                      path_in_repo=path_in_repo)
    print("uploaded bench:", path_in_repo)
PY

echo "POD_R41_V041_DELEGATE_DONE"
