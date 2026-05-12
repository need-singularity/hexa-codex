# tier-a-findings — Tier A web verification pass

> **Status:** `RESEARCH_FIRST`. Web verification of Tier A "language-native
> idiom canon" sources for the `philosophy` stage of `docs/code-llm.md`.
> Cross-link: [`papers/coding-philosophy-sources.md` §1](./coding-philosophy-sources.md).
> Method: `WebFetch` / `WebSearch` against each candidate. URLs marked
> `UNVERIFIED` could not be confirmed live; new finds marked `★`.

Token-estimate convention: rough order of magnitude. Method noted per row.
Word-to-token ratio assumed ~1.3 tok/word (English prose + code blocks).

---

## Python

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| PEP-8 (style guide) | https://peps.python.org/pep-0008/ | Public domain | ~15K (12K words × 1.3) | full include | "This document has been placed in the public domain." |
| PEP-20 (Zen) | https://peps.python.org/pep-0020/ | Public domain | ~400 (250 words) | full include | Tiny but high-signal; ×10 weight candidate. |
| PEP-257 (docstrings) | https://peps.python.org/pep-0257/ | Public domain | ~2.5K (1.9K words) | full include | Public domain. |
| stdlib "Pythonic" rationale | https://docs.python.org/3/library/ | PSF License v2 + 0BSD (code) | ~1.5M-3M (huge ref) | full include | PSF v2 permits redistribution w/ copyright notice; code examples dual 0BSD. Cherry-pick rationale prose. |
| ★ Python Tutorial (full) | https://docs.python.org/3/tutorial/ | PSF License v2 + 0BSD | ~150K (16 chapters) | full include | Canonical "this is how Python is written" tutorial. |
| ★ Python HOWTOs | https://docs.python.org/3/howto/ | PSF License v2 + 0BSD | ~250K-400K (20+ guides) | full include | functional-programming, enum, descriptors, sorting — direct idiom teaching. |
| ★ itertools recipes section | https://docs.python.org/3/library/itertools.html | PSF License v2 + 0BSD | ~15K | full include | Canonical Pythonic-iteration patterns. |
| ★ Google Python Style Guide | https://google.github.io/styleguide/pyguide.html | CC-BY 3.0 | ~25K (18K words) | full include w/ attribution | Industry-influential supplementary canon. |
| ★ All accepted PEPs index | https://peps.python.org/ | Public domain (per-PEP) | ~10M+ (hundreds of PEPs) | full include | Filter to Informational/Process PEPs; Standards Track PEPs are rationale-rich. |

### decision points

- PSF v2 vs CC-BY: PSF requires copyright-notice retention. Acceptable for bulk-include, but tag rows so downstream packagers preserve notice.
- PEP corpus is huge — pre-filter to design/style PEPs (8, 20, 257, 484, 526, 3107, 621, etc.) or risk drowning Tier A in implementation-detail PEPs.
- `docs.python.org/3/library` is reference, not idiom prose. Use module **intro paragraphs** + **deprecation rationales**, not entire API tables.

---

## Rust

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| Rust API Guidelines | https://rust-lang.github.io/api-guidelines/ | MIT OR Apache-2.0 | ~15K-25K (11 chapters) | full include | Repo: rust-lang/api-guidelines. Confirmed MIT in LICENSE-MIT; Apache pair standard for rust-lang/* repos. |
| The Rust Book | https://doc.rust-lang.org/book/ | MIT OR Apache-2.0 | ~250K-350K (20 chapters + appendices) | full include | Repo rust-lang/book; COPYRIGHT confirms dual. Print edition published by No Starch — text on web is open. |
| Rustonomicon | https://doc.rust-lang.org/nomicon/ | MIT OR Apache-2.0 | ~50K-80K | full include | "Dark arts of unsafe Rust." Confirmed MIT+Apache. Incomplete (per its own warning). |
| rust-clippy lint rationale | https://github.com/rust-lang/rust-clippy | MIT OR Apache-2.0 | ~500K-1M (~600+ lints × ~1K each) | full include | Extract lint-doc strings from `clippy_lints/src/**/*.rs`. Highest-signal "what is non-idiomatic Rust" corpus. |
| ★ The Rust Reference | https://doc.rust-lang.org/reference/ | MIT OR Apache-2.0 | ~200K-300K | full include | rust-lang/reference repo; dual license confirmed. Language spec — more formal than the Book. |
| ★ Rust RFCs (accepted) | https://rust-lang.github.io/rfcs/ | MIT OR Apache-2.0 | ~2M-4M (hundreds of RFCs) | full include | github.com/rust-lang/rfcs; dual MIT/Apache. Each accepted RFC = rationale + alternatives = pure design philosophy. |
| ★ rustc-dev-guide | https://rustc-dev-guide.rust-lang.org/ | MIT OR Apache-2.0 (rust-lang/*) | ~150K-250K | full include | Compiler internals; teaches "how the canon thinks" — valuable for AST-faithful refactor signal. |
| ★ Rust Edition Guide | UNVERIFIED — likely https://doc.rust-lang.org/edition-guide/ | MIT OR Apache-2.0 (assumed) | ~30K-50K | full include | Documents migration rationale across editions. Did not fetch; mark verify-before-use. |

### decision points

- Clippy lint corpus is the single largest Rust signal and is structured (rule + rationale + example) — perfect for DPO negative/positive pairing into Tier E.
- RFCs include rejected/withdrawn ones — filter to **merged** RFCs only.
- The Rust Design FAQ (1.6.0 era) at `doc.rust-lang.org/1.6.0/complement-design-faq.html` exists but is **stale** (2015); include as historical only, do not bulk-train on it.

---

## TypeScript

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| TS Handbook (full) | https://www.typescriptlang.org/docs/handbook/ | CC-BY-4.0 (docs) + MIT (code) | ~200K-300K (50+ sections) | full include w/ attribution | Repo microsoft/TypeScript-Website. Dual: prose CC-BY-4.0, code MIT. Attribution required. |
| Declaration "Do's and Don'ts" | https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html | CC-BY-4.0 | ~2K (1.3K words) | full include | Subset of handbook; canonical "what not to do" file. |
| tsconfig `strict` rationale | https://www.typescriptlang.org/tsconfig | CC-BY-4.0 | ~25K (18K words) | full include | Full TSConfig reference; per-flag rationale. |
| ★ TC39 proposals (finished + active) | https://github.com/tc39/proposals | UNVERIFIED (no LICENSE file in root) | ~500K-1M (1.1K+ commits, hundreds of proposals) | partial — quote-only until license confirmed | Individual proposal repos under tc39/* often have explicit licenses; aggregate index repo doesn't. Per-proposal license check required. |
| ★ TC39 ECMA-262 spec text | UNVERIFIED — https://tc39.es/ecma262/ (ECMA copyright) | ECMA royalty-free policy | ~500K | partial / quote-only | ECMA spec is *readable* but redistribution terms differ from CC/MIT. Treat as quote-only. |
| ★ DefinitelyTyped contribution guide | UNVERIFIED — https://github.com/DefinitelyTyped/DefinitelyTyped (CONTRIBUTING.md) | MIT (repo) | ~5K | full include | Canonical "how to write good `.d.ts`" — pairs with handbook Do's and Don'ts. |

### decision points

- CC-BY-4.0 attribution: every TS-handbook chunk needs source-URL preserved through the data pipeline. Build a `provenance:` front-matter key.
- TC39 proposals: license is **per-proposal repo**, not the index. Auto-scan each repo for LICENSE before inclusion.
- ECMA-262 itself: read-only / quote-only. Bulk training on the spec text would be a license risk.

---

## Go

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| Effective Go | https://go.dev/doc/effective_go | CC-BY-4.0 (docs, per go.dev/copyright) + BSD-3 (code) | ~25K (18K words, ~20 sections) | full include w/ attribution | go.dev confirmed CC-BY-4.0 for site content. |
| Go Code Review Comments | https://go.dev/wiki/CodeReviewComments | CC-BY-4.0 | ~15K (30+ short sections) | full include | Companion to Effective Go; "laundry list" of idiom violations. |
| Go Proverbs | https://go-proverbs.github.io/ | MIT (repo) | ~200 (19 proverbs) | full include | Tiny canon; Pike's talk transcript. Repo go-proverbs/go-proverbs.github.io has MIT license file. |
| ★ Go Language Specification | https://go.dev/ref/spec | CC-BY-4.0 | ~50K (50+ printed pages) | full include | Reference, but rationale-rich (interface methodset, generics constraints). |
| ★ Go FAQ | https://go.dev/doc/faq | CC-BY-4.0 | ~25K-35K | full include | Pure design-philosophy doc; "why X and not Y" answers. |
| ★ Go Blog (official posts) | https://go.dev/blog/all | CC-BY-4.0 | ~500K-1M (200+ posts since 2010) | full include w/ attribution | Pike/Cox/etc essays; high signal. Filter to design/idiom posts. |

### decision points

- All go.dev content is uniformly CC-BY-4.0 — single attribution scheme covers Effective Go + spec + FAQ + blog. Clean.
- The wiki (`go.dev/wiki/*`) license inheritance from go.dev/copyright is *implicit*; confirm before bulk include of CodeReviewComments specifically.

---

## C

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| CERT C Coding Standard | https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard | CC-BY 4.0 (text) + MIT (code examples) | ~500K-800K (hundreds of rules) | full include w/ attribution | Confirmed via web search. Originally listed as "partial / quotable" — **upgrade to full include**. Confluence wiki was 403-blocked on fetch but the SEI public statement is unambiguous. |
| Linux kernel coding-style | https://www.kernel.org/doc/html/latest/process/coding-style.html | GPL-2.0 (kernel docs) | ~11K (8.5K words) | **quote-only** | License contamination risk — only excerpt under fair-use. |
| ★ ISO C99 Rationale (V5.10) | https://www.open-std.org/jtc1/sc22/wg14/www/C99RationaleV5.10.pdf | WG14 publishes free; no explicit reuse license | ~200K (PDF) | quote-only | Document is "available from WG14 for free" but not formally CC/MIT. Treat as quote-only canonical reference. |
| ★ GNU C Coding Standards | UNVERIFIED — https://www.gnu.org/prep/standards/ | GFDL | ~30K-50K | **quote-only** | GFDL is copyleft — same contamination concern as GPL kernel docs. |
| ★ C FAQ (comp.lang.c) | UNVERIFIED — https://c-faq.com/ | Copyright Steve Summit; "free to copy for non-commercial" | ~150K (400+ Qs) | **quote-only** | Permission terms restrict commercial use; quote-only is safe path. |
| ★ OpenBSD style(9) man page | UNVERIFIED — https://man.openbsd.org/style.9 | BSD-3 (OpenBSD docs) | ~5K | full include | Native BSD-style canonical C-style. Verify exact license on the man page. |

### decision points

- CERT C upgrade from "partial" to "full include w/ attribution" is the single biggest license win in Tier A — it's a large, high-quality, CC-BY corpus.
- Kernel + GNU + comp.lang.c FAQ: all quote-only. C's permissively-licensed idiom canon is thinner than Rust/Go/Python — OpenBSD style(9) and CERT C are the load-bearing rows.
- No "C book" equivalent of "The Rust Book" exists permissively — K&R is copyrighted Prentice Hall. Accept the gap.

---

## Zig

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| Zig language reference | https://ziglang.org/documentation/master/ | MIT (Expat) | ~150K-250K (15K-20K lines) | full include | Repo ziglang/zig confirmed MIT. |
| "Zig zen" | UNVERIFIED — **no official `ziglang.org` page exists** | n/a | n/a | n/a | Original list assumed this exists. Web search confirms only a GitHub issue (`ziglang/zig#1567`) and unaffiliated `zenofzig.com`. **Remove from Tier A** or reframe as "Zig design principles extracted from docs." |
| ★ Zig overview ("In-depth Overview") | https://ziglang.org/learn/overview/ | MIT (assumed — repo-canon) | ~25K | full include | Authoritative philosophy doc: "no hidden control flow," etc. |
| ★ "Why Zig When There Is C++/D/Rust?" | https://ziglang.org/learn/why_zig_rust_d_cpp/ | MIT (assumed) | ~3K (2K words) | full include | Direct comparative philosophy. |
| ★ Zig Build System guide | UNVERIFIED — https://ziglang.org/learn/build-system/ | MIT (assumed) | ~15K | full include | Build idiom canon. |
| ★ Zig standard library source comments | https://github.com/ziglang/zig (lib/std/) | MIT | ~200K-500K (doc comments only) | full include | Mine doc-comment strings from stdlib; canonical-idiom-by-example. |

### decision points

- **"Zig zen" entry in the original list is unfounded** — there is no official document by that name. Either delete or replace with the Overview + Why-Zig pair.
- ziglang.org page licenses are not stated per-page; defer to repo (MIT). Confirm with the Zig team if doing a public release.

---

## SQL

| source | URL | license | tokens (est.) | quotability | notes |
| --- | --- | --- | --- | --- | --- |
| PostgreSQL docs | https://www.postgresql.org/docs/current/ | PostgreSQL License (BSD-like, permissive) | ~3M-5M (70+ major sections, hundreds of pages) | full include | Confirmed via `/about/licence/`. Filter to SQL-idiom-bearing chapters (Tutorial, SQL Language, Functions) — skip server-admin chapters. |
| ★ PostgreSQL "Internals" chapters | https://www.postgresql.org/docs/current/internals.html | PostgreSQL License | ~500K | full include | Query planner, MVCC rationale — design-philosophy gold. |
| ★ SQLite "About" + design docs | https://www.sqlite.org/about.html (+ docindex) | Public domain | ~200K-400K | full include | Confirmed public-domain via copyright.html. Includes "When To Use SQLite," "How SQLite Is Tested," "The WAL" — high-signal philosophy docs. |
| ★ SQLite Lang Reference | UNVERIFIED — https://www.sqlite.org/lang.html | Public domain | ~150K | full include | Full SQL-dialect reference. |
| ANSI SQL rationale notes | UNVERIFIED — no public ISO SQL rationale doc | ISO (copyrighted) | n/a | quote-only | ISO SQL standards are not freely redistributable. **Remove this row from Tier A** unless we mean Postgres-as-proxy. |
| ★ MySQL / MariaDB docs | UNVERIFIED — license per page; MySQL docs are CC-BY (some) but Oracle-controlled | mixed | n/a | quote-only (default) | Skip unless individual-page license confirmed. Postgres + SQLite cover SQL idiom canon adequately. |

### decision points

- The original list says "ANSI rationale notes" — there is no freely-licensed ANSI/ISO SQL rationale document equivalent to C99-Rationale. **Drop the row.**
- Postgres + SQLite together give us a permissive SQL corpus larger than any other language in Tier A. Risk: SQL-dialect skew toward these two engines. Acceptable for native-first prior since we *want* dialect-specific idiom.

---

## Cross-cutting issues

| issue | affects | resolution proposal |
| --- | --- | --- |
| Attribution-required licenses (CC-BY-*, PSF, PostgreSQL) need per-chunk provenance | Python, TS, Go, C (CERT), Postgres | Add `provenance:` front-matter to every training example; pipeline must not strip it. |
| Quote-only sources (GPL kernel, GFDL GNU, ISO docs, Oracle MySQL) cannot be bulk-included | C, SQL | Build a separate "quote-only excerpts" sub-corpus (≤ ~10% of a doc per fair-use heuristic); train as small-volume signal, not bulk. |
| "Zig zen" does not exist as an official page | Zig | Replace with `learn/overview/` + `learn/why_zig_rust_d_cpp/`. Update `papers/coding-philosophy-sources.md`. |
| `tc39/proposals` index repo has no root LICENSE; per-proposal repos vary | TypeScript | Auto-scan each tc39/* proposal repo for LICENSE before inclusion; default-exclude on miss. |
| go.dev wiki license inheritance is implicit, not stated | Go (CodeReviewComments) | Email go-doc team or accept implicit CC-BY-4.0 via parent-domain footer. |
| PEP corpus is too large if bulk-included | Python | Pre-filter to design/style/process PEPs; skip Standards Track API PEPs unless they include rationale prose. |
| Translated/non-English idiom canon (open Q in source file §7) | all | Out of scope for v0.0 pass; revisit after English Tier A is locked. |
| LLM-generated tutorial pollution risk | all (esp. Python, JS/TS) | Strict allowlist of canonical domains (peps.python.org, doc.rust-lang.org, go.dev, ziglang.org, postgresql.org, sqlite.org, kernel.org, sei.cmu.edu) — no medium.com / dev.to / blog mirrors. |
| Stale official docs (Rust 1.6 Design FAQ) | Rust | Date-gate: any doc that links to a pinned-version URL (e.g. `/1.6.0/`) is historical-only. |

---

## Token roll-up

Order-of-magnitude per-language estimate (full-include rows only, before dedup):

| language | est. tokens (full include) | notes |
| --- | --- | --- |
| Python | ~12M-14M | dominated by HOWTOs + filtered PEP corpus + Google Style Guide |
| Rust | ~3M-6M | clippy lints + RFCs dominate |
| TypeScript | ~250K-350K | handbook + tsconfig only; TC39 proposals license-gated, drop conservative |
| Go | ~600K-1.1M | go.dev blog dominates |
| C | ~500K-800K | CERT C dominates; rest is quote-only |
| Zig | ~400K-800K | stdlib doc-comments dominate |
| SQL | ~4M-6M | Postgres docs dominate |
| **subtotal full-include** | **~21M-30M tokens** | |
| quote-only sub-corpus (kernel, ISO C99, GNU, MySQL etc.) | ~500K-1M (post-excerpt) | trained as small signal, not bulk |
| **Tier A grand total** | **~22M-31M tokens** | |

### Reconciliation with the 3B-tok target

`docs/code-llm.md §STRUCT` says **philosophy = ~3B tok**. Tier A even with
generous inclusion produces **~22M-31M tokens** — roughly **1% of the
target**. The 3B-tok number is dominated by:

- Tier D (hexa-canon, weight ×10 on a small corpus → effective volume)
- Tier B/C (engineering principles + post-mortems) — to be researched next
- **Repetition / weighted oversampling** of Tier A high-signal docs (PEP-20, Go Proverbs, Rust API Guidelines) within the mix

Implication for sourcing: do NOT pad Tier A by lowering the quality bar.
The 3B-tok budget will come from oversampling + Tiers B/C/D, not from
admitting marginal Tier A sources. The native-first prior is taught by
**quality and repetition**, not by raw token volume.

---

## Cross-link

- Stage spec: [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset)
- Source list this report verifies: [`papers/coding-philosophy-sources.md §1`](./coding-philosophy-sources.md)
- Recommended edits to source list:
  - Replace "Zig zen" with `learn/overview/` + `learn/why_zig_rust_d_cpp/`.
  - Drop "ANSI rationale notes" row; promote Postgres + SQLite docs instead.
  - Upgrade CERT C from "partial" to "full include w/ attribution" (CC-BY 4.0 confirmed).
  - Add Rust Reference, Rust RFCs, Clippy lint corpus as explicit rows.
  - Add Google Python Style Guide, Python HOWTOs, Python Tutorial.
  - Add TC39 proposals with per-proposal license-scan caveat.
