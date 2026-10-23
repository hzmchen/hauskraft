# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E03-01: first-run setup creates the household and the first owner, exactly once (ADR 0017)."""

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url

from hauskraft_core.app import create_app
from hauskraft_core.db import migrations
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent, User
from hauskraft_core.settings import Settings

pytestmark = pytest.mark.integration

HOUSEHOLD = {"name": "Familie Müller", "timezone": "Europe/Berlin", "locale": "de"}
OWNER = {"username": "mia", "display_name": "Mia", "password": "mia-household-pass-2026"}


def _body(**owner: str) -> dict[str, Any]:
    return {"household": dict(HOUSEHOLD), "owner": {**OWNER, **owner}}


@pytest.fixture
def empty(pg_url: str, db_settings: Settings) -> Iterator[Settings]:
    """A migrated database without accounts, like a fresh install."""
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS setup_probe WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE setup_probe"))
    url = make_url(pg_url).set(database="setup_probe").render_as_string(hide_password=False)
    settings = db_settings.model_copy(update={"database_url": url, "allowed_origins": ["http://testserver"]})
    migrations.upgrade(settings)
    yield settings
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS setup_probe WITH (FORCE)"))
    admin.dispose()


@pytest.fixture
def client(empty: Settings) -> Iterator[Callable[..., TestClient]]:
    opened: list[TestClient] = []

    def _open(origin: str = "http://testserver") -> TestClient:
        c = TestClient(create_app(empty), headers={"Origin": origin})
        c.__enter__()
        opened.append(c)
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _scalar(settings: Settings, statement: Any) -> Any:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            return conn.execute(statement).scalar()
    finally:
        engine.dispose()


def _rows(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            return list(conn.execute(statement))
    finally:
        engine.dispose()


def test_setup_creates_the_household_and_signs_in_the_owner(client: Callable[..., TestClient], empty: Settings) -> None:
    c = client()
    assert c.get("/api/v1/setup").json() == {"required": True}
    r = c.post("/api/v1/setup", json=_body())
    assert r.status_code == 201, r.text
    session = r.json()
    assert session["user"]["username"] == "mia"
    assert session["user"]["role"] == "owner"
    assert session["user"]["locale"] == "de", "the owner gets the household language"
    assert session["user"]["must_change_password"] is False
    assert {"settings.household.set", "user.create"} <= set(session["permissions"])
    assert r.headers["set-cookie"].startswith("hauskraft_session=")
    c.headers["X-CSRF-Token"] = session["csrf_token"]
    assert c.get("/api/v1/household").json() == HOUSEHOLD
    assert c.get("/api/v1/setup").json() == {"required": False}
    assert _scalar(empty, select(User.last_login_at).where(User.username == "mia")) is not None

    events = [row[0] for row in _rows(empty, select(OutboxEvent.envelope))]
    assert [e["type"] for e in events] == ["hauskraft.user.created"], "exactly one event"
    assert events[0]["actorid"] == session["user"]["id"]


def test_setup_runs_once(client: Callable[..., TestClient]) -> None:
    c = client()
    assert c.post("/api/v1/setup", json=_body()).status_code == 201
    again = client().post("/api/v1/setup", json=_body(username="second"))
    assert again.status_code == 409
    assert again.json()["code"] == "setup_done"


def test_setup_is_closed_once_any_account_exists(db_settings: Settings, make_user: Callable[..., str]) -> None:
    make_user()
    settings = db_settings.model_copy(update={"allowed_origins": ["http://testserver"]})
    with TestClient(create_app(settings), headers={"Origin": "http://testserver"}) as c:
        assert c.get("/api/v1/setup").json() == {"required": False}
        r = c.post("/api/v1/setup", json=_body(username="intruder"))
        assert r.status_code == 409
        assert r.json()["code"] == "setup_done"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"household": {**HOUSEHOLD, "timezone": "Mars/Olympus_Mons"}}, "invalid_timezone"),
        ({"owner": {**OWNER, "password": "short"}}, "password_policy"),
        ({"owner": {**OWNER, "username": "No Spaces Allowed"}}, "invalid_username"),
        ({"household": {**HOUSEHOLD, "name": "  "}}, None),
        ({"household": {**HOUSEHOLD, "locale": "fr"}}, None),
        ({"owner": {**OWNER, "role": "adult"}}, None),
    ],
)
def test_invalid_setup_stores_nothing(
    client: Callable[..., TestClient], empty: Settings, change: dict[str, Any], code: str | None
) -> None:
    r = client().post("/api/v1/setup", json={**_body(), **change})
    assert r.status_code == 422, r.text
    if code:
        assert r.json()["code"] == code
    assert _scalar(empty, select(func.count()).select_from(User)) == 0
    assert _scalar(empty, select(func.count()).select_from(DeploymentSetting)) == 0
    assert _scalar(empty, select(func.count()).select_from(OutboxEvent)) == 0


def test_setup_from_a_foreign_origin_is_rejected(client: Callable[..., TestClient], empty: Settings) -> None:
    r = client(origin="http://evil.example").post("/api/v1/setup", json=_body())
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_failed"
    assert _scalar(empty, select(func.count()).select_from(User)) == 0


def test_concurrent_setup_has_exactly_one_winner(client: Callable[..., TestClient], empty: Settings) -> None:
    clients = [client() for _ in range(5)]

    def attempt(i: int) -> int:
        return clients[i].post("/api/v1/setup", json=_body(username=f"mia{i}")).status_code

    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = sorted(pool.map(attempt, range(5)))
    assert statuses == [201, 409, 409, 409, 409]
    assert _scalar(empty, select(func.count()).select_from(User)) == 1
