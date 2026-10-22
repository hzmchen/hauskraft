# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E08-06: per-user dashboard layouts on a 12-column grid."""

import asyncio
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select

from hauskraft_core.dashboard.service import save_layout
from hauskraft_core.db.models import DashboardLayout, User
from hauskraft_core.policy import DenyAllPolicy
from hauskraft_core.settings import Settings
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor
from hauskraft_sdk.errors import PolicyDeniedError
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration
CELL = {"i": "dev.hauskraft.tasks/tasks.list", "plugin_id": "dev.hauskraft.tasks", "widget_id": "tasks.list"}


def _login(client: TestClient, username: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    return {"X-CSRF-Token": r.json()["csrf_token"]}


@pytest.fixture
def h(client: TestClient, make_user: Callable[..., str]) -> dict[str, str]:
    return _login(client, make_user("Demo Adult"))


def test_default_layout_places_the_tasks_widget_at_its_default_size(client: TestClient, h: dict[str, str]) -> None:
    r = client.get("/api/v1/dashboard/today", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"dashboard_id": "today", "layout": [{**CELL, "x": 0, "y": 0, "w": 4, "h": 6}]}


def test_put_persists_per_user(client: TestClient, h: dict[str, str], make_user: Callable[..., str]) -> None:
    moved = [{**CELL, "x": 6, "y": 2, "w": 6, "h": 8}]
    r = client.put("/api/v1/dashboard/today", json={"layout": moved}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["layout"] == moved
    assert client.get("/api/v1/dashboard/today", headers=h).json()["layout"] == moved
    other = _login(client, make_user("Alex"))
    assert client.get("/api/v1/dashboard/today", headers=other).json()["layout"][0]["x"] == 0


@pytest.mark.parametrize(
    "cell",
    [
        {"x": 10, "y": 0, "w": 6, "h": 4},
        {"x": -1, "y": 0, "w": 4, "h": 4},
        {"x": 0, "y": -1, "w": 4, "h": 4},
        {"x": 0, "y": 0, "w": 0, "h": 4},
        {"x": 0, "y": 0, "w": 13, "h": 4},
        {"x": 0, "y": 0, "w": 4, "h": 0},
    ],
)
def test_cells_outside_the_grid_are_422(client: TestClient, h: dict[str, str], cell: dict[str, int]) -> None:
    r = client.put("/api/v1/dashboard/today", json={"layout": [{**CELL, **cell}]}, headers=h)
    assert r.status_code == 422
    assert r.json()["code"] == "validation_failed"


def test_duplicate_cell_ids_are_422(client: TestClient, h: dict[str, str]) -> None:
    cell = {**CELL, "x": 0, "y": 0, "w": 4, "h": 4}
    assert client.put("/api/v1/dashboard/today", json={"layout": [cell, cell]}, headers=h).status_code == 422


def test_needs_a_session_and_csrf(client: TestClient, h: dict[str, str]) -> None:
    assert TestClient(client.app).get("/api/v1/dashboard/today").status_code == 401
    r = client.put("/api/v1/dashboard/today", json={"layout": []})
    assert r.status_code == 403


def test_deny_all_writes_nothing(api_settings: Settings, make_user: Callable[..., str]) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    username = make_user("Probe")
    engine = create_engine(api_settings.database_url)
    with engine.connect() as conn:
        user_id = conn.scalar(select(User.id).where(User.username == username))
    actor = Actor(id=str(user_id), role="adult", display_name="Probe")

    async def denied() -> None:
        aengine = create_async_engine(api_settings.database_url, poolclass=NullPool)
        try:
            async with UnitOfWork(async_sessionmaker(aengine), DenyAllPolicy(), api_settings) as uow:
                await save_layout(uow, actor, "today", [])
        finally:
            await aengine.dispose()

    with pytest.raises(PolicyDeniedError):
        asyncio.run(denied())
    with engine.connect() as conn:
        count = conn.scalar(
            select(func.count()).select_from(DashboardLayout).where(DashboardLayout.user_id == uuid.UUID(str(user_id)))
        )
    engine.dispose()
    assert count == 0
