<!-- SPDX-License-Identifier: MIT -->

# AGENTS.md: `@hearthos/ui`

Local rules on top of the [root AGENTS.md](../../AGENTS.md). Contract: [E13-02](../../docs/backlog/m0-star/E13-theming-system.md) and spec §10.2.

- **MIT, plugin-facing.** Never import from `apps/web` or any plugin.
- **Components read only theme tokens:** CSS variables (`--hearth-*` and the shadcn aliases) through the Tailwind `@theme inline` mapping. No colour literals anywhere except `src/tokens/fallback.css`, which holds the Default theme's values.
- **Variants come from data attributes** (`data-hearth-chrome`, `data-hearth-header`, `data-hearth-button-primary`, `data-hearth-checkbox`, density). Never accept a theme id or raw style props.
- **Variants change presentation only.** Roles, accessible names, heading levels, focus order and keyboard behaviour are identical in every variant; tests assert this per variant.
- **Icons:** `<Icon name>` takes semantic names from `packages/schemas/theme/icon-names-v1.json`; the active theme's sprite wins if it has the name, Lucide is the fallback. Icons are `aria-hidden` unless given a `label`.
- **Density** scales spacing, control heights and grid rows via `--hearth-space-unit` × `--hearth-density`; never hard-code heights.
- **Motion** honours `prefers-reduced-motion` (durations 0).
- shadcn components live in `src/components`; regenerate them with the shadcn CLI, then adapt them to tokens.
