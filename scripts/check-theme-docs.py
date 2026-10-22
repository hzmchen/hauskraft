#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Doc-test for the theme authoring guide (M0S-E13-09).

    uv run python scripts/check-theme-docs.py [--guide docs/themes.md]

Every ```json block in the guide must follow a marker comment that says where the example belongs:

    <!-- example: manifest | theme | tokens.light | tokens.dark | tokens.both [expect=<error code>] -->

The example is deep-merged into a fresh copy of ``themes/template`` (objects merge, everything else replaces) and the
copy is validated with the real validator. Without ``expect`` the theme must have no errors; with it, that error
code must be reported. Exits 1 on the first broken example or on a JSON block without a marker.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from hauskraft_core.themes.validate import validate_theme

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "themes" / "template"
BLOCK = re.compile(r"(?:<!--\s*example:\s*(?P<marker>[^>]*?)\s*-->\s*\n)?```json\n(?P<body>.*?)\n```", re.S)
TARGETS = {
    "manifest": ["hauskraft.plugin.json"],
    "theme": ["theme.json"],
    "tokens.light": ["tokens.light.json"],
    "tokens.dark": ["tokens.dark.json"],
    "tokens.both": ["tokens.light.json", "tokens.dark.json"],
}


def merge(base: Any, patch: Any) -> Any:
    if isinstance(base, dict) and isinstance(patch, dict):
        return {**base, **{k: merge(base.get(k), v) for k, v in patch.items()}}
    return patch


def check(marker: str, body: str) -> str | None:
    """Return a problem description, or None when the example behaves as documented."""
    target, _, expect = marker.partition(" expect=")
    if target not in TARGETS:
        return f"unknown example target {target!r}"
    try:
        patch = json.loads(body)
    except json.JSONDecodeError as exc:
        return f"not valid JSON: {exc}"
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "example"
        shutil.copytree(TEMPLATE, folder)
        for name in TARGETS[target]:
            path = folder / name
            path.write_text(json.dumps(merge(json.loads(path.read_text()), patch)), encoding="utf-8")
        report = validate_theme(folder)
    codes = {issue.code for issue in report.errors}
    if expect:
        return None if expect in codes else f"expected {expect}, got {sorted(codes) or 'no errors'}"
    if report.errors:
        return "; ".join(f"{i.code} at {i.path}: {i.message}" for i in report.errors)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--guide", type=Path, default=REPO / "docs" / "themes.md")
    args = parser.parse_args(argv)
    text = args.guide.read_text(encoding="utf-8")
    blocks = list(BLOCK.finditer(text))
    failed = 0
    for index, match in enumerate(blocks, 1):
        line = text.count("\n", 0, match.start("body"))
        marker = (match.group("marker") or "").strip()
        problem = check(marker, match.group("body")) if marker else "JSON example without an example marker"
        if problem:
            failed += 1
            print(f"{args.guide}:{line}: example {index}: {problem}")
    if failed or not blocks:
        print(f"{failed} of {len(blocks)} examples failed", file=sys.stderr)
        return 1
    print(f"{len(blocks)} examples OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
