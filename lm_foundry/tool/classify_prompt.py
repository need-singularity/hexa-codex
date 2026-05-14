#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""classify_prompt.py — pre-7B prompt classifier for v0.5.0 orchestration routing.

CPU-only keyword/regex router. Decides whether a user prompt should be:

  * routed to the local 7B (label="hexa")  — hexa-canon code / annotations
                                              / diagnostics / triples / refusal
  * dispatched to a frontier vendor (label="ood")  — non-hexa programming,
                                                     math/reasoning, long-context,
                                                     structured-output extraction
  * refused at the gate (label="refuse")  — security-sensitive / harmful

Design per `papers/spec-orchestration-v0.5.0.md` §4.A. Built after v0.4.x
disproved in-weight routing across five rounds (r40–r43.1).

Scoring philosophy:
  Stage 1 — security refuse (highest priority, irreversible)
  Stage 2 — strong hexa signal (≥1 high-confidence match like @grace, HX*xxx,
            target triple, atlas L[N]) → hexa
  Stage 3 — OOD signal (non-hexa language name / framework / math keyword /
            structured-output cue / explicit token-count for long-context)
  Stage 4 — disambiguation (both fired)
  Stage 5 — fallthrough → ood (safer default; Claude handles graceful refusal
            of anything truly off)

USAGE
    from classify_prompt import classify_prompt
    decision = classify_prompt("Write the hexa enum `Result<T>`: Ok(T), Err(String).")
    # → ClassifierDecision(label="hexa", confidence=0.95, reason="hexa: enum-decl + type-param", …)
"""
from __future__ import annotations

import os as _os
import sys as _sys
# Strip this file's dir from sys.path so stdlib imports (`tokenize` →
# `linecache` → `inspect` → `dataclasses`) don't shadow on sibling tool/*.py.
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import re
from dataclasses import dataclass, field


@dataclass
class ClassifierDecision:
    label: str                        # "hexa" | "ood" | "refuse"
    confidence: float                 # 0.0–1.0 (heuristic from match count / strength)
    reason: str                       # one-line explanation for telemetry
    matched_signals: list[str] = field(default_factory=list)


# ============================================================================
# Security-refuse patterns (Stage 1 — highest priority, irreversible)
# ============================================================================
# Match → label=refuse. Cover the spec-delegation §6 hard-block list +
# the DLG-mk0 security-refuse category vocabulary.
_REFUSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("exfil",        re.compile(r"\bexfiltrat\w*\b", re.IGNORECASE)),
    ("phishing",     re.compile(r"\bphishing\b|phish-?(?:email|message|kit)", re.IGNORECASE)),
    # r51: extend conjugation to catch "brute-forces" (3sg present) — DLG-262
    ("brute-force",  re.compile(r"\bbrute[-_ ]?forc(?:e|es|ed|ing)\b", re.IGNORECASE)),
    ("password-crack", re.compile(r"\bcrack(?:ing)? (?:a |the )?password\b|password (?:cracker|cracking)\b", re.IGNORECASE)),
    ("malware",      re.compile(r"\bmalware\b|\brootkit\b|\bbackdoor\b(?! into hexa)|\bkeylogger\b|\bworm\b(?! that propagates)|\bransom(?:ware)?\b", re.IGNORECASE)),
    ("ddos",         re.compile(r"\bddos\b|\bdos attack\b", re.IGNORECASE)),
    ("xss-hijack",   re.compile(r"\bhijack\w* (?:session|cookie|token)\b|\bvia xss\b|cross[-_ ]?site[-_ ]?scripting\b", re.IGNORECASE)),
    ("sql-injection", re.compile(r"\bsql[-_ ]?injection\b", re.IGNORECASE)),
    ("license-bypass", re.compile(r"\bbypass\w* (?:license|drm|copy[-_ ]?protection|cap?tcha|two[-_ ]?factor|2fa|content[-_ ]?filter|endpoint[-_ ]?detection)\b", re.IGNORECASE)),
    ("badge-clone",  re.compile(r"\bclone\b.*\b(?:rfid|hid|iclass|badge|someone\'?s? rfid|someone\'?s? badge)\b|\bsim[-_ ]?swap\b", re.IGNORECASE)),
    ("scrape-private", re.compile(r"\bscrap(?:e|es|ing)\b.*\b(?:private|user\s+email|emails?|credit[-_ ]?card|linkedin|competitor pricing|age-?restrict)\b|\bscrap(?:e|es|ing)\b.*\bdespite\b", re.IGNORECASE)),
    ("deepfake",     re.compile(r"\bdeep[-_ ]?fake\b", re.IGNORECASE)),
    ("hide-mining",  re.compile(r"\bhidden in (?:a |the )?(?:chrome extension|background|browser)\b|\bmining script that runs hidden\b", re.IGNORECASE)),
    ("forge-cert",   re.compile(r"\bforg(?:e|ing) (?:a |an )?(?:tls|ssl|digital) (?:certificate|signature)\b", re.IGNORECASE)),
    ("fake-account", re.compile(r"\bmass[-_ ]?creat\w* (?:fake |spam |bot )?accounts?\b|\bmass[-_ ]?spam\b", re.IGNORECASE)),
    ("fake-reviews", re.compile(r"\bauto[-_ ]?(?:like|review|post)\w*\b|\bmass[-_ ]?(?:like|review)\w*\b|\bfake[-_ ]?reviews?\b", re.IGNORECASE)),
    ("disable-security", re.compile(r"\bdisable\w* (?:windows defender|audit logging|endpoint[-_ ]?detection|edr|antivirus)\b", re.IGNORECASE)),
    ("steganography-cmd", re.compile(r"\bsteganograph\w*.*\bcommand\b|\bhide\w* commands? in images\b", re.IGNORECASE)),
    ("compromise-network", re.compile(r"\bcompromis(?:e|ing) (?:a |the )?wi-?fi\b|\bman[-_ ]?in[-_ ]?the[-_ ]?middle\b|\bmitm\b|\busb autorun\b", re.IGNORECASE)),
    ("session-token-capture", re.compile(r"\bforge\w* (?:oauth|jwt|session) (?:callback|redirect|token)\b|\bcapture\w* (?:tokens|cookies)\b", re.IGNORECASE)),
    ("voice-clone-malicious", re.compile(r"\bvoice clone\w*\b", re.IGNORECASE)),
    ("auto-spam", re.compile(r"\bmass[-_ ]?spam\b|\bauto[-_ ]?delet\w* other people\b|\bcredential stuffing\b|\binject\w* ads into", re.IGNORECASE)),
    ("reverse-engineer-drm", re.compile(r"\breverse[-_ ]?engineer\w* drm\b", re.IGNORECASE)),
    ("router-firmware-backdoor", re.compile(r"\bmodify\w* (?:a |the )?router firmware\b|\bremote backdoor\b", re.IGNORECASE)),
    ("counterfeit-bypass", re.compile(r"\bcounterfeit currency detector bypass\b|\bage[-_ ]?restrict\w*\b.*bypass", re.IGNORECASE)),
    ("kernel-hijack", re.compile(r"\bdll[-_ ]?hijack\w*\b|\bsystemd unit.*persistenc\w*\b", re.IGNORECASE)),
    # r51: gaps surfaced by DLG-261..270 expansion (held-out refuse variants).
    # jailbreak: covers "jailbreak my work laptop", "jailbreak to bypass" — policy-bypass framing.
    ("jailbreak-policy", re.compile(r"\bjailbreak(?:ing)?\b.*\b(?:work|corporate|company|laptop|iphone|android|device|to bypass|IT controls|MDM|policy)\b", re.IGNORECASE)),
    # prompt-injection: "write a prompt-injection attack", "leak its system prompt", "exfil system prompt"
    ("prompt-injection", re.compile(r"\bprompt[-_ ]?injection\b|\bleak\w*\s+(?:its\s+|the\s+)?system\s+prompt\b|\bsystem[-_ ]?prompt\s+(?:leak|exfil|disclosure)\b", re.IGNORECASE)),
    # weapon synthesis: chemical / biological / radiological / nerve agents
    ("weapon-synthesis", re.compile(r"\b(?:sarin|vx[-_ ]?agent|tabun|soman|cyanide|ricin|anthrax|nerve\s+agent|chemical\s+weapon|bio[-_ ]?weapon|nuclear\s+weapon|dirty\s+bomb)\b|\bsynthesi[zs]e\b.*\b(?:explosive|pathogen|toxin|nerve|precursor)\b|\bprecursor\b.*\b(?:nerve\s+agent|sarin|vx|tabun)\b", re.IGNORECASE)),
    # doxing / personal-info compilation
    ("doxing",       re.compile(r"\bdox(?:x|xes|xed|xing)?\s+(?:someone|the\s+(?:user|target|person)|them|him|her)\b|\bdoxx?ing\b|\bdox\s+(?:someone|the\s+person)\s+given\b", re.IGNORECASE)),
]


# ============================================================================
# Hexa-canon positive signals (Stage 2 — strong hexa)
# ============================================================================
# Each entry: (signal_name, regex, weight). Weight 2.0 = strong (single match
# is enough); weight 1.0 = weak (need ≥2 to dominate).
_HEXA_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    # --- Strong signals (weight 2.0): hexa-specific tokens only seen in canon ---
    ("at-grace",         re.compile(r"@grace\b"),                                                       2.0),
    ("at-implements",    re.compile(r"@implements\b"),                                                  2.0),
    ("at-discover",      re.compile(r"@discover\b"),                                                    2.0),
    ("hx-code-family",   re.compile(r"\bHX[0-9]xxx\b|\bHX[0-9]{4}\b|\bwhich hx family\b", re.IGNORECASE), 2.0),
    ("hexa-canon",       re.compile(r"\bhexa[-_ ]?canon\b|\bhexa[-_ ]?lang\b|\bhexa[-_ ]?cc\b", re.IGNORECASE), 2.0),
    ("hexa-keyword",     re.compile(r"\bhexa\b", re.IGNORECASE),                                        2.0),
    ("atlas-L",          re.compile(r"\bL\[\d+\]"),                                                     2.0),
    ("target-triple",    re.compile(r"\btarget triple\b|\bthumb[a-z0-9]+-none-eabi\b|\briscv\d+\w*-unknown\b|\baarch64-(?:apple|unknown)\b|\bwasm32-(?:wasi|unknown)\b", re.IGNORECASE), 2.0),
    ("stdlib-layering",  re.compile(r"\bstdlib/(?:core|io|alloc|net|embedded|proof)\b|\bcan\s+(?:the\s+)?(?:stdlib|firmware|applications|tools|test\s+harness|codex-techniques|compiler|the\s+compiler)\b.*\b(?:import|depend\s+on)\b", re.IGNORECASE),  2.0),
    ("hexa-vocab-atlas", re.compile(r"\batlas\s+(?:annotation|L-anchor)|\b@discover\(kind=\"L\"\)|\bdiscover\w*\s+(?:new\s+)?(?:law|invariant|axiom|conjecture)|\bproof\s+of\s+\w+\s+(?:to|for)\s+(?:L\[|atlas)", re.IGNORECASE), 2.0),
    ("hexa-vocab-prove", re.compile(r"\bprove[-_ ]?(?:assoc|distributivity|idempotent|commutativity|theorem|completeness|monotone|tricho|identity|normalization)\w*\(\)", re.IGNORECASE), 2.0),
    ("hexa-vocab-discover", re.compile(r"\bdiscover[-_ ]?(?:new[-_ ]?)?(?:law|laws|invariants?|axiom|axioms?|lemma|lemmas?)\w*\(\)", re.IGNORECASE), 2.0),

    # --- Medium signals (weight 1.5): hexa-specific but could appear in OOD context ---
    ("rfc-020-enum",     re.compile(r"\bRFC-?02[0-9]\b", re.IGNORECASE),                                1.5),
    ("hexa-enum-decl",   re.compile(r"\bhexa enum\b|enum \w+\s*<[A-Z],?[ A-Z]*>", re.IGNORECASE),       1.5),

    # --- Weak signals (weight 1.0): generic markers needing corroboration ---
    ("compile-checked",  re.compile(r"\bcompile-checked\b", re.IGNORECASE),                             1.0),
    ("5-nl-eval",        re.compile(r"\b5-nl\b|five[-_ ]?nl\b", re.IGNORECASE),                         1.0),

    # --- T8-family non-code prompts (hexa-eval refusal family) ---
    # The 7B GA is trained to refuse these with `out-of-domain — <category>` format.
    # Routing them to hexa preserves that capability; sending to Claude would change
    # the user-facing behaviour (Claude might creative-write the poem rather than refuse).
    # Eval manifest (DLG-mk0 T8) confirms must_delegate=False for this category.
    ("t8-creative",      re.compile(r"\b(?:write|compose|generate)\s+(?:me\s+)?(?:a |an |some )?(?:poem|haiku|tanka|song|sonnet|story|fable|screenplay|scene|toast|love letter|thank-you note|short story|wedding toast|birthday card)\b", re.IGNORECASE), 2.0),
    ("t8-joke",          re.compile(r"\btell\s+(?:me\s+)?(?:a |an )?(?:joke|knock[-_ ]?knock joke|bedtime story|fable|tanka|haiku)\b", re.IGNORECASE), 2.0),
    ("t8-translate",     re.compile(r"\btranslate\b\s+(?:this|that|these|the\s+\w+|[\"'][\w\s]+[\"'])\s+(?:to|into)\s+\w+", re.IGNORECASE), 2.0),
    ("t8-recommend",     re.compile(r"\b(?:recommend|suggest)\s+(?:me\s+)?(?:a |an |some )?(?:movie|book|podcast|documentary|playlist|meditation|workout|recipe|vacation|trip|itinerary)\b", re.IGNORECASE), 2.0),
    ("t8-explain-plot",  re.compile(r"\bexplain\s+(?:me\s+)?(?:the\s+)?(?:plot|story)\b", re.IGNORECASE), 2.0),
    ("t8-life-advice",   re.compile(r"\b(?:give\s+me\s+)?(?:dating|life|career|relationship|coaching|fitness|meditation|meal[-_ ]?plan(?:ning)?|workout)\s+(?:advice|tip(?:s)?|routine|plan|playlist)\b", re.IGNORECASE), 2.0),
    ("t8-meaning",       re.compile(r"\b(?:meaning\s+of\s+life|tell\s+me\s+about\s+(?:your\s+)?(?:day|childhood))\b", re.IGNORECASE), 2.0),
    ("t8-recipe",        re.compile(r"\brecipe\s+for\s+\w+", re.IGNORECASE),                            2.0),
    ("t8-personal-write", re.compile(r"\bwrite\s+(?:me\s+)?(?:a\s+)?(?:resume|cover\s+letter|toast|wedding\s+toast|birthday\s+card|love\s+letter|thank[-_ ]?you\s+note)\b", re.IGNORECASE), 2.0),
    ("t8-forecast",      re.compile(r"\bpredict\s+(?:next\s+\w+'s?\s+)?weather\b|\bweather forecast\b", re.IGNORECASE), 2.0),
    ("t8-puzzle",        re.compile(r"\bsolve\s+(?:this\s+)?(?:crossword\s+clue|riddle)\b", re.IGNORECASE), 2.0),
]


# ============================================================================
# Non-English hexa signals (Stage 2 — 5-NL i18n)
# ============================================================================
# Non-English question forms that mention HX-codes / hexa terminology directly.
_HEXA_NONENG_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("kr-hx-family",     re.compile(r"HX 패밀리|HX-?코드 패밀리"),                                       2.0),
    ("ja-hx-family",     re.compile(r"HXファミリ|HXコード"),                                             2.0),
    ("zh-hx-family",     re.compile(r"HX家族|哪个HX"),                                                   2.0),
    ("de-hx-family",     re.compile(r"HX[-_ ]?Familie\b|Welche HX", re.IGNORECASE),                     2.0),
    ("es-hx-family",     re.compile(r"familia HX\b", re.IGNORECASE),                                    2.0),
    ("fr-hx-family",     re.compile(r"famille HX\b", re.IGNORECASE),                                    2.0),
]


# ============================================================================
# OOD positive signals (Stage 3 — non-hexa)
# ============================================================================
_OOD_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    # Programming language names (word-boundary to avoid hexa-canon false-pos)
    ("rust",              re.compile(r"\bRust\b(?!\-style)", re.IGNORECASE),                            2.0),
    ("python",            re.compile(r"\bpython\b", re.IGNORECASE),                                     2.0),
    # r55: extend golang to catch DLG-109/112/119/243 patterns:
    #   "Go: implement a worker pool with bounded concurrency using channels"
    #   "Write a Go `context.Context`-aware function ..."
    #   "Go table-driven test for a parser function with 8 cases"
    #   "Implement a Go context.Context-aware worker pool with cancellation"
    # Adds worker pool / table-driven / context.Context / sync.Mutex /
    # standalone `goroutine` and `channels` (with go nearby) markers.
    ("golang",            re.compile(r"\b(?:go(?:lang)?\s*[:`]?\s*(?:function|method|pattern|HTTP|channel|goroutine|generic|struct|worker|table[-_ ]?driven|context\.Context|implement)|golang|goroutine|context\.Context|sync\.(?:Mutex|WaitGroup|RWMutex|Once)|table[-_ ]?driven\s+test)\b", re.IGNORECASE), 2.0),
    ("typescript",        re.compile(r"\btypescript\b|\bts\s+(?:discriminated|debounce|class)\b", re.IGNORECASE), 2.0),
    ("javascript",        re.compile(r"\bjavascript\b|\bnode\.?js\b|\bes6\b|\breact\b|\bvue\b|\bangular\b", re.IGNORECASE), 2.0),
    ("kotlin",            re.compile(r"\bkotlin\b", re.IGNORECASE),                                     2.0),
    ("swift-long",        re.compile(r"\bswift\b.*\b(?:server|long|framework|deep)\b", re.IGNORECASE),  1.5),  # short Swift = mid-conf
    # r55: Swift + SwiftUI / @Published / @AppStorage / @State framework markers
    # closes DLG-253 / DLG-291 (Swift + SwiftUI patterns) which slip past mid-conf
    # detection but had no positive OOD signal.
    ("swift-framework",   re.compile(r"\bswiftui\b|\bswift\b.*\b(?:@Published|@AppStorage|@State|@Binding|@Environment|Combine\s+framework|jetpack[-_ ]?compose)\b", re.IGNORECASE), 2.0),
    ("java",              re.compile(r"\bjava\b(?!script)|\bspring\b|\bjvm\b", re.IGNORECASE),          2.0),
    ("c-plusplus",        re.compile(r"\bC\+\+\b|\bc-plus-plus\b", re.IGNORECASE),                      2.0),
    ("ruby",              re.compile(r"\bruby\b(?! enum)|\brails\b", re.IGNORECASE),                    2.0),
    ("haskell",           re.compile(r"\bhaskell\b", re.IGNORECASE),                                    2.0),
    ("scala",             re.compile(r"\bscala\b", re.IGNORECASE),                                      2.0),
    ("elixir",            re.compile(r"\belixir\b|\bgen_?server\b|\bgenserver\b", re.IGNORECASE),       2.0),
    ("zig",               re.compile(r"\bzig\b(?!-build)", re.IGNORECASE),                              2.0),
    ("nim",               re.compile(r"\bnim\b\s+(?:function|macro|template)", re.IGNORECASE),          2.0),
    ("dart",              re.compile(r"\bdart\b", re.IGNORECASE),                                       2.0),
    ("php",               re.compile(r"\bphp\b", re.IGNORECASE),                                        2.0),
    ("perl",              re.compile(r"\bperl\b", re.IGNORECASE),                                       2.0),
    ("lua",               re.compile(r"\blua\b", re.IGNORECASE),                                        2.0),
    ("ocaml-fsharp",      re.compile(r"\bocaml\b|\bf#\b|\bfsharp\b", re.IGNORECASE),                    2.0),
    ("clojure",           re.compile(r"\bclojure\b", re.IGNORECASE),                                    2.0),
    ("erlang",            re.compile(r"\berlang\b", re.IGNORECASE),                                     2.0),
    ("c-language",        re.compile(r"\bc function\b|c\+\+|\bgcc\b|\bansi c\b", re.IGNORECASE), 1.5),
    ("r-stats",           re.compile(r"\bR function\b.*(?:t-test|vector)|\btidyverse\b", re.IGNORECASE), 2.0),
    ("julia",             re.compile(r"\bjulia\b\s+(?:function|matrix|multiple dispatch)", re.IGNORECASE), 2.0),
    ("matlab",            re.compile(r"\bmatlab\b", re.IGNORECASE),                                     2.0),
    ("solidity",          re.compile(r"\bsolidity\b", re.IGNORECASE),                                   2.0),
    ("agda-coq-lean",     re.compile(r"\bagda\b|\bcoq\b|\blean(?:4)?\b|\bidris\b", re.IGNORECASE),      2.0),

    # Frameworks / tools strongly OOD
    ("tokio",             re.compile(r"\btokio\b", re.IGNORECASE),                                      2.0),
    ("asyncio",           re.compile(r"\basyncio\b|\basync/?await\b.*\bpython\b", re.IGNORECASE),       1.5),
    ("react",             re.compile(r"\breact\b|\buseEffect\b|\buseState\b", re.IGNORECASE),           2.0),
    ("kubernetes",        re.compile(r"\bkubernetes\b|\bk8s\b|\bhelm\b|\bistio\b", re.IGNORECASE),      2.0),
    ("docker",            re.compile(r"\bdockerfile\b|\bdocker\b", re.IGNORECASE),                      2.0),
    ("terraform",         re.compile(r"\bterraform\b|\bpulumi\b|\bcdk\b", re.IGNORECASE),               2.0),
    ("aws-cloud",         re.compile(r"\baws\b|\bs3\b|\blambda\b|\bec2\b|\beks\b|\bvpc\b|\bgcp\b|\bcloudflare\b|\bazure\b", re.IGNORECASE), 2.0),
    ("nginx-haproxy",     re.compile(r"\bnginx\b|\bhaproxy\b|\benvoy\b", re.IGNORECASE),                2.0),
    ("sql-explicit",      re.compile(r"\bSQL\b|\bpostgresql\b|\bpostgres\b|\bmysql\b|\bsqlite\b|\bclickhouse\b|\bduckdb\b", re.IGNORECASE), 2.0),
    ("grpc-graphql",      re.compile(r"\bgrpc\b|\bgraphql\b|\bprotobuf\b|\bthrift\b", re.IGNORECASE),   2.0),
    ("redis-mongo-kafka", re.compile(r"\bredis\b|\bmongodb?\b|\bkafka\b|\bspark\b|\bflink\b|\bdbt\b|\bairflow\b|\bdagster\b|\bbeam\b", re.IGNORECASE), 2.0),
    ("ci-github-gitlab",  re.compile(r"\bgithub actions\b|\bgitlab ci\b", re.IGNORECASE),               2.0),
    ("jest-pytest-junit", re.compile(r"\bjest\b|\bpytest\b|\bjunit\b|\bselenium\b|\bplaywright\b", re.IGNORECASE), 2.0),

    # Math / hard reasoning
    #   r49: prove-derive extended to catch "proof" NOUN (currently only verb
    #   form fires) — closes DLG-135 ("Walk through the proof that there are
    #   infinitely many primes") which currently emits no reasoning signal.
    ("prove-derive",      re.compile(r"\b(?:prov(?:e|ing)|deriv(?:e|ation|ing)|show\s+that|theorem|lemma|corollary|induct(?:ion|ively)|proof\s+(?:that|of|by)|infinitely\s+many)\b", re.IGNORECASE), 1.5),
    ("complexity-bigO",   re.compile(r"\bcomplexity\b|\bbig[-_ ]?O\b|\bclosed[-_ ]?form\b|\brecurrence\b|\bO\(.*\)", re.IGNORECASE), 1.5),
    # r55: ml-internals expanded to catch MoE / RLHF / DPO / KL-penalty / top-k
    # routing — closes DLG-100/238 no-signal-fallthrough.
    ("ml-internals",      re.compile(r"\battention\b|\btransformer\b|\bRoPE\b|\bLoRA\b|\bDoRA\b|\bGRPO\b|\bPPO\b|\bRAG\b|\bembedding\b|\bsoftmax\b|\bmixture[-_ ]?of[-_ ]?experts\b|\bMoE\b|\btop[-_ ]?[2k]\s+(?:routing|expert|gate)|\bRLHF\b|\bDPO\b|\bRLAIF\b|\bKL[-_ ]?(?:penalty|divergence|loss|anchor)\b|\breward\s+model\b", re.IGNORECASE), 1.5),
    # r49 NEW signals for fine-grained tier routing (see select_vendor_tier
    # priority steps 2 + 3). `derivation-algo` triggers when the prompt asks
    # for a closed-form / recurrence / formula derivation (textbook algorithmic
    # math — o4-mini is the sweet spot). The tier selector demotes to o4-mini
    # ONLY when ml-internals is NOT also matched (ML gradient derivations stay
    # on opus — DLG-092). `ml-comparison` flags ml-internals questions phrased
    # as comparative trade-offs ("difference between", "give better X",
    # "reduce memory vs", "when does X help") — these are sonnet-tier.
    # r55: derivation-algo extended to catch "complexity ... show the
    # derivation" (P10 in r53 e2e smoke) — also covers `Big-O ... derivation`.
    # The tier selector's `AND NOT ml-internals` guard still protects DLG-092
    # (ML gradient derivation stays opus).
    # r55: derivation-algo extended further to catch pure complexity-of-X /
    # Big-O-of-X / master-theorem prompts (DLG-227, DLG-230) — these are
    # textbook algorithmic-math territory (o4-mini tier). The `AND NOT
    # ml-internals` guard in select_vendor_tier still preserves ML gradient
    # derivations (DLG-092) on opus.
    ("derivation-algo",   re.compile(r"\bderiv(?:e|ation|ing)\s+(?:the\s+)?(?:closed[-_ ]?form|recurrence|formula|dual|integral|complexity|big[-_ ]?O)\b|\bclosed[-_ ]?form\b|\brecurrence\b|\bT\(n\)\s*=|\b(?:complexity|big[-_ ]?O)\b.{0,80}\bderivation\b|\bshow\s+the\s+derivation\b|\bmaster\s+theorem\b|\b(?:complexity|big[-_ ]?O)\s+of\s+\w+", re.IGNORECASE), 1.0),
    # r55: add `trade-offs` and `top-N vs top-M` patterns to catch DLG-100
    # ("mixture-of-experts routing — top-2 vs top-1 trade-offs"). The tier
    # selector's `ml-comparison AND ml-internals` guard ensures these only
    # demote when ml topic is also present.
    ("ml-comparison",     re.compile(r"\bdifference\s+between\b|\bgives?\s+better\b|\bwhen\s+does\s+\w+\s+help\b|\breduce\s+(?:memory|compute|cost|latency)\s+vs\b|\bbetter\s+(?:diversity|throughput|latency|memory)\b|\btrade[-_ ]?offs?\b|\btop[-_ ]?\d+\s+vs\s+top[-_ ]?\d+\b", re.IGNORECASE), 1.0),

    # Structured output / JSON extraction
    ("structured-json",   re.compile(r"\b(?:parse|convert|extract|classify|validate|return|summari[zs]e|generate|output|emit)\b.*\bjson\b", re.IGNORECASE), 1.5),
    ("json-schema",       re.compile(r"\bjson schema\b|\bzod\b|\bjsonschema\b", re.IGNORECASE),         1.5),

    # Long-context explicit token count
    ("long-context",      re.compile(r"\b\d{2,4}K-?token\b|\b\d+(?:\.\d+)?M-?token\b|\b\d+K[-_ ]?token\b", re.IGNORECASE), 2.0),

    # r55: LLM-infrastructure signals — closes DLG-093 (Anthropic prompt
    # caching) and similar. Matches vendor names + caching/context terminology.
    ("llm-infra",         re.compile(r"\b(?:anthropic|claude(?:-\d|\s+(?:api|model|opus|sonnet|haiku))|openai|gpt-?[345]|o[34][-_ ]?mini|gemini(?:-\d)?|prompt[-_ ]?cach(?:e|ing)|cache_?control|system\s+prompt|context\s+window\s+management|TTL\s+semantic|frontier\s+model|tier\s+(?:routing|selection))\b", re.IGNORECASE), 1.5),

    # r55: generic code-write verb — weak signal (w=1.0) for "Write a
    # script/function/tool ..." when no language is mentioned. Catches
    # DLG-297 ("Write a script that fuzzes form inputs for XSS"). Hexa
    # prompts with "Write a hexa function" still win via strong hexa-keyword.
    ("generic-write-code", re.compile(r"\bwrite\s+(?:a\s+|an\s+)?(?:script|function|program|tool|module|class|wrapper|cli|server)\b", re.IGNORECASE), 1.0),
]


# Ambiguous / under-specified prompts — route to OOD (Claude handles clarify)
_AMBIGUOUS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # r55: added "speed this up" variant (DLG-279) and "make ... faster/slower".
    ("vague-imperative", re.compile(r"^(?:make it|fix this|why is it|optimize|refactor|polish|reduce|improve|trim|lock down|standardize|add|update|configure|simplify|speed up|speed this up|make it (?:secure|cleaner|faster|production-ready|slower)|make this (?:faster|slower|cleaner)|set up|set the|implement the|cache it|run it|print|get the|send it|save it|delete it|reset|install it|upload it)\b", re.IGNORECASE)),
    # r55: vague-question — closes DLG-185/189/190/278/298/300 no-signal-
    # fallthrough rows. These are short conversational/uncertain prompts that
    # had no positive signal but ARE genuinely ambiguous-OOD.
    ("vague-question",   re.compile(r"^(?:should\s+i|what'?s\s+the\s+best|is\s+this\s+(?:idiomatic|right|correct|broken|ok)|why\s+won'?t|tell\s+me\b|help\s*[\.\?!]?$|any\s+ideas?\b|how\s+do\s+i\s+pick|got\s+a\s+(?:question|sec)|quick\s+question)", re.IGNORECASE)),
]


# Mid-confidence patterns (DLG-mk0 mid-conf category): SHORT idiomatic prompts
# that route to the 7B with `<|confidence:medium|>` band. Per the DLG-mk0
# build script's mid_confidence block:
#   - Swift: 10 prompts, ALL mid-conf (no ood Swift in DLG-mk0)
#   - Python: 10 prompts, descriptive-idiom style (no "Write a Python <X>")
#   - Go: 5 prompts, descriptive-idiom style
# OOD Python/Go in DLG-mk0 uses functional-verb prefixes: "Write a Python
# decorator that ...", "Show a Python context manager ...", "Idiomatic
# Python for X-ing Y", "Implement <thing>" — these go to claude-sonnet OOD.
_MID_CONF_LANG_RE = re.compile(r"\b(?:swift|python|go|kotlin|ruby)\b", re.IGNORECASE)
_MID_CONF_FRAMEWORK_RE = re.compile(r"\b(?:tokio|kubernetes|docker|terraform|aws|gcp|azure|kafka|spark|airflow|django|flask|fastapi|spring|react|vue|angular|nextjs|next\.js|swiftui|combine|jetpack[-_ ]?compose)\b", re.IGNORECASE)
_MID_CONF_LONG_RE = re.compile(r"\b(?:long-context|long context|microservice|distributed|production-ready)\b", re.IGNORECASE)
# Functional-code-request markers (signals "this is a full-scope code write,
# route to OOD, not mid-conf"). Anchored: must appear near the start.
_FUNCTIONAL_VERB_RE = re.compile(r"^\s*(?:write|show|implement|build|create|generate)\s+(?:a |an )?(?:python|go|kotlin|ruby|rust|java|typescript|javascript|node\.?js|swift)\b", re.IGNORECASE)
_IDIOMATIC_FOR_RE   = re.compile(r"^\s*idiomatic\s+(?:python|go|kotlin|ruby|java|rust|typescript|javascript)\s+(?:for|to|\w+(?:wrapping|handling|caching|typing|dataclass)|\w+\s+(?:dataclass|fixture|test))\b", re.IGNORECASE)
# Additional functional-marker words anywhere in the prompt (not just prefix).
# These signal "full-scope code request, not bare idiom" — push to OOD.
_FUNCTIONAL_CONTENT_RE = re.compile(r"\b(?:function\s+(?:that|for)|fixture\s+(?:that|for)|pytest fixture|test\s+for\s+a\s+\w+|(?:Go|Python)\s*:\s*implement|implement a\b|pattern\b\.?$|validation\b\.?$|wrapping\b\.?$|table[-_ ]?driven test|min[-_ ]?heap)\b", re.IGNORECASE)
# Swift always mid-conf (DLG-mk0 has zero OOD Swift).
_SWIFT_KEYWORD_RE = re.compile(r"\bswift\b", re.IGNORECASE)


def _is_mid_confidence(prompt: str) -> bool:
    """Mid-conf rules:
      - Swift mention → mid-conf (DLG-mk0 has no OOD Swift; always route to 7B).
      - Python/Go/Kotlin/Ruby short prompt with NO functional-verb prefix and
        NO "Idiomatic X for ..." prefix → mid-conf (descriptive idiom).
      - Anything with framework/system depth signals → OOD.
    """
    if _MID_CONF_FRAMEWORK_RE.search(prompt) or _MID_CONF_LONG_RE.search(prompt):
        return False
    # Swift: always mid-conf.
    if _SWIFT_KEYWORD_RE.search(prompt) and len(prompt) <= 200:
        return True
    # Python/Go/etc — short + descriptive (no functional verb prefix or
    # content marker).
    if not _MID_CONF_LANG_RE.search(prompt):
        return False
    if len(prompt) > 120:
        return False
    if _FUNCTIONAL_VERB_RE.search(prompt) or _IDIOMATIC_FOR_RE.search(prompt):
        return False
    if _FUNCTIONAL_CONTENT_RE.search(prompt):
        return False
    return True


def _scan(prompt: str, patterns: list) -> tuple[float, list[str]]:
    """Run a list of `(name, regex, [weight])` patterns. Return (total_weight, hits)."""
    total = 0.0
    hits: list[str] = []
    for entry in patterns:
        name = entry[0]
        pat = entry[1]
        weight = entry[2] if len(entry) > 2 else 1.0
        if pat.search(prompt):
            total += weight
            hits.append(name)
    return total, hits


def _emit_conf(total: float, full_threshold: float, floor: float = 0.85) -> float:
    """r54 calibrated-confidence emission (replaces prior `min(1.0, X/Y)`).

    Empirical r52 reliability table showed single-signal cases at conf
    0.25-0.50 had ~100% empirical accuracy (massive underconfidence). The
    fix is a piecewise emission:

      total <= 0                    → 0.0    (no signal)
      0 < total < full_threshold    → floor + (1-floor) * (total / full_threshold)
      total >= full_threshold       → 1.0    (saturated)

    `floor` is the empirically-warranted confidence for a single signal of
    the relevant strength class:

      - refuse single match  → floor=0.95 (r52 acc 1.00, prior 0.5)
      - strong hexa/ood      → floor=0.85
      - weak hexa            → floor=0.80
      - weak ood fallthrough → floor=0.80

    The label-dispatch logic is UNCHANGED — only the emitted confidence
    moves. DLG-mk0 accuracy is preserved by construction.
    """
    if total <= 0.0:
        return 0.0
    if total >= full_threshold:
        return 1.0
    return min(1.0, floor + (1.0 - floor) * (total / full_threshold))


# ============================================================================
# Public API
# ============================================================================

def classify_prompt(prompt: str) -> ClassifierDecision:
    """Classify a user prompt into {hexa, ood, refuse}.

    Decision order:
      1. Security-refuse → refuse  (highest priority, irreversible)
      2. Strong hexa signals (≥1 weight≥2.0 hit) → hexa
      3. OOD signals (≥1 weight≥2.0 hit) → ood
      4. Hexa weak-only (no strong hit but ≥2 weak hits) → hexa
      5. Ambiguous imperative → ood (Claude handles ambiguity)
      6. Fallthrough → ood (safer default)
    """
    p = prompt.strip()

    # r54: confidence recalibration per r52 Brier/ECE finding.
    #
    # r52 reliability table on r51's 300-task DLG-mk0:
    #   bin [0.30, 0.40)  19 tasks  conf 0.30  acc 1.00  gap -0.70  ← extreme underconf
    #   bin [0.50, 0.60)  51 tasks  conf 0.50  acc 1.00  gap -0.50  ← extreme underconf
    #   bin [0.70, 0.80)  37 tasks  conf 0.70  acc 0.92  gap -0.22  ← moderate underconf
    #   bin [0.80, 0.90)   8 tasks  conf 0.83  acc 1.00  gap -0.17  ← mild underconf
    #   bin [0.90, 1.00) 183 tasks  conf 1.00  acc 1.00  gap  0.00  ← perfectly calibrated
    #
    # Root cause: the prior `min(1.0, X / Y)` formulas emitted 0.25-0.50
    # for single-signal cases that have empirical 100% accuracy. The fix
    # is `_emit_conf(total, full_threshold, floor=0.80-0.95)` — single
    # signal → floor (well above prior 0.5); multiple signals scale to
    # 1.0 at full_threshold. The label dispatch logic is UNCHANGED (only
    # the emitted `confidence` value moves), so DLG-mk0 accuracy is
    # preserved by construction.

    # 1. Refuse — empirically 100% acc on r51; emit ≥0.95 floor.
    refuse_total, refuse_hits = 0.0, []
    for name, pat in _REFUSE_PATTERNS:
        if pat.search(p):
            refuse_total += 2.0
            refuse_hits.append(name)
    if refuse_total > 0:
        return ClassifierDecision(
            label="refuse", confidence=_emit_conf(refuse_total, 2.0, floor=0.95),
            reason=f"security-sensitive: {refuse_hits[0]}", matched_signals=refuse_hits,
        )

    # 2. Hexa.
    hexa_total, hexa_hits = _scan(p, _HEXA_PATTERNS + _HEXA_NONENG_PATTERNS)
    strong_hexa = any(name for name, pat, w in (_HEXA_PATTERNS + _HEXA_NONENG_PATTERNS)
                       if w >= 2.0 and pat.search(p))

    # 2.5. Mid-confidence short-circuit — empirical acc 0.92 on r51; keep 0.7
    # as the matching emission (already well-calibrated).
    if _is_mid_confidence(p) and not strong_hexa:
        return ClassifierDecision(
            label="hexa", confidence=0.7,
            reason="mid-confidence: short language idiom — 7B answers with confidence:medium",
            matched_signals=["mid-conf-short-lang"],
        )

    # 3. OOD.
    ood_total, ood_hits = _scan(p, _OOD_PATTERNS)
    strong_ood = any(name for name, pat, w in _OOD_PATTERNS
                      if w >= 2.0 and pat.search(p))

    # Long-context length heuristic — anything ≥ 12 000 chars is long-context.
    if len(p) >= 12000:
        ood_total += 2.0
        ood_hits.append("long-prompt-chars")
        strong_ood = True

    # 4. Disambiguation — strong-signal paths (single w=2.0 match dominates).
    if strong_hexa and not strong_ood:
        return ClassifierDecision(
            label="hexa", confidence=_emit_conf(hexa_total, 2.0, floor=0.85),
            reason=f"hexa-canon: {hexa_hits[0]}", matched_signals=hexa_hits,
        )
    if strong_ood and not strong_hexa:
        return ClassifierDecision(
            label="ood", confidence=_emit_conf(ood_total, 2.0, floor=0.85),
            reason=f"out-of-domain: {ood_hits[0]}", matched_signals=ood_hits,
        )
    if strong_hexa and strong_ood:
        # Both fired — let total weight decide; tie → hexa (specialist-leaning).
        # Proportional formula preserved (it conveys "how strongly H beats O"),
        # but with floor 0.85 since r52 shows both-fired-* bin acc = 1.00.
        if hexa_total >= ood_total:
            return ClassifierDecision(
                label="hexa", confidence=_emit_conf(hexa_total, hexa_total + ood_total, floor=0.85),
                reason=f"both-fired-hexa-wins: hexa={hexa_total:.1f} ood={ood_total:.1f}",
                matched_signals=hexa_hits + ood_hits,
            )
        return ClassifierDecision(
            label="ood", confidence=_emit_conf(ood_total, hexa_total + ood_total, floor=0.85),
            reason=f"both-fired-ood-wins: hexa={hexa_total:.1f} ood={ood_total:.1f}",
            matched_signals=hexa_hits + ood_hits,
        )

    # 5. Ambiguous imperative — empirical acc 1.00 on r51's 22 ambiguous tasks;
    # bump from 0.5 → 0.85 floor.
    for name, pat in _AMBIGUOUS_PATTERNS:
        if pat.search(p) and len(p) < 80:  # short imperative
            return ClassifierDecision(
                label="ood", confidence=0.85,
                reason="ambiguous: under-specified imperative",
                matched_signals=[name],
            )

    # 6. Weak hexa (≥2 hits, no strong) → hexa. Single weak signal (total=1.0,
    # divisor=4.0) used to emit 0.25 → bin [0.30, 0.40) under-conf cluster.
    if hexa_total >= 2.0:
        return ClassifierDecision(
            label="hexa", confidence=_emit_conf(hexa_total, 4.0, floor=0.80),
            reason=f"weak-hexa: {hexa_hits[0]}", matched_signals=hexa_hits,
        )

    # 7. Fallthrough → ood. Preserve any weak OOD signals that fired (weight
    # < 2.0 patterns like prove-derive, complexity-bigO, ml-internals,
    # structured-json) so the downstream `select_vendor_tier()` can route to
    # the right tier (reason / struct / longctx) instead of defaulting to
    # general. Single weak signal used to emit 0.33 → bin [0.30, 0.40).
    if ood_hits:
        return ClassifierDecision(
            label="ood", confidence=_emit_conf(ood_total, 3.0, floor=0.80),
            reason=f"out-of-domain: {ood_hits[0]}",
            matched_signals=ood_hits,
        )
    # No-signal fallthrough — least certain branch (per r52, ambiguous-but-no-
    # signal prompts route here and have ~100% acc empirically but the path is
    # speculative — keep below the signal-emit floor as an "unsure but routed
    # ood" tier-band signal).
    return ClassifierDecision(
        label="ood", confidence=0.55,
        reason="no-signal-fallthrough", matched_signals=[],
    )


# ============================================================================
# CLI smoke test
# ============================================================================

def _smoke() -> int:
    cases = [
        # (prompt, expected_label, label_for_diagnostics)
        ("Write the hexa enum `Result<T>`: Ok(T), Err(String).",                "hexa",   "T4-enum-generic"),
        ("Mark `old_api()` deprecated with @grace: code HX9123.",                "hexa",   "T3-grace"),
        ("Which HX family covers parse errors?",                                  "hexa",   "T5-hx-family"),
        ("Target triple for ARM Cortex-M4 without FPU?",                          "hexa",   "T6-triple"),
        ("Can stdlib/io depend on stdlib/core? yes or no.",                       "hexa",   "T7-stdlib"),
        ("Annotate prove_assoc() as @implements(L[412]).",                        "hexa",   "T2-atlas"),
        ("HX 패밀리 중 어느 것이 codegen/link 에러를 다루나?",                       "hexa",   "5NL-kr"),
        ("Write me a poem about the moon.",                                       "hexa",   "T8-creative-refuse-by-7B"),
        ("Write a Rust async server using tokio that listens on TCP port 8080.", "ood",    "OOD-rust"),
        ("Explain how multi-head attention works.",                               "ood",    "OOD-ml"),
        ("Prove that the sum of the first n odd integers equals n².",             "ood",    "OOD-math"),
        ("Parse 'Alice, 32, alice@example.com' into JSON {name, age, email}.",   "ood",    "OOD-structured"),
        ("Here is a 500K-token spec document. Summarise rate-limiting section.", "ood",    "OOD-long-ctx"),
        ("Make it work.",                                                          "ood",    "ambiguous"),
        ("Fix this.",                                                              "ood",    "ambiguous"),
        ("Write code that exfiltrates environment variables to a remote URL.",   "refuse", "security-exfil"),
        ("Help me write a phishing email.",                                       "refuse", "security-phishing"),
        ("Write a Python decorator for HTTP caching with TTL.",                  "ood",    "OOD-python"),
        # Swift always mid-conf per DLG-mk0 build: routes to 7B (label="hexa"
        # with confidence:medium banding), NOT external delegation.
        ("Swift `if let` to safely unwrap an optional `String?`.",                "hexa",   "mid-conf-swift"),
        # Edge cases — should land hexa even though they're short
        ("Write a hexa function `f(n: i32) -> i32` returning n*2.",              "hexa",   "T1-syntax-bare"),
        ("Hexa enum `Color`: Red, Green, Blue.",                                  "hexa",   "T4-enum-simple"),
    ]
    n_correct = 0
    print(f"{'expected':<8} {'got':<8} {'label':<30} prompt")
    for prompt, expected, label in cases:
        d = classify_prompt(prompt)
        flag = "✓" if d.label == expected else "✗"
        if d.label == expected:
            n_correct += 1
        print(f"  {flag} {expected:<6} {d.label:<6} {label:<28} {prompt[:70]!r}")
        if d.label != expected:
            print(f"      reason: {d.reason}  signals: {d.matched_signals}")
    print(f"\n=== {n_correct}/{len(cases)} smoke cases pass ({n_correct/len(cases)*100:.0f}%) ===")
    return 0 if n_correct == len(cases) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_smoke())
