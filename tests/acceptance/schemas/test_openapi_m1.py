# SPDX-License-Identifier: MIT
"""M1* endpoints in the committed OpenAPI 3.1 contract (backlog docs/backlog/m1-star/, API tables per epic)."""

from __future__ import annotations

import re

import pytest

from _support.red import require_json

story = pytest.mark.story
OPENAPI = "packages/schemas/openapi/core-api.openapi.json"


def _doc(sid: str) -> dict:
    return require_json(OPENAPI, sid)


def _operations(sid: str) -> dict[tuple[str, str], dict]:
    ops = {}
    for path, item in _doc(sid).get("paths", {}).items():
        norm = re.sub(r"\{[^}]+\}", "{}", path.removeprefix("/api/v1"))
        for method, op in item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                ops[(method.upper(), norm)] = op
    return ops


ENDPOINTS = [
    ("M1S-E03-01", "GET", "/setup"), ("M1S-E03-01", "POST", "/setup"),
    ("M1S-E04-01", "GET", "/household"), ("M1S-E04-01", "PATCH", "/household"),
    ("M1S-E05-01", "POST", "/me/password"),
    ("M1S-E05-02", "GET", "/me/sessions"), ("M1S-E05-02", "DELETE", "/me/sessions/{}"),
    ("M1S-E05-02", "POST", "/auth/logout-everywhere"),
    ("M1S-E06-01", "GET", "/users"), ("M1S-E06-01", "GET", "/users/{}"),
    ("M1S-E06-02", "PATCH", "/users/{}"),
    ("M1S-E06-03", "POST", "/users/{}/deactivate"), ("M1S-E06-03", "POST", "/users/{}/reactivate"),
    ("M1S-E06-04", "POST", "/users/{}/password"),
]


@pytest.mark.parametrize(("sid", "method", "path"),
                         [pytest.param(*e, marks=story(e[0]), id=f"{e[1]} {e[2]}") for e in ENDPOINTS])
def test_endpoint_is_in_contract(sid: str, method: str, path: str) -> None:
    assert (method, path) in _operations(sid), f"{method} /api/v1{path} missing from {OPENAPI}"


def _schema(sid: str, name: str) -> dict:
    schemas = _doc(sid).get("components", {}).get("schemas", {})
    hit = next((s for key, s in schemas.items() if key == name or key.endswith(name)), None)
    assert hit is not None, f"component schema {name!r} missing from {OPENAPI}"
    return hit


@story("M1S-E02-04")
def test_session_has_permissions() -> None:
    assert "permissions" in _schema("M1S-E02-04", "SessionOut").get("properties", {})


@story("M1S-E07-01")
def test_user_has_must_change_password() -> None:
    assert "must_change_password" in _schema("M1S-E07-01", "UserOut").get("properties", {})


@story("M1S-E06-01")
def test_member_schema_has_no_secrets() -> None:
    props = set(_schema("M1S-E06-01", "MemberOut").get("properties", {}))
    assert {"is_active", "created_at", "last_login_at", "must_change_password"} <= props
    assert not props & {"password", "password_hash", "sessions", "ip"}


@story("M1S-E02-02")
def test_user_create_accepts_role() -> None:
    assert "role" in _schema("M1S-E02-02", "UserCreate").get("properties", {})
