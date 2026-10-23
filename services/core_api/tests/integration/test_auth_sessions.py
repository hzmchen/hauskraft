# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-02: login, logout, sliding sessions, /auth/session, /me and the login rate limit."""

import datetime as dt
import hashlib
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update

from hauskraft_core.db.models import Session
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


def _login(client: TestClient, username: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _session_row(settings: Settings, token: str) -> Session:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            row = conn.execute(select(Session).where(Session.id == hashlib.sha256(token.encode()).hexdigest()))
            return row.one()  # type: ignore[return-value]
    finally:
        engine.dispose()


def _age_session(settings: Settings, token: str, **values: dt.datetime) -> None:
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(update(Session).where(Session.id == hashlib.sha256(token.encode()).hexdigest()).values(values))
    engine.dispose()


def test_login_sets_a_hardened_cookie_and_returns_the_session(
    client: TestClient, make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user("Demo Adult")
    r = _login(client, username.upper())
    assert r.status_code == 200, r.text
    cookie = r.headers["set-cookie"]
    low = cookie.lower()
    assert cookie.startswith("hauskraft_session=")
    assert "httponly" in low
    assert "samesite=lax" in low
    assert "path=/" in low
    assert "secure" not in low
    body = r.json()
    assert body["user"] == {
        "id": body["user"]["id"],
        "username": username,
        "display_name": "Demo Adult",
        "role": "adult",
        "locale": "en",
    }
    assert len(body["csrf_token"]) >= 32
    token = client.cookies["hauskraft_session"]
    assert len(token) >= 43, "256-bit random token"
    row = _session_row(api_settings, token)
    assert row.id == hashlib.sha256(token.encode()).hexdigest(), "only the hash is stored"
    assert row.csrf_token == body["csrf_token"]
    expires = dt.datetime.fromisoformat(body["expires_at"])
    assert dt.timedelta(days=13) < expires - dt.datetime.now(dt.UTC) <= dt.timedelta(days=14)


def test_secure_flag_follows_the_setting(api_settings: Settings, make_user: Callable[..., str]) -> None:
    from hauskraft_core.app import create_app

    username = make_user()
    secure = api_settings.model_copy(update={"cookie_secure": True})
    with TestClient(create_app(secure), headers={"Origin": "http://testserver"}) as client:
        assert "secure" in _login(client, username).headers["set-cookie"].lower()


def test_session_logout_and_401(client: TestClient, make_user: Callable[..., str]) -> None:
    _login(client, make_user())
    assert client.get("/api/v1/auth/session").status_code == 200
    csrf = client.get("/api/v1/auth/session").json()["csrf_token"]
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    r = client.get("/api/v1/auth/session")
    assert r.status_code == 401
    assert r.json()["code"] == "unauthenticated"


def test_login_rotates_the_session(client: TestClient, make_user: Callable[..., str], api_settings: Settings) -> None:
    username = make_user()
    _login(client, username)
    first = client.cookies["hauskraft_session"]
    _login(client, username)
    second = client.cookies["hauskraft_session"]
    assert first != second
    assert _session_row(api_settings, first).revoked_at is not None


def test_wrong_password_and_unknown_user_look_the_same(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user()
    a = _login(client, username, "definitely-wrong-password")
    b = _login(client, "nobody-at-all", "definitely-wrong-password")
    strip = lambda body: {k: v for k, v in body.items() if k != "request_id"}  # noqa: E731
    assert a.status_code == b.status_code == 401
    assert strip(a.json()) == strip(b.json())
    assert a.json()["code"] == "invalid_credentials"


def test_rate_limit_after_five_failures_and_reset_on_success(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user()
    for _ in range(5):
        assert _login(client, username, "wrong-password-123").status_code == 401
    limited = _login(client, username, "wrong-password-123")
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) > 0
    assert _login(client, username).status_code == 429, "even the right password waits"


def test_idle_sessions_expire(client: TestClient, make_user: Callable[..., str], api_settings: Settings) -> None:
    _login(client, make_user())
    token = client.cookies["hauskraft_session"]
    _age_session(api_settings, token, last_seen_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=8))
    assert client.get("/api/v1/auth/session").status_code == 401


def test_expired_sessions_are_rejected(
    client: TestClient, make_user: Callable[..., str], api_settings: Settings
) -> None:
    _login(client, make_user())
    token = client.cookies["hauskraft_session"]
    _age_session(api_settings, token, expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1))
    assert client.get("/api/v1/auth/session").status_code == 401


def test_activity_slides_the_expiry(client: TestClient, make_user: Callable[..., str], api_settings: Settings) -> None:
    _login(client, make_user())
    token = client.cookies["hauskraft_session"]
    old = dt.datetime.now(dt.UTC) - dt.timedelta(days=2)
    _age_session(api_settings, token, last_seen_at=old, expires_at=old + dt.timedelta(days=14))
    assert client.get("/api/v1/auth/session").status_code == 200
    row = _session_row(api_settings, token)
    assert row.last_seen_at > old + dt.timedelta(days=1)
    assert row.expires_at > dt.datetime.now(dt.UTC) + dt.timedelta(days=13)


def test_me_read_and_update(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user("Me Adult")
    csrf = _login(client, username).json()["csrf_token"]
    me = client.get("/api/v1/me").json()
    assert me["username"] == username
    assert me["locale"] == "en"
    r = client.patch(
        "/api/v1/me", json={"locale": "de", "display_name": "  Me Erwachsen "}, headers={"X-CSRF-Token": csrf}
    )
    assert r.status_code == 200, r.text
    assert r.json()["locale"] == "de"
    assert r.json()["display_name"] == "Me Erwachsen"
    for bad in ({"locale": "fr"}, {"role": "owner"}, {"display_name": ""}):
        res = client.patch("/api/v1/me", json=bad, headers={"X-CSRF-Token": csrf})
        assert res.status_code == 422, bad


def test_protected_routes_need_a_session(client: TestClient) -> None:
    for method, path in (
        ("GET", "/api/v1/me"),
        ("PATCH", "/api/v1/me"),
        ("GET", "/api/v1/auth/session"),
        ("POST", "/api/v1/auth/logout"),
    ):
        assert client.request(method, path).status_code == 401, path


@pytest.mark.parametrize("role", ["owner", "adult"])
def test_session_lists_the_role_permissions(client: TestClient, make_user: Callable[..., str], role: str) -> None:
    """M1S-E02-04: login and /auth/session carry the actions the role may do, from the policy table."""
    from hauskraft_core.policy import permissions_for

    login = _login(client, make_user(role=role))
    assert login.json()["permissions"] == permissions_for(role)
    assert client.get("/api/v1/auth/session").json()["permissions"] == permissions_for(role)
