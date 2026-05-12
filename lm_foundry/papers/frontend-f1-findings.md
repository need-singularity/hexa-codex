# frontend-f1-findings — Tier F-1 frontend canon

> **Status:** `RESEARCH_FIRST`. Web verification 2026-05-11 for the `code` verb's
> frontend domain training corpus. Tier F-1 covers component frameworks +
> design systems + state management + type-safety.
> Cross-link: [`papers/coding-philosophy-sources.md`](./coding-philosophy-sources.md),
> [`docs/code-llm.md §STRUCT`](../docs/code-llm.md#struct--dataset).
> Convention: ★ = new find I didn't list. `UNVERIFIED` = could not confirm.
> Token estimates are order-of-magnitude (10K / 100K / 1M).

---

## Part 1 — Component framework landscape

| item | current canon (2026) | deprecated form | license | sources |
| --- | --- | --- | --- | --- |
| **React** | React 19.2 (Oct 2025) stable; **RSC + Server Functions + Actions** the canonical mutation path. **React Compiler 1.0** (Oct 7 2025) auto-memoizes; `useMemo`/`useCallback`/`React.memo` mostly unnecessary. `ref` as prop, `<Context>` (not `.Provider`), `use()` for promises/context, document metadata in components, `useActionState`/`useOptimistic`/`useFormStatus`, `<Activity>` for state preservation, `useEffectEvent` for non-reactive event logic, `cacheSignal` (RSC). | `forwardRef`, `useFormState`, `<Context.Provider>`, class components, lifecycle methods, manual `useMemo`/`useCallback`/`memo`, `componentDidMount`, HOCs (`withRouter`/`withRedux`). | MIT | [react.dev/blog/2024/12/05/react-19](https://react.dev/blog/2024/12/05/react-19), [react.dev/blog/2025/10/01/react-19-2](https://react.dev/blog/2025/10/01/react-19-2), [react.dev/blog/2025/10/07/react-compiler-1](https://react.dev/blog/2025/10/07/react-compiler-1) |
| **Vue 3** | **Composition API + `<script setup>`** is canon. Vue 3.6 (in beta Feb-Apr 2026, beta.9 ≈ feature-complete) ships **Vapor Mode** (no v-DOM, Solid-class perf) — Vapor only supports Composition API. Options API still supported but second-class for new code. | Options API for new full-scale apps; `Vue.extend`; mixins; filters; Vue 2 patterns. | MIT | [vueschool.io vue-3-6-vapor](https://vueschool.io/articles/news/vn-talk-evan-you-preview-of-vue-3-6-vapor-mode/), [vuejs.org/guide/extras/composition-api-faq](https://vuejs.org/guide/extras/composition-api-faq), [x.com/vuejs status/2003469481163784611](https://x.com/vuejs/status/2003469481163784611) |
| **Svelte 5** | **Runes** (Oct 2024 GA): `$state`, `$derived`, `$effect`, `$props`, `$bindable`, `$inspect`, `$host`. Works in `.svelte.ts`/`.svelte.js` → "**reactive class**" pattern replaces stores. Snippets replace slots. 91% retention (highest of FE frameworks, State of JS 2025). | `let x = ...` for reactive declarations, `$:` reactive statements, `export let` props, `<slot>`, writable/readable stores for in-app state. | MIT | [svelte.dev/blog/runes](https://svelte.dev/blog/runes), [svelte.dev/docs/svelte/v5-migration-guide](https://svelte.dev/docs/svelte/v5-migration-guide), [onehorizon.ai/blog/svelte-best-practices-in-2026](https://onehorizon.ai/blog/svelte-best-practices-in-2026-scaling-with-runes-snippets-and-pure-reactivity) |
| **Solid** | Solid 1.x stable; **Solid 2.0** experimental, **SolidStart 2.0 alpha**. Fine-grained reactivity, no v-DOM, signals/createMemo/createEffect/createResource canonical. Roughly 70% faster than React in standard benchmarks. | None internal to Solid (still pre-1.0 for SolidStart so meta-framework choices are mobile). React-style class lifecycle, manual diffing patterns. | MIT | [github.com/solidjs/solid/discussions/2425](https://github.com/solidjs/solid/discussions/2425), [docs.solidjs.com/advanced-concepts/fine-grained-reactivity](https://docs.solidjs.com/advanced-concepts/fine-grained-reactivity), [thenewstack.io/solidjs-creator-on-fine-grained-reactivity](https://thenewstack.io/solidjs-creator-on-fine-grained-reactivity-as-next-frontier/) |
| **Angular** | Angular 21+ — **Zoneless is default for new projects** (provideZonelessChangeDetection landed stable in 20.2, default in 21). **Signals stable in v20**. **`@if`/`@for`/`@switch` control flow**, **`@defer` deferred views**, **Signal Forms** (v21), **standalone components default**, **incremental hydration**. zone.js drop = −33 KB. | NgModules-by-default, `*ngIf`/`*ngFor`/`*ngSwitch`, `ChangeDetectionStrategy.Default` w/ Zone, RxJS-only state, `@Input()`/`@Output()` decorators when `input()`/`output()` signal-based equivalents apply. | MIT | [angular.dev/guide/zoneless](https://angular.dev/guide/zoneless), [medium.com/ng-guide/angular-20-stable-signals-zoneless](https://medium.com/ng-guide/angular-20-stable-signals-zoneless-and-more-68fbd094a521), [pkgpulse.com/guides/angular-21-zoneless](https://www.pkgpulse.com/guides/angular-21-zoneless-zone-js-performance-2026) |
| **Qwik** | **Resumability** (vs hydration): code runs on server, client "resumes" w/o re-executing. Qwik 2.0 cited as 15–20 KB initial bundle. **Adoption ≈ 2–5 %** of new projects — niche-perf/SEO, not mass market. | Hydration-style `useEffect` patterns, eager `mount` everything-on-load. | MIT | [qwik.dev/docs/faq/](https://qwik.dev/docs/faq/), [markaicode.com/qwik-resumable-apps-vs-react-server-components](https://markaicode.com/qwik-resumable-apps-vs-react-server-components/), [thenewstack.io javascript-on-demand-how-qwik-differs](https://thenewstack.io/javascript-on-demand-how-qwik-differs-from-react-hydration/) |
| **HTMX / Alpine / islands** | **HTMX + Alpine**: hypermedia-driven, server returns HTML fragments swapped by `hx-*` attrs; Alpine handles local UI toggles. **Preact/Astro/SolidJS islands** for the 5 % of components needing per-item state. Treated as production-tier in 2026, not experimental. | jQuery, full-SPA-by-default for content sites, custom XHR-then-innerHTML. | HTMX: BSD-2-Clause / 0BSD; Alpine: MIT | [htmx.org](https://htmx.org/), [vibe.forem.com/del_rosario/htmx-in-2026](https://vibe.forem.com/del_rosario/htmx-in-2026-why-hypermedia-is-dominating-the-modern-web-41id), [tschuehly.de preact-islands](https://tschuehly.de/preact-islands-in-spring-boot-with-htmx-when-alpinejs-isnt-enough-anymore) |
| ★ **Preact** | Preact + signals (`@preact/signals`) remains the lightweight React-API alternative for islands. | Mithril/Riot-style frameworks. | MIT | [preactjs.com](https://preactjs.com/) (general knowledge, link not re-fetched) |
| ★ **Lit / Web Components** | Lit + the TC39 Signals proposal preview (Lit Labs signals integration, Oct 2024). Useful when output must outlive a framework. | Polymer, custom-element class boilerplate without reactive props. | BSD-3-Clause | [lit.dev/blog/2024-10-08-signals](https://lit.dev/blog/2024-10-08-signals/) |

**Analysis — what to TEACH vs AVOID**

- **React**: Teach RSC mental model (server-by-default, opt-in `"use client"`), Server Actions for mutations, ref-as-prop, `use()`. **AVOID** teaching `forwardRef`, class components, manual memoization, HOC patterns, `componentWillMount`. The 2018-era React (Redux + `mapStateToProps` + class components) is **anti-canon**.
- **Vue**: Teach `<script setup>` + Composition API + Pinia. AVOID Options API in new full-scale code, mixins (use composables), filters (gone in 3.x).
- **Svelte**: Teach runes universally. AVOID `$:` reactive statements, `let` for reactive state, writable stores for app-local state (use a `.svelte.ts` class).
- **Solid**: Teach signals + `<Show>`/`<For>` JSX, `createResource` for async. SolidStart is still pre-1.0 (despite alpha 2.0), so mark "experimental" rather than canonical for the meta-framework.
- **Angular**: Teach signals, zoneless, `@if/@for/@switch`, standalone components, `input()`/`output()`, `@defer`. AVOID NgModules-by-default, structural directive prefix syntax, ZoneJS, RxJS for state when signals work.
- **Qwik**: Teach resumability conceptually; mark as **minority** framework — do not over-represent in corpus.
- **HTMX/Alpine**: Teach as a first-class alternative to SPA for content-heavy/server-rendered apps. The "server-rendered renaissance" is a real 2026 shift.

---

## Part 2 — Meta-framework consolidation

| item | current canon (2026) | deprecated form | license | sources |
| --- | --- | --- | --- | --- |
| **Next.js** | **App Router** stable + default; **Pages Router maintenance mode**. RSC by default, `"use client"` opt-in. **Server Actions** replace API routes for mutations. Parallel routes (`@folder`) + intercepting routes (`(.)`, `(..)`, `(...)`) for modal-with-URL UX. Next 16.x in 2026. | Pages Router for new apps, `getServerSideProps`/`getStaticProps`, `_app.tsx`/`_document.tsx`, custom API routes for simple mutations. | MIT | [nextjs.org/docs/app](https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes), [nextjs.org docs app intercepting-routes](https://nextjs.org/docs/app/api-reference/file-conventions/intercepting-routes), [dev.to ottoaria nextjs-app-router-2026](https://dev.to/ottoaria/nextjs-app-router-in-2026-the-complete-guide-for-full-stack-developers-5bjl) |
| **Nuxt 4** | **Stable** (one-year compat-mode beta). New `app/` directory layout; per-context `tsconfig.json`; auto-shared `useFetch`/`useAsyncData` per key. Nuxt 4.4 (Mar 2026): vue-router v5, accessibility announcer, build profiling. | Root-level `pages/`/`components/` layout, Nuxt 2 patterns in `@nuxt/kit`, single-tsconfig setup. | MIT | [nuxt.com/blog/v4](https://nuxt.com/blog/v4), [nuxt.com/blog/v4-4](https://nuxt.com/blog/v4-4) |
| **SvelteKit** | Stable since late 2022, paired with **Svelte 5 runes**. File-based routing, `+page.svelte`/`+page.server.ts`/`+layout.svelte`. Load functions + form actions are the canonical data path. | Pre-1.0 SvelteKit experimentation, store-based form state. | MIT | [kit.svelte.dev](https://kit.svelte.dev/), [github.com/sveltejs/kit/issues/13365](https://github.com/sveltejs/kit/issues/13365) |
| **React Router 7** (Remix merge) | **Remix v2 merged into React Router v7** ("Framework Mode"). Loaders, actions, nested routes, progressive enhancement — same Remix idioms now under RR7. Three modes: SPA / data router / full framework. | Standalone Remix v2 imports (`@remix-run/*` packages — replace with `react-router`), `react-router-dom` v5/v6 API for new apps. | MIT | [remix.run/blog/merging-remix-and-react-router](https://remix.run/blog/merging-remix-and-react-router), [remix.run/blog/react-router-v7](https://remix.run/blog/react-router-v7), [reactrouter.com/upgrading/remix](https://reactrouter.com/upgrading/remix) |
| **Astro 5** | **Server Islands** (`server:defer`) for personalized chunks inside cached pages. **Content Layer / Content Collections 2.0** w/ glob/file/remote loaders, Zod schemas, full TS. Islands-by-default; zero-JS unless opted-in. Builds 5× faster (Markdown), 2× faster (MDX). | Pre-5 collections API, eager-hydrate-everything, custom integrations replicating what content layer now does natively. | MIT | [astro.build/blog/astro-5/](https://astro.build/blog/astro-5/), [docs.astro.build/en/guides/server-islands/](https://docs.astro.build/en/guides/server-islands/) |
| **TanStack Start** | **v1 Release Candidate** (extended beta → 1.0 imminent / shipped per some sources). Built on TanStack Router + Vite + Nitro. Philosophy: "just React" — no RSC, no compiler magic, no `"use client"`. Server functions + SSR streaming. | RSC-style mental model when using Start (it explicitly rejects it). | MIT | [tanstack.com/start/latest](https://tanstack.com/start/latest), [tanstack.com/blog/announcing-tanstack-start-v1](https://tanstack.com/blog/announcing-tanstack-start-v1) |
| **Qwik City** | Stable on top of Qwik 2.0. File-based routing + resumable loaders/actions. Minority adoption. | Hydration-style frameworks built atop Qwik. | MIT | [qwik.dev/docs/qwikcity/](https://qwik.dev/docs/qwikcity/) |
| **SolidStart** | **Pre-1.0 / 2.0-alpha in 2026.** Server functions, file-based routing, fine-grained reactivity SSR. Production-ready but smaller ecosystem. | None internal; just temper claims about maturity. | MIT | [start.solidjs.com](https://start.solidjs.com/), [docs.solidjs.com/solid-start](https://docs.solidjs.com/solid-start) |

**Analysis**

- **Canon for new React app in 2026**: Next.js App Router (server-heavy, RSC) **or** React Router 7 Framework Mode (client-first, loader/action) **or** TanStack Start (no-RSC, type-safe). Three legitimate stacks, not one.
- **Canon for content sites**: Astro 5 with island components from any framework.
- **Canon for Vue**: Nuxt 4.
- **Canon for Svelte**: SvelteKit + Svelte 5 runes.
- **AVOID teaching**: standalone Remix imports (now React Router), Pages Router for new code, `getServerSideProps`, single-tsconfig Nuxt layouts.

---

## Part 3 — Design system philosophy

| item | current canon (2026) | deprecated form | license | sources |
| --- | --- | --- | --- | --- |
| **shadcn/ui** | **The default for new React projects.** Copy-paste source model (no npm dep for components). 75 K+ GitHub stars. **As of Feb 2026 supports both Radix and Base UI as primitive layers.** Visual Builder (Feb 2026) reduces setup friction. | Heavy npm-dep component libraries when customization needed (MUI/Chakra for net-new projects where you don't need their batteries). | MIT | [ui.shadcn.com](https://ui.shadcn.com/), [pkgpulse.com/guides/shadcn-ui-vs-base-ui-vs-radix](https://www.pkgpulse.com/guides/shadcn-ui-vs-base-ui-vs-radix-components-2026), [shadcnstudio.com/blog/radix-ui-vs-shadcn-ui](https://shadcnstudio.com/blog/radix-ui-vs-shadcn-ui) |
| **Radix UI** | Headless primitives; `@radix-ui/react-slot` alone at ~131 M weekly downloads in mid-2026. Acquired by WorkOS, development pace slowed. Still the most-deployed primitive set. | Bootstrap/Bulma-style "looks-baked-in" libraries for design-system-grade UI. | MIT | [radix-ui.com](https://www.radix-ui.com/), [blog.logrocket.com/headless-ui-alternatives/](https://blog.logrocket.com/headless-ui-alternatives/) |
| **Base UI** | MUI team's headless successor; **v1 released Feb 2026** with 35 accessible components. Addresses Radix architectural gaps. shadcn supports as alt primitive. | Legacy unstyled-MUI / `@mui/base` pre-v1. | MIT | [infoq.com/news/2026/02/baseui-v1-accessible](https://www.infoq.com/news/2026/02/baseui-v1-accessible/) |
| **React Aria Components** | Adobe's hook + component lib, deepest a11y + i18n primitives (30+ locales, RTL, calendars). 50+ components. Chosen when accessibility is non-negotiable. | Manual ARIA wiring; React Spectrum's older non-Aria pieces. | Apache-2.0 | [react-spectrum.adobe.com/react-aria/](https://react-spectrum.adobe.com/react-aria/index.html), [react-aria.adobe.com](https://react-aria.adobe.com/) |
| ★ **Ark UI** | Chakra team's cross-framework (React / Vue / Solid) primitives — same machine driving each. Pairs with **Park UI** for styling. | One-framework-only headless kits when cross-framework parity matters. | MIT | [ark-ui.com](https://ark-ui.com/) (general knowledge — link not re-fetched) |
| **Material Design 3 (M3 Expressive)** | Google's 2025-26 update — spring motion, 35 morphing shapes, heavier type, background-blur depth. Backed by 46 studies / 18 K participants. | Flat-minimal Material 2 patterns, ripple-only motion model. | Apache-2.0 (Material guidelines) | [zoewave.medium.com material-3-design-system](https://zoewave.medium.com/material-3-design-system-e91a15d303a0), [9to5google.com/2025/12/27/recap-material-3-expressive](https://9to5google.com/2025/12/27/recap-material-3-expressive/) |
| **Apple HIG (Liquid Glass)** | **Liquid Glass** (mid-2025) — translucent refractive material across iOS/iPadOS/macOS/visionOS/watchOS/tvOS. Spatial computing guidance, Control Center extensions, widget reform, AI integrations. | iOS 7-era flat aesthetic as a forward-looking default. | Proprietary (Apple Developer license — non-redistributable text; reference only) | [developer.apple.com/design/human-interface-guidelines/materials](https://developer.apple.com/design/human-interface-guidelines/materials), [moqups.com/blog/ios-26-material-design-3-ui-kits](https://moqups.com/blog/ios-26-material-design-3-ui-kits/) |
| **Tailwind v4** | **v4.0 GA Jan 22 2025, v4.1 Apr 2025.** Rust "Oxide" engine (3.8× full / 8.8× incremental / 182× zero-change). **CSS-first config** via `@theme`; **OKLCH** default palette; container queries built-in; cascade layers, `@property`, `color-mix()`, 3D transforms, `@starting-style`, `not-*` variant. Single `@import "tailwindcss"`. | `tailwind.config.js`, `@tailwind base/components/utilities`, `@tailwindcss/container-queries` plugin, `bg-gradient-*` (now `bg-linear-*`), sRGB-only palette. | MIT | [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4) |
| **CVA + cn (clsx + tailwind-merge)** | Idiomatic variant API for Tailwind components: `cva()` for variant matrix, `cn()` helper to merge conditional classes safely. Standard in shadcn-derived codebases. | Hand-written `template literal` class strings, ad-hoc class concat with conflicts. | CVA: Apache-2.0; clsx: MIT; tailwind-merge: MIT | [cva.style/docs](https://cva.style/docs), [dev.to whoffagents tailwind-css-patterns-that-actually-scale](https://dev.to/whoffagents/tailwind-css-patterns-that-actually-scale-cva-cn-and-design-tokens-3cbo) |
| **CSS-in-JS (runtime)** | **On life support for new projects.** styled-components / Emotion legacy-only. Runtime injection is bad for RSC, adds KB, blocks render. | styled-components/Emotion in new code, runtime `css` prop frameworks for greenfield. | MIT | [pkgpulse.com/blog/state-of-css-in-js-2026](https://www.pkgpulse.com/blog/state-of-css-in-js-2026) |
| **Panda CSS** (zero-runtime CSS-in-TS) | Build-time CSS-in-JS, RSC-compatible, variant-first, type-safe. Pairs well with shadcn primitives if you need design-token DSL > Tailwind utilities. | Runtime CSS-in-JS for the same use case. | MIT | [panda-css.com](https://panda-css.com/docs/overview/why-panda) |
| **vanilla-extract** | Zero-runtime stylesheets-in-TS — fully typed CSS as TS. Build-time. | Runtime styled-components for design systems. | MIT | [vanilla-extract.style](https://vanilla-extract.style/) |
| ★ **StyleX** (Meta) | Atomic CSS-in-JS, zero runtime, dedupe; production at Meta. Niche but credible. | Same runtime-CSS-in-JS legacy. | MIT | [stylexjs.com](https://stylexjs.com/) (general knowledge — link not re-fetched) |
| **Pigment CSS** | MUI's zero-runtime CSS-in-JS to replace Emotion in MUI v6+. **Status: still pre-stable / niche-adoption in 2026** (`UNVERIFIED` for v1). | Emotion-backed MUI styling for performance-sensitive new code. | MIT | [github.com/mui/material-ui issues/38137](https://github.com/mui/material-ui/issues/38137), [github.com/mui/material-ui issues/34826](https://github.com/mui/material-ui/issues/34826) |

**Analysis**

- **2026 dominant paradigm**: Tailwind v4 + shadcn/ui (Radix or Base UI underneath) + CVA + cn(). This stack covers ≈ the majority of net-new React app design systems.
- **Server-component-safe**: Tailwind v4 and zero-runtime CSS-in-JS (Panda, vanilla-extract, Pigment, StyleX) work with RSC. **Runtime CSS-in-JS does not.** This is the load-bearing reason styled-components is being retired.
- **Headless layers**: Radix is still default, Base UI is rising, React Aria for a11y-critical, Ark UI for cross-framework. Teach the **headless / styled-by-consumer** philosophy — not heavy-styled component kits.
- **AVOID teaching**: styled-components for new React app, `tailwind.config.js`-as-canon (it works in v4 via JS shim but `@theme` is canon), separate container-queries plugin, hand-written class-concat.

---

## Part 4 — State management current canon

| item | current canon (2026) | deprecated form | license | sources |
| --- | --- | --- | --- | --- |
| **Signals (cross-framework)** | Native primitive in **Solid, Vue (ref), Svelte 5 (`$state`), Angular (signal), Preact (`@preact/signals`)**. **TC39 proposal at Stage 1** w/ design input from Angular, Ember, MobX, Preact, Qwik, RxJS, Solid, Svelte, Vue, Wiz authors. React notably **not native** — relies on hooks + Compiler. | Observable-pattern boilerplate, RxJS-only state where signals suffice. | per-framework MIT/Apache-2.0; TC39 spec CC-BY | [github.com/tc39/proposal-signals](https://github.com/tc39/proposal-signals), [lit.dev/blog/2024-10-08-signals](https://lit.dev/blog/2024-10-08-signals/) |
| **TanStack Query** | **Default for server state in React/Solid/Vue/Svelte/Angular adapters.** ~5 M weekly downloads. Cache + refetch + loading/error + optimistic + infinite + suspense. Universally paired with a separate client-state lib. | Hand-rolled `useEffect(() => fetch(...))` for remote data; storing server data in Redux; SWR for net-new (TanStack Query has overtaken). | MIT | [pkgpulse.com/blog/state-of-react-state-management-2026](https://www.pkgpulse.com/blog/state-of-react-state-management-2026) |
| **Zustand** | **Default client UI state for new React projects.** ~4 M weekly downloads, ~40 % of new projects, 30 % YoY growth. Tiny API, hook-based, no provider. | Redux (vanilla) for new app-local state; Context-based-global-state-from-scratch; `useReducer`+Context megastores. | MIT | [pkgpulse.com/blog/state-of-react-state-management-2026](https://www.pkgpulse.com/blog/state-of-react-state-management-2026), [betterstack.com/community/guides/scaling-nodejs/zustand-vs-redux-toolkit-vs-jotai](https://betterstack.com/community/guides/scaling-nodejs/zustand-vs-redux-toolkit-vs-jotai/) |
| **Jotai** | Atomic state — derived/computed state graphs, async atoms. ~2 M weekly. Chosen when state-shape is genuinely atomic/graph-like. | Redux selectors for fundamentally atomic state; Context+useReducer for derived chains. | MIT | [pkgpulse.com state-of-react-state-management-2026](https://www.pkgpulse.com/blog/state-of-react-state-management-2026) |
| **Redux Toolkit** | ~4 M weekly. Still recommended **for large enterprise apps** with complex global state needing devtools, middleware, time-travel. **Rarely chosen for new projects in 2026.** Hand-written Redux down to ~10 % of new projects. | Hand-written Redux boilerplate (`mapStateToProps`, `connect`, plain `createStore`), `redux-thunk` without RTK. | MIT | [medium.com mernstackdev state-management-2026](https://medium.com/@mernstackdevbykevin/state-management-in-2026-what-comes-after-redux-34576682c68e) |
| **React Hook Form** | **Default for forms in 2026.** Uncontrolled (refs), minimum re-renders, perfect for high-perf dashboards. | Controlled inputs everywhere with custom validation hooks; Formik for new code. | MIT | [react-hook-form.com](https://react-hook-form.com/) |
| **TanStack Form** | Headless, framework-agnostic (React/Solid/Vue/Lit/Angular), first-class TS, per-validator triggers, async-validation as first-class. Pick over RHF when you want type safety + reusable form pieces across frameworks. | Single-framework form libs when type-safety + cross-framework matters. | MIT | [tanstack.com/form/latest](https://tanstack.com/form/latest), [formisch.dev/blog/react-form-library-comparison/](https://formisch.dev/blog/react-form-library-comparison/) |
| **vee-validate** (Vue) | Idiomatic Vue forms — schema-driven, composable, plays w/ Zod/Valibot. | Hand-rolled `v-model`+watchers validation for non-trivial forms. | MIT | [vee-validate.logaretm.com](https://vee-validate.logaretm.com/) (general knowledge — link not re-fetched) |
| **nuqs** | **Type-safe URL state** for Next.js (app+pages) / React-SPA / Remix / React Router / TanStack Router. `useState`-like API stored in `?q=...`. 6 KB. | Manual `URLSearchParams` plumbing; storing nav-state in Redux/Zustand instead of URL. | MIT | [nuqs.dev](https://nuqs.dev/), [github.com/47ng/nuqs](https://github.com/47ng/nuqs) |
| **TanStack Router search params** | First-class **typed search params** w/ Zod schemas — search params *are* state. Built into TanStack Router/Start. | Untyped string parsing, `qs` lib without schema, route state divorced from URL. | MIT | [tanstack.com/blog/search-params-are-state](https://tanstack.com/blog/search-params-are-state) |

**Analysis**

- **2026 default React stack**: TanStack Query (server) + Zustand (client UI) + React Hook Form (forms) + nuqs (URL). Most apps need nothing else.
- **Signals are the cross-framework story**: every non-React major framework is signals-native; React stays special with Compiler + hooks. The TC39 proposal points at a future where signals are runtime-free across frameworks. Teach signals as a **paradigm**, not a library.
- **Redux Toolkit is enterprise-legacy canon, not new-project canon**. Teach it as "you'll see this in big codebases" — don't teach it as the first answer for a greenfield app.
- **AVOID teaching**: `mapStateToProps`/`connect`, hand-written Redux boilerplate, Formik for new apps, untyped URL string fiddling, storing server data in client store.

---

## Part 5 — Type-safety philosophy

| item | current canon (2026) | deprecated form | license | sources |
| --- | --- | --- | --- | --- |
| **tRPC** | **Champion for dedicated type-safe API layers.** ~35 K GitHub stars. End-to-end TS types **without codegen**, batching, integrates w/ TanStack Query. Used for SaaS dashboards, multi-client (web+mobile). | Untyped `fetch` + manual response typing; OpenAPI codegen as the type-safety strategy for greenfield TS apps. | MIT | [trpc.io](https://trpc.io/), [medium.com factman60 next-js-server-actions-vs-trpc-2026](https://medium.com/@factman60/next-js-server-actions-vs-trpc-a-2026-architects-guide-85cc4953bae4) |
| **Server Actions (Next/React)** | Default for **form-heavy, content, e-commerce** Next.js apps. Progressive enhancement, deep RSC integration. | API routes for simple mutations in App Router apps. | MIT | [react.dev/blog/2024/12/05/react-19](https://react.dev/blog/2024/12/05/react-19) |
| **Hono RPC** | Lightest end-to-end-typed option. `hc<typeof app>(url)` typed client from Hono routes. Native Cloudflare Workers. Trending up. | Express-ish APIs with manual types when running on Workers/edge. | MIT | [hono.dev/docs/guides/rpc](https://hono.dev/docs/guides/rpc) |
| ★ **oRPC** | Newer entrant — OpenAPI-spec output + tRPC-style ergonomics. Bridges REST and typed-RPC worlds. | tRPC when you also need to publish an OpenAPI spec. | MIT | [pkgpulse.com/blog/orpc-vs-trpc-vs-hono-rpc-type-safe-apis-2026](https://www.pkgpulse.com/blog/orpc-vs-trpc-vs-hono-rpc-type-safe-apis-2026) |
| **Zod** | **The default validation lib.** Zod 4 stable. Method-chain DSL, parseAsync, transforms, refinements. Pairs with everything (tRPC, React Hook Form, Astro content collections, nuqs, TanStack Router). | `joi` for new TS code; hand-written `typeof x === ...` validation for API boundaries. | MIT | [zod.dev](https://zod.dev/), [pkgpulse.com/guides/zod-vs-arktype-2026](https://www.pkgpulse.com/guides/zod-vs-arktype-2026) |
| **Valibot** | **Bundle-size champion** — 8.7 KB full / 1.4 KB tree-shaken (vs Zod 14 KB). Tree-shakeable function-based API. Default for frontend / edge where every KB matters. | Zod in a tight-budget client bundle when Valibot covers the same shape. | MIT | [valibot.dev/guides/comparison/](https://valibot.dev/guides/comparison/) |
| **ArkType** | **Performance champion** — 3–4× faster than Zod (1.7× vs Zod 4 in 1 M iter). TypeScript-syntax-literal DSL (e.g. `"string|number"`). Heavier bundle (~42 KB). | Zod when perf is the binding constraint. | MIT | [arktype.io](https://arktype.io/), [pkgpulse.com/guides/zod-vs-arktype-2026](https://www.pkgpulse.com/guides/zod-vs-arktype-2026) |
| **TypeScript-first runtimes** | **Bun**: in-process TS via own bundler, all TS features incl. enums/decorators. **Deno 2**: native TS + type-check + format. **Node 22+**: `--experimental-strip-types` (becoming default-on in 23+); strips annotations only — no enums/namespaces/decorators. | `tsc` → run-`node dist/` build steps for app code in 2026; `ts-node` for greenfield. | Bun: MIT; Deno: MIT; Node: MIT | [dev.to dataformathub nodejs-vs-deno-vs-bun-2026](https://dev.to/dataformathub/nodejs-vs-deno-vs-bun-the-ultimate-runtime-guide-for-2026-di), [dayzero.live native-typescript-node-deno-bun-comparison-2026](https://www.dayzero.live/web-development/native-typescript-node-deno-bun-comparison-2026) |
| **JSDoc-as-TS** | Adopted by library authors (Svelte switched in 2024) to ship typed source without a build step. Good for libs that must run as ESM `.js` directly. | Bundled-only `.d.ts` shipping when a JSDoc-typed `.js` works; pure-JS libs with no types in 2026. | per-project | [alexharri.com/blog/jsdoc-as-an-alternative-typescript-syntax](https://alexharri.com/blog/jsdoc-as-an-alternative-typescript-syntax), [luhr.co/blog/2024/01/25/build-free-type-annotations-with-jsdoc-and-typescript](https://luhr.co/blog/2024/01/25/build-free-type-annotations-with-jsdoc-and-typescript/) |
| ★ **TSDoc** | Microsoft's TS-specific successor to JSDoc syntax; adopted by API Extractor, ESLint plugins. | Free-form JSDoc tags in libraries that need stable cross-tooling. | MIT | [tsdoc.org](https://tsdoc.org/) |

**Analysis**

- **2026 mutation-path decision tree**: Next.js + form-heavy → **Server Actions**. SaaS / multi-client / heavy dashboard → **tRPC**. Edge / Workers → **Hono RPC** (or oRPC if OpenAPI needed).
- **Validation lib decision tree**: default → **Zod**; bundle-constrained → **Valibot**; perf-critical → **ArkType**. Teach Zod first.
- **Runtime canon shifting**: TypeScript-as-source-of-truth, runtimes execute it directly. Bun has the most complete native TS; Deno 2 a close second; Node is catching up but limited. **AVOID** teaching `tsc` build steps for app code as default.
- **JSDoc-as-TS** is a library-author concern, not application-developer. Teach for library/SDK authoring sections, not app sections.

---

## Anti-canon (do not teach)

A consolidated filter list — patterns the model must **not** propose as best-practice in 2026. Each pairs with a Tier-A idiomatic positive.

### React anti-canon
- Class components (`class Foo extends React.Component`) for new code.
- Lifecycle methods (`componentDidMount`, `componentWillReceiveProps`, `shouldComponentUpdate`).
- `forwardRef` → use `ref` as a prop.
- `useFormState` → use `useActionState`.
- `<Context.Provider>` → use `<Context>` directly.
- Manual `useMemo`/`useCallback`/`React.memo` to fix renders → use React Compiler.
- HOCs: `withRouter`, `withRedux`, `connect()`, `compose()`.
- `mapStateToProps`/`mapDispatchToProps`.
- `componentWillMount`, `UNSAFE_*` lifecycles.
- Function components without TS in greenfield code.
- `defaultProps` on function components — use destructuring defaults.
- PropTypes — use TypeScript.
- API routes for simple mutations in App Router → Server Actions.
- Pages Router for new Next.js apps.

### Vue anti-canon
- Options API for new full-scale apps (still legal, not canonical).
- Mixins → composables.
- Filters (gone in v3 anyway).
- Vue 2 lifecycle names (`beforeDestroy` etc.).
- `Vuex` for new code → Pinia.

### Svelte anti-canon
- `$:` reactive statements → `$derived` / `$effect`.
- `let count = 0` for reactive component state → `let count = $state(0)`.
- `export let foo` → `let { foo } = $props()`.
- `<slot>` → snippets.
- Writable stores for app-local state → reactive class in `.svelte.ts`.

### Angular anti-canon
- NgModules-by-default → standalone components.
- `*ngIf`/`*ngFor`/`*ngSwitch` → `@if`/`@for`/`@switch`.
- `ChangeDetectionStrategy.Default` w/ Zone in performance-sensitive new code.
- ZoneJS for new v21+ apps.
- `@Input()`/`@Output()` decorators where `input()`/`output()` signal APIs apply.
- RxJS-only state when signals suffice.

### Tailwind anti-canon
- `tailwind.config.js` as the source of truth for tokens → `@theme` in CSS.
- `@tailwind base;` / `@tailwind components;` / `@tailwind utilities;` → `@import "tailwindcss";`.
- `@tailwindcss/container-queries` plugin → built-in `@container`.
- `bg-gradient-to-r` → `bg-linear-to-r`.
- sRGB hex palette as the default → OKLCH.

### State / data anti-canon
- Redux + `connect` HOC for new apps → Zustand/Jotai or RTK with hooks.
- Hand-written Redux without RTK.
- Storing server data in Redux/Zustand → TanStack Query.
- `useEffect(() => fetch(...))` for remote data.
- SWR for greenfield (acceptable, but TanStack Query has overtaken).
- Formik for new code → React Hook Form / TanStack Form.
- Manual `URLSearchParams` for nav state → nuqs / TanStack Router search params.

### CSS anti-canon
- styled-components / Emotion for new React app (esp. with RSC).
- Runtime CSS-in-JS in any RSC context.
- Hand-concatenated Tailwind class strings → CVA + cn().
- Sass `@import` for design tokens when CSS custom props + `@theme` exist.

### Type-safety anti-canon
- `any` for "I'll type this later".
- `joi` validation in new TS code → Zod/Valibot/ArkType.
- OpenAPI codegen as the primary type-safety story in a fully-TS stack → tRPC / Hono RPC.
- Manual response typing on `fetch` calls in a typed-RPC stack.
- `tsc` → `node dist/` build steps as default for app code → Bun/Deno/Node-strip-types.

### Misc anti-canon
- jQuery for new apps.
- Standalone Remix (`@remix-run/*`) imports for new code → React Router v7.
- SWR2 for greenfield (legacy of choice; not wrong, just not canon).
- HOC libraries in general — composition over HOCs.
- `Function` / `Object` / `{}` types in TS (use precise shapes).
- Premature SPA-by-default for content sites → Astro/HTMX/Server Components.

---

## Token estimate

Per canonical source, order-of-magnitude. Method: word-count of canonical docs × ~1.3 tok/word, or known repo guide lengths.

| source | tokens (est.) | method |
| --- | --- | --- |
| React docs (react.dev) — Learn + Reference + Blog | ~500K | major framework docs, ~400K-600K range |
| Vue 3 docs (vuejs.org) — Guide + API + Examples | ~300K | mid-size framework docs |
| Svelte 5 docs (svelte.dev) + Runes blog + Migration guide | ~150K | younger framework, dense |
| SolidJS docs (docs.solidjs.com) + SolidStart docs | ~80K | small but rich |
| Angular docs (angular.dev) — Guide + Reference | ~600K | large + reference-heavy |
| Qwik docs (qwik.dev) | ~80K | comparable to Solid |
| HTMX docs (htmx.org) + Hypermedia book chapters | ~50K | small + opinionated |
| Alpine.js docs | ~15K | tiny |
| Next.js docs (nextjs.org/docs) | ~400K | extensive App Router docs |
| Nuxt docs (nuxt.com/docs) | ~250K | comparable |
| SvelteKit docs (kit.svelte.dev) | ~100K | mid |
| Astro docs (docs.astro.build) | ~250K | strong content-layer / islands docs |
| React Router v7 docs (reactrouter.com) | ~120K | merged + tutorial |
| TanStack docs (Query + Router + Form + Start) | ~300K | combined |
| TC39 signals proposal README + Stage docs | ~10K | small |
| Tailwind v4 docs (tailwindcss.com) | ~120K | large utility ref |
| shadcn/ui docs (ui.shadcn.com) | ~30K | mostly component snippets |
| Radix UI docs (radix-ui.com) | ~80K | per-primitive |
| Base UI docs (mui.com/base-ui) | ~50K | newer + smaller |
| React Aria docs (react-spectrum.adobe.com) | ~120K | hook + component cross-ref |
| Material Design 3 (m3.material.io) | ~200K | extensive guidelines + components |
| Apple HIG (developer.apple.com/design/human-interface-guidelines) | ~250K | platform-wide reference — **read-only** |
| Panda CSS docs (panda-css.com) | ~40K | mid |
| vanilla-extract docs | ~20K | small |
| Zod docs (zod.dev) | ~25K | concise |
| Valibot docs (valibot.dev) | ~25K | concise |
| ArkType docs (arktype.io) | ~30K | concise |
| tRPC docs (trpc.io) | ~40K | mid |
| Hono docs (hono.dev) | ~80K | broader (runtime + RPC) |
| nuqs docs (nuqs.dev) | ~10K | small |
| TanStack Query docs (subset of TanStack above; standalone ~80K) | ~80K | counted in TanStack total |
| Zustand docs / README | ~15K | tiny |
| Jotai docs | ~25K | mid |
| Redux Toolkit docs (redux-toolkit.js.org) | ~80K | mid + tutorial |
| React Hook Form docs (react-hook-form.com) | ~30K | mid |
| TanStack Form docs | ~40K | mid |
| **Estimated grand-total canonical FE corpus** | **~4–5M tokens** (rough sum) | budget plan-able against `code-llm.md` SCALE |

Numbers are order-of-magnitude; final extraction will set exact counts.

---

## License gate notes

The frontend ecosystem is **overwhelmingly MIT / Apache-2.0** and safe for verbatim quotation with attribution. Flagged exceptions:

| source | license | concern | mitigation |
| --- | --- | --- | --- |
| **Apple Human Interface Guidelines** | Apple Developer license (proprietary) | **NOT redistributable** — even fair use of text is risky; Apple aggressively enforces. | **Reference-only**: teach concepts ("blur-as-depth", "Liquid Glass"), describe pillars in our own words; do not bulk-quote the docs into the corpus. Cite by URL. |
| **Material Design 3 (m3.material.io)** | Apache-2.0 (per Google's design docs licensing) | Some assets / icon fonts have separate license terms (icons Apache-2.0). | Quote text under Apache-2.0 (attribution + license notice); do not bundle icon binaries. |
| **shadcn/ui** | MIT | Component code is copy-paste-by-design — license follows codebase. | Standard MIT attribution. |
| **Class Variance Authority (CVA)** | Apache-2.0 (per repo) | Standard Apache attribution. | Include `NOTICE` if shipping bundled. |
| **React Aria (Adobe)** | Apache-2.0 | Standard Apache attribution. | Include `NOTICE` if shipping bundled. |
| **HTMX** | BSD-2-Clause / 0BSD (per htmx.org/repo) | Permissive — attribution sufficient. | Standard BSD notice. |
| **Tailwind / Vue / React / Svelte / Solid / Angular / Astro / Next / Nuxt / TanStack / Radix / Base UI / Zod / Valibot / ArkType / Zustand / Jotai / RTK / RHF / nuqs / Panda / vanilla-extract / Hono / tRPC** | **MIT** | None — safe to quote with attribution. | Standard MIT notice. |
| **TC39 proposal-signals README** | CC-BY (TC39 default for proposals) | Attribution required. | Cite TC39 + commit hash. |

**Net**: only Apple HIG is a hard blocker for bulk inclusion. Everything else is corpus-friendly with attribution. Maintain a `LICENSES.md` manifest mapping each ingested document to its license + attribution string, identical to how Tier A handles PSF v2 / CC-BY rows.

---

### Notes & UNVERIFIED items

- **Pigment CSS** — multiple 2024 / early-2026 MUI issues confirm intent, but I did not find a clear v1 stable announcement; treating as `UNVERIFIED` for stable status.
- **TanStack Start v1.0** — sources disagree: one says "shipped early 2025", another says "v1 RC in 2026". Treating as "RC / very-near-stable" — verify against the actual `package.json` version when ingesting.
- **Solid 2.0 / SolidStart 2.0** — confirmed in active alpha; not yet stable.
- **Vue 3.6 Vapor Mode** — confirmed in beta.9 as of Apr 2026; **not yet stable**. Teach as "upcoming canon" rather than "current canon" until 3.6 ships GA.
- **Ark UI specific version numbers / weekly downloads** — `UNVERIFIED`; general framework-agnostic status is well-established.
- **React Compiler default-on status in major frameworks** — confirmed 1.0 stable; Next.js `reactCompiler` config flag landed, but defaulting behavior per framework varies (`UNVERIFIED` for "default-on everywhere").
