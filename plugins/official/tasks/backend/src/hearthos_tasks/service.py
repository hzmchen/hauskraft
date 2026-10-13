# SPDX-License-Identifier: MIT
"""Task service (M0S-E07-02): pure functions over ``PluginContext``.

Every write calls ``ctx.authorize`` first, changes the row and emits exactly one event in the same unit of
work (``ctx.db_session()``). The list is shared (decision D3): any adult may edit or delete any task.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_sdk import Actor, DataClass, PluginContext, ResourceRef
from hearthos_sdk.errors import ConflictError, NotFoundError
from hearthos_sdk.events import (
    TaskChanges,
    TaskCompletedData,
    TaskCreatedData,
    TaskDeletedData,
    TaskSnapshot,
    TaskUpdatedData,
)
from hearthos_tasks.models import Task, users
from hearthos_tasks.schemas import Sort, Status, TaskCreate, TaskOut, TaskPage, TaskPatch, UserRef

DATA_CLASS = DataClass.HOUSEHOLD
CAPABILITY = "graph:write:Task"


def subject(task_id: uuid.UUID) -> str:
    return f"task/{task_id}"


def snapshot(task: Task) -> TaskSnapshot:
    return TaskSnapshot(id=task.id, title=task.title, done=task.done, due_on=task.due_on, version=task.version)


async def _authorize(ctx: PluginContext, actor: Actor, verb: str, task_id: uuid.UUID | None) -> None:
    await ctx.authorize(
        actor, f"task.{verb}", ResourceRef("Task", str(task_id) if task_id else None), DATA_CLASS, CAPABILITY
    )


async def create_task(ctx: PluginContext, actor: Actor, body: TaskCreate) -> Task:
    async with ctx.db_session() as session:
        task_id = uuid.uuid4()
        await _authorize(ctx, actor, "create", task_id)
        now = dt.datetime.now(dt.UTC)
        task = Task(
            id=task_id,
            title=body.title,
            due_on=body.due_on,
            done=False,
            version=1,
            created_by=uuid.UUID(actor.id),
            updated_by=uuid.UUID(actor.id),
            created_at=now,
            updated_at=now,
        )
        session.add(task)
        await session.flush()
        await ctx.emit("hearthos.task.created", subject(task.id), TaskCreatedData(task=snapshot(task)), DATA_CLASS)
    return task


async def _get_for_update(session: AsyncSession, task_id: uuid.UUID) -> Task:
    task = (await session.execute(select(Task).where(Task.id == task_id).with_for_update())).scalar_one_or_none()
    if task is None:
        raise NotFoundError("Task not found.")
    return task


async def update_task(ctx: PluginContext, actor: Actor, task_id: uuid.UUID, patch: TaskPatch) -> Task:
    async with ctx.db_session() as session:
        task = await _get_for_update(session, task_id)
        if patch.version is not None and patch.version != task.version:
            raise ConflictError(
                "version_conflict",
                "The task was changed meanwhile; reload and try again.",
                extra={"current_version": task.version},
            )
        fields = patch.model_fields_set - {"version"}
        changes: dict[str, tuple[Any, Any]] = {}
        for name in ("title", "due_on", "done"):
            if name in fields:
                new = getattr(patch, name)
                if name in ("title", "done") and new is None:
                    continue
                if getattr(task, name) != new:
                    changes[name] = (getattr(task, name), new)
        if not changes:
            return task
        await _authorize(ctx, actor, "update", task.id)
        now = dt.datetime.now(dt.UTC)
        for name, (_, new) in changes.items():
            setattr(task, name, new)
        completed = changes.get("done") == (False, True)
        if "done" in changes:
            task.done_at = now if task.done else None
        task.version += 1
        task.updated_by = uuid.UUID(actor.id)
        task.updated_at = now
        await session.flush()
        if completed:
            await ctx.emit(
                "hearthos.task.completed",
                subject(task.id),
                TaskCompletedData(task=snapshot(task), completed_at=now),
                DATA_CLASS,
            )
        else:
            await ctx.emit(
                "hearthos.task.updated",
                subject(task.id),
                TaskUpdatedData(task=snapshot(task), changes=TaskChanges(**changes)),
                DATA_CLASS,
            )
    return task


async def delete_task(ctx: PluginContext, actor: Actor, task_id: uuid.UUID) -> None:
    async with ctx.db_session() as session:
        task = await _get_for_update(session, task_id)
        await _authorize(ctx, actor, "delete", task.id)
        last = snapshot(task)
        await session.delete(task)
        await session.flush()
        await ctx.emit("hearthos.task.deleted", subject(task_id), TaskDeletedData(task=last), DATA_CLASS)


@dataclass
class Page:
    items: list[Task]
    total: int


async def list_tasks(session: AsyncSession, status: Status, sort: Sort, limit: int, offset: int) -> Page:
    query = select(Task)
    if status == "open":
        query = query.where(Task.done.is_(False))
    elif status == "done":
        query = query.where(Task.done.is_(True))
    orders: dict[str, list[ColumnElement[Any]]] = {
        "created_at": [Task.created_at.asc(), Task.id.asc()],
        "-created_at": [Task.created_at.desc(), Task.id.desc()],
        "due_on": [Task.due_on.asc().nulls_last(), Task.created_at.desc()],
        "-due_on": [Task.due_on.desc().nulls_last(), Task.created_at.desc()],
    }
    order = orders[sort]
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = (await session.execute(query.order_by(*order).limit(limit).offset(offset))).scalars().all()
    return Page(list(items), int(total))


async def get_task(session: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    return task


async def _names(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    rows = await session.execute(select(users.c.id, users.c.display_name).where(users.c.id.in_(ids)))
    return {uid: name for uid, name in rows.all()}


async def task_page(session: AsyncSession, page: Page, limit: int, offset: int) -> TaskPage:
    names = await _names(session, {t.created_by for t in page.items} | {t.updated_by for t in page.items})
    return TaskPage(items=[_out(t, names) for t in page.items], total=page.total, limit=limit, offset=offset)


async def task_out(session: AsyncSession, task: Task) -> TaskOut:
    return _out(task, await _names(session, {task.created_by, task.updated_by}))


def _out(task: Task, names: dict[uuid.UUID, str]) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        done=task.done,
        done_at=task.done_at,
        due_on=task.due_on,
        data_class=task.data_class,
        version=task.version,
        created_by=UserRef(id=task.created_by, display_name=names.get(task.created_by, "")),
        updated_by=UserRef(id=task.updated_by, display_name=names.get(task.updated_by, "")),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
