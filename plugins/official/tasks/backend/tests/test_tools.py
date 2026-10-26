# SPDX-License-Identifier: MIT
"""M2S-E02-04: the tasks plugin's agent tools (ADR 0019): the contract, compact outputs, records, Undo."""

import datetime as dt
import json
import uuid

import pytest
from conftest import FakeContext, make_adult
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_sdk.errors import HauskraftError
from hauskraft_tasks import service
from hauskraft_tasks.schemas import TaskCreate
from hauskraft_tasks.tools import TOOLS

pytestmark = pytest.mark.integration
BY_NAME = {t.name: t for t in TOOLS}


def test_four_tools_with_their_contract() -> None:
    assert sorted(BY_NAME) == ["tasks.create", "tasks.delete", "tasks.list", "tasks.update"]
    assert BY_NAME["tasks.list"].annotations.read_only is True
    assert BY_NAME["tasks.delete"].annotations.destructive is True
    assert BY_NAME["tasks.create"].annotations.destructive is False
    assert BY_NAME["tasks.update"].annotations.idempotent is True
    assert {t.permission for t in TOOLS} == {"task.read", "task.create", "task.update", "task.delete"}
    assert {str(t.data_class) for t in TOOLS} == {"household"}
    assert all(not t.annotations.open_world for t in TOOLS)


def test_definitions_stay_within_the_budget() -> None:
    wire = [{"name": t.wire_name, "description": t.description, "parameters": t.parameters()} for t in TOOLS]
    assert len(json.dumps(wire)) <= 6000


async def test_create_records_and_offers_undo(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    tool = BY_NAME["tasks.create"]
    out = await tool.handler(ctx, me, tool.input_model.model_validate({"title": "Buy milk", "due_on": tomorrow}))
    task_id = out.output["task"]["id"]
    assert out.output["task"] == {"id": task_id, "title": "Buy milk", "done": False, "due_on": tomorrow}
    assert out.record is not None
    assert (out.record.type, out.record.id, out.record.label) == ("Task", task_id, "Buy milk")
    assert out.summary_key == "tasks:tool.create.done"
    assert out.undo is not None
    assert (out.undo.tool, dict(out.undo.args)) == ("tasks.delete", {"task_id": task_id})
    assert [e["type"] for e in ctx.events] == ["hauskraft.task.created"]


async def test_completing_says_completed_and_undo_reopens(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    task = await service.create_task(ctx, me, TaskCreate(title="Water plants"))
    tool = BY_NAME["tasks.update"]
    out = await tool.handler(ctx, me, tool.input_model.model_validate({"task_id": str(task.id), "done": True}))
    assert out.summary_key == "tasks:tool.complete.done"
    assert out.undo is not None
    assert dict(out.undo.args) == {"task_id": str(task.id), "title": "Water plants", "done": False, "due_on": None}


async def test_renaming_says_updated(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    task = await service.create_task(ctx, me, TaskCreate(title="Old"))
    tool = BY_NAME["tasks.update"]
    out = await tool.handler(ctx, me, tool.input_model.model_validate({"task_id": str(task.id), "title": "New"}))
    assert out.summary_key == "tasks:tool.update.done"
    assert out.record is not None
    assert out.record.label == "New"
    assert out.undo is not None
    assert dict(out.undo.args)["title"] == "Old"


async def test_delete_has_a_preview_and_no_undo(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    task = await service.create_task(ctx, me, TaskCreate(title="Old flyers"))
    tool = BY_NAME["tasks.delete"]
    args = tool.input_model.model_validate({"task_id": str(task.id)})
    assert tool.preview is not None
    preview = await tool.preview(ctx, me, args)
    assert preview is not None
    assert preview.label == "Old flyers"
    out = await tool.handler(ctx, me, args)
    assert out.output == {"deleted": True, "id": str(task.id)}
    assert out.summary_key == "tasks:tool.delete.done"
    assert out.undo is None


async def test_list_is_compact_and_capped(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    for i in range(3):
        await service.create_task(ctx, me, TaskCreate(title=f"Item {i}"))
    tool = BY_NAME["tasks.list"]
    out = await tool.handler(ctx, me, tool.input_model.model_validate({"limit": 2}))
    assert len(out.output["items"]) == 2
    assert set(out.output["items"][0]) == {"id", "title", "done", "due_on"}
    assert out.output["total"] >= 3
    with pytest.raises(ValueError, match="limit"):
        tool.input_model.model_validate({"limit": 51})


async def test_unknown_task_has_a_code_the_model_can_use(ctx: FakeContext, db_session: AsyncSession) -> None:
    me = await make_adult(db_session, "Mia")
    tool = BY_NAME["tasks.update"]
    with pytest.raises(HauskraftError) as caught:
        await tool.handler(ctx, me, tool.input_model.model_validate({"task_id": str(uuid.uuid4()), "done": True}))
    assert caught.value.code == "task_not_found"
