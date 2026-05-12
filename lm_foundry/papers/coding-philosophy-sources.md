# coding-philosophy-sources — `code` verb §STRUCT/philosophy corpus

> ## ⚠️ SUPERSEDED — pre-research draft retained for diff history
>
> **This file is the v0.0 draft before web research landed.** The live
> source list lives in tier-specific findings:
>
> - [`tier-a-findings.md`](tier-a-findings.md) — language-native idiom canon (verified)
> - [`tier-b-findings.md`](tier-b-findings.md) — cross-lang engineering principles (license downgrades inside)
> - [`tier-c-findings.md`](tier-c-findings.md) — post-mortem canon (URL corrections inside)
> - [`tier-e-findings.md`](tier-e-findings.md) — anti-corpus (DPO negatives, linter-driven)
> - [`frontend-f1-findings.md`](frontend-f1-findings.md) — frontend frameworks + design systems + state mgmt
> - [`frontend-f2-findings.md`](frontend-f2-findings.md) — CSS + native web platform + build tooling
> - [`frontend-f3-findings.md`](frontend-f3-findings.md) — perf + a11y + AI-native UI + mobile + testing
>
> The roll-up matrix is in [`plan-domain-coverage.md §5`](plan-domain-coverage.md#5-philosophy-stage-post-tier-research-consolidation)
> (philosophy stage) + [`§9`](plan-domain-coverage.md#9-frontend--web-app-coverage) (frontend).
>
> **Key corrections vs this draft** (do not rely on this draft for these):
>
> 1. **Token target re-estimate**: original "~3B tok" was off by ~100×.
>    Raw across A+B+C+F ≈ ~35M; effective ≈ **500M-1B** after ×10
>    canon weight + ×5-10 principle×idiom synth. See `plan-decisions-pending.md` D-017.
> 2. **License downgrades (D-018)**: danluu (no CC license), Worse-is-Better (CC BY-NC-SA), Pragmatic Programmer tips, AWS Builders' Library, Cloudflare blog, GitHub blog, Google SRE Book (NC-ND → use SRE **Workbook** instead, CC BY 4.0).
> 3. **URL corrections (D-019)**: GitHub post-mortems → `github.blog/tag/github-availability-report/`, k8s → `kubernetes/community/.../sig-cluster-lifecycle/postmortems`, AWS PES → `aws.amazon.com/premiumsupport/technology/pes/`.
> 4. **§1 Tier A corrections**: "Zig zen" page does not exist (replaced by `ziglang.org/learn/overview/`); SQL "ANSI rationale notes" row deleted (use Postgres + SQLite docs); **CERT C promoted to full-include** (CC-BY-4.0 + MIT, not quote-only).
> 5. **Tier C license-clarity wins**: **Cloudflare blog** is the only verified `ai-train=yes` robots.txt signal in Tier C.
> 6. **Tier E (D-016)**: StackExchange dump license-in-dispute → middle-path = pre-2024-07 Academic Torrents only.
>
> The draft content below is **historical only** — see findings docs above.
>
> ---
>
> ## (Historical draft v0.0)
>
> **Draft v0.0.** Source list for the `philosophy` stage in
> [`docs/code-llm.md §STRUCT`](../docs/code-llm.md). Target ~3B tok,
> permissive/quotable only, **native-first + canon-first** priors.
> Not a curation — a candidate pool to be filtered.

| field        | value                                                       |
| ------------ | ----------------------------------------------------------- |
| stage        | `philosophy`                                                |
| target size  | ~3B tok ← **superseded: see §superseded banner above**      |
| priors       | native-first · canon-first ← **+ 2026-canon-first added per §VERIFY** |
| license bar  | permissive (MIT/Apache/BSD/CC-BY/CC0) OR official/quotable  |
| status       | SUPERSEDED by tier-{a,b,c,e}-findings + frontend-f{1,2,3}-findings |

---

## §1 Tier A — language-native idiom canon (must-have)

The **native-first** prior is taught here. One block per core lang
(hexa, Python, Rust, TypeScript, Go, C, Zig, SQL — same set as §WHY).

| lang       | source                                              | license      | quotability        |
| ---------- | --------------------------------------------------- | ------------ | ------------------ |
| Python     | PEP-8, PEP-20 (Zen), PEP-257                        | PSF / public | full include       |
| Python     | "Pythonic" rationale notes in stdlib docs           | PSF          | full include       |
| Rust       | Rust API Guidelines (rust-lang/api-guidelines)      | MIT/Apache   | full include       |
| Rust       | The Rust Book + Rustonomicon (public chapters)      | MIT/Apache   | full include       |
| Rust       | rust-clippy lint rationale strings                  | MIT/Apache   | full include       |
| Go         | Effective Go, Go Code Review Comments               | BSD-3        | full include       |
| Go         | Go Proverbs (Pike) — short corpus, high signal      | quotable     | full include       |
| TypeScript | TS Handbook (Do's and Don'ts, Declaration patterns) | Apache-2     | full include       |
| TypeScript | tsconfig `strict` rationale                         | Apache-2     | full include       |
| C          | CERT C Coding Standard public excerpts              | quotable     | partial            |
| C          | Linux kernel `Documentation/process/coding-style.rst` | GPL-2 docs | **quote-only**     |
| Zig        | Zig zen + ziglang docs                              | MIT          | full include       |
| SQL        | PostgreSQL docs style + ANSI rationale notes        | PostgreSQL   | full include       |
| hexa       | hexa-canon `§STYLE`, `§NAMING`, `§DOC` entries      | repo-canon   | full include + ×10 |

**Filter rules:**
- GPL docs → quote/excerpt only, never bulk include (license contamination).
- Vendor blog posts → exclude unless explicitly CC-licensed.
- Translated/secondary summaries → exclude (we want primary canon).

## §2 Tier B — engineering principle canon (cross-lang)

Teaches **why** (design principles, trade-offs) without language lock-in.

- **A Philosophy of Software Design** (Ousterhout) — public lecture
  notes / Stanford CS190 slides ONLY (book itself not redistributable).
- **The Pragmatic Programmer** — public excerpts + tip list only.
- **SOLID / DRY / YAGNI / KISS** — Wikipedia + original Martin/Hunt
  blog posts where CC-licensed.
- **"Worse is Better"** (Gabriel) — full essay, public.
- **"The Cathedral and the Bazaar"** (Raymond) — OPL, full.
- **"Out of the Tar Pit"** (Moseley & Marks) — paper, public PDF.
- **"No Silver Bullet"** (Brooks) — quotable, partial.
- **danluu.com** — most posts CC-BY, full include.

## §3 Tier C — post-mortem canon (operational philosophy)

Teaches recovery, blast-radius reasoning, "measure twice, cut once".

- **AWS Builders' Library** — full essays, AWS-published.
- **Google SRE Book** — official free HTML edition, full include.
- **GitHub status post-mortems** — public, full.
- **Cloudflare blog post-mortems** — public, full.
- **danluu post-mortem roundups** — CC-BY, full.
- **k8s.io postmortem repo** — Apache-2.
- **AWS service event summaries** — public.

**Filter rules:**
- Strip blame/PII before inclusion.
- Pair each post-mortem with the upstream fix commit when available
  (cross-stage signal into `repair`).

## §4 Tier D — hexa-canon (canonical-first prior, weight ×10)

The **canon-first** prior comes from here. Same source as `hexa-native`
stage but tagged differently (philosophy vs mechanics).

- `~/core/canon/proposals/**.md` — every accepted spec.
- `~/core/canon/§*/**` — § skeleton, naming, doc shape canon.
- Every `~/core/hexa-*` repo's `README.md` + `docs/*-llm.md` + `TODO.md`
  — they encode the canon-applied-in-practice pattern.
- This file itself (and `docs/code-llm.md`) once stable.

**Weight:** ×10 in the philosophy mix (matches `hexa-native` mechanics
weighting). Canon trumps generic principle when both apply.

## §5 Tier E — anti-corpus (what to NOT learn from)

Trained against (as negative DPO pairs) — recognise these patterns and
prefer the native/canon alternative:

- StackOverflow "C-style Python" answers (mutable default args, manual
  `range(len(x))` loops, `try/except: pass`).
- Java-ported Rust (factory pattern, `Box<dyn Trait>` everywhere,
  ignoring ownership).
- OOP-ported Go (interface-per-struct, getter/setter chains).
- "Enterprise" pattern catalogs applied to scripting langs.
- LLM-generated tutorials (high pollution risk — exclude entire
  domains: medium.com/<recent-AI-slop-tag>, etc.).

**Sourcing:** mined from public datasets (StackExchange dump, GitHub
issues marked `wontfix: not idiomatic`), then auto-paired with the
idiomatic fix from Tier A.

---

## §6 Sourcing pipeline (research TODOs)

- [ ] **license audit pass** — every Tier A/B source confirmed permissive
      via SPDX header or explicit license file. Quote-only sources tagged.
- [ ] **token count pass** — measure raw token volume per source; target
      ~3B with Tier D weighted ×10 post-dedup.
- [ ] **dedup pass** — near-dup removal across Tier A/B (PEP-8 is quoted
      in many places).
- [ ] **canon-tag schema** — every doc in the mix gets a `canon-tag:
      {native|canon|principle|postmortem|anti}` front-matter field. Used
      downstream for DPO preference weighting.
- [ ] **anti-corpus auto-pairing** — script to take a Tier E negative
      and find its Tier A positive counterpart for DPO pairs.
- [ ] **eval slice** — carve 5% as held-out for the `native-first /
      canon-first` DPO signal evaluation (referenced in
      [`docs/code-llm.md` open Q](../docs/code-llm.md#open-questions-v010)).

## §7 Open questions

- [ ] book content (Ousterhout, Hunt/Thomas) — fair-use excerpts only,
      or skip entirely? Skipping loses signal; including risks DMCA.
- [ ] medium.com / dev.to / hashnode — bulk exclude (LLM-slop risk) or
      filter by author allowlist?
- [ ] non-English idiom canon — Japanese Rust community, Korean Go
      community have native idiom guides. Include? Translate?
- [ ] should `philosophy` stage run **before** `domain-bias` (prior
      shaping) or **after** (style fine-tune)? Likely after, but test.

---

## Cross-link

- Stage definition: [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset)
- Style contract: [`docs/code-llm.md §VERIFY`](../docs/code-llm.md#verify--serving-contract)
- Open questions roll-up: [`docs/code-llm.md` open questions](../docs/code-llm.md#open-questions-v010)
