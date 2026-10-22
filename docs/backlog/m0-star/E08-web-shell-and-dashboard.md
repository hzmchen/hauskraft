# E08 · Web shell & dashboard

**Goal:** A React 19 shell with login, navigation model, per-device colour mode, i18n, a Today grid and plugin page routing.
**Out of scope:** PWA, kiosk mode, offline. Theme loading and the non-default navigation styles are in E13.
**Dependencies:** E01, E03-05, E06-05/06.
**UI contract:** the accessible names and test hooks in `docs/testing/ui-contract.md` are part of every UI story's AC; the spec-owned e2e tests in `tests/e2e/` rely on them.

---

## M0S-E08-01 · Vite + React + TanStack scaffold and `@hauskraft/ui` package
- **Story:** As a frontend agent, I want the shell and a shared UI package scaffolded with the chosen stack, so that features and plugins drop into known places.
- **AC:**
  - Given `apps/web`, when I run `pnpm --filter web dev`, then Vite 8 serves the shell with TanStack Router file-based routing (`@tanstack/router-plugin/vite` placed before `@vitejs/plugin-react`, `autoCodeSplitting: true`, generated `routeTree.gen.ts` committed), a QueryClient provider and Tailwind 4 via `@tailwindcss/vite`.
  - `packages/ui` (`@hauskraft/ui`, MIT) is initialised with shadcn/ui on Radix (`components.json` points into `packages/ui/src/components`) and contains `button, input, checkbox, card, dialog, dropdown-menu, popover, calendar, sonner, tabs, sheet`. `apps/web` and plugin web packages import components only from `@hauskraft/ui`.
  - Components reference only CSS variables (shadcn's variable names); no colour literals. Token wiring and variants come in E13-02.
- **Tech:** React `^19.3`, `@tanstack/react-router@1.170.x`, `@tanstack/react-query@5.104.x`. Vitest 4 jsdom project for units plus a `browser` project via `@vitest/browser-playwright`. A temporary `packages/ui/src/tokens/fallback.css` holds the default theme's values until E13-03 serves compiled themes.
- **Tests:** Vitest render smoke test of the shell and one `@hauskraft/ui` component.
- **Deps:** E01-03 · **Est:** M · **Labels:** area:web

## M0S-E08-02 · Colour mode per device (system, light, dark)
- **Story:** As an adult household member, I want each device to choose system, light or dark mode, so that the kitchen tablet can go dark at night while my phone stays light, all in the same household theme.
- **AC:**
  - Given the mode control in Settings → Appearance and in the user menu, when I pick Dark, then the `.dark` class is set on `<html>` and the choice persists in `localStorage("hauskraft.mode")` on this device only. Other devices are unaffected.
  - `system` (default) follows `prefers-color-scheme` and reacts live to OS changes.
  - The mode is applied before first paint by an inline script in `index.html` (no light flash on a dark device). The script's SHA-256 hash is documented for the CSP in E11-01.
  - If `localStorage` is unavailable (private mode), the control still works for the session and falls back to `system` on reload.
  - Mode never changes the deployment theme and is never sent to the server.
- **Tech:** `shell/ColorMode.tsx`, `index.html` inline script (≤ 1 KB). All `localStorage` access in try/catch.
- **Tests:** Vitest: toggle, persistence, system listener, storage failure. Playwright: two browser contexts keep independent modes (used by demo step 9).
- **Deps:** E08-01 · **Est:** S · **Labels:** area:web, theme, a11y

## M0S-E08-03 · Login page and auth guard
- **Story:** As an adult household member, I want a login screen and protected routes, so that only household members see the dashboard.
- **AC:**
  - Given no session, visiting `/today` redirects to `/login?redirect=/today`.
  - Correct credentials navigate to `redirect`. A wrong password shows a localised error without revealing which field was wrong.
  - Logout in the user menu clears the query cache and returns to `/login`.
  - The login page uses the active deployment theme (it is public CSS, no data).
- **Tech:** `routes/login.tsx`; `routes/_app.tsx` with `beforeLoad` calling `ensureQueryData(sessionQuery)`. CSRF token kept in memory from the `Session`.
- **Tests:** Vitest: guard logic; Playwright: login/logout.
- **Deps:** E08-01, E05-03, E06-05 · **Est:** M · **Labels:** area:web, auth

## M0S-E08-04 · i18n groundwork (en, de)
- **Story:** As a German-speaking household member, I want the UI in Deutsch, so that everyone at home can use it.
- **AC:**
  - Given the language switcher, when I choose Deutsch, then all shell and plugin strings switch and the choice is saved via `PATCH /me {locale}` and in `localStorage`.
  - Missing keys fall back to `en` and log in dev.
  - A test fails if the `en` and `de` key sets differ.
  - Theme names and descriptions are shown as provided by the theme (not translated); all surrounding UI text is translated.
- **Tech:** i18next 26.4 + react-i18next 17.0. Namespaces: `shell` (`apps/web/src/i18n/locales/{en,de}/shell.json`) and one per plugin, loaded from `PluginWebModule.locales`. Dates via `Intl.DateTimeFormat`.
- **Tests:** Vitest key-parity test across all namespaces.
- **Deps:** E08-01 · **Est:** S · **Labels:** area:web, i18n

## M0S-E08-05 · App shell, navigation model and plugin page route
- **Story:** As an adult household member, I want navigation with Today, plugin pages, Activity and Settings, so that I can find everything in the same place regardless of theme.
- **AC:**
  - Given enabled plugins, a single `NavModel` is built: Today (order 10), each `contributes.pages[]` with `nav: true` by `nav_order` (Tasks → `/p/tasks`, order 20), Activity (order 90), Settings (order 100). Each item has `id, label key, icon name, href, order`.
  - The default renderers `SidebarNav` (wide) and `DrawerNav` (narrow, < 768 px) render that model. Both are a `nav` landmark with an accessible name and the same item list in the same order.
  - `/p/$pageId` resolves the page component from the registry, or shows 404.
  - The shell is keyboard-navigable with a skip link.
  - Renderers may differ only in presentation; no renderer filters, reorders or relabels items (contract test).
- **Tech:** `shell/nav/{model.ts,SidebarNav.tsx,DrawerNav.tsx,NavRenderer.tsx}`; `routes/_app/p.$pageId.tsx`; `usePluginsQuery()`. `NavRenderer` picks a renderer from the active theme's layout (E13-05 adds `TopbarNav` and `BottomTabsNav`).
- **Tests:** Vitest: model building with a mocked registry; renderer contract test (same items, order, names); Playwright nav.
- **Deps:** E08-03, E06-06, E06-04 · **Est:** M · **Labels:** area:web, plugin

## M0S-E08-06 · Today dashboard grid
- **Story:** As an adult household member, I want a Today dashboard with movable widgets, so that my cockpit fits my household.
- **AC:**
  - Given first login, `/today` shows a default layout with the `tasks.list` widget at its `default_size`.
  - When I drag or resize it in Edit mode and click Done, `PUT /api/v1/dashboard/today {layout}` persists the change, and it survives a reload.
  - On widths under 768 px widgets stack in one column.
  - `PUT` rejects cells outside the 12-column grid with 422.
  - The grid has 12 columns in every theme. Row height and gutter come from the active theme's density (CSS variables `--hauskraft-grid-row`, `--hauskraft-grid-gap`), so switching theme never invalidates a saved layout.
  - Each widget is wrapped in `@hauskraft/ui`'s `WidgetFrame` (chrome variant from the theme, E13-02) and an error boundary.
- **Tech:**
  - react-grid-layout `^2` (`ResponsiveGridLayout` + `useContainerWidth`, explicit `layout` prop; import its CSS), 12 cols.
  - Backend `dashboard/router.py` stores `[{i, plugin_id, widget_id, x, y, w, h}]` in `dashboard_layouts` via a service with `authorize()`; `GET` returns the default when no row exists.
- **Tests:** Vitest: layout ↔ API mapping, row height read from CSS variable; integration: PUT/GET; Playwright: widget visible.
- **Deps:** E08-05, E04-02, E13-02 · **Est:** M · **Labels:** area:web, api
