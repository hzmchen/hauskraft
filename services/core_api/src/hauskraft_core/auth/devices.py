# SPDX-License-Identifier: AGPL-3.0-or-later
"""Short device descriptions for the sessions list (M1S-E05-02), such as "Firefox on Linux".

A deliberately small User-Agent reading without a parser dependency: the first matching browser and system win,
and anything unrecognised is "Unknown device".
"""

from __future__ import annotations

UNKNOWN_DEVICE = "Unknown device"

# Order matters: Edge and Opera also say "Chrome", Chrome also says "Safari", iOS browsers say "Mac OS X".
_BROWSERS = (
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("FxiOS/", "Firefox"),
    ("Firefox/", "Firefox"),
    ("CriOS/", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)
_SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("CrOS", "ChromeOS"),
    ("Windows", "Windows"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
)


def _first(user_agent: str, table: tuple[tuple[str, str], ...]) -> str | None:
    return next((name for marker, name in table if marker in user_agent), None)


def describe(user_agent: str | None) -> str:
    ua = (user_agent or "").strip()
    browser, system = _first(ua, _BROWSERS), _first(ua, _SYSTEMS)
    if browser and system:
        return f"{browser} on {system}"
    if system:
        return f"Browser on {system}"
    return browser or UNKNOWN_DEVICE
