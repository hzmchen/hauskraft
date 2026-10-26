# SPDX-License-Identifier: MIT
"""The tasks plugin's agent tools (M2S-E02-04, ADR 0019).

Four coarse tools instead of many fine ones; outputs carry only what a model needs (id, title, done, due date) and
lists are capped. Writes go through the service functions, so they authorize first and emit one event each.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from hauskraft_sdk import Actor, PluginContext
from hauskraft_sdk.errors import NotFoundError
from hauskraft_sdk.tools import RecordRef, ToolAnnotations, ToolOutcome, ToolSpec, UndoCall
from hauskraft_tasks import service
from hauskraft_tasks.models import Task
from hauskraft_tasks.schemas import DueOn, Status, TaskCreate, TaskPatch, Title

NS = "tasks:tool."


class TaskNotFoundError(NotFoundError):
    code = "task_not_found"


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListArgs(_Args):
    status: Status = Field(default="open", description="open (default), done or all")
    due_before: DueOn = Field(default=None, description="Only tasks due before this date (YYYY-MM-DD).")
    limit: Annotated[int, Field(ge=1, le=50)] = 20


class CreateArgs(_Args):
    title: Title
    due_on: DueOn = Field(default=None, description="Due date, YYYY-MM-DD, in the household's time zone.")


class UpdateArgs(_Args):
    task_id: uuid.UUID
    title: Title | None = None
    done: bool | None = None
    due_on: DueOn = Field(default=None, description="New due date; null removes it.")


class DeleteArgs(_Args):
    task_id: uuid.UUID


def compact(task: Task) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "title": task.title,
        "done": task.done,
        "due_on": task.due_on.isoformat() if task.due_on else None,
    }


def _record(task: Task) -> RecordRef:
    return RecordRef(type="Task", id=str(task.id), label=task.title)


async def _find(ctx: PluginContext, task_id: uuid.UUID) -> Task:
    async with ctx.db_session() as session:
        try:
            return await service.get_task(session, task_id)
        except NotFoundError as exc:
            raise TaskNotFoundError(f"There is no task with id {task_id}.") from exc


async def list_handler(ctx: PluginContext, actor: Actor, args: ListArgs) -> ToolOutcome:
    async with ctx.db_session() as session:
        page = await service.list_tasks(session, args.status, "-created_at", args.limit, 0, due_before=args.due_before)
    return ToolOutcome(output={"items": [compact(t) for t in page.items], "total": page.total})


async def create_handler(ctx: PluginContext, actor: Actor, args: CreateArgs) -> ToolOutcome:
    task = await service.create_task(ctx, actor, TaskCreate(title=args.title, due_on=args.due_on))
    return ToolOutcome(
        output={"task": compact(task)},
        record=_record(task),
        summary_key=NS + "create.done",
        undo=UndoCall(tool="tasks.delete", args={"task_id": str(task.id)}),
    )


async def update_handler(ctx: PluginContext, actor: Actor, args: UpdateArgs) -> ToolOutcome:
    before = await _find(ctx, args.task_id)
    previous = compact(before)
    patch = TaskPatch.model_validate({name: getattr(args, name) for name in args.model_fields_set - {"task_id"}})
    try:
        task = await service.update_task(ctx, actor, args.task_id, patch)
    except NotFoundError as exc:
        raise TaskNotFoundError(f"There is no task with id {args.task_id}.") from exc
    completed = not previous["done"] and task.done
    return ToolOutcome(
        output={"task": compact(task)},
        record=_record(task),
        summary_key=NS + ("complete.done" if completed else "update.done"),
        undo=UndoCall(
            tool="tasks.update",
            args={
                "task_id": previous["id"],
                "title": previous["title"],
                "done": previous["done"],
                "due_on": previous["due_on"],
            },
        ),
    )


async def delete_preview(ctx: PluginContext, actor: Actor, args: DeleteArgs) -> RecordRef | None:
    return _record(await _find(ctx, args.task_id))


async def delete_handler(ctx: PluginContext, actor: Actor, args: DeleteArgs) -> ToolOutcome:
    task = await _find(ctx, args.task_id)
    record = _record(task)
    await service.delete_task(ctx, actor, args.task_id)
    return ToolOutcome(output={"deleted": True, "id": str(args.task_id)}, record=record, summary_key=NS + "delete.done")


TOOLS = [
    ToolSpec(
        name="tasks.list",
        description="List the household's tasks, newest first: id, title, done, due date. Use it to find a task's id.",
        input_model=ListArgs,
        handler=list_handler,
        permission="task.read",
        annotations=ToolAnnotations(read_only=True, destructive=False, idempotent=True, open_world=False),
    ),
    ToolSpec(
        name="tasks.create",
        description="Add a task to the household's shared list, optionally with a due date.",
        input_model=CreateArgs,
        handler=create_handler,
        permission="task.create",
        annotations=ToolAnnotations(read_only=False, destructive=False, idempotent=False, open_world=False),
    ),
    ToolSpec(
        name="tasks.update",
        description="Change a task: rename it, mark it done or open again, or set or clear its due date.",
        input_model=UpdateArgs,
        handler=update_handler,
        permission="task.update",
        annotations=ToolAnnotations(read_only=False, destructive=False, idempotent=True, open_world=False),
    ),
    ToolSpec(
        name="tasks.delete",
        description="Delete a task for good. The app asks the person before it runs.",
        input_model=DeleteArgs,
        handler=delete_handler,
        permission="task.delete",
        annotations=ToolAnnotations(read_only=False, destructive=True, idempotent=True, open_world=False),
        preview=delete_preview,
    ),
]

__all__ = ["TOOLS", "TaskNotFoundError"]
