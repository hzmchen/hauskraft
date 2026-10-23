# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E05-01: members change their own password and display name; both are account events (ADR 0018)."""

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import OutboxEvent, User
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

NEW_PASSWORD = "a-brand-new-passphrase"


@pytest.fixture
def browser(api_settings: Settings) -> Iterator[Callable[..., TestClient]]:
    opened: list[TestClient] = []

    def _open(username: str, password: str = PASSWORD) -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _user(settings: Settings, username: str) -> User:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            return conn.execute(select(User).where(User.username == username)).one()  # type: ignore[return-value]
    finally:
        engine.dispose()


def _events(settings: Settings, username: str) -> list[dict[str, Any]]:
    """The account's events after its creation (user.created comes with every account, M1S-E06-01)."""
    user_id = _user(settings, username).id
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                select(OutboxEvent.envelope).where(OutboxEvent.subject == f"user/{user_id}").order_by(OutboxEvent.time)
            )
            return [row[0] for row in rows if row[0]["type"] != "hauskraft.user.created"]
    finally:
        engine.dispose()


def _change(c: TestClient, current: str, new: str = NEW_PASSWORD):  # type: ignore[no-untyped-def]
    return c.post("/api/v1/me/password", json={"current_password": current, "new_password": new})


def test_change_password_keeps_this_session_and_ends_the_others(
    browser: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user("Pat")
    me, other = browser(username), browser(username)
    r = _change(me, PASSWORD)
    assert r.status_code == 204, r.text
    assert me.get("/api/v1/me").status_code == 200
    assert other.get("/api/v1/me").status_code == 401
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as fresh:
        old = fresh.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        assert old.status_code == 401
        new = fresh.post("/api/v1/auth/login", json={"username": username, "password": NEW_PASSWORD})
        assert new.status_code == 200


def test_password_change_is_an_event_without_secrets(
    browser: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user("Pat")
    me = browser(username)
    assert _change(me, PASSWORD).status_code == 204
    [event] = _events(api_settings, username)
    user = _user(api_settings, username)
    assert event["type"] == "hauskraft.user.password_changed"
    assert event["dataclass"] == "personal"
    assert event["actorid"] == str(user.id)
    assert event["data"] == {"user": {"id": str(user.id), "username": username, "display_name": "Pat", "role": "adult"}}
    raw = json.dumps(event).lower()
    for secret in (PASSWORD, NEW_PASSWORD, "argon2", "hash"):
        assert secret not in raw


@pytest.mark.parametrize(
    ("current", "new", "code"),
    [("not-my-password-at-all", NEW_PASSWORD, "wrong_password"), (PASSWORD, "short", "password_policy")],
)
def test_rejected_changes_change_nothing(
    browser: Callable[..., TestClient],
    make_user: Callable[..., str],
    api_settings: Settings,
    current: str,
    new: str,
    code: str,
) -> None:
    username = make_user()
    me, other = browser(username), browser(username)
    r = _change(me, current, new)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == code
    assert other.get("/api/v1/me").status_code == 200
    assert _events(api_settings, username) == []
    browser(username, PASSWORD)  # the old password still works


def test_repeated_wrong_current_passwords_are_rate_limited(
    browser: Callable[..., TestClient], make_user: Callable[..., str]
) -> None:
    me = browser(make_user())
    codes = [_change(me, f"wrong-password-{i:04d}").status_code for i in range(6)]
    assert codes == [422] * 5 + [429]


def test_display_name_change_is_an_event_language_is_not(
    browser: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user("Robin")
    me = browser(username)
    assert me.patch("/api/v1/me", json={"locale": "de"}).status_code == 200
    assert me.patch("/api/v1/me", json={"display_name": "Robin"}).status_code == 200, "unchanged: no event"
    assert _events(api_settings, username) == []
    r = me.patch("/api/v1/me", json={"display_name": "Robin K.", "locale": "en"})
    assert r.status_code == 200, r.text
    [event] = _events(api_settings, username)
    assert event["type"] == "hauskraft.user.updated"
    assert event["data"]["user"]["display_name"] == "Robin K."
    assert event["data"]["changes"] == {"display_name": {"from": "Robin", "to": "Robin K."}}


def test_password_change_needs_a_session(client: TestClient) -> None:
    assert _change(client, PASSWORD).status_code == 401
