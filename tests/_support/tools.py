# SPDX-License-Identifier: MIT
"""Run repo tooling (ruff, eslint, node, python scripts) as black boxes."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from . import REPO


def _cmd(env_var: str, candidates: list[list[str]], story: str) -> list[str]:
    if os.environ.get(env_var):
        return shlex.split(os.environ[env_var])
    for cand in candidates:
        if shutil.which(cand[0]) and (cand[0] not in ("uv", "pnpm") or (REPO / ("pyproject.toml" if cand[0] == "uv" else "package.json")).exists()):
            return cand
    pytest.fail(f"RED ({story}): no tool available ({env_var} unset; tried {[c[0] for c in candidates]})", pytrace=False)


def run(cmd: list[str], stdin: str | None = None, timeout: float = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO, input=stdin, capture_output=True, text=True, timeout=timeout, check=False)


def ruff_on_stdin(source: str, as_path: str, story: str) -> list[dict[str, Any]]:
    """Lint `source` as if it lived at `as_path` (so per-file config applies)."""
    if not (REPO / "pyproject.toml").exists():
        pytest.fail(f"RED ({story}): no root pyproject.toml with ruff config yet", pytrace=False)
    base = _cmd("HAUSKRAFT_RUFF", [["ruff"], ["uv", "run", "--quiet", "ruff"]], story)
    proc = run([*base, "check", "--no-cache", "--output-format", "json", "--stdin-filename", as_path, "-"], stdin=source)
    if proc.returncode not in (0, 1):
        pytest.fail(f"ruff failed ({proc.returncode}): {proc.stderr[:500]}", pytrace=False)
    return json.loads(proc.stdout or "[]")


def eslint_on_stdin(source: str, as_path: str, story: str) -> list[dict[str, Any]]:
    """Lint `source` as if it lived at `as_path`; returns ESLint messages."""
    if not (REPO / "node_modules").exists():
        pytest.fail(f"RED ({story}): run `pnpm install` first (no node_modules)", pytrace=False)
    base = _cmd("HAUSKRAFT_ESLINT", [["pnpm", "exec", "eslint"]], story)
    proc = run([*base, "--format", "json", "--stdin", "--stdin-filename", as_path], stdin=source)
    if proc.returncode not in (0, 1):
        pytest.fail(f"eslint failed ({proc.returncode}): {proc.stderr[:500]}", pytrace=False)
    results = json.loads(proc.stdout or "[]")
    return [m for r in results for m in r.get("messages", [])]


def node_script(rel: str, *args: str, story: str) -> subprocess.CompletedProcess[str]:
    script = REPO / rel
    if not script.exists():
        pytest.fail(f"RED ({story}): {rel} does not exist yet", pytrace=False)
    if not shutil.which("node"):
        pytest.fail("node is not installed", pytrace=False)
    return run(["node", str(script), *args])


def python_script(rel: str, *args: str, story: str) -> subprocess.CompletedProcess[str]:
    script = REPO / rel
    if not script.exists():
        pytest.fail(f"RED ({story}): {rel} does not exist yet", pytrace=False)
    return run([sys.executable, str(script), *args])


def rel_to_repo(path: Path) -> str:
    return str(path.relative_to(REPO))
