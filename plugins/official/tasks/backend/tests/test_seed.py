# SPDX-License-Identifier: MIT
"""M0S-E07-04: seeded demo tasks go through the service (events) and are idempotent by fixture key."""

import datetime as dt
import json
from pathlib import Path

import pytest
from conftest import FakeContext, make_adult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_tasks.models import Task
from hauskraft_tasks.seed import seed

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[5]
DEMO = json.loads((REPO / "fixtures" / "household" / "demo.json").read_text())


async def test_demo_fixture_seeds_three_tasks_once(ctx: FakeContext, db_session: AsyncSession) -> None:
    demo = await make_adult(db_session, "Demo Adult")
    fixture = {**DEMO["plugins"]["dev.hauskraft.tasks"], "actors": {"demo": demo}}
    await seed(ctx, fixture)
    await seed(ctx, fixture)
    tasks = {
        t.title: t
        for t in (await db_session.execute(select(Task))).scalars()
        if t.title in {"Water the plants", "Take out recycling", "Book chimney sweep"}
    }
    assert set(tasks) == {"Water the plants", "Take out recycling", "Book chimney sweep"}
    assert tasks["Water the plants"].done is False
    assert tasks["Water the plants"].due_on is None
    assert tasks["Take out recycling"].done is False
    assert tasks["Take out recycling"].due_on == dt.date.today() + dt.timedelta(days=1)
    assert tasks["Book chimney sweep"].done is True
    assert all(str(t.created_by) == demo.id for t in tasks.values())
    created = [e for e in ctx.events if e["type"] == "hauskraft.task.created"]
    assert len(created) == 3
    assert [e["type"] for e in ctx.events].count("hauskraft.task.completed") == 1


def test_seed_is_registered() -> None:
    from hauskraft_tasks.plugin import plugin

    class Ctx:
        plugin_id = "dev.hauskraft.tasks"

        async def current_actor(self) -> None:
            return None

    assert plugin.register(Ctx()).seed is seed  # type: ignore[arg-type]
