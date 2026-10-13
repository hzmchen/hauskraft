# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for API-level integration tests: an app on the migrated test database and real users."""

import asyncio
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hearthos_core.app import create_app
from hearthos_core.policy import NoOpPolicy
from hearthos_core.settings import Settings
from hearthos_core.uow import UnitOfWork
from hearthos_core.users.service import SYSTEM_ACTOR, create_user

PASSWORD = "correct-horse-battery"


@pytest.fixture
def api_settings(db_settings: Settings) -> Settings:
    return db_settings.model_copy(update={"allowed_origins": ["http://testserver"]})


@pytest.fixture
def client(api_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as c:
        yield c


@pytest.fixture
def make_user(api_settings: Settings) -> Callable[..., str]:
    """Create a committed adult with a unique username; returns the username."""

    def _make(display_name: str = "Test Adult", password: str = PASSWORD) -> str:
        username = "u" + uuid.uuid4().hex[:10]

        async def _create() -> None:
            engine = create_async_engine(api_settings.database_url, poolclass=NullPool)
            try:
                async with UnitOfWork(
                    async_sessionmaker(engine, expire_on_commit=False), NoOpPolicy(), api_settings
                ) as uow:
                    await create_user(
                        uow, SYSTEM_ACTOR, username=username, display_name=display_name, password=password
                    )
            finally:
                await engine.dispose()

        asyncio.run(_create())
        return username

    return _make
