#!/bin/bash
# r42 — v0.4.2 routing-RL. GRPO with binary route-correctness × schema-validity
# reward on 200 eval-held-out prompts. Continues from r39 v3-t3patch GA
# (NOT from r40/r41 — those drifted). Lever-4 mechanics: KL=0.01 LR=5e-6
# group=4 batch=4 4 epochs. Cost ~$2-3 / 3h on 40GB A100.
#
# Payload at /workspace/:
#   hexa_cc  manifest-mk1.jsonl  five-nl.jsonl  delegation-mk0.jsonl
#   score_bf16.py (FIXED for delegation markers)
#   score_delegation_mk0.py  build_routing_rl_prompts.py
#   train_rl_grpo_routing.py  .env  (this script)
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

echo "=== [1] pip — pinned TRL-0.17.0 stack with vllm (GRPO needs it) ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "accelerate==1.6.0" \
    "datasets==3.5.0" "trl==0.17.0" "vllm==0.7.3" "huggingface_hub" \
    "sentencepiece" "tiktoken" 2>&1 | tail -8
python3 -c "import torch, transformers, trl, peft, accelerate, datasets, vllm; print('torch', torch.__version__, '| transformers', transformers.__version__, '| trl', trl.__version__, '| vllm', vllm.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
python3 -c "from trl import GRPOTrainer, GRPOConfig; print('GRPOTrainer import OK')"

echo "=== [2] build 200 routing-RL training prompts (eval-held-out) ==="
python3 build_routing_rl_prompts.py --out /workspace/rl_routing_prompts.jsonl
echo "--- dist ---"; head -1 /workspace/rl_routing_prompts.jsonl

echo "=== [3] GRPO routing-RL from r39 v3-t3patch; KL=0.01 LR=5e-6 group=4 batch=4 4ep ==="
ADAPTER_OUT=/workspace/adapter-v042-route-rl
python3 train_rl_grpo_routing.py \
  --base "Qwen/Qwen2.5-Coder-7B" \
  --adapter "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3-t3patch" \
  --prompts /workspace/rl_routing_prompts.jsonl \
  --output "$ADAPTER_OUT" \
  --epochs 4 --lr 5e-6 --kl-coef 0.01 --group-size 4 --batch-size 4 \
  --max-new-tokens 200 --temperature 0.7 --logging-steps 50 2>&1 | tee /workspace/train_v042.log | grep -vE "^\s*$" | tail -120
echo "--- rl_summary.json ---"; cat "$ADAPTER_OUT/rl_summary.json"

echo "=== [4] score Mk.I (with v0.4.x scorer fix — delegation token strip) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/manifest-mk1.jsonl --output /workspace/score-mk1-v042 2>&1 | tail -20
echo "--- scores_strict.json (Mk.I) ---"; cat /workspace/score-mk1-v042/scores_strict.json

echo "=== [5] score 5-NL ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/five-nl.jsonl --output /workspace/score-5nl-v042 2>&1 | tail -20
echo "--- scores_strict.json (5-NL) ---"; cat /workspace/score-5nl-v042/scores_strict.json

echo "=== [6] score DLG-mk0 routing (the v0.4.x metric) ==="
python3 score_delegation_mk0.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/delegation-mk0.jsonl --output /workspace/score-dlg-v042 2>&1 | tail -30
echo "--- scores_routing.json (DLG-mk0) ---"; cat /workspace/score-dlg-v042/scores_routing.json

echo "=== [7] Acceptance gate check (spec-delegation §11) ==="
python3 - <<'PY'
import json
mk1 = json.load(open("/workspace/score-mk1-v042/scores_strict.json"))
nl  = json.load(open("/workspace/score-5nl-v042/scores_strict.json"))
dlg = json.load(open("/workspace/score-dlg-v042/scores_routing.json"))
t4 = float(mk1["per_family"]["T4"].split("=")[-1].strip().rstrip("%"))
gates = {
    "Mk.I ≥ 88% strict":         mk1["pass_at_1"] >= 0.88,
    "5-NL ≥ 95%":                nl["pass_at_1"] >= 0.95,
    "DLG-mk0 route ≥ 0.90":      dlg["s_route"] >= 0.90,
    "DLG-mk0 schema ≥ 0.98":     dlg["s_schema"] >= 0.98,
    "DLG-mk0 overall ≥ 0.85":    dlg["overall"] >= 0.85,
    "T4 ≥ 95%":                  t4 >= 95.0,
}
print("--- acceptance gates ---")
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
adapter_repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.2-route-rl"
api.create_repo(adapter_repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/adapter-v042-route-rl", repo_id=adapter_repo,
                  repo_type="model", ignore_patterns=["checkpoint-*"])
print("uploaded adapter:", adapter_repo)
bench_repo = "dancinlab/hexa-forge-bench-cold-v0.1.3"
api.create_repo(bench_repo, repo_type="dataset", exist_ok=True)
for subdir, path_in_repo in [
    ("/workspace/score-mk1-v042", "hexa-eval-mk1-7b-v042-route-rl"),
    ("/workspace/score-5nl-v042", "five-nl-7b-v042-route-rl"),
    ("/workspace/score-dlg-v042", "delegation-mk0-7b-v042-route-rl"),
]:
    api.upload_folder(folder_path=subdir, repo_id=bench_repo, repo_type="dataset",
                      path_in_repo=path_in_repo)
    print("uploaded bench:", path_in_repo)
PY

echo "POD_R42_V042_ROUTE_RL_DONE"
