# SPDX-License-Identifier: MIT
"""The theme contract v1 as the acceptance suite expects it.

Source of truth for humans: docs/spec/hearthos-spec-v0.2.md §10.2 and
docs/backlog/m0-star/E13-theming-system.md ("Contracts"). The machine-readable files
in packages/schemas/theme/ (M0S-E13-01) must agree with this module; a test checks that.
"""

from __future__ import annotations

COLOUR_TOKENS = [
    # surfaces
    "color.background", "color.foreground", "color.surface", "color.surface-foreground",
    "color.muted", "color.muted-foreground", "color.border", "color.input", "color.ring",
    "color.overlay",
    # roles
    "color.primary", "color.primary-foreground", "color.secondary", "color.secondary-foreground",
    "color.accent", "color.accent-foreground", "color.destructive", "color.destructive-foreground",
    "color.success", "color.success-foreground", "color.warning", "color.warning-foreground",
    "color.info", "color.info-foreground",
    # chrome
    "color.nav-background", "color.nav-foreground", "color.nav-active", "color.nav-active-foreground",
    "color.widget-background", "color.widget-foreground", "color.widget-border",
    # data
    "color.chart-1", "color.chart-2", "color.chart-3", "color.chart-4", "color.chart-5", "color.chart-6",
]

OTHER_TOKENS = {
    "font.sans": "fontFamily", "font.heading": "fontFamily", "font.mono": "fontFamily",
    "font-size.xs": "dimension", "font-size.sm": "dimension", "font-size.base": "dimension",
    "font-size.lg": "dimension", "font-size.xl": "dimension", "font-size.2xl": "dimension",
    "font-size.3xl": "dimension",
    "font-weight.regular": "fontWeight", "font-weight.medium": "fontWeight", "font-weight.bold": "fontWeight",
    "line-height.tight": "number", "line-height.normal": "number",
    "radius.sm": "dimension", "radius.md": "dimension", "radius.lg": "dimension",
    "radius.xl": "dimension", "radius.full": "dimension",
    "space.unit": "dimension",
    "shadow.sm": "shadow", "shadow.md": "shadow", "shadow.lg": "shadow",
    "duration.fast": "duration", "duration.normal": "duration",
    "easing.standard": "cubicBezier",
}

REQUIRED_TOKENS: dict[str, str] = {**{name: "color" for name in COLOUR_TOKENS}, **OTHER_TOKENS}

# (foreground, background) pairs that must reach 4.5:1 in both modes.
TEXT_PAIRS = [
    ("color.foreground", "color.background"),
    ("color.surface-foreground", "color.surface"),
    ("color.muted-foreground", "color.background"),
    ("color.primary-foreground", "color.primary"),
    ("color.secondary-foreground", "color.secondary"),
    ("color.accent-foreground", "color.accent"),
    ("color.destructive-foreground", "color.destructive"),
    ("color.success-foreground", "color.success"),
    ("color.warning-foreground", "color.warning"),
    ("color.info-foreground", "color.info"),
    ("color.nav-foreground", "color.nav-background"),
    ("color.nav-active-foreground", "color.nav-active"),
    ("color.widget-foreground", "color.widget-background"),
]
TEXT_MIN = 4.5

# Non-text UI pairs that must reach 3:1 in both modes.
NON_TEXT_PAIRS = [
    (fg, bg)
    for fg in ("color.border", "color.input", "color.ring")
    for bg in ("color.background", "color.surface")
]
NON_TEXT_MIN = 3.0

# Proposed in ADR-0013; the suite uses the same number.
DESTRUCTIVE_PRIMARY_MIN_OKLAB = 0.15

CORE_ICON_NAMES = [
    "nav.today", "nav.tasks", "nav.activity", "nav.settings",
    "action.add", "action.edit", "action.delete", "action.confirm", "action.cancel",
    "status.done", "status.due", "status.overdue",
    "user.menu", "mode.system", "mode.light", "mode.dark", "widget.unavailable",
]

LAYOUT_OPTIONS = {
    "navigation.wide": ["sidebar", "topbar"],
    "navigation.narrow": ["bottom-tabs", "drawer"],
    "density": ["compact", "comfortable", "spacious"],
    "content_width": ["full", "contained"],
    "widget.chrome": ["flat", "outlined", "elevated", "tinted"],
    "widget.header": ["inline", "banner"],
    "button.primary": ["solid", "soft", "outline"],
    "checkbox.style": ["square", "round"],
}

# Issue codes reported by `hearthos themes validate --json` and GET /api/v1/themes.
ERROR_CODES = {
    "manifest.invalid",        # plugin manifest or theme plugin rules violated
    "schema.invalid",          # theme.json fails the theme schema (incl. URL schemes, '..', css keys)
    "token.missing",           # a required token is absent in a mode
    "token.invalid_value",     # value does not parse for its $type (incl. injection attempts)
    "token.alias_cycle",       # aliases form a cycle or point nowhere
    "contrast.text",           # a TEXT_PAIRS pair is below 4.5:1
    "contrast.non_text",       # a NON_TEXT_PAIRS pair is below 3:1
    "distinct.destructive_primary",  # destructive too close to primary
    "asset.path",              # asset outside the theme folder (incl. symlinks leaving it)
    "asset.type",              # disallowed type or bad magic bytes
    "asset.size",              # single asset over 2 MB
    "asset.limit",             # total over 10 MB, more than 8 fonts, or sprite over 500 symbols
    "svg.unsafe",              # SVG contains script, foreignObject, handlers or external refs
}
WARNING_CODES = {
    "icons.partial",           # sprite does not cover every core icon name
    "preview.missing",         # no preview swatches
    "licence.missing",         # bundled fonts or icons without a licence file in LICENSES/
}
