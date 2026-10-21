# SPDX-License-Identifier: MIT
"""M0S-E01-02: plugins may import only hauskraft_sdk, never core internals (ruff TID251).

Runs ruff on stdin as if the probe lived at different paths, so the per-path configuration applies.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from _support import REPO

pytestmark = pytest.mark.story("M0S-E01-02")

PLUGIN_PROBE = "from hauskraft_core.db import models\n\n__all__ = ['models']\n"
SDK_PROBE = "from hauskraft_sdk import Plugin\n\n__all__ = ['Plugin']\n"


def _codes(source: str, as_path: str) -> set[str]:
    ruff = shutil.which("ruff") or str(REPO / ".venv" / "bin" / "ruff")
    proc = subprocess.run(
        [ruff, "check", "--no-cache", "--output-format", "json", "--stdin-filename", as_path, "-"],
        cwd=REPO,
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr
    return {f["code"] for f in json.loads(proc.stdout or "[]")}


@pytest.mark.parametrize(
    "as_path",
    [
        "plugins/official/tasks/backend/src/hauskraft_tasks/service.py",
        "plugins/official/tasks/backend/tests/test_service.py",
        "plugins/community/example/backend/src/example/plugin.py",
    ],
)
def test_core_import_is_banned_in_plugins(as_path: str) -> None:
    assert "TID251" in _codes(PLUGIN_PROBE, as_path)


@pytest.mark.parametrize(
    "as_path",
    [
        "services/core_api/src/hauskraft_core/app.py",
        "services/core_api/tests/unit/test_app.py",
    ],
)
def test_core_import_is_allowed_outside_plugins(as_path: str) -> None:
    assert "TID251" not in _codes(PLUGIN_PROBE, as_path)


def test_plugins_may_import_the_sdk() -> None:
    assert "TID251" not in _codes(SDK_PROBE, "plugins/official/tasks/backend/src/hauskraft_tasks/plugin.py")
