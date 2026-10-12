# SPDX-License-Identifier: MIT
"""M0S-E03-05 · The committed OpenAPI 3.1 file covers every endpoint the backlog defines."""

from __future__ import annotations

import re

import pytest

from _support.red import require_json

story = pytest.mark.story
OPENAPI = "packages/schemas/openapi/core-api.openapi.json"


def _operations() -> dict[tuple[str, str], dict]:
    doc = require_json(OPENAPI, "M0S-E03-05")
    ops = {}
    for path, item in doc.get("paths", {}).items():
        norm = re.sub(r"\{[^}]+\}", "{}", path.removeprefix("/api/v1"))
        for method, op in item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                ops[(method.upper(), norm)] = op
    return ops


@story("M0S-E03-05")
def test_openapi_version_is_3_1() -> None:
    assert str(require_json(OPENAPI, "M0S-E03-05").get("openapi", "")).startswith("3.1")


ENDPOINTS = [
    ("M0S-E03-02", "GET", "/healthz"), ("M0S-E03-02", "GET", "/readyz"),
    ("M0S-E05-02", "POST", "/auth/login"), ("M0S-E05-02", "POST", "/auth/logout"),
    ("M0S-E05-02", "GET", "/auth/session"), ("M0S-E05-02", "GET", "/me"), ("M0S-E05-02", "PATCH", "/me"),
    ("M0S-E05-05", "POST", "/users"),
    ("M0S-E06-04", "GET", "/plugins"), ("M0S-E06-04", "PATCH", "/plugins/{}"),
    ("M0S-E07-03", "GET", "/tasks"), ("M0S-E07-03", "POST", "/tasks"), ("M0S-E07-03", "GET", "/tasks/{}"),
    ("M0S-E07-03", "PATCH", "/tasks/{}"), ("M0S-E07-03", "DELETE", "/tasks/{}"),
    ("M0S-E08-06", "GET", "/dashboard/{}"), ("M0S-E08-06", "PUT", "/dashboard/{}"),
    ("M0S-E10-03", "GET", "/activity"),
    ("M0S-E13-04", "GET", "/themes"), ("M0S-E13-04", "GET", "/theme"), ("M0S-E13-04", "GET", "/theme/active.css"),
    ("M0S-E13-04", "GET", "/theme/assets/{}/{}"), ("M0S-E13-04", "PUT", "/settings/theme"),
]


@pytest.mark.parametrize(("sid", "method", "path"),
                         [pytest.param(*e, marks=story("M0S-E03-05", e[0]), id=f"{e[1]} {e[2]}") for e in ENDPOINTS])
def test_endpoint_is_in_contract(sid: str, method: str, path: str) -> None:
    ops = _operations()
    alt = path.replace("/{}", "/today") if path.startswith("/dashboard") else path
    assert (method, path) in ops or (method, alt) in ops, f"{method} /api/v1{path} missing from {OPENAPI}"


OPERATION_IDS = [
    ("M0S-E07-03", "tasks_list"), ("M0S-E07-03", "tasks_create"), ("M0S-E07-03", "tasks_get"),
    ("M0S-E07-03", "tasks_update"), ("M0S-E07-03", "tasks_delete"),
    ("M0S-E13-04", "themes_list"), ("M0S-E13-04", "settings_theme_set"),
]


@pytest.mark.parametrize(("sid", "op_id"),
                         [pytest.param(*o, marks=story("M0S-E03-05", o[0]), id=o[1]) for o in OPERATION_IDS])
def test_operation_id_is_stable(sid: str, op_id: str) -> None:
    ids = {op.get("operationId") for op in _operations().values()}
    assert op_id in ids, f"operationId {op_id!r} missing (generated client names depend on it)"


@story("M0S-E03-05")
def test_operation_ids_are_unique() -> None:
    ids = [op.get("operationId") for op in _operations().values()]
    assert len(ids) == len(set(ids)), "duplicate operationIds"
