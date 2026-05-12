# Tier F-3 — Frontend Performance, Accessibility, AI-Native UI (2025-2026)

> Research date: 2026-05-11. Target: `code` verb training corpus for `hexa-forge`.
> Scope: latest canon for performance, a11y, AI-native UI, mobile, testing.
> Convention: ★ = new since prior tiers / non-obvious. `UNVERIFIED` = inference, not source-confirmed.

---

## Part 1 — Performance canon

### Core Web Vitals (current as of 2026)

| Metric | Good (p75) | Needs Improvement | Poor | Notes |
|---|---|---|---|---|
| LCP (Largest Contentful Paint) | ≤ 2.5 s | 2.6–4.0 s | > 4.0 s | Hardest to pass; only ~62% mobile pages pass per 2025 Web Almanac |
| INP (Interaction to Next Paint) | ≤ 200 ms | 201–500 ms | > 500 ms | ★ Replaced FID March 12, 2024. Whole-interaction, not just first-input |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | 0.11–0.25 | > 0.25 | Session-windowed since 2021 |

**Pass rule**: ≥ 75th-percentile real-user data (CrUX/RUM) must hit "Good" on all three. Source: [web.dev defining thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds), [web.dev Web Vitals](https://web.dev/articles/vitals).

### Image / resource patterns

| Canon (2026) | Deprecated / Avoid | Rationale | Source |
|---|---|---|---|
| `<img fetchpriority="high">` on the **single** LCP image | `fetchpriority="high"` on every hero / sprinkled everywhere | Etsy +4%, Google internal LCP 2.6→1.9s. Excess use causes bandwidth contention | [web.dev fetch-priority](https://web.dev/articles/fetch-priority), [DebugBear](https://www.debugbear.com/blog/avoid-overusing-fetchpriority-high) |
| `loading="lazy"` on below-the-fold imgs; **never** on LCP candidate | `loading="lazy"` on hero | Hero must be discoverable & non-deferred | [web.dev fetch-priority](https://web.dev/articles/fetch-priority) |
| `decoding="async"` on non-critical imgs | Synchronous decode by default | Avoids main-thread blocking | MDN |
| `<picture>` with AVIF → WebP → JPEG fallback | Single `.jpg`; serving WebP via UA-sniff | AVIF Baseline-2024, WebP Widely-Available (97% support) | [web.dev picture](https://web.dev/learn/design/picture-element), [DebugBear image-formats](https://www.debugbear.com/blog/image-formats) |
| `srcset` + `sizes` on `<img>` for resolution switching | Single fixed-DPR image | Browser picks best candidate per viewport + DPR | [MDN responsive images](https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Responsive_images) |
| `<picture><source media=...>` for **art direction** only | Using `<picture>` when `srcset`/`sizes` would do | `picture` = commands; `srcset` = suggestions | [css-tricks responsive-images](https://css-tricks.com/a-guide-to-the-responsive-images-syntax-in-html/) |

### Resource hints

| Hint | When to use | Trap |
|---|---|---|
| `<link rel="preconnect" href="https://cdn">` | Cross-origin critical origin (fonts, image CDN) | Limit to ~3-4 critical; each holds a TCP/TLS handshake |
| `<link rel="preload" as="font" crossorigin>` | LCP-contributing font, hero image | ★ Fonts **always** need `crossorigin`; missing it = double-download |
| `<link rel="modulepreload">` | High-priority ES module on current page | Specialised preload — no `as=` needed; populates module map |
| `<link rel="prefetch">` | (Largely superseded by Speculation Rules for navigation) | Low priority; not a substitute for preload |
| HTTP `103 Early Hints` + `Link:` header | Server-stage hints before final response | ★ Best perf; supported on Cloudflare/Fastly/Vercel |

Source: [web.dev resource-hints](https://web.dev/learn/performance/resource-hints), [MDN Speculative loading](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Speculative_loading).

### Speculation Rules API ★

```json
<script type="speculationrules">
{
  "prerender": [{ "where": { "href_matches": "/*" }, "eagerness": "moderate" }],
  "prefetch":  [{ "where": { "href_matches": "/*" }, "eagerness": "conservative" }]
}
</script>
```

- **Replaces** `<link rel="prefetch">` for navigation. Chromium-based browsers only (Chrome/Edge/Opera). Safari/Firefox: graceful no-op. Source: [MDN Speculation Rules](https://developer.mozilla.org/en-US/docs/Web/API/Speculation_Rules_API).
- ★ `eagerness` levels: `immediate` | `eager` | `moderate` (hover) | `conservative` (pointerdown).
- ★ Chrome 144 origin trial: **prerender-until-script** — middle ground between prefetch and full prerender. Source: [Chrome blog](https://developer.chrome.com/blog/prerender-until-script-origin-trial).
- Use `"relative_to": "document"` for relative URL resolution.

### Code splitting & lazy

| Canon | Deprecated | Note |
|---|---|---|
| `const Mod = React.lazy(() => import('./Mod'))` + `<Suspense>` | `React.Loadable` (deprecated) | Built-in since R16.6 |
| Dynamic `import()` for route-level splits | Eager bundle-all | Vite/Rollup auto-split on dynamic import |
| Vite `build.rollupOptions.output.manualChunks` for vendor groups | Webpack `SplitChunksPlugin` (when on Vite) | |
| Route-level + interaction-gated splits | Component-level splits everywhere | Network round-trips > parse cost for small chunks |

Source: [Vite discussion 17730](https://github.com/vitejs/vite/discussions/17730).

### `scheduler.yield()` & Long Animation Frames ★

```js
async function chunkedWork(items) {
  for (const item of items) {
    process(item);
    if (navigator.scheduler?.yield) await scheduler.yield();
    else await new Promise(r => setTimeout(r, 0)); // fallback
  }
}
```

- ★ `scheduler.yield()` continuation is **prioritized** — resumes before other queued tasks. `setTimeout(0)` does not.
- Available Chromium 129+; polyfill via `scheduler-polyfill`.
- **Long Animation Frames (LoAF)** API: `PerformanceObserver({type:'long-animation-frame'})` — supersedes Long Tasks for INP root-causing.
- Source: [web.dev optimize-long-tasks](https://web.dev/articles/optimize-long-tasks), [Chrome LoAF](https://developer.chrome.com/docs/web-platform/long-animation-frames).

### Bundle-size budgets

| Tier | Critical-path JS (min+gzip) | Source |
|---|---|---|
| Aggressive (Calibre/Tinder) | ≤ 100 KB | [calibreapp blog](https://calibreapp.com/blog/bundle-size-optimization) |
| Default mobile (Lighthouse default) | ≤ 170 KB | [addyosmani performance-budgets](https://addyosmani.com/blog/performance-budgets/) |
| CSS critical path | ≤ 20 KB | Tinder example |

Rationale: $200 Android on 400 Kbps link → ~170 KB critical-path budget to hit interactive targets. ★ Vite emits warning at 500 KB chunk — treat as soft fail.

### Edge runtime / streaming SSR ★

- **Next.js Partial Prerendering (PPR)** — stable in Next 16 (Oct 2025). Static shell on edge CDN; dynamic islands streamed from origin. Sub-100 ms LCP achievable. Source: [Vercel PPR](https://vercel.com/blog/partial-prerendering-with-next-js-creating-a-new-default-rendering-model).
- **React Server Components + Flight protocol** — stream serialized component tree chunks; client reconstructs incrementally. Push `"use client"` to leaf components. Source: [react.dev RSC](https://react.dev/reference/rsc/server-components).
- Pattern: each independent data dependency in its own `<Suspense>` boundary with dimension-matched skeleton.
- Edge runtimes (Vercel Edge, Cloudflare Workers): execute closer to user; ms-level resolution. `UNVERIFIED`: Cloudflare retains ~80% edge-CDN-Workers share in 2026.

---

## Part 2 — Accessibility canon (a11y)

### WCAG 2.2 (current legal standard) ★

Published Oct 5, 2023. Now the basis for **ADA, Section 508, and EU EAA**. WCAG 2.1 superseded but back-compat. Source: [W3C What's New 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/).

| New 2.2 SC | Level | Requirement |
|---|---|---|
| 2.4.11 Focus Not Obscured (Min) | AA | Focused control not fully hidden by author UI |
| 2.4.12 Focus Not Obscured (Enh) | AAA | Not partially hidden |
| 2.4.13 Focus Appearance | AAA | ≥ 2 CSS-px outline equivalent + 3:1 vs adjacent |
| 2.5.7 Dragging Movements | AA | Drag-only ops MUST have single-pointer alt |
| 2.5.8 Target Size (Minimum) | AA | ≥ 24×24 CSS px (with explicit exceptions: inline, UA-controlled, essential, equivalent elsewhere) |
| 3.2.6 Consistent Help | A | Help mechanisms in consistent order across pages |
| 3.3.7 Redundant Entry | A | Don't re-ask for previously-entered info in a process |
| 3.3.8 Accessible Authentication (Min) | AA | No cognitive function tests (e.g. transcribe code) without alt |
| 3.3.9 Accessible Authentication (Enh) | AAA | Same, no object-recognition or non-text-content tests |

★ 4.1.1 Parsing was **removed** in 2.2.

### WCAG 3.0 / Silver — DO NOT use for compliance

- Working Draft only. Latest: March 3, 2026 (174 requirements). Source: [W3C WCAG 3 intro](https://www.w3.org/WAI/standards-guidelines/wcag/wcag3-intro/).
- Candidate Recommendation target: Q4 2027. Final Recommendation: ≥ 2028, realistically ~2029.
- Anticipated shifts: outcome-based scoring, APCA contrast, broader cognitive coverage, mobile/native apps, conformance "bronze/silver/gold".
- **Do not teach as production** — flag as forward-looking only.

### ARIA APG (canonical pattern source) ★

- Source: https://www.w3.org/WAI/ARIA/apg/
- Patterns: accordion, alert, alertdialog, breadcrumb, button, carousel, checkbox, combobox, dialog (modal), disclosure, feed, grid, link, listbox, menu, menubar, meter, radio, slider, switch, table, tabs, toolbar, tooltip, treeview.
- ★ Caveat (Stefan Judis, others): APG examples have historically had AT support gaps. Cross-check with AT in real screen readers before shipping.

### 5 Rules of ARIA (W3C `using-aria`) ★

1. **Don't use ARIA if you can use native HTML.** ("No ARIA is better than bad ARIA" — WebAIM survey: pages with ARIA average 41% more detected errors.)
2. Don't change native semantics unless you absolutely must (don't `role="button"` on a `<h2>` — wrap content in `<button>`).
3. All interactive ARIA controls must be keyboard-accessible.
4. Don't use `role="presentation"` or `aria-hidden="true"` on focusable elements.
5. All interactive elements must have an accessible name.

Source: [W3C using-aria](https://www.w3.org/TR/using-aria/), [Deque top-5](https://www.deque.com/blog/top-5-rules-of-aria/).

### Focus management

| Canon (2026) | Deprecated | Source |
|---|---|---|
| `<dialog>.showModal()` — auto focus-trap, Esc-to-close, correct role | Manual focus-trap JS in custom div | [css-tricks no-focus-trap](https://css-tricks.com/there-is-no-need-to-trap-focus-on-a-dialog-element/) |
| `inert` attribute on background trees during modal | `aria-hidden="true"` + `tabindex="-1"` shuffle | [HTML spec inert](https://html.spec.whatwg.org/dev/interaction.html), [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/inert) |
| `:focus-visible` for keyboard-only focus rings | `:focus` (overrides mouse-click focus) | [MDN focus-visible](https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible), Baseline since 2022 |
| Default browser focus ring; restyle only with care | `outline: none` with no replacement | WCAG 2.4.7, 2.4.13 |

### Media-query a11y signals

```css
@media (prefers-reduced-motion: reduce) { /* kill non-essential animation */ }
@media (prefers-contrast: more)         { /* boost contrast */ }
@media (forced-colors: active)          { /* respect system palette; use system-color keywords */ }
@media (prefers-color-scheme: dark)     { /* dark theme */ }
```

- ★ `forced-colors: active` (Windows High Contrast / Contrast Themes): use `CanvasText`, `LinkText`, `ButtonFace`, `Highlight` system-color keywords. Avoid box-shadow-based borders (stripped in forced colors).
- Source: [MDN prefers-contrast](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-contrast).

### Color contrast: APCA vs WCAG 2

| Algorithm | Status | Range | Use today |
|---|---|---|---|
| WCAG 2.x luminance ratio (4.5:1 AA / 7:1 AAA) | **Legal standard** | ratio | Yes, for compliance |
| APCA (Lc value, perceptual) | Working in WCAG 3 draft, not normative | -106 to +106 | ★ Future-proof choice; use **both** if dual-targeting |

WCAG 2 contrast fails ~86% of websites; APCA accounts for font weight/size implicitly. Source: [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html).

### Keyboard navigation / composite widgets

- **Roving tabindex**: container `tabindex="0"`, all but one descendant `tabindex="-1"`; on arrow-key, swap which is `0`. Source: [W3C APG keyboard-interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/).
- Alternative: `aria-activedescendant="IDREF"` — single focused container, descendants stay non-focusable; suited for comboboxes, listboxes.
- ★ Browser auto-scrolls to roving-focused element — works with virtualized lists if elements exist in DOM.

### Screen reader testing matrix (2026)

| SR | Browser | Platform | Market % (WebAIM 2024) |
|---|---|---|---|
| NVDA | Firefox / Chrome | Windows | 65.6% |
| JAWS | Chrome / Edge | Windows (paid) | 60.5% |
| VoiceOver | Safari | macOS / iOS (only on iPhone) | dominant mobile |
| TalkBack | Chrome | Android | dominant Android |
| Narrator | Edge | Windows (built-in) | <5% |

Source: [WebAIM Survey #10](https://webaim.org/projects/screenreadersurvey10/). Minimum coverage: NVDA+Firefox (free) + VoiceOver+Safari iOS.

### i18n

| Canon | Note |
|---|---|
| `<html lang="en">` always set; per-fragment `lang="ja"` for mixed | Required for SR pronunciation |
| `dir="rtl"` + CSS logical properties (`margin-inline-start`) | BiDi safe; no `margin-left` |
| `Intl.DateTimeFormat`, `Intl.NumberFormat`, `Intl.PluralRules`, `Intl.ListFormat`, `Intl.Segmenter` | Native; no library needed for primitives |
| ICU MessageFormat for complex plurals/gender | `formatjs` / `react-intl`, `lingui`, `i18next-icu` |
| `Intl.MessageFormat` (TC39 stage-1) | ★ `UNVERIFIED` final shape; not yet shippable |

Source: [react-intl FormatJS](https://formatjs.github.io/docs/react-intl/), [ICU guide Phrase](https://phrase.com/blog/posts/guide-to-the-icu-message-format/).

---

## Part 3 — AI-native UI patterns (2025-2026)

### Streaming completions UI

| Concern | Canon (2026) |
|---|---|
| Token rendering | Server-sent events / fetch streaming → append to virtualised list |
| Cancel | `AbortController` passed into `fetch(..., { signal })`; also propagate to server (idempotency key) so tokens aren't wasted ★ |
| Combining signals | `AbortSignal.any([userAbort, AbortSignal.timeout(30_000)])` ★ |
| Optimistic UI | React 19 `useOptimistic` hook; reconcile on settled response |
| Resumable streams | Server stores partial; client resumes on reconnect (Vercel AI SDK v5 `resumableStream`) `UNVERIFIED` |

Source: [Chrome render-llm-responses](https://developer.chrome.com/docs/ai/render-llm-responses), [MDN AbortSignal](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal).

### Vercel AI SDK / AI Elements ★

- **AI SDK** (v4/v5): provider-agnostic (`@ai-sdk/openai`, `@ai-sdk/anthropic`, etc.), unified streaming primitives (`streamText`, `streamObject`, `streamUI`).
- **`useChat()`** React hook: messages array, status, stop, regenerate, optimistic append.
- **`streamObject`** — partial-object streaming via Zod schema; progressively fills UI from structured output.
- **AI Elements** (shadcn-style components): pre-built `<Message>`, `<Tool>`, `<Reasoning>`, `<Source>`, `<Image>` primitives.
- Generative UI via React Server Components: model returns server-component tree (Flight) → streamed to client. Source: [Vercel AI SDK 3 generative UI](https://vercel.com/blog/ai-sdk-3-generative-ui), [ai-sdk.dev](https://ai-sdk.dev/docs/ai-sdk-ui).

### Tool-use rendering pattern ★

State-machine per tool call:

| State | UI |
|---|---|
| `model decides to call` | Placeholder card with tool name + spinner |
| `executing` | Same card animated; show partial args if streamed |
| `success` | Card replaced with rich rendering (chart, table, diff, embed) |
| `error` | Inline alert; offer retry |

- Citations: numbered superscripts inline, expandable source card (sidebar or below). Source: [shapeof.ai citations](https://www.shapeof.ai/patterns/citations).
- Code diffs: render with syntax-highlighted `+`/`-` gutters; `diff-match-patch` or `react-diff-viewer`.

### Agent-friendly DOM ★

- Today AI agents (ChatGPT Atlas, Claude Computer Use, browser-use) read **the accessibility tree** — same surface SRs use.
- ⇒ "Good a11y" = "good agent-ability." `getByRole`-passing apps work for agents.
- ★ Emerging: `data-testid` and `data-agent-*` attributes for agent-only hints. No standard yet. `UNVERIFIED`: WAI considering `data-llm-hint` or similar.
- **NLWeb / MCP**: Microsoft's pattern for exposing site capabilities to agents via Model Context Protocol. Source: [techcommunity Microsoft NLWeb](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/the-future-of-ai-optimize-your-site-for-agents---its-cool-to-be-a-tool/4434189).

### Generative UI ★

- Server: model produces JSX / serialized RSC tree (Flight payload).
- Client: receives stream; renders trusted components only (allowlist whitelist!).
- Anti-pattern: letting model output arbitrary HTML strings, then `dangerouslySetInnerHTML` without sanitization.
- Vercel `streamUI` for the canonical implementation.

### Chat UI canon

| Concern | Canon |
|---|---|
| Long message list | **TanStack Virtual** — measure-after-render for variable heights | [TanStack Virtual](https://tanstack.com/virtual/latest) |
| Message edit / retry | Allow edit user message → re-issue from that point (branching tree, not flat) |
| Attachments | Drag-drop + clipboard paste; show thumbnail before upload completes |
| Reasoning trace | Collapsed `<details>` "Thinking…" with token count |
| Streaming code blocks | Render markdown progressively; use **streaming-markdown** + DOMPurify ★ |

### Embedding model output safely

```js
import DOMPurify from 'dompurify';
import { parse as smdParse } from 'streaming-markdown';

const sanitized = DOMPurify.sanitize(htmlChunk);
// If DOMPurify removed anything, halt — content is suspicious.
if (sanitized !== htmlChunk) abortRender();
```

- ★ Treat **LLM output as user-generated content** ("ignore all previous instructions" attack vector).
- Never sanitise chunks in isolation — dangerous code can straddle chunks. Sanitise the **combined** stream and bail on any removal.
- Source: [Chrome render-llm-responses](https://developer.chrome.com/docs/ai/render-llm-responses).

### Latency-tolerant patterns

| Pattern | When |
|---|---|
| Skeleton with **dimension-matched** wireframe | Layout-affecting content (avoids CLS) |
| Shimmer overlay | Loading > 400 ms |
| Optimistic append + reconcile | User-initiated mutations |
| Token-by-token streaming | Any model-generated text > 1 s total |
| Speculation Rules prerender on hover | Likely-next route |

### Local model integration ★

| Tool | Use |
|---|---|
| **Transformers.js (`@xenova/transformers` / Hugging Face)** | NLP/vision via ONNX in browser; WebGPU accel |
| **ONNX Runtime Web** | Generic model runtime; Wasm + WebGPU EPs |
| **Web LLM (MLC)** | LLM-specific WebGPU runtime; Llama 3 / Phi-3 in-browser |
| **WebGPU** | Required for non-trivial throughput; CPU/Wasm fallback usable for small models |
| **Web Neural Network (WebNN)** | ★ Standardised browser NN API; OS-level accelerator routing; behind flag in Chromium 2026 `UNVERIFIED` final shipping date |

Source: [Intel in-browser LLM guide](https://www.intel.com/content/www/us/en/developer/articles/technical/web-developers-guide-to-in-browser-llms.html).

---

## Part 4 — Mobile + cross-platform

| Stack | Status (2026) | Use when |
|---|---|---|
| **React Native + New Architecture (Fabric + TurboModules + JSI + Hermes)** | Default since 2024-25. Hermes default; ~90% core modules migrated. | Mobile-first, web-shareable JS logic |
| **Expo SDK 55** (with RN 0.83) | Released 3× per year; pairs with a single RN version | New RN projects — basically the default starting point |
| **Capacitor** (Ionic) | Modern successor to Cordova; supports Cordova plugins for migration | Web codebase wrapping; PWA + native shell |
| **Cordova** | Declining; legacy maintenance only | Don't start new projects |
| **Tauri 2** | Stable Oct 2024; desktop + iOS/Android. ~10 MB binaries vs Electron ~100 MB | Rust backend, small distributable; mobile is "iterating" |
| **Flutter** | ~46% cross-platform share (RN ~35%); Dart; Flutter Web matured | Pixel-perfect UI parity, embedded/IoT, multi-platform 95%+ code reuse |
| **PWA** | First-class on Android; degraded on iOS (no WebUSB/BT/NFC/MIDI; 7-day cache; EU-DMA standalone removed) | Web reach + install affordance + push (Android-strong) |

Sources: [RN architecture landing](https://reactnative.dev/architecture/landing-page), [Expo SDK 54/55 changelog](https://expo.dev/changelog), [Tauri 2.0 blog](https://v2.tauri.app/blog/tauri-20/), [PWA vs native 2026 magicbell](https://www.magicbell.com/blog/pwa-vs-native-app-when-to-build-installable-progressive-web-app).

### PWA 2026 capability matrix

| Capability | Chrome Android | Safari iOS |
|---|---|---|
| Install / standalone | Yes | Yes (non-EU); **removed in EU under DMA** |
| Push notifications | Native-parity | Limited; less mature |
| Background sync | Yes | No |
| Web Bluetooth / NFC / USB / Serial / MIDI | Yes | No |
| WebGPU / WebNN | Yes | Partial |
| Cache TTL | persistent | 7-day expiry |
| Lighthouse PWA score | ~97/100 | ~86/100 |

---

## Part 5 — Testing canon

| Layer | Canon (2026) | Deprecated / Avoid |
|---|---|---|
| E2E browser | **Playwright** (~20-30M weekly npm vs Cypress ~5M; 4,484+ verified enterprises) | Cypress for new projects; Selenium for new projects (legacy only) |
| Unit / component | **Vitest** (new projects); Jest 30 (existing) | Jest for new Vite projects (slow, ESM clunky) |
| Component dev | **Storybook 9** (Vitest-powered tests + a11y addon + visual diff in one UI) | Storybook 6/7 patterns; manually wired CSF |
| Component dev (lite) | **Ladle** for React-only fast iteration (1.2 s cold start vs Storybook 8 s) | Histoire (Vue/Svelte Vite-based) |
| Visual regression | **Chromatic** for component-level + Storybook; **Percy** for full-page cross-browser; **Playwright `toHaveScreenshot`** in-process | Snapshot-only with no visual layer |
| A11y | **axe-core** via `@axe-core/playwright`, `jest-axe`, Storybook test addon | Manual a11y reviews alone |

### Testing Library first principle ★

`getByRole(name)` is the canonical query — mirrors how SRs and AI agents see the page. Source: [Testing Library byRole](https://testing-library.com/docs/queries/byrole/).

Query priority (Testing Library docs):
1. `getByRole`
2. `getByLabelText` (forms)
3. `getByPlaceholderText`
4. `getByText` (non-interactive)
5. `getByDisplayValue`
6. `getByAltText`, `getByTitle`
7. `getByTestId` (last resort)

### Storybook 9 highlights ★

- Released June 2025; 48% leaner core.
- Vitest-powered interaction tests run via test widget in sidebar.
- A11y testing built-in.
- Visual diff (pixel UI) shipped in-product.
- Watch mode triggers tests on save.

Source: [Storybook 9 blog](https://storybook.js.org/blog/storybook-9/).

### Playwright a11y patterns ★

```ts
import AxeBuilder from '@axe-core/playwright';
test('home is accessible', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

Catches ~50% of WCAG issues automatically; integrates into CI. Source: [Playwright accessibility-testing](https://playwright.dev/docs/accessibility-testing).

---

## Anti-canon (do not teach)

| Anti-pattern | Replace with |
|---|---|
| FID metric | INP (since March 2024) |
| `position: fixed` + manual overlay for modals | `<dialog>.showModal()` + `inert` background |
| `tabindex="2"`, `tabindex="3"` (positive values) | `tabindex="0"` for participation; `tabindex="-1"` programmatic-only; never positive |
| `<img>` with no `alt` | `alt=""` (decorative) or descriptive `alt="..."` |
| ARIA `role="button"` on a `<div>` | Use `<button>` |
| `aria-label="Submit"` on a `<button>Submit</button>` | Redundant; remove |
| `outline: none` with no replacement | `:focus-visible { outline: 2px solid ... }` |
| Mock keyboard events (`fireEvent.keyDown`) for keyboard tests | Playwright `page.keyboard.press('Tab')`; Testing Library `userEvent.keyboard()` |
| `fetchpriority="high"` on every image | Single LCP candidate only |
| `loading="lazy"` on the LCP image | Remove; LCP image must not be deferred |
| `<link rel="prefetch">` for next-page nav | Speculation Rules API |
| `setTimeout(fn, 0)` to yield to browser | `await scheduler.yield()` (or polyfill) |
| WCAG 2.0/2.1 as ship target | WCAG 2.2 AA (legal floor for ADA / Section 508 / EAA) |
| WCAG 3.0 for production compliance | Not normative; do not claim conformance |
| `dangerouslySetInnerHTML(modelOutput)` | DOMPurify + streaming-markdown; bail on sanitiser removal |
| Cordova for new mobile hybrid projects | Capacitor (Ionic) |
| Cypress as default for new E2E | Playwright |
| Jest for new Vite/ESM projects | Vitest |
| Manual focus-trap in `<div role="dialog">` | Native `<dialog>` + `inert` |
| `aria-hidden="true"` on background during modal | `inert` |
| `:focus` styled with no `:focus-visible` consideration | `:focus-visible` to avoid mouse-click rings |

---

## Token estimate

- Approximate body content above: ~5,500 tokens (rough: 1 token ≈ 4 chars; ~22 KB of markdown).
- Per-item canonical tables + code snippets → ~80% structural / 20% prose.
- Recommended distillation into training corpus: keep tables verbatim; collapse rationale prose to single sentences where the table column is empty.

## License gate

| Source class | License | Use in training corpus |
|---|---|---|
| W3C specs (WAI/ARIA/WCAG/HTML/CSS) | W3C Document License (permissive, attribution) | OK |
| MDN content | CC-BY-SA 2.5 | OK with attribution + share-alike if redistributed |
| web.dev / Chrome for Developers | CC-BY 4.0 | OK with attribution |
| Storybook docs | MIT | OK |
| Playwright / Vitest / Testing-Library docs | Apache-2.0 / MIT | OK |
| Vercel AI SDK docs | Apache-2.0 | OK |
| Tauri docs | Apache-2.0 / MIT dual | OK |
| **Exceptions / restricted**: | | |
| Deque Axe rule docs / DequeUniversity | Proprietary (some pages free, some gated) | ★ Quote sparingly; prefer linking |
| Adobe Spectrum (referenced for roving tabindex) | Apache-2.0 | OK |
| JAWS / Freedom Scientific docs | Proprietary | Don't reproduce; cite behavior only |
| WebAIM survey raw data | Proprietary; summary stats fair-use citation | OK to cite stats |
| Vendor blogs (DebugBear, LogRocket, etc.) | All-rights-reserved by default | Cite + paraphrase; don't reproduce verbatim |

Most canonical sources (W3C, MDN, web.dev, framework docs) are corpus-safe. The two flag-classes: **Deque proprietary** content and **vendor blog** prose — paraphrase rather than ingest verbatim.

---

## Key sources (compact)

- [web.dev Web Vitals](https://web.dev/articles/vitals) · [defining thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds)
- [web.dev fetch-priority](https://web.dev/articles/fetch-priority) · [DebugBear avoid-overuse](https://www.debugbear.com/blog/avoid-overusing-fetchpriority-high)
- [MDN Speculation Rules](https://developer.mozilla.org/en-US/docs/Web/API/Speculation_Rules_API) · [Chrome prerender](https://developer.chrome.com/docs/web-platform/prerender-pages)
- [web.dev optimize-long-tasks](https://web.dev/articles/optimize-long-tasks) · [Chrome LoAF](https://developer.chrome.com/docs/web-platform/long-animation-frames)
- [web.dev resource-hints](https://web.dev/learn/performance/resource-hints) · [DebugBear resource-hints](https://www.debugbear.com/blog/resource-hints-rel-preload-prefetch-preconnect)
- [W3C WCAG 2.2 What's New](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) · [W3C WCAG 3 intro](https://www.w3.org/WAI/standards-guidelines/wcag/wcag3-intro/)
- [W3C ARIA APG](https://www.w3.org/WAI/ARIA/apg/) · [W3C using-aria](https://www.w3.org/TR/using-aria/)
- [W3C APG keyboard-interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/)
- [MDN inert](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/inert) · [css-tricks no focus trap on dialog](https://css-tricks.com/there-is-no-need-to-trap-focus-on-a-dialog-element/)
- [MDN prefers-contrast](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-contrast) · [MDN focus-visible](https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible)
- [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html)
- [WebAIM Survey #10](https://webaim.org/projects/screenreadersurvey10/)
- [Chrome render-llm-responses](https://developer.chrome.com/docs/ai/render-llm-responses)
- [Vercel AI SDK docs](https://ai-sdk.dev/docs/ai-sdk-ui) · [Vercel AI SDK 3 generative UI](https://vercel.com/blog/ai-sdk-3-generative-ui)
- [Vercel PPR blog](https://vercel.com/blog/partial-prerendering-with-next-js-creating-a-new-default-rendering-model) · [react.dev RSC](https://react.dev/reference/rsc/server-components)
- [Reactnative.dev New Architecture](https://reactnative.dev/architecture/landing-page) · [Tauri 2.0 blog](https://v2.tauri.app/blog/tauri-20/)
- [Playwright accessibility-testing](https://playwright.dev/docs/accessibility-testing) · [Testing Library byRole](https://testing-library.com/docs/queries/byrole/)
- [Storybook 9 release](https://storybook.js.org/blog/storybook-9/) · [Ladle v3](https://ladle.dev/blog/ladle-v3/)
- [TanStack Virtual](https://tanstack.com/virtual/latest)
- [addyosmani performance budgets](https://addyosmani.com/blog/performance-budgets/)
- [Intel in-browser LLM guide](https://www.intel.com/content/www/us/en/developer/articles/technical/web-developers-guide-to-in-browser-llms.html)
