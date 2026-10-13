#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# /// script
# requires-python = ">=3.13"
# dependencies = ["fonttools[woff]==4.60.1"]
# ///
"""Build the built-in themes' self-hosted fonts (M0S-E13-06). One-off; the output is committed.

    uv run scripts/subset-fonts.py

Downloads each OFL-1.1 font from google/fonts at a pinned commit, checks its SHA-256, pins optical-size axes
to their default, subsets to Latin + Latin Extended (enough for German and most European languages) and
writes WOFF2 into ``themes/builtin/<theme>/assets/fonts/``. It also writes the OFL text to
``themes/builtin/<theme>/LICENSES/OFL-1.1.txt``; each font's copyright line lives in REUSE.toml.
``fonttools`` comes from the inline metadata above, so it is not a dependency of the workspace.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

REPO = Path(__file__).resolve().parents[1]
COMMIT = "66928797f271fed5ee428544e7229685e2d90127"  # google/fonts, 2026-10
RAW = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/"

# Google Fonts' "latin" and "latin-ext" unicode ranges, merged.
UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,"
    "U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD,"
    "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,"
    "U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"
)

# (theme, source path in google/fonts, output file name)
FONTS = [
    ("default", "ofl/inter/Inter%5Bopsz,wght%5D.ttf", "Inter-Variable.woff2"),
    ("paper", "ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf", "SourceSerif4-Variable.woff2"),
    (
        "paper",
        "ofl/atkinsonhyperlegiblenext/AtkinsonHyperlegibleNext%5Bwght%5D.ttf",
        "AtkinsonHyperlegibleNext-Variable.woff2",
    ),
    ("hackspace", "ofl/vt323/VT323-Regular.ttf", "VT323-Regular.woff2"),
    ("hackspace", "ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", "JetBrainsMono-Variable.woff2"),
]
# The licence text without the font-specific copyright line; REUSE.toml carries each font's copyright.
OFL_SOURCE = "ofl/inter/OFL.txt"
SHA256 = {
    "ofl/inter/Inter%5Bopsz,wght%5D.ttf": "29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031",
    "ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf": (
        "97b2d4da6e3cb494b5a1e66ae176914d852ccabef49e0c02c0df25f3e39aca0b"
    ),
    "ofl/atkinsonhyperlegiblenext/AtkinsonHyperlegibleNext%5Bwght%5D.ttf": (
        "5a455d1cfa099b601ab70751bb9673e8fe1854dc4500c80e1a220d0d75e31745"
    ),
    "ofl/vt323/VT323-Regular.ttf": "cf4de751ada78ceac033dbe16a687742939995b77bc2a052ae17a4957958594d",
    "ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf": "48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda",
}


def fetch(path: str) -> bytes:
    with urllib.request.urlopen(RAW + path, timeout=60) as response:  # noqa: S310 - fixed https URL
        data: bytes = response.read()
    expected = SHA256.get(path)
    actual = hashlib.sha256(data).hexdigest()
    if expected is not None and actual != expected:
        raise SystemExit(f"{path}: sha256 {actual} does not match the pinned {expected}")
    return data


def build(source: bytes) -> bytes:
    """Deterministic: the same source gives byte-identical output (no fresh timestamps)."""
    font = TTFont(io.BytesIO(source), recalcTimestamp=False)
    if "fvar" in font and any(a.axisTag == "opsz" for a in font["fvar"].axes):
        pinned = io.BytesIO()
        instancer.instantiateVariableFont(font, {"opsz": None}).save(pinned)
        # reload, so the subsetter sees consistent tables
        font = TTFont(io.BytesIO(pinned.getvalue()), recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
    subsetter.subset(font)
    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    return out.getvalue()


def main() -> None:
    for theme, path, name in FONTS:
        target = REPO / "themes" / "builtin" / theme / "assets" / "fonts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(build(fetch(path)))
        print(f"{target.relative_to(REPO)}: {target.stat().st_size // 1024} KiB")
    lines = fetch(OFL_SOURCE).decode("utf-8").splitlines()
    text = "\n".join(lines[next(i for i, line in enumerate(lines) if line.startswith("This Font Software")) :])
    for theme in sorted({theme for theme, _, _ in FONTS}):
        target = REPO / "themes" / "builtin" / theme / "LICENSES" / "OFL-1.1.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
