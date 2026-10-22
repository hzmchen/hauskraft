# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E04-03: outbox_events is append-only (only published_at and attempts may change)."""

import datetime as dt

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.ids import new_id
from hauskraft_core.db.models import OutboxEvent

pytestmark = pytest.mark.integration
NOW = dt.datetime(2026, 10, 12, 9, 0, tzinfo=dt.UTC)


async def _event(db_session: AsyncSession) -> OutboxEvent:
    event_id = new_id()
    event = OutboxEvent(
        id=event_id,
        type="hauskraft.task.created",
        source="dev.hauskraft.tasks",
        subject="task/x",
        data_class="household",
        time=NOW,
        envelope={"specversion": "1.0", "id": str(event_id)},
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def test_insert_defaults(db_session: AsyncSession) -> None:
    event = await _event(db_session)
    await db_session.refresh(event)
    assert event.attempts == 0
    assert event.published_at is None
    assert event.actor_id is None


async def test_publishing_columns_may_change(db_session: AsyncSession) -> None:
    event = await _event(db_session)
    await db_session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event.id)
        .values(published_at=NOW, attempts=OutboxEvent.attempts + 1)
    )
    await db_session.refresh(event)
    assert event.attempts == 1
    assert event.published_at == NOW


@pytest.mark.parametrize("column", ["envelope", "type", "source", "subject", "data_class", "time"])
async def test_other_columns_are_immutable(db_session: AsyncSession, column: str) -> None:
    event = await _event(db_session)
    value = {"envelope": {"tampered": True}, "time": NOW + dt.timedelta(days=1)}.get(column, "tampered")
    with pytest.raises(DBAPIError, match="append-only"):
        async with db_session.begin_nested():  # the savepoint rolls back the failed statement
            await db_session.execute(update(OutboxEvent).where(OutboxEvent.id == event.id).values({column: value}))


async def test_delete_is_rejected(db_session: AsyncSession) -> None:
    event = await _event(db_session)
    with pytest.raises(DBAPIError, match="append-only"):
        async with db_session.begin_nested():  # the savepoint rolls back the failed statement
            await db_session.execute(delete(OutboxEvent).where(OutboxEvent.id == event.id))


async def test_truncate_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(DBAPIError, match="append-only"):
        async with db_session.begin_nested():  # the savepoint rolls back the failed statement
            await db_session.execute(text("TRUNCATE outbox_events"))


async def test_unpublished_and_time_indexes_exist(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename = 'outbox_events'"))
    defs = " ".join(r[0] for r in rows)
    assert "WHERE (published_at IS NULL)" in defs
    assert '"time" DESC' in defs
