# tier-e-findings — anti-corpus sourcing for DPO preference pairs

> **Research note for `philosophy` stage, Tier E.** Sources confirmed via web
> fetch / search 2026-05-11. UNVERIFIED tags where ambiguity remains.
> Cross-link: [`coding-philosophy-sources.md §5`](./coding-philosophy-sources.md#5-tier-e--anti-corpus-what-to-not-learn-from),
> [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset).

| field        | value                                                              |
| ------------ | ------------------------------------------------------------------ |
| stage        | `philosophy / Tier E (anti-corpus)`                                |
| role         | negative half of DPO preference pairs                              |
| pairing      | each negative paired with idiomatic positive from Tier A           |
| target yield | ~1-5M pairs (linter-driven dominates; SO + PR diffs supplemental) |

---

## Part 1 — anti-pattern catalog

Per-language tables of high-frequency anti-idioms. The `mining hint` column
points to which **linter rule** (or other automated signal) can flag the
negative form at scale — this is the bridge into Part 3.

### Python

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| mutable default arg | `def f(x, acc=[]): acc.append(x); return acc` | `def f(x, acc=None): acc = [] if acc is None else acc; ...` | ruff `B006` |
| `for i in range(len(x))` | `for i in range(len(xs)): print(i, xs[i])` | `for i, x in enumerate(xs): print(i, x)` | ruff `PLR1736`, pylint `consider-using-enumerate` |
| bare/broad except + pass | `try: foo()\nexcept: pass` | `try: foo()\nexcept SpecificError as e: log.exception(e); raise` | ruff `E722`, `S110`, `BLE001` |
| manual file close | `f = open(p); data = f.read(); f.close()` | `with open(p) as f: data = f.read()` | ruff `SIM115` |
| dict-as-namespace | `cfg = {"host": "x", "port": 8}; cfg["host"]` | `@dataclass\nclass Cfg: host: str; port: int` | manual; ruff `FURB` partial |
| C-style string concat in loop | `s = ""\nfor x in xs: s += str(x)` | `s = "".join(str(x) for x in xs)` | perflint `PERF401`, `PERF402` |
| `if len(x) == 0` / `== None` | `if len(xs) == 0:` / `if x == None:` | `if not xs:` / `if x is None:` | ruff `E711`, `E712`, pylint `C1801` |
| classmethod factory + getter/setter | `class Foo: def get_x(self): return self._x` | `@dataclass class Foo: x: int` (direct attr) | manual review; pylint `unnecessary-getter` (UNVERIFIED in core) |
| `os.path` instead of `pathlib` | `os.path.join(a, b); os.path.exists(p)` | `Path(a) / b; p.exists()` | ruff `PTH` family |
| string-typed enum | `MODE = "fast"  # or "slow"` | `class Mode(StrEnum): FAST = "fast"` | manual; some via `PLR2004` magic value |

### Rust

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| `.unwrap()` on `Result` in lib code | `let f = File::open(p).unwrap();` | `let f = File::open(p)?;` (or `.context(...)?`) | clippy `unwrap_used`, `expect_used` (restriction) |
| gratuitous `Box<dyn Trait>` for struct internals | `struct S { handler: Box<dyn Handler> }` | `struct S<H: Handler> { handler: H }` | manual; clippy `clippy::borrowed_box` partial |
| Java-style getter/setter | `impl Foo { pub fn get_x(&self) -> &T { &self.x } }` | `pub x: T` (or named after the field, no `get_` prefix) | clippy `clippy::wrong_self_convention`, API guidelines C-GETTER |
| factory-pattern abstraction | `trait FooFactory { fn build() -> Box<dyn Foo>; }` | `impl Foo { pub fn new(...) -> Self { ... } }` | manual; AST heuristic on `*Factory` names |
| ignoring `Result` with `let _ =` | `let _ = writeln!(stderr, "...");` | `writeln!(stderr, "...")?;` | clippy `let_underscore_must_use` |
| `if let Some(x) = opt { x } else { default }` | as written | `opt.unwrap_or(default)` | clippy `option_if_let_else`, `manual_unwrap_or` |
| `.clone()` to defeat borrow checker | `let s2 = s.clone(); pass(s2);` | `pass(&s);` (borrow) or restructure | clippy `redundant_clone` |
| `impl Default` written manually | `impl Default for S { fn default() -> Self { S { x: 0 } } }` | `#[derive(Default)]` | clippy `derivable_impls` |
| `match` with single arm + `_ => ()` | `match x { Foo::A => f(), _ => () }` | `if let Foo::A = x { f() }` | clippy `single_match` |
| `String` arg where `&str` suffices | `fn f(s: String) { println!("{s}"); }` | `fn f(s: &str) { ... }` | clippy `ptr_arg`, `needless_pass_by_value` |

### Go

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| `I` prefix on interface names | `type IReader interface { Read(p []byte) (int, error) }` | `type Reader interface { Read(p []byte) (int, error) }` | revive `var-naming`, stylecheck `ST1003` |
| preemptive interface per struct | `type UserService interface {...}; type userServiceImpl struct{...}` | define struct first; let consumer declare narrow interface | manual; `interfacebloat` linter |
| ignoring error with `_` | `result, _ := json.Marshal(v)` | `result, err := json.Marshal(v); if err != nil { return ... }` | `errcheck`, `errcheck-all` |
| naked `panic()` as control flow | `if x == nil { panic("nil!") }` | `if x == nil { return fmt.Errorf("...") }` | `revive panic`, custom |
| `return nil, err` swallow / no wrap | `return nil, err` | `return nil, fmt.Errorf("loading %s: %w", path, err)` | `wrapcheck`, `errorlint` |
| getter named `GetFoo` | `func (s *S) GetFoo() int { return s.foo }` | `func (s *S) Foo() int { return s.foo }` | revive `getter-return`, `golint` |
| init-required struct (zero-value broken) | `cfg := &Config{}; cfg.Init()` then use | zero value usable: `var b bytes.Buffer` works directly | manual / design review |
| empty interface `interface{}` for "any" pre-1.18 | `func f(x interface{}) {}` | `func f(x any) {}` (or generics) | `predeclared` linter |
| unnecessary `else` after `return` | `if x { return a } else { return b }` | `if x { return a }\nreturn b` | revive `indent-error-flow`, `golint` |
| accept concrete, return interface | `func New() Reader; takes *Buffer` | accept interface, return concrete struct | manual (cited in [gocloudstudio idiomatic-go](https://www.gocloudstudio.com/post/writing-idiomatic-go-patterns-that-separate-clean-code-from-java-in-go)) |

### TypeScript

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| `any` to silence errors | `function f(x: any) { return x.foo; }` | `function f(x: { foo: string }) { ... }` or `unknown` + narrow | eslint `@typescript-eslint/no-explicit-any` |
| numeric enum with reverse mapping | `enum Mode { Fast, Slow }` | `type Mode = "fast" \| "slow"` | eslint `@typescript-eslint/prefer-literal-enum-member`; biome lint |
| untagged union "stringly typed" | `type Result = string \| { error: string }` | `type Result = { ok: true; value: string } \| { ok: false; error: string }` | manual (discriminant pattern) |
| `as` cast instead of narrowing | `const u = data as User;` | `if (isUser(data)) { ... }` (type guard) | eslint `@typescript-eslint/consistent-type-assertions` |
| `Function` / `Object` types | `cb: Function` | `cb: (x: number) => void` | eslint `@typescript-eslint/ban-types` |
| classes for what could be a function | `class Greeter { greet(n: string) {...} }` | `function greet(n: string) {...}` | manual; TS handbook "do's and don'ts" |
| Promise without await/return | `async function f() { someAsync(); }` | `await someAsync()` | eslint `@typescript-eslint/no-floating-promises` |
| `// @ts-ignore` blanket | `// @ts-ignore\nfoo(bar)` | `// @ts-expect-error: <reason>` | eslint `@typescript-eslint/ban-ts-comment` |
| `!` non-null assertion in business logic | `user!.name` | narrow with `if (user)` | eslint `@typescript-eslint/no-non-null-assertion` |
| barrel `index.ts` re-exporting world | `export * from "./a"; export * from "./b";` | explicit named exports per consumer | manual / circular import detector |

### C

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| `strcpy` / `strcat` unchecked | `strcpy(dst, src);` | `strlcpy(dst, src, sizeof dst);` or `snprintf` | clang-tidy `cert-str34-c`, `bugprone-unsafe-functions` |
| `memcpy` between incompatible types | `memcpy(&i, p, sizeof i);` (raw byte buffer) | use typed accessor / `memcpy_s` with size check | MISRA C2012 21.15 |
| `malloc` w/o checking NULL | `p = malloc(n); p->x = 1;` | `p = malloc(n); if (!p) return ERR;` | clang-tidy `clang-analyzer-unix.Malloc` |
| integer signedness mixing | `for (int i = 0; i < strlen(s); ...)` | use `size_t`; hoist length | clang-tidy `bugprone-narrowing-conversions` |
| `gets()` | `gets(buf);` | `fgets(buf, sizeof buf, stdin);` | `-Wno-deprecated-declarations` off; CERT MSC24-C |
| macro-as-function unprotected args | `#define SQ(x) x*x` | `static inline int sq(int x){return x*x;}` or `#define SQ(x) ((x)*(x))` | clang-tidy `bugprone-macro-parentheses` |
| goto-only-forward chain for cleanup is fine; goto upward is not | upward goto loops | structured loop + `goto cleanup` only | manual; CERT MEM12-C |
| ignoring `return` of `fread` / `write` | `fread(buf, 1, n, f);` | check return == n | clang-tidy `bugprone-unused-return-value` |
| sizeof on pointer mistaken for array | `sizeof(p)` where `p` is `char *` | `sizeof(arr)` only on array; pass length | clang-tidy `bugprone-sizeof-expression` |
| signed integer overflow assumed wraparound | `int x = INT_MAX + 1;` | use unsigned, or check before add | UB sanitizer; CERT INT32-C |

### Zig

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| hidden allocator (global) | function allocates without taking `Allocator` arg | every alloc takes `allocator: std.mem.Allocator` | `zig build` style; manual lint |
| missing `errdefer` after alloc | `const r = try a.create(R); try setup(r);` (leak on error) | `const r = try a.create(R); errdefer a.destroy(r);` | manual; `std.testing.allocator` leak report |
| catching error to ignore | `foo() catch {};` | `foo() catch |e| return e;` or explicit log | manual review |
| C-style explicit cast spam | `@intCast(i32, x)` (old syntax / unneeded) | use result-location type inference | `zig fmt` + version compat |
| `unreachable` as "should not happen" | `if (x > 10) unreachable;` in lib code | return `error.OutOfRange` | manual; semantic |
| forgot `defer` for cleanup | open then return without close | `defer file.close();` right after open | manual |
| oversized return-by-value structs | returning huge struct by value | take output pointer or use allocator | manual; perf |
| `[]const u8` confused with C string | passing slice where null-terminated expected | use `[:0]const u8` or `std.mem.span` | manual |

### SQL

| pattern | negative example | idiomatic positive | mining hint |
| --- | --- | --- | --- |
| `SELECT *` in app code | `SELECT * FROM users WHERE id = ?` | `SELECT id, email, created_at FROM users WHERE id = ?` | sqlfluff `L044`; pgsanity |
| implicit (comma) join | `SELECT * FROM a, b WHERE a.id = b.aid` | `SELECT ... FROM a JOIN b ON b.aid = a.id` | sqlfluff `L032` |
| N+1 via loop-of-queries (app side) | `for u in users: db.exec("SELECT ... WHERE uid=?", u.id)` | single `WHERE uid IN (...)` or JOIN | tracing / ORM lint (django `nplusone`) |
| string concatenation for params | `f"SELECT * FROM u WHERE name='{n}'"` | parameterised: `cur.execute("... WHERE name=%s", (n,))` | bandit `B608`; ruff `S608` |
| no `LIMIT` on exploratory query | `SELECT * FROM logs` | `SELECT ... FROM logs ORDER BY ts DESC LIMIT 100` | manual; query-plan review |
| `WHERE col != NULL` | `WHERE deleted_at != NULL` | `WHERE deleted_at IS NOT NULL` | sqlfluff; sql-lint |
| function on indexed col in WHERE | `WHERE LOWER(email) = ?` (kills index) | functional index or store normalised | EXPLAIN-driven; manual |
| `ORDER BY` ordinal | `ORDER BY 1, 3` | `ORDER BY created_at, name` | sqlfluff `L054` |
| `DISTINCT` used to mask bad join | `SELECT DISTINCT ...` | fix join cardinality | manual; review |
| stored boolean-as-string | `status = 'true'` | `status BOOLEAN` | schema review |

---

## Part 2 — sourcing

Per-source: URL, license, volume, mining method, risk. Sorted by yield potential.

### Linter rule corpora (rationale text = positive; flagged code = negative)

| field | value |
| --- | --- |
| URL | https://rust-lang.github.io/rust-clippy/master/index.html |
| identity | clippy lint catalogue |
| volume | **814 lints** (verified 2026-05-11). ~30-40% machine-applicable |
| license | MIT / Apache-2.0 (rust-clippy repo) |
| mining method | scrape lint docs → use `"What it does"` + `"Why is this bad"` as **positive rationale**; use `"Example"` + `"Use instead"` blocks as direct DPO `(rejected, chosen)` pair |
| risk | very low — official, permissive, written by the language team |
| note | restriction-category lints (`unwrap_used`, `expect_used`) catch the deepest anti-idioms |

| field | value |
| --- | --- |
| URL | https://docs.astral.sh/ruff/rules/ |
| identity | ruff Python lint rules |
| volume | **900+ rules** (verified). Safe-fix and unsafe-fix subsets tagged |
| license | MIT (astral-sh/ruff) |
| mining method | identical to clippy: rule pages already contain a "bad" / "good" code pair → direct DPO `(rejected, chosen)`. Also: run ruff `--fix --unsafe-fixes` on `the-stack-v2` Python subset and harvest each diff |
| risk | low; safety-tier flag (`safe` vs `unsafe`) lets us filter the unsafe fixes from DPO pairs to avoid behaviour-changing pairs |

| field | value |
| --- | --- |
| URL | https://golangci-lint.run/docs/linters/ |
| identity | golangci-lint aggregator (revive, stylecheck, errcheck, gosimple, ineffassign, …) |
| volume | 130+ linters wrapping ~thousands of rules |
| license | GPL-3 (golangci-lint runner) but underlying linters MIT/BSD — **rule docs and rationales are independently licensed**; quote rule text under fair use, do **not** distribute runner binary in dataset |
| mining method | run on `the-stack-v2` Go subset → diff before/after; rule docs as rationale |
| risk | medium — GPL on runner means we can't redistribute the tool, only its outputs |

| field | value |
| --- | --- |
| URL | https://clang.llvm.org/extra/clang-tidy/checks/list.html (UNVERIFIED domain — known to exist) |
| identity | clang-tidy checks (C/C++) — covers CERT, MISRA, bugprone |
| volume | 600+ checks |
| license | Apache-2 with LLVM exception |
| mining method | run on the-stack-v2 C subset; CERT/MISRA categories already map to anti-idiom rationale |
| risk | low |

### StackExchange data dump

| field | value |
| --- | --- |
| URL | https://archive.org/details/stackexchange (historical), recent dumps at https://archive.org/details/stackexchange_20251231 + Academic Torrents `0d1d597fa78...` (2025-12-31) |
| identity | Stack Exchange Q&A dump, all sites |
| volume | Code-heavy sites (SO, codereview.SE) — hundreds of millions of posts; tens of millions contain code |
| license | **CC BY-SA 4.0** on user content. **BUT**: Stack Overflow added a 2024 click-through clause stating "this file is being provided … for projects that do not include training a large language model (LLM)". Critics argue this contradicts CC-BY-SA's no-additional-restrictions clause (devclass, feep.dev). Decision required: |
| risk | **HIGH-ambiguity**. Three options: (a) treat CC-BY-SA as overriding → include + attribute; (b) treat ToS as binding → exclude; (c) use the **community torrent mirror** that exists pre-2024 and operate under the older terms. Recommend: legal review before bulk-include. Mirror: Academic Torrents `9132fa0997b...` (2024-12-31) and earlier are pre-clause |
| mining method | (1) pair `(low-voted, negative-score)` answer vs `(accepted, top-voted)` answer on **same question** as a natural DPO pair. (2) accepted-but-low-voted is most signal — community judged it wrong. (3) filter to posts with code blocks ≥ 3 lines |
| alt access | BigQuery `bigquery-public-data.stackoverflow` (quarterly updates) — Google's hosting; same content; **same license question applies** |
| est yield | ~1-3M code DPO pairs if we filter for code-bearing questions in {python, rust, go, typescript, c, sql} tags with ≥ 2 answers and vote-diff ≥ 5 |

### GitHub PR review diffs

| field | value |
| --- | --- |
| URL | https://api.github.com (REST); https://docs.github.com/graphql |
| identity | PR diff sequences: rejected revision → accepted revision; PR review comments |
| volume | billions of PRs across permissive repos in the-stack-v2 |
| license | per-repo (filter to MIT/Apache/BSD via SPDX) |
| mining method | (1) within a PR, take commit-N (force-pushed away) vs commit-N+1 as a (rejected, accepted) pair when commit-N has a "request-changes" review attached. (2) for each inline review comment, treat pre-comment hunk vs post-comment hunk in same file as DPO pair. (3) text of review comment = rationale |
| risk | medium — code itself is licensed per-repo (filter); review comments are arguably uncopyrightable but err on permissive-repo filter |
| rate-limit | search API: 30 req/min; code search: 10 req/min; clone-and-walk-git is unrate-limited |
| precedent | Microsoft CodeReviewer dataset (arxiv 2203.09095) — 116K samples mined this way, 9 langs. Available on Zenodo. **Direct reuse possible** (license: their dataset CC-BY-NC-SA 4.0 — UNVERIFIED, check) |

### Reviewdog / linter-bot PR comments

| field | value |
| --- | --- |
| URL | https://github.com/reviewdog/reviewdog |
| identity | PRs where reviewdog/sonarcloud/codacy left auto-comments with line-level lint hits |
| volume | UNVERIFIED at scale; reviewdog appears in tens of thousands of public repos |
| license | per-repo (permissive filter) |
| mining method | search PR comments authored by reviewdog/sonarcloud-bots → comment text is rule rationale, file+line is negative example, commit that resolved the comment is positive example |
| risk | low |
| est yield | 100K-500K pairs |

### LeetCode / Codeforces discussions

| field | value |
| --- | --- |
| URL | leetcode.com/problems/<slug>/solutions, codeforces.com submissions |
| identity | accepted vs WA submissions; high-voted vs low-voted solutions |
| volume | LeetCode: ~3.5K problems × dozens of solutions each; Codeforces: 369K source files mined in COFO (arxiv 2503.18251) |
| license | **NOT permissive** — LeetCode ToS forbids scraping; Codeforces robots.txt forbids; CF has no declared license at all |
| mining method | use existing **derivative datasets**: TACO (arxiv 2312.14852), COFO, LeetCodeDataset (arxiv 2504.14655) — each pre-licensed by authors |
| risk | **HIGH** — using these datasets pushes the license decision to the dataset author; acceptable but flag in our license audit. Direct scraping = no-go |
| signal type | accepted/WA is correctness, not idiomaticity → less directly useful for Tier E than SO |

### Excluded: medium.com, dev.to, hashnode, *.substack.com (post-2022)

See "Pollution / exclusion list" below.

---

## Part 3 — auto-pairing strategy

| strategy | pros | cons | est yield (pairs) | confidence |
| --- | --- | --- | --- | --- |
| **linter-driven (clippy/ruff/golangci/clang-tidy autofix)** — run on the-stack-v2 → `(before_diff, after_diff)` + rule rationale as context | very high signal; rationale is canonical; permissive licenses across the board; **already-deduped corpus**; deterministic | only catches anti-patterns the linter encodes (no "design smell" capture); some autofixes are unsafe — gate on `safe`-only | **2-5M** (the-stack-v2 has 3.28B files; even 0.1% triggers ≥1 lint = 3M pairs) | HIGH |
| **lint-rule doc scraping** — each rule's example block is a hand-curated `(bad, good)` pair | tiny corpus (~3K total rules), but extremely high signal; doubles as a teaching signal for canon | small absolute count | ~3K | HIGH |
| **StackExchange vote-delta pairs** — same question, top-voted vs accepted-but-low-voted (or downvoted-but-working) | natural human preference signal; cross-paradigm (catches "Java-in-Python" style) | license ambiguity (2024 LLM clause); code-quality is noisy (many low-voted answers are wrong, not just unidiomatic) | ~1-3M (code-tagged Q's with ≥2 answers and ≥5 vote-diff) | MED |
| **PR revision pairs** — rejected commit → accepted commit in same PR, where review comment exists | rationale is natural language from a real reviewer; captures design smells linters miss | hard to align hunks across rewrites; many force-pushes are unrelated fixups; needs PR-tracking | 100K-500K | MED |
| **CodeReviewer dataset reuse** (Microsoft, arxiv 2203.09095) | pre-mined, 116K samples, 9 langs, pre-aligned | license UNVERIFIED (probably CC-BY-NC-SA → derivative concern); some quality issues per arxiv 2502.02757 ("Too Noisy To Learn") | 116K direct | HIGH (provenance) |
| **bot-comment harvesting** (reviewdog, sonarcloud, codacy on public PRs) | rationale + line-level pinpoint; matches PR force-push to fix → after-state | bot coverage uneven across repos; mostly overlaps with linter-driven | 100K-500K | MED |
| **LLM-judge synthesis** (have a frontier model rewrite "translated" code into idiomatic) | scales to any pattern; can target known gaps | **circular pollution risk** — we are mining LLM output to train an LLM; violates Shumailov "Curse of Recursion"; degrades over time | uncapped, but **DO NOT USE** for v0.1 | LOW (anti-recommendation) |

**Recommended composition for v0.1 (~3M pairs target):**

- 60% linter-driven autofix diffs on the-stack-v2 (Python via ruff, Rust via clippy, Go via golangci-lint, C via clang-tidy)
- 15% lint-rule doc example pairs (hand-curated by the rule authors — pure gold)
- 15% StackExchange vote-delta (if legal review clears it; otherwise drop to 0%)
- 10% CodeReviewer dataset + bot-comment harvest

**Pairing format for DPO:**

```json
{
  "context": "<lint rule rationale OR review-comment text OR question body>",
  "chosen":   "<idiomatic positive code>",
  "rejected": "<anti-idiomatic negative code>",
  "source":   "ruff:B006 | clippy:unwrap_used | so:<post_id> | pr:<owner/repo#pr/file:hunk>",
  "lang":     "python|rust|go|ts|c|zig|sql",
  "applicability": "safe|unsafe"
}
```

---

## Pollution / exclusion list

Domains and date-cutoffs to **bulk-filter** during ingest. Driven by AI-slop
prevalence (Pangram, Originality reports) and known LLM-tutorial flood.

| domain | rule | rationale | source |
| --- | --- | --- | --- |
| `medium.com` (incl. all `*.medium.com`) | **exclude entirely after 2023-01-01** | Medium CEO admits AI-slop up "10x" in 2024; Pangram: 47% AI-gen; Originality: 40%+ LLM output | [pivot-to-ai 2024-11](https://pivot-to-ai.com/2024/11/16/substack-readers-may-be-paying-for-ai-generated-newsletters-medium-full-of-slop-too/) |
| `dev.to` | exclude after 2023-01-01 | same vector as medium; lower verification | (inferred) |
| `hashnode.com`, `*.hashnode.dev` | exclude after 2023-01-01 | same | (inferred) |
| `*.substack.com` | exclude after 2023-01-01 | confirmed AI slop in newsletters | same pivot-to-ai source |
| `geeksforgeeks.org` | exclude entirely | known pre-LLM low-quality tutorial farm; many copy-pasted SO answers without attribution | manual |
| `tutorialspoint.com`, `w3schools.com` (code examples only) | quote-only, no bulk include | low-idiom, error-prone | manual |
| `quora.com` (code answers) | exclude | low signal-to-noise | manual |
| `linkedin.com/pulse/*` | exclude after 2023-01-01 | confirmed AI-tutorial vector | manual |
| `*.blogspot.com` (post 2022) | exclude | mass-spam vector | manual |
| any subdomain matching `/ai/`, `/chatgpt/`, `/llm/` in path | exclude post-2022 | high pollution prior | heuristic |
| `commoncrawl.org` raw dumps | **never use directly** for philosophy stage; needs heavy filter | by Nov 2024 AI-gen content roughly equal to human-written in their sample (Graphite/Surfer analysis) | [Axios 2025-10-14](https://www.axios.com/2025/10/14/ai-generated-writing-humans) |

**Allowlist for blog content** (override exclusion):
- danluu.com (CC-BY, hand-written)
- fasterthanli.me, smallcultfollowing.com (named Rust authors, pre-LLM voice)
- specific author allowlist via GitHub `commits` history check (≥ 2020 active before LLM era)

**Date-cutoff philosophy:** prefer pre-2022 content where signal-to-noise is
known good. For post-2022, require domain allowlist OR linter-verified
positive signal.

**Cited research on pollution:**
- Shumailov et al., "AI models collapse when trained on recursively generated data" (Nature 2024) — confirms training on synthetic-of-synthetic degrades; motivates strict source filter
- "A Note on Shumailov et al." (arxiv 2410.12954) — qualifies severity but does not refute mechanism
- Mozilla Foundation, "Training Data for the Price of a Sandwich" — Common Crawl's role in shaping LLM training corpora
- "Too Noisy To Learn" (arxiv 2502.02757) — code review data has quality issues; supports our CodeReviewer-dataset-with-filter approach

---

## Open questions

- [ ] **StackExchange license decision.** The 2024 LLM-training clause vs CC-BY-SA 4.0 conflict is unresolved. Decision needed before mining: (a) treat CC as overriding → include + attribute, (b) use only pre-2024 community mirrors, (c) exclude entirely. Affects ~1-3M pairs of yield.
- [ ] **CodeReviewer dataset license** UNVERIFIED — confirm on Zenodo before reuse.
- [ ] **clang-tidy total check count and URL** UNVERIFIED — confirm 600+ figure.
- [ ] **Codeforces / LeetCode** — use derivative datasets only (TACO/COFO/LeetCodeDataset). Confirm each derivative's redistribution terms before include.
- [ ] **Zig anti-pattern automation** — no mature linter exists comparable to clippy. Manual curation + `zig fmt` diffs only. Yield will be tiny for Zig. Accept or seek alternative (write hexa custom lints? defer to native-first Tier A weighting?).
- [ ] **SQL dialect-specific rules** — sqlfluff handles many but Postgres-specific anti-idioms (e.g. `varchar(n)` vs `text`) may need custom rules. Source: Postgres docs (already in Tier A).
- [ ] **"Design smell" anti-patterns** (factory overuse, premature abstraction) — these are not linter-flaggable. Only PR-review-comment mining catches them. Lower yield, higher value — invest in PR-mining tooling?
- [ ] **Cross-lang anti-patterns** ("Java-in-Rust", "OOP-in-Go") — no automated detector. Could train a classifier on the few hundred labeled cases from quii's "Learn Go with tests" anti-patterns chapter + manual labels, then bootstrap. Defer to v0.2.
- [ ] **DPO-pair difficulty stratification** — should we deliberately mix easy linter-pairs with hard PR-review-pairs, or train in curriculum? Affects §FLOW Stage 3 design (out of scope for sourcing, but relevant).

---

## Cross-link

- Tier definitions: [`papers/coding-philosophy-sources.md`](./coding-philosophy-sources.md)
- Stage spec: [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset), Stage 3 [`§FLOW`](../docs/code-llm.md#flow--training-stages)
- Sourcing pipeline TODO: [`coding-philosophy-sources.md §6`](./coding-philosophy-sources.md#6-sourcing-pipeline-research-todos)
