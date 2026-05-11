# forge T4 empirical: infer_cost — 2026-05-11-stack-v1-fetch-pipeline

> **Stage 0 stub.** Emitted by `tool/emit_t4.py` at run time;
> measurement fields populated from forge run artefacts. Until SFT /
> inference / eval runs land, this draft holds the **interface shape**
> only — the `<TODO>` markers reveal where real numbers slot in.

## Provenance
- forge run: `2026-05-11-stack-v1-fetch-pipeline` (commit SHA: `942d5c6bc3`)
- model: `Qwen/Qwen2.5-Coder-7B`
- date: `2026-05-11`
- compute: `<TODO>`
- corpus snapshot: `<TODO>`
- tokenizer: `<TODO>`

## What this measures
latency + KV-cache profile. Verb: `infer_cost` — falsifier target: `F-CODEX-2` (T4 (D-005)).
For details, consult the verb spec at
`~/core/hexa-codex/infer_cost/ai-infer-cost.md`
(authoritative; do NOT inline-copy here per linkage rule).

## Falsifier closure delta
- `F-CODEX-2`: T4 was `PENDING`; now `UNDETERMINED` (stub — awaiting real forge run)
- Recipe §3 `closure_pct` impact: <TODO once real numbers land>

## Numbers
| metric | value | reference |
| ------ | ----- | --------- |
| context_lengths | <TODO: parse /home/summer/runs/forge_measurements/infer_cost.json> | (TODO add ref) |
| tokens_per_sec_per_ctx | <TODO: parse /home/summer/runs/forge_measurements/infer_cost.json> | (TODO add ref) |
| kv_cache_bytes_per_token | <TODO: parse /home/summer/runs/forge_measurements/infer_cost.json> | (TODO add ref) |
| measured_tau_exponent | <TODO: parse /home/summer/runs/forge_measurements/infer_cost.json> | (TODO add ref) |

## Reproducibility
- script: `<TODO: path to forge run driver>`
- inputs: `<TODO: corpus subset SHA / eval set SHA>`
- runtime: `ubu-2-cpu`
- determinism: seed = <TODO>; nondeterminism notes: <TODO>

## Cross-link
- forge-side artifact: `<TODO: runs/2026-05-11-stack-v1-fetch-pipeline/...>`
- hexa-codex landing site: `verify/numerics_infer_cost_t4_parity.hexa` (new)
- F-CODEX arithmetic floor (T1+T2+T3): already PASS at hexa-codex v1.0.0

## License / attribution
### corpus license tags
- MIT,Apache-2.0,BSD-3-Clause

### benchmark sources (with license)
- <TODO: list benchmark sources with license>

## Validation checklist
- [ ] `hexa-codex verify falsifier-check` still PASS
- [ ] `hexa-codex verify saturation-check` still emits `__HEXA_CODEX_SATURATION_CHECK__ PASS`
- [ ] `hexa-codex verify release-ladder` monotonicity holds
- [ ] new T4 layer's parity verifier landed (`verify/numerics_infer_cost_t4_parity.hexa`)
- [ ] CHANGELOG entry in hexa-codex (`[Unreleased]` block)
- [ ] `tool/license_clean_scan.py` against `<TODO>` PASS
- [ ] forge-side commit pinned: `942d5c6bc3`

---
*Emitted by `tool/emit_t4.py` (forge stage 0). Spec: `papers/plan-feedback-channel-ops.md`. Outbox discipline: `outbox/hexa-codex/README.md`.*
