# SPDX-License-Identifier: AGPL-3.0-or-later
"""First-run setup service (M1S-E03-01, ADR 0017).

While no account exists, anyone who reaches the app may create the household and become its first owner. The check
and the inserts run in one transaction under a transaction-scoped advisory lock, so of several simultaneous requests
exactly one succeeds. The service acts as the system actor (``setup.complete``) and emits exactly one event,
``hauskraft.user.created``, with the new owner as its actor.
"""

from __future__ import annotations

from sqlalchemy import exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.auth.deps import actor_for
from hauskraft_core.db.models import User, UserRole
from hauskraft_core.events.outbox import emit
from hauskraft_core.household.service import KEYS, Household, check_timezone
from hauskraft_core.settings_store import repository
from hauskraft_core.uow import UnitOfWork
from hauskraft_core.users.service import SYSTEM_ACTOR, insert_account, user_ref
from hauskraft_sdk import ResourceRef
from hauskraft_sdk.errors import ConflictError
from hauskraft_sdk.events import UserData

SETUP_LOCK = 0x48534B52  # any constant; it only has to be the same for every setup request


class SetupDoneError(ConflictError):
    def __init__(self) -> None:
        super().__init__("setup_done", "This household is already set up. Sign in instead.")


async def setup_required(session: AsyncSession) -> bool:
    return not await session.scalar(select(exists().where(User.id.is_not(None))))


async def complete_setup(
    uow: UnitOfWork, household: Household, *, username: str, display_name: str, password: str
) -> User:
    """Store the household settings and create the first owner; 409 ``setup_done`` once any account exists."""
    await uow.authorize(SYSTEM_ACTOR, "setup.complete", ResourceRef("Household"), "household", "setup:complete")
    check_timezone(household.timezone)
    await uow.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SETUP_LOCK})
    if not await setup_required(uow.session):
        raise SetupDoneError
    owner = await insert_account(
        uow,
        username=username,
        display_name=display_name,
        password=password,
        role=UserRole.OWNER,
        locale=household.locale,
    )
    for field, key in KEYS.items():
        await repository.upsert(uow.session, key, getattr(household, field), owner.id)
    uow.actor = actor_for(owner)  # the owner created themself: the event's actor
    data = UserData(user=user_ref(owner))
    await emit("hauskraft.user.created", f"user/{owner.id}", data.model_dump(mode="json"), "personal")
    return owner
