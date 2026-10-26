# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E08-02: the usage overview for owners, with a cost estimate when prices are set."""

import datetime as dt
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, insert, select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import AssistantUsage, DeploymentSetting, User
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


def _db(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


@pytest.fixture
def owner(api_settings: Settings, make_user: Callable[..., str]) -> Iterator[tuple[TestClient, str]]:
    _db(api_settings, delete(AssistantUsage))
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))
    username = make_user(role="owner", display_name="Usage Owner")
    [(user_id,)] = _db(api_settings, select(User.id).where(User.username == username))
    now = dt.datetime.now(dt.UTC)
    rows = [
        {"user_id": user_id, "kind": "chat", "model": "m-a", "input_tokens": 1000, "output_tokens": 100},
        {"user_id": user_id, "kind": "chat", "model": "m-a", "input_tokens": 3000, "output_tokens": 300},
        {"user_id": user_id, "kind": "skill", "model": "m-b", "input_tokens": None, "output_tokens": None},
        {
            "user_id": user_id,
            "kind": "test",
            "model": "m-b",
            "input_tokens": 10,
            "output_tokens": 1,
            "created_at": now - dt.timedelta(days=40),
        },
    ]
    for r in rows:
        _db(api_settings, insert(AssistantUsage).values(id=uuid.uuid4(), status="ok", **r))
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as c:
        r = c.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        yield c, str(user_id)


def test_default_is_the_last_30_days_by_day(owner: tuple[TestClient, str]) -> None:
    body = owner[0].get("/api/v1/assistant/usage").json()
    assert body["group_by"] == "day"
    assert body["totals"] == {
        "requests": 3,
        "input_tokens": 4000,
        "output_tokens": 400,
        "unknown_requests": 1,
        "cost": None,
    }
    assert len(body["groups"]) == 1
    assert body["groups"][0]["key"] == dt.date.today().isoformat() or len(body["groups"][0]["key"]) == 10


@pytest.mark.parametrize("group_by", ["user", "model", "kind"])
def test_groups_sum_to_the_totals(owner: tuple[TestClient, str], group_by: str) -> None:
    body = owner[0].get("/api/v1/assistant/usage", params={"group_by": group_by}).json()
    for f in ("requests", "input_tokens", "output_tokens", "unknown_requests"):
        assert sum(g[f] for g in body["groups"]) == body["totals"][f]
    if group_by == "user":
        assert body["groups"][0]["label"] == "Usage Owner"
        assert body["groups"][0]["key"] == owner[1]
    if group_by == "model":
        assert [g["key"] for g in body["groups"]] == ["m-a", "m-b"], "sorted by input tokens, descending"


def test_range_and_cost(owner: tuple[TestClient, str]) -> None:
    c = owner[0]
    start = (dt.date.today() - dt.timedelta(days=60)).isoformat()
    assert c.get("/api/v1/assistant/usage", params={"from": start}).json()["totals"]["requests"] == 4
    c.patch("/api/v1/assistant/settings", json={"prices": {"input_per_million": 2.5, "output_per_million": 10}})
    cost = c.get("/api/v1/assistant/usage").json()["totals"]["cost"]
    assert cost == {"amount": 0.01, "currency": "EUR"}  # 4000 * 2.5e-6 + 400 * 1e-5 = 0.014 → 0.01


def test_validation(owner: tuple[TestClient, str]) -> None:
    assert owner[0].get("/api/v1/assistant/usage", params={"group_by": "planet"}).status_code == 422
