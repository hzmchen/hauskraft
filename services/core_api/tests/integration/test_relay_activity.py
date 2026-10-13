# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E10-03 (backend): the log relay publishes outbox events; /activity lists them newest first."""

import datetime as dt
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hearthos_core.db.models import OutboxEvent
from hearthos_core.events.relay import publish_batch
from hearthos_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


def _login(client: TestClient, username: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    return {"X-CSRF-Token": r.json()["csrf_token"]}


async def test_relay_publishes_unpublished_events(
    api_settings: Settings, client: TestClient, make_user: Callable[..., str], caplog: pytest.LogCaptureFixture
) -> None:
    h = _login(client, make_user())
    task = client.post("/api/v1/tasks", json={"title": "relay me"}, headers=h).json()
    engine = create_async_engine(api_settings.database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    published = 0
    while (n := await publish_batch(sessions, batch_size=100)) > 0:
        published += n
    await engine.dispose()
    assert published >= 1
    sync = create_engine(api_settings.database_url)
    with sync.connect() as conn:
        row = conn.execute(
            select(OutboxEvent.published_at, OutboxEvent.attempts).where(OutboxEvent.subject == f"task/{task['id']}")
        ).one()
        unpublished = conn.execute(text("SELECT count(*) FROM outbox_events WHERE published_at IS NULL")).scalar()
    sync.dispose()
    assert row.published_at is not None
    assert row.attempts == 1
    assert unpublished == 0
    assert any(isinstance(r.msg, dict) and r.msg.get("event") == "event.published" for r in caplog.records)


def test_activity_newest_first_with_actor_and_pagination(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user("Activity Adult")
    h = _login(client, username)
    title = f"act-{uuid.uuid4().hex[:6]}"
    task = client.post("/api/v1/tasks", json={"title": title}, headers=h).json()
    client.patch(f"/api/v1/tasks/{task['id']}", json={"done": True}, headers=h)
    items = client.get("/api/v1/activity", params={"limit": 50}).json()
    mine = [i for i in items if i["subject"] == f"task/{task['id']}"]
    assert [i["type"] for i in mine] == ["hearthos.task.completed", "hearthos.task.created"]
    entry = mine[-1]
    assert set(entry) == {"id", "type", "time", "actor", "subject", "summary_key", "data"}
    assert entry["actor"]["display_name"] == "Activity Adult"
    assert entry["summary_key"] == "activity.task.created"
    assert entry["data"]["task"]["title"] == title
    times = [i["time"] for i in items]
    assert times == sorted(times, reverse=True)

    first = client.get("/api/v1/activity", params={"limit": 2}).json()
    assert len(first) == 2
    older = client.get("/api/v1/activity", params={"limit": 2, "before": first[-1]["time"]}).json()
    assert all(dt.datetime.fromisoformat(i["time"]) < dt.datetime.fromisoformat(first[-1]["time"]) for i in older)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"before": "yesterday"}])
def test_activity_parameter_validation(
    client: TestClient, make_user: Callable[..., str], params: dict[str, object]
) -> None:
    _login(client, make_user())
    assert client.get("/api/v1/activity", params=params).status_code == 422


def test_activity_needs_a_session(client: TestClient) -> None:
    assert client.get("/api/v1/activity").status_code == 401
