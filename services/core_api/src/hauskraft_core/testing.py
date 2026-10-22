# SPDX-License-Identifier: AGPL-3.0-or-later
"""pytest plugin with database fixtures for integration tests (M0S-E04-04).

Registered as the ``pytest11`` entry point ``hauskraft``, so core and plugin tests get it automatically:

* ``pg_url`` (session): a ``postgres:16-alpine`` Testcontainers database, started once. Set
  ``HAUSKRAFT_TEST_DATABASE_URL`` to use an existing database instead (it must be disposable).
* ``db_settings`` (session): ``Settings`` for that database, migrated to ``heads`` (core plus every
  plugin under ``plugins/official``).
* ``db_session`` (function): an ``AsyncSession`` inside a transaction that is rolled back after the test.
  Commits inside the test only release a savepoint.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from hauskraft_core.db import migrations
from hauskraft_core.settings import Settings

REPO = Path(__file__).resolve().parents[4]
POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    external = os.environ.get("HAUSKRAFT_TEST_DATABASE_URL")
    if external:
        yield external
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def db_settings(pg_url: str) -> Settings:
    settings = Settings(
        env="test",
        database_url=pg_url,
        plugin_paths=[REPO / "plugins" / "official"],
        theme_paths=[REPO / "themes" / "builtin"],
        relay_enabled=False,
    )
    migrations.upgrade(settings)
    return settings


@pytest_asyncio.fixture
async def db_session(db_settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(db_settings.database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()
