# SPDX-License-Identifier: AGPL-3.0-or-later
"""``GET /activity``: what happened, who did it, newest first (M0S-E10-03)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from hauskraft_core.auth.deps import CurrentActor
from hauskraft_core.db.models import OutboxEvent, User
from hauskraft_core.db.session import DbSession

router = APIRouter(tags=["activity"])


class ActivityActor(BaseModel):
    id: uuid.UUID | None
    display_name: str


class ActivityItem(BaseModel):
    id: uuid.UUID
    type: str
    time: dt.datetime
    actor: ActivityActor | None
    subject: str | None
    summary_key: str
    data: Any
    agentrunid: str | None = None  # the assistant run that acted for the actor (M2S-E04-07)


def summary_key(event_type: str) -> str:
    """i18n key for the web feed, e.g. ``hauskraft.task.created`` -> ``activity.task.created``."""
    return "activity." + event_type.removeprefix("hauskraft.")


@router.get("/activity", responses={401: {}, 422: {}})
async def list_(
    db: DbSession,
    actor: CurrentActor,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: dt.datetime | None = None,
) -> list[ActivityItem]:
    query = (
        select(OutboxEvent, User.display_name)
        .outerjoin(User, User.id == OutboxEvent.actor_id)
        .order_by(OutboxEvent.time.desc(), OutboxEvent.id.desc())
        .limit(limit)
    )
    if before is not None:
        query = query.where(OutboxEvent.time < before)
    rows = (await db.execute(query)).all()
    return [
        ActivityItem(
            id=event.id,
            type=event.type,
            time=event.time,
            subject=event.subject,
            summary_key=summary_key(event.type),
            data=event.envelope.get("data"),
            agentrunid=event.envelope.get("agentrunid"),
            actor=ActivityActor(id=event.actor_id, display_name=name) if event.actor_id else None,
        )
        for event, name in rows
    ]
