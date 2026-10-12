# SPDX-License-Identifier: MIT
"""Helpers that turn "not built yet" into clear RED failures instead of noisy errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from . import REPO


def require_file(rel: str, story: str) -> Path:
    path = REPO / rel
    if not path.exists():
        pytest.fail(f"RED ({story}): {rel} does not exist yet", pytrace=False)
    return path


def require_json(rel: str, story: str) -> Any:
    path = require_file(rel, story)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"{rel} is not valid JSON: {exc}", pytrace=False)


def require_text(rel: str, story: str) -> str:
    return require_file(rel, story).read_text(encoding="utf-8")
