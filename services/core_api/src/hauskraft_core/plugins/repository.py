# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``plugins`` table: one record per discovered plugin, upserted at startup (M0S-E06-04)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.db.models import PluginRecord
from hearthos_core.plugins.loader import LoadedPlugin


async def upsert_loaded(session: AsyncSession, plugins: Iterable[LoadedPlugin]) -> dict[str, bool]:
    """Record every discovered plugin and return ``{id: enabled}`` (``enabled`` is owned by the database)."""
    now = dt.datetime.now(dt.UTC)
    for p in plugins:
        values = {
            "version": p.manifest.get("version"),
            "kind": p.kind,
            "manifest": p.manifest,
            "manifest_sha256": p.manifest_sha256,
            "loaded_at": None if p.load_error else now,
            "load_error": p.load_error,
        }
        stmt = insert(PluginRecord).values(id=p.id, **values)
        await session.execute(stmt.on_conflict_do_update(index_elements=[PluginRecord.id], set_=values))
    rows = await session.execute(select(PluginRecord.id, PluginRecord.enabled))
    return {pid: enabled for pid, enabled in rows.all()}
