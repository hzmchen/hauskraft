<!-- SPDX-License-Identifier: MIT -->

# Built-in themes

Default, Paper and Hackspace live here (M0S-E13-06). Themes are data only: see `docs/spec/hauskraft-spec-v0.3.md` §10.2
and the "Built-in themes" table in `docs/backlog/m0-star/E13-theming-system.md`.

| Theme     | Folder       | Fonts (OFL-1.1)                                              | Icons                      |
| --------- | ------------ | ------------------------------------------------------------ | -------------------------- |
| Default   | `default/`   | Inter                                                        | default pack (Lucide)      |
| Paper     | `paper/`     | Source Serif 4 (headings), Atkinson Hyperlegible Next (body) | default pack (Lucide)      |
| Hackspace | `hackspace/` | VT323 (headings), JetBrains Mono (body)                      | Pixelarticons sprite (MIT) |

Theme data (`*.json`, the grid background) is MIT. Fonts are OFL-1.1 (`LICENSES/OFL-1.1.txt` in each theme, copyright
lines in the repository's `REUSE.toml`); the Hackspace sprite is MIT (`hackspace/LICENSES/MIT-pixelarticons.txt`).

## Rebuilding the assets

The generated assets are committed; rebuild them only on purpose:

- Fonts: `uv run scripts/subset-fonts.py` downloads the pinned sources, subsets them to Latin + Latin Extended and
  writes WOFF2. The output is byte-for-byte reproducible.
- Hackspace icons: `uv run python scripts/build-hackspace-icons.py <pixelarticons>/svg` (see the script for the exact version).

Any change to a theme's files changes its hash, so regenerate the golden stylesheets in
`services/core_api/tests/unit/golden/` and review the diff.
