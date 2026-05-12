# Tier F-2 — CSS + Native Web Platform Canon (2025-2026)

Research recipe: what the `code` verb of `hexa-forge` should teach when a programmer says "modern frontend" in 2026. Output describes what's actually shipping in browsers and considered canonical, not 2010-era CSS.

Date of research: 2026-05-11.
Legend: ★ = additional find beyond the prompt list. `UNVERIFIED` = exact version/date not double-checked.

---

## Part 1 — CSS layout & sizing current canon

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| Container Queries (`@container`, size queries) | Baseline since Feb 2023; ~95% global in 2026 | Component-level responsive design tied to *parent box*, not viewport | Most `@media (max-width:…)` breakpoints for component-internal layout | MDN; LogRocket; web.dev |
| Container query units (`cqi`, `cqb`, `cqw`, `cqh`, `cqmin`, `cqmax`) | Same as above | Typography & spacing scaled to container inline size (`font-size: clamp(1rem, 4cqi, 2rem)`) | viewport-relative `vw`/`vh` for inside-component sizing | CSS-Tricks; caniuse |
| Style queries (`@container style(--theme: dark)`) | Chromium 111+; Firefox/Safari rolling in 2026 | Theming variants on a per-subtree basis | Class-toggle hacks | LogRocket 2026 |
| CSS Grid (Level 1/2) | Universal since ~2017 | Two-dimensional layout, including page shell | `float` layouts, table-layout abuse | MDN |
| `subgrid` | Baseline Widely Available **2026-03-15**; Firefox 71+, Safari 16+, Chrome 117+ | Nested grids that inherit parent track sizing — card grids, form rows aligning across siblings | Manual width matching, JS measuring | zenn.dev; caniuse |
| Masonry layout (CSS Grid Level 3 / "grid lanes") | **Not Baseline** as of 2026-05; ongoing implementation; WG resolved syntax late 2025 using `display: grid-lanes` | Pinterest-style packed layouts, when shipped | JS masonry libs (Masonry.js, isotope) | w3c blog 2025-09; WebKit blog; MDN |
| Flexbox + `gap` | Universal | One-dimensional row/column layout; component-internal spacing | margin hacks; `> * + *` lobotomized owl for siblings | MDN |
| Logical properties (`margin-inline`, `padding-block`, `inset-inline-start`, `border-block-end`) | Universal | i18n-correct spacing & borders that flip in RTL writing-modes automatically | `margin-left`/`right`, manual `[dir=rtl]` overrides | drafts.csswg.org; lapidist.net |
| Anchor Positioning (`anchor()`, `position-anchor`, `@position-try`, `position-area`) | Baseline 2026; Chrome 125+, Firefox 132/147+, Safari 26+ (`@position-try` 18.4+) | Tooltips, menus, popovers tethered to a trigger without JS positioning libs | Floating UI, Popper.js for many cases | OddBird 2025-10; Chrome blog; caniuse |
| Scroll-driven animations (`animation-timeline: scroll()` / `view()`) | Chromium 115+, Safari 18+; Firefox behind flag 2026; ~85% caniuse | Progress bars, parallax, fade-in-on-view, sticky-reveal — CSS-only | IntersectionObserver scroll listeners; GSAP ScrollTrigger for simple cases | MDN; Chrome blog; Josh Comeau |
| ★ Scroll-triggered animations (Chrome 145, 2026) | Shipping in Chrome 145 | Time-based animation triggered when crossing a scroll offset | JS event listeners on scroll | Chrome blog 2026 |
| `aspect-ratio` | Universal since 2021 | Reserving box space for media; `aspect-ratio: 16/9` on video/img containers | Padding-bottom hack (`padding-bottom: 56.25%`) | MDN |
| `min-content` / `max-content` / `fit-content()` | Universal in Grid/Flex contexts | Shrink-wrap and shrink-to-fit sizing; text won't wrap with `width: max-content`, fits parent with `fit-content()` | Magic numbers; JS measuring | w3.org CSS Sizing 3 |

**Analysis.** The 2026 layout canon is: Grid for the page shell, Flexbox for one-dimensional rows of controls, container queries for any sizing logic that depends on the *component's* space (sidebars, embedded cards), and logical properties so RTL Just Works. Subgrid is now safe to ship and replaces the JS measurement hacks for "make these heights line up across cards". Anchor positioning is the headline 2026 feature — entire Floating UI use cases collapse into a stylesheet. Masonry is *not* yet Baseline, so for now JS masonry libs remain canonical for that one specific pattern.

---

## Part 2 — CSS color & visual current canon

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| `oklch()` / `oklab()` | Baseline (Chrome 111+, Safari 15.4+, Firefox 113+); Widely Available 2026 | Design-token color definitions; perceptually uniform lightness ramps | `hsl()` for any lightness scale (HSL's `L` lies across hues) | MDN; evilmartians |
| `color-mix(in oklch, …)` | Baseline Widely Available 2026 | Token tinting/shading (`color-mix(in oklch, var(--accent), white 20%)`); hover/active state derivation | Sass `lighten()`/`darken()`, JS color libs (chroma.js, color2k) for static derivations | DevToolbox 2026; CSS-Tricks |
| Relative Color Syntax (`oklch(from var(--c) calc(l - 0.1) c h)`) | Baseline 2024-2025; widely available | Programmatic color manipulation in pure CSS — derive hover/focus/dark variants from one source | Build-time SCSS color functions for variable colors | Chrome blog; MDN |
| `color-scheme: light dark` | Universal since 2022 | Opt UA controls (scrollbars, form widgets) into both schemes | Manual styling of every UA chrome element | MDN; modern-css.com |
| `light-dark(<light>, <dark>)` | Chrome 123, Safari 17.4, Firefox 120; ~95% in 2026 | Dual-scheme token values without `prefers-color-scheme` media query, e.g. `color: light-dark(black, white)` | `@media (prefers-color-scheme: dark)` block duplication | web.dev; MDN |
| CSS Custom Properties (`--token`) | Universal | Design-token medium; theme switching via root vars; component-scoped vars for variants | Sass/Less variables for runtime-mutable values | MDN |
| `@property` (registered custom properties, typed + animatable) | Baseline (Chrome 85+, Safari 16.4+, Firefox 128+) | Typed, animatable variables — gradient animations, smooth color interpolations, type-safe tokens | Discrete (non-interpolated) variable transitions | web.dev; MDN |
| Cascade Layers (`@layer reset, base, tokens, components, utilities`) | All evergreen browsers since 2022 | Design-system layering: third-party CSS goes in a low-priority layer; utility classes in the top layer beats components; **no `!important` arms race** | Specificity hacks, `!important`, BEM-only discipline | CSS-Tricks; design.dev |
| `:has()` parent/contains selector | Baseline since 2023; "most-loved" State of CSS 2025 | Style a card *because* it contains an image; style a form *because* an input is invalid; light/dark toggle via `:has(:checked)` purely in CSS | JS class-toggling for state-driven styling | WebKit blog; ishadeed; logrocket |
| `:focus-visible` | Universal | Show focus ring only on keyboard navigation, not mouse clicks — the modern accessibility default | Brutally suppressed `:focus { outline: none }` patterns | MDN |
| ★ `@starting-style` | Chrome 117+, Safari 17.5+, Firefox 129+ | Animate elements from a starting state on first paint or on display change (e.g., dialog/popover entry) | JS-driven "add class on next tick" entry animations | Frontend Masters |

**Analysis.** Color in 2026 is: declare tokens once in `oklch()`, derive every variant with `color-mix()` / relative color syntax, expose to dark mode with `light-dark()`. Cascade Layers are the structural lever — design systems that ship as a single CSS layer cannot be over-specified by app code by accident. `:has()` is the single biggest shift in selector philosophy since the cascade itself; it dissolves dozens of patterns that used to require JS state. `@property` is what makes gradient and conic animations possible at all.

---

## Part 3 — Native HTML elements that replaced JS libs

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| `<dialog>` + `dialog.showModal()` | Baseline (Chrome 37+, Firefox 98+, Safari 15.4+) | Native modal: focus trap, backdrop, ESC dismiss, `::backdrop`, returnable result via `<form method="dialog">` | react-modal, Headless UI Dialog, react-aria-modal, every bespoke modal | MDN; Frontend Masters |
| Popover API (`popover` attr, `popovertarget`, `popovertargetaction`) | Baseline Widely Available 2025-2026 | Non-modal overlays: menus, dropdowns, toasts, tooltips. Auto-dismiss on outside click / ESC; top-layer rendering | Floating UI runtime for triggering; ad-hoc click-outside handlers | MDN Popover API; calmops |
| `<details>` / `<summary>` | Universal | Disclosure widgets, FAQs, accordions (`name=""` attr 2024+ makes exclusive groups) | All "accordion" component libs for simple disclosure | MDN |
| `::details-content` & `interpolate-size: allow-keywords` ★ | Chrome 131+; rolling out 2026 | Animating `<details>` open/close (height auto interpolation finally works) | JS height-measuring accordion components | Chrome blog 2024-2026 |
| View Transitions API (`document.startViewTransition()`) | Same-document: Chrome 111+, Safari 18+, Firefox 133+. Cross-doc (MPA): Chrome 126+ | Animated transitions between SPA route changes and MPA navigations; shared-element transitions via `view-transition-name` | Framer Motion `AnimatePresence` for route transitions; Next.js `<Link>` page-transition libs | MDN; Chrome devs |
| `inert` attribute | Universal (Firefox added it 2023) | Disable an entire subtree from focus/click/find-in-page while a modal is open | Manual `tabindex="-1"` walking; `aria-hidden` + `pointer-events: none` hacks | MDN; chromestatus |
| `<search>` element | Universal as of 2024 | Landmark for site/app search regions — `role="search"` without ARIA | `<div role="search">` | MDN HTML |
| `field-sizing: content` (textarea/input auto-grow) | Chromium 123+; **not Baseline** — Firefox/Safari still missing as of mid-2025 | Auto-growing textarea without JS | `react-textarea-autosize`, manual `scrollHeight` measuring (still required as fallback) | MDN; CSS-Tricks |
| ★ Invoker Commands (`command`, `commandfor`) | Chrome 135+ shipping 2025-2026 | Declarative wiring of buttons to actions on other elements without JS | onclick handlers for show/hide/toggle | Frontend Masters |

**Analysis.** The hexa-forge corpus should bias hard toward native elements first. The chain `<dialog>` + Popover API + Anchor Positioning + View Transitions handles maybe 70% of what UI libraries used to do — modals, menus, dropdowns, tooltips, and route transitions — all without JS. `<details name="…">` finally makes radio-group accordions a one-liner. `field-sizing` is *almost* there but still needs a JS fallback in Firefox/Safari; teach it as progressive enhancement only.

---

## Part 4 — Web platform APIs current

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| Container Queries × `:has()` combined | Baseline | "Card has image AND container is wide → horizontal layout" — pure-CSS conditional component variants | Render-prop variants in JS for layout switching | logrocket |
| WebGPU | All major browsers shipping by Jan 2026 (Firefox 147, Safari iOS/macOS 26); ~70% global, growing | New 3D / GPGPU code; ML in browser via WebGPU compute; Three.js r171+ ships WebGPU backend w/ WebGL2 fallback | WebGL2 for new projects (still need fallback for ~30% of users) | webgpu.com; web.dev; utsubo three.js |
| WebAuthn / Passkeys (`navigator.credentials.create/get` w/ `publicKey`) | Universal in all major browsers and OSes (iOS/Android/Win/macOS); FIDO Alliance >200% YoY growth | Primary auth flow for new apps; passwords become recovery-only by 2026-2027 per analysts | Password + 2FA SMS/TOTP for the primary auth path | webauthn.me; mojoauth; canadiantechnologymagazine |
| WebTransport (over HTTP/3 / QUIC) | Chrome/Edge stable; Firefox partial; Safari in development; ~75% coverage 2025 | Niche: gaming, low-latency media streaming, multiplexed streams with mixed reliability | WebSockets *only when* you need datagrams or multiplexed streams; otherwise WS still canonical | websocket.org; ably; videosdk |
| WebSockets | Universal; 99%+ | Bidirectional realtime for most apps | Long-polling for nearly all use cases | websocket.org |
| Streams API (`ReadableStream`, `TransformStream`, `WritableStream`) | Universal | SSR streaming via `renderToReadableStream` (edge) / `renderToPipeableStream` (Node); SSE bodies; large file processing in chunks | Buffering full responses in memory; manual chunk handling | React docs; patterns.dev |
| `AbortController` / `AbortSignal` (incl. `AbortSignal.timeout()`, `AbortSignal.any()`) | Universal | Cancellable fetch; React effect cleanup; user-cancelled long tasks; per-request timeouts | `isMounted` flags; race-condition cleanup hacks; manual timeout loops | MDN; webdevsimplified 2025 |
| Service Workers | Universal | Offline cache; network interception; precache + runtime caching with strategies (cache-first for assets, stale-while-revalidate for shell, network-first for API) | AppCache (long deprecated); manual cache headers alone | web.dev; MDN |
| Background Sync / Background Fetch | Chromium-only as of 2026 (Firefox/Safari not implemented) | Defer-and-retry network operations when offline; large downloads that survive tab close | Manual retry queues in localStorage | MDN PWA |
| IndexedDB via Dexie | Universal IDB; Dexie is canonical wrapper | Offline-first apps with real schemas, indexes, queries; `useLiveQuery` for reactive React | Raw IDB (verbose); localForage (simpler but less powerful) | dexie.org; pkgpulse |
| `idb-keyval` (Jake Archibald) | Universal | Tiny (~600B) key-value cache when you don't need queries — auth tokens, last-route, cached JSON | localStorage (synchronous, blocks main thread) | github jakearchibald/idb |
| Storage Access API (`requestStorageAccess()`) | All major browsers (slight differences) | Cross-site embeds that legitimately need first-party storage (SSO, embedded media) under 3p-cookie deprecation | Third-party cookies (now blocked by default in Safari, Firefox, increasingly Chrome) | MDN; privacysandbox |
| Storage Buckets API | `UNVERIFIED` — Chromium experiment, not Baseline | Partition site storage into eviction-priority buckets | Single quota for all storage | chromestatus |

**Analysis.** WebGPU is *the* graphics inflection — teach WebGPU for new GPU code, but with a WebGL2 fallback path (Three.js does this automatically). Passkeys are the new password — corpus should default new auth examples to WebAuthn registration + assertion, with password as legacy. WebTransport is a footnote — most realtime still uses WebSockets in 2026; only teach WebTransport for the narrow case (datagrams, gaming, low-latency media). `AbortController` is the most under-taught primitive on the platform; it should appear in every fetch example.

---

## Part 5 — Build tooling current canon

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| Vite (5 / 6 / 7+) | Dominant — 65M weekly npm downloads; default for Nuxt, SvelteKit, Astro, Angular 17+, SolidStart | Default frontend dev server + builder; native ESM dev, Rollup/Rolldown for prod | Webpack for nearly all new greenfield projects; Create React App (deprecated) | pkgpulse; theregister |
| Rolldown | Stable in Vite 8 (2026); 10–30× faster builds vs esbuild+Rollup combo | Vite's internal bundler (production + dev); reduces dev/prod parser divergence | The esbuild+Rollup split inside Vite | theregister 2026-03; devclass |
| esbuild | Universal in tooling; "very fast" tier | Library bundling, lambda bundling, CLI tools; still Vite's transformer in older versions | Babel + Webpack pipeline for pure JS/TS builds | github |
| Bun (runtime + bundler + test runner + pkg manager) | Production for many shops as of 2025-2026 | All-in-one toolchain for Node-replacement workloads; HTTP server, test runner, `bun install` faster than pnpm | Node + npm + jest + webpack for greenfield server JS | pkgpulse Bun vs Vite |
| Turbopack | Stable in Next.js dev (2024) and prod (rolling); **Next.js-only** as of mid-2026, no standalone | Default dev/build for new Next.js apps | Webpack inside Next.js | techsy.io; pkgpulse |
| Rspack (Rust-based Webpack-compatible) | Stable; ByteDance + adopted at scale | Drop-in faster Webpack for projects with Webpack-specific plugins they can't shed | Webpack (when migration is too costly) | github rstackjs; kunalganglani |
| SWC (Rust) | Default transformer in Next.js, Parcel, Rspack, Deno | TypeScript/JSX → JS transform; ~20× faster than Babel single-thread, ~70× on 4 cores | Babel for nearly all standard transforms (Babel still wins on exotic plugins) | swc.rs; logrocket |
| Oxc | Emerging Rust JS toolchain (linter, resolver, transformer) `UNVERIFIED` for prod use scale | Faster lint + resolve in monorepos | ESLint + parts of SWC for narrow cases | pkgpulse oxc vs swc |

**Analysis.** Canon 2026: **Vite for the frontend, Bun if you want one-tool everything, Next.js + Turbopack only if you're already in Next.js.** Webpack is legacy maintenance; new projects should not start there. Rolldown rolling into Vite collapses the dev/prod bundler split that has caused subtle bugs for years. SWC is the de-facto transform layer beneath nearly every modern toolchain — Babel survives only for plugin-heavy edge cases.

---

## Part 6 — TypeScript ecosystem

| feature | browser support / status | canonical use | replaces / supersedes | sources |
|---|---|---|---|---|
| Native TS in Node (`--experimental-strip-types` default in v22.18+ and v24.3+) | Stable in Node 22.18+ / 24.3+; Node 24 = recommended LTS (2026) | Run `.ts` directly with `node script.ts` for scripts, simple apps | `ts-node`, `tsx`, dedicated transpile-then-run flow | nodejs.org typescript; nodesource |
| Type-stripping limits | Cannot strip: enums, instantiated namespaces, parameter properties (these emit JS). Node ignores `tsconfig.json` — no `paths`, no down-leveling | Write "erasable TS": types, interfaces, `as`, generics — yes. Avoid `enum`/`namespace` if relying on strip | The Babel/SWC plugin step for pure type erasure | nodejs.org; satanacchio |
| `tsc --noEmit` | Universal | Type-check only — emit comes from bundler (esbuild/SWC/Vite) | `tsc` as compiler for emit (slow for large repos) | typescriptlang.org |
| `tsgo` / TypeScript 7 (Native port in **Go**, not Rust) | TypeScript 7.0 Beta released **2026-04-21**; stable in mid-2026 | 10× faster type-checking (78s → 7.5s on VS Code), 2.9× lower memory | `tsc` (JS) for large-codebase type-check perf | github microsoft/typescript-go; infoworld 2026; devblogs |
| Canonical `tsconfig.json` (2026) | Standard | `"strict": true`, `"target": "ES2022"`+, `"module": "esnext"`, `"moduleResolution": "bundler"`, `"isolatedModules": true`, `"noEmit": true`, `"verbatimModuleSyntax": true`, `"skipLibCheck": true`, `"esModuleInterop": true`, `"resolveJsonModule": true` | `"moduleResolution": "node"` for bundler projects; `"strict": false`; `"target": "ES5"` for non-IE projects | typescriptlang.org; starterpick; reintech |

**Analysis.** The prompt asked about a "Rust TS compiler" — it's actually Go (Project Corsa). That mistake is worth correcting in the corpus. Native Node TS is a real shift: small scripts and tools no longer need a build step at all, but production apps still want a real bundle (Vite/Bun) and a real type-check pass (`tsc --noEmit` or `tsgo`). The 2026 tsconfig defaults converge across frameworks; `moduleResolution: "bundler"` is now the consensus rather than `node`/`node16`.

---

## Anti-canon (do NOT teach)

- **Floats for layout.** Floats are for text-wrap around images. Use Grid/Flexbox.
- **`position: absolute` + negative-margin centering.** Use Grid `place-items: center` or Flexbox `align-items: center; justify-content: center`.
- **jQuery, Backbone, Knockout.** No new code. Even DOM convenience is covered by `querySelector`, `closest`, `fetch`, `AbortController`.
- **IE6/7/8/9 polyfills, `core-js` for ES6 features, `@babel/preset-env` targeting IE.** Baseline targets 2 years back of evergreen browsers.
- **`@media (max-width: 768px)` for component-internal responsiveness.** Use container queries. Viewport media queries are now reserved for *page-level* breakpoints (sidebar collapse, etc.).
- **`hsl()` for design tokens.** Use `oklch()` — HSL lightness is not perceptual and produces uneven ramps.
- **Sass `lighten()`/`darken()` for runtime variants.** Use `color-mix(in oklch, …)` or relative color syntax — they're runtime, theme-aware, and live in CSS.
- **JS modal libraries (react-modal, react-aria-modal).** Use `<dialog>` + `showModal()` unless you need a non-standard behavior. Use Popover API for non-modal overlays.
- **Floating UI / Popper.js for tooltip & menu positioning.** Use CSS Anchor Positioning where supported. Keep Floating UI only as fallback for Safari <26 and complex flip logic.
- **CSS-in-JS runtime (styled-components, Emotion) for new design systems.** Use CSS Custom Properties + Cascade Layers + `@property`. Zero-runtime CSS-in-JS (vanilla-extract, Panda CSS) is acceptable if the team genuinely needs it.
- **`tabindex="-1"` walks + `aria-hidden` to disable a subtree.** Use `inert`.
- **`localStorage` for non-trivial state.** Synchronous, main-thread blocking, 5MB cap. Use IndexedDB via `idb-keyval` (simple) or Dexie (real data).
- **`onerror` retry loops, `isMounted` flags.** Use `AbortController` and `AbortSignal.timeout()`.
- **`renderToString` SSR.** Use streaming SSR (`renderToReadableStream` / `renderToPipeableStream`) for any large page.
- **WebGL2 for greenfield 3D / GPU compute.** Use WebGPU with a WebGL2 fallback (Three.js handles this).
- **Babel for vanilla TS → JS.** Use SWC or esbuild. Babel only when you need plugin features SWC doesn't replicate.
- **Webpack for new projects.** Use Vite (or Turbopack in Next.js, Rspack if migrating from Webpack).
- **`ts-node` / `tsx` for Node scripts (when Node ≥22.18).** Use native type-stripping for scripts; reach for `tsx` only when you need decorators, enums, namespaces, or tsconfig paths.
- **`tsconfig.json` with `moduleResolution: "node"` in a Vite/Bun/esbuild project.** Use `"bundler"`.
- **CommonJS-only packages in new code.** Author ESM; publish dual where needed.
- **Passwords as primary auth in a new app.** Default to passkeys (WebAuthn); keep password as recovery-only.
- **Third-party cookies for SSO embeds.** Use Storage Access API + partitioned storage / FedCM.

---

## Token estimate

Rough order, single-pass without sub-expansion of linked sources:

| section | est. tokens |
|---|---|
| Part 1 layout | ~1,500 |
| Part 2 color/visual | ~1,400 |
| Part 3 native HTML | ~1,200 |
| Part 4 platform APIs | ~1,600 |
| Part 5 build tooling | ~1,000 |
| Part 6 TypeScript | ~900 |
| Anti-canon | ~700 |
| **Total** | **~8,300** |

Order-of-magnitude budget for the `code` verb training shard derived from this report (with examples + minimal source quotes expanded): **~25-40k tokens**.

---

## Sources

Layout & sizing:
- [LogRocket — Container queries in 2026](https://blog.logrocket.com/container-queries-2026/)
- [web.dev — Container queries in action](https://web.dev/articles/baseline-in-action-container-queries)
- [caniuse — CSS Container Query Units](https://caniuse.com/css-container-query-units)
- [W3C CSSWG — Masonry update Sep 2025](https://www.w3.org/blog/CSS/2025/09/18/masonry-update-issues/)
- [WebKit blog — Masonry syntax](https://webkit.org/blog/16026/css-masonry-syntax/)
- [zenn.dev — Subgrid in all browsers](https://zenn.dev/tonkotsuboy_com/articles/css-subgrid-all-browsers?locale=en)
- [caniuse — CSS Subgrid](https://caniuse.com/css-subgrid)
- [OddBird — Anchor positioning fall 2025](https://www.oddbird.net/2025/10/13/anchor-position-area-update/)
- [Chrome devs — Anchor positioning API](https://developer.chrome.com/blog/anchor-positioning-api)
- [MDN — Scroll-driven animations](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations)
- [Chrome devs — Scroll-triggered animations](https://developer.chrome.com/blog/scroll-triggered-animations)
- [W3C CSS Logical Properties](https://drafts.csswg.org/css-logical/)
- [Brett Dorrans — From margin-left to margin-inline](https://lapidist.net/articles/2025/from-margin-left-to-margin-inline-why-logical-css-properties-matter/)
- [W3C CSS Box Sizing 3](https://www.w3.org/TR/css-sizing-3/)

Color & visual:
- [Evil Martians — OKLCH in CSS](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl)
- [MDN — oklch()](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/oklch)
- [DevToolbox — color-mix complete guide 2026](https://devtoolbox.dedyn.io/blog/css-color-mix-complete-guide)
- [Chrome devs — Relative color syntax](https://developer.chrome.com/blog/css-relative-color-syntax)
- [MDN — light-dark()](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/light-dark)
- [web.dev — light-dark()](https://web.dev/articles/light-dark)
- [web.dev — @property baseline](https://web.dev/blog/at-property-baseline)
- [MDN — @property](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@property)
- [CSS-Tricks — Cascade Layers guide](https://css-tricks.com/css-cascade-layers/)
- [Design Systems Collective — Cascade Layers for design systems](https://www.designsystemscollective.com/mastering-css-cascade-layers-for-scalable-design-systems-981fdab2a961)
- [WebKit — :has() pseudo-class](https://webkit.org/blog/13096/css-has-pseudo-class/)
- [Ahmad Shadeed — :has() parent selector](https://ishadeed.com/article/css-has-parent-selector/)

Native HTML & overlays:
- [MDN — `<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
- [MDN — Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API)
- [Frontend Masters — Difference between dialog and popovers](https://frontendmasters.com/blog/whats-the-difference-between-htmls-dialog-element-and-popovers/)
- [Frontend Masters — Menus, toasts, popovers, anchors, @starting-style](https://frontendmasters.com/blog/menus-toasts-and-more/)
- [MDN — View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API)
- [Chrome devs — View Transitions](https://developer.chrome.com/docs/web-platform/view-transitions)
- [MDN — inert attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/inert)
- [MDN — field-sizing](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/field-sizing)

Platform APIs:
- [webgpu.com — WebGPU hits critical mass](https://www.webgpu.com/news/webgpu-hits-critical-mass-all-major-browsers/)
- [web.dev — WebGPU in major browsers](https://web.dev/blog/webgpu-supported-major-browsers)
- [webauthn.me — WebAuthn and Passkeys](https://www.webauthn.me/passkeys)
- [MojoAuth — Enterprise SaaS passkeys](https://mojoauth.com/blog/why-enterprise-saas-companies-are-moving-to-passkeys)
- [Ably — WebTransport vs WebSockets](https://ably.com/blog/can-webtransport-replace-websockets)
- [WebSocket.org — Future of WebSockets](https://websocket.org/guides/future-of-websockets/)
- [MDN — AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [Web Dev Simplified — Advanced AbortController](https://blog.webdevsimplified.com/2025-06/advanced-abort-controller/)
- [web.dev — Service workers](https://web.dev/learn/pwa/service-workers)
- [MDN — Offline and background operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation)
- [Dexie.org](https://dexie.org/)
- [github jakearchibald/idb](https://github.com/jakearchibald/idb)
- [MDN — Storage Access API](https://developer.mozilla.org/en-US/docs/Web/API/Storage_Access_API)
- [patterns.dev — Streaming SSR](https://www.patterns.dev/react/streaming-ssr/)
- [React docs — renderToPipeableStream](https://react.dev/reference/react-dom/server/renderToPipeableStream)

Build tooling:
- [The Register — Vite team claims 10-30x faster with Rolldown](https://www.theregister.com/software/2026/03/16/vite-team-claims-10-30x-faster-builds-with-rolldown/5221578)
- [DevClass — Vite + Rolldown 10-30x](https://www.devclass.com/development/2026/03/17/vite-team-boasts-10-30x-faster-builds-with-rust-powered-rolldown/5209472)
- [PkgPulse — Bun vs Vite 2026](https://www.pkgpulse.com/guides/bun-vs-vite-2026)
- [PkgPulse — Turbopack vs Vite 2026](https://www.pkgpulse.com/guides/turbopack-vs-vite-2026)
- [Techsy.io — Turbopack vs Webpack vs Vite](https://techsy.io/en/blog/turbopack-vs-webpack-vs-vite)
- [github rstackjs/build-tools-performance](https://github.com/rstackjs/build-tools-performance)
- [swc.rs](https://swc.rs/)
- [LogRocket — Why use SWC over Babel](https://blog.logrocket.com/why-you-should-use-swc/)

TypeScript:
- [Node.js Modules: TypeScript](https://nodejs.org/api/typescript.html)
- [NodeSource — Native TypeScript in Node.js](https://nodesource.com/blog/Node.js-Supports-TypeScript-Natively)
- [github microsoft/typescript-go](https://github.com/microsoft/typescript-go)
- [InfoWorld — Native TS port targets early 2026](https://www.infoworld.com/article/4100582/microsoft-steers-native-port-of-typescript-to-early-2026-release.html)
- [Microsoft devblogs — TypeScript 7.0 Beta](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0-beta/)
- [StarterPick — TSConfig boilerplate best practices 2026](https://starterpick.com/guides/typescript-config-boilerplate-best-practices-2026)
- [typescriptlang.org — moduleResolution](https://www.typescriptlang.org/tsconfig/moduleResolution.html)
