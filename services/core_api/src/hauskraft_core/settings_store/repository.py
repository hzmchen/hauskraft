# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reads and upserts on ``deployment_settings``. Callers own the transaction and the ``authorize()`` call."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.models import DeploymentSetting


async def get(session: AsyncSession, key: str) -> Any:
    return await session.scalar(select(DeploymentSetting.value).where(DeploymentSetting.key == key))


async def get_for_update(session: AsyncSession, key: str) -> Any:
    """Lock the row (if any) so two concurrent changes report a consistent ``from``."""
    return await session.scalar(select(DeploymentSetting.value).where(DeploymentSetting.key == key).with_for_update())


async def upsert(session: AsyncSession, key: str, value: Any, updated_by: uuid.UUID | None) -> None:
    stmt = insert(DeploymentSetting).values(key=key, value=value, updated_by=updated_by)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[DeploymentSetting.key],
            set_={"value": stmt.excluded.value, "updated_by": stmt.excluded.updated_by, "updated_at": func.now()},
        )
    )
