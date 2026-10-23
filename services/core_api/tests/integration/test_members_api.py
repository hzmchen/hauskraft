# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E06-01..03: owners list, see, edit, deactivate and reactivate members; there is always an active
owner (spec §2.3)."""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.engine import make_url

from hauskraft_core.app import create_app
from hauskraft_core.db import migrations
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


# ---------------------------------------------------------------- M1S-E06-02 edit a member, keep an owner
def _member(owner: TestClient, username: str) -> dict[str, Any]:
    return next(m for m in owner.get("/api/v1/users").json() if m["username"] == username)


def _events_for(settings: Settings, user_id: str) -> list[dict[str, Any]]:
    rows = _sql(
        settings,
        select(OutboxEvent.envelope).where(OutboxEvent.subject == f"user/{user_id}").order_by(OutboxEvent.time),
    )
    return [row[0] for row in rows if row[0]["type"] != "hauskraft.user.created"]


def test_owner_renames_and_promotes_a_member(
    signed_in: Callable[..., TestClient], make_user: Callable[..., str], api_settings: Settings
) -> None:
    username = make_user("Robin")
    member_client = signed_in(username=username)
    owner = signed_in()
    member = _member(owner, username)
    r = owner.patch(f"/api/v1/users/{member['id']}", json={"display_name": "Robin K.", "role": "owner"})
    assert r.status_code == 200, r.text
    assert (r.json()["display_name"], r.json()["role"]) == ("Robin K.", "owner")
    assert "user.create" in member_client.get("/api/v1/auth/session").json()["permissions"], "applies at once"
    [event] = _events_for(api_settings, member["id"])
    assert event["type"] == "hauskraft.user.updated"
    assert event["data"]["user"]["role"] == "owner"
    assert event["data"]["changes"] == {
        "display_name": {"from": "Robin", "to": "Robin K."},
        "role": {"from": "adult", "to": "owner"},
    }
    assert owner.patch(f"/api/v1/users/{member['id']}", json={"role": "owner"}).status_code == 200
    assert len(_events_for(api_settings, member["id"])) == 1, "an unchanged PATCH emits nothing"


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"username": "renamed"}, 422, None),
        ({"role": "kid"}, 422, "role_not_enabled"),
        ({"display_name": ""}, 422, None),
    ],
)
def test_invalid_member_edits(
    signed_in: Callable[..., TestClient],
    make_user: Callable[..., str],
    body: dict[str, str],
    status: int,
    code: str | None,
) -> None:
    owner = signed_in()
    member = _member(owner, make_user())
    r = owner.patch(f"/api/v1/users/{member['id']}", json=body)
    assert r.status_code == status, r.text
    if code:
        assert r.json()["code"] == code


def test_member_edits_need_an_owner_and_a_member(
    signed_in: Callable[..., TestClient], make_user: Callable[..., str]
) -> None:
    username = make_user()
    owner = signed_in()
    member = _member(owner, username)
    missing = owner.patch(f"/api/v1/users/{uuid.uuid4()}", json={"display_name": "Nobody"})
    assert missing.status_code == 404
    denied = signed_in("adult").patch(f"/api/v1/users/{member['id']}", json={"display_name": "Nope"})
    assert denied.status_code == 403
    assert denied.json()["code"] == "policy_denied"


@pytest.fixture
def one_owner(pg_url: str, db_settings: Settings) -> Iterator[Callable[[], TestClient]]:
    """A fresh household whose only owner is Mia, set up through POST /setup."""
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS members_probe WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE members_probe"))
    url = make_url(pg_url).set(database="members_probe").render_as_string(hide_password=False)
    settings = db_settings.model_copy(update={"database_url": url, "allowed_origins": ["http://testserver"]})
    migrations.upgrade(settings)
    opened: list[TestClient] = []

    def _mia() -> TestClient:
        c = TestClient(create_app(settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        body = {
            "household": {"name": "H", "timezone": "Europe/Berlin", "locale": "en"},
            "owner": {"username": "mia", "display_name": "Mia", "password": PASSWORD},
        }
        r = c.post("/api/v1/setup", json=body)
        if r.status_code == 409:
            r = c.post("/api/v1/auth/login", json={"username": "mia", "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _mia
    for c in opened:
        c.__exit__(None, None, None)
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS members_probe WITH (FORCE)"))
    admin.dispose()


def test_the_last_owner_cannot_step_down(one_owner: Callable[[], TestClient]) -> None:
    mia = one_owner()
    me = mia.get("/api/v1/me").json()
    r = mia.patch(f"/api/v1/users/{me['id']}", json={"role": "adult"})
    assert r.status_code == 409
    assert r.json()["code"] == "last_owner"
    assert mia.get("/api/v1/me").json()["role"] == "owner"
    jonas = mia.post(
        "/api/v1/users",
        json={"username": "jonas", "display_name": "Jonas", "password": PASSWORD, "role": "owner"},
    ).json()
    assert mia.patch(f"/api/v1/users/{me['id']}", json={"role": "adult"}).status_code == 200, "a second owner exists"
    assert mia.get("/api/v1/me").json()["role"] == "adult"
    assert jonas["role"] == "owner"


# ---------------------------------------------------------------- M1S-E06-03 deactivate and reactivate
def test_deactivate_ends_sessions_blocks_sign_in_and_reactivate_undoes_it(
    signed_in: Callable[..., TestClient],
    make_user: Callable[..., str],
    api_settings: Settings,
) -> None:
    username = make_user("Leaving")
    member_client = signed_in(username=username)
    owner = signed_in()
    member = _member(owner, username)
    r = owner.post(f"/api/v1/users/{member['id']}/deactivate")
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False
    assert member_client.get("/api/v1/me").status_code == 401, "open sessions end at the next request"
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as probe:
        right = probe.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        assert right.status_code == 403
        assert right.json()["code"] == "account_deactivated"
        wrong = probe.post("/api/v1/auth/login", json={"username": username, "password": "wrong-password-0000"})
        assert wrong.status_code == 401
        assert wrong.json()["code"] == "invalid_credentials"
        assert _member(owner, username)["is_active"] is False, "deactivated members stay in the list"
        assert owner.post(f"/api/v1/users/{member['id']}/deactivate").status_code == 200, "no-op"
        r = owner.post(f"/api/v1/users/{member['id']}/reactivate")
        assert r.status_code == 200
        assert r.json()["is_active"] is True
        assert owner.post(f"/api/v1/users/{member['id']}/reactivate").status_code == 200, "no-op"
        login = probe.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        assert login.status_code == 200
    types = [e["type"] for e in _events_for(api_settings, member["id"])]
    assert types == ["hauskraft.user.deactivated", "hauskraft.user.reactivated"], "no-ops emit nothing"


def test_deactivation_needs_an_owner_and_a_member(
    signed_in: Callable[..., TestClient], make_user: Callable[..., str]
) -> None:
    username = make_user()
    owner = signed_in()
    member = _member(owner, username)
    for action in ("deactivate", "reactivate"):
        assert owner.post(f"/api/v1/users/{uuid.uuid4()}/{action}").status_code == 404
        denied = signed_in("adult").post(f"/api/v1/users/{member['id']}/{action}")
        assert denied.status_code == 403
        assert denied.json()["code"] == "policy_denied"


def test_the_last_owner_cannot_deactivate_themself(one_owner: Callable[[], TestClient]) -> None:
    mia = one_owner()
    me = mia.get("/api/v1/me").json()
    r = mia.post(f"/api/v1/users/{me['id']}/deactivate")
    assert r.status_code == 409
    assert r.json()["code"] == "last_owner"
    assert mia.get("/api/v1/me").status_code == 200
