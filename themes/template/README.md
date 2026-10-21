<!-- SPDX-License-Identifier: MIT -->

# Theme template

A complete, valid theme to start from (M0S-E13-09). It is a copy of the built-in Default theme with the placeholder
id `org.example.theme.mytheme`. The full guide is [docs/themes.md](../../docs/themes.md).

1. Copy this folder, e.g. to `./data/themes/mytheme/`.
2. In `hauskraft.plugin.json`, change `id` (reverse domain you control, e.g. `io.github.yourname.theme.mytheme`),
   `name`, `description`, `authors` and `source`.
3. Change colours in `tokens.light.json` and `tokens.dark.json`, the variants and layout in `theme.json`, and
   optionally fonts (keep their licence in `LICENSES/`).
4. Check it: `hauskraft themes validate --strict ./data/themes/mytheme`.
5. Restart the `api` service and pick the theme in Settings → Appearance.

The bundled font is Inter (OFL-1.1, `LICENSES/OFL-1.1.txt`). Theme data is MIT (`LICENSE`).
