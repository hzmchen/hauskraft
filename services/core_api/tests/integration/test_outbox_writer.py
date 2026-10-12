# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E10-02: events are appended to the current unit of work and validated outside production."""

import datetime as dt
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hearthos_core.db.models import OutboxEvent, User
from hearthos_core.events.outbox import EventValidationError, OutsideUnitOfWorkError, emit
from hearthos_core.policy import NoOpPolicy
from hearthos_core.schemas import validator
from hearthos_core.settings import Settings
from hearthos_core.uow import UnitOfWork
from hearthos_sdk import Actor, DataClass, ResourceRef
from hearthos_sdk.events import TaskCreatedData, TaskSnapshot

pytestmark = pytest.mark.integration

TASK_ID = uuid.UUID("0199f3a2-6c1d-7c55-8a10-3e2b9f4c0d21")


@pytest.fixture
async def actor(db_session: AsyncSession) -> AsyncIterator[Actor]:
    user = User(username=f"outbox{uuid.uuid4().hex[:6]}", display_name="Outbox Adult", password_hash="x")
    db_session.add(user)
    await db_session.flush()
    yield Actor(id=str(user.id), role="adult", display_name="Outbox Adult")


def _uow(db_session: AsyncSession, settings: Settings) -> UnitOfWork:
    # Reuse the test's connection so the outer test transaction still rolls everything back.
    factory = async_sessionmaker(bind=db_session.bind, join_transaction_mode="create_savepoint", expire_on_commit=False)
    return UnitOfWork(factory, NoOpPolicy(), settings)


def _created() -> TaskCreatedData:
    return TaskCreatedData(task=TaskSnapshot(id=TASK_ID, title="Buy milk", done=False, due_on=None, version=1))


async def test_emit_stores_a_schema_valid_envelope(
    db_session: AsyncSession, db_settings: Settings, actor: Actor
) -> None:
    async with _uow(db_session, db_settings) as uow:
        await uow.authorize(actor, "task.create", ResourceRef("Task", str(TASK_ID)), "household", "graph:write:Task")
        event_id = await emit(
            "hearthos.task.created", f"task/{TASK_ID}", _created(), DataClass.HOUSEHOLD, source="org.hearthos.tasks"
        )
    row = (await db_session.execute(select(OutboxEvent).where(OutboxEvent.id == uuid.UUID(event_id)))).scalar_one()
    env = row.envelope
    assert uuid.UUID(env["id"]).version == 7
    assert env["specversion"] == "1.0"
    assert env["source"] == "org.hearthos.tasks"
    assert env["type"] == "hearthos.task.created"
    assert env["subject"] == f"task/{TASK_ID}"
    assert env["dataclass"] == "household"
    assert env["actorid"] == actor.id
    assert env["dataschema"] == "https://schemas.hearthos.org/events/task.created/v1.json"
    assert dt.datetime.fromisoformat(env["time"]).tzinfo is not None
    assert env["data"]["task"]["title"] == "Buy milk"
    assert row.actor_id == uuid.UUID(actor.id)
    assert row.data_class == "household"
    assert row.published_at is None
    assert not list(validator("events/cloudevent.schema.json").iter_errors(env))


async def test_rollback_removes_the_event(db_session: AsyncSession, db_settings: Settings, actor: Actor) -> None:
    holder: dict[str, str] = {}
    with pytest.raises(RuntimeError):
        async with _uow(db_session, db_settings) as uow:
            await uow.authorize(actor, "task.create", ResourceRef("Task"), "household", "graph:write:Task")
            holder["id"] = await emit(
                "hearthos.task.created", f"task/{TASK_ID}", _created(), "household", source="org.hearthos.tasks"
            )
            raise RuntimeError("the write failed after the event was queued")
    assert (await db_session.get(OutboxEvent, uuid.UUID(holder["id"]))) is None


async def test_emit_outside_a_unit_of_work_raises() -> None:
    with pytest.raises(OutsideUnitOfWorkError):
        await emit("hearthos.task.created", "task/x", _created(), "household")


async def test_invalid_events_are_rejected_when_validation_is_on(
    db_session: AsyncSession, db_settings: Settings, actor: Actor
) -> None:
    with pytest.raises(EventValidationError):
        async with _uow(db_session, db_settings) as uow:
            await uow.authorize(actor, "task.create", ResourceRef("Task"), "household", "graph:write:Task")
            await emit(
                "hearthos.task.created", "task/x", {"task": {"title": ""}}, "household", source="org.hearthos.tasks"
            )


async def test_validation_can_be_switched_off(db_session: AsyncSession, db_settings: Settings, actor: Actor) -> None:
    settings = db_settings.model_copy(update={"validate_events": False})
    async with _uow(db_session, settings) as uow:
        await uow.authorize(actor, "probe.write", ResourceRef("Probe"), "household", "events:emit:probe")
        await emit("hearthos.probe.unschematised", "probe/1", {"anything": True}, "household")


async def test_system_events_without_an_actor(db_session: AsyncSession, db_settings: Settings) -> None:
    async with _uow(db_session, db_settings) as uow:
        event_id = await emit(
            "hearthos.plugin.toggled",
            "plugin/org.hearthos.tasks",
            {"plugin_id": "org.hearthos.tasks", "enabled": True},
            "household",
        )
        assert uow.actor is None
    row = await db_session.get(OutboxEvent, uuid.UUID(event_id))
    assert row is not None
    assert row.actor_id is None
    assert "actorid" not in row.envelope
    assert row.source == "org.hearthos.core"
