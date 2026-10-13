#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the Hackspace theme's icon sprite from Pixelarticons (MIT) (M0S-E13-06). One-off; output is committed.

    npm pack pixelarticons@2.4.2 && tar xzf pixelarticons-2.4.2.tgz
    uv run python scripts/build-hackspace-icons.py package/svg

Writes ``themes/builtin/hackspace/assets/icons/sprite.svg`` with one ``<symbol>`` per core icon name
(``packages/schemas/theme/icon-names-v1.json``), keeping only each icon's ``<path d>`` so the sprite passes
the theme validator's SVG allowlist. The downloaded SVGs are parsed with ``defusedxml``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from defusedxml import ElementTree as SafeET

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "themes" / "builtin" / "hackspace" / "assets" / "icons" / "sprite.svg"
SVG_NS = "http://www.w3.org/2000/svg"

# core icon name -> Pixelarticons icon
ICONS = {
    "nav.today": "calendar",
    "nav.tasks": "list-box",
    "nav.activity": "analytics",
    "nav.settings": "sliders",
    "action.add": "plus",
    "action.edit": "pencil",
    "action.delete": "trash",
    "action.confirm": "check",
    "action.cancel": "close",
    "status.done": "checkbox-on",
    "status.due": "clock",
    "status.overdue": "alarm-clock",
    "user.menu": "user",
    "mode.system": "monitor",
    "mode.light": "sun",
    "mode.dark": "moon",
    "widget.unavailable": "warning-diamond",
}


def main(source: Path) -> None:
    core = json.loads((REPO / "packages" / "schemas" / "theme" / "icon-names-v1.json").read_text())["icons"]
    if sorted(core) != sorted(ICONS):
        raise SystemExit(f"mapping does not match icon-names-v1.json: {sorted(set(core) ^ set(ICONS))}")
    lines = [f'<svg xmlns="{SVG_NS}">']
    for name in core:
        root = SafeET.parse(source / f"{ICONS[name]}.svg").getroot()
        paths = [el.get("d") for el in root.iter(f"{{{SVG_NS}}}path")]
        if not paths or any(d is None for d in paths):
            raise SystemExit(f"{ICONS[name]}.svg: expected only <path d> elements")
        body = "".join(f'<path d="{d}"/>' for d in paths)
        lines.append(f'  <symbol id="{name}" viewBox="0 0 24 24" fill="currentColor">{body}</symbol>')
    lines.append("</svg>")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{TARGET.relative_to(REPO)}: {len(core)} symbols")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
