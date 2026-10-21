# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dashboard layouts (M0S-E08-06). Writes call ``authorize()`` first.

A layout is per-user configuration (spec §9: DashboardLayout is a configuration entity, not part of the
graph), so saving it emits no domain event in M0*, like account and session bookkeeping.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.dashboard.schemas import COLUMNS, DashboardCell
from hearthos_core.db.models import DashboardLayout
from hearthos_core.uow import UnitOfWork
from hearthos_sdk import Actor, ResourceRef


async def stored_layout(session: AsyncSession, user_id: uuid.UUID, dashboard_id: str) -> list[DashboardCell] | None:
    raw = await session.scalar(
        select(DashboardLayout.layout).where(
            DashboardLayout.user_id == user_id, DashboardLayout.dashboard_id == dashboard_id
        )
    )
    return None if raw is None else [DashboardCell.model_validate(cell) for cell in raw]


def default_layout(widgets: Iterable[tuple[str, dict[str, Any]]]) -> list[DashboardCell]:
    """Place each contributed widget at its default size, left to right, wrapping at 12 columns."""
    cells: list[DashboardCell] = []
    x = y = row_height = 0
    for plugin_id, widget in widgets:
        size = widget.get("default_size") or {}
        w = max(1, min(COLUMNS, int(size.get("w", 4))))
        h = max(1, int(size.get("h", 4)))
        if x + w > COLUMNS:
            x, y, row_height = 0, y + row_height, 0
        cells.append(
            DashboardCell(
                i=f"{plugin_id}/{widget['id']}", plugin_id=plugin_id, widget_id=widget["id"], x=x, y=y, w=w, h=h
            )
        )
        x += w
        row_height = max(row_height, h)
    return cells


async def save_layout(
    uow: UnitOfWork, actor: Actor, dashboard_id: str, cells: list[DashboardCell]
) -> list[DashboardCell]:
    await uow.authorize(
        actor,
        "dashboard.layout.set",
        ResourceRef("DashboardLayout", f"{actor.id}/{dashboard_id}"),
        "personal",
        "dashboard:write",
    )
    layout = [cell.model_dump() for cell in cells]
    stmt = insert(DashboardLayout).values(user_id=uuid.UUID(actor.id), dashboard_id=dashboard_id, layout=layout)
    await uow.session.execute(
        stmt.on_conflict_do_update(
            index_elements=[DashboardLayout.user_id, DashboardLayout.dashboard_id],
            set_={"layout": stmt.excluded.layout, "updated_at": func.now()},
        )
    )
    return cells
