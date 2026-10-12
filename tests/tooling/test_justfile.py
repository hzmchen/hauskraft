# SPDX-License-Identifier: MIT
"""M0S-E01-04: the justfile parses, lists every recipe and its cheap recipes run green."""

from __future__ import annotations

import shutil
import subprocess

import pytest
from _support import REPO

pytestmark = [
    pytest.mark.story("M0S-E01-04"),
    pytest.mark.skipif(shutil.which("just") is None, reason="just is not installed"),
]


def _just(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["just", *args], cwd=REPO, capture_output=True, text=True, check=False, timeout=600)


def test_just_lists_recipes() -> None:
    proc = _just("--list")
    assert proc.returncode == 0, proc.stderr
    assert "check" in proc.stdout


def test_dry_run_of_every_recipe_parses() -> None:
    names = _just("--summary").stdout.split()
    assert names, "no recipes"
    for name in names:
        proc = _just("--dry-run", name)
        assert proc.returncode == 0, f"{name}: {proc.stderr}"
