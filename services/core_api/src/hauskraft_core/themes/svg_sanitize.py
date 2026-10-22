# SPDX-License-Identifier: AGPL-3.0-or-later
"""SVG allowlist check for theme sprites and images (M0S-E13-03, spec §11.1)."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as SafeET

ALLOWED_ELEMENTS = {
    "svg",
    "symbol",
    "g",
    "defs",
    "title",
    "desc",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "use",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "mask",
}
ALLOWED_ATTRIBUTES = {
    "id",
    "viewBox",
    "width",
    "height",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "d",
    "points",
    "fill",
    "fill-rule",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-opacity",
    "stroke-dasharray",
    "opacity",
    "transform",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientUnits",
    "gradientTransform",
    "clip-path",
    "clip-rule",
    "mask",
    "href",
    "preserveAspectRatio",
    "shape-rendering",
    "version",
    "xmlns",
    "aria-hidden",
    "role",
    "class",
}
_LOCAL_URL = re.compile(r"url\(\s*#[A-Za-z0-9_.:-]+\s*\)")


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def problems(path: Path) -> list[str]:
    """Return what makes the SVG unsafe (empty if it is fine)."""
    try:
        root = SafeET.parse(path).getroot()
    except Exception as exc:  # defusedxml raises for entities, DTDs and malformed XML
        return [f"not a safe, well-formed SVG ({type(exc).__name__})"]
    if root is None:
        return ["empty SVG document"]
    found: list[str] = []
    elements: list[Element] = list(root.iter())
    for el in elements:
        tag = _local(el.tag)
        if tag not in ALLOWED_ELEMENTS:
            found.append(f"element <{tag}> is not allowed")
        for raw_name, value in el.attrib.items():
            name = _local(raw_name)
            if name.lower().startswith("on"):
                found.append(f"event handler {name!r} on <{tag}>")
            elif name not in ALLOWED_ATTRIBUTES:
                found.append(f"attribute {name!r} on <{tag}> is not allowed")
            elif name == "href" and not value.startswith("#"):
                found.append(f"external reference {value!r} on <{tag}>")
            if "url(" in value and _LOCAL_URL.sub("", value).count("url(") > 0:
                found.append(f"url() outside the document on <{tag}>")
            if "javascript:" in value.lower():
                found.append(f"script URL on <{tag}>")
        if el.text and tag not in ("title", "desc") and el.text.strip():
            found.append(f"text content in <{tag}>")
    return sorted(set(found))


def symbol_ids(path: Path) -> list[str]:
    root = SafeET.parse(path).getroot()
    if root is None:
        return []
    return [el.attrib["id"] for el in root.iter() if _local(el.tag) == "symbol" and "id" in el.attrib]
