# SPDX-License-Identifier: MIT
"""Relative Markdown links in the repo's docs resolve to real files."""

from __future__ import annotations

import re

import pytest

from _support import REPO

pytestmark = pytest.mark.meta

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
DOCS = sorted(p for p in [*REPO.glob("*.md"), *(REPO / "docs").rglob("*.md"), *(REPO / "tests").rglob("*.md")]
              if "node_modules" not in p.parts)


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(REPO)))
def test_relative_links_resolve(path) -> None:
    broken = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        file_part = target.split("#", 1)[0]
        if file_part and not (path.parent / file_part).resolve().exists():
            broken.append(target)
    assert not broken, f"{path.relative_to(REPO)}: broken links {broken}"
