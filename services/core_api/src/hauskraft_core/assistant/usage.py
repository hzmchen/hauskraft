# SPDX-License-Identifier: AGPL-3.0-or-later
"""The usage overview (M2S-E08-02): totals by day, member, model or kind, with a cost estimate.

Dates are inclusive and counted in the household time zone. Requests whose tokens the server didn't report count
as ``unknown_requests``. With prices set, cost = input tokens * input price + output tokens * output price per
million, rounded to cents.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.models import AssistantUsage, User

GroupBy = Literal["day", "user", "model", "kind"]
DEFAULT_DAYS = 30


@dataclass
class Bucket:
    key: str
    label: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    unknown_requests: int = 0

    def add(self, row: AssistantUsage) -> None:
        self.requests += 1
        if row.input_tokens is None and row.output_tokens is None:
            self.unknown_requests += 1
        self.input_tokens += row.input_tokens or 0
        self.output_tokens += row.output_tokens or 0


@dataclass
class UsageReport:
    start: dt.date
    end: dt.date
    group_by: GroupBy
    totals: Bucket
    groups: list[Bucket] = field(default_factory=list)
    cost: float | None = None


async def report(
    session: AsyncSession,
    timezone: str,
    group_by: GroupBy,
    start: dt.date | None,
    end: dt.date | None,
    prices: dict[str, float | None],
) -> UsageReport:
    zone = ZoneInfo(timezone)
    today = dt.datetime.now(zone).date()
    end = end or today
    start = start or end - dt.timedelta(days=DEFAULT_DAYS - 1)
    lower = dt.datetime.combine(start, dt.time(), zone)
    upper = dt.datetime.combine(end + dt.timedelta(days=1), dt.time(), zone)
    rows = (
        await session.execute(
            select(AssistantUsage, User.display_name)
            .outerjoin(User, User.id == AssistantUsage.user_id)
            .where(AssistantUsage.created_at >= lower, AssistantUsage.created_at < upper)
        )
    ).all()
    totals = Bucket("total", "total")
    groups: dict[str, Bucket] = defaultdict(lambda: Bucket("", ""))
    for row, name in rows:
        totals.add(row)
        if group_by == "day":
            key = label = row.created_at.astimezone(zone).date().isoformat()
        elif group_by == "user":
            key, label = (str(row.user_id) if row.user_id else "unknown"), (name or "")
        elif group_by == "model":
            key = label = row.model or "unknown"
        else:
            key = label = row.kind
        bucket = groups[key]
        bucket.key, bucket.label = key, label
        bucket.add(row)
    ordered = (
        sorted(groups.values(), key=lambda b: b.key)
        if group_by == "day"
        else sorted(groups.values(), key=lambda b: (-b.input_tokens, b.key))
    )
    cost = None
    if prices.get("input_per_million") is not None or prices.get("output_per_million") is not None:
        cost = round(
            totals.input_tokens * (prices.get("input_per_million") or 0) / 1_000_000
            + totals.output_tokens * (prices.get("output_per_million") or 0) / 1_000_000,
            2,
        )
    return UsageReport(start=start, end=end, group_by=group_by, totals=totals, groups=ordered, cost=cost)
