# tier-c-findings — post-mortem canon source verification

> **Draft v0.0.** Verification report for [`papers/coding-philosophy-sources.md` §3 Tier C](./coding-philosophy-sources.md#3-tier-c--post-mortem-canon-operational-philosophy).
> Verified 2026-05-11 via WebFetch + WebSearch. Token estimates are
> rough (assume ~4 chars/tok, English prose).

| field | value |
| --- | --- |
| stage | `philosophy` (Tier C subset) |
| target signal | blast-radius reasoning, recovery, measure-twice-cut-once |
| license bar | permissive **OR** vendor-published (fair-use research) |
| top risk | (a) anti-AI-training ToS on vendor blogs, (b) PII / blame leakage |

---

## §1 Verified sources (originally listed)

### AWS Builders' Library

| field | value |
| --- | --- |
| URL | https://aws.amazon.com/builders-library/ |
| License / terms | **proprietary**, "© 2026 Amazon Web Services, Inc. All rights reserved." Standard AWS site terms. FAQ says "available for anyone — similar to any other public case study" but **no explicit reuse grant**. robots.txt has no AI-bot blocks (catch-all `*` only). |
| Volume | ~60+ long-form articles (Operations Excellence, Architecture, Software Delivery, Mechanical Sympathy categories). Index loads dynamically — couldn't enumerate via WebFetch shim. Est. ~400-700 k tok. |
| Quotability | **excerpt + cite** — full ingest is legally borderline. Treat as fair-use research-only; **flag for commercial-use risk**. |
| PII risk | **LOW** — articles are pattern/principle-shaped ("Caching challenges and strategies", "Static stability using AZs"). Authored by senior engineers but content is not blame-attributing. |
| Status | **VERIFIED** |

Top-shelf operational philosophy — load-shedding, jitter/backoff, control-plane vs data-plane, "constant work" pattern. Highest signal-per-token in Tier C. Recommend ingest with attribution and a `vendor-fair-use` canon tag.

### Google SRE Book (free HTML edition)

| field | value |
| --- | --- |
| URL | https://sre.google/sre-book/table-of-contents/ |
| License / terms | **CC BY-NC-ND 4.0** — Attribution, NonCommercial, NoDerivatives. © 2017 Google / O'Reilly. |
| Volume | 34 chapters + appendices. Est. ~400-500 k tok. Key chapters: Ch.14 Managing Incidents, Ch.15 Postmortem Culture, Ch.16 Tracking Outages, Ch.6 SLOs, Ch.22 Cascading Failures. |
| Quotability | **excerpt only legally**. NC clause is the blocker — training a commercial-grade model arguably violates it; training a research artifact is gray. ND clause means tokenization may itself be a "derivative". |
| PII risk | **LOW** — Google deliberately de-personalizes their canonical "postmortem-as-learning" framing. Some named authors but no blame attribution. |
| Status | **VERIFIED — license is the binding constraint** |

The canonical text for blameless-postmortem culture. Note: the **Site Reliability Workbook** (https://sre.google/workbook/) and **classroom** materials are **CC BY 4.0** (commercial-OK) per Google's site signal — *prefer the Workbook for training*. Re-check per-page footer before ingest.

### GitHub status post-mortems

| field | value |
| --- | --- |
| URL (status) | https://www.githubstatus.com/history — **short** status updates only. |
| URL (real post-mortems) | https://github.blog/tag/github-availability-report/ — monthly RCA roll-ups. |
| Historical RCAs | https://github.blog/ — search "post-incident analysis", e.g. https://github.blog/news-insights/company-news/oct21-post-incident-analysis/ |
| License / terms | "© 2026 GitHub, Inc." — proprietary. robots.txt has no AI-bot block (catch-all `User-agent: *` with empty `Disallow:` permits all). |
| Volume | ~18 monthly Availability Reports (Jan-2025 → Mar-2026) + ~10 named post-incident analyses going back to 2014. Est. ~80-150 k tok. |
| Quotability | **excerpt** — fair-use research. |
| PII risk | **MEDIUM** — availability reports name internal teams (e.g. "the database team rolled out…"); rarely names individuals. Easy to filter. |
| Status | **VERIFIED — URL in source list (`githubstatus.com`) is the wrong one; use `github.blog/tag/github-availability-report/`.** |

### Cloudflare blog post-mortems

| field | value |
| --- | --- |
| URL (canonical tag) | https://blog.cloudflare.com/tag/post-mortem/ — **prefer this over `tag/outage`** (the post-mortem tag is the engineering-canonical one). |
| Also useful | https://blog.cloudflare.com/tag/outage/ — overlapping but smaller set. |
| License / terms | Cloudflare blog robots.txt **explicitly permits training**: `ai-train=yes, search=yes, ai-input=yes`. Site copyright remains "© Cloudflare". |
| Volume | ~20+ posts under `post-mortem` tag, range Oct-2023 → May-2026. With pagination, est. 40-60 posts. Each post is long-form (~3-8 k tok). Total est. ~200-400 k tok. |
| Quotability | **full ingest is safe** — explicit ai-train signal is the strongest license clarity in Tier C. |
| PII risk | **LOW** — Cloudflare post-mortems attribute by author byline but do not blame individuals; root causes are framed systemically. |
| Status | **VERIFIED — highest-clarity license in Tier C.** |

### danluu post-mortem roundups

| field | value |
| --- | --- |
| URL (essay) | https://danluu.com/postmortem-lessons/ |
| URL (repo) | https://github.com/danluu/post-mortems |
| License / terms | **No explicit license** on danluu.com (robots.txt only contains a sitemap). The repo has no LICENSE file either. Source list called this "CC-BY" — **that claim is UNVERIFIED**. |
| Volume | Essay: ~10 k tok. Repo: 12.1 k stars, ~389 commits, ~100s of linked post-mortems, but the repo itself is mostly *links*, not text. PR backlog flagged ("Sorry for the delay merging PRs"). |
| Quotability | Essay: excerpt-only until license confirmed. Repo: useful as a **link-spine for crawler seeds**, not as text. |
| PII risk | **LOW** for the essay. The linked third-party post-mortems vary. |
| Status | **PARTIAL — license claim in source list is wrong. Treat as research-fair-use until danluu clarifies.** |

### k8s.io postmortem repo

| field | value |
| --- | --- |
| URL (claimed) | The source list's bare `k8s.io postmortem repo` doesn't resolve. The actual location is **https://github.com/kubernetes/community/tree/master/sig-cluster-lifecycle/postmortems** (top-level `/postmortems` is 404). |
| License / terms | **Apache-2.0** (parent `kubernetes/community` repo). Cleanest license in Tier C. |
| Volume | **Tiny — only 1-2 markdown files** (`kubeadm-1.6.md` is the canonical one). Est. ~5-10 k tok. |
| Quotability | **full ingest, no restriction.** |
| PII risk | **LOW** — files name SIGs and PRs but no blame. |
| Status | **VERIFIED but oversold in source list — the volume is much smaller than implied.** |

### AWS service event summaries (PES)

| field | value |
| --- | --- |
| URL | https://aws.amazon.com/premiumsupport/technology/pes/ |
| License / terms | Proprietary, "© 2026 AWS". 5-year retention guaranteed. |
| Volume | ~10-15 archived PES (DynamoDB Oct-2025, Kinesis Jul-2024, Lambda Jun-2023, S3-2017 et al). Each is ~2-5 k tok. Total est. ~30-60 k tok. |
| Quotability | **excerpt** — fair-use research. |
| PII risk | **LOW** — AWS PES are scrupulously blameless; no individuals named. Gold-standard format. |
| Status | **VERIFIED — URL pattern is `/message/<id>/` for individual events.** |

---

## §2 New finds (★)

### ★ Google SRE Workbook

| field | value |
| --- | --- |
| URL | https://sre.google/workbook/table-of-contents/ |
| License / terms | **CC BY 4.0** per Google's SRE materials signal (verify per-page) — *commercial-OK*, unlike the SRE Book which is BY-NC-ND. |
| Volume | ~25 chapters, ~300-400 k tok. |
| Quotability | **full ingest** if CC BY 4.0 confirmed. |
| PII risk | **LOW** — case studies from Evernote, Home Depot, NYT; no blame. |
| Status | **★ STRONGLY RECOMMENDED — preferred over SRE Book for license clarity.** |

This is the most under-rated source. License is permissive enough to bulk-ingest, and the content is hands-on post-mortem / incident-management material. Should sit at the top of the ingestion order.

### ★ GitHub Availability Reports (monthly)

| field | value |
| --- | --- |
| URL | https://github.blog/tag/github-availability-report/ |
| License / terms | proprietary, no AI-bot block. |
| Volume | ~18 monthly + growing, ~3-5 k tok each ≈ 60-90 k tok. |
| Quotability | excerpt / fair-use. |
| PII risk | **LOW-MEDIUM**. |

Already covered above — surfaced as ★ because the original source list pointed to the wrong (status-page) URL.

### ★ Discord Engineering blog (post-mortems)

| field | value |
| --- | --- |
| URL | https://discord.com/category/engineering — e.g. "Behind the Scenes of the 3/25/26 Voice Outage" |
| License / terms | proprietary, "© Discord". robots.txt not separately verified. |
| Volume | ~3-5 substantial post-mortems known (2020 outage, 2024 Cassandra-to-Scylla migration, 2026 voice outage). Est. ~30-50 k tok. |
| Quotability | excerpt. |
| PII risk | **LOW** — systemic framing. |

### ★ Stripe — incident retros (sparse but high-signal)

| field | value |
| --- | --- |
| URL | https://stripe.com/blog/engineering — search "incident" / "2019-07-10" |
| License / terms | "© 2026 Stripe, LLC". robots.txt has no AI-bot block. |
| Volume | **Low**. Stripe rarely publishes formal post-mortems; the 2019-07-10 narrative (David Singleton) is the canonical one. Most Stripe incident lore lives in Increment magazine + USENIX talks. Est. ~10-20 k tok. |
| Quotability | excerpt. |
| PII risk | **LOW** — written for systemic learning. |

### ★ Heroku post-mortems

| field | value |
| --- | --- |
| URL | https://www.heroku.com/blog/ — search "postmortem" / "incident review" / "outage" |
| License / terms | "© 2026 Salesforce, Inc." proprietary. |
| Volume | ~5-8 named post-mortems (Apr-2022 review, Jun-2025 24-hr outage, Apr-21 outage, et al.). Est. ~30-50 k tok. |
| Quotability | excerpt. |
| PII risk | **LOW** — but the June-2025 case is a textbook "unsafe auto-update" failure mode worth keeping verbatim. |

### ★ Datadog March 2023 outage series

| field | value |
| --- | --- |
| URLs | https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/ + three "deep dive" follow-ups (incident response, platform impact, platform recovery) |
| License / terms | proprietary, "© Datadog". |
| Volume | 4 long-form posts + USENIX SRECon talk (Laura de Vesine). Est. ~25-40 k tok. |
| Quotability | excerpt. |
| PII risk | **LOW** — systemic and remarkably honest. Names a few engineers by role (Incident Commander) but not in a blame context. |
| Why valuable | One of the best **multi-region cascade-failure** post-mortems in print. The Cilium-CNI / systemd-networkd interaction story is canon-grade material on blast-radius reasoning. |

### ★ Fastly — June 8 2021 outage

| field | value |
| --- | --- |
| URL | https://www.fastly.com/blog/summary-of-june-8-outage |
| License / terms | proprietary. |
| Volume | 1 canonical post (~3-5 k tok). Other Fastly post-mortems are sparse. |
| Quotability | excerpt. |
| PII risk | **LOW**. |
| Why | Textbook example of "valid customer config triggers latent bug → 85% network blast radius in 49 min". Pairs perfectly with the Cloudflare November 2025 post-mortem (config-induced cascade). |

### ★ Azure Post-Incident Reviews (PIRs)

| field | value |
| --- | --- |
| URL | https://azure.status.microsoft/en-us/status/history/ |
| License / terms | "© 2026 Microsoft" proprietary, 5-year retention. |
| Volume | dozens of PIRs spanning multiple years. Each is a full RCA essay. Est. ~150-300 k tok. |
| Quotability | excerpt. |
| PII risk | **LOW** — Microsoft PIR template is blameless by construction. |
| Why | Missed entirely in the original list. **Volume rivals AWS PES.** |

### ★ GCP incidents.json archive

| field | value |
| --- | --- |
| URLs | https://status.cloud.google.com/summary + machine-readable https://status.cloud.google.com/incidents.json |
| License / terms | "© 2026 Google" — no explicit license. |
| Volume | hundreds of incidents historically; depth varies (some 1-line, some full RCA). Est. machine-parseable ~100-200 k tok of RCA prose. |
| Quotability | excerpt. |
| PII risk | **LOW**. |
| Why | The `incidents.json` endpoint is a **trivially ingestible structured dump** — easier to corpus-build than HTML scraping. |

### ★ PyPI incident-report blog

| field | value |
| --- | --- |
| URL | https://blog.pypi.org/ |
| License / terms | PyPI is part of PSF — likely PSF terms. Posts authored by Trail of Bits engineers carry implicit research-fair-use. |
| Volume | ~5-10 named incident reports (Organization Team Privileges Apr-2025, LiteLLM/Telnyx supply-chain Apr-2026, several token-exfil events). Est. ~15-25 k tok. |
| Quotability | excerpt. |
| PII risk | **MEDIUM** — does name external reporters and (sometimes) attackers. Strip names. |
| Why | Distinct genre: **supply-chain / registry** post-mortems, not infra-outage. Important for teaching defense-in-depth philosophy. |

### ★ GitLab Handbook — incident management section

| field | value |
| --- | --- |
| URL | https://handbook.gitlab.com/handbook/engineering/incident-management/ |
| License / terms | **CC BY-SA 4.0** (GitLab Handbook is famously CC-BY-SA; verify per-page). |
| Volume | Process docs, not many actual post-mortems. GitLab's biggest post-mortem (2017 db1 incident) lives separately on the blog. |
| Quotability | full ingest if CC-BY-SA confirmed. |
| PII risk | **LOW** for process docs. The 2017 db1 incident *does* name `team-member-1` publicly — easy to mask. |

### ★ Kubernetes Failure Stories (k8s.af)

| field | value |
| --- | --- |
| URL | https://k8s.af/ (also https://github.com/hjacobs/kubernetes-failure-stories) |
| License / terms | Repo: not explicitly stated; community-contributed. |
| Volume | ~70+ curated failure stories, each linking to external talk/blog/video. Est. ~100-200 k tok if you follow links and ingest the texts (not the index itself). |
| Quotability | as a **seed list** for crawling; not for direct text ingest. |
| PII risk | varies by linked source. |

### ★ Surfing Complexity (Lorin Hochstein)

| field | value |
| --- | --- |
| URL | https://surfingcomplexity.blog/ + `/category/systems/incidents/` |
| License / terms | personal blog, no explicit license. |
| Volume | hundreds of posts on incident analysis through a resilience-engineering lens. Est. ~200-400 k tok. |
| Quotability | excerpt only. |
| PII risk | **LOW** — academic-style analysis, no blame. |
| Why | One of the few sources that meta-analyzes post-mortems through Woods/Cook/Dekker frameworks. Distinct signal vs. raw vendor RCAs — teaches **how to read** a post-mortem. |

### ★ awesome-postmortem (saystone) + awesome-tech-postmortems (snakescott)

| field | value |
| --- | --- |
| URLs | https://github.com/saystone/awesome-postmortem · https://github.com/snakescott/awesome-tech-postmortems |
| License / terms | saystone: **CC0** · snakescott: **CC BY 4.0** |
| Volume | small (7 + ~20 entries) but useful as additional **link-spines**. |
| Quotability | full ingest of the list text; the *linked* post-mortems retain their own licenses. |
| PII risk | low (it's a link list). |
| Status | both **stale** (last updates 2019-2021) — use as seed, not living source. |

### ★ Increment Magazine archive (Stripe-funded)

| field | value |
| --- | --- |
| URL | https://increment.com/issues/ |
| License / terms | "© Stripe" proprietary. Now **dormant** (last issue Nov-2021). |
| Volume | 19 issues, ~250 stories, several specifically on incidents/on-call/SRE. Est. ~300-500 k tok across the archive. |
| Quotability | excerpt — fair-use. |
| PII risk | **LOW** — magazine-shaped, edited. |
| Why | A surprisingly large reservoir of high-quality operational-philosophy essays. Dormant = corpus is **stable** (no moving target). |

---

## §3 Sources investigated and rejected / weak

| source | verdict | reason |
| --- | --- | --- |
| Honeycomb blog | weak | publishes incident-response *theory* but not its own post-mortems |
| Slack engineering | weak | mostly feature posts; no public post-mortem cadence found |
| Datadog engineering (general) | strong only for Mar-2023 series | non-Mar-2023 posts are mostly product content |
| GitHub Status page (`githubstatus.com/history`) | reject | short status updates only; the real post-mortems live on `github.blog` |
| "morethanseven.net" (from prompt) | not found as a postmortem source | likely a confusion; could not verify any postmortem roundup there |
| `kubernetes/community/postmortems` (top-level) | 404 | actual path is `/sig-cluster-lifecycle/postmortems` |

---

## §4 Ingestion order

Sorted by **(license clarity × volume × signal)**. Tier within Tier C, top = ingest first.

| order | source | one-line reason |
| --- | --- | --- |
| 1 | **Cloudflare blog `/tag/post-mortem/`** | Only Tier C source with explicit `ai-train=yes`. High volume, blameless framing. |
| 2 | **★ Google SRE Workbook** | CC BY 4.0 (commercial-OK), large volume, canonical operational philosophy. Pair with sre.google/classroom. |
| 3 | **★ Azure PIRs** | Large volume, blameless-by-template, 5-year retention. Fair-use safe. |
| 4 | **AWS Builders' Library** | Highest signal/tok of the lot. License gray, ingest as fair-use research with attribution. |
| 5 | **AWS PES** (`/premiumsupport/technology/pes/`) | Gold-standard blameless RCAs, small but every entry is high-signal. |
| 6 | **GitHub Availability Reports** (`github.blog/tag/...`) | Monthly cadence, replaceable URL fixed; medium volume. |
| 7 | **★ Datadog Mar-2023 series** | 4 deep-dive posts on a single cascade — best teaching set for blast-radius. |
| 8 | **★ Surfing Complexity** | Meta-analysis layer; teaches the *reading* of post-mortems. |
| 9 | **★ GCP `incidents.json`** | Structured machine-readable feed; easy ingest, variable depth. |
| 10 | **Google SRE Book** | Use sparingly — BY-NC-ND is the harshest license here. Excerpt for canon quotes (blameless-postmortem ch.15) only. |
| 11 | **★ Heroku post-mortems** | Small but classic "unsafe auto-update" failure-mode stories. |
| 12 | **★ Discord engineering** | Voice/session post-mortems; small but vivid. |
| 13 | **★ Increment archive** | Dormant magazine; ingest once, mine for operational essays. |
| 14 | **★ Fastly Jun-2021** | Single canonical post; pair with Cloudflare config-cascade posts. |
| 15 | **★ Stripe 2019-07-10** | Sparse but the one extant Stripe RCA is genre-defining. |
| 16 | **★ PyPI incident reports** | Different genre (supply-chain); essential for that axis. |
| 17 | **★ GitLab Handbook / 2017 db1** | Process + one classic post-mortem; CC-BY-SA. |
| 18 | **k8s/community postmortems** | Apache-2 but tiny (1-2 files). Include for completeness. |
| 19 | **danluu/post-mortems repo + essay** | Use as link-spine for crawl seeds; license **unverified**. |
| 20 | **k8s.af + awesome-postmortem lists** | Link-spines only. |

---

## §5 PII / blame filter design

Tier C content fans out across genres with different PII profiles. Recommended pipeline (cheap → expensive):

1. **Regex / NER first pass** — covers the long tail.
   - Strip patterns matching `@[a-z0-9_-]+`, `<firstname> <lastname> from the X team`, `our engineer <name>`, GitHub-handle backticks `\`[a-z0-9-]+\`` *only when adjacent to* "engineer", "wrote", "deployed", "merged", "pushed", "approved".
   - Strip pager IDs, ticket IDs that aren't useful (`SEV-12345`, `INC-99999`) unless cross-referenced to a fix commit.
   - Use a small NER model (spaCy `en_core_web_sm` + custom ruleset) to mask `PERSON` entities *unless* they appear in author-byline metadata (which we want to preserve as provenance, separated from training tokens).

2. **Heuristic blame-phrase stripping** — small allow/deny phrase list.
   - **Deny** phrases (rewrite or strip the surrounding sentence): "human error", "the engineer who", "[name] forgot to", "[name] mistakenly", "should have caught", "failed to follow".
   - **Allow** phrases (keep — these are the *learning* signal): "the change", "the deploy", "the configuration", "the rollback procedure", "the runbook did not cover", "the alarm did not fire because", "blast radius", "fail small".

3. **LLM-pass for ambiguous cases** — cheap model (Haiku-class), one-shot prompt:
   > "Rewrite the following post-mortem excerpt to remove any individual attribution of fault while preserving every technical detail, timestamp, command, configuration value, and root-cause description. If the excerpt is already blameless, return it unchanged."
   - Run only on chunks where the regex/NER pass flagged ≥1 candidate. Budget: ~5-10% of corpus.

4. **Per-source policy overrides** — encode in the canon-tag schema:
   - AWS PES, Azure PIRs, Cloudflare, Datadog, AWS Builders' Library, Discord, SRE Book/Workbook → blameless-by-construction; **skip step 3** to save spend.
   - GitHub blog, Heroku, Stripe → **run full pipeline**, modest risk of role-naming.
   - PyPI incident reports, surfingcomplexity, danluu's linked third-party post-mortems → **highest risk**, run full pipeline + manual spot-check on every chunk that mentions a non-Anthropic-affiliated individual.

5. **Skip-section rules** — drop entire sections when:
   - section header contains "Personnel" / "Roles" / "Who" without "Why".
   - "Acknowledgements" / "Thanks to" sections — useful metadata, but not training prose.

6. **Provenance preserved separately** — store author + URL + license in front-matter; strip from token stream. This is what `canon-tag` schema is for.

---

## §6 Token roll-up

| bucket | est. tokens | notes |
| --- | --- | --- |
| Cloudflare post-mortem tag | 200-400 k | full ingest OK |
| Google SRE Workbook | 300-400 k | CC BY 4.0 |
| Google SRE Book (excerpts only) | 50-100 k after filtering | BY-NC-ND limits |
| Azure PIRs | 150-300 k | proprietary, fair-use |
| AWS Builders' Library | 400-700 k | proprietary, fair-use |
| AWS PES | 30-60 k | proprietary, fair-use |
| GitHub Availability + history | 80-150 k | proprietary, fair-use |
| Datadog Mar-2023 series | 25-40 k | proprietary, fair-use |
| Surfing Complexity | 200-400 k | personal blog, fair-use |
| GCP incidents.json | 100-200 k | structured |
| Heroku + Discord + Stripe + Fastly | 80-130 k combined | proprietary, fair-use |
| Increment Magazine | 300-500 k | proprietary, fair-use, dormant (stable) |
| PyPI blog | 15-25 k | PSF / fair-use |
| GitLab Handbook (incident sections) | 30-80 k | CC BY-SA |
| k8s postmortems + k8s.af + awesome-* | 5-15 k direct text | mostly link-spines |
| danluu essay + linked roundups | 10-30 k direct | + crawl seeds |

**Total Tier C raw estimate: ~2.0 – 3.5 M tokens.**

At Tier C's likely budget within the ~3 B-tok `philosophy` mix (Tier A/B/D dominate by weight), 2-3 M raw tokens is **already over-supply**. Recommendation: ingest the top 8-10 sources fully (ordered §4), then sample-quote the rest. With dedup + PII filter, expect ~1.0-1.5 M usable Tier C tokens.

---

## §7 Action items back into source list

- [ ] Fix `papers/coding-philosophy-sources.md` §3:
  - replace bare "GitHub status post-mortems" with `github.blog/tag/github-availability-report/`.
  - replace bare "k8s.io postmortem repo" with `github.com/kubernetes/community/tree/master/sig-cluster-lifecycle/postmortems` and note volume is small.
  - remove "CC-BY, full" claim on danluu — license unverified.
  - add: SRE Workbook (CC BY 4.0) above the SRE Book.
- [ ] Add `vendor-fair-use` and `commercial-risk-flagged` canon-tags to schema.
- [ ] Pre-commit hook: every Tier C chunk must carry `pii-pass: regex|llm|none` provenance.
- [ ] Mark `morethanseven.net` claim as `UNVERIFIED — could not locate`.
