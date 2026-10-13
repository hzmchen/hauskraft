# SPDX-License-Identifier: MIT
"""M0S-E07-01: the tasks plugin owns its table and migration branch."""

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_tasks.models import Task, metadata

pytestmark = pytest.mark.integration


async def _user(db_session: AsyncSession) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO users (id, username, display_name, password_hash) VALUES (:id, :u, 'T', 'x')"),
        {"id": user_id, "u": f"t{user_id.hex[:8]}"},
    )
    return user_id


async def test_defaults(db_session: AsyncSession) -> None:
    user = await _user(db_session)
    task = Task(id=uuid.uuid4(), title="Buy milk", created_by=user, updated_by=user)
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    assert task.done is False
    assert task.done_at is None
    assert task.due_on is None
    assert task.data_class == "household"
    assert task.version == 1
    assert task.created_at is not None


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
async def test_title_check(db_session: AsyncSession, title: str) -> None:
    user = await _user(db_session)
    db_session.add(Task(id=uuid.uuid4(), title=title, created_by=user, updated_by=user))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_creator_must_exist(db_session: AsyncSession) -> None:
    ghost = uuid.uuid4()
    db_session.add(Task(id=uuid.uuid4(), title="x", created_by=ghost, updated_by=ghost))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_indexes(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename = 'tasks'"))
    defs = " ".join(r[0] for r in rows)
    assert "(done, created_at DESC)" in defs
    assert "WHERE (due_on IS NOT NULL)" in defs


async def test_migration_branch_is_labelled_with_the_plugin_id(db_session: AsyncSession) -> None:
    versions = {r[0] for r in await db_session.execute(text("SELECT version_num FROM alembic_version"))}
    assert any(v.startswith("tasks_") for v in versions), versions


def test_plugin_owns_its_metadata() -> None:
    assert "tasks" in metadata.tables
    assert metadata.naming_convention.get("pk") == "pk_%(table_name)s"


def test_entrypoint_registers(db_settings: Any) -> None:
    from hearthos_sdk import Plugin, PluginRegistration
    from hearthos_tasks.plugin import plugin

    assert isinstance(plugin, Plugin)
    assert plugin.id == "org.hearthos.tasks"

    class Ctx:
        plugin_id = "org.hearthos.tasks"

        async def current_actor(self) -> None:
            return None

    registration = plugin.register(Ctx())  # type: ignore[arg-type]
    assert isinstance(registration, PluginRegistration)
    assert registration.metadata is metadata
