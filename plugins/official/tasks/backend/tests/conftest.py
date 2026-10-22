# SPDX-License-Identifier: MIT
"""A fake PluginContext for service tests: records authorize calls and emitted events.

``db_session()`` hands out the test's own session inside a savepoint, so a failing write rolls back like
core's unit of work does, and the outer test transaction still cleans everything up.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_sdk import Actor, DataClass, ResourceRef


@dataclass
class FakeContext:
    session: AsyncSession
    plugin_id: str = "dev.hauskraft.tasks"
    authorized: list[tuple[str, str, ResourceRef, str, str]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    fail_emit: bool = False
    _actor: Actor | None = None

    @asynccontextmanager
    async def db_session(self) -> AsyncIterator[AsyncSession]:
        async with self.session.begin_nested():
            yield self.session

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> None:
        self._actor = actor
        self.authorized.append((actor.id, action, resource, str(data_class), capability))

    async def emit(self, event_type: str, subject: str, data: Any, data_class: DataClass | str) -> str:
        if self.fail_emit:
            raise RuntimeError("emit failed on purpose")
        dumped = data.model_dump(mode="json", by_alias=True) if hasattr(data, "model_dump") else data
        self.events.append(
            {
                "type": event_type,
                "subject": subject,
                "data": dumped,
                "dataclass": str(data_class),
                "actorid": self._actor.id if self._actor else None,
            }
        )
        return str(uuid.uuid4())


async def make_adult(session: AsyncSession, name: str) -> Actor:
    user_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO users (id, username, display_name, password_hash) VALUES (:id, :u, :d, 'x')"),
        {"id": user_id, "u": f"t{user_id.hex[:10]}", "d": name},
    )
    return Actor(id=str(user_id), role="adult", display_name=name)


@pytest.fixture
def ctx(db_session: AsyncSession) -> FakeContext:
    return FakeContext(db_session)
