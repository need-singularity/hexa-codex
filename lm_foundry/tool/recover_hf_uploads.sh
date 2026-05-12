#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 OR MIT
# recover_hf_uploads.sh — replay all pending dancinlab/* uploads after HF
# token refresh. Mid-session (2026-05-12 ~01:00 KST) the Mac-side
# `secret get HF_TOKEN` started returning an HF-marked-expired token,
# blocking 6 pending uploads. Run this once the operator has refreshed
# the token via:
#
#   # On Mac:
#   # 1. Open https://huggingface.co/settings/tokens
#   # 2. Create new Fine-grained token: Write to dancinlab/* (model+dataset+create)
#   # 3. secret set HF_TOKEN  (paste new token at the value: prompt)
#
# Then on Linux side:
#   bash tool/recover_hf_uploads.sh
#
# This script is idempotent — uploads that have already completed (e.g.
# r7 adapter) will be skipped or no-op'd.

set -euo pipefail

HF_TOKEN_VALUE="$(ssh mac '/Users/ghost/core/secret/bin/secret get HF_TOKEN' 2>/dev/null)"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN_VALUE"

# verify token
WHOAMI=$(curl -s -H "Authorization: Bearer $HF_TOKEN_VALUE" https://huggingface.co/api/whoami-v2)
if echo "$WHOAMI" | grep -q expired; then
    echo "ERROR: HF token still expired. Refresh on Mac side first."
    exit 1
fi
echo "whoami: $(echo "$WHOAMI" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name"))')"

# r6 / r7 GGUF F16 + Q5 source dirs (assemble per upload)
mkdir -p /tmp/r6_f16 /tmp/r6_q5 /tmp/r7_f16 /tmp/r7_q5

# r6: files may have been moved during earlier session — relink if available
[ -f /home/summer/runs/hexa-forge-code-3b-v0.2.0-r6.f16.gguf ] && \
    mv /home/summer/runs/hexa-forge-code-3b-v0.2.0-r6.f16.gguf /tmp/r6_f16/ 2>/dev/null || true
[ -f /home/summer/runs/hexa-forge-code-3b-v0.2.0-r6.Q5_K_M.gguf ] && \
    mv /home/summer/runs/hexa-forge-code-3b-v0.2.0-r6.Q5_K_M.gguf /tmp/r6_q5/ 2>/dev/null || true

# r7: copy from canonical home
cp /home/summer/runs/hexa-forge-code-3b-v0.2.0-r7.f16.gguf /tmp/r7_f16/ 2>/dev/null || true
cp /home/summer/runs/hexa-forge-code-3b-v0.2.0-r7.Q5_K_M.gguf /tmp/r7_q5/ 2>/dev/null || true

# README templates
for round in r6 r7; do
    for fmt in f16 q5; do
        TARGET="/tmp/${round}_${fmt}/README.md"
        [ -f "$TARGET" ] && continue
        if [ "$fmt" = "f16" ]; then
            BPW="FP16"
            SZ="6.17 GB"
            QSPEC=""
        else
            BPW="Q5_K_M (5.75 BPW)"
            SZ="2.07 GB"
            QSPEC="-Q5_K_M"
        fi
        cat > "$TARGET" <<EOFMD
---
license: apache-2.0
language: [en, ko, zh, ru, ja]
tags: [hexa-forge, hexa-canon, code, lora, sft, gguf, swift, swiftui]
base_model: Qwen/Qwen2.5-Coder-3B
---

# hexa-forge-code-3b${QSPEC}-GGUF${QSPEC:+ }${round}

GGUF $BPW export of the v0.2.0-${round} LoRA-merged Qwen2.5-Coder-3B model.
Size: $SZ.

## Eval (STRICT, real hexa-cc compile + spec matchers)

| bench | r6 | r7 |
|-------|-----|-----|
| hexa-eval Mk.0.1 | 53.6% | 60.7% |
| 5-NL Mk.0.1 | 92% | 92% |

## Lineage

- base: \`Qwen/Qwen2.5-Coder-3B\`
- adapter: \`dancinlab/hexa-forge-code-3b-qwen2.5-lora-r16-v0.2.0-${round}\`

## Inference

\`\`\`bash
./llama-cli -m hexa-forge-code-3b-v0.2.0-${round}.${fmt}.gguf \\
    -p "### User:\nWrite a SwiftUI view.\n### Assistant:\n"
\`\`\`
EOFMD
    done
done

# Upload each missing piece
python3 << 'PY'
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ['HUGGING_FACE_HUB_TOKEN'])

UPLOADS = [
    ("dancinlab/hexa-forge-code-3b-GGUF-f16-v0.2.0-r6", "/tmp/r6_f16", "model"),
    ("dancinlab/hexa-forge-code-3b-Q5_K_M-GGUF-v0.2.0-r6", "/tmp/r6_q5", "model"),
    ("dancinlab/hexa-forge-code-3b-GGUF-f16-v0.2.0-r7", "/tmp/r7_f16", "model"),
    ("dancinlab/hexa-forge-code-3b-Q5_K_M-GGUF-v0.2.0-r7", "/tmp/r7_q5", "model"),
]
for repo_id, folder, repo_type in UPLOADS:
    if not os.path.exists(folder) or not any(f.endswith(".gguf") for f in os.listdir(folder)):
        print(f"SKIP (no gguf locally): {repo_id}")
        continue
    try:
        api.create_repo(repo_id, repo_type=repo_type, exist_ok=False)
        print(f"created {repo_id}")
    except Exception as e:
        print(f"create {repo_id}: {e}")
    r = api.upload_folder(folder_path=folder, repo_id=repo_id, repo_type=repo_type,
        commit_message="GGUF export — recovery upload after token refresh")
    print(f"  upload: {r}")

# Bench results from local runs/ (r7-strict)
BENCH = [
    ("/home/summer/runs/hexa-eval-r7", "hexa-eval-r7-strict"),
    ("/home/summer/runs/five-nl-r7", "five-nl-r7-strict"),
]
for src, sub in BENCH:
    if not os.path.exists(src):
        print(f"SKIP bench: {src}")
        continue
    r = api.upload_folder(folder_path=src,
                          repo_id="dancinlab/hexa-forge-bench-cold-v0.1.3",
                          path_in_repo=sub, repo_type="dataset",
                          commit_message=f"add {sub} (recovery)")
    print(f"bench {sub}: {r}")

print("RECOVERY DONE")
PY
