# SPDX-License-Identifier: AGPL-3.0-or-later
"""Household settings services (M1S-E04-01). Stored as the deployment settings ``household.name``,
``household.timezone`` and ``household.locale``; unset values fall back to defaults (for example right after an
M0* upgrade). Writes call ``authorize()`` first and emit one ``hauskraft.settings.household_changed`` event that
lists only the changed fields; a write that changes nothing emits nothing.
"""

from __future__ import annotations

import uuid
import zoneinfo
from dataclasses import dataclass, fields, replace
from functools import cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.models import DeploymentSetting
from hauskraft_core.events.outbox import emit
from hauskraft_core.settings import Settings
from hauskraft_core.settings_store import repository
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor, ResourceRef
from hauskraft_sdk.errors import HauskraftError
from hauskraft_sdk.events import HouseholdChangedData

KEYS = {"name": "household.name", "timezone": "household.timezone", "locale": "household.locale"}
DEFAULT_NAME = "Household"
DEFAULT_LOCALE = "en"
SUBJECT = "setting/household"


class InvalidTimezoneError(HauskraftError):
    status = 422
    code = "invalid_timezone"
    title = "Unknown time zone"


@dataclass(frozen=True, slots=True)
class Household:
    name: str
    timezone: str
    locale: str


@cache
def _time_zones() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones())


def check_timezone(name: str) -> None:
    """Accept only IANA names this server knows (``zoneinfo``)."""
    if name not in _time_zones():
        raise InvalidTimezoneError(f"{name!r} is not a time zone this server knows.")


def changes(before: Household, after: Household) -> dict[str, dict[str, str]]:
    """``{field: {from, to}}`` for the fields that differ."""
    return {
        f.name: {"from": getattr(before, f.name), "to": getattr(after, f.name)}
        for f in fields(Household)
        if getattr(before, f.name) != getattr(after, f.name)
    }


async def read_household(session: AsyncSession, settings: Settings, *, for_update: bool = False) -> Household:
    query = select(DeploymentSetting.key, DeploymentSetting.value).where(DeploymentSetting.key.in_(KEYS.values()))
    stored: dict[str, object] = dict((await session.execute(query.with_for_update() if for_update else query)).all())

    def value(field: str, default: str) -> str:
        found = stored.get(KEYS[field])
        return found if isinstance(found, str) and found else default

    return Household(
        name=value("name", DEFAULT_NAME),
        timezone=value("timezone", settings.default_timezone),
        locale=value("locale", DEFAULT_LOCALE),
    )


async def update_household(
    uow: UnitOfWork,
    actor: Actor,
    settings: Settings,
    *,
    name: str | None = None,
    timezone: str | None = None,
    locale: str | None = None,
) -> Household:
    """Change any subset of the household settings (owners only, ``settings.household.set``)."""
    await uow.authorize(
        actor, "settings.household.set", ResourceRef("DeploymentSetting", "household"), "household", "settings:write"
    )
    if timezone is not None:
        check_timezone(timezone)
    before = await read_household(uow.session, settings, for_update=True)
    wanted = {"name": name, "timezone": timezone, "locale": locale}
    after = replace(before, **{field: value for field, value in wanted.items() if value is not None})
    diff = changes(before, after)
    if not diff:
        return before
    updated_by = uuid.UUID(actor.id) if actor.kind == "user" else None
    for field in diff:
        await repository.upsert(uow.session, KEYS[field], getattr(after, field), updated_by)
    data = HouseholdChangedData.model_validate({"changes": diff})
    await emit("hauskraft.settings.household_changed", SUBJECT, data.model_dump(mode="json"), "household")
    return after
