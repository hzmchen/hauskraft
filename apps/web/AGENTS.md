<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# AGENTS.md: web shell (`apps/web`)

Local rules on top of the [root AGENTS.md](../../AGENTS.md). Contract: [E08](../../docs/backlog/m0-star/E08-web-shell-and-dashboard.md), [E13](../../docs/backlog/m0-star/E13-theming-system.md) and [docs/testing/ui-contract.md](../../docs/testing/ui-contract.md).

- **AGPL.** Plugins never import from here; shared UI goes into `@hearthos/ui` (MIT), shared types into `@hearthos/sdk-ts`.
- **Data:** TanStack Query with the generated options and mutations from `@hearthos/sdk-ts` only. No ad-hoc `fetch`. The CSRF token stays in memory.
- **Never edit generated files:** `src/routeTree.gen.ts` (TanStack Router plugin), `src/plugins/registry.gen.ts` (`just gen`).
- **Navigation:** every renderer (sidebar, topbar, drawer, bottom tabs) consumes the one `NavModel`. Renderers may change presentation only, never items, order, labels or icons.
- **Themes change presentation, never function.** Read theme variants from `data-hearth-*` attributes and CSS variables; never branch on `theme_id` in code. The accessibility tree of every view must be identical in every theme (the invariance suite fails otherwise).
- **Colour mode** (system/light/dark) lives only in this browser (`localStorage("hearthos.mode")`, wrapped in try/catch) and is never sent to the server.
- **No raw styles:** no colour literals, Tailwind palette classes, arbitrary values or inline colour/font/spacing styles (`hearthos/no-raw-styles`).
- **i18n:** every user-facing string is a key in `src/i18n/locales/{en,de}/shell.json`; the key-parity test fails if the two differ. Theme names are shown as the theme provides them.
- **Accessible names and test hooks** come from [docs/testing/ui-contract.md](../../docs/testing/ui-contract.md); the spec-owned Playwright tests depend on them.
