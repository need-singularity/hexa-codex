#!/bin/bash
# v0.4.0-rl-t4-v3 — round 38: Lever 4 v3 — compile-feedback RL to close T4's
# residual generic fails. Continues RL from the v2 adapter (89.47% Mk.I).
# Runs ON the pod. payload + .env scp'd to /workspace/.
#
# payload expected at /workspace/:
#   hexa_cc  manifest-mk1.jsonl (r38-fixed)  five-nl.jsonl  score_bf16.py
#   train_rl_grpo_t4.py  build_rl_t4_prompts.py  .env  (this script)
set -e
set -o pipefail   # so a failing python in a `… | tee | tail` pipeline aborts the script
cd /workspace
[ -f /workspace/.env ] && source /workspace/.env
export HF_HOME=/workspace/.hf
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_PROGRESS_BARS=1
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1
HF_TOKEN="${HUGGING_FACE_HUB_TOKEN:?HUGGING_FACE_HUB_TOKEN must be set}"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
chmod +x /workspace/hexa_cc

echo "=== [1] pip — pinned TRL-0.17.0 stack (vllm required for GRPOTrainer import) ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
# torch 2.5.1+cu121 already in the image; vllm 0.7.3 pins torch==2.5.1 (satisfied).
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "accelerate==1.6.0" "datasets==3.5.0" \
    "trl==0.17.0" "vllm==0.7.3" "huggingface_hub" "sentencepiece" "tiktoken" 2>&1 | tail -10
python3 -c "import torch, transformers, trl, peft, accelerate, datasets, vllm; print('torch', torch.__version__, '| transformers', transformers.__version__, '| trl', trl.__version__, '| peft', peft.__version__, '| accelerate', accelerate.__version__, '| vllm', vllm.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
python3 -c "from trl import GRPOTrainer, GRPOConfig; print('GRPOTrainer import OK')"

echo "=== [2] hexa_cc canon probe — which enum forms compile? ==="
python3 - <<'PY'
import subprocess, tempfile
from pathlib import Path
HEXA_CC = "/workspace/hexa_cc"
ERR_PATS = ("Parse error","parse error","CODEGEN ERROR","Resolve error","Type error",
            "Lint S","unhandled binop","unhandled operator","unexpected token")
def verdict(src):
    with tempfile.TemporaryDirectory() as td:
        ip = Path(td)/"in.hexa"; op = Path(td)/"out.c"; ip.write_text(src + "\n")
        try:
            r = subprocess.run([HEXA_CC, str(ip), str(op)], capture_output=True, text=True, timeout=10)
        except Exception as e:
            return f"EXC {e}"
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        if r.returncode != 0:
            return f"FAIL(rc={r.returncode}) {out.replace(chr(10),' | ').strip()[:120]}"
        for p in ERR_PATS:
            if p in out:
                return f"FAIL(errpat={p!r}) {out.replace(chr(10),' | ').strip()[:120]}"
        return "OK"
probes = [
    "enum Option<T> { None, Some(T) }",
    "enum Option { None, Some(T) }",
    "enum Validated<T> { Valid(T), Invalid(StringList) }",
    "enum Validated { Valid(T), Invalid(StringList) }",
    "enum Tree<T> { Leaf(T), Node(Tree, Tree) }",
    "enum Tree { Leaf(T), Node(Tree, Tree) }",
    "enum Items { Of(Vec<String>), Empty }",
    "enum Items { Of(Strings), Empty }",
    "enum Container { Holds(Box<i32>), Nil }",
    "enum Container { Holds(i32), Nil }",
    "enum Triple { Three(A, B, C) }",
    "enum Pair { Two(A, B) }",
]
print("=== CANON PROBE BEGIN ===")
for s in probes:
    print(f"  {verdict(s):60s}  <-  {s}")
print("=== CANON PROBE END ===")
PY

echo "=== [3] build v3 RL prompt dataset (30 specs, 80% generic-bait) ==="
python3 build_rl_t4_prompts.py --out /workspace/rl_t4_prompts_v3.jsonl

echo "=== [4] GRPO compile-feedback RL — from v2 adapter; KL=0.01 LR=5e-6 5ep group=4 batch=4 ==="
ADAPTER_OUT=/workspace/adapter-v040-rl-t4-v3
python3 train_rl_grpo_t4.py \
  --base "Qwen/Qwen2.5-Coder-7B" \
  --adapter "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v2" \
  --prompts /workspace/rl_t4_prompts_v3.jsonl \
  --hexa-cc /workspace/hexa_cc \
  --output "$ADAPTER_OUT" \
  --epochs 5 --lr 5e-6 --kl-coef 0.01 --group-size 4 --batch-size 4 \
  --max-new-tokens 120 --temperature 0.7 --logging-steps 50 2>&1 | tee /workspace/train_v3.log | grep -vE "^\s*$" | tail -120
echo "--- rl_summary.json ---"; cat "$ADAPTER_OUT/rl_summary.json"

echo "=== [5] score Mk.I (r38-fixed manifest, bf16, greedy) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/manifest-mk1.jsonl --output /workspace/score-mk1-v3 2>&1 | tail -20
echo "--- scores_strict.json (Mk.I) ---"; cat /workspace/score-mk1-v3/scores_strict.json

echo "=== [6] score 5-NL (bf16, greedy) ==="
python3 score_bf16.py --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER_OUT" \
  --manifest /workspace/five-nl.jsonl --output /workspace/score-5nl-v3 2>&1 | tail -20
echo "--- scores_strict.json (5-NL) ---"; cat /workspace/score-5nl-v3/scores_strict.json

echo "=== [7] T4 per-task fail dump (for the landing writeup) ==="
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open("/workspace/score-mk1-v3/per_task_strict.jsonl") if l.strip()]
t4 = [r for r in rows if r["family"] == "T4"]
fails = [r for r in t4 if not r["pass"]]
print(f"T4 pass {sum(1 for r in t4 if r['pass'])}/{len(t4)} | fails={len(fails)}")
for r in fails:
    print(f"  {r['task_id']} gold={r['gold_pattern']!r} :: {r['completion'][:160]!r}")
PY

echo "=== [8] HF push adapter + bench subdirs ==="
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
adapter_repo = "dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.0-rl-t4-v3"
api.create_repo(adapter_repo, repo_type="model", exist_ok=True)
api.upload_folder(folder_path="/workspace/adapter-v040-rl-t4-v3", repo_id=adapter_repo,
                  repo_type="model", ignore_patterns=["checkpoint-*"])
print("uploaded adapter:", adapter_repo)
bench_repo = "dancinlab/hexa-forge-bench-cold-v0.1.3"
api.create_repo(bench_repo, repo_type="dataset", exist_ok=True)
api.upload_folder(folder_path="/workspace/score-mk1-v3", repo_id=bench_repo, repo_type="dataset",
                  path_in_repo="hexa-eval-mk1-7b-v040-rl-t4-v3")
api.upload_folder(folder_path="/workspace/score-5nl-v3", repo_id=bench_repo, repo_type="dataset",
                  path_in_repo="five-nl-7b-v040-rl-t4-v3")
print("uploaded bench:", bench_repo)
PY

echo "POD_V040RLT4V3_DONE"
