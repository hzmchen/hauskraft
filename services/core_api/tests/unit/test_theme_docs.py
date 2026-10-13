# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E13-09: every JSON example in docs/themes.md validates when applied to the template theme."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]


def test_guide_examples_validate() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check-theme-docs.py")], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "examples OK" in result.stdout
