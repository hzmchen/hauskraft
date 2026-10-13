# SPDX-License-Identifier: MIT
"""M0S-E07-02: every task write authorizes first, writes, and emits exactly one event."""

import datetime as dt
import uuid

import pytest
from conftest import FakeContext, make_adult
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_sdk.errors import ConflictError, NotFoundError
from hearthos_tasks import service
from hearthos_tasks.models import Task
from hearthos_tasks.schemas import TaskCreate, TaskPatch

pytestmark = pytest.mark.integration


async def test_create(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="  Buy milk  "))
    assert task.title == "Buy milk"
    assert task.version == 1
    assert ctx.authorized == [(demo.id, "task.create", ctx.authorized[0][2], "household", "graph:write:Task")]
    assert ctx.authorized[0][2].type == "Task"
    assert [e["type"] for e in ctx.events] == ["hearthos.task.created"]
    assert ctx.events[0]["subject"] == f"task/{task.id}"
    assert ctx.events[0]["data"]["task"]["title"] == "Buy milk"
    assert ctx.events[0]["actorid"] == demo.id
    out = await service.task_out(db_session, task)
    assert out.created_by.display_name == "Demo Adult"
    assert out.updated_by.display_name == "Demo Adult"


async def test_update_records_changes(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Buy milk"))
    tomorrow = dt.date.today() + dt.timedelta(days=1)
    updated = await service.update_task(ctx, demo, task.id, TaskPatch(title="Buy oat milk", due_on=tomorrow))
    assert updated.version == 2
    event = ctx.events[-1]
    assert event["type"] == "hearthos.task.updated"
    assert event["data"]["changes"] == {"title": ["Buy milk", "Buy oat milk"], "due_on": [None, tomorrow.isoformat()]}


async def test_complete_and_reopen(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Plants"))
    done = await service.update_task(ctx, demo, task.id, TaskPatch(done=True))
    assert done.done is True
    assert done.done_at is not None
    assert ctx.events[-1]["type"] == "hearthos.task.completed"
    assert ctx.events[-1]["data"]["completed_at"]
    reopened = await service.update_task(ctx, demo, task.id, TaskPatch(done=False))
    assert reopened.done_at is None
    assert ctx.events[-1]["type"] == "hearthos.task.updated"
    assert ctx.events[-1]["data"]["changes"] == {"done": [True, False]}


async def test_explicit_null_clears_the_due_date_and_absence_keeps_it(
    ctx: FakeContext, db_session: AsyncSession
) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Due", due_on=dt.date(2026, 10, 20)))
    kept = await service.update_task(ctx, demo, task.id, TaskPatch(title="Due!"))
    assert kept.due_on == dt.date(2026, 10, 20)
    cleared = await service.update_task(ctx, demo, task.id, TaskPatch.model_validate({"due_on": None}))
    assert cleared.due_on is None


async def test_no_change_means_no_write_and_no_event(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Same"))
    same = await service.update_task(ctx, demo, task.id, TaskPatch(title="Same"))
    assert same.version == 1
    assert len(ctx.events) == 1


async def test_version_conflict(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="v"))
    await service.update_task(ctx, demo, task.id, TaskPatch(title="v2", version=1))
    with pytest.raises(ConflictError) as err:
        await service.update_task(ctx, demo, task.id, TaskPatch(title="stale", version=1))
    assert err.value.code == "version_conflict"
    assert err.value.status == 409


async def test_delete_emits_a_snapshot(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Gone"))
    await service.delete_task(ctx, demo, task.id)
    assert await db_session.get(Task, task.id) is None
    assert ctx.events[-1]["type"] == "hearthos.task.deleted"
    assert ctx.events[-1]["data"]["task"]["title"] == "Gone"
    with pytest.raises(NotFoundError):
        await service.delete_task(ctx, demo, task.id)


async def test_any_adult_may_edit_and_delete_any_task(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    alex = await make_adult(db_session, "Alex Adult")
    task = await service.create_task(ctx, demo, TaskCreate(title="Shared"))
    edited = await service.update_task(ctx, alex, task.id, TaskPatch(title="Shared (by alex)"))
    assert str(edited.updated_by) == alex.id
    assert str(edited.created_by) == demo.id
    assert ctx.events[-1]["actorid"] == alex.id
    await service.delete_task(ctx, alex, task.id)
    assert ctx.events[-1]["actorid"] == alex.id


async def test_failed_emit_leaves_no_row(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    ctx.fail_emit = True
    with pytest.raises(RuntimeError):
        await service.create_task(ctx, demo, TaskCreate(title="Never stored"))
    assert (await service.list_tasks(db_session, status="all", sort="-created_at", limit=200, offset=0)).total >= 0
    titles = [t.title for t in (await service.list_tasks(db_session, "all", "-created_at", 200, 0)).items]
    assert "Never stored" not in titles


async def test_unknown_task(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    with pytest.raises(NotFoundError):
        await service.update_task(ctx, demo, uuid.uuid4(), TaskPatch(title="x"))


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {},
        {"title": "ok", "colour": "red"},
        {"title": "ok", "due_on": "13.10.2026"},
    ],
)
def test_create_validation(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(body)


@pytest.mark.parametrize(
    "body", [{"title": ""}, {"done": "maybe"}, {"done": 1}, {"version": 0}, {"unknown": 1}, {"due_on": 20261013}]
)
def test_patch_validation(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TaskPatch.model_validate(body)
