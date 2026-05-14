# OPERATIONS — forge runtime production runbook

> **Domain doc** (per dancinlab-wide `domain-meta-domain` principle:
> per-topic operations as root `UPPERCASE.md`). The orchestration
> *spec* lives in [`ORCHESTRATION.md`](ORCHESTRATION.md); this file is
> *what you do at 3 AM when the on-call page fires*. Current state
> below, chronological build history at `## Log` (bottom).

**Status:** OPS RUNBOOK · v0.5.14 (r62) target stack · 2026-05-14

---

## 0. The 5-step pre-deploy checklist

Before flipping the runtime on for real traffic, in order:

1. Run `python3 tool/run_all_smoke.py` — exit 0 required (7/7 steps).
2. Confirm `state/delegation_log.jsonl.parent` is writable + on local disk.
3. If using `forge_db_path` (SQLite WAL): confirm path is on local disk
   (NOT NFS/CIFS — see §5 below).
4. Confirm vendor keys present: `python3 -c "from tool.forge_runtime import ForgeRuntimeConfig; cfg = ForgeRuntimeConfig.from_env(); print('anthropic:', bool(cfg.anthropic_api_key), 'openai:', bool(cfg.openai_api_key), 'gemini:', bool(cfg.gemini_api_key))"`.
5. Soak test for ≥1 hour with `forge_audit --since-hours 1` showing
   `cache_hit_rate ≥ 0.0` (no negative noise), `error_rate ≤ 0.05`,
   and no `upstream_5xx` codes.

---

## 1. Topology — what writes / reads what

```
ForgeRuntime
   ├─ writes  → state/delegation_log.jsonl   (one line per turn)
   ├─ writes  → forge_db_path                (SQLite WAL: cache + conv)
   │            OR vendor_cache_path JSONL   (single-process fallback)
   │            OR conv_history_path JSONL   (single-process fallback)
   ├─ reads   → ANTHROPIC_API_KEY env / secret CLI
   ├─ reads   → OPENAI_API_KEY env / secret CLI
   ├─ reads   → GEMINI_API_KEY env / secret CLI

forge_audit                      forge_vacuum
   reads ← state/delegation_log    reads + writes ← forge_db_path
   exit 2 on gate breach            (requires runtime IDLE during VACUUM)
```

**Read-only paths**: `eval/delegation-mk0/manifest.jsonl` (300-task
held-out manifest — never modified post-r51).

**Append-only paths**: `state/delegation_log.jsonl`. Should be
log-rotated by external tooling (e.g. `logrotate`) — runtime does not
self-rotate.

**Read + write paths**: `vendor_cache_path` JSONL or `forge_db_path`
SQLite — compacted on eviction (JSONL) or on `forge_vacuum` (SQLite).

---

## 2. Daily cron template

`/etc/cron.d/forge`:

```cron
# 03:00 — vacuum SQLite (must be runtime-idle window)
0 3 * * * forge python3 /opt/forge/tool/forge_vacuum.py \
    --db /var/lib/forge/forge.sqlite3 \
    --keep-recent 4096 \
    --conv-days 30 \
    > /var/log/forge/vacuum.$(date +\%Y\%m\%d).log 2>&1

# 03:30 — audit last 24h, alert on breach
30 3 * * * forge python3 /opt/forge/tool/forge_audit.py \
    --input /var/lib/forge/state/delegation_log.jsonl \
    --since-hours 24 \
    --alert-cache-hit-min 0.20 \
    --alert-error-rate-max 0.05 \
    --alert-cost-day-max 50.00 \
    > /var/log/forge/audit.$(date +\%Y\%m\%d).log 2>&1 \
    || mail -s "forge degraded on $(hostname)" oncall@example.com

# 04:00 — rotate delegation log (preserves last 30 days)
0 4 * * * forge logrotate /etc/logrotate.d/forge

# Weekly Sunday 02:00 — re-run smoke against current code
0 2 * * 0 forge cd /opt/forge && python3 tool/run_all_smoke.py \
    > /var/log/forge/smoke.$(date +\%Y\%m\%d).log 2>&1
```

`/etc/logrotate.d/forge`:

```
/var/lib/forge/state/delegation_log.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 forge forge
    postrotate
        # No reload needed — runtime opens log in append mode each turn
    endscript
}
```

---

## 3. Error code troubleshooting (DelegationCall.error)

Per [`ORCHESTRATION.md §8.E`](ORCHESTRATION.md), the runtime emits 6
error codes. Each maps to a specific operator action:

### `auth_fail`

**Cause**: vendor SDK not installed OR API key not configured OR 401 from upstream.

**Diagnosis**:
```bash
# Check SDK presence
python3 -c "import anthropic; print(anthropic.__version__)"
python3 -c "import openai; print(openai.__version__)"
python3 -c "from google import genai; print('genai ok')"

# Check key loading (uses _load_key path: env → secret CLI)
python3 -c "from tool.forge_runtime import ForgeRuntimeConfig; \
    cfg = ForgeRuntimeConfig.from_env(); \
    print('anthropic:', bool(cfg.anthropic_api_key)); \
    print('openai:', bool(cfg.openai_api_key)); \
    print('gemini:', bool(cfg.gemini_api_key))"
```

**Fix**:
- macOS keychain: `security add-generic-password -s anthropic.api_key -a $USER -w sk-ant-...`
- Linux env: `export ANTHROPIC_API_KEY=sk-ant-...` in the forge user's profile
- Install missing SDK: `pip install anthropic` / `openai` / `google-genai`

**Telemetry sign**: `forge_audit` shows `auth_fail` in errors breakdown.
If cluster: usually a key rotation that missed the runtime restart.

### `upstream_timeout`

**Cause**: vendor took longer than 30s to respond.

**Diagnosis**:
- Single occurrence: transient; retry succeeds.
- Pattern: vendor degraded OR network path to vendor degraded.

**Fix**:
- Confirm vendor status page (status.anthropic.com / status.openai.com).
- If your network: check egress firewall / NAT.
- If sustained: increase timeout via `ForgeRuntimeConfig` override (default 30s; rebuild + redeploy).

### `upstream_5xx`

**Cause**: vendor returned a 500-level error.

**Diagnosis**: usually vendor-side. Check vendor status page.

**Fix**: typically transient; client should retry with backoff. Runtime
does NOT auto-retry (per ORCHESTRATION.md §15 caveat — auto-retry is
v0.6.x candidate). Calling code can implement retry loop on this code.

### `upstream_quota`

**Cause**: vendor 429 — rate limit OR daily/monthly quota exhausted.

**Diagnosis**:
- Check vendor dashboard for usage vs tier limits
- For Gemini-pro: free-tier limit=0 by default; needs paid-tier
  activation (see v0.6.0+ roadmap in ORCHESTRATION.md §12).

**Fix**:
- Wait for rate-limit window to reset (usually 60s) OR upgrade tier.
- If chronic: lower request rate via calling-code throttling, or move
  routing to a cheaper tier (e.g. opus → sonnet for non-deep prompts).

### `schema_violation`

**Cause**: runtime config rejected the delegation (tool not in
allowlist, model not allowed, etc.).

**Diagnosis**:
```bash
python3 -c "from tool.forge_runtime import ForgeRuntimeConfig; \
    cfg = ForgeRuntimeConfig.from_env(); \
    print('allowed_tools:', cfg.allowed_tools)"
```

**Fix**: Update `ForgeRuntimeConfig.allowed_tools` to include the
target tool. If the call came from a legitimate user prompt, this is
a config drift — re-deploy with the correct allowlist.

### `redaction_block`

**Cause**: prompt contained one of the PII / secret classes (api-key,
bearer-token, email, private-key-block, aws-key-id, secret-name-like,
phone, internal-host).

**Diagnosis**: the DelegationCall record includes
`prompt_redacted_classes` — surfacing WHICH class fired.

**Fix**: this is the runtime working correctly. Tell the user to strip
the secret + retry. If false-positive: tighten the relevant pattern in
`tool/forge_runtime.py` `redact()`.

---

## 4. Health gate troubleshooting

`forge_audit --alert-*` flags exit 2 on threshold breach. Common
patterns:

### `cache hit rate X% < threshold Y%`

**Possible causes**:
1. Fresh deploy — no cache warmup yet. Wait 15 min.
2. Prompt distribution changed — calling code is asking many unique
   prompts. Investigate prompt patterns.
3. TTL too short for the workload. Default 300s may be too aggressive
   for prompts with low repeat rate. Tune `vendor_cache_ttl_s`.
4. Cache misses on conversational flows when `multi_turn_memory_auto_prepend`
   is on — by design, each turn produces a different cache key. Use
   `forge_audit` per-tier breakdown to confirm.

### `error rate X% > threshold Y%`

**Drill-down**:
```bash
python3 tool/forge_audit.py \
    --input /var/lib/forge/state/delegation_log.jsonl \
    --since-hours 1 \
    --output json | jq '.error_codes'
```

If errors are concentrated in one code, see §3 above.

### `24h cost $X > threshold $Y`

**Drill-down**:
```bash
# Top tiers by spend
python3 tool/forge_audit.py --since-hours 24 --output json \
    | jq '.cost_usd.by_tier'

# Top expensive turns
python3 tool/forge_audit.py --since-hours 24 \
    | tail -20  # "TOP MOST EXPENSIVE TURNS" section
```

If opus calls dominate cost, consider:
- Promoting more prompts to o4-mini via classifier patterns
- Reducing `max_tokens` for opus tier in `select_vendor_tier`
- Manually de-tiering specific repeat prompts via pre-classifier rules

---

## 5. Multi-process deployment notes

**SQLite WAL is multi-process safe** but with specific constraints:

- **Local disk only** — NOT NFS, CIFS, SMB, FUSE, or other network
  filesystems. SQLite WAL relies on POSIX file locking semantics that
  most network FS implementations don't honor correctly. For
  distributed deploys, use a real network DB (Postgres / managed
  Redis / DynamoDB) — out of v0.5.x scope.
- **Single writer at a time** — readers can be concurrent. If you see
  `sqlite3.OperationalError: database is locked`, a writer held the
  lock past the 10s default timeout. Either increase timeout via the
  config or split high-throughput workloads (>1K writes/sec) across
  multiple DBs by some sharding key.
- **VACUUM requires exclusive lock** — `forge_vacuum` will block on
  active writers. Schedule cron in a low-traffic window.

**JSONL paths (`vendor_cache_path` / `conv_history_path`) are
NOT multi-process safe.** Two processes appending to the same JSONL
file CAN interleave (each append is one syscall but writers don't
coordinate). Use JSONL only for single-process deployments.

---

## 6. Rollback procedures

### Rollback v0.5.x → v0.4.0 (last specialist-only era)

This is the safe fallback if orchestration causes a regression:

```python
cfg = ForgeRuntimeConfig.from_env(
    use_orchestration=False,  # legacy v0.4.0 path
)
```

The runtime then bypasses classifier + tier selector + cache + multi-
turn entirely; every turn goes straight to the 7B with no external
delegation. Quality unchanged at r39 GA's 94.29% Mk.I strict.

### Rollback SQLite → JSONL

If SQLite WAL exhibits problems (locked DB, corruption, etc.):

```python
cfg = ForgeRuntimeConfig.from_env(
    forge_db_path=None,                # disable SQLite
    vendor_cache_path=Path("/var/lib/forge/cache.jsonl"),
    multi_turn_memory_enabled=True,
    conv_history_path=Path("/var/lib/forge/conv.jsonl"),
)
```

This is a config-only rollback; no code change. CAVEAT: data does NOT
migrate between backends — switching loses the cache + conv state from
the prior backend.

### Rollback cache TTL

If 5-min TTL is too aggressive (low cache hit rate) or too lax (stale
responses), adjust:

```python
cfg.vendor_cache_ttl_s = 600  # 10 minutes
# or
cfg.vendor_cache_ttl_s = 0    # disable cache entirely (test mode)
```

---

## 7. Common runbook scripts

### "Verify everything before deploy"

```bash
python3 tool/run_all_smoke.py
# Exit 0 = all 7 steps green; exit 1 = any failed
```

### "Show production health right now"

```bash
python3 tool/forge_audit.py \
    --input /var/lib/forge/state/delegation_log.jsonl \
    --since-hours 24
```

### "Measure classifier latency"

```bash
python3 tool/perf_bench.py --iterations 10000
# Headline: combined classify+select round-trip p50/p95/p99 in μs
```

### "Drain expired cache + conv-history"

```bash
python3 tool/forge_vacuum.py \
    --db /var/lib/forge/forge.sqlite3 \
    --keep-recent 4096 --conv-days 30
```

### "Dry-run vacuum (no changes, report only)"

```bash
python3 tool/forge_vacuum.py \
    --db /var/lib/forge/forge.sqlite3 \
    --keep-recent 4096 --conv-days 30 --dry-run
```

### "Re-score classifier on held-out manifest"

```bash
python3 tool/score_orchestration_mk0.py \
    --manifest eval/delegation-mk0/manifest.jsonl \
    --output bench/score-orchestration-mk0-$(date +%Y%m%d)
```

---

## 8. Performance baselines (r63 perf_bench)

Measured 2026-05-14 on Mac M-chip, Python 3.9, 5K iterations:

| Component | mean | p50 | p95 | p99 |
|---|---:|---:|---:|---:|
| `classify_prompt` | 528μs | 557μs | 890μs | **1.86ms** |
| `select_vendor_tier` (OOD only) | 1.71μs | 1.21μs | 1.54μs | 1.62μs |
| Combined classify+select | 520μs | 556μs | 800μs | **1.66ms** |
| `vendor_cache_key` (sha256) | 1.64μs | 1.29μs | 1.46μs | 2.04μs |

**ORCHESTRATION.md §4 "~1ms per prompt" claim**: verified — p50 is
556μs (well under 1ms), p99 is 1.66ms (worst-case still sub-2ms).
Classifier dominates the budget; the tier selector and cache key are
single-digit microseconds.

For production-relevant context: vendor-call latency is typically
3000-15000ms (claude-sonnet) or 5000-25000ms (claude-opus). Classifier
+ selector add **< 0.01% of total turn latency** — effectively free.

---

## 9. Honest limits + what we don't know yet

- **Real-world hit rate** is workload-dependent. The 300-task DLG-mk0
  manifest is held-out but synthetic. Production telemetry over weeks
  is the only honest answer to "what's our cache hit rate".
- **Cost-saved estimate in `forge_audit`** is a heuristic (avg same-
  (tool, model) miss cost × hits). High variance per-call workloads
  make this noisier; track over time.
- **The `confidence` field** is calibrated (Brier 0.0242 / ECE 0.0461)
  but on the manifest used to design the patterns. Production
  monitoring should validate ECE doesn't drift.
- **No SQL/time-series database integration**. `forge_audit` is a
  one-shot CLI. For continuous dashboards, scrape its CSV output into
  Prometheus/Datadog/your monitoring system.
- **OpenAI key not provisioned** at the time of writing (r62). Reason-algo
  + struct routes will all `auth_fail` until a key is added to the
  secret store. Until then, prompts routed to those tiers fall through
  to the user-facing "auth not configured" message.
- **Anthropic cross-turn cache_control marker IS A NO-OP in practice**
  (r64 finding; see `bench/score-anthropic-xt-r64/`). Anthropic auto-
  caches conversation prefix using only the system-message marker
  (r45 baseline behavior). r62's `_anthropic_cache_mark` was kept in
  code as a defensive marker but produces identical cache behavior to
  baseline at sonnet scale. Operators should NOT expect additional
  savings from `anthropic_cross_turn_cache_enabled=True` beyond what
  anthropic's automatic caching already provides; the toggle exists
  for A/B verification and future-proofing, not for cost reduction.

---

## 10. Bookmarks

- [`ORCHESTRATION.md`](ORCHESTRATION.md) — runtime spec (the "what")
- [`ROADMAP.md`](ROADMAP.md) — per-round narrative (r1–r63)
- [`LEARNING_PROGRAMMING.md`](LEARNING_PROGRAMMING.md) — recipe + training history
- [`LATTICE_POLICY.md`](LATTICE_POLICY.md) — dancinlab real-limits standard
- [`bench/`](bench/) — per-round score artifacts (latest: r55 orch, r55 brier, r53 e2e)

---

## Log

- **2026-05-14 r63** — This runbook created alongside `tool/run_all_smoke.py`
  (unified smoke runner, 7 steps, exit-0-or-1 for CI) and
  `tool/perf_bench.py` (classifier + selector + cache_key latency
  measurement, backs ORCHESTRATION.md §4 "~1ms" claim with hard numbers:
  p50 556μs / p99 1.66ms). All 7 unified smoke steps PASS in 4.50s on
  Mac M-chip.
