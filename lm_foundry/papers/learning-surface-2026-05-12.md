# Learning Surface Audit — 2026-05-12

> Survey of `~/core/*` (90 projects) to identify domains the hexa-forge
> code-LLM should learn beyond the current 7 langs (Python/Rust/TS/Go/C/
> Zig/Swift) + Apple stack.

## Method

- Walked all 90 `~/core/*` subdirs (excluding `archive-*`, `anima_clm_*`
  numbered snapshots, `legacy`).
- Tagged each by: dominant file extension(s), build manifest, presence of
  framework files (Dockerfile, CMakeLists.txt, package.json, Cargo.toml,
  go.mod, pyproject.toml, Package.swift, pubspec.yaml, build.zig).
- Read README/spec headers for the top-signal projects.
- Discarded archives, internal-only marker streams, snapshot directories.

## Findings — domains the LLM does NOT currently know

Ordered by both **volume of code in the user's ecosystem** AND **likelihood
of being asked**.

### Tier 1 — actively used, large volume

| domain                     | source project        | files (approx) | why it matters |
|----------------------------|-----------------------|----------------|----------------|
| **Dart / Flutter**         | `cake-wallet/`        | ~962 `.dart`   | The Stage-1 backend of `wraith-wallet` wraps cake-wallet directly. Multi-chain BTC + XMR + ETH + LTC mobile UI. User actively maintains the fork. |
| **Zig (deep)**             | `void/`               | substantial `.zig` (build.zig + src/) | `void` is a CMake-wrapped Zig library (libvoid-vt). Real-world Zig + Zig build system (`build.zig.zon`). Our current Zig coverage is Stack v1 sample only — no `build.zig` patterns. |
| **PyTorch + CUDA + RunPod**| `anima/`              | ~3296 `.json`, large Python `training/` tree | Production ML stack: pytorch/pytorch:2.5.1-cuda12.4 docker, requirements pinning, RunPod SSH, cloudflared tunneling, checkpoint management (`checkpoints/clm_v2/`). |
| **Playwright (browser automation)** | `browser-harness/` | `playwright-core` node deps | Cross-browser scraping / e2e test harness. Not in our SFT. |
| **Discord bot + Anthropic SDK** | `pixie/`         | node + Anthropic SDK     | `pixie/discord-translator/` + `worker/` use `@anthropic-ai/sdk`. Bot patterns: slash commands, interactions, embeds. |
| **TOML schema design**     | `hexa-meta/`          | ~601 `.toml`   | `hexa-toml-spec.json` versioned 1.0.0. The user's whole stack uses TOML for project manifests (hexa.toml everywhere). Our SFT touched a few but not the patterns. |
| **DuckDB analytics**       | `orpheus/dormant_explorer/` | implicit | "DuckDB main path; BigQuery driven; lost-likelihood heuristics" — chain-wide Bitcoin dormant address analysis. |
| **BigQuery SQL**           | `orpheus/`            | implicit       | Same project, BigQuery for chain-scale aggregations. |

### Tier 2 — domain-specific terminology + libraries

| domain                  | source           | concept set |
|-------------------------|------------------|-------------|
| **BIP-series crypto**   | wraith-wallet, orpheus | BIP39 mnemonic (24 words + wordlist checksum), HD wallet derivation, PSBT, ECDSA recovery, Schnorr/Taproot |
| **Monero / XMR / RingCT** | wraith-wallet/backend_cake → backend_native | RingCT, ring signatures, stealth addresses, view/spend keys |
| **Tor stack**           | wraith-wallet, cake-wallet | built-in Tor integration for mobile wallet; .onion v3 |
| **Lightning Network**   | wraith-wallet (relay sub-domain) | HTLCs, channel state, BOLT specs |
| **Slipstream / Eden / bloXroute** | orpheus, wraith-wallet | private mempool / private-relay procurement |
| **age-file key store**  | wraith-wallet/vault/ | age encryption format for keys at rest |
| **TOTP 2FA**            | wraith-wallet/vault/ | RFC 6238 time-based OTP |
| **Atomic swaps**        | cake-wallet integration | BTC↔XMR atomic swap protocol |

### Tier 3 — meta-tooling / build / ops

| domain                | source              | gap |
|-----------------------|---------------------|-----|
| **Docker (PyTorch ML)** | anima/Dockerfile  | apt-get, cloudflared, SSH-for-RunPod patterns |
| **cloudflared tunneling** | anima           | Linux GPU rental tunneling |
| **age encryption**    | wraith-wallet/vault | symmetric file encryption |
| **GitHub Actions / CI** | hexa-forge .github/workflows | (we have one workflow, but minimal SFT) |
| **CMake → Zig bridge**| void/CMakeLists.txt | non-trivial cross-build-system pattern |

### Tier 4 — narrow but distinctive

| domain          | source         | notes |
|-----------------|----------------|-------|
| **DSP / audio** | anima (portaudio19-dev, libportaudio2) | audio I/O on GPU runtime |
| **Cairo / circuit DSL** | (not found) | not in ecosystem |
| **Solidity / Ethereum smart contracts** | (mentioned in cake-wallet ETH support but no source) | not in repo |
| **QRNG / quantum entropy** | qmirror, qrng | hardware entropy source consumption for cryptography |

## Specifically excluded per user direction

- **ORM** — user said "ORM 은 사용안되고 있을수 있다 (may not be used)". Survey confirms: no SQLAlchemy / Prisma / Diesel / TypeORM /
  Drizzle / Hibernate / Active Record patterns visible. Stack uses raw
  SQL via DuckDB/BigQuery, or `hexa.toml` declarative state. **SKIP ORM.**

## Recommended additions for v0.3.0 SFT

In priority order by user-value × LLM-leverage:

### P0 (next round — high yield)

1. **Dart / Flutter** — ~100 hand-crafted Q/A pairs covering:
   - StatelessWidget / StatefulWidget skeleton
   - BLoC pattern, Provider, Riverpod
   - flutter_secure_storage for keys
   - HTTP via dio / http
   - JSON via dart:convert + json_serializable
   - Flutter for desktop (cake-wallet is multi-platform)
   - Plus: Dart-side BIP39 / ECDSA helper calls (since cake-wallet uses them)

2. **PSBT + BIP39 + HD-wallet** — ~50 pairs covering canonical recipes:
   - BIP39 mnemonic → seed → master xprv → derivation path
   - PSBT v0 + v2 structure (BIP-174 / BIP-370)
   - Taproot key-spend vs script-spend
   - Common scripts: P2WPKH, P2WSH, P2TR
   - Anti-pattern: hand-rolled wordlist (always use BIP39 official list)

3. **PyTorch training-loop boilerplate** — ~80 pairs:
   - DataLoader + Dataset + collate_fn
   - mixed-precision (autocast + GradScaler)
   - DDP (DistributedDataParallel) skeleton
   - checkpoint save/load + `strict=False` for resume
   - LR schedulers (cosine + warmup, WSD)
   - PyTorch 2.5+ specific: `torch.compile()`, FSDP2

### P1 (round after)

4. **Zig deep** — ~50 pairs:
   - `build.zig.zon` package manifest
   - `build.zig` artifact / dep / pkg-config emit
   - `comptime` patterns
   - allocator hygiene (`std.heap.GeneralPurposeAllocator`)
   - error sets + `errdefer`

5. **Discord bot patterns** — ~30 pairs (since pixie uses them):
   - discord.js Client + intents
   - slash commands via SlashCommandBuilder
   - interaction.deferReply for >3s work
   - embeds + components (buttons / select menus)
   - rate limit handling

6. **Playwright (browser-harness style)** — ~30 pairs:
   - `browser.newContext` + storage state
   - `page.waitForLoadState` patterns
   - locator chaining, `getByRole` / `getByText`
   - download/upload handling
   - tracing + video for debugging

7. **TOML schema design** — ~30 pairs:
   - root-table key conventions
   - inline table vs table-array
   - dotted key path semantics
   - validation via `serde` (Rust) / `tomli` (Python)

### P2 (later)

8. **DuckDB + BigQuery SQL** — analytical patterns (window funcs, CTEs, qualify).
9. **age encryption** — file encryption recipe + key recovery.
10. **Tor / .onion integration** — stem/torpy basics.

## Per-project recommendation table (what to mine for SFT)

| project              | tier | mine for          | rough effort |
|----------------------|------|-------------------|--------------|
| cake-wallet/         | P0   | Dart/Flutter idioms; BIP39 in Dart | 1-2 hours hand-curate |
| anima/               | P0   | PyTorch boilerplate; CUDA dockerfile patterns | 1 hour |
| void/                | P1   | Zig build.zig; libvt patterns | 1 hour |
| pixie/               | P1   | Discord bot + Anthropic SDK; node worker patterns | 30 min |
| browser-harness/     | P1   | Playwright recipes | 30 min |
| orpheus/             | P0   | BIP/crypto + DuckDB analytics | 1 hour |
| wraith-wallet/       | P0   | BIP/age/TOTP/PSBT recipes | 1 hour |
| hexa-meta/           | P1   | TOML schema authoring | 30 min |
| hexa-codex/          | (already covered in canon corpus) | — | — |
| hexa-lang/           | (already covered in canon corpus) | — | — |

## Not worth SFT-ing

- `anima_clm_01..13` snapshot directories — historical only; no new patterns.
- `archive-*` — explicitly archived.
- `state/`, `markers/` — large counts of `.marker` files are state, not code.
- `gamebox/` — release-note heavy; minimal new code patterns.
- `legacy/` — opt-out.
- All `hexa-<single-word>` placeholders with mostly empty contents (hexa-arts,
  hexa-cosmos, etc. — 14-18 md files = roadmap stubs).

## Operating note

The `~/core/*` survey itself reveals an important framing fact: this
ecosystem is **>90% hexa + .marker state files**, with the actual code-LLM
training surface coming from a **small set of high-density projects**
(cake-wallet, void, anima, pixie, browser-harness, orpheus). Future
SFT iterations should mine these directly rather than treating the full
ecosystem as a uniform corpus.

## v0.3.0 SFT dataset proposal

Builder: `tool/build_sft_dataset_v8.py` (next round)

Composition (target ~2,400 rows):
- v7 base                                          1,985
- Dart/Flutter Q/A (P0)                              100
- BIP39/PSBT/HD-wallet (P0)                           50
- PyTorch training-loop (P0)                          80
- Zig deep (P1)                                       50
- Discord bot (P1)                                    30
- Playwright (P1)                                     30
- TOML schema (P1)                                    30
- Plus optional: T5 HX-codes recovery + T4 enum fix  ~50

This would land the **v0.2.0-r8** adapter on dancinlab with crypto-wallet
ecosystem competence (cake-wallet maintainability) + ML-systems competence
(anima training loops) + browser automation + Discord bot patterns.

Expected eval impact (best case):
- hexa-eval STRICT: 60.7% → 60-65% (steady, depending on r7 retention)
- 5-NL F1 code synth: 100% → 100% (broader code base, same baseline)
- New ad-hoc benches possible:
  - **dart-eval**: Flutter widget Q/A (10-20 tasks)
  - **crypto-eval**: BIP/PSBT recipes (15-20 tasks)
  - **pytorch-eval**: training-loop Q/A (20-30 tasks)
