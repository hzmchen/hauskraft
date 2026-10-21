# SPDX-License-Identifier: MIT
"""Demo tasks (M0S-E07-04), invoked by core's seed command through ``PluginRegistration.seed``.

Each fixture task has a key; its id is derived from the key (UUIDv5), so running the seed again changes
nothing. Seeding goes through the service, so it authorizes and emits events like any other write.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any

from hearthos_sdk import Actor, PluginContext
from hearthos_tasks import service
from hearthos_tasks.models import Task
from hearthos_tasks.schemas import TaskCreate, TaskPatch

SEED_NAMESPACE = uuid.UUID("6f1d3c1e-2b8a-5f0e-9c4d-7a1b2c3d4e5f")


def seed_id(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"org.hearthos.tasks/{key}")


async def seed(ctx: PluginContext, fixture: Mapping[str, Any]) -> None:
    """``fixture`` = the plugin's section of the household fixture plus ``actors`` ({key: Actor})."""
    actors: Mapping[str, Actor] = fixture["actors"]
    today = dt.date.today()
    for item in fixture.get("tasks", []):
        task_id = seed_id(item["key"])
        async with ctx.db_session() as session:
            if await session.get(Task, task_id) is not None:
                continue
        actor = actors[item["created_by"]]
        due = today + dt.timedelta(days=int(item["due_in_days"])) if "due_in_days" in item else None
        await service.create_task(ctx, actor, TaskCreate(title=item["title"], due_on=due), task_id=task_id)
        if item.get("done"):
            await service.update_task(ctx, actor, task_id, TaskPatch(done=True))
