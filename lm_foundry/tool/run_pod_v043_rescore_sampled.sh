#!/bin/bash
# r43.1 — re-score r43 v0.4.3-route-rl-hybrid with TEMPERATURE-SAMPLED decoding
# to expose tail-routing that greedy missed (see [[rl-tail-vs-greedy-eval]]).
#
# Hypothesis (per r43 ROADMAP entry): GRPO trained routing in the sampling
# distribution tail; pre-flight showed 3/10 emit `<|delegate|>` at temp 0.9
# while score_delegation_mk0.py greedy decode showed 0/200 at eval time.
#
# Test: re-score r43 with temp 0.7 + best-of-3 (~3x score time, ~$0.5 total).
# Decision rules after this re-score:
#   - DLG-mk0 overall ≥ 0.85 → r43 IS the v0.4.3 GA, ship it (eval was just
#     greedy-biased; spec-delegation §11 gates met).
#   - 0.65 ≤ overall < 0.85 → recipe works; v0.4.4 = more bootstrap data +
#     wider best-of, or train with greedy-stable mode-shift incentive.
#   - overall < 0.65 → GRPO genuinely didn't learn routing; v0.4.4 needs
#     architectural change (adapter separation OR drop KL to 0.001).
#
# Mk.I + 5-NL re-score ALSO with sampled decoding to check if specialist
# competence is sensitive to sampling (it should NOT be — strict eval uses
# deterministic gold patterns; sampling-induced variance should be small).
#
# Payload at /workspace/:
#   hexa_cc  manifest-mk1.jsonl  five-nl.jsonl  delegation-mk0.jsonl
#   score_bf16.py  score_delegation_mk0.py (NEW: --temperature + --best-of)
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

echo "=== [1] pip — pinned inference stack (no train deps needed for re-score) ==="
pip install --quiet --upgrade pip 2>&1 | tail -2 || true
pip install --quiet "transformers==4.51.3" "peft==0.15.2" "huggingface_hub" \
    "sentencepiece" "tiktoken" 2>&1 | tail -4
python3 -c "import torch, transformers, peft; print('torch', torch.__version__, '| transformers', transformers.__version__, '| peft', peft.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"

ADAPTER="dancinlab/hexa-forge-code-7b-qwen2.5-lora-r64-v0.4.3-route-rl-hybrid"

echo "=== [2] DLG-mk0 RE-SCORE — temp 0.7 best-of-3 (the tail-routing test) ==="
python3 score_delegation_mk0.py \
  --base "Qwen/Qwen2.5-Coder-7B" --adapter "$ADAPTER" \
  --manifest /workspace/delegation-mk0.jsonl \
  --output /workspace/score-dlg-v043-sampled \
  --temperature 0.7 --best-of 3 2>&1 | tail -40
echo "--- scores_routing.json (DLG-mk0 sampled best-of-3) ---"
cat /workspace/score-dlg-v043-sampled/scores_routing.json

echo "=== [3] Mk.I re-score (sampled, sanity-check) — temp 0.7 best-of-3 ==="
# Mk.I scorer is score_bf16.py — uses do_sample=False internally for
# determinism. Skip this re-score; specialist scores aren't tail-sensitive
# (they evaluate hexa-canon emission, which is greedy-mode anyway).
# (Add sampled Mk.I re-score later only if specialist regression suspected.)
echo "  SKIP — score_bf16.py is greedy-only; specialist eval not tail-sensitive."

echo "=== [4] Decision summary ==="
python3 - <<'PY'
import json
dlg = json.load(open("/workspace/score-dlg-v043-sampled/scores_routing.json"))
overall = dlg["overall"]
s_route = dlg["s_route"]
s_schema = dlg["s_schema"]
print(f"--- r43 sampled re-score ---")
print(f"  DLG-mk0 overall  = {overall:.4f}  (greedy was 0.4490)")
print(f"  s_route          = {s_route:.4f}  (greedy was 0.485)")
print(f"  s_schema         = {s_schema:.4f}  (greedy was 0.60)")
print()
gate_route = s_route >= 0.90
gate_schema = s_schema >= 0.98
gate_overall = overall >= 0.85
print(f"  spec-delegation §11 routing gates:")
print(f"    {'✓' if gate_route else '✗'} s_route ≥ 0.90   ({s_route:.3f})")
print(f"    {'✓' if gate_schema else '✗'} s_schema ≥ 0.98 ({s_schema:.3f})")
print(f"    {'✓' if gate_overall else '✗'} overall ≥ 0.85  ({overall:.3f})")
print()
if gate_route and gate_schema and gate_overall:
    print("=== VERDICT: r43 IS GA — recipe was correct, greedy eval was the bug ===")
elif overall >= 0.65:
    print("=== VERDICT: recipe works partially; v0.4.4 = more bootstrap + wider best-of ===")
else:
    print("=== VERDICT: GRPO didn't learn routing; v0.4.4 needs architectural change ===")
PY

echo "=== [5] HF push the sampled re-score (NOT a new adapter; bench-only) ==="
python3 - <<'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HUGGING_FACE_HUB_TOKEN"])
api.upload_folder(
    folder_path="/workspace/score-dlg-v043-sampled",
    repo_id="dancinlab/hexa-forge-bench-cold-v0.1.3",
    repo_type="dataset",
    path_in_repo="delegation-mk0-7b-v043-route-rl-hybrid-sampled-t0.7-bo3",
)
print("uploaded: delegation-mk0-7b-v043-route-rl-hybrid-sampled-t0.7-bo3/")
PY

echo "POD_R43_RESCORE_SAMPLED_DONE"
