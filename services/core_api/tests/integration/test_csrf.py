# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-03: synchronizer token plus Origin check on every state-changing request."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


def _login(client: TestClient, username: str) -> str:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return str(r.json()["csrf_token"])


def _patch_me(client: TestClient, headers: dict[str, str]):  # type: ignore[no-untyped-def]
    return client.patch("/api/v1/me", json={"locale": "de"}, headers=headers)


def _assert_csrf_failed(r) -> None:  # type: ignore[no-untyped-def]
    assert r.status_code == 403, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "csrf_failed"


def test_missing_token(client: TestClient, make_user: Callable[..., str]) -> None:
    _login(client, make_user())
    _assert_csrf_failed(_patch_me(client, {}))


def test_wrong_token(client: TestClient, make_user: Callable[..., str]) -> None:
    _login(client, make_user())
    _assert_csrf_failed(_patch_me(client, {"X-CSRF-Token": "nope"}))


def test_another_sessions_token(client: TestClient, make_user: Callable[..., str], api_settings) -> None:  # type: ignore[no-untyped-def]
    from hauskraft_core.app import create_app

    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as other:
        other_token = _login(other, make_user())
    _login(client, make_user())
    _assert_csrf_failed(_patch_me(client, {"X-CSRF-Token": other_token}))


def test_foreign_origin_with_valid_token(client: TestClient, make_user: Callable[..., str]) -> None:
    token = _login(client, make_user())
    _assert_csrf_failed(_patch_me(client, {"X-CSRF-Token": token, "Origin": "http://evil.example"}))


def test_happy_path(client: TestClient, make_user: Callable[..., str]) -> None:
    token = _login(client, make_user())
    assert _patch_me(client, {"X-CSRF-Token": token}).status_code == 200


def test_no_origin_header_still_needs_the_token(client: TestClient, make_user: Callable[..., str]) -> None:
    token = _login(client, make_user())
    del client.headers["Origin"]
    assert _patch_me(client, {"X-CSRF-Token": token}).status_code == 200
    _assert_csrf_failed(_patch_me(client, {}))


def test_reads_need_no_token(client: TestClient, make_user: Callable[..., str]) -> None:
    _login(client, make_user())
    assert client.get("/api/v1/me", headers={"Origin": "http://evil.example"}).status_code == 200


def test_login_checks_origin_but_not_token(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user()
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": "http://evil.example"},
    )
    _assert_csrf_failed(r)
    assert client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200


def test_logout_needs_the_token(client: TestClient, make_user: Callable[..., str]) -> None:
    token = _login(client, make_user())
    _assert_csrf_failed(client.post("/api/v1/auth/logout"))
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token}).status_code == 204
