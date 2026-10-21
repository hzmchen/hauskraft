# SPDX-License-Identifier: MIT
"""Tasks REST API (M0S-E07-03). Contract table: docs/backlog/m0-star/E07-tasks-plugin.md.

Mounted by core at ``/api/v1/tasks`` with tag ``tasks``, so operation ids are ``tasks_<function>``.
Every route needs a session; writes also need the CSRF token (both enforced by ``ctx.current_actor``).
No ``from __future__ import annotations`` here: FastAPI must see the local ``CurrentActor`` alias.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from hauskraft_sdk import Actor, PluginContext
from hauskraft_tasks import service
from hauskraft_tasks.schemas import Sort, Status, TaskCreate, TaskOut, TaskPage, TaskPatch

ERRORS: dict[int | str, dict[str, str]] = {
    401: {"description": "Not signed in"},
    422: {"description": "Validation failed"},
}


def build_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    CurrentActor = Annotated[Actor, Depends(ctx.current_actor)]

    @router.get("", responses=ERRORS)
    async def list(
        actor: CurrentActor,
        status: Status = "all",
        sort: Sort = "-created_at",
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    ) -> TaskPage:
        async with ctx.db_session() as session:
            page = await service.list_tasks(session, status, sort, limit, offset)
            return await service.task_page(session, page, limit, offset)

    @router.post("", status_code=201, responses={**ERRORS, 403: {"description": "Forbidden"}})
    async def create(body: TaskCreate, actor: CurrentActor, request: Request, response: Response) -> TaskOut:
        task = await service.create_task(ctx, actor, body)
        response.headers["Location"] = str(request.url_for("get", task_id=task.id).path)
        async with ctx.db_session() as session:
            return await service.task_out(session, task)

    @router.get("/{task_id}", responses={**ERRORS, 404: {"description": "Not found"}})
    async def get(task_id: uuid.UUID, actor: CurrentActor) -> TaskOut:
        async with ctx.db_session() as session:
            return await service.task_out(session, await service.get_task(session, task_id))

    @router.patch(
        "/{task_id}",
        responses={
            **ERRORS,
            403: {"description": "Forbidden"},
            404: {"description": "Not found"},
            409: {"description": "Conflict"},
        },
    )
    async def update(task_id: uuid.UUID, body: TaskPatch, actor: CurrentActor) -> TaskOut:
        task = await service.update_task(ctx, actor, task_id, body)
        async with ctx.db_session() as session:
            return await service.task_out(session, task)

    @router.delete(
        "/{task_id}",
        status_code=204,
        responses={**ERRORS, 403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
    )
    async def delete(task_id: uuid.UUID, actor: CurrentActor) -> Response:
        await service.delete_task(ctx, actor, task_id)
        return Response(status_code=204)

    return router
