# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E06-03: a plugin writes through ctx.db_session(), ctx.authorize() and ctx.emit()."""

import uuid

import pytest
from sqlalchemy import select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent
from hauskraft_core.plugins.context import CorePluginContext
from hauskraft_core.settings import Settings
from hauskraft_sdk import Actor, ResourceRef

pytestmark = pytest.mark.integration

MANIFEST = {"capabilities": ["settings:write"], "data_classes": {"emits": ["household"]}}


async def test_context_writes_and_emits_in_one_transaction(db_settings: Settings) -> None:
    from fastapi.testclient import TestClient

    # The mechanics, not the permission table, are under test here.
    app = create_app(db_settings.model_copy(update={"plugin_paths": [], "theme_paths": [], "policy": "noop"}))
    with TestClient(app):
        ctx = CorePluginContext("org.example.ctx", MANIFEST, app)
        actor = Actor(id=str(uuid.uuid4()), role="adult", display_name="Ctx", kind="agent")
        key = f"ctx.{uuid.uuid4().hex[:6]}"
        async with ctx.db_session() as session:
            await ctx.authorize(
                actor, "setting.set", ResourceRef("DeploymentSetting", key), "household", "settings:write"
            )
            session.add(DeploymentSetting(key=key, value="v"))
            event_id = await ctx.emit(
                "hauskraft.plugin.toggled",
                "plugin/org.example.ctx",
                {"plugin_id": "org.example.ctx", "enabled": True},
                "household",
            )
        async with app.state.sessionmaker() as s:
            assert (await s.get(DeploymentSetting, key)) is not None
            event = (await s.execute(select(OutboxEvent).where(OutboxEvent.id == uuid.UUID(event_id)))).scalar_one()
            assert event.source == "org.example.ctx"
            assert event.envelope["actorid"] == actor.id
            assert event.actor_id is None, "agents are not users"
