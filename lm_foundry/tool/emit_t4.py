#!/usr/bin/env python3
"""emit_t4.py — render a forge T4 empirical PR draft for hexa-codex.

Stage 0 implementation: Python (stdlib only). Port to hexa-lang when
stage 1 settles per `~/core/hexa-lang/SPEC.md §15`. Spec contract per
`papers/plan-feedback-channel-ops.md` (M-005). Output convention per
`outbox/hexa-codex/README.md`.

USAGE
    python tool/emit_t4.py \\
        --verb train_cost \\
        --run-id 2026-05-15-abc1234 \\
        --input runs/abc1234/ \\
        --model qwen2.5-coder-7b-q5_k_m \\
        --compute "1xH100 SXM5" \\
        --corpus-hash "datasets.toml@a1b2c3d4" \\
        --tokenizer "qwen-base + hexa-ext@e5f6"

The script reads `<input>/loss.parquet` (or `latency.parquet`, etc.,
per verb), aggregates the numbers, and writes
`outbox/hexa-codex/<verb>/<run_id>.md`. The draft is immutable; if
re-emission is required, allocate a new run_id (e.g. append `-r2`).

VERB -> F-CODEX MAPPING (mirrors plan-feedback-channel-ops.md §1)
    train_cost     -> F-CODEX-1 T4 (D-004) — SFT loss-vs-FLOP curve
    infer_cost     -> F-CODEX-2 T4 (D-005) — latency + KV-cache profile
    quality_scale  -> cross-cutter — HumanEval+/hexa-eval/5-NL aggregate
    safety         -> F-CODEX-3 T4 input — refusal matrix
    alignment      -> F-CODEX-3 T4 — HELM-Core 12-axis
    adversarial    -> F-CODEX-3 stress — red-team failure modes
    interpret      -> F-CODEX-4 T4 analog — tree-sitter idiom audit
    rlhf           -> substrate — DPO yield + judge quality
    eval           -> meta — Mk progression refinements
    agent_serving  -> F-CODEX-2 SLO input — tool-use schema iter
    deploy         -> ops — hardware-tier recipes
"""
from __future__ import annotations

# NOTE: a sibling `tool/tokenize.py` shadows the stdlib `tokenize` module
# when ANY tool in `tool/` is launched as a script (Python prepends the
# script's directory to sys.path). The shadow propagates through
# `dataclasses` → `inspect` → `linecache` → `tokenize` and crashes import.
# Prune the script directory before any other imports.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Optional


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


VERB_FALSIFIER = {
    "train_cost":    ("F-CODEX-1", "T4 (D-004)",        "SFT loss-vs-FLOP curve"),
    "infer_cost":    ("F-CODEX-2", "T4 (D-005)",        "latency + KV-cache profile"),
    "quality_scale": ("F-CODEX-1/2", "cross-cutter",    "HumanEval+ / hexa-eval / 5-NL aggregate"),
    "safety":        ("F-CODEX-3", "T4 input (D-006)",  "5-NL x adversarial refusal matrix"),
    "alignment":     ("F-CODEX-3", "T4 (D-006)",        "HELM-Core 12-axis composite"),
    "adversarial":   ("F-CODEX-3", "stress input",      "red-team failure modes"),
    "interpret":     ("F-CODEX-4", "T4 analog (D-007)", "tree-sitter idiom audit motif count"),
    "rlhf":          (None,        "substrate input",   "DPO pair yield + judge quality"),
    "eval":          (None,        "meta (wraps F-1..4)", "Mk progression refinements"),
    "agent_serving": ("F-CODEX-2", "SLO input",         "tool-use schema iteration"),
    "deploy":        (None,        "ops input",         "hardware-tier deployment recipe"),
}


@dataclass
class T4Draft:
    verb: str
    run_id: str
    forge_commit: str
    model: str
    compute: str
    corpus_hash: str
    tokenizer: str
    measured: dict  # verb-specific numbers
    runtime_wallclock: Optional[str] = None
    seed: Optional[int] = None
    license_tags: Optional[list] = None
    benchmark_sources: Optional[list] = None


def discover_forge_commit() -> str:
    """Return the current forge git SHA (short) or '<unknown>' if not a repo."""
    try:
        head_file = REPO_ROOT / ".git" / "HEAD"
        if not head_file.exists():
            return "<unknown>"
        head = head_file.read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[len("ref: ") :]
            ref_file = REPO_ROOT / ".git" / ref
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8").strip()[:10]
        return head[:10] if head else "<unknown>"
    except Exception:
        return "<unknown>"


def load_measured(verb: str, input_path: pathlib.Path) -> dict:
    """Verb-specific measurement loader (STUB — pending SFT/inference runs).

    The shape returned MUST match the §3 template's `## Numbers` table.
    At v0.1.2 (no forge runs yet), this returns a TODO marker plus the
    expected fields for the verb, so the draft is syntactically valid
    and reviewers can see the placeholder.
    """
    expected = {
        "train_cost": ["chinchilla_fit_N", "chinchilla_fit_D", "measured_flops",
                       "measured_loss_curve", "extrapolated_N24_exponent_observed"],
        "infer_cost": ["context_lengths", "tokens_per_sec_per_ctx",
                       "kv_cache_bytes_per_token", "measured_tau_exponent"],
        "quality_scale": ["humaneval_plus_pass1", "hexa_eval_pass", "swe_bench_lite",
                          "live_code_bench", "five_nl_pass_aggregate"],
        "safety": ["off_domain_refusal_rate_en", "off_domain_refusal_rate_ko",
                   "off_domain_refusal_rate_zh", "off_domain_refusal_rate_ru",
                   "off_domain_refusal_rate_ja", "adversarial_refusal_rate"],
        "alignment": ["helm_core_axis_scores_12", "weighted_mean"],
        "adversarial": ["red_team_pass_rate", "categories_covered"],
        "interpret": ["native_idiom_correct_count", "translated_pattern_count",
                      "ratio", "tree_sitter_rule_pack_version"],
        "rlhf": ["dpo_pair_count", "judge_quality_pass_rate", "pair_source_breakdown"],
        "eval": ["mk_handoff_template_version", "delta_from_previous"],
        "agent_serving": ["tool_surface_version", "tool_use_pass_rate"],
        "deploy": ["tier_recipes_count", "verified_targets"],
    }
    fields = expected.get(verb, [])
    if not input_path.exists():
        return {f: "<TODO: pending forge run>" for f in fields}
    # When forge runs exist, parse parquet/json artefacts here.
    # For now stub returns the fields with a sentinel.
    return {f: f"<TODO: parse {input_path}>" for f in fields}


def render_draft(draft: T4Draft) -> str:
    falsifier, t4_role, what = VERB_FALSIFIER.get(
        draft.verb, ("<n/a>", "<n/a>", "<n/a>")
    )

    f_label = f"`{falsifier}`" if falsifier else "(no direct F-CODEX bind)"
    f_status_line = (
        f"- {f_label}: T4 was `PENDING`; now `UNDETERMINED` "
        f"(stub — awaiting real forge run)"
    )

    numbers_rows = "\n".join(
        f"| {k} | {v} | (TODO add ref) |" for k, v in draft.measured.items()
    )

    license_block = (
        "\n".join(f"- {tag}" for tag in (draft.license_tags or []))
        or "- <TODO: list corpus license tags>"
    )
    bench_block = (
        "\n".join(f"- {b}" for b in (draft.benchmark_sources or []))
        or "- <TODO: list benchmark sources with license>"
    )

    seed_line = f"`{draft.seed}`" if draft.seed is not None else "<TODO>"
    runtime_line = draft.runtime_wallclock or "<TODO: HH:MM:SS>"

    return f"""# forge T4 empirical: {draft.verb} — {draft.run_id}

> **Stage 0 stub.** Emitted by `tool/emit_t4.py` at run time;
> measurement fields populated from forge run artefacts. Until SFT /
> inference / eval runs land, this draft holds the **interface shape**
> only — the `<TODO>` markers reveal where real numbers slot in.

## Provenance
- forge run: `{draft.run_id}` (commit SHA: `{draft.forge_commit}`)
- model: `{draft.model}`
- date: `{dt.date.today().isoformat()}`
- compute: `{draft.compute}`
- corpus snapshot: `{draft.corpus_hash}`
- tokenizer: `{draft.tokenizer}`

## What this measures
{what}. Verb: `{draft.verb}` — falsifier target: {f_label} ({t4_role}).
For details, consult the verb spec at
`~/core/hexa-codex/{draft.verb}/ai-{draft.verb.replace("_", "-")}.md`
(authoritative; do NOT inline-copy here per linkage rule).

## Falsifier closure delta
{f_status_line}
- Recipe §3 `closure_pct` impact: <TODO once real numbers land>

## Numbers
| metric | value | reference |
| ------ | ----- | --------- |
{numbers_rows}

## Reproducibility
- script: `<TODO: path to forge run driver>`
- inputs: `<TODO: corpus subset SHA / eval set SHA>`
- runtime: `{runtime_line}`
- determinism: seed = {seed_line}; nondeterminism notes: <TODO>

## Cross-link
- forge-side artifact: `<TODO: runs/{draft.run_id}/...>`
- hexa-codex landing site: `verify/numerics_{draft.verb}_t4_parity.hexa` (new)
- F-CODEX arithmetic floor (T1+T2+T3): already PASS at hexa-codex v1.0.0

## License / attribution
### corpus license tags
{license_block}

### benchmark sources (with license)
{bench_block}

## Validation checklist
- [ ] `hexa-codex verify falsifier-check` still PASS
- [ ] `hexa-codex verify saturation-check` still emits `__HEXA_CODEX_SATURATION_CHECK__ PASS`
- [ ] `hexa-codex verify release-ladder` monotonicity holds
- [ ] new T4 layer's parity verifier landed (`verify/numerics_{draft.verb}_t4_parity.hexa`)
- [ ] CHANGELOG entry in hexa-codex (`[Unreleased]` block)
- [ ] `tool/license_clean_scan.py` against `{draft.corpus_hash}` PASS
- [ ] forge-side commit pinned: `{draft.forge_commit}`

---
*Emitted by `tool/emit_t4.py` (forge stage 0). Spec: `papers/plan-feedback-channel-ops.md`. Outbox discipline: `outbox/hexa-codex/README.md`.*
"""


def write_draft(verb: str, run_id: str, body: str) -> pathlib.Path:
    outbox = REPO_ROOT / "outbox" / "hexa-codex" / verb
    if not outbox.exists():
        raise SystemExit(
            f"ERROR: outbox path missing: {outbox}\n"
            f"       Create it via the layout in outbox/hexa-codex/README.md "
            f"before re-running."
        )
    target = outbox / f"{run_id}.md"
    if target.exists():
        raise SystemExit(
            f"ERROR: outbox draft already exists (write-once discipline): {target}\n"
            f"       Allocate a new run_id (e.g. append `-r2`) and re-emit."
        )
    target.write_text(body, encoding="utf-8")
    return target


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        prog="emit_t4.py",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See `outbox/hexa-codex/README.md` for the routing + verb table.",
    )
    parser.add_argument("--verb", required=True, choices=sorted(VERB_FALSIFIER.keys()),
                        help="target hexa-codex verb (chooses falsifier mapping)")
    parser.add_argument("--run-id", required=True,
                        help="forge run identifier (e.g. 2026-05-15-abc1234)")
    parser.add_argument("--input", required=True, type=pathlib.Path,
                        help="forge run artefact directory or file (stub: may not exist)")
    parser.add_argument("--model", default="<TODO>",
                        help="model identifier (e.g. qwen2.5-coder-7b-q5_k_m)")
    parser.add_argument("--compute", default="<TODO>",
                        help="compute description (e.g. '1xH100 SXM5')")
    parser.add_argument("--corpus-hash", default="<TODO>",
                        help="datasets.toml@<hash> identifier")
    parser.add_argument("--tokenizer", default="<TODO>",
                        help="tokenizer identifier (e.g. 'qwen-base + hexa-ext@<hash>')")
    parser.add_argument("--runtime", default=None,
                        help="wall-clock runtime (HH:MM:SS)")
    parser.add_argument("--seed", type=int, default=None,
                        help="run seed (if deterministic)")
    parser.add_argument("--license-tags", action="append", default=None,
                        help="corpus license tag (repeatable)")
    parser.add_argument("--bench-source", action="append", default=None,
                        help="benchmark source with license (repeatable)")
    parser.add_argument("--stdout", action="store_true",
                        help="print to stdout instead of writing outbox file")
    parser.add_argument("--dry-run", action="store_true",
                        help="render but do not write (preview)")

    args = parser.parse_args(argv)

    draft = T4Draft(
        verb=args.verb,
        run_id=args.run_id,
        forge_commit=discover_forge_commit(),
        model=args.model,
        compute=args.compute,
        corpus_hash=args.corpus_hash,
        tokenizer=args.tokenizer,
        measured=load_measured(args.verb, args.input),
        runtime_wallclock=args.runtime,
        seed=args.seed,
        license_tags=args.license_tags,
        benchmark_sources=args.bench_source,
    )

    body = render_draft(draft)

    if args.stdout or args.dry_run:
        sys.stdout.write(body)
        if args.dry_run:
            sys.stdout.write(
                f"\n--- DRY RUN (would write to outbox/hexa-codex/{args.verb}/{args.run_id}.md) ---\n"
            )
        return 0

    target = write_draft(args.verb, args.run_id, body)
    print(f"__FORGE_T4_EMITTED__ {args.verb} {args.run_id}")
    print(f"draft: {target.relative_to(REPO_ROOT)}")
    return 0


def _self_test() -> int:
    """Inline self-test — runs when invoked with no args."""
    print("emit_t4.py self-test")
    # 1) every verb in VERB_FALSIFIER renders successfully
    for verb in VERB_FALSIFIER:
        draft = T4Draft(
            verb=verb,
            run_id="0000-00-00-selftest",
            forge_commit="deadbeef",
            model="self-test-model",
            compute="self-test-cpu",
            corpus_hash="self-test-corpus@0",
            tokenizer="self-test-tok@0",
            measured=load_measured(verb, pathlib.Path("/nonexistent")),
        )
        body = render_draft(draft)
        if "forge T4 empirical:" not in body:
            print(f"  [FAIL] {verb} — header missing")
            return 1
        if "<TODO" not in body:
            print(f"  [WARN] {verb} — no <TODO> markers found (expected at v0.1.2)")
        print(f"  [PASS] {verb} ({len(body)} bytes)")

    # 2) write-once guard fires when the file exists
    test_outbox = REPO_ROOT / "outbox" / "hexa-codex" / "train_cost"
    if test_outbox.exists():
        existing = list(test_outbox.glob("*.md"))
        if existing:
            try:
                write_draft("train_cost", existing[0].stem, "duplicate body")
                print("  [FAIL] write-once guard did not fire")
                return 1
            except SystemExit:
                print("  [PASS] write-once guard fires on duplicate run_id")

    print("__EMIT_T4_SELFTEST__ PASS")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise SystemExit(_self_test())
    raise SystemExit(main(sys.argv[1:]))
