# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E04-01: GET and PATCH /household; owners change it, every change is one household_changed event."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

CHANGED = "hauskraft.settings.household_changed"
DEFAULTS = {"name": "Household", "timezone": "Europe/Berlin", "locale": "en"}


def _db(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


@pytest.fixture
def household(api_settings: Settings) -> Iterator[Settings]:
    """An unset household (as right after an M0* upgrade), cleaned up again afterwards."""
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("household.%")))
    yield api_settings
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("household.%")))


@pytest.fixture
def signed_in(household: Settings, make_user: Callable[..., str]) -> Iterator[Callable[[str], TestClient]]:
    opened: list[TestClient] = []

    def _open(role: str) -> TestClient:
        c = TestClient(create_app(household), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": make_user(role=role), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _events(settings: Settings) -> list[dict[str, Any]]:
    rows = _db(
        settings,
        select(OutboxEvent.envelope).where(OutboxEvent.subject == "setting/household").order_by(OutboxEvent.time),
    )
    return [row[0] for row in rows]


def test_unset_household_has_defaults(signed_in: Callable[[str], TestClient]) -> None:
    r = signed_in("adult").get("/api/v1/household")
    assert r.status_code == 200, r.text
    assert r.json() == DEFAULTS


def test_default_time_zone_follows_the_setting(household: Settings, make_user: Callable[..., str]) -> None:
    settings = household.model_copy(update={"default_timezone": "Pacific/Kiritimati"})
    with TestClient(create_app(settings), headers={"Origin": "http://testserver"}) as c:
        c.post("/api/v1/auth/login", json={"username": make_user(), "password": PASSWORD})
        assert c.get("/api/v1/household").json()["timezone"] == "Pacific/Kiritimati"


def test_owner_changes_some_values_and_one_event_lists_them(
    signed_in: Callable[[str], TestClient], household: Settings
) -> None:
    before = len(_events(household))
    owner = signed_in("owner")
    r = owner.patch("/api/v1/household", json={"name": "  Familie Müller ", "timezone": "Pacific/Kiritimati"})
    assert r.status_code == 200, r.text
    assert r.json() == {"name": "Familie Müller", "timezone": "Pacific/Kiritimati", "locale": "en"}
    assert signed_in("adult").get("/api/v1/household").json() == r.json()
    events = _events(household)[before:]
    assert len(events) == 1
    assert events[0]["type"] == CHANGED
    assert events[0]["dataclass"] == "household"
    assert events[0]["data"] == {
        "changes": {
            "name": {"from": "Household", "to": "Familie Müller"},
            "timezone": {"from": "Europe/Berlin", "to": "Pacific/Kiritimati"},
        }
    }


def test_unchanged_patch_emits_nothing(signed_in: Callable[[str], TestClient], household: Settings) -> None:
    owner = signed_in("owner")
    assert owner.patch("/api/v1/household", json={"locale": "de"}).status_code == 200
    before = len(_events(household))
    assert owner.patch("/api/v1/household", json={"locale": "de", "name": "Household"}).status_code == 200
    assert owner.patch("/api/v1/household", json={}).status_code == 200
    assert len(_events(household)) == before


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"timezone": "Mars/Olympus_Mons"}, "invalid_timezone"),
        ({"timezone": ""}, "invalid_timezone"),
        ({"name": "   "}, None),
        ({"name": "x" * 81}, None),
        ({"locale": "fr"}, None),
        ({"colour": "red"}, None),
    ],
)
def test_invalid_values_change_nothing(
    signed_in: Callable[[str], TestClient], household: Settings, body: dict[str, str], code: str | None
) -> None:
    owner = signed_in("owner")
    before = len(_events(household))
    r = owner.patch("/api/v1/household", json=body)
    assert r.status_code == 422, r.text
    if code:
        assert r.json()["code"] == code
    assert owner.get("/api/v1/household").json() == DEFAULTS
    assert len(_events(household)) == before


def test_adults_cannot_change_the_household(signed_in: Callable[[str], TestClient]) -> None:
    adult = signed_in("adult")
    r = adult.patch("/api/v1/household", json={"name": "Not allowed"})
    assert r.status_code == 403
    assert r.json()["code"] == "policy_denied"
    assert adult.get("/api/v1/household").json() == DEFAULTS


def test_household_needs_a_session(household: Settings) -> None:
    with TestClient(create_app(household), headers={"Origin": "http://testserver"}) as c:
        assert c.get("/api/v1/household").status_code == 401
