# SPDX-License-Identifier: AGPL-3.0-or-later
"""DTCG 2025.10 tokens: flattening, alias resolution, typed parsing and safe CSS serialisation.

Values are parsed into typed objects and re-serialised by this module; raw text from a theme never reaches
the stylesheet, so a value cannot break out of its CSS declaration (spec §11.1).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from coloraide import Color

ALIAS = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")
_FAMILY = re.compile(r"^[A-Za-z0-9 _.-]{1,60}$")
_GENERIC_FAMILIES = {
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "ui-serif",
    "ui-sans-serif",
    "ui-monospace",
    "ui-rounded",
    "math",
    "emoji",
    "fangsong",
}
_DIMENSION = re.compile(r"^(-?\d+(?:\.\d+)?)(px|rem|em)$")
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)(ms|s)$")
_DTCG_SPACES = {
    "srgb": "srgb",
    "srgb-linear": "srgb-linear",
    "display-p3": "display-p3",
    "oklab": "oklab",
    "oklch": "oklch",
    "hsl": "hsl",
    "hwb": "hwb",
    "lab": "lab",
    "lch": "lch",
    "a98-rgb": "a98-rgb",
    "prophoto-rgb": "prophoto-rgb",
    "rec2020": "rec2020",
    "xyz-d65": "xyz-d65",
    "xyz-d50": "xyz-d50",
}
_FONT_WEIGHTS = {
    "thin": 100,
    "hairline": 100,
    "extra-light": 200,
    "ultra-light": 200,
    "light": 300,
    "normal": 400,
    "regular": 400,
    "book": 400,
    "medium": 500,
    "semi-bold": 600,
    "demi-bold": 600,
    "bold": 700,
    "extra-bold": 800,
    "ultra-bold": 800,
    "black": 900,
    "heavy": 900,
}


class TokenValueError(ValueError):
    pass


class AliasError(ValueError):
    pass


def flatten(tree: dict[str, Any], prefix: str = "", inherited: str | None = None) -> dict[str, dict[str, Any]]:
    """``{"color.primary": {"$type": "color", "$value": ...}}`` for every token; ``$type`` inherits."""
    out: dict[str, dict[str, Any]] = {}
    group_type = tree.get("$type", inherited)
    for key, node in tree.items():
        if key.startswith("$") or not isinstance(node, dict):
            continue
        name = f"{prefix}.{key}" if prefix else key
        if "$value" in node:
            out[name] = {"$type": node.get("$type", group_type), "$value": node["$value"]}
        else:
            out.update(flatten(node, name, group_type))
    return out


def resolve(tokens: dict[str, dict[str, Any]], name: str) -> Any:
    """Follow ``{group.token}`` aliases; raise ``AliasError`` on a cycle or a missing target."""
    seen: list[str] = []
    current = name
    while True:
        if current in seen:
            raise AliasError("alias cycle: " + " -> ".join([*seen, current]))
        if current not in tokens:
            raise AliasError(f"{seen[-1] if seen else name} points to missing token {current!r}")
        seen.append(current)
        value = tokens[current]["$value"]
        match = ALIAS.match(value) if isinstance(value, str) else None
        if not match:
            return value
        current = match.group(1)


# ---------------------------------------------------------------- typed values
@dataclass(frozen=True)
class Rgba:
    r: float
    g: float
    b: float
    a: float

    def css(self) -> str:
        channels = " ".join(str(round(c * 255)) for c in (self.r, self.g, self.b))
        return f"rgb({channels})" if self.a >= 1 else f"rgb({channels} / {round(self.a, 3)})"

    def over(self, bg: Rgba) -> Rgba:
        a = self.a
        return Rgba(self.r * a + bg.r * (1 - a), self.g * a + bg.g * (1 - a), self.b * a + bg.b * (1 - a), 1.0)


def parse_colour(value: Any) -> Rgba:
    try:
        if isinstance(value, dict):
            space = _DTCG_SPACES.get(str(value.get("colorSpace")))
            comps = value.get("components")
            if space is None or not (
                isinstance(comps, list) and len(comps) == 3 and all(isinstance(c, (int, float)) for c in comps)
            ):
                raise TokenValueError(f"unsupported DTCG colour {value!r}")
            alpha = value.get("alpha", 1)
            if not isinstance(alpha, (int, float)) or not 0 <= alpha <= 1:
                raise TokenValueError("alpha must be between 0 and 1")
            colour = Color(space, [float(c) for c in comps], float(alpha))
        elif isinstance(value, str) and len(value) <= 80 and not set(value) & set(";{}<>\\\"'@"):
            colour = Color(value.strip())
        else:
            raise TokenValueError(f"not a colour: {value!r}")
        srgb = colour.convert("srgb").fit("srgb")
    except (ValueError, TypeError) as exc:
        raise TokenValueError(str(exc)) from None
    r, g, b = (min(1.0, max(0.0, float(c))) for c in srgb.coords())
    a = float(srgb.alpha())
    if any(math.isnan(x) for x in (r, g, b, a)):
        raise TokenValueError(f"not a colour: {value!r}")
    return Rgba(r, g, b, a)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(c: Rgba) -> float:
    return 0.2126 * _lin(c.r) + 0.7152 * _lin(c.g) + 0.0722 * _lin(c.b)


WHITE = Rgba(1.0, 1.0, 1.0, 1.0)


def contrast(fg: Rgba, bg: Rgba) -> float:
    """WCAG 2.x contrast; translucent colours are composited (background over white first)."""
    base = bg.over(WHITE) if bg.a < 1 else bg
    front = fg.over(base)
    hi, lo = sorted((luminance(front), luminance(base)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def oklab_distance(a: Rgba, b: Rgba) -> float:
    pa = Color("srgb", [a.r, a.g, a.b]).convert("oklab").coords()
    pb = Color("srgb", [b.r, b.g, b.b]).convert("oklab").coords()
    return math.dist(pa, pb)


def parse_dimension(value: Any) -> str:
    if isinstance(value, dict):
        number, unit = value.get("value"), value.get("unit")
        if not isinstance(number, (int, float)) or isinstance(number, bool) or unit not in ("px", "rem", "em"):
            raise TokenValueError(f"dimension needs a number and px|rem|em, got {value!r}")
        return f"{_num(number)}{unit}"
    if isinstance(value, str) and (m := _DIMENSION.match(value.strip())):
        return f"{_num(float(m.group(1)))}{m.group(2)}"
    raise TokenValueError(f"not a dimension: {value!r}")


def parse_duration(value: Any) -> str:
    if isinstance(value, dict):
        number, unit = value.get("value"), value.get("unit")
        if not isinstance(number, (int, float)) or isinstance(number, bool) or number < 0 or unit not in ("ms", "s"):
            raise TokenValueError(f"duration needs a number and ms|s, got {value!r}")
        return f"{_num(number)}{unit}"
    if isinstance(value, str) and (m := _DURATION.match(value.strip())):
        return f"{_num(float(m.group(1)))}{m.group(2)}"
    raise TokenValueError(f"not a duration: {value!r}")


def parse_font_family(value: Any) -> str:
    names = [value] if isinstance(value, str) else value
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        raise TokenValueError(f"font family must be a string or a list of strings, got {value!r}")
    out = []
    for name in names:
        name = name.strip()
        if not _FAMILY.match(name):
            raise TokenValueError(f"unsafe font family name {name!r}")
        out.append(name if name in _GENERIC_FAMILIES else f'"{name}"')
    return ", ".join(out)


def parse_font_weight(value: Any) -> str:
    if isinstance(value, str) and value in _FONT_WEIGHTS:
        return str(_FONT_WEIGHTS[value])
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 1000:
        return _num(value)
    raise TokenValueError(f"font weight must be 1-1000 or a DTCG keyword, got {value!r}")


def parse_number(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return _num(value)
    raise TokenValueError(f"not a number: {value!r}")


def parse_cubic_bezier(value: Any) -> str:
    if (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(v, (int, float)) for v in value)
        and 0 <= value[0] <= 1
        and 0 <= value[2] <= 1
    ):
        return "cubic-bezier(" + ", ".join(_num(v) for v in value) + ")"
    raise TokenValueError(f"cubicBezier needs [x1, y1, x2, y2] with x in 0..1, got {value!r}")


def parse_shadow(value: Any, colour_of: Any) -> str:
    layers = value if isinstance(value, list) else [value]
    parts = []
    for layer in layers:
        if not isinstance(layer, dict):
            raise TokenValueError(f"shadow layer must be an object, got {layer!r}")
        try:
            dims = [parse_dimension(layer[k]) for k in ("offsetX", "offsetY", "blur", "spread")]
        except KeyError as exc:
            raise TokenValueError(f"shadow needs {exc.args[0]}") from None
        inset = "inset " if layer.get("inset") is True else ""
        parts.append(f"{inset}{' '.join(dims)} {colour_of(layer.get('color')).css()}")
    return ", ".join(parts)


def _num(number: float) -> str:
    text = f"{number:.4f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"
