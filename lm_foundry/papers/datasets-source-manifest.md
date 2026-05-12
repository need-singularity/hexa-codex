# datasets-source-manifest — consolidated rollup

> One-row-per-source table consolidating 7 tier/frontend findings docs.
> Tooling consumers: `tool/license_clean_scan.py` (license check),
> `tool/fetch_sources.py` (planned), `datasets.toml` (registry).
> When a tier-findings doc changes, this rollup is REGENERATED, not
> manually patched. (Add a regen-script note at the bottom.)

| field         | value                            |
| ------------- | -------------------------------- |
| status        | LIVE                             |
| last regen    | 2026-05-11                       |
| total entries | 182                              |
| consumers     | tool/license_clean_scan.py, datasets.toml |

---

## §1 Master table

(sorted by tier then alphabetical by source name)

| # | source name | canonical URL | license | tier | stage | tokens (est) | fetch status | notes |
| - | ----------- | ------------- | ------- | ---- | ----- | ------------ | ------------ | ----- |
| 1 | All accepted PEPs index | https://peps.python.org/ | public-domain | A | philosophy | ~10M | ⚠ pending | per-PEP public domain; pre-filter to design/style/process PEPs |
| 2 | C FAQ (comp.lang.c) | https://c-faq.com/ | proprietary | A | philosophy | ~150K | ✗ url-broken | UNVERIFIED; non-commercial use only; quote-only |
| 3 | CERT C Coding Standard | https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard | CC-BY-4.0 | A | philosophy | ~500K | ✓ ready | text CC-BY-4.0 + code MIT; full include (was partial, upgraded) |
| 4 | Declaration "Do's and Don'ts" | https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html | CC-BY-4.0 | A | philosophy | ~10K | ✓ ready | TS handbook subset |
| 5 | DefinitelyTyped contribution guide | https://github.com/DefinitelyTyped/DefinitelyTyped | MIT | A | philosophy | ~10K | ⚠ pending | UNVERIFIED — CONTRIBUTING.md; pairs w/ handbook do's/don'ts |
| 6 | Effective Go | https://go.dev/doc/effective_go | CC-BY-4.0 | A | philosophy | ~50K | ✓ ready | docs CC-BY-4.0 + code BSD-3-Clause |
| 7 | GNU C Coding Standards | https://www.gnu.org/prep/standards/ | GFDL | A | philosophy | ~50K | ✗ blocked-by-license | UNVERIFIED; GFDL copyleft → quote-only |
| 8 | Go Blog (official posts) | https://go.dev/blog/all | CC-BY-4.0 | A | philosophy | ~1M | ✓ ready | 200+ posts since 2010; filter to design/idiom |
| 9 | Go Code Review Comments | https://go.dev/wiki/CodeReviewComments | CC-BY-4.0 | A | philosophy | ~10K | ⚠ pending | wiki implicit license inheritance |
| 10 | Go FAQ | https://go.dev/doc/faq | CC-BY-4.0 | A | philosophy | ~50K | ✓ ready | pure design-philosophy doc |
| 11 | Go Language Specification | https://go.dev/ref/spec | CC-BY-4.0 | A | philosophy | ~50K | ✓ ready | reference, rationale-rich |
| 12 | Go Proverbs | https://go-proverbs.github.io/ | MIT | A | philosophy | ~10K | ✓ ready | Pike's talk transcript |
| 13 | Google Python Style Guide | https://google.github.io/styleguide/pyguide.html | CC-BY-3.0 | A | philosophy | ~50K | ✓ ready | also overlaps Tier B |
| 14 | ISO C99 Rationale (V5.10) | https://www.open-std.org/jtc1/sc22/wg14/www/C99RationaleV5.10.pdf | UNKNOWN | A | philosophy | ~100K | ✗ blocked-by-license | WG14 free but no formal CC/MIT → quote-only |
| 15 | Linux kernel coding-style | https://www.kernel.org/doc/html/latest/process/coding-style.html | GPL-2.0 | A | philosophy | ~10K | ✗ blocked-by-license | quote-only under fair-use |
| 16 | OpenBSD style(9) man page | https://man.openbsd.org/style.9 | BSD-3-Clause | A | philosophy | ~10K | ⚠ pending | UNVERIFIED — confirm exact license on page |
| 17 | PEP-20 (Zen of Python) | https://peps.python.org/pep-0020/ | public-domain | A | philosophy | ~10K | ✓ ready | 250 words; high-signal ×10 weight candidate |
| 18 | PEP-257 (docstrings) | https://peps.python.org/pep-0257/ | public-domain | A | philosophy | ~10K | ✓ ready | PSF/public domain |
| 19 | PEP-8 (style guide) | https://peps.python.org/pep-0008/ | public-domain | A | philosophy | ~50K | ✓ ready | Python style guide |
| 20 | PostgreSQL "Internals" chapters | https://www.postgresql.org/docs/current/internals.html | PostgreSQL | A | philosophy | ~500K | ✓ ready | query planner, MVCC rationale |
| 21 | PostgreSQL docs | https://www.postgresql.org/docs/current/ | PostgreSQL | A | philosophy | ~5M | ✓ ready | BSD-like permissive; filter to SQL-idiom chapters |
| 22 | Python HOWTOs | https://docs.python.org/3/howto/ | PSF | A | philosophy | ~500K | ✓ ready | functional-programming, enum, descriptors, sorting |
| 23 | Python Tutorial (full) | https://docs.python.org/3/tutorial/ | PSF | A | philosophy | ~100K | ✓ ready | canonical "how Python is written" |
| 24 | Rust API Guidelines | https://rust-lang.github.io/api-guidelines/ | MIT | A | philosophy | ~50K | ✓ ready | dual MIT/Apache-2.0; 11 chapters |
| 25 | Rust Edition Guide | https://doc.rust-lang.org/edition-guide/ | MIT | A | philosophy | ~50K | ⚠ pending | UNVERIFIED; dual MIT/Apache assumed |
| 26 | Rust Reference | https://doc.rust-lang.org/reference/ | MIT | A | philosophy | ~500K | ✓ ready | dual MIT/Apache-2.0; language spec |
| 27 | Rust RFCs (accepted) | https://rust-lang.github.io/rfcs/ | MIT | A | philosophy | ~5M | ✓ ready | dual MIT/Apache; filter to merged only |
| 28 | Rust clippy lint rationale | https://github.com/rust-lang/rust-clippy | MIT | A | philosophy | ~1M | ✓ ready | dual MIT/Apache; also feeds Tier E DPO |
| 29 | Rustonomicon | https://doc.rust-lang.org/nomicon/ | MIT | A | philosophy | ~100K | ✓ ready | dual MIT/Apache; unsafe Rust |
| 30 | SQLite "About" + design docs | https://www.sqlite.org/about.html | public-domain | A | philosophy | ~500K | ✓ ready | When To Use SQLite, How SQLite Is Tested, The WAL |
| 31 | SQLite Lang Reference | https://www.sqlite.org/lang.html | public-domain | A | philosophy | ~100K | ⚠ pending | UNVERIFIED URL; public domain |
| 32 | TC39 ECMA-262 spec text | https://tc39.es/ecma262/ | proprietary | A | philosophy | ~500K | ✗ blocked-by-license | ECMA royalty-free policy; quote-only |
| 33 | TC39 proposals (finished + active) | https://github.com/tc39/proposals | UNKNOWN | A | philosophy | ~1M | ⚠ pending | per-proposal LICENSE scan required |
| 34 | The Rust Book | https://doc.rust-lang.org/book/ | MIT | A | philosophy | ~500K | ✓ ready | dual MIT/Apache-2.0 |
| 35 | TS Handbook (full) | https://www.typescriptlang.org/docs/handbook/ | CC-BY-4.0 | A | philosophy | ~500K | ✓ ready | prose CC-BY-4.0 + code MIT |
| 36 | itertools recipes section | https://docs.python.org/3/library/itertools.html | PSF | A | philosophy | ~10K | ✓ ready | canonical Pythonic iteration |
| 37 | stdlib "Pythonic" rationale | https://docs.python.org/3/library/ | PSF | A | philosophy | ~5M | ✓ ready | PSF v2 + 0BSD; cherry-pick rationale prose |
| 38 | tsconfig `strict` rationale | https://www.typescriptlang.org/tsconfig | CC-BY-4.0 | A | philosophy | ~50K | ✓ ready | TSConfig per-flag rationale |
| 39 | Zig Build System guide | https://ziglang.org/learn/build-system/ | MIT | A | philosophy | ~10K | ⚠ pending | UNVERIFIED page existence |
| 40 | Zig language reference | https://ziglang.org/documentation/master/ | MIT | A | philosophy | ~100K | ✓ ready | Expat MIT |
| 41 | Zig overview ("In-depth Overview") | https://ziglang.org/learn/overview/ | MIT | A | philosophy | ~50K | ✓ ready | replaces non-existent "Zig zen" page |
| 42 | Zig standard library source comments | https://github.com/ziglang/zig | MIT | A | philosophy | ~500K | ✓ ready | mine doc-comments from lib/std/ |
| 43 | "Why Zig When There Is C++/D/Rust?" | https://ziglang.org/learn/why_zig_rust_d_cpp/ | MIT | A | philosophy | ~10K | ✓ ready | direct comparative philosophy |
| 44 | A Philosophy of Software Design (extract) | https://web.stanford.edu/~ouster/cgi-bin/aposd.php | proprietary | B | philosophy | ~50K | ✗ blocked-by-license | free extract PDF only; full book paid |
| 45 | Cathedral and the Bazaar | https://archive.org/details/CathedralAndTheBazaar | UNKNOWN | B | philosophy | ~50K | ✓ ready | Open Publication License v2.0 (permissive, derivable) |
| 46 | Clean Code critique cluster | https://qntm.org/clean | proprietary | B | philosophy | ~50K | ✗ blocked-by-license | qntm + overreacted.io + Ousterhout/Martin debate; DPO pairs |
| 47 | Dijkstra EWD340 + EWD archive | https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD340.html | UNKNOWN | B | philosophy | ~50K | ✗ blocked-by-license | ACM CACM 1972; UT Austin "reproduced w/ permission" |
| 48 | Drew DeVault's blog | https://drewdevault.com/ | CC-BY-SA-4.0 | B | philosophy | ~500K | ✓ ready | actually CC-BY-SA 2.0 per site footer; allowlist exception |
| 49 | Google Engineering Practices (eng-practices) | https://google.github.io/eng-practices/ | CC-BY-3.0 | B | philosophy | ~50K | ✓ ready | code-review playbook |
| 50 | Hoare "Hints on Programming Language Design" | https://www.cs.yale.edu/flint/cs428/doc/HintsPL.pdf | UNKNOWN | B | philosophy | ~10K | ✗ blocked-by-license | Stanford TR 1973; academic fair-use only |
| 51 | HtDP — How to Design Programs (2e) | https://htdp.org/2023-8-14/Book/ | CC-BY-NC-ND-4.0 | B | philosophy | ~100K | ✗ blocked-by-license | ND clause blocks derivatives |
| 52 | MIT 6.005 — Software Construction | https://web.mit.edu/6.005/www/archive/ | CC-BY-NC-SA-4.0 | B | philosophy | ~100K | ✗ blocked-by-license | NC blocks commercial training |
| 53 | Naur "Programming as Theory Building" | https://pages.cs.wisc.edu/~remzi/Naur.pdf | UNKNOWN | B | philosophy | ~10K | ✗ blocked-by-license | 1985 essay; academic mirror; fair-use |
| 54 | No Silver Bullet (Brooks) | https://worrydream.com/refs/Brooks_1986_-_No_Silver_Bullet.pdf | proprietary | B | philosophy | ~10K | ✗ blocked-by-license | © IEEE; academic fair-use |
| 55 | Out of the Tar Pit (Moseley & Marks) | http://curtclifton.net/papers/MoseleyMarks06a.pdf | UNKNOWN | B | philosophy | ~50K | ⚠ pending | SPA 2006; no SPDX; de-facto public |
| 56 | Pragmatic Programmer (tips) | https://pragprog.com/tips/ | proprietary | B | philosophy | ~10K | ✗ blocked-by-license | publisher-permissioned only |
| 57 | SICP — Structure and Interpretation of Computer Programs (2e) | https://sarabander.github.io/sicp/html/ | CC-BY-SA-4.0 | B | philosophy | ~500K | ✓ ready | re-licensed by MIT Press ~2016 |
| 58 | SOLID / DRY / YAGNI / KISS (Wikipedia) | https://en.wikipedia.org/wiki/SOLID | CC-BY-SA-4.0 | B | philosophy | ~50K | ✓ ready | Wikipedia principle articles |
| 59 | Stanford CS190 (Ousterhout) slides | https://web.stanford.edu/class/cs190/ | UNKNOWN | B | philosophy | ~50K | ✗ url-broken | UNVERIFIED — not publicly indexed |
| 60 | Stepanov "Notes on Programming" | https://stepanovpapers.com/notes.pdf | UNKNOWN | B | philosophy | ~100K | ⚠ pending | author-hosted; no SPDX |
| 61 | Thompson "Reflections on Trusting Trust" | https://www.cs.cmu.edu/~rdriley/487/papers/Thompson_1984_ReflectionsonTrustingTrust.pdf | UNKNOWN | B | philosophy | ~10K | ✗ blocked-by-license | ACM "educational/personal use only" |
| 62 | Worse is Better (Gabriel) | https://www.dreamsongs.com/RiseOfWorseIsBetter.html | CC-BY-NC-SA-3.0 | B | philosophy | ~10K | ✗ blocked-by-license | NC clause blocks bulk train |
| 63 | danluu.com | https://danluu.com/ | UNKNOWN | B | philosophy | ~500K | ✗ blocked-by-license | no license stated; allowlist exception for excerpts |
| 64 | AWS Builders' Library | https://aws.amazon.com/builders-library/ | proprietary | C | philosophy | ~500K | ⚠ pending | © Amazon; vendor-fair-use research |
| 65 | AWS service event summaries (PES) | https://aws.amazon.com/premiumsupport/technology/pes/ | proprietary | C | philosophy | ~50K | ⚠ pending | gold-standard blameless RCAs |
| 66 | Azure Post-Incident Reviews (PIRs) | https://azure.status.microsoft/en-us/status/history/ | proprietary | C | philosophy | ~100K | ⚠ pending | © Microsoft; 5-year retention |
| 67 | Cloudflare blog post-mortems | https://blog.cloudflare.com/tag/post-mortem/ | proprietary | C | philosophy | ~500K | ✓ ready | robots.txt: ai-train=yes; explicit train OK |
| 68 | Datadog March 2023 outage series | https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/ | proprietary | C | philosophy | ~50K | ⚠ pending | 4 deep-dive posts + USENIX talk |
| 69 | Discord Engineering blog (post-mortems) | https://discord.com/category/engineering | proprietary | C | philosophy | ~50K | ⚠ pending | voice/session post-mortems |
| 70 | Fastly — June 8 2021 outage | https://www.fastly.com/blog/summary-of-june-8-outage | proprietary | C | philosophy | ~10K | ⚠ pending | config-cascade post-mortem |
| 71 | GCP incidents.json archive | https://status.cloud.google.com/incidents.json | proprietary | C | philosophy | ~100K | ⚠ pending | machine-readable structured dump |
| 72 | GitHub status post-mortems (Availability Reports) | https://github.blog/tag/github-availability-report/ | proprietary | C | philosophy | ~100K | ⚠ pending | corrected URL (was githubstatus.com) |
| 73 | GitLab Handbook — incident management | https://handbook.gitlab.com/handbook/engineering/incident-management/ | CC-BY-SA-4.0 | C | philosophy | ~50K | ✓ ready | famously CC-BY-SA |
| 74 | Google SRE Book | https://sre.google/sre-book/table-of-contents/ | CC-BY-NC-ND-4.0 | C | philosophy | ~500K | ✗ blocked-by-license | ND+NC double-block; prefer Workbook |
| 75 | Google SRE Workbook | https://sre.google/workbook/table-of-contents/ | CC-BY-4.0 | C | philosophy | ~500K | ✓ ready | preferred over SRE Book; commercial-OK |
| 76 | Heroku post-mortems | https://www.heroku.com/blog/ | proprietary | C | philosophy | ~50K | ⚠ pending | © Salesforce |
| 77 | Increment Magazine archive | https://increment.com/issues/ | proprietary | C | philosophy | ~500K | ⚠ pending | © Stripe; dormant; stable corpus |
| 78 | Kubernetes Failure Stories (k8s.af) | https://k8s.af/ | UNKNOWN | C | philosophy | ~100K | ⚠ pending | community-contributed; link-spine |
| 79 | PyPI incident-report blog | https://blog.pypi.org/ | UNKNOWN | C | philosophy | ~10K | ⚠ pending | PSF terms; supply-chain incident genre |
| 80 | Stripe — incident retros | https://stripe.com/blog/engineering | proprietary | C | philosophy | ~10K | ⚠ pending | 2019-07-10 narrative is canonical |
| 81 | Surfing Complexity (Lorin Hochstein) | https://surfingcomplexity.blog/ | UNKNOWN | C | philosophy | ~500K | ⚠ pending | personal blog; resilience-eng analysis |
| 82 | awesome-postmortem (saystone) | https://github.com/saystone/awesome-postmortem | CC0-1.0 | C | philosophy | ~10K | ✓ ready | link-spine; stale 2019-21 |
| 83 | awesome-tech-postmortems (snakescott) | https://github.com/snakescott/awesome-tech-postmortems | CC-BY-4.0 | C | philosophy | ~10K | ✓ ready | link-spine; stale 2019-21 |
| 84 | danluu/post-mortems repo | https://github.com/danluu/post-mortems | UNKNOWN | C | philosophy | ~10K | ✗ blocked-by-license | repo no LICENSE; link-spine only |
| 85 | k8s/community postmortems | https://github.com/kubernetes/community/tree/master/sig-cluster-lifecycle/postmortems | Apache-2.0 | C | philosophy | ~10K | ✓ ready | corrected URL; tiny but full ingest OK |
| 86 | CodeReviewer dataset (Microsoft) | https://github.com/microsoft/CodeBERT | UNKNOWN | E | repair | ~100K | ⚠ pending | arxiv 2203.09095; license UNVERIFIED |
| 87 | GitHub PR review diffs (API) | https://api.github.com | UNKNOWN | E | repair | ~5M | ⚠ pending | per-repo license filter to MIT/Apache/BSD |
| 88 | LeetCode / Codeforces (via derivatives) | https://leetcode.com/problems/ | proprietary | E | repair | ~100K | ✗ blocked-by-license | use TACO/COFO/LeetCodeDataset derivatives only |
| 89 | Reviewdog / linter-bot PR comments | https://github.com/reviewdog/reviewdog | MIT | E | repair | ~500K | ⚠ pending | per-repo permissive filter required |
| 90 | StackExchange data dump | https://archive.org/details/stackexchange | CC-BY-SA-4.0 | E | repair | ~5M | ✗ blocked-by-license | 2024 LLM-training clause vs CC ambiguity; legal review |
| 91 | clang-tidy checks | https://clang.llvm.org/extra/clang-tidy/checks/list.html | Apache-2.0 | E | repair | ~500K | ⚠ pending | 600+ checks; Apache-2 LLVM exception |
| 92 | clippy lint catalogue | https://rust-lang.github.io/rust-clippy/master/index.html | MIT | E | repair | ~1M | ✓ ready | 814 lints; dual MIT/Apache-2.0 |
| 93 | golangci-lint aggregator | https://golangci-lint.run/docs/linters/ | MIT | E | repair | ~500K | ⚠ pending | runner GPL-3 (don't redistribute); rule docs MIT/BSD |
| 94 | ruff Python lint rules | https://docs.astral.sh/ruff/rules/ | MIT | E | repair | ~1M | ✓ ready | 900+ rules; safe-fix tagged |
| 95 | Alpine.js | https://alpinejs.dev/ | MIT | F1 | philosophy | ~10K | ✓ ready | hypermedia-driven micro-framework |
| 96 | Angular docs | https://angular.dev/guide/zoneless | MIT | F1 | philosophy | ~500K | ✓ ready | zoneless + signals canon |
| 97 | Ark UI | https://ark-ui.com/ | MIT | F1 | philosophy | ~50K | ⚠ pending | cross-framework headless primitives |
| 98 | ArkType | https://arktype.io/ | MIT | F1 | philosophy | ~50K | ✓ ready | perf validation champion |
| 99 | Astro 5 | https://astro.build/blog/astro-5/ | MIT | F1 | philosophy | ~500K | ✓ ready | server islands + content layer |
| 100 | Base UI | https://mui.com/base-ui | MIT | F1 | philosophy | ~50K | ✓ ready | MUI team headless successor |
| 101 | CVA (Class Variance Authority) | https://cva.style/docs | Apache-2.0 | F1 | philosophy | ~10K | ✓ ready | variant API for Tailwind |
| 102 | HTMX | https://htmx.org/ | BSD-2-Clause | F1 | philosophy | ~50K | ✓ ready | also 0BSD; hypermedia-driven |
| 103 | Hono RPC | https://hono.dev/docs/guides/rpc | MIT | F1 | philosophy | ~100K | ✓ ready | edge-native typed RPC |
| 104 | JSDoc-as-TS | https://alexharri.com/blog/jsdoc-as-an-alternative-typescript-syntax | UNKNOWN | F1 | philosophy | ~10K | ⚠ pending | library-author concern |
| 105 | Jotai | https://jotai.org/ | MIT | F1 | philosophy | ~50K | ✓ ready | atomic state |
| 106 | Lit / Web Components | https://lit.dev/blog/2024-10-08-signals/ | BSD-3-Clause | F1 | philosophy | ~50K | ✓ ready | TC39 Signals integration |
| 107 | Material Design 3 (M3 Expressive) | https://m3.material.io/ | Apache-2.0 | F1 | philosophy | ~500K | ✓ ready | guidelines Apache-2.0; icons separate |
| 108 | Next.js (App Router) | https://nextjs.org/docs/app | MIT | F1 | philosophy | ~500K | ✓ ready | RSC + Server Actions canon |
| 109 | Nuxt 4 | https://nuxt.com/docs | MIT | F1 | philosophy | ~500K | ✓ ready | app/ directory layout |
| 110 | Panda CSS | https://panda-css.com/docs/overview/why-panda | MIT | F1 | philosophy | ~50K | ✓ ready | zero-runtime CSS-in-TS |
| 111 | Pigment CSS | https://github.com/mui/pigment-css | MIT | F1 | philosophy | ~50K | ⚠ pending | UNVERIFIED v1 stable status |
| 112 | Preact | https://preactjs.com/ | MIT | F1 | philosophy | ~50K | ✓ ready | lightweight React-API w/ signals |
| 113 | Qwik / Qwik City | https://qwik.dev/docs/ | MIT | F1 | philosophy | ~100K | ✓ ready | resumability framework |
| 114 | React 19 docs | https://react.dev/ | MIT | F1 | philosophy | ~500K | ✓ ready | RSC + Compiler + use() canon |
| 115 | React Aria Components | https://react-spectrum.adobe.com/react-aria/ | Apache-2.0 | F1 | philosophy | ~100K | ✓ ready | Adobe; deepest a11y + i18n |
| 116 | React Hook Form | https://react-hook-form.com/ | MIT | F1 | philosophy | ~50K | ✓ ready | uncontrolled-refs form default |
| 117 | React Router 7 (Remix merge) | https://reactrouter.com/upgrading/remix | MIT | F1 | philosophy | ~100K | ✓ ready | Remix v2 merged into RR7 |
| 118 | Redux Toolkit | https://redux-toolkit.js.org/ | MIT | F1 | philosophy | ~100K | ✓ ready | enterprise-legacy canon |
| 119 | Radix UI | https://www.radix-ui.com/ | MIT | F1 | philosophy | ~100K | ✓ ready | headless primitives |
| 120 | Server Actions (Next/React) | https://react.dev/blog/2024/12/05/react-19 | MIT | F1 | philosophy | ~50K | ✓ ready | progressive-enhancement form path |
| 121 | Solid | https://docs.solidjs.com/ | MIT | F1 | philosophy | ~100K | ✓ ready | fine-grained reactivity |
| 122 | SolidStart | https://start.solidjs.com/ | MIT | F1 | philosophy | ~50K | ⚠ pending | pre-1.0 / 2.0-alpha |
| 123 | StyleX | https://stylexjs.com/ | MIT | F1 | philosophy | ~50K | ⚠ pending | Meta atomic CSS-in-JS |
| 124 | Svelte 5 (Runes) | https://svelte.dev/blog/runes | MIT | F1 | philosophy | ~100K | ✓ ready | $state/$derived/$effect canon |
| 125 | SvelteKit | https://kit.svelte.dev/ | MIT | F1 | philosophy | ~100K | ✓ ready | Svelte 5 paired meta-framework |
| 126 | TC39 proposal-signals | https://github.com/tc39/proposal-signals | CC-BY-4.0 | F1 | philosophy | ~10K | ✓ ready | also Tier A overlap; Stage 1 |
| 127 | TSDoc | https://tsdoc.org/ | MIT | F1 | philosophy | ~10K | ✓ ready | Microsoft TS-specific JSDoc successor |
| 128 | Tailwind v4 | https://tailwindcss.com/blog/tailwindcss-v4 | MIT | F1 | philosophy | ~100K | ✓ ready | Oxide engine, CSS-first config |
| 129 | TanStack (Query + Router + Form + Start) | https://tanstack.com/ | MIT | F1 | philosophy | ~500K | ✓ ready | server-state + typed search params |
| 130 | TanStack Form | https://tanstack.com/form/latest | MIT | F1 | philosophy | ~50K | ✓ ready | headless framework-agnostic forms |
| 131 | TanStack Start | https://tanstack.com/start/latest | MIT | F1 | philosophy | ~100K | ⚠ pending | RC / pre-1.0 in 2026 |
| 132 | Valibot | https://valibot.dev/ | MIT | F1 | philosophy | ~50K | ✓ ready | bundle-size validation champion |
| 133 | Vue 3 docs | https://vuejs.org/ | MIT | F1 | philosophy | ~300K | ✓ ready | Composition API + script setup |
| 134 | Zod | https://zod.dev/ | MIT | F1 | philosophy | ~50K | ✓ ready | default validation lib |
| 135 | Zustand | https://zustand-demo.pmnd.rs/ | MIT | F1 | philosophy | ~10K | ✓ ready | default client UI state |
| 136 | nuqs | https://nuqs.dev/ | MIT | F1 | philosophy | ~10K | ✓ ready | type-safe URL state |
| 137 | oRPC | https://orpc.unnoq.com/ | MIT | F1 | philosophy | ~10K | ⚠ pending | tRPC-style + OpenAPI |
| 138 | shadcn/ui | https://ui.shadcn.com/ | MIT | F1 | philosophy | ~50K | ✓ ready | default for new React projects |
| 139 | tRPC | https://trpc.io/ | MIT | F1 | philosophy | ~50K | ✓ ready | end-to-end TS types no codegen |
| 140 | vanilla-extract | https://vanilla-extract.style/ | MIT | F1 | philosophy | ~50K | ✓ ready | zero-runtime stylesheets-in-TS |
| 141 | vee-validate (Vue) | https://vee-validate.logaretm.com/ | MIT | F1 | philosophy | ~50K | ⚠ pending | Vue forms canon |
| 142 | Bun | https://bun.sh/docs | MIT | F2 | philosophy | ~100K | ✓ ready | runtime + bundler + test + pm |
| 143 | Deno 2 | https://docs.deno.com/ | MIT | F2 | philosophy | ~100K | ✓ ready | native TS runtime |
| 144 | MDN Web Docs | https://developer.mozilla.org/ | CC-BY-SA-4.0 | F2 | philosophy | ~5M | ✓ ready | actually CC-BY-SA 2.5 per license-gate note |
| 145 | Node.js TS docs | https://nodejs.org/api/typescript.html | MIT | F2 | philosophy | ~50K | ✓ ready | --experimental-strip-types |
| 146 | Oxc | https://oxc.rs/ | MIT | F2 | philosophy | ~50K | ⚠ pending | UNVERIFIED prod scale |
| 147 | Rolldown | https://rolldown.rs/ | MIT | F2 | philosophy | ~50K | ✓ ready | Vite 8 default; 10-30× faster |
| 148 | Rspack | https://rspack.dev/ | MIT | F2 | philosophy | ~100K | ✓ ready | Rust-based Webpack-compatible |
| 149 | SWC | https://swc.rs/ | Apache-2.0 | F2 | philosophy | ~50K | ✓ ready | Rust JS transformer |
| 150 | Turbopack | https://turbo.build/pack | MPL-2.0 | F2 | philosophy | ~50K | ✓ ready | Next.js-only bundler |
| 151 | Vite | https://vite.dev/ | MIT | F2 | philosophy | ~100K | ✓ ready | dominant FE dev server |
| 152 | W3C CSS Logical Properties | https://drafts.csswg.org/css-logical/ | UNKNOWN | F2 | philosophy | ~50K | ✓ ready | W3C Document License |
| 153 | W3C CSS Sizing 3 | https://www.w3.org/TR/css-sizing-3/ | UNKNOWN | F2 | philosophy | ~50K | ✓ ready | W3C Document License |
| 154 | caniuse.com | https://caniuse.com/ | CC-BY-4.0 | F2 | philosophy | ~500K | ✓ ready | browser support matrix |
| 155 | esbuild | https://esbuild.github.io/ | MIT | F2 | philosophy | ~50K | ✓ ready | universal bundler |
| 156 | tsgo / TypeScript-Go (Project Corsa) | https://github.com/microsoft/typescript-go | Apache-2.0 | F2 | philosophy | ~50K | ✓ ready | TypeScript 7 in Go (not Rust); beta Apr 2026 |
| 157 | typescriptlang.org docs | https://www.typescriptlang.org/tsconfig | CC-BY-4.0 | F2 | philosophy | ~50K | ✓ ready | also overlap Tier A row 38 |
| 158 | web.dev (Chrome for Developers) | https://web.dev/ | CC-BY-4.0 | F2 | philosophy | ~1M | ✓ ready | Google web platform docs |
| 159 | APCA (perceptual contrast) | https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html | UNKNOWN | F3 | philosophy | ~10K | ⚠ pending | WCAG 3 draft algorithm |
| 160 | Capacitor (Ionic) | https://capacitorjs.com/docs | MIT | F3 | philosophy | ~50K | ✓ ready | modern Cordova successor |
| 161 | Chrome for Developers — AI / LLM rendering | https://developer.chrome.com/docs/ai/render-llm-responses | CC-BY-4.0 | F3 | philosophy | ~10K | ✓ ready | streaming-markdown + DOMPurify pattern |
| 162 | Chromatic (visual regression) | https://www.chromatic.com/docs/ | UNKNOWN | F3 | philosophy | ~10K | ⚠ pending | proprietary docs; cite-only |
| 163 | Dexie.js | https://dexie.org/ | Apache-2.0 | F3 | philosophy | ~50K | ✓ ready | canonical IDB wrapper |
| 164 | Expo SDK | https://docs.expo.dev/ | MIT | F3 | philosophy | ~100K | ✓ ready | RN default starting point |
| 165 | Flutter | https://docs.flutter.dev/ | BSD-3-Clause | F3 | philosophy | ~500K | ✓ ready | Dart cross-platform |
| 166 | Ladle | https://ladle.dev/ | MIT | F3 | philosophy | ~10K | ✓ ready | fast Storybook-lite for React |
| 167 | ONNX Runtime Web | https://onnxruntime.ai/docs/get-started/with-javascript/web.html | MIT | F3 | philosophy | ~50K | ✓ ready | generic model runtime |
| 168 | Playwright | https://playwright.dev/ | Apache-2.0 | F3 | philosophy | ~100K | ✓ ready | default E2E |
| 169 | React Native | https://reactnative.dev/ | MIT | F3 | philosophy | ~500K | ✓ ready | New Architecture + Fabric |
| 170 | Storybook 9 | https://storybook.js.org/ | MIT | F3 | philosophy | ~100K | ✓ ready | Vitest + a11y + visual diff in one |
| 171 | TanStack Virtual | https://tanstack.com/virtual/latest | MIT | F3 | philosophy | ~10K | ✓ ready | variable-height virtualization |
| 172 | Tauri 2 | https://v2.tauri.app/ | MIT | F3 | philosophy | ~100K | ✓ ready | Rust backend; small binaries |
| 173 | Testing Library | https://testing-library.com/ | MIT | F3 | philosophy | ~50K | ✓ ready | getByRole canonical |
| 174 | Transformers.js | https://huggingface.co/docs/transformers.js | Apache-2.0 | F3 | philosophy | ~50K | ✓ ready | ONNX-in-browser + WebGPU |
| 175 | Vercel AI SDK | https://ai-sdk.dev/docs/ai-sdk-ui | Apache-2.0 | F3 | philosophy | ~100K | ✓ ready | streamText/streamObject/streamUI |
| 176 | Vitest | https://vitest.dev/ | MIT | F3 | philosophy | ~50K | ✓ ready | unit/component for new projects |
| 177 | W3C ARIA APG | https://www.w3.org/WAI/ARIA/apg/ | UNKNOWN | F3 | philosophy | ~100K | ✓ ready | W3C Document License; pattern source |
| 178 | W3C WCAG 2.2 | https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ | UNKNOWN | F3 | philosophy | ~100K | ✓ ready | W3C Document License; current legal standard |
| 179 | W3C using-aria (5 Rules) | https://www.w3.org/TR/using-aria/ | UNKNOWN | F3 | philosophy | ~10K | ✓ ready | W3C Document License |
| 180 | Web LLM (MLC) | https://webllm.mlc.ai/ | Apache-2.0 | F3 | philosophy | ~50K | ✓ ready | LLM-specific WebGPU runtime |
| 181 | WebAIM Screen Reader Survey | https://webaim.org/projects/screenreadersurvey10/ | proprietary | F3 | philosophy | ~10K | ✓ ready | stats fair-use citation |
| 182 | axe-core | https://github.com/dequelabs/axe-core | MPL-2.0 | F3 | philosophy | ~50K | ✓ ready | a11y rule engine |

Tier distribution (primary-tier counts):

- A: 43
- B: 20
- C: 22
- E: 9
- F1: 47
- F2: 17
- F3: 24
- **total: 182**

## §2 License breakdown

| license            | count | tier mix |
| ------------------ | ----- | -------- |
| MIT                | 76    | A:14 B:0 C:0 E:4 F1:40 F2:8 F3:10 |
| UNKNOWN            | 25    | A:2 B:9 C:4 E:2 F1:1 F2:2 F3:5 |
| proprietary        | 20    | A:2 B:4 C:12 E:1 F1:0 F2:0 F3:1 |
| CC-BY-4.0          | 16    | A:9 B:0 C:2 E:0 F1:1 F2:3 F3:1 |
| Apache-2.0         | 12    | A:0 B:0 C:1 E:1 F1:3 F2:2 F3:5 |
| public-domain      | 6     | A:6 B:0 C:0 E:0 F1:0 F2:0 F3:0 |
| CC-BY-SA-4.0       | 6     | A:0 B:3 C:1 E:1 F1:0 F2:1 F3:0 |
| PSF                | 4     | A:4 B:0 C:0 E:0 F1:0 F2:0 F3:0 |
| CC-BY-NC-SA-4.0    | 2     | A:0 B:1 C:1 E:0 F1:0 F2:0 F3:0 |
| BSD-3-Clause       | 3     | A:1 B:0 C:0 E:0 F1:1 F2:0 F3:1 |
| PostgreSQL         | 2     | A:2 B:0 C:0 E:0 F1:0 F2:0 F3:0 |
| MPL-2.0            | 2     | A:0 B:0 C:0 E:0 F1:0 F2:1 F3:1 |
| CC-BY-3.0          | 2     | A:1 B:1 C:0 E:0 F1:0 F2:0 F3:0 |
| CC-BY-NC-ND-4.0    | 2     | A:0 B:1 C:1 E:0 F1:0 F2:0 F3:0 |
| GPL-2.0            | 1     | A:1 B:0 C:0 E:0 F1:0 F2:0 F3:0 |
| GFDL               | 1     | A:1 B:0 C:0 E:0 F1:0 F2:0 F3:0 |
| CC0-1.0            | 1     | A:0 B:0 C:1 E:0 F1:0 F2:0 F3:0 |
| CC-BY-NC-SA-3.0    | 1     | A:0 B:1 C:0 E:0 F1:0 F2:0 F3:0 |
| BSD-2-Clause       | 1     | A:0 B:0 C:0 E:0 F1:1 F2:0 F3:0 |

(A source with multi-license dual-grant — e.g. MIT/Apache-2.0 — is
counted under its primary SPDX id only. Allowed SPDX ids match the
consolidation-prompt list, plus `CC-BY-NC-ND-4.0` added to capture the
SRE Book and HtDP "ND" cases.)

## §3 Fetch-status breakdown

| status                 | count |
| ---------------------- | ----- |
| ✓ ready                | 120   |
| ⚠ pending verification | 40    |
| ✗ blocked-by-license   | 20    |
| ✗ url-broken           | 2     |

## §4 Anti-corpus list (Tier E + pollution exclude)

Domains / patterns that MUST be filtered out of any fetch. From
`tier-e-findings.md`:

- `medium.com` (incl. all `*.medium.com`) — exclude entirely after 2023-01-01 (AI-slop saturation; Pangram 47%, Originality 40%+)
- `dev.to` — exclude after 2023-01-01
- `hashnode.com`, `*.hashnode.dev` — exclude after 2023-01-01
- `*.substack.com` — exclude after 2023-01-01
- `geeksforgeeks.org` — exclude entirely (pre-LLM low-quality tutorial farm)
- `tutorialspoint.com`, `w3schools.com` — quote-only, no bulk include
- `quora.com` — exclude (low signal-to-noise)
- `linkedin.com/pulse/*` — exclude after 2023-01-01
- `*.blogspot.com` (post-2022) — exclude
- Any path matching `/ai/`, `/chatgpt/`, `/llm/` post-2022 — exclude
- `commoncrawl.org` raw dumps — never use directly for philosophy stage

**Allowlist exceptions** (named pre-LLM authors, override exclusion):
- `danluu.com` (no-license, hand-written — excerpt-only)
- `fasterthanli.me` (Amos Wenger, pre-LLM Rust voice)
- `smallcultfollowing.com` (Niko Matsakis — Rust)
- `drewdevault.com` (CC-BY-SA, allowlisted)
- `jvns.ca` (Julia Evans — no CC, excerpt-only)
- specific author allowlist via GitHub commits ≥ 2020 active before LLM era

**Date-cutoff philosophy:** prefer pre-2022 content where signal-to-noise
is known good. Post-2022 requires domain allowlist OR linter-verified
positive signal.

## §5 Linter rule corpora (Tier E DPO source)

| linter        | rule count | rule docs URL                                       | license               |
| ------------- | ---------- | --------------------------------------------------- | --------------------- |
| clippy        | 814        | https://rust-lang.github.io/rust-clippy/master/index.html | MIT (dual w/ Apache-2.0) |
| ruff          | 900+       | https://docs.astral.sh/ruff/rules/                  | MIT                   |
| golangci-lint | 130+ (linters wrapping thousands of rules) | https://golangci-lint.run/docs/linters/ | GPL-3 (runner — quote rule docs only, do NOT distribute runner) |
| clang-tidy    | 600+       | https://clang.llvm.org/extra/clang-tidy/checks/list.html | Apache-2.0 with LLVM exception |

## §6 Critical errata (from research)

- **Zig zen page does NOT exist.** Original spec assumed an official
  `ziglang.org` page by that name; only a GitHub issue
  (`ziglang/zig#1567`) and unaffiliated `zenofzig.com` exist. Use
  `ziglang.org/learn/overview/` + `ziglang.org/learn/why_zig_rust_d_cpp/`
  instead.
- **ANSI SQL rationale notes do not exist as a free doc.** No
  freely-licensed ANSI/ISO SQL rationale equivalent to C99-Rationale.
  Row deleted from Tier A; Postgres + SQLite docs cover the gap.
- **CERT C upgraded.** Originally listed as "partial / quotable" — actual
  license is CC-BY-4.0 (text) + MIT (code), so full-include with
  attribution. Biggest license win in Tier A.
- **danluu.com has NO license stated.** Spec assumed CC-BY but neither
  the homepage nor `/about/` carries any license statement. Downgrade to
  excerpt-only / allowlist-exception until Dan Luu clarifies.
- **Worse-is-Better is CC-BY-NC-SA-3.0**, not permissive. NC clause
  blocks a commercial LLM training mix; treat as quote-only.
- **SRE Workbook preferred over SRE Book.** Workbook is CC-BY-4.0
  (commercial-OK); the canonical SRE Book is CC-BY-NC-ND 4.0 (NC+ND
  double-block). Bulk-train the Workbook; quote the Book.
- **GitHub status post-mortems URL was wrong.** Original spec pointed at
  `githubstatus.com` (short status updates only). Real post-mortems
  live at `github.blog/tag/github-availability-report/`.
- **k8s.io postmortem repo URL was wrong.** Bare `k8s.io postmortem repo`
  doesn't resolve. Actual path is
  `github.com/kubernetes/community/tree/master/sig-cluster-lifecycle/postmortems`
  (top-level `/postmortems` is 404). Volume is also much smaller than
  implied (1-2 markdown files).
- **AWS PES** lives at `aws.amazon.com/premiumsupport/technology/pes/`
  with per-event URL pattern `/message/<id>/`.
- **Apple HIG is a proprietary blocker.** Excluded entirely — Apple
  Developer license, non-redistributable, even fair-use risky. Cite by
  URL and describe concepts ("Liquid Glass", "blur-as-depth") in our own
  words only.
- **tsgo is Go-based, not Rust.** Project Corsa / TypeScript 7 native
  port is written in Go. Worth correcting in corpus when teaching the
  modern TS toolchain.
- **WCAG 3.0 is Working Draft only.** Not yet normative. Candidate
  Recommendation target Q4 2027; do not teach as production-conformance.
- **`4.1.1 Parsing` was removed in WCAG 2.2.** Don't emit it as a
  required success criterion.
- **FID has been replaced by INP** since March 12, 2024. Tier F-3
  performance section: never emit FID for new corpus.

## §7 Regen note

This file is regenerated from the tier-* and frontend-f*-findings
files. Do NOT hand-edit individual rows — fix the source finding
and re-run `tool/regen_source_manifest.py` (planned tool, not yet
written).

Input docs:
- `papers/tier-a-findings.md`
- `papers/tier-b-findings.md`
- `papers/tier-c-findings.md`
- `papers/tier-e-findings.md`
- `papers/frontend-f1-findings.md`
- `papers/frontend-f2-findings.md`
- `papers/frontend-f3-findings.md`

Regen contract:
1. Each finding's named source with a canonical URL becomes one row.
2. Sources appearing in multiple tiers keep one row; primary tier in the
   `tier` column, secondary tier mentioned in `notes`.
3. License normalised to SPDX (see allowed-value list in the regen-tool
   header, mirroring the constraint list in the consolidation prompt).
4. `tokens (est)` uses order-of-magnitude buckets: `~10K`, `~50K`,
   `~100K`, `~500K`, `~1M`, `~5M`.
5. `fetch_status` is derived from finding-doc verdicts:
   - `✓ ready` — URL valid + license permissive
   - `⚠ pending` — UNVERIFIED in findings OR license-unclear
   - `✗ blocked-by-license` — NC, ND, GPL, proprietary, or no-license
   - `✗ url-broken` — UNVERIFIED + finding says page doesn't resolve
