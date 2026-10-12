# SPDX-License-Identifier: MIT
"""Run the `hearthos` CLI (M0S-E05-05, M0S-E13-09) as a black box.

Override the command with HEARTHOS_CLI, e.g. HEARTHOS_CLI="uv run hearthos".
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

import pytest

from . import REPO


@dataclass
class CliResult:
    code: int
    stdout: str
    stderr: str

    def json(self) -> Any:
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"CLI did not print JSON.\nstdout:\n{self.stdout}\nstderr:\n{self.stderr}", pytrace=False)


def _base_command() -> list[str]:
    configured = os.environ.get("HEARTHOS_CLI")
    if configured:
        return shlex.split(configured)
    if shutil.which("hearthos"):
        return ["hearthos"]
    if shutil.which("uv") and (REPO / "pyproject.toml").exists():
        return ["uv", "run", "--quiet", "hearthos"]
    pytest.fail("RED: no `hearthos` CLI found (set HEARTHOS_CLI or implement M0S-E05-05/M0S-E13-09)",
                pytrace=False)


def run(*args: str, timeout: float = 120) -> CliResult:
    cmd = [*_base_command(), *args]
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        pytest.fail(f"RED: cannot run {cmd[0]!r}: {exc}", pytrace=False)
    return CliResult(proc.returncode, proc.stdout, proc.stderr)
