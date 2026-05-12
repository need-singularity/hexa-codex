# tier-b-findings — `philosophy` corpus, cross-language principle canon

> **Draft v0.0.** Web-research verification pass for
> [`papers/coding-philosophy-sources.md §2 Tier B`](./coding-philosophy-sources.md#2-tier-b--engineering-principle-canon-cross-lang).
> Per-source: canonical URL, license, availability, token estimate,
> quotability verdict. New finds marked ★.
>
> Token estimates are order-of-magnitude (1 word ≈ 1.3 tokens for BPE).
> Where a single number — that's a point estimate. Where a range — actual
> length depends on edition/version available.

---

## A Philosophy of Software Design (Ousterhout)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://web.stanford.edu/~ouster/cgi-bin/aposd.php                 |
| license       | book = copyrighted (Yaknyam Press); free PDF extract only          |
| availability  | 2nd-edition extract PDF (new chapters + Clean Code comparison) free; full book paid |
| tokens        | extract ~15-25k tok; full book ~80-100k tok (NOT redistributable)  |
| quotability   | excerpt-only (fair use) — flag as book content                     |

The author publishes a free 2nd-edition extract PDF containing the new
chapters and the head-to-head with Robert Martin's *Clean Code* — this is
the canonical free Ousterhout text. The book itself is not redistributable.
There's also a public Ousterhout↔Martin debate on GitHub
(`johnousterhout/aposd-vs-clean-code` — high signal). Stanford CS190
lecture slides referenced in our source list are **not** publicly indexed —
UNVERIFIED whether redistributable slides exist.

---

## The Pragmatic Programmer (Hunt & Thomas)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://pragprog.com/tips/                                         |
| license       | "All Rights Reserved" — © Pragmatic Programmers LLC                |
| availability  | 100-tip list public on pragprog.com; full book paid                |
| tokens        | tip list ~2-3k tok; book ~120k tok (NOT redistributable)           |
| quotability   | excerpt-only — tip list is "reproduced with permission" not CC     |

Footer says "Tips excerpted... Reproduced with permission of the publisher."
This is publisher-permissioned reproduction on their own site, **not** a
CC grant. We can quote individual tips as fair-use commentary but cannot
bulk-include. Flag as book.

---

## SOLID / DRY / YAGNI / KISS (acronym canon)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URLs | Wikipedia articles (CC-BY-SA 4.0); Martin's original "PrinciplesOfOod" page on objectmentor.com (defunct, archive.org); Hunt/Thomas DRY in *Pragmatic Programmer* (book) |
| license       | Wikipedia CC-BY-SA; original blog posts mostly all-rights-reserved |
| availability  | Wikipedia full; original Martin posts via archive.org              |
| tokens        | ~5-10k tok per article × 4 ≈ 30k tok                               |
| quotability   | Wikipedia: full-include; original-source quotes: excerpt-only      |

Pull from Wikipedia (clean CC-BY-SA) as canonical principle definitions.
Original blog posts (Martin's `objectmentor.com` archive, Hunt's
`PragmaticTip` series) are not CC — quote-only. **Pair with critique**:
Dan Abramov's "Goodbye, Clean Code" and Hillel Wayne's essays for
balance (see anti-canon section).

---

## "Worse is Better" (Gabriel)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://www.dreamsongs.com/RiseOfWorseIsBetter.html                |
| license       | **CC BY-NC-SA 3.0 US** (site-wide, per dreamsongs.com homepage)    |
| availability  | full essay + Gabriel's later rebuttals ("Is Worse Really Better?", "Worse is Better is Worse") |
| tokens        | core essay ~3k tok; full saga (4 essays) ~12-15k tok               |
| quotability   | **excerpt-only — NC clause blocks bulk training inclusion**        |

The site footer explicitly states CC BY-NC-SA 3.0. The **NC**
(NonCommercial) clause is the blocker — a commercial LLM training mix
arguably violates it. Treat as quote-only or seek explicit permission.
The full Worse-is-Better saga (4 essays where Gabriel debates himself
under a pseudonym) is canonical and tightly written — worth the lawyer-call.

---

## The Cathedral and the Bazaar (Raymond)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | http://www.catb.org/~esr/writings/cathedral-bazaar/cathedral-bazaar/ (TLS cert is broken on the host — use HTTP or archive.org mirror) |
| license       | **Open Publication License v2.0** (no options invoked = permissive) |
| availability  | full essay collection; also First Monday + Internet Archive mirrors |
| tokens        | core essay ~12k tok; full collection (5 essays + appendices) ~50-70k tok |
| quotability   | **full-include** (OPL is permissive enough for redistribution + derivatives) |

OPL v2.0 with no "Option A/B" invocations = freely redistributable and
derivable. Verified via Wikipedia + Raymond's site. Cert error on
`catb.org` is a host config issue, not a content one — use the
Internet Archive mirror (`https://archive.org/details/CathedralAndTheBazaar`)
or First Monday's version.

---

## Out of the Tar Pit (Moseley & Marks)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | http://curtclifton.net/papers/MoseleyMarks06a.pdf                  |
| license       | UNVERIFIED — paper is SPA 2006 conference, no SPDX header          |
| availability  | freely available from multiple academic mirrors (curtclifton, shaffner.us, abilian lab) |
| tokens        | ~25-30k tok (66-page PDF)                                          |
| quotability   | excerpt-only by default — fair-use academic                        |

The paper has no explicit license but is universally redistributed in
academic contexts (mirrored on multiple university sites, an ePUB exists
on GitHub, blog.acolyer.org has a public summary). De-facto public.
Authors' contact: `ben@moseley.name`. Recommend treating as fair-use
academic quotation unless we ping them. PDF text-extraction is non-trivial
(compressed streams) — pre-process via `pdftotext`.

---

## No Silver Bullet (Brooks)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://worrydream.com/refs/Brooks_1986_-_No_Silver_Bullet.pdf (Bret Victor mirror); IEEE original behind paywall |
| license       | © IEEE / Brooks — academic fair-use only                           |
| availability  | full text via university course mirrors + worrydream                |
| tokens        | ~7-10k tok                                                         |
| quotability   | excerpt-only (book chapter / IEEE Computer article)                |

Originally in IEEE Computer, also a chapter in *The Mythical Man-Month*
anniversary edition. Widely circulated in academic contexts but not
CC-licensed. Pair with "No Silver Bullet — Refired" (Brooks's own
follow-up). Fair-use excerpts only.

---

## danluu.com

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://danluu.com/                                                |
| license       | **NO LICENSE STATED** on the public site or `/about/` — original spec assumed CC-BY but this is **unverified** |
| availability  | ~100 public posts (2013-2024) + ~70 Patreon-exclusive               |
| tokens        | ~500-800k tok across the public archive (long-form, dense)         |
| quotability   | **DOWNGRADE TO EXCERPT-ONLY** until license is confirmed           |

**Action required:** the source spec assumed CC-BY but neither the
homepage nor the `/about/` page carries any license statement. The
`danluu-hugo-theme` repo is Apache-2 but that's the *theme*, not the
*content*. Need to either:
1. Email Dan Luu and ask for an explicit license, or
2. Treat as fair-use quote-only (loses bulk-train signal).

Until then **do not bulk-include danluu**. This is the biggest delta from
the original source spec.

---

# ★ Missed sources (new finds)

## ★ "The Humble Programmer" (Dijkstra EWD 340)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD340.html  |
| license       | ACM CACM 1972; UT Austin archive "reproduced with permission"      |
| availability  | full HTML transcription + scanned PDF on UT Austin EWD Archive     |
| tokens        | ~6-8k tok                                                          |
| quotability   | excerpt-only — academic fair use                                   |

Dijkstra's 1972 Turing Award lecture. Foundational "humility" essay.
The entire EWD archive (1300+ manuscripts) is on the UT Austin site
under fair-use terms. Pair with EWD 1036 ("On the cruelty of really
teaching computing science") and EWD 1209 ("The end of computing
science?") for the full Dijkstra principles set.

## ★ "Reflections on Trusting Trust" (Thompson)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://www.cs.cmu.edu/~rdriley/487/papers/Thompson_1984_ReflectionsonTrustingTrust.pdf |
| license       | ACM "educational/personal use only" notice                         |
| availability  | mirrored on dozens of university servers; Internet Archive         |
| tokens        | ~3-4k tok (short)                                                  |
| quotability   | excerpt-only — academic fair use                                   |

Thompson's 1983 Turing Award lecture. Short and canonical. Pair with
Russ Cox's `research.swtch.com/nih` modern re-implementation for the
"how to verify" loop. Essential for the security/trust dimension of
engineering principles.

## ★ "Programming as Theory Building" (Naur)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://pages.cs.wisc.edu/~remzi/Naur.pdf                          |
| license       | originally 1985 essay; mirrored academically; no SPDX              |
| availability  | freely available (Wisconsin, gwern.net mirrors)                    |
| tokens        | ~10-12k tok                                                        |
| quotability   | excerpt-only — academic fair use                                   |

The "theory" framing of programming — why senior engineers carry value
beyond the codebase. High signal for a code-LLM that should encode the
*why* alongside the *what*. Often cited as the antidote to Clean-Code-style
mechanical rules.

## ★ Hoare — "Hints on Programming Language Design" (1973)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://www.cs.yale.edu/flint/cs428/doc/HintsPL.pdf                |
| license       | Stanford TR 1973; no explicit license but widely mirrored          |
| availability  | Yale, Queen's, Grinnell, DTIC mirrors                              |
| tokens        | ~15-20k tok                                                        |
| quotability   | excerpt-only — fair use                                            |

Hoare's principles for *language* design — directly relevant to a
code-LLM's "native idiom" prior. Tells the model why Python, Rust,
and Go look the way they do.

## ★ Stepanov — "Notes on Programming"

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://stepanovpapers.com/notes.pdf                               |
| license       | UNVERIFIED — author-hosted, no SPDX                                |
| availability  | freely downloadable from stepanovpapers.com (author's own domain)  |
| tokens        | ~100k tok (book-length lecture notes)                              |
| quotability   | excerpt-only by default; author-hosted suggests permissive intent  |

Lecture notes from Stepanov's SGI/Adobe teaching. STL-history-adjacent
but the principles (regular types, value semantics, generic programming)
transfer cleanly to Rust/C++/Zig. Worth contacting Stepanov for explicit
license.

## ★ Google Engineering Practices (eng-practices)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://google.github.io/eng-practices/                            |
| license       | **CC-BY 3.0** (confirmed in repo LICENSE file)                     |
| availability  | full code-review guide (reviewer + author perspectives)            |
| tokens        | ~30-40k tok                                                        |
| quotability   | **full-include** — clean CC-BY                                     |

Google's public code-review playbook. Exactly the "why we code this way"
canon the spec calls for. Permissive enough for bulk include. Pair with
Google's style guides (`github.com/google/styleguide`, also CC-BY 3.0)
which the original spec already implicitly covers in Tier A.

## ★ SICP — Structure and Interpretation of Computer Programs (2e)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://sarabander.github.io/sicp/html/ (community HTML) + https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/index.html (MIT-hosted) |
| license       | **CC BY-SA 4.0** (Abelson + Sussman, MIT Press)                    |
| availability  | full book, HTML + PDF, multiple mirrors                            |
| tokens        | ~250-300k tok (full book)                                          |
| quotability   | **full-include** — clean CC-BY-SA                                  |

Re-licensed by Abelson/Sussman/MIT Press in ~2016 under CC-BY-SA 4.0.
Foundational engineering text on abstraction, evaluation, modularity.
JavaScript edition (`sicp.sourceacademy.org/sicpjs.pdf`) is CC-BY-NC-SA
(downgrade). Use the 2nd-edition Scheme original.

## ★ HtDP — How to Design Programs (2e)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://htdp.org/2023-8-14/Book/                                   |
| license       | **CC BY-NC-ND 4.0**                                                |
| availability  | full book online                                                   |
| tokens        | ~200k tok                                                          |
| quotability   | **excerpt-only — ND clause blocks derivatives**                    |

Felleisen/Findler/Flatt/Krishnamurthi — the "design recipe" methodology.
Excellent principle content (design-by-types, refinement steps) but
**ND = no derivatives** means it can't go into a derivative work like a
training mix. Fair-use excerpts only.

## ★ MIT 6.005 — Software Construction

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://web.mit.edu/6.005/www/archive/  (Spring 2016 archive)      |
| license       | **CC BY-NC-SA 4.0** (MIT OpenCourseWare)                           |
| availability  | full reading set: specs, ADTs, testing, concurrency, immutability  |
| tokens        | ~150-200k tok across readings                                      |
| quotability   | **excerpt-only — NC clause blocks commercial training**            |

Modern, well-written engineering principles. NC clause is the blocker
for commercial training but ideal for fair-use excerpting. Replaced by
6.102 in MIT's current curriculum but the 6.005 archive remains the
canonical version.

## ★ Drew DeVault's blog (drewdevault.com)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://drewdevault.com/                                           |
| license       | **CC-BY-SA 2.0** (explicitly stated in site footer)                |
| availability  | ~10 years of posts, system-software focus (Sway, Sourcehut, suckless-adjacent) |
| tokens        | ~300-500k tok                                                      |
| quotability   | **full-include** — clean CC-BY-SA                                  |

Strong opinions, well-written, mostly correct on systems-engineering
principles. Apply some skepticism on community-politics posts but the
*technical* posts are gold. CC-BY-SA 2.0 (slightly outdated — modern
preference is 4.0 but 2.0 is valid).

## ★ Google SRE Book (2 vols)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URL | https://sre.google/sre-book/table-of-contents/ + https://sre.google/workbook/table-of-contents/ |
| license       | **CC BY-NC-ND 4.0**                                                |
| availability  | full HTML, both volumes                                            |
| tokens        | SRE Book ~400-500k tok; Workbook ~300-400k tok                     |
| quotability   | **excerpt-only — ND + NC double-block**                            |

Already in Tier C (post-mortem canon) but the *principles* chapters
(SLO design, error budgets, eliminating toil) belong in philosophy.
ND clause is hard — no derivatives at all. Fair-use excerpting only.
Don't bulk-train; quote for principle definitions.

## ★ Anti-canon: Clean Code critique cluster (for DPO pairs)

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| canonical URLs | https://qntm.org/clean ; Dan Abramov "Goodbye, Clean Code" (overreacted.io); https://bugzmanov.github.io/cleancode-critique/ ; Ousterhout vs Martin GitHub debate |
| license       | mixed — qntm.org and overreacted.io are author copyright           |
| availability  | all freely readable                                                |
| tokens        | ~25-40k tok across the cluster                                     |
| quotability   | excerpt-only — author copyright                                    |

**Critical for anti-canon:** Clean Code is the most-recommended,
most-controversial book in the field. The model needs to see both sides.
qntm's "It's probably time to stop recommending Clean Code" is the
canonical critique. Ousterhout↔Martin GitHub debate is high-signal
because both authors agreed to it publicly. **Pair each critique with
the Clean Code claim it refutes** as a DPO preference pair.

---

# UNVERIFIED / dropped from candidate pool

- **Julia Evans (jvns.ca)** — listed as candidate in original
  source list. Footer is plain copyright, no CC. Drop or quote-only.
- **fasterthanli.me (Amos Wenger)** — license not on homepage; legal
  notice + terms pages exist but content not fetched. UNVERIFIED — treat
  as standard copyright until checked.
- **lethain.com (Will Larson)** — © Will Larson 2026, no license stated.
  `staffeng.com` book content is on the web but not CC. Quote-only.
- **charity.wtf (Charity Majors)** — observability essays widely cited
  but no CC license found in public-facing pages. UNVERIFIED.
- **Cloudflare blog post-mortems** — no license statement on the blog.
  Listed in Tier C of original spec but should be tagged "quote-only"
  not "full include".
- **AWS Builders' Library** — © Amazon, site-terms TOS. Listed in
  Tier C as "AWS-published full essays" but AWS's TOS does NOT grant
  redistribution. Downgrade to **excerpt-only**.
- **GitHub post-mortems** — github.blog posts are © GitHub, no CC.
  Excerpt-only.
- **Stanford CS190 (Ousterhout) slides** — referenced in spec but
  not publicly indexed under a clear license. UNVERIFIED. Suggest
  emailing Ousterhout — he's been generous with the APoSD extract.
- **Increment (Stripe magazine)** — © Stripe, no license. Discontinued
  in 2022. Quote-only.

---

# Inclusion verdict

| source                                       | verdict             | reason                                              |
| -------------------------------------------- | ------------------- | --------------------------------------------------- |
| Cathedral and the Bazaar                     | **include-full**    | OPL v2.0, derivable                                 |
| Google eng-practices ★                       | **include-full**    | CC-BY 3.0, code-review canon                        |
| Google styleguide (Tier A overlap)           | **include-full**    | CC-BY 3.0                                           |
| SICP 2e ★                                    | **include-full**    | CC-BY-SA 4.0, foundational                          |
| Drew DeVault blog ★                          | **include-full**    | CC-BY-SA 2.0, systems principles                    |
| Wikipedia (SOLID/DRY/YAGNI/KISS articles)    | **include-full**    | CC-BY-SA 4.0                                        |
| Hoare "Hints on PL Design" ★                 | **include-excerpt** | no license, but academic fair-use established       |
| Naur "Programming as Theory Building" ★      | **include-excerpt** | academic fair-use                                   |
| Dijkstra EWD340 + EWD archive ★              | **include-excerpt** | academic fair-use, UT Austin permission             |
| Thompson "Trusting Trust" ★                  | **include-excerpt** | academic fair-use                                   |
| Out of the Tar Pit                           | **include-excerpt** | academic fair-use; de-facto public                  |
| No Silver Bullet                             | **include-excerpt** | IEEE; fair-use only                                 |
| Worse is Better (Gabriel saga)               | **include-excerpt** | CC BY-NC-SA 3.0 — NC blocks bulk                    |
| MIT 6.005 ★                                  | **include-excerpt** | CC BY-NC-SA 4.0 — NC blocks bulk                    |
| HtDP 2e ★                                    | **include-excerpt** | CC BY-NC-ND 4.0 — ND blocks derivatives             |
| Google SRE Book + Workbook ★                 | **include-excerpt** | CC BY-NC-ND 4.0                                     |
| Pragmatic Programmer (tips)                  | **include-excerpt** | publisher-permissioned only, not CC                 |
| Philosophy of Software Design (extract)      | **include-excerpt** | free extract only; book is paid                     |
| Stepanov "Notes on Programming" ★            | **include-excerpt** | author-hosted, license unverified                   |
| Clean Code critique cluster ★                | **include-excerpt** | fair-use commentary; pair as DPO contrast           |
| danluu.com                                   | **EXCERPT-ONLY (DOWNGRADE)** | no license stated — spec was wrong       |
| Cloudflare/GitHub/AWS blog post-mortems      | **include-excerpt** | proprietary; spec needs correction                  |
| jvns.ca, fasterthanli.me, lethain.com        | **exclude (default)** | no CC; quote-only if specifically warranted       |
| charity.wtf, Increment                       | **exclude (default)** | no CC found                                       |
| Beautiful Code (O'Reilly anthology)          | **exclude**         | © O'Reilly, no public chapters with license         |
| Stanford CS190 slides                        | **UNVERIFIED**      | spec mentions them; need direct contact w/ Ousterhout |

---

# Token roll-up

| bucket                                  | tokens (rough)   | mix share at ~3B target |
| --------------------------------------- | ---------------- | ----------------------- |
| **Full-include (permissive bulk)**      | ~1.0-1.3M tok    | tiny — needs dedup-aware repetition or principle-expansion synthesis |
| → SICP 2e                               | ~280k            |                         |
| → Cathedral & Bazaar (full collection)  | ~60k             |                         |
| → Google eng-practices                  | ~35k             |                         |
| → Drew DeVault blog                     | ~400k            |                         |
| → Wikipedia principle articles          | ~30k             |                         |
| → Google styleguide (Tier A overlap)    | ~200k            |                         |
| **Excerpt-only (NC/ND/fair-use)**       | ~1.5-2.0M tok    | the bulk of "philosophy" signal; must be **excerpted**, not bulk-included |
| → Pragmatic Programmer tips             | ~3k              |                         |
| → APoSD extract                         | ~20k             |                         |
| → Worse is Better saga                  | ~15k             |                         |
| → Tar Pit                               | ~30k             |                         |
| → No Silver Bullet + Refired            | ~15k             |                         |
| → Dijkstra EWD selections               | ~50k             |                         |
| → Naur, Hoare, Thompson                 | ~25k             |                         |
| → Stepanov Notes                        | ~100k            |                         |
| → SRE Book + Workbook excerpts          | ~150k (curated)  |                         |
| → MIT 6.005 readings (curated)          | ~80k             |                         |
| → HtDP design-recipe excerpts           | ~40k             |                         |
| → Clean Code critique cluster           | ~35k             |                         |
| → danluu (excerpt-mode pending license) | ~200k (sample)   |                         |
| → AWS/GitHub/Cloudflare post-mortems    | ~500k (curated)  |                         |

**Gap analysis vs ~3B target:**

Tier B raw, even with the new finds, is only ~3M tok — three orders of
magnitude below the 3B target. The 3B is realistically met by:

1. **Tier A** language-native canon (PEPs, Rust Book, Effective Go, etc.)
   — likely 50-100M tok permissive.
2. **Tier C** post-mortem canon — bulk includes if licensing tolerates.
3. **Tier D** hexa-canon ×10 weighting — multiplies hexa-canon ~10M into
   100M effective.
4. **Tier B principle-expansion synthesis** — take each principle from
   the excerpt set and have the model generate K canonical
   per-language elaborations (Pythonic comprehension, Rusty `Result`,
   Go-channelled CSP). This is how the principle canon punches above
   its raw weight in the mix.

**Recommendation:** treat Tier B as a *high-signal seed* (~3M tok),
not as a bulk source. The 3B-tok philosophy target is hit by Tier A +
Tier D weighting + synthesis amplification, with Tier B providing
the **principle anchors** that synthesis expands against.

---

# Cross-link

- Stage definition: [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset)
- Source candidate list: [`papers/coding-philosophy-sources.md §2`](./coding-philosophy-sources.md#2-tier-b--engineering-principle-canon-cross-lang)
- Open Q on book content (Ousterhout, Hunt/Thomas): [`coding-philosophy-sources.md §7`](./coding-philosophy-sources.md#7-open-questions) — this report resolves: **fair-use excerpts only**, flagged with `canon-tag: principle-book-excerpt`.
- Open Q on `philosophy` ordering: still open — recommend running this
  stage **after** `domain-bias` so the language priors are already in
  place when principle anchors land.
