# SPDX-License-Identifier: MIT
"""Independent colour maths for the acceptance suite.

The theme validator (M0S-E13-03) must implement these rules itself. The suite keeps its
own small implementation so fixtures and built-in themes can be checked independently
of the code under test. Supported inputs: hex (#rgb, #rgba, #rrggbb, #rrggbbaa),
``rgb()/rgba()`` with 0-255 channels, and DTCG 2025.10 colour objects in the sRGB space.
"""

from __future__ import annotations

import math
import re
from typing import Any

RGBA = tuple[float, float, float, float]  # 0..1 each

_HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB = re.compile(r"^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$")


class ColourError(ValueError):
    pass


def parse(value: Any) -> RGBA:
    """Parse a token colour value into linear-free sRGB 0..1 floats plus alpha."""
    if isinstance(value, dict):
        if value.get("colorSpace") != "srgb":
            raise ColourError(f"only sRGB DTCG colours are supported here, got {value!r}")
        comps = value.get("components")
        if not (isinstance(comps, list) and len(comps) == 3):
            raise ColourError(f"bad DTCG components in {value!r}")
        r, g, b = (float(c) for c in comps)
        a = float(value.get("alpha", 1))
        return (r, g, b, a)
    if not isinstance(value, str):
        raise ColourError(f"not a colour: {value!r}")
    s = value.strip()
    m = _HEX.match(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b, a)
    m = _RGB.match(s)
    if m:
        r, g, b = (float(m.group(i)) / 255 for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    raise ColourError(f"unsupported colour syntax: {value!r}")


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    """Alpha-composite fg over an opaque bg."""
    a = fg[3]
    return (
        fg[0] * a + bg[0] * (1 - a),
        fg[1] * a + bg[1] * (1 - a),
        fg[2] * a + bg[2] * (1 - a),
        1.0,
    )


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(c: RGBA) -> float:
    r, g, b = (_lin(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: Any, bg: Any) -> float:
    """WCAG 2.x contrast ratio; fg with alpha is composited over bg."""
    b = parse(bg)
    if b[3] < 1:
        b = composite(b, (1.0, 1.0, 1.0, 1.0))
    f = composite(parse(fg), b)
    l1, l2 = sorted((relative_luminance(f), relative_luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def to_oklab(c: RGBA) -> tuple[float, float, float]:
    r, g, b = (_lin(x) for x in c[:3])
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_distance(a: Any, b: Any) -> float:
    la, lb = to_oklab(parse(a)), to_oklab(parse(b))
    return math.dist(la, lb)
