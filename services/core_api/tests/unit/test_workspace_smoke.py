# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke test for the uv workspace (M0S-E01-01): every member package imports."""

import importlib

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("module", ["hauskraft_core", "hauskraft_sdk", "hauskraft_tasks"])
def test_workspace_package_imports(module: str) -> None:
    assert importlib.import_module(module).__name__ == module
