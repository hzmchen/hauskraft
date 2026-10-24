# E13 · Theming system

**Goal:** Adults can switch the whole deployment between theme packages that change colours, type, shapes, component styles, icons and a few layout options, while every function stays exactly the same. Each device keeps its own light/dark/system mode.
**Spec:** `docs/spec/hauskraft-spec-v0.4.md` §10.2 (normative), §5.3 (theme plugin rules), §11.1 (theme threats).
**Decisions:** D4 (scope A + B + limited C, no custom CSS, packages only, no editor, built-in themes), D5 (one theme per deployment, mode per device), D6 (function invariance).
**Out of scope:** theme editor, custom CSS or scripts, per-user or per-device themes, hot reload, registry and signing, HA theme import, MCP Apps theme variables (M5).
**Dependencies:** E04-02, E06-01/03, E08-01/05.
**UI contract:** the accessible names and test hooks in `docs/testing/ui-contract.md` are part of every UI story's AC; the spec-owned e2e tests in `tests/e2e/` rely on them.

---

## Contracts

### Theme identity
`theme_id` = the theme plugin's `id` (e.g. `dev.hauskraft.theme.hackspace`). If one plugin contributes several themes, `theme_id` = `<plugin id>:<theme key>`. Built-ins: `dev.hauskraft.theme.default`, `dev.hauskraft.theme.paper`, `dev.hauskraft.theme.hackspace`. `HAUSKRAFT_DEFAULT_THEME` takes a `theme_id`; if unset or invalid, `dev.hauskraft.theme.default` is used.

### Files in `packages/schemas/theme/` (MIT)
- `hauskraft.theme.schema.json`: schema for `theme.json` (spec §10.2.4).
- `tokens-v1.json`: the required semantic token names, their DTCG `$type`, and the contrast pairs (spec §10.2.5). Single source for the compiler, `@hauskraft/ui` and the docs.
- `icon-names-v1.json`: core semantic icon names (spec §10.2.6).
- `layout-options-v1.json`: enums for navigation (`wide: sidebar|topbar`, `narrow: bottom-tabs|drawer`), density (`compact|comfortable|spacious`), content width (`full|contained`) and component variants (`widget.chrome: flat|outlined|elevated|tinted`, `widget.header: inline|banner`, `button.primary: solid|soft|outline`, `checkbox.style: square|round`).

### Theme API (core-api; OpenAPI tag `themes`)

| Method & path | Auth | Request | Response | Status codes |
|---|---|---|---|---|
| `GET /api/v1/themes` | session | — | `ThemeSummary[]` | 200, 401 |
| `GET /api/v1/theme` | **public** (login page needs it) | — | `ActiveTheme` | 200 |
| `GET /api/v1/theme/active.css` | public | `If-None-Match` | `text/css`, strong `ETag` = theme hash, `Cache-Control: no-cache` | 200, 304 |
| `GET /api/v1/theme/assets/{theme_id}/{path}` | public | `?h=<hash>` | asset bytes with allowlisted `Content-Type`, `Cache-Control: public, max-age=31536000, immutable`, `X-Content-Type-Options: nosniff` | 200, 404 |
| `PUT /api/v1/settings/theme` | session + CSRF | `{theme_id}` | `ThemeSummary` | 200, 401, 403, 404 `unknown_theme`, 409 `theme_invalid` |

```text
ThemeSummary = { theme_id, name, description, version, authors[], licence, origin: "builtin"|"installed",
                 valid: bool, errors: Issue[], warnings: Issue[], active: bool,
                 preview: { swatches: { light: string[], dark: string[] },
                            navigation: {wide, narrow}, density, widget_chrome } }
Issue        = { code, message, path }            # path points into the theme files, e.g. "tokens.dark.json#/color/primary"
ActiveTheme  = { theme_id, name, hash, css_url, components: {widget:{chrome,header}, button:{primary}, checkbox:{style}},
                 layout: {navigation:{wide,narrow}, density, content_width},
                 icons: { sprite_url: string|null, names: string[] } }
```

Public endpoints expose only theme data, never household data.

### Validator and CLI contract
- `hauskraft themes validate <path> [--strict] [--json]`: exit `0` valid (and, with `--strict`, no warnings), `1` invalid, `2` usage error such as a missing path. `--json` prints `{theme_id, path, valid, errors: Issue[], warnings: Issue[]}`; `Issue = {code, message, path}` where `path` points into the theme files (e.g. `tokens.light.json#/color/muted-foreground`).
- Error codes (fixed): `manifest.invalid`, `schema.invalid`, `token.missing`, `token.invalid_value`, `token.alias_cycle`, `contrast.text`, `contrast.non_text`, `distinct.destructive_primary`, `asset.path`, `asset.type`, `asset.size`, `asset.limit`, `svg.unsafe`.
- Warning codes (fixed): `icons.partial`, `preview.missing`, `licence.missing`.
- The same issues appear in `ThemeSummary.errors` / `warnings`.
- Expected outcomes for every fixture package are in `tests/fixtures/themes/expected.json`; the exact token list, pairs and enums the suite expects are in `tests/_support/theme_contract.py`.

### Contract file shapes (`packages/schemas/theme/`)
- `tokens-v1.json`: `{"tokens": {"<name>": {"type": "<DTCG $type>"}}, "contrast": {"text": {"min": 4.5, "pairs": [[fg, bg], …]}, "non_text": {"min": 3.0, "pairs": […]}}, "distinct": {"destructive_primary_min_oklab": 0.15}}`. Font sizes are `xs, sm, base, lg, xl, 2xl, 3xl`; chart colours `chart-1` … `chart-6`.
- `icon-names-v1.json`: `{"icons": [<17 core names in spec order>]}`.
- `layout-options-v1.json`: `{"navigation.wide": […], "navigation.narrow": […], "density": […], "content_width": […], "widget.chrome": […], "widget.header": […], "button.primary": […], "checkbox.style": […]}`.
- `theme.json` required keys: `theme_api`, `name`, `tokens.light`, `tokens.dark`, `components` (all four variants) and `layout` (navigation wide and narrow, density, content width). Optional: `$schema`, `description`, `fonts`, `icons`, `background`, `preview`. No other keys; no key named `css`, `script`, `style` or `html` anywhere; asset paths relative, without `..`, URL schemes or `data:`.

### Test hooks (also in `docs/testing/ui-contract.md`)
- `<html data-hauskraft-theme="<theme_id>">` plus the variant attributes; `.dark` class for dark mode.
- The main `nav` (accessible name "Main") carries `data-nav-style="sidebar|topbar|bottom-tabs|drawer"`.

### Compiled stylesheet shape

```css
/* dev.hauskraft.theme.hackspace 0.1.0 hash=… */
@font-face { font-family: "JetBrains Mono"; font-weight: 100 800; font-display: swap;
  src: url("/api/v1/theme/assets/dev.hauskraft.theme.hackspace/assets/fonts/JetBrainsMono-Variable.woff2?h=…") format("woff2"); }
:root {
  color-scheme: light;
  --hauskraft-color-background: …; /* every token from tokens.light.json */
  --background: var(--hauskraft-color-background);   /* shadcn aliases */
  --hauskraft-space-unit: 4px; --hauskraft-density: 0.85;
  --hauskraft-grid-row: calc(10 * var(--hauskraft-space-unit) * var(--hauskraft-density));
  --hauskraft-grid-gap: calc(4 * var(--hauskraft-space-unit) * var(--hauskraft-density));
}
:root.dark { color-scheme: dark; /* every token from tokens.dark.json */
  --hauskraft-app-bg-image: url("/api/v1/theme/assets/…/grid-dark.webp?h=…"); }
```

Component variants and layout are **not** CSS from the theme. They are applied as data attributes on `<html>` (`data-hauskraft-chrome`, `data-hauskraft-header`, `data-hauskraft-button`, `data-hauskraft-checkbox`, `data-hauskraft-density`, `data-hauskraft-content`) and styled by pre-built CSS in `@hauskraft/ui`. Navigation style is read by `NavRenderer`.

### Built-in themes

| Theme | Feel | Nav wide / narrow | Density | Widget chrome / header | Primary button | Checkbox | Fonts (OFL-1.1) | Icons |
|---|---|---|---|---|---|---|---|---|
| **Default** `dev.hauskraft.theme.default` | Calm neutral, soft blue accent | sidebar / drawer | comfortable | outlined / inline | solid | square | Inter | Lucide (default pack) |
| **Paper** `dev.hauskraft.theme.paper` | Ink on paper, high contrast, flat | topbar / drawer | compact | flat / inline | outline | square | Source Serif 4 (headings), Atkinson Hyperlegible Next (body) | Lucide |
| **Hackspace** `dev.hauskraft.theme.hackspace` | Underground hackerspace: near-black, phosphor green and magenta accents, amber warnings, square corners, faint grid background in dark mode; light mode looks like a green-ink printout | topbar / bottom-tabs | compact | tinted / banner (terminal-style title bar) | solid | square | VT323 (headings), JetBrains Mono (body) | Pixelarticons sprite (MIT) for all core names |

Content width: Default and Paper use `full`, Hackspace `contained` (an 80-column feel). Together the three cover every navigation and content-width option. `spacious` density, `elevated` widget chrome, `soft` buttons and `round` checkboxes are not used by a built-in theme; E13-02's variant tests cover them.

Hackspace is inspired by the Berlin hackerspace scene. It must not use the name, logo or artwork of any real club, event or organisation; all visuals are original or from permissively licensed packs.

---

## M0S-E13-01 · Theme contract schemas
- **Story:** As a theme author and as the agents building the compiler and UI kit, I want one machine-readable theme contract, so that themes, compiler and components agree on every token and option.
- **AC:**
  - Given `packages/schemas/theme/*` (files above), then `hauskraft.theme.schema.json` validates the Hackspace `theme.json` example from the spec and rejects: unknown keys, unknown enum values for any variant or layout option, missing `tokens.light` or `tokens.dark`, asset paths that are absolute, contain `..` or a URL scheme, and any `css`, `script`, `style` or `html` key anywhere.
  - `tokens-v1.json` lists every required token from spec §10.2.5 with its DTCG `$type`, and every contrast pair with its threshold (4.5 text, 3.0 non-text).
  - `icon-names-v1.json` contains the 17 core names from spec §10.2.6; a generated TypeScript union `IconName` and a Python `Literal` are produced by `just gen`.
  - ADR-0013 records thresholds, limits and the destructive/primary distance rule; the files reference the ADR.
- **Tech:** JSON Schema 2020-12, MIT header. Generators: `scripts/gen-theme-types.mjs` (TS) and `scripts/gen_theme_types.py` (Python).
- **Tests:** Contract: `check-jsonschema` with valid and invalid fixtures in `packages/schemas/tests/theme/`; generated types compile.
- **Deps:** E06-01 · **Est:** M · **Labels:** area:theme, contract

## M0S-E13-02 · `@hauskraft/ui` themed primitives
- **Story:** As a widget or plugin author, I want UI primitives that read only theme tokens and variant attributes, so that my widget looks right in every theme without me doing anything.
- **AC:**
  - Given `@hauskraft/ui`, then Tailwind v4 `@theme inline` maps utilities (`bg-background`, `text-foreground`, `bg-primary`, `text-primary-foreground`, `border-border`, `rounded-lg`, `shadow-md`, `font-heading`, chart colours, status colours) onto `--hauskraft-*` variables, and shadcn aliases are defined, so shadcn components work unmodified.
  - `WidgetFrame` renders a widget's title, actions slot and body, with styles for all `data-hauskraft-chrome` × `data-hauskraft-header` combinations. The title keeps the same heading level and accessible name in every variant.
  - `Button` (primary intent) and `Checkbox` render all variants from the attributes; their roles, names and keyboard behaviour do not change between variants.
  - Density utilities (`gap-density`, `p-density`, control heights) derive from `--hauskraft-space-unit` × `--hauskraft-density`.
  - `<Icon name: IconName | string>` renders from the active sprite if the name is listed in `ActiveTheme.icons.names`, otherwise from the default pack (Lucide mapping for all core names). Icons are `aria-hidden` unless given `label`.
  - Motion respects `prefers-reduced-motion` (durations 0).
  - A bundled `fallback.css` with Default theme values applies before the compiled theme stylesheet loads.
- **Tech:** `packages/ui/src/{tokens/theme.css,tokens/fallback.css,widget/WidgetFrame.tsx,components/*,icons/{Icon.tsx,default-pack.ts}}`. `lucide-react` (ISC) as the default pack.
- **Tests:** Vitest browser mode renders every variant combination with Default, Paper and Hackspace token fixtures; accessible-name assertions per variant; Icon fallback test.
- **Deps:** E08-01, E13-01 · **Est:** M · **Labels:** area:theme, web

## M0S-E13-03 · Theme loader, validator and compiler (backend)
- **Story:** As an operator, I want theme packages discovered, checked and compiled at startup, so that a broken or unsafe theme can never reach the browser.
- **AC:**
  - Given `HAUSKRAFT_THEME_PATHS` folders, when the API starts, then every theme plugin handed over by the plugin loader (E06-03) is validated and either compiled (valid) or recorded with errors (invalid). The registry holds `ThemeSummary` data in memory.
  - Validation rejects a theme when any of these fail:
    - manifest theme rules (E06-01) and `theme.json` schema (E13-01);
    - all required tokens present in both modes; DTCG aliases resolve without cycles; values parse for their `$type` (DTCG 2025.10 object forms and CSS-string shorthand accepted for colours and dimensions);
    - text contrast ≥ 4.5 and non-text contrast ≥ 3.0 for every pair in `tokens-v1.json`, in both modes (colours with alpha composited over their background);
    - `color.destructive` vs `color.primary` distance ≥ the ADR-0013 threshold in both modes;
    - assets: relative paths inside the theme folder only (no `..`, no symlinks leaving it), allowlisted types (`.woff2` with `wOF2` magic, `.png`, `.webp`, `.avif`, `.jpg`, `.svg`), ≤ 2 MB each, ≤ 10 MB total, ≤ 8 font files;
    - SVGs sanitised to an element/attribute allowlist (no `script`, `foreignObject`, event handlers, external `href`, or `url()` pointing outside the document); a sprite must not exceed 500 symbols.
  - Warnings (theme still valid): missing optional icons, missing preview swatches, fonts without a licence file in `LICENSES/`.
  - Issues use the fixed codes in "Validator and CLI contract"; every fixture in `tests/fixtures/themes/expected.json` produces its listed outcome.
  - The compiler emits the stylesheet shape above. Token values are serialised by the compiler (never copied as raw text), so a value cannot break out of its declaration. Output is deterministic; `hash` = SHA-256 over the theme's file contents.
  - If the active theme is invalid at startup, the API serves the Default theme and logs `theme.fallback` with reasons; readiness fails only if the built-in Default theme itself fails (check registered with E03-02's registry).
- **Tech:** `hauskraft_core/themes/{registry.py,validate.py,compile.py,svg_sanitize.py,dtcg.py}`. Colour parsing, WCAG contrast and OKLab distance via a tested library (candidate: `coloraide`, MIT; pin at implementation). XML parsing with `defusedxml`.
- **Tests:** Unit with fixture themes for every rejection rule, each warning, alias cycles, alpha compositing, and a CSS-injection attempt (`"red; } body { display:none"` as a colour value → rejected); golden-file test of compiled CSS for each built-in theme.
- **Deps:** E13-01, E06-03, E03-02 · **Est:** M · **Labels:** area:theme, security

## M0S-E13-04 · Deployment theme setting and theme API
- **Story:** As an adult household member, I want to set the household theme once for everyone, so that every device in the house shows the same look.
- **AC:**
  - Given the Theme API contract above, then every endpoint behaves as tabled. `GET /theme` and `active.css` work without a session (login page) and return no household data.
  - `PUT /settings/theme` goes through a settings service: `authorize(actor, "settings.theme.set", ResourceRef("DeploymentSetting","theme_id"), "household", "settings:write")`, upserts `deployment_settings['theme_id']`, and emits `hauskraft.settings.theme_changed` (`source: dev.hauskraft.core`, `dataclass: household`, `data: {from, to}`) in the same transaction. Any adult may call it in M0*.
  - Selecting an invalid theme returns 409 `theme_invalid` with its `errors`; an unknown id returns 404.
  - With no row in `deployment_settings`, the active theme is `HAUSKRAFT_DEFAULT_THEME` (or Default).
  - `active.css` returns 304 for a matching `If-None-Match`.
- **Tech:** `hauskraft_core/themes/router.py`, `hauskraft_core/settings_store/{service.py,repository.py}`; event data schema `packages/schemas/events/settings.theme_changed.data.schema.json`. OpenAPI regenerated.
- **Tests:** Integration: set/get, invalid/unknown, event in same transaction (rollback removes both), DenyAll → 403, ETag/304, public endpoints without cookie.
- **Deps:** E13-03, E04-02, E03-04, E10-02, E05-03 · **Est:** S · **Labels:** area:theme, api, governance

## M0S-E13-05 · Shell theme runtime and navigation styles
- **Story:** As an adult household member, I want the shell to apply the household theme without flicker and pick up a change made on another device, so that the house stays consistent.
- **AC:**
  - `index.html` links `/api/v1/theme/active.css` directly after the bundled fallback CSS. The colour-mode script (E08-02) runs before it. No flash of the fallback theme on a normal load (Playwright: first screenshot after navigation already uses the active theme's background).
  - `ThemeRuntime` queries `GET /theme` (`refetchInterval: 60_000`, `refetchOnWindowFocus: true`). When `hash` changes, it swaps the stylesheet `href` (preloaded first, then swapped, so no unstyled frame) and updates the `data-hauskraft-*` attributes, without a page reload and without losing form input.
  - `NavRenderer` adds `TopbarNav` and `BottomTabsNav` and chooses among the four renderers from `layout.navigation` (`wide` ≥ 768 px, `narrow` below). All four pass the renderer contract test from E08-05 (same items, order, names, `nav` landmark).
  - `BottomTabsNav` shows at most 5 items; if the model has more, the 5th becomes "More" opening a sheet with the rest, in model order. (M0* has 4 items, so no overflow, but the rule is tested.)
  - `content_width: contained` limits the main column to a max width from `@hauskraft/ui`; `full` uses the full width.
  - The app background uses `--hauskraft-app-bg-image` when present.
  - The shell sets the test hooks: `data-hauskraft-theme` on `<html>` and `data-nav-style` on the main `nav`.
- **Tech:** `apps/web/src/shell/{ThemeRuntime.tsx,nav/TopbarNav.tsx,nav/BottomTabsNav.tsx}`.
- **Tests:** Vitest: hash change swaps link and attributes; renderer contract for all four renderers; overflow rule. Playwright: second browser context picks up a theme change within 65 s (demo step 8).
- **Deps:** E13-04, E13-02, E08-05, E08-02 · **Est:** M · **Labels:** area:theme, web

## M0S-E13-06 · Three built-in themes
- **Story:** As a household, I want a few good themes out of the box, so that we can change the look without finding or making a package.
- **AC:**
  - Given `themes/builtin/{default,paper,hackspace}/`, each with `hauskraft.plugin.json`, `theme.json`, `tokens.light.json`, `tokens.dark.json`, `assets/` and `LICENSES/`, then all three pass `hauskraft themes validate --strict` (no warnings) and match the built-in themes table above.
  - Paper reaches ≥ 7:1 for `foreground/background` and `surface-foreground/surface` in both modes.
  - All fonts are self-hosted `.woff2` subsets (Latin + Latin Extended, enough for German) with OFL-1.1 licence texts. Hackspace's sprite covers all 17 core icon names; its licence file is included. Hackspace's monospace body text still meets every contrast rule, and its dark-mode grid background stays below the contrast of `color.border` so it never competes with content.
  - Each theme is MIT (theme data), with REUSE annotations for fonts and icons.
  - Colour values use sRGB (hex, `rgb()` or DTCG `srgb` objects) so the suite can verify contrast independently of the validator.
- **Tech:** Token files in DTCG 2025.10 format. Font subsetting with `fonttools` (`pyftsubset`) in a one-off script `scripts/subset-fonts.py` (output committed).
- **Tests:** CI `just themes-validate --strict`; golden CSS from E13-03; manual visual review screenshots attached to the PR for each theme, light and dark, wide and narrow.
- **Deps:** E13-03 · **Est:** M · **Labels:** area:theme, design

## M0S-E13-07 · Appearance settings page
- **Story:** As an adult household member, I want one page to pick the household theme and this device's light/dark mode, so that I understand which choice affects everyone and which only my device.
- **AC:**
  - Given `/settings/appearance`, then section **Household theme** says (localised) "Applies to everyone on every device" and lists theme cards from `GET /themes`: name, author, version, light and dark swatches, navigation style and density as small labels, "Active" marker.
  - Invalid themes appear greyed out with an expandable list of reasons (`Issue.message` and `path`) and cannot be selected.
  - Choosing a theme opens a confirmation dialog ("Change the look for everyone?"), then calls `PUT /settings/theme` and applies it immediately on this device.
  - Section **This device** shows the System / Light / Dark control from E08-02 with the note "Only this device".
  - A link "Add a theme" opens `docs/themes.md` guidance (served as a static page or link to the repo docs).
  - There is no editor and no free-form input on this page.
  - Settings is reachable from the navigation model (E08-05).
- **Tech:** `apps/web/src/routes/_app/settings.appearance.tsx`, components from `@hauskraft/ui`. Uses generated `themesListOptions` and `settingsThemeSetMutation`.
- **Tests:** Vitest: invalid themes not selectable, confirmation flow; Playwright: switch to Hackspace and back (demo step 8).
- **Deps:** E13-04, E13-05, E08-02 · **Est:** S · **Labels:** area:theme, web

## M0S-E13-08 · Function invariance and visual quality gates
- **Story:** As a maintainer, I want CI to prove that themes never change what the cockpit does, so that "function is fixed, presentation is swappable" stays true as themes and features grow.
- **AC:**
  - Given `tests/e2e/theme-invariance.spec.ts` (already written, spec-owned), for each built-in theme × mode (`light`, `dark`) × viewport (1280×800, 390×844), it visits `/today`, `/p/tasks`, `/activity` and `/settings/appearance` with the same seeded data, and:
    - captures `page.getByRole('main').ariaSnapshot()` and asserts it equals the Default/light capture for the same view and viewport, with the theme-picker's selected state masked;
    - captures the navigation item list (role, name, order), opening the drawer or "More" sheet if present, and asserts equality across themes;
    - runs an axe scan (`@axe-core/playwright`) with zero serious or critical violations.
  - Comparisons run across themes within the same test run (no stored ARIA baselines), so ordinary copy changes do not break the suite.
  - `toHaveScreenshot` baselines exist per theme for Today and All tasks (wide, light and dark); they catch visual regressions and are updated deliberately.
  - ESLint rule `hauskraft/no-raw-styles` fails on: colour literals (hex, rgb[a], hsl[a], oklch, oklab, named CSS colours) in TS/TSX/CSS; Tailwind default palette classes (e.g. `bg-red-500`, `text-slate-700`); arbitrary values (`p-[13px]`, `bg-[#fff]`); inline `style` with colour, font or spacing properties. It applies to `apps/web`, `packages/ui` (except `tokens/fallback.css`) and `plugins/**/web`, and has unit tests. The probes in `tests/fixtures/lint/` are flagged (or, for `semantic-ok.tsx`, not flagged) when linted with `eslint --stdin --stdin-filename plugins/official/tasks/web/src/_probe.tsx`.
- **Tech:** `tools/eslint-plugin-hauskraft/` (local plugin, MIT). Playwright `toMatchAriaSnapshot`/`ariaSnapshot()` (Playwright 1.64). Theme switching in tests via `PUT /settings/theme` as `demo`.
- **Tests:** The suite itself; lint-rule unit tests with good/bad fixtures; a deliberately broken fixture theme or component (renamed button in one renderer) proves the suite fails.
- **Deps:** E13-05, E13-06, E09-02, E10-03, E13-07 · **Est:** M · **Labels:** area:theme, type:test, a11y

## M0S-E13-09 · Theme authoring kit
- **Story:** As a tinkering parent, I want a template, a guide and a validator, so that I can make my own theme in an evening without reading the source code.
- **AC:**
  - `themes/template/` is a complete, valid theme (copy of Default with a placeholder id `org.example.theme.mytheme`) that passes `hauskraft themes validate`.
  - `hauskraft themes validate <path> [--strict] [--json]` prints each issue with code, file path and JSON pointer, exits 1 on errors (and on warnings with `--strict`) and 2 on usage errors such as a missing path. `hauskraft themes list` shows discovered themes, validity and which is active.
  - `docs/themes.md` covers: what a theme can and cannot change (levels A, B, limited C; no custom CSS), the function-invariance rule, file layout, the token contract with examples (both DTCG object form and CSS-string shorthand), contrast rules and how to check them, component variants, layout options, icon names and sprite format, asset limits, fonts and licences (OFL or similar, include the licence), installation (`./data/themes/<folder>`, restart `api`, select in Settings → Appearance), and exporting tokens from Figma / Tokens Studio / Penpot.
  - The guide's commands and examples are tested (doc-test script runs the validator against every JSON example in the guide).
- **Tech:** CLI in `hauskraft_core/cli.py` (`themes` sub-app) reusing E13-03's validator.
- **Tests:** CLI unit tests with CliRunner (valid, invalid, `--json` output shape); doc-test script in CI.
- **Deps:** E13-03, E13-06 · **Est:** S · **Labels:** area:theme, docs
