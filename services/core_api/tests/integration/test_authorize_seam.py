# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-04: with DenyAllPolicy a write answers 403 policy_denied and leaves no row and no event."""

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent
from hauskraft_core.settings import Settings
from hauskraft_core.uow import UnitOfWork, unit_of_work
from hauskraft_sdk import Actor, ResourceRef

pytestmark = pytest.mark.integration
ACTOR = Actor(id="0199f390-1111-7aaa-8bbb-cccccccccccc", role="adult", display_name="Probe")


def _client(db_settings: Settings, policy: str) -> TestClient:
    settings = db_settings.model_copy(update={"policy": policy})
    app = create_app(settings)
    probe = APIRouter(prefix="/api/v1/_probe", tags=["probe"])

    @probe.put("/setting/{key}")
    async def put_setting(key: str, uow_factory: UnitOfWork = Depends(unit_of_work)) -> dict[str, str]:  # noqa: B008
        async with uow_factory as uow:
            await uow.authorize(
                ACTOR, "settings.probe.set", ResourceRef("DeploymentSetting", key), "household", "settings:write"
            )
            uow.session.add(DeploymentSetting(key=key, value="v"))
        return {"key": key}

    app.include_router(probe)
    return TestClient(app)


def _counts(url: str, key: str) -> tuple[int, int]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(func.count()).select_from(DeploymentSetting).where(DeploymentSetting.key == key))
            events = conn.execute(select(func.count()).select_from(OutboxEvent))
            return rows.scalar_one(), events.scalar_one()
    finally:
        engine.dispose()


def test_deny_all_returns_403_and_writes_nothing(db_settings: Settings) -> None:
    events_before = _counts(db_settings.database_url, "probe.denied")[1]
    with _client(db_settings, "deny_all") as client:
        r = client.put("/api/v1/_probe/setting/probe.denied")
    assert r.status_code == 403
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "policy_denied"
    assert _counts(db_settings.database_url, "probe.denied") == (0, events_before)


def test_noop_policy_lets_the_write_commit(db_settings: Settings) -> None:
    with _client(db_settings, "noop") as client:
        assert client.put("/api/v1/_probe/setting/probe.allowed").status_code == 200
    assert _counts(db_settings.database_url, "probe.allowed")[0] == 1
    engine = create_engine(db_settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM deployment_settings WHERE key = 'probe.allowed'"))
    engine.dispose()
