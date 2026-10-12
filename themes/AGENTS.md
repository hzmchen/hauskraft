<!-- SPDX-License-Identifier: MIT -->

# AGENTS.md: themes

Local rules on top of the [root AGENTS.md](../AGENTS.md). Contract: spec §10.2, [E13](../docs/backlog/m0-star/E13-theming-system.md), [ADR-0013](../docs/adr/0013-theming.md).

- **Themes are data only.** `hearthos.plugin.json` (type `["theme"]`, `runtime.kind: "declarative"`, no capabilities, no data classes), `theme.json`, `tokens.light.json`, `tokens.dark.json`, `assets/`, `LICENSE`, `LICENSES/`. No CSS, scripts, HTML or external URLs, ever.
- **Tokens:** DTCG 2025.10; every name in `packages/schemas/theme/tokens-v1.json` in both modes. Use sRGB colours (hex, `rgb()` or DTCG `srgb`) in the built-in themes.
- **Hard rules (theme rejected otherwise):** text contrast ≥ 4.5:1 and non-text ≥ 3:1 for the pairs in `tokens-v1.json`, both modes; destructive vs primary OKLab distance ≥ 0.15; assets ≤ 2 MB each, ≤ 10 MB total, ≤ 8 fonts, sprite ≤ 500 symbols; SVGs pass the sanitiser.
- **Variants and layout** use only the enums in `packages/schemas/theme/layout-options-v1.json`. New tokens, variants or layout options need an ADR and a schema change first.
- **Function invariance:** a theme never adds, removes, renames, relabels, reorders or hides a function. Theme names are proper nouns and are not translated.
- **Licences:** theme data MIT; fonts self-hosted `.woff2` with their OFL-1.1 text in `LICENSES/`; icon packs with their own licence. No names, logos or artwork of real clubs, events or brands.
- **Check before committing:** `just themes-validate` (built-ins, `--strict`) or `hearthos themes validate --strict <folder>`.
- `builtin/` ships in the image; `template/` is the authoring starting point and must stay valid.
