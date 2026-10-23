# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E05-02: members list and end their own sessions; sign out everywhere."""

import datetime as dt
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update

from hauskraft_core.app import create_app
from hauskraft_core.auth.sessions import COOKIE_NAME, token_hash
from hauskraft_core.db.models import Session
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"


@pytest.fixture
def browser(api_settings: Settings) -> Iterator[Callable[..., TestClient]]:
    """Opens further signed-in clients ("browsers") on the same app."""
    opened: list[TestClient] = []

    def _open(username: str, user_agent: str = "python-httpx") -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver", "User-Agent": user_agent})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _sessions(c: TestClient) -> list[dict[str, object]]:
    r = c.get("/api/v1/me/sessions")
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def _set(settings: Settings, token: str, **values: object) -> None:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            conn.execute(update(Session).where(Session.id == token_hash(token)).values(values))
    finally:
        engine.dispose()


def test_list_marks_the_current_session_newest_first(
    browser: Callable[..., TestClient], make_user: Callable[..., str]
) -> None:
    username = make_user()
    laptop = browser(username, FIREFOX)
    phone = browser(username)
    items = _sessions(phone)
    assert [i["current"] for i in items] == [True, False], "the calling session was used last"
    assert [i["device"] for i in items] == ["Unknown device", "Firefox on Linux"]
    for item in items:
        assert set(item) == {"id", "device", "created_at", "last_seen_at", "current"}
    assert [i["current"] for i in _sessions(laptop)].count(True) == 1


def test_list_hides_revoked_expired_and_idle_sessions(
    browser: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user()
    me = browser(username)
    gone = [browser(username) for _ in range(3)]
    tokens = [c.cookies.get(COOKIE_NAME) or "" for c in gone]
    past = dt.datetime.now(dt.UTC) - dt.timedelta(days=30)
    _set(api_settings, tokens[0], revoked_at=past)
    _set(api_settings, tokens[1], expires_at=past)
    _set(api_settings, tokens[2], last_seen_at=past)
    assert len(_sessions(me)) == 1


def test_the_list_leaks_no_secrets(browser: Callable[..., TestClient], make_user: Callable[..., str]) -> None:
    me = browser(make_user())
    raw = me.get("/api/v1/me/sessions").text
    token = me.cookies.get(COOKIE_NAME) or ""
    assert token
    assert token not in raw
    assert token_hash(token) not in raw
    assert me.headers["X-CSRF-Token"] not in raw
    assert "127.0.0.1" not in raw
    assert "testclient" not in raw


def test_end_my_other_session(browser: Callable[..., TestClient], make_user: Callable[..., str]) -> None:
    username = make_user()
    me, other = browser(username), browser(username)
    target = next(i for i in _sessions(me) if not i["current"])
    assert me.delete(f"/api/v1/me/sessions/{target['id']}").status_code == 204
    assert other.get("/api/v1/me").status_code == 401
    assert [i["id"] for i in _sessions(me)] != []
    assert target["id"] not in [i["id"] for i in _sessions(me)]
    assert me.delete(f"/api/v1/me/sessions/{target['id']}").status_code == 404, "already ended"


def test_cannot_end_someone_elses_or_unknown_sessions(
    browser: Callable[..., TestClient], make_user: Callable[..., str]
) -> None:
    me, them = browser(make_user()), browser(make_user())
    theirs = _sessions(them)[0]["id"]
    for target in (theirs, "does-not-exist", "00000000-0000-0000-0000-000000000000"):
        r = me.delete(f"/api/v1/me/sessions/{target}")
        assert r.status_code == 404, (target, r.text)
        assert r.json()["code"] == "not_found"
    assert them.get("/api/v1/me").status_code == 200


def test_sign_out_everywhere(
    browser: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user()
    me, other = browser(username), browser(username)
    token = me.cookies.get(COOKIE_NAME) or ""
    r = me.post("/api/v1/auth/logout-everywhere")
    assert r.status_code == 204, r.text
    assert COOKIE_NAME in r.headers.get("set-cookie", "")
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert other.get("/api/v1/auth/session").status_code == 401
    engine = create_engine(api_settings.database_url)
    try:
        with engine.connect() as conn:
            revoked = conn.scalar(select(Session.revoked_at).where(Session.id == token_hash(token)))
    finally:
        engine.dispose()
    assert revoked is not None


def test_session_endpoints_need_a_session(client: TestClient) -> None:
    assert client.get("/api/v1/me/sessions").status_code == 401
    assert client.post("/api/v1/auth/logout-everywhere").status_code == 401
