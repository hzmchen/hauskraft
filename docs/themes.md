<!-- SPDX-License-Identifier: MIT -->

# Making a Hauskraft theme

A theme changes how Hauskraft looks: colours, type, shapes, spacing, a few component styles and the navigation
layout. It never changes what Hauskraft does. This guide takes you from a copy of the template to your theme being
active in the household, in an evening, without reading any source code.

Contract details live in the [spec, §10.2](spec/hauskraft-spec-v0.3.md#102-theming-system) and
[ADR-0013](adr/0013-theming.md). The machine-readable contract is in
[`packages/schemas/theme/`](../packages/schemas/theme/).

## What a theme can and cannot change

| Level | You may change | How |
|---|---|---|
| **A. Tokens** | Colours (by role), typography (families, sizes, weights, line heights), corner radius, spacing unit, shadows, motion speed, focus ring, app background (colour, gradient or a bundled image) | `tokens.light.json`, `tokens.dark.json`, `theme.json` → `background` |
| **B. Component styles** | Widget chrome, widget header, primary button style, checkbox style, icon pack | `theme.json` → `components`, `icons` (fixed choices) |
| **C. Layout (limited)** | Navigation style on wide and narrow screens, density, content width | `theme.json` → `layout` (fixed choices) |
| **D. Custom CSS or scripts** | **Not allowed** | There is no custom CSS, no JavaScript, no HTML and no external URL anywhere in a theme |

A theme is data. Hauskraft reads it, checks it and compiles it into one stylesheet itself; nothing from your files is
copied into CSS as raw text. A key called `css`, `script`, `style` or `html` anywhere makes the theme invalid.

### Function invariance

Whatever your theme does, every user still gets the same pages, the same navigation items in the same order, the same
widgets, buttons, labels, keyboard shortcuts and screen-reader names. A theme may not add, remove, reorder, rename,
relabel or hide anything. Labels come from the app's translations and cannot be overridden. CI checks this by
comparing the accessibility tree of every view across the built-in themes.

Readability counts as function: a button nobody can read is effectively hidden. That is why the contrast rules
below are hard errors, not warnings.

### One theme per household

The theme applies to the whole household on every device. Light or dark mode is chosen per device (system, light or
dark), so a wall tablet can go dark at night while a phone stays light. Your theme must provide both modes.

## File layout

```text
mytheme/
  hauskraft.plugin.json     # who you are: id, name, version, licence (type ["theme"], declarative)
  theme.json               # components, layout, fonts, icons, background, preview
  tokens.light.json        # design tokens for light mode (DTCG 2025.10)
  tokens.dark.json         # design tokens for dark mode
  assets/fonts/*.woff2     # self-hosted fonts only
  assets/images/*          # backgrounds (png, webp, avif, jpg, svg)
  assets/icons/sprite.svg  # optional icon pack
  LICENSE                  # the licence of your theme data (MIT is a good choice)
  LICENSES/                # licence texts of bundled fonts and icons
```

Start from [`themes/template/`](../themes/template/): a complete, valid copy of the Default theme with the
placeholder id `org.example.theme.mytheme`.

### `hauskraft.plugin.json`

Change `id`, `name`, `description`, `authors` and `source`. The id is a reverse domain name you control, for example
`io.github.yourname.theme.mytheme`. Keep `type`, `runtime`, `capabilities` and `data_classes` exactly as they are:
themes cannot ask for capabilities or data.

<!-- example: manifest -->
```json
{
  "id": "io.github.yourname.theme.mytheme",
  "name": "My Theme",
  "version": "0.1.0",
  "description": "Warm evening colours with rounded corners.",
  "authors": [{ "name": "Your Name" }],
  "source": "https://github.com/yourname/hauskraft-mytheme"
}
```

## Tokens

Tokens use the [Design Tokens Community Group](https://www.designtokens.org/) format, version 2025.10. Every token
in the contract must exist in **both** files. Group tokens with a shared `$type`; reference another token with
`{group.name}`.

The required tokens are listed in
[`packages/schemas/theme/tokens-v1.json`](../packages/schemas/theme/tokens-v1.json):

| Group | Tokens |
|---|---|
| Colour, surfaces | `background`, `foreground`, `surface`, `surface-foreground`, `muted`, `muted-foreground`, `border`, `input`, `ring`, `overlay` |
| Colour, roles | `primary`, `secondary`, `accent`, `destructive`, `success`, `warning`, `info`, each with a `-foreground` |
| Colour, chrome | `nav-background`, `nav-foreground`, `nav-active`, `nav-active-foreground`, `widget-background`, `widget-foreground`, `widget-border` |
| Colour, data | `chart-1` … `chart-6` |
| Typography | `font.sans`, `font.heading`, `font.mono`, `font-size.xs` … `font-size.3xl`, `font-weight.regular` / `medium` / `bold`, `line-height.tight` / `normal` |
| Shape | `radius.sm`, `radius.md`, `radius.lg`, `radius.xl`, `radius.full` |
| Spacing | `space.unit` (density multiplies it) |
| Elevation | `shadow.sm`, `shadow.md`, `shadow.lg` |
| Motion | `duration.fast`, `duration.normal`, `easing.standard` (set to 0 automatically for people who prefer reduced motion) |

### Values: object form and CSS shorthand

Colours and dimensions can be written in the DTCG object form or as a short CSS string. Both of these are valid
(this one is for `tokens.light.json`: a dark blue `primary` would fail contrast in dark mode):

<!-- example: tokens.light -->
```json
{
  "color": {
    "$type": "color",
    "primary": { "$value": { "colorSpace": "srgb", "components": [0.114, 0.306, 0.847] } },
    "ring": { "$value": "{color.primary}" }
  },
  "radius": {
    "$type": "dimension",
    "lg": { "$value": { "value": 10, "unit": "px" } },
    "xl": { "$value": "14px" }
  }
}
```

<!-- example: tokens.light -->
```json
{
  "color": {
    "$type": "color",
    "accent": { "$value": "#dbeafe" },
    "accent-foreground": { "$value": "rgb(30 58 138)" },
    "overlay": { "$value": "#0f172a99" }
  }
}
```

Accepted colour strings: hex (`#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa`), `rgb()`/`rgba()`, `hsl()`, `oklch()` and
named colours. Lengths use `px`, `rem` or `em`; durations `ms` or `s`; `easing` is a cubic Bézier (four numbers). A
value that is not a clean colour, length or duration is rejected, for example:

<!-- example: tokens.light expect=token.invalid_value -->
```json
{ "color": { "$type": "color", "primary": { "$value": "red; } body { display: none" } } }
```

Fonts are a list of family names, most preferred first:

<!-- example: tokens.both -->
```json
{
  "font": {
    "$type": "fontFamily",
    "sans": { "$value": ["Inter", "system-ui", "sans-serif"] },
    "heading": { "$value": "{font.sans}" }
  }
}
```

## Contrast rules (hard requirements)

Checked in both modes; a theme that fails any of them cannot be selected.

- **Text ≥ 4.5:1** (WCAG 2.2 AA) for each foreground on its background: `foreground`/`background`,
  `surface-foreground`/`surface`, `muted-foreground`/`background`, every role (`primary`, `secondary`, `accent`,
  `destructive`, `success`, `warning`, `info`) with its `-foreground`, `nav-foreground`/`nav-background`,
  `nav-active-foreground`/`nav-active` and `widget-foreground`/`widget-background`.
- **Non-text ≥ 3:1** for `border`, `input` and `ring` against `background` and against `surface`.
- **Delete must not look like Save:** `destructive` and `primary` need an OKLab distance of at least 0.15.
- Colours with transparency are blended over their background before contrast is measured.

This one fails, because light grey text on white is about 1.5:1:

<!-- example: tokens.light expect=contrast.text -->
```json
{ "color": { "$type": "color", "muted-foreground": { "$value": "#c0c4cc" } } }
```

**How to check:** run the validator (below). It names the token, the mode, the ratio and the minimum, for example
`color.muted-foreground on color.background is 1.48:1 in light mode (needs 4.5:1)`. Any WCAG contrast checker gives
the same numbers for opaque colours.

## Component styles and layout

Pick one value for each option. The choices are fixed (see
[`layout-options-v1.json`](../packages/schemas/theme/layout-options-v1.json)); a new option needs an ADR and a schema
change first.

| Option | Choices |
|---|---|
| `components.widget.chrome` | `flat`, `outlined`, `elevated`, `tinted` |
| `components.widget.header` | `inline`, `banner` |
| `components.button.primary` | `solid`, `soft`, `outline` |
| `components.checkbox.style` | `square`, `round` |
| `layout.navigation.wide` | `sidebar`, `topbar` |
| `layout.navigation.narrow` | `bottom-tabs`, `drawer` |
| `layout.density` | `compact`, `comfortable`, `spacious` |
| `layout.content_width` | `full`, `contained` |

Navigation styles change where the menu sits, never which items it has or their order. Density changes spacing,
control size, grid row height and gutters only; the dashboard grid always has 12 columns, so saved layouts keep
working in every theme.

<!-- example: theme -->
```json
{
  "components": {
    "widget": { "chrome": "elevated", "header": "banner" },
    "button": { "primary": "soft" },
    "checkbox": { "style": "round" }
  },
  "layout": {
    "navigation": { "wide": "topbar", "narrow": "bottom-tabs" },
    "density": "spacious",
    "content_width": "contained"
  }
}
```

### Background and preview

`background` takes, per mode, exactly one of `color`, `gradient` or `image` (a file in your theme). `preview.swatches`
lists up to six colours (token references are fine) shown on your theme's card in Settings → Appearance.

<!-- example: theme -->
```json
{
  "background": {
    "light": { "gradient": { "from": "{color.background}", "to": "{color.muted}", "angle": 180 } },
    "dark": { "color": "{color.background}" }
  },
  "preview": { "swatches": ["{color.background}", "{color.primary}", "{color.accent}"] }
}
```

## Icons

Icons are referenced by meaning, never by file. The core names (v1) are:

`nav.today`, `nav.tasks`, `nav.activity`, `nav.settings`, `action.add`, `action.edit`, `action.delete`,
`action.confirm`, `action.cancel`, `status.done`, `status.due`, `status.overdue`, `user.menu`, `mode.system`,
`mode.light`, `mode.dark`, `widget.unavailable`.

To bring your own icon pack, add one SVG sprite with a `<symbol>` per name and point `icons.pack` at it. Any name you
leave out falls back to the default pack (Lucide); the validator warns with `icons.partial`.

```text
<svg xmlns="http://www.w3.org/2000/svg">
  <symbol id="action.add" viewBox="0 0 24 24" fill="currentColor"><path d="M11 5h2v14h-2zM5 11h14v2H5z"/></symbol>
  <symbol id="action.delete" viewBox="0 0 24 24" fill="currentColor"><path d="..."/></symbol>
</svg>
```

Use `currentColor` so icons follow the text colour. Sprites may only contain shapes (`path`, `rect`, `circle`, …),
groups and gradients: no scripts, `foreignObject`, event handlers, external links or `url()` pointing outside the
file. Screen-reader names come from the app, never from the sprite. The Hackspace theme's sprite is a worked example.

## Fonts and licences

- Fonts must be bundled as `.woff2` in `assets/fonts/`; links to font services are not allowed (they would leak
  every visit to a third party). Subset them to the characters you need: Latin plus Latin Extended covers German
  and most European languages.
- Use fonts whose licence allows bundling, such as the SIL Open Font License (OFL-1.1). Put the licence text in
  `LICENSES/` (for example `LICENSES/OFL-1.1.txt`); the validator warns with `licence.missing` otherwise.
- Icon packs need their licence in `LICENSES/` as well.
- Do not use names, logos or artwork you have no right to use.

<!-- example: theme -->
```json
{
  "fonts": [
    { "family": "Inter", "src": "assets/fonts/Inter-Variable.woff2", "weight": "100 900", "style": "normal" }
  ]
}
```

## Asset limits

| Limit | Value |
|---|---|
| Allowed files | `.woff2` (checked by content), `.png`, `.webp`, `.avif`, `.jpg`, `.svg` |
| Paths | relative and inside the theme folder; no `..`, no absolute paths, no URLs, no symlinks leaving the folder |
| Size per file | 2 MB |
| All assets together | 10 MB |
| Fonts | at most 8 files |
| Icon sprite | at most 500 symbols |

## Check your theme

```text
hauskraft themes validate ./data/themes/mytheme            # errors make it exit 1
hauskraft themes validate --strict ./data/themes/mytheme   # warnings fail too
hauskraft themes validate --json ./data/themes/mytheme     # machine-readable report
hauskraft themes list                                      # every theme found, valid or not, and the active one
```

Each issue shows a fixed code, the file and the place in it, then a message:

```text
error    contrast.text                 tokens.light.json#/color/muted-foreground
         color.muted-foreground on color.background is 1.48:1 in light mode (needs 4.5:1)
org.example.theme.mytheme: invalid, 1 error(s), 0 warning(s)
```

Errors: `manifest.invalid`, `schema.invalid`, `token.missing`, `token.invalid_value`, `token.alias_cycle`,
`contrast.text`, `contrast.non_text`, `distinct.destructive_primary`, `asset.path`, `asset.type`, `asset.size`,
`asset.limit`, `svg.unsafe`. Warnings: `icons.partial`, `preview.missing`, `licence.missing`. Exit codes: 0 valid
(with `--strict`: and no warnings), 1 invalid, 2 usage error such as a missing folder.

## Install and select it

1. Put the folder in the themes volume: `./data/themes/<folder>` on the host (`/data/themes` in the container,
   configured by `HAUSKRAFT_THEME_PATHS`).
2. Restart the `api` service: `docker compose restart api`. Themes are discovered at start.
3. Open Settings → Appearance. Your theme is listed with its validation result; invalid themes are shown with their
   reasons but cannot be selected. Choose it, and it applies to everyone in the household.

## Exporting tokens from design tools

Because the token files are standard DTCG JSON, you can design in a tool and export:

- **Tokens Studio** (Figma plugin): export in the W3C DTCG format, one file per mode.
- **Penpot**: export the design tokens as JSON in DTCG format.
- **Figma variables**: export with a plugin or script that writes DTCG JSON, one file per mode.

Then rename your tokens to the Hauskraft names above (`color.primary`, `font-size.base`, …), keep `$type` and
`$value`, split light and dark into `tokens.light.json` and `tokens.dark.json`, and run the validator. Extra tokens
that are not in the contract are ignored.
