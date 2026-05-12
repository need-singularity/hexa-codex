<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->
<!-- SPDX-FileCopyrightText: 2026 hexa-forge contributors -->
<!-- @canonical: forge@v0.1.2:papers/spec-firmware-eval.md -->
<!-- @owns(sections=[HEADER, WHY, COMPARE, REQUIRES, STRUCT, FLOW, EVOLVE, VERIFY, FEEDBACK, TOOLING], strict=false, order=sequential, prefix="S") -->

# `firmware-eval` — custom benchmark spec for bare-metal + RTOS fidelity

> **Acceptance gate (v1.0.0).** This spec defines benchmark **⑥** from
> [`docs/code-llm.md` §EVOLVE](../docs/code-llm.md#evolve--eval-harness)
> — the **firmware** group rolling up four custom benches: `MCU-bench`
> (≥ 50% on Cortex-M), `linker-script literacy` (≥ 70%), `memory-fit`
> (≥ 80% hit budget), and `hexa target gate` (100% correct rejection).
> The four are shipped as **one** runner with one task taxonomy so the
> aggregate gate ⑥ is a single number. Bar exists in the recipe; the
> **shape** is defined here. Implementation lands v0.1.3+.
>
> **Decisions referenced.** D-020 (C + firmware §WHY/§STRUCT add —
> firmware is a first-class surface; `firmware-native` + `hexa-firmware`
> stages live in §STRUCT; §EVOLVE 4 firmware benches; §VERIFY firmware
> tool surface `run_size / read_map / read_disasm / read_register`),
> D-006 (hexa-lang is firmware-native, acknowledged from SPEC.md §18),
> D-013 (no LLM-judge for gold-output synthesis — Shumailov 2024
> model-collapse risk), D-021 (hexa fidelity contract — including the
> `--target=*-none-*` host-stdlib rejection rule that anchors T8 here).
> See [`papers/plan-decisions-pending.md`](plan-decisions-pending.md).
>
> **Sister methodology canon.** Section discipline (S-prefix,
> falsifier-anchored, Mk.I → Mk.V progression) mirrors
> [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md).
> Forge does not duplicate methodology — it instantiates it for one
> custom benchmark in a domain (firmware) that public benches do not
> address at all.
>
> **Sister forge specs.** [`spec-hexa-eval.md`](spec-hexa-eval.md)
> (gate ③, hexa-fidelity) and [`spec-five-nl-eval.md`](spec-five-nl-eval.md)
> (gate ④, cross-lingual). `firmware-eval` T8 (hexa target gate) and
> hexa-eval T6/T7 (linker-aware codegen + stdlib direction) intersect
> on the host-stdlib rejection contract — by design, both surfaces
> verify the same canon from different angles.

---

## S0 HEADER

| field             | value                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| verb              | `code` (sub-artifact `firmware-eval`)                                                          |
| family            | `hexa-forge`                                                                                   |
| status            | `RESEARCH_FIRST` — spec only, runner script planned                                            |
| dispatch          | `hexa-forge code eval --bench firmware-eval`                                                   |
| acceptance gate   | **≥ 50% pass on Cortex-M** (primary); RISC-V + Xtensa softer at this gate (≥ 35% diagnostic)   |
| task count target | **~600** (T1=100, T2=80, T3=50, T4=80, T5=50, T6=80, T7=30, T8=30, T9=100)                     |
| owner             | `forge.code` verb                                                                              |
| sister gates      | ③ `hexa-eval` ([`spec-hexa-eval.md`](spec-hexa-eval.md)); ④ `5-NL eval` ([`spec-five-nl-eval.md`](spec-five-nl-eval.md)) |
| codex feedback    | `hexa-codex/quality_scale` (firmware-fidelity axis) + `hexa-codex/eval` (firmware methodology delta) + `hexa-codex/deploy` (hardware-tier recipes) — per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md) |
| last updated      | 2026-05-11                                                                                     |

---

## S1 WHY — why firmware is its own benchmark surface

Firmware is **not** a subset of "general code." The surface area is
disjoint along every axis that matters for evaluation:

- **memory model** — MMIO peripheral registers, `volatile` to defeat
  the compiler, write-only / read-clear / W1C semantics, DMA alignment
- **execution model** — preemptive ISRs, cooperative RTOS tasks, DMA
  that runs parallel with CPU, WFI/sleep modes mutating state
- **build artifact** — linker script controls
  `.text/.bss/.data/.rodata/.heap/.stack`; reset vector at fixed
  address (or `VTOR`-redirected); section alignment matters for
  flash-erase granularity and DMA-bounce buffers
- **toolchain** — `arm-none-eabi-gcc`, `clang
  --target=thumbv7em-none-eabi`, `riscv32-unknown-elf-gcc`,
  `xtensa-esp32-elf-gcc` — each with libc-newlib / semihosting / LTO
  / ISR-symbol-preservation quirks
- **resource budget** — 256 KB flash + 64 KB SRAM is normal; failure
  mode is silent (link succeeds, runtime overflows stack, hardfaults)

Off-the-shelf benches don't touch any of this. HumanEval+ asks "write
a function," SWE-bench "patch this repo," LiveCodeBench "solve this
puzzle," MBPP "write this snippet." None of them measure whether the
candidate can put a GPIO into push-pull, mask a USART overrun flag
in an ISR, set up a circular DMA on half-buffer IRQ, or write a
linker script whose `.bss` is correctly zeroed before `main`.

The recipe (`docs/code-llm.md §WHY` + `§STRUCT firmware-native +
hexa-firmware`) commits to firmware as a first-class surface for the
`code` verb. **This spec is what makes that commitment falsifiable.**

**Core falsifiable claim.** If the trained `code` verb cannot pass
firmware-eval at ≥ 50% on Cortex-M, the "firmware-native LLM" thesis
is empirically falsified for v1.0.0. The 50% bar is deliberately
below hexa-eval's 80% and 5-NL's 70% — firmware is harder, the
corpus is smaller, and `firmware-native` is itself a new stage in
v0.1.x.

## S2 COMPARE — vs existing firmware sample corpora + benches

There is no firmware-fidelity benchmark at LLM scale. The closest
artifacts are **sample trees** maintained by RTOS/SDK vendors as
documentation, not as graded benches:

```
+--------------------------------------------------------------------+
|  [Firmware-fidelity axis]                                          |
+--------------------------------------------------------------------+
|  HumanEval+ / SWE / LCB  #........................  zero           |
|  MBED FRDM samples       ########.................  copy-paste*    |
|  Zephyr samples          ##########...............  copy-paste*    |
|  Pico SDK examples       ########.................  copy-paste*    |
|  ESP-IDF examples        ##########...............  copy-paste*    |
|  firmware-eval (this)    ##################........ graded synth   |
+--------------------------------------------------------------------+
|  [Coverage of firmware idioms — per task family]                   |
+--------------------------------------------------------------------+
|  vendor samples          ########.................  per-board only |
|  firmware-eval T1..T3    ##########...............  init+IRQ+DMA   |
|  firmware-eval T4..T5    ###############..........  +linker +size  |
|  firmware-eval T6..T7    ##################........  +RTOS +boot   |
|  firmware-eval T8..T9    ##################........  +target +tc   |
+--------------------------------------------------------------------+
|  [Cross-target parity (Cortex-M / RV32 / Xtensa-ESP32)]            |
+--------------------------------------------------------------------+
|  vendor samples          ########.................  per-vendor lock|
|  firmware-eval           ##################........ 3-target shape |
+--------------------------------------------------------------------+
```

\*Vendor sample trees are **didactic**, not graded. A model that
memorises Zephyr `samples/basic/blinky` scores 100% on "reproduce
blinky" — uninformative. firmware-eval inputs are held-out per-task
and emulator-verified.

**firmware-eval's niche.** Complementary to vendor samples (reference
patterns) and to public code benches (general synthesis). The `code`
verb is expected to pass HumanEval+ ≥ DeepSeek-Coder-V2-7B (recipe
§EVOLVE row 1) **and** firmware-eval ≥ 50% on Cortex-M — a model
that passes one but not the other fails gate ⑥.

## S3 REQUIRES — prerequisites

| prerequisite                                              | source / location                                                                          | check               |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------- |
| `arm-none-eabi-gcc` toolchain                             | gcc-arm-embedded distribution (GPL — used as tool, not ingested)                           | binary on $PATH     |
| `arm-none-eabi-binutils` (`ld`, `objdump`, `size`)        | same distribution                                                                          | binary on $PATH     |
| `clang --target=thumbv7em-none-eabi`                      | LLVM 18+ (Apache-2 with LLVM exception)                                                    | binary on $PATH     |
| `riscv32-unknown-elf-gcc` toolchain                       | riscv-collab/riscv-gnu-toolchain (GPL — tool)                                              | binary on $PATH     |
| `xtensa-esp32-elf-gcc` toolchain                          | Espressif crosstool-NG (GPL — tool)                                                        | binary on $PATH     |
| QEMU ≥ 8.0 (ARM + RISC-V system-mode + `xtensa-esp32`)    | qemu.org (GPL-2 — tool)                                                                    | `qemu-system-arm --version` |
| Renode ≥ 1.14                                             | renode.io (MIT)                                                                            | binary on $PATH     |
| `probe-rs` (CMSIS-DAP / J-Link host)                      | probe-rs.org (MIT/Apache-2) — Mk.III hardware tier                                         | binary on $PATH     |
| License-clean RTOS corpus mirror                          | Zephyr (Apache-2) / FreeRTOS (MIT) / NuttX (Apache-2) / Mbed (Apache-2) / Embassy (MIT-Apache-2) / Tock (MIT-Apache-2) / ESP-IDF (Apache-2 most) / Pi Pico SDK (BSD-3) / ARM CMSIS (Apache-2) | per `firmware-native` row in [`code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset) |
| In-house hexa compiler (`hexa cc`) with target stub       | [`~/core/hexa-lang/SPEC.md §18`](../../hexa-lang/SPEC.md) — target gate `--target=*-none-*` | exit-0 on fixtures  |
| hexa-lang `stdlib/{core,alloc,hal,embedded,mcu}` partitioning | hexa SPEC §18 Option C — `stdlib/host` reject set vs `stdlib/core+alloc+hal+embedded+mcu` allow set | dependency-direction lint green |
| Datasheet-excerpt corpus (license-clean)                  | CMSIS device headers (Apache-2); permissive vendor app-notes; RISC-V CC-BY ISA spec; ESP32 TRM quote-only (D-020) | per-row audit |

**No GPL / vendor-EULA text in the gold answers.** Toolchains may be
GPL because forge uses them as **tools** (output is non-derivative),
but the **task prose** and **gold code** must be license-compatible
with the Apache-2 OR MIT forge license. ARM TRM text is referenced
by section number only, never quoted.

**Stage ordering.** `firmware-eval` runs only **after** `hexa cc`
compiles each candidate output for at least T8 (target gate); for
T1-T7/T9 the candidate produces C or hexa, and the appropriate
cross-compiler is the gate. `firmware-eval` is independent of
`hexa-eval` (the two run in parallel and aggregate separately;
overlap is intentional on the target-gate axis).

**No upstream pollution.** Per the `firmware-native` stage filter in
[`code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset) and
[`plan-domain-coverage.md §4`](plan-domain-coverage.md#4-firmware-coverage-post-specmd-finding),
firmware-eval task prose is tagged `bench-text` and excluded from
the training corpus to prevent benchmark contamination.

## S4 STRUCT — task taxonomy

9 task families, ~600 total. Each task ties to a specific firmware
idiom that vendor samples document but no public bench grades.

### S4.1 Task family table

| ID  | family                          | count | anchor (recipe / SPEC)                       | what it measures                                                                | gold-format               |
| --- | ------------------------------- | ----- | -------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------- |
| T1  | peripheral init                 | ~100  | CMSIS / Zephyr drivers / Pico SDK            | datasheet excerpt → CMSIS-conformant init code (GPIO/UART/SPI/I2C/ADC/PWM/Timer/RTC) | emulator side-effect      |
| T2  | IRQ handler synthesis           | ~80   | NVIC / vector tables                         | interrupt-source spec → handler + vector entry + NVIC enable; correct `volatile` | emulator IRQ fire         |
| T3  | DMA setup                       | ~50   | DMA controller manuals                       | peripheral↔memory / scatter-gather; half/full interrupt semantics               | emulator transfer trace   |
| T4  | linker-script literacy          | ~80   | SoC memory map → `.ld`                       | section placement + alignment + reset vector + heap/stack layout                | `ld` + `objdump` parity   |
| T5  | memory-fit                      | ~50   | SRAM/FLASH budget                            | functional spec under budget; FAIL on overflow                                  | `arm-none-eabi-size` ≤ budget |
| T6  | RTOS patterns                   | ~80   | FreeRTOS / Zephyr / NuttX API canon          | task / queue / mutex / semaphore / event-group; no priority-inversion smell      | API-pattern match         |
| T7  | boot sequence                   | ~30   | Reset → SystemInit → main + CRT init         | per-target reset path; `.bss` zeroed, `.data` initialised before `main`         | emulator entry trace      |
| T8  | hexa target gate                | ~30   | [`hexa-lang SPEC §18.2`](../../hexa-lang/SPEC.md) | `--target=thumbv7em-none-eabihf` source → identify host-stdlib import rejection | `HX[CCCC]` codegen-family |
| T9  | cross-toolchain build           | ~100  | Make / CMake / west / idf.py / cargo-probe   | project → working build setup for the target                                    | dry-run build exit-0      |
|     | **total**                       | **~600** |                                           |                                                                                 |                           |

Math check: 100 + 80 + 50 + 80 + 50 + 80 + 30 + 30 + 100 = **600**. ✓

### S4.2 Per-family detail

**T1 — peripheral init (~100).** Input: CMSIS-style register-map
excerpt + one-line behaviour spec (e.g. "init USART2 at 115200 8N1,
RX-IRQ on"). Output: CMSIS-conformant C or hexa-`stdlib/hal` code.
Pass: emulator boot → peripheral observed in expected state.
Peripheral mix: GPIO 25 / UART 20 / SPI 15 / I2C 15 / ADC 10 / PWM 7
/ Timer 5 / RTC 3.

**T2 — IRQ handler synthesis (~80).** Input: an IRQ-source spec
(line, priority, payload). Output: handler + vector-table entry +
`NVIC_EnableIRQ`, with correct `volatile` placement on shared state.
Pass: emulator fires the source, handler drains it, head/tail
pointers update, no data race on the emulator's race probe.

**T3 — DMA setup (~50).** Input: a transfer spec (circular /
linked-list / scatter-gather; half + complete IRQ semantics).
Output: DMA init + handlers. Pass: emulator pumps a known stream;
half-IRQ + complete-IRQ fire at expected offsets; all bytes captured
in order. Mix: M2P 15 / P2M 20 / M2M 10 / scatter-gather 5.

**T4 — linker-script literacy (~80).** Input: an SoC memory map
(flash + SRAM bases/sizes, stack location, vector-table constraint).
Output: GNU `ld` script with required sections + `PROVIDE` symbols
(`_estack`, `_sdata`, `_edata`, `_sbss`, `_ebss`, `_end`). Pass:
`arm-none-eabi-ld` exit-0 + `objdump -h` shows expected VMA/LMA per
section. SoC mix: STM32 25 / NXP 15 / Nordic 10 / Pi Pico 10 /
generic Cortex-M 10 / RV32 5 / ESP32 5.

**T5 — memory-fit (~50).** Input: a functional spec + hard budget
(FLASH ≤ X KB, SRAM ≤ Y KB). Output: complete implementation. Pass:
`arm-none-eabi-size -A` reports `.text + .rodata ≤ FLASH` and
`.data + .bss + stack-reserve ≤ SRAM`. **Hard fail on overflow** (1-
byte over = fail; mirrors real flash-fit semantics). Budget tier:
tight 20 / medium 20 / loose 10.

**T6 — RTOS patterns (~80).** Input: a concurrency spec + RTOS
choice (FreeRTOS 35 / Zephyr 35 / NuttX 10 + hexa-`stdlib/embedded`
task API 10). Output: the task / queue / mutex / semaphore /
event-group call sequence. Pass: pattern match on API sequence
**plus** absence of priority-inversion smell (mutex held by low-prio
under high-prio wait without priority-inheritance enabled).

**T7 — boot sequence (~30).** Input: target triple + memory map.
Output: Reset_Handler + SystemInit + CRT0 init (copy `.data`
LMA→VMA, zero `.bss`, optional `__libc_init_array`, branch to
`main`). Pass: emulator trace at `main` entry → `.bss` zeroed,
`.data` populated, SP = `_estack`. Mix: Cortex-M 15 / RV32 8 /
Xtensa-ESP32 7.

**T8 — hexa target gate (~30).** Input: hexa source under
`--target=thumbv7em-none-eabihf` (or RV32 / Xtensa variant) that
imports one or more host-stdlib modules (`stdlib/{net,http,fs,
process,json,threading,asyncio,…}`) per
[`hexa SPEC §18.2`](../../hexa-lang/SPEC.md). Output: REJECT + the
`HX[CCCC]` codegen-family code. Pass: rejection correct AND HX code
in correct family. Intentionally overlaps `hexa-eval` T7 (stdlib
direction) — same D-021 canon, two independent verification surfaces.

**T9 — cross-toolchain build (~100).** Input: project skeleton +
target SoC + build-system choice. Output: complete build config —
`Makefile` / `CMakeLists.txt` / `west.yml` / `idf.py` `CMakeLists.txt`
/ `Cargo.toml + .cargo/config.toml`. Pass: dry-run build exit-0 +
expected artifact path in the plan. Mix: Make 25 / CMake 30 / west
15 / idf.py 15 / cargo + probe-rs 15.

### S4.3 Hardness distribution

Per-family hardness encoded as `easy / medium / hard` so the
aggregate ≥ 50% bar is meaningful regardless of which families
saturate first:

```
T1:  easy 40% / med 40% / hard 20%   -- GPIO easy, ADC/PWM/RTC harder
T2:  easy 30% / med 50% / hard 20%   -- single-source easy, nested IRQ hard
T3:  easy 20% / med 50% / hard 30%   -- scatter-gather + race-free hard
T4:  easy 30% / med 40% / hard 30%   -- single section easy, full SoC hard
T5:  easy 30% / med 40% / hard 30%   -- tight-budget tier intrinsically hard
T6:  easy 30% / med 50% / hard 20%   -- task/queue easy, prio-inversion hard
T7:  easy 30% / med 50% / hard 20%   -- Cortex-M easy, ESP32 multi-core hard
T8:  easy 60% / med 30% / hard 10%   -- mostly binary; hard tier = edge cases
T9:  easy 30% / med 50% / hard 20%   -- Make easy, west/idf.py multi-component hard
```

A candidate that passes ≥ 50% **overall on Cortex-M** but fails any
single family's `hard` tier completely is flagged for review (the
50% bar is the gate; the per-family hard-tier floor is **diagnostic**,
not blocking).

## S5 FLOW — generation + scoring discipline

```
[1] Task authoring     --> [2] Gold-output freeze --> [3] Hash-pin
        |                       |                       |
        v                       v                       v
   mined from RTOS         emulator/linker          target triples +
   sample trees +          self-pass on gold        toolchain SHAs +
   datasheet excerpts                               task hash
        |                       |                       |
        +-----------+-----------+-----------+-----------+
                                |
                                v
                  [4] Candidate response  -->  [5] Score
                                |                |
                                v                v
                       cross-compile           per-family scorer
                       (gcc / clang / hexa cc) emulator side-effect /
                       link (arm-none-eabi-ld) size / API match /
                       emulate (QEMU/Renode)   HX-code / dry-run
                                |                |
                                +-------+--------+
                                        |
                                        v
                          [6] outbox/hexa-codex/quality_scale/  (aggregate)
                          [7] outbox/hexa-codex/eval/           (methodology)
                          [8] outbox/hexa-codex/deploy/         (hw-tier recipes)
```

### S5.1 Authoring discipline (D-013 enforced)

**No LLM-judge synthesis for gold output.** All gold answers are:
- hand-authored by a firmware maintainer (or recruited contributor
  with verified RTOS PR history), OR
- mined from license-clean RTOS sample trees (Zephyr `samples/`,
  FreeRTOS `Demo/`, Pi Pico SDK examples, ESP-IDF examples,
  Embassy/Tock examples) with minimal adaptation, OR
- generated by a **deterministic** transformer (CMSIS-template +
  register-map AST builder) — never by a downstream LLM.

This matches the rule applied in
[`spec-hexa-eval.md §S5.1`](spec-hexa-eval.md) — Shumailov 2024
model-collapse risk applies to bench authoring as much as to DPO
scoring.

### S5.2 Scoring algorithm (per-task, summary form)

```
score(task, candidate):
    emit = candidate(task.input)
    match task.family:
      T1|T2|T3|T7: img = cross_compile(emit, target, tc); if FAIL→COMPILE_FAIL
                   trace = emulate(img, recipe, duration_ms)
                   return assert_side_effect(trace, task.expected)
      T4:          ld = arm_none_eabi_ld(test_obj, emit); if FAIL→LINKER_FAIL
                   return objdump_h(ld.elf) == task.expected_layout
      T5:          img = cross_compile(...); sz = size -A(img)
                   return sz.flash ≤ FLASH_budget AND sz.sram ≤ SRAM_budget
      T6:          return rtos_api_pattern_match(emit, gold, no_prio_inv=True)
      T8:          (dec, hx) = hexa_cc(emit, --target=…)
                   return dec == REJECT AND hx in HX_CODEGEN_FAMILY
      T9:          return dry_run_build(emit, build_system) == OK
    tally per family + aggregate per target
```

### S5.3 Determinism + reproducibility

- Per-task pins: `task_id` + `target_triple` + `toolchain_sha` +
  `qemu_or_renode_recipe_hash` + `gold_hash`.
- Runner-config pins: toolchain SHAs (gcc-arm-embedded, clang,
  riscv-gnu, xtensa-esp32), QEMU + Renode versions, `hexa cc` SHA,
  SPEC.md hash, task-set hash. Any drift → **new `run_id`**, no
  in-place re-grade.
- Temperature = 0 primary; `pass@k` (k=5, T=0.7) diagnostic only.
- Emulator non-determinism mitigation: QEMU `-icount shift=auto`;
  Renode deterministic-time mode for race-sensitive T2/T3.

## S6 EVOLVE — Mk.I → Mk.V progression

Mirrors hexa-codex `eval/ai-eval-pipeline.md §S6 EVOLVE` 5-stage shape.

- **Mk.I (1 month) — T1 + T2 only, single target (Cortex-M4F via
  QEMU `mps2-an386` or `lm3s6965evb`).** ~180 tasks (100 T1 + 80
  T2). Scoring: maintainer runs `arm-none-eabi-gcc` + `qemu-system-arm`
  and tallies. No multi-target orchestration. Goal: establish whether
  the bench discriminates at all between an untrained base and a
  forge-finetuned candidate with the `firmware-native` stage active.
  **Gate at Mk.I: discrimination ≥ 15pp between base and SFT-bias-
  only candidate on T1.**

- **Mk.II (2 months) — full T1-T6 + T9, QEMU-only, Cortex-M
  primary.** ~540 tasks live (T7 + T8 deferred — T8 requires the
  hexa target-gate compiler stub, which is gated on `hexa-lang` F3
  per SPEC.md §18.5 "Decision Log"). `tool/run_firmware_eval.py`
  (S9) emits JSON per run with per-target and per-family breakdowns.
  **Gate: aggregate ≥ 35% on Cortex-M on SFT-bias-only candidate**
  (Mk.II is calibration, not release).

- **Mk.III (3 months) — full T1-T9 across 3 targets + Renode
  integration.** T7 (boot) and T8 (hexa target gate) come online
  once `hexa cc` target stub lands. Renode added for boards QEMU
  doesn't model well (Pi Pico RP2040, ESP32 dual-core). Adversarial
  perturbation: register-map permutation (T1), IRQ-priority shuffle
  (T2), memory-map relocation (T4), budget-tightening (T5). Gold
  task set remains pinned at Mk.II baseline. **Gate: adversarial
  drop ≤ 15pp from base aggregate on Cortex-M.**

- **Mk.IV (4 months) — hardware-in-the-loop CI integration.**
  Physical hardware: Pi Pico (RP2040) + STM32 Discovery (Cortex-M4F)
  + ESP32 DevKit added to the runner via `probe-rs` and `idf.py
  flash --monitor`. Per-PR canary on `forge` weight changes uses
  QEMU only (~60 tasks); tag-pushes trigger full hardware run.
  Output routes per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md).
  **Gate: aggregate ≥ 50% on Cortex-M + secondary targets ≥ 35% +
  3 consecutive CI runs on RC weights ⇒ v1.0.0 release-eligible.**

- **Mk.V (long-term) — industry-standard + contamination quarantine
  + per-target rotation.** Task set published with cryptographic
  hash per target. Downstream forks must prove non-leakage (n-gram
  overlap + register-map similarity per
  [`~/core/hexa-codex/eval/ai-eval-pipeline.md §S7.9`](../../hexa-codex/eval/ai-eval-pipeline.md)).
  Task rotation: T1 / T2 / T9 quarterly (generatable by template
  from new CMSIS device headers); T3 / T4 / T5 / T6 / T7 / T8
  yearly (effort-bound). New SoC families added on a 6-month cadence
  as hexa firmware boards mature.

| Mk    | scope                                                           | pass criterion                                          | unlocks                          |
| ----- | --------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------- |
| Mk.I  | T1 + T2 Cortex-M only (manual)                                  | ≥ 15pp base→SFT discrimination on T1                    | proceed to T3-T9 authoring       |
| Mk.II | T1-T6 + T9 Cortex-M, QEMU                                       | ≥ 35% aggregate on Cortex-M (SFT)                       | wire into CI                     |
| Mk.III | + T7 + T8 (hexa cc stub) + RV32 + Xtensa + adversarial          | adversarial drop ≤ 15pp                                 | publish bench v1                 |
| Mk.IV | + HIL on Pi Pico / STM32 Disco / ESP32 + CI integration         | Cortex-M ≥ 50% + RV32/Xtensa ≥ 35% × 3 consecutive runs | **v1.0.0 forge release**         |
| Mk.V  | + contamination quarantine + per-target rotation                | hash-pinned, leak-audited per target                    | community-standard candidate     |

## S7 VERIFY — acceptance bar + failure semantics

### S7.1 Acceptance arithmetic

- **Aggregate gate (Cortex-M, primary).** `passed_on_cortex_m / 600
  ≥ 0.50` ⇒ release-eligible (this bench alone; other §EVOLVE rows
  must also hold). The bar is computed over **all 9 families** with
  Cortex-M as the target variant; tasks that have no Cortex-M
  variant (e.g. ESP32-specific Xtensa boot in T7) are excluded from
  the Cortex-M denominator.
- **Secondary targets (diagnostic, non-blocking at v1.0.0).** RV32
  aggregate ≥ 35%; Xtensa-ESP32 aggregate ≥ 35%. A model that hits
  Cortex-M ≥ 50% but RV32 < 35% is **flagged** but not blocked at
  v1.0.0 — the recipe's primary firmware tier is Cortex-M (hexa-rtsc,
  hexa-chip per `plan-domain-coverage.md §4`).
- **Per-family floor (diagnostic, non-blocking).** No family below
  25% on Cortex-M. An aggregate dominated by easy families is still
  flagged.
- **T8 floor (blocking).** T8 (hexa target gate) must hit ≥ 90% on
  Cortex-M — this is the `--target=*-none-*` rejection rule from
  D-021 / hexa SPEC §18.2 and is intentionally the same canon as
  hexa-eval T7. Below 90% means the model has not learned the
  stdlib-direction rule and the firmware corpus filter failed.
- **Hard-tier sanity.** Each family's `hard` tier must be > 0% — no
  zeroes. A 0% on hard tier implies hardness mis-calibration, not
  capability.

### S7.2 Per-task scorer detail

Restated from S4 / S5 in scorer-form:

| family | scorer                                              | tool surface                                                 | pass criterion                                                              |
| ------ | --------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| T1     | emulator side-effect probe                          | QEMU / Renode + `read_register`                              | peripheral observed in expected state (GPIO toggle, UART byte stream, etc.) |
| T2     | emulator IRQ-fire probe                             | QEMU / Renode + synthetic IRQ source                         | handler drains source; ring buffer head/tail correct; no data race          |
| T3     | emulator DMA-transfer trace                         | QEMU / Renode (DMA-modelled boards) or Renode-only           | half + complete IRQ fire at expected byte offsets; all bytes captured       |
| T4     | linker pass + section map check                     | `arm-none-eabi-ld` + `arm-none-eabi-objdump -h` + `read_map` | `ld` exit-0; section VMA/LMA match gold                                     |
| T5     | image size measurement                              | `arm-none-eabi-size -A` + `tool/run_size.py`                 | `.text + .rodata ≤ FLASH`; `.data + .bss + stack ≤ SRAM`; **hard fail on overflow** |
| T6     | RTOS API pattern + priority-inversion probe         | regex/AST pattern match + static smell detection             | API call sequence matches gold; no priority-inversion smell                 |
| T7     | emulator trace at `main` entry                      | QEMU `-singlestep` + breakpoint on `main`                    | `.bss` zeroed; `.data` initialised; SP = `_estack`                          |
| T8     | hexa cc target-gate                                 | `hexa cc --target=thumbv7em-none-eabihf` + HX code parse     | REJECT decision + HX code in codegen-family                                 |
| T9     | dry-run build                                       | `make -n` / `cmake --build --dry-run` / `west build --dry-run` / `idf.py build --dry-run` / `cargo build --dry-run` | dry-run exit-0; expected artifact path appears in plan                      |

The four §VERIFY firmware tools from [`docs/code-llm.md §VERIFY`](../docs/code-llm.md#verify--serving-contract)
(`run_size`, `read_map`, `read_disasm`, `read_register`) map onto
this taxonomy: T5 → `run_size`; T4 → `read_map`; T1 / T2 / T7 →
`read_register` (peripheral / SP / `.bss` introspection); `read_disasm`
is used by T2 / T3 for hot-path verification (interrupt prologue
correct, DMA descriptor on a 32-byte boundary).

### S7.3 Failure taxonomy

| failure code          | meaning                                                            | family         |
| --------------------- | ------------------------------------------------------------------ | -------------- |
| `COMPILE_FAIL`        | candidate code didn't cross-compile                                | T1-T3,T5,T7,T9 |
| `LINKER_FAIL`         | linker script rejected by `arm-none-eabi-ld`                       | T4             |
| `LINK_SYMBOL_MISSING` | compile OK but linker can't resolve (e.g. ISR symbol)              | T1-T3,T7       |
| `SIZE_OVERFLOW`       | `size -A` over budget (**hard fail**)                              | T5             |
| `EMULATOR_TIMEOUT`    | QEMU/Renode past `duration_ms` without expected observation        | T1-T3,T7       |
| `SIDE_EFFECT_WRONG`   | peripheral observed in wrong state                                 | T1-T3          |
| `RACE_DETECTED`       | emulator race probe flagged a data race                            | T2-T3          |
| `BOOT_STATE_WRONG`    | `main`-entry trace: non-zero `.bss` or wrong SP                    | T7             |
| `API_PATTERN_MISS`    | RTOS API call sequence didn't match gold                           | T6             |
| `PRIO_INVERSION`      | priority-inversion smell detected (**hard**)                       | T6             |
| `HX_CODE_WRONG`       | REJECT correct but HX code in wrong family                         | T8             |
| `REJECT_MISSING`      | accepted a `firmware/*` host-stdlib import (**blocking** per S7.1) | T8             |
| `BUILD_DRY_FAIL`      | build-system dry-run returned non-zero                             | T9             |
| `PASS`                | all checks green                                                   | all            |

`COMPILE_FAIL` and `SIDE_EFFECT_WRONG` are both fails but
**distinguished** in the report — `COMPILE_FAIL` = "doesn't speak
firmware C / hexa firmware idiom" (Stage 1 / Stage 2 training issue);
`SIDE_EFFECT_WRONG` = "speaks firmware but got the register write
wrong" (Stage 3 DPO / domain-bias issue).

### S7.4 Intent vs surface; non-failures

A refusal on a T1 prompt is **fail** (intent — firmware is in-domain).
A syntax-broken T1 emission is **fail** (surface — `COMPILE_FAIL`).
A false refusal on a T8 accept-case (valid `stdlib/core` import) is
**fail**. Symmetric with [`spec-hexa-eval.md §S7.3`](spec-hexa-eval.md).

**Non-failures:** register-write idiom choice within CMSIS canon
(`((volatile uint32_t *)0x40000000)` vs `USART2->CR1 = …` both pass
if the effect matches); whitespace/comments; toolchain choice on
T1-T7/T9 (toolchain only graded on T9); stack-allocation order
within `.stack` as long as `_estack` is at SRAM top.

## S8 FEEDBACK — upstream channel

Per [`plan-feedback-channel-ops.md §1`](plan-feedback-channel-ops.md),
firmware-eval results route to **three** hexa-codex destinations:

| forge output                                                  | hexa-codex destination                                                                   | PR shape                                                                              | falsifier T4         |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------- |
| Aggregate firmware-eval pass rate per target + per release    | [`hexa-codex/quality_scale`](../../hexa-codex/quality_scale/ai-quality-scale.md)         | cross-cutter: firmware-fidelity axis added to quality table                           | cross-cutter         |
| Per-family failure-distribution + adversarial drop + T4 (linker) empirical | [`hexa-codex/eval`](../../hexa-codex/eval/ai-eval-pipeline.md) §S6 Mk.II / Mk.III | methodology delta — empirical confirmation that emulator-anchored scoring transfers   | meta (wraps F-1..4)  |
| Hardware-tier deployment recipes (Pi Pico / STM32 Disco / ESP32 + flash/probe workflows) | [`hexa-codex/deploy`](../../hexa-codex/deploy/ai-deployment.md) | recipe annex — adds firmware tier alongside M4 / Mac Studio / H100 tiers              | ops input            |

T4 (linker-script literacy) is **novel signal** for hexa-codex —
there is no public empirical baseline on LLM linker-script generation
at scale. The methodology PR to `hexa-codex/eval` documents the
emulator-anchored + linker-anchored scoring pattern as a transferable
template for any future bare-metal benchmarks (e.g. when `hexa-chip`
adds neuromorphic-fabric targets).

**Outbox path** (per `plan-feedback-channel-ops.md §7`):
- `outbox/hexa-codex/quality_scale/<run_id>-firmware-eval.md`
- `outbox/hexa-codex/eval/<run_id>-firmware-eval-methodology.md`
- `outbox/hexa-codex/deploy/<run_id>-firmware-hardware-tier.md`

The emit script (S9 below) writes the PR draft using the template in
`plan-feedback-channel-ops.md §2`.

### S8.1 Contribution to v1.0.0 forge gate

`docs/code-llm.md §VERIFY upstream feedback contract` requires ≥ 5
PRs landed in hexa-codex. firmware-eval contributes **three** of
those by design (quality_scale + eval-methodology + deploy-recipes).
Combined with `hexa-eval` (2 PRs) and `5-NL eval` (up to 5 PRs), the
gate is comfortably over-satisfied from the eval surface alone.

## S9 Tooling

Two scripts (planned) + reliance on the existing tier-tool surface
from [`docs/code-llm.md §VERIFY`](../docs/code-llm.md#verify--serving-contract):

| script                          | reads                                                                          | writes                                                                                  | status  |
| ------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | ------- |
| `tool/run_firmware_eval.py`     | `tests/firmware-eval/tasks/*.toml` + candidate endpoint + toolchain SHAs       | `runs/<id>/firmware-eval.parquet` + per-(target, family) JSON                           | PLANNED |
| `tool/emit_firmware_eval_pr.py` | `runs/<id>/firmware-eval.parquet`                                              | `outbox/hexa-codex/{quality_scale,eval,deploy}/<id>-firmware-*.md`                       | PLANNED |

Existing tier-tools consumed (per `docs/code-llm.md §VERIFY` firmware
tool surface):
- `run_size` — wraps `arm-none-eabi-size -A` for T5 budget check
- `read_map` — parses `arm-none-eabi-ld` `.map` for T4 section placement
- `read_disasm` — wraps `arm-none-eabi-objdump -d` for T2/T3 hot-path
  verification (ISR prologue, DMA descriptor alignment)
- `read_register` — wraps QEMU `monitor` / Renode `peripheral` for
  T1/T2/T7 peripheral + CPU-state introspection

Both new scripts follow the existing `tool/emit_t4.py` shape and the
per-family pattern set by `tool/run_hexa_eval.py` (planned,
[`spec-hexa-eval.md §S9`](spec-hexa-eval.md)) and `tool/run_5nl_eval.py`
(planned, [`spec-five-nl-eval.md §S9`](spec-five-nl-eval.md)). Wiring
matches [`plan-feedback-channel-ops.md §3`](plan-feedback-channel-ops.md)
automation triggers — emit on bench-run-complete.

**Determinism contract.** `SOURCE_DATE_EPOCH` for timestamps; pinned
hashes for toolchain SHAs + QEMU/Renode versions + `hexa cc` SHA +
SPEC.md hash + task-set hash; exit-0 on Cortex-M aggregate ≥ 50%
**and** T8 ≥ 90%; non-zero with structured stderr otherwise.

**Not in scope for v0.1.3.** Actual task TOMLs
(`tests/firmware-eval/tasks/`), gold corpus, QEMU/Renode recipe
scripts, runner impl — land v0.1.3+ after D-007 (base weights)
closes, hexa-lang F3 (target codegen) lands per
[`~/core/hexa-lang/SPEC.md §18`](../../hexa-lang/SPEC.md), and a
candidate model exists to run against.

---

## Open questions (v0.1.2 → v0.1.3 handoff)

- [ ] **D-NEW-H (this spec)** — Should T6 cover the full board set
      (`rtsc`, `chip`, `cern`, `antimatter`, `space`) at Mk.II or
      only the 3 target triples? *Proposed: triples at Mk.II; per-
      board at Mk.IV after `firmware-native` stage matures and
      `firmware/boards/*` absorption settles per
      [`hexa SPEC §18.1`](../../hexa-lang/SPEC.md). Mirrors
      `hexa-eval` open question D-NEW-A.*
- [ ] **D-NEW-I (this spec)** — Hardware-in-the-loop (Mk.IV) board
      set: just Pi Pico + STM32 Disco + ESP32 DevKit, or also Nordic
      nRF52840 + RP2350? *Proposed: 3 boards at Mk.IV (cheapest
      coverage of Cortex-M + RV32 + Xtensa); RP2350 deferred to
      v2.0.0 once Pi Pico 2 firmware-native canon matures.*
- [ ] **D-NEW-J (this spec)** — Renode vs QEMU split for T3 (DMA):
      QEMU's DMA modeling is uneven across boards; Renode models
      DMA more faithfully but is slower. *Proposed: QEMU for
      `lm3s6965evb`/`mps2-an386` DMA-light tasks; Renode for STM32 +
      ESP32 + scatter-gather. Decision pinned in Mk.III task TOMLs.*
- [ ] **D-NEW-K (this spec)** — RV32 secondary bar at v1.0.0: 35%
      diagnostic vs blocking? *Proposed: diagnostic (non-blocking)
      through v1.0.0; promote to blocking at v1.1.0 once
      `firmware/boards/cern` (RISC-V) absorbs into `hexa-firmware`.
      Cortex-M is the only blocking primary at v1.0.0 because that's
      where the hexa-rtsc reference port lives ([`hexa SPEC §18.1`](../../hexa-lang/SPEC.md)).*

Resolved decisions referenced by this spec:
- D-006 (hexa-lang firmware-native) — closed 2026-05-11
- D-013 (no LLM-judge for gold) — closed 2026-05-11
- D-020 (C + firmware §WHY/§STRUCT add) — closed 2026-05-11
- D-021 (hexa fidelity contract — incl. `--target=*-none-*` gate) — closed 2026-05-11

---

## Cross-link

- Recipe SSOT: [`../docs/code-llm.md`](../docs/code-llm.md) §EVOLVE
  firmware rows (acceptance gate ⑥) + §VERIFY firmware tool surface
  (`run_size` / `read_map` / `read_disasm` / `read_register`).
- Sister specs: [`spec-hexa-eval.md`](spec-hexa-eval.md) (gate ③ —
  T7 stdlib-direction mirrors T8 here); [`spec-five-nl-eval.md`](spec-five-nl-eval.md)
  (gate ④).
- Domain matrix: [`plan-domain-coverage.md §4`](plan-domain-coverage.md)
  (firmware coverage: `firmware-native` + `hexa-firmware` stages,
  hardware reference literacy, §EVOLVE additions).
- Decisions ledger: [`plan-decisions-pending.md`](plan-decisions-pending.md)
  (D-006, D-013, D-020, D-021).
- Feedback channel ops: [`plan-feedback-channel-ops.md`](plan-feedback-channel-ops.md)
  (PR routing, template, automation triggers).
- Methodology canon: [`~/core/hexa-codex/eval/ai-eval-pipeline.md`](../../hexa-codex/eval/ai-eval-pipeline.md)
  §S6 EVOLVE Mk.I-Mk.V shape source.
- Hexa SPEC.md: [`~/core/hexa-lang/SPEC.md`](../../hexa-lang/SPEC.md)
  §3 (parallel-dual targets — `thumbv7em-none-eabihf` /
  `riscv32imac-unknown-none-elf` / `xtensa-esp32-none-elf`) + §18
  (Option C `stdlib/{core,alloc,hal,embedded,mcu}` split +
  `firmware/boards/{rtsc,chip,cern,antimatter,space}` absorption +
  §18.2 target-gate `--target=*-none-*` rejection rule that anchors T8).
- Existing tier-tools: `tool/emit_t4.py` (shape source for both new
  scripts), `tool/run_size.py` / `tool/read_map.py` / `tool/read_disasm.py`
  / `tool/read_register.py` (firmware tool surface to be consumed by
  the planned runner).
