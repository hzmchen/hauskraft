# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alembic environment for core and plugin branches (M0S-E04-01). Async engine via psycopg 3."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from hauskraft_core.db.migrations import target_metadata
from hauskraft_core.settings import Settings

config = context.config
settings: Settings = config.attributes.get("settings") or Settings()
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))


def _include_object(obj: object, name: str | None, type_: str, reflected: bool, compare_to: object) -> bool:
    """Skip tables a plugin declares only so its foreign keys resolve (core owns them)."""
    info = getattr(obj, "info", {}) or {}
    return not (type_ == "table" and info.get("hauskraft_reference_only"))


def _configure(connection: Connection | None = None) -> None:
    context.configure(
        include_object=_include_object,
        connection=connection,
        url=None if connection is not None else config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata(settings),
        compare_type=True,
        literal_binds=connection is None,
    )


def _run_sync(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    _configure()
    with context.begin_transaction():
        context.run_migrations()
else:
    existing = config.attributes.get("connection")
    if existing is not None:
        _run_sync(existing)
    else:
        asyncio.run(_run_async())
