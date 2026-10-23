# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E06-01: owners list the household's members and see each one; new accounts are user.created events."""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update

from hauskraft_core.app import create_app
from hauskraft_core.db.models import OutboxEvent, User
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

MEMBER_FIELDS = {
    "id",
    "username",
    "display_name",
    "role",
    "locale",
    "must_change_password",
    "is_active",
    "created_at",
    "last_login_at",
}


@pytest.fixture
def signed_in(api_settings: Settings, make_user: Callable[..., str]) -> Iterator[Callable[..., TestClient]]:
    opened: list[TestClient] = []

    def _open(role: str = "owner", username: str | None = None) -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": username or make_user(role=role), "password": PASSWORD})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _sql(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


def test_owners_list_everyone_ordered_without_secrets(
    signed_in: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    gone = make_user("aaa Gone")
    _sql(api_settings, update(User).where(User.username == gone).values(is_active=False))
    owner = signed_in()
    r = owner.get("/api/v1/users")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert gone in {m["username"] for m in rows}, "deactivated members are listed too"
    assert next(m for m in rows if m["username"] == gone)["is_active"] is False
    for row in rows:
        assert set(row) == MEMBER_FIELDS
    keys = [(m["display_name"].lower(), m["username"]) for m in rows]
    assert keys == sorted(keys)


def test_owners_see_one_member(signed_in: Callable[..., TestClient], make_user: Callable[..., str]) -> None:
    username = make_user("Single")
    owner = signed_in()
    member = next(m for m in owner.get("/api/v1/users").json() if m["username"] == username)
    r = owner.get(f"/api/v1/users/{member['id']}")
    assert r.status_code == 200
    assert r.json() == member
    assert r.json()["last_login_at"] is None
    missing = owner.get(f"/api/v1/users/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


def test_adults_cannot_list_or_see_members(signed_in: Callable[..., TestClient]) -> None:
    adult = signed_in("adult")
    me = adult.get("/api/v1/me").json()
    for path in ("/api/v1/users", f"/api/v1/users/{me['id']}"):
        r = adult.get(path)
        assert r.status_code == 403, path
        assert r.json()["code"] == "policy_denied"


def test_created_member_takes_the_household_language_and_is_an_event(
    signed_in: Callable[..., TestClient], api_settings: Settings
) -> None:
    owner = signed_in()
    assert owner.patch("/api/v1/household", json={"locale": "de"}).status_code == 200
    try:
        username = "n" + uuid.uuid4().hex[:8]
        r = owner.post("/api/v1/users", json={"username": username, "display_name": "Neu", "password": PASSWORD})
        assert r.status_code == 201, r.text
        member = r.json()
        assert set(member) == MEMBER_FIELDS
        assert member["locale"] == "de"
        assert member["is_active"] is True
        explicit = owner.post(
            "/api/v1/users",
            json={"username": "e" + uuid.uuid4().hex[:8], "display_name": "E", "password": PASSWORD, "locale": "en"},
        )
        assert explicit.json()["locale"] == "en"
    finally:
        owner.patch("/api/v1/household", json={"locale": "en"})
    [event] = [
        row[0]
        for row in _sql(api_settings, select(OutboxEvent.envelope).where(OutboxEvent.subject == f"user/{member['id']}"))
    ]
    assert event["type"] == "hauskraft.user.created"
    assert event["dataclass"] == "personal"
    assert event["data"] == {"user": {k: member[k] for k in ("id", "username", "display_name", "role")}}
