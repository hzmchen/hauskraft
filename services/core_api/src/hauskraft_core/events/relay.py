# SPDX-License-Identifier: AGPL-3.0-or-later
"""Log relay for the outbox (M0S-E10-03, ADR-0007).

A lifespan task polls every 2 seconds, takes up to 100 unpublished events with ``FOR UPDATE SKIP LOCKED``
(so several API processes never publish the same event), logs each as ``event.published`` and sets
``published_at``. Brokers and ``subscribes[]`` delivery replace the log line in later milestones.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hauskraft_core.db.models import OutboxEvent
from hauskraft_core.logging import get_logger

POLL_SECONDS = 2.0
BATCH_SIZE = 100

_log = get_logger("hauskraft.events")


async def publish_batch(sessions: async_sessionmaker[AsyncSession], batch_size: int = BATCH_SIZE) -> int:
    async with sessions() as session, session.begin():
        rows = (
            (
                await session.execute(
                    select(OutboxEvent)
                    .where(OutboxEvent.published_at.is_(None))
                    .order_by(OutboxEvent.time)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        now = dt.datetime.now(dt.UTC)
        for event in rows:
            _log.info(
                "event.published",
                event_id=str(event.id),
                type=event.type,
                source=event.source,
                subject=event.subject,
                dataclass=event.data_class,
            )
            event.published_at = now
            event.attempts += 1
        return len(rows)


async def run_relay(sessions: async_sessionmaker[AsyncSession], stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            while await publish_batch(sessions) == BATCH_SIZE and not stop.is_set():
                pass
        except Exception as exc:  # the database may be away; keep polling
            _log.warning("relay.failed", error_type=type(exc).__name__)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
