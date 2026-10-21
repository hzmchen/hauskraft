# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compile a validated theme into one stylesheet (M0S-E13-03).

Light tokens go on ``:root``, dark tokens on ``:root.dark``. Values come from the typed parser in ``dtcg``;
nothing from the theme files is copied as raw text. Component variants and layout are applied as data
attributes by the shell, not as CSS from the theme.
"""

from __future__ import annotations

from hauskraft_core.themes import dtcg
from hauskraft_core.themes.model import ThemeReport

ASSET_URL = "/api/v1/theme/assets/{theme_id}/{path}?h={hash}"
DENSITY = {"compact": "0.85", "comfortable": "1", "spacious": "1.15"}
# shadcn/ui variable names, so @hauskraft/ui components work unmodified (spec §10.2.5).
SHADCN = {
    "background": "color.background",
    "foreground": "color.foreground",
    "card": "color.surface",
    "card-foreground": "color.surface-foreground",
    "popover": "color.surface",
    "popover-foreground": "color.surface-foreground",
    "primary": "color.primary",
    "primary-foreground": "color.primary-foreground",
    "secondary": "color.secondary",
    "secondary-foreground": "color.secondary-foreground",
    "muted": "color.muted",
    "muted-foreground": "color.muted-foreground",
    "accent": "color.accent",
    "accent-foreground": "color.accent-foreground",
    "destructive": "color.destructive",
    "destructive-foreground": "color.destructive-foreground",
    "border": "color.border",
    "input": "color.input",
    "ring": "color.ring",
    "chart-1": "color.chart-1",
    "chart-2": "color.chart-2",
    "chart-3": "color.chart-3",
    "chart-4": "color.chart-4",
    "chart-5": "color.chart-5",
    "sidebar": "color.nav-background",
    "sidebar-foreground": "color.nav-foreground",
    "sidebar-primary": "color.nav-active",
    "sidebar-primary-foreground": "color.nav-active-foreground",
    "sidebar-accent": "color.nav-active",
    "sidebar-accent-foreground": "color.nav-active-foreground",
    "sidebar-border": "color.border",
    "sidebar-ring": "color.ring",
    "radius": "radius.lg",
}


def var(token: str) -> str:
    return "--hauskraft-" + token.replace(".", "-")


def asset_url(report: ThemeReport, path: str) -> str:
    return ASSET_URL.format(theme_id=report.theme_id, path=path, hash=report.hash[:16])


def _background(report: ThemeReport, mode: str) -> list[str]:
    spec = (report.theme.get("background") or {}).get(mode) or {}
    values = report.css_values[mode]
    lines = []
    if "color" in spec:
        lines.append(f"  --hauskraft-app-bg-color: {_colour(spec['color'], values)};")
    if "image" in spec:
        lines.append(f'  --hauskraft-app-bg-image: url("{asset_url(report, spec["image"])}");')
    if "gradient" in spec:
        g = spec["gradient"]
        angle = dtcg.parse_number(g.get("angle", 180))
        lines.append(
            f"  --hauskraft-app-bg-image: linear-gradient({angle}deg, {_colour(g['from'], values)}, "
            f"{_colour(g['to'], values)});"
        )
    if not spec:
        lines.append("  --hauskraft-app-bg-color: var(--hauskraft-color-background);")
    return lines


def _colour(value: str, values: dict[str, str]) -> str:
    match = dtcg.ALIAS.match(value)
    if match and match.group(1) in values:
        return f"var({var(match.group(1))})"
    return dtcg.parse_colour(value).css()


def compile_css(report: ThemeReport) -> str:
    theme = report.theme
    out = [f"/* {report.theme_id} {report.version} hash={report.hash} */"]
    for font in theme.get("fonts") or []:
        family = dtcg.parse_font_family([font["family"]])
        weight = font.get("weight", "400")
        style = font.get("style", "normal")
        out.append(
            f"@font-face {{ font-family: {family}; font-weight: {weight}; font-style: {style}; "
            f'font-display: swap; src: url("{asset_url(report, font["src"])}") format("woff2"); }}'
        )
    layout = theme["layout"]
    for mode in ("light", "dark"):
        values = report.css_values[mode]
        out.append(":root {" if mode == "light" else ":root.dark {")
        out.append(f"  color-scheme: {mode};")
        out.extend(f"  {var(token)}: {value};" for token, value in sorted(values.items()))
        out.extend(f"  --{alias}: var({var(token)});" for alias, token in SHADCN.items())
        if mode == "light":
            out.append(f"  --hauskraft-density: {DENSITY[layout['density']]};")
            out.append("  --hauskraft-grid-row: calc(10 * var(--hauskraft-space-unit) * var(--hauskraft-density));")
            out.append("  --hauskraft-grid-gap: calc(4 * var(--hauskraft-space-unit) * var(--hauskraft-density));")
        out.extend(_background(report, mode))
        out.append("}")
    out.append("@media (prefers-reduced-motion: reduce) {")
    out.append("  :root, :root.dark { --hauskraft-duration-fast: 0ms; --hauskraft-duration-normal: 0ms; }")
    out.append("}")
    return "\n".join(out) + "\n"
