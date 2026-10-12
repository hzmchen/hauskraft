# SPDX-License-Identifier: MIT
"""M0S-E02-05: scripts/check-denylist.mjs rejects lockfiles with compromised package versions."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from _support import REPO

pytestmark = pytest.mark.story("M0S-E02-05")

SCRIPT = REPO / "scripts" / "check-denylist.mjs"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    assert SCRIPT.exists(), "scripts/check-denylist.mjs missing"
    node = shutil.which("node")
    assert node, "node is not installed"
    return subprocess.run([node, str(SCRIPT), *args], cwd=REPO, capture_output=True, text=True, check=False)


def _lock(tmp_path: Path, body: str) -> str:
    path = tmp_path / "pnpm-lock.yaml"
    path.write_text("lockfileVersion: '9.0'\n\n" + body)
    return str(path)


def test_peer_suffixed_versions_are_caught(tmp_path: Path) -> None:
    lock = _lock(
        tmp_path,
        "snapshots:\n  '@tanstack/react-router@1.169.8(react-dom@19.3.0)(react@19.3.0)':\n    dependencies: {}\n",
    )
    proc = _run(lock)
    assert proc.returncode == 1
    assert "@tanstack/react-router@1.169.8" in proc.stdout + proc.stderr


def test_unquoted_keys_are_caught(tmp_path: Path) -> None:
    lock = _lock(tmp_path, "packages:\n  '@tanstack/router-plugin@1.167.38':\n    resolution: {integrity: x}\n")
    assert _run(lock).returncode == 1


def test_neighbouring_versions_pass(tmp_path: Path) -> None:
    lock = _lock(
        tmp_path,
        "packages:\n  '@tanstack/react-router@1.169.50':\n    resolution: {integrity: x}\n"
        "  '@tanstack/react-router@1.170.2':\n    resolution: {integrity: x}\n",
    )
    proc = _run(lock)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_missing_lockfile_is_a_usage_error(tmp_path: Path) -> None:
    assert _run(str(tmp_path / "nope.yaml")).returncode == 2


def test_the_repository_lockfile_is_clean() -> None:
    proc = _run()
    assert proc.returncode == 0, proc.stdout + proc.stderr
