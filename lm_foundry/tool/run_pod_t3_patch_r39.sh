#!/bin/bash
# r39 — T3 quote-fragility patch — small T3-only SFT on top of v0.4.0-rl-t4-v3.
# 30 quoted-date pairs × 2 epochs, batch 1 grad_accum 8, LR 5e-5 (half normal —
# minimal-perturbation continue-train). Targets T3 quoted gold form recovery
# (58.8% v3 → ≥65% target) without disturbing other v3-family wins.
#
# Payload at /workspace/:
#   hexa_cc  manifest-mk1.jsonl  five-nl.jsonl  score_bf16.py
#   train_sft_lora.py  sft_t3_patch.jsonl  .env  (this script)
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

echo "=== [1] pip — pinned SFT stack (no vllm needed; SFTTrainer is vllm-free) ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
# Same pinned versions as r38 RL but vllm is dropped — SFTTrainer doesn't import it.
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "accelerate==1.6.0" \
    "datasets==3.5.0" "trl==0.17.0" "huggingface_hub" "sentencepiece" "tiktoken" 2>&1 | tail -8
python3 -c "import torch, transformers, trl, peft, accelerate, datasets; print('torch', torch.__version__, '| transformers', transformers.__version__, '| trl', trl.__version__, '| peft', peft.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
python3 -c "from trl import SFTTrainer, SFTConfig; print('SFTTrainer import OK')"

echo "=== [2] dataset sanity (T3 patch — 30 quoted-date pairs) ==="
echo "rows: $(wc -l < /workspace/sft_t3_patch.jsonl)"
echo "first 2 rows:"
head -2 /workspace/sft_t3_patch.jsonl

echo "=== [3] SFT continue from v3 adapter — LoRA r=64/α=128, 2 ep, LR 5e-5 ==="
ADAPTER_OUT=/workspace/adapter-v040-rl-t4-v3-t3patch
python3 train_sft_lora.py \
  --model "Qwen/Qwen2.5-Coder-7B" \
  --adapter-in "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3" \
  --dataset /workspace/sft_t3_patch.jsonl \
  --output "$ADAPTER_OUT" \
  --lora-r 64 --lora-alpha 128 \
  --epochs 2 --batch-size 1 --grad-accum 8 --lr 5e-5 \
  --max-seq-length 512 2>&1 | tee /workspace/train_t3patch.log | grep -vE "^\s*$" | tail -80
echo "--- training_summary.json ---"
cat "$ADAPTER_OUT/training_summary.json"

echo "=== [4] score Mk.I (r38-fixed manifest, bf16, greedy) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/manifest-mk1.jsonl --output /workspace/score-mk1-t3patch 2>&1 | tail -20
echo "--- scores_strict.json (Mk.I) ---"; cat /workspace/score-mk1-t3patch/scores_strict.json

echo "=== [5] score 5-NL (bf16, greedy) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/five-nl.jsonl --output /workspace/score-5nl-t3patch 2>&1 | tail -20
echo "--- scores_strict.json (5-NL) ---"; cat /workspace/score-5nl-t3patch/scores_strict.json

echo "=== [6] T3 per-task dump (verify quoted form recovered) ==="
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open("/workspace/score-mk1-t3patch/per_task_strict.jsonl") if l.strip()]
t3 = [r for r in rows if r["family"] == "T3"]
p = sum(1 for r in t3 if r["pass"])
print(f"T3 pass {p}/{len(t3)} = {p/len(t3)*100:.1f}%")
fails = [r for r in t3 if not r["pass"]]
quoted_in_fail = sum(1 for r in fails if 'until="' in r["completion"])
unquoted_in_fail = sum(1 for r in fails if 'until=' in r["completion"] and 'until="' not in r["completion"])
print(f"fails: {len(fails)} (quoted-emitted: {quoted_in_fail}, unquoted-emitted: {unquoted_in_fail}, other: {len(fails)-quoted_in_fail-unquoted_in_fail})")
for r in fails[:6]:
    print(f"  {r['task_id']} gold={r['gold_pattern']!r} :: {r['completion'][:130]!r}")
PY

echo "=== [7] HF push adapter + bench subdirs ==="
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
adapter_repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch"
api.create_repo(adapter_repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/adapter-v040-rl-t4-v3-t3patch", repo_id=adapter_repo,
                  repo_type="model", ignore_patterns=["checkpoint-*"])
print("uploaded adapter:", adapter_repo)
bench_repo = "dancinlab/hexa-forge-bench-cold-v0.1.3"
api.create_repo(bench_repo, repo_type="dataset", exist_ok=True)
api.upload_folder(folder_path="/workspace/score-mk1-t3patch", repo_id=bench_repo, repo_type="dataset",
                  path_in_repo="hexa-eval-mk1-7b-v040-rl-t4-v3-t3patch")
api.upload_folder(folder_path="/workspace/score-5nl-t3patch", repo_id=bench_repo, repo_type="dataset",
                  path_in_repo="five-nl-7b-v040-rl-t4-v3-t3patch")
print("uploaded bench:", bench_repo)
PY

echo "POD_R39_T3PATCH_DONE"
