# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/household`` (M1S-E04-01): every member reads it, owners change it."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.db.session import DbSession
from hauskraft_core.household.schemas import HouseholdOut, HouseholdPatch
from hauskraft_core.household.service import read_household, update_household
from hauskraft_core.uow import UnitOfWork

router = APIRouter(tags=["household"])


@router.get("/household", responses={401: {}})
async def read(request: Request, db: DbSession, _: CurrentSession) -> HouseholdOut:
    return HouseholdOut.of(await read_household(db, request.app.state.settings))


@router.patch("/household", responses={401: {}, 403: {}, 422: {}})
async def update(body: HouseholdPatch, request: Request, resolved: CurrentSession) -> HouseholdOut:
    """Change any subset of name, time zone and default language (owners only)."""
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        household = await update_household(
            uow,
            actor_for(resolved[1]),
            request.app.state.settings,
            name=body.name,
            timezone=body.timezone,
            locale=body.locale,
        )
    return HouseholdOut.of(household)
