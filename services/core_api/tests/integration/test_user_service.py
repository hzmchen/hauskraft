# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-01: the user service (authorize first, lowercase usernames, adult only)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hearthos_core.db.models import User, UserRole
from hearthos_core.policy import Decision
from hearthos_core.settings import Settings
from hearthos_core.uow import UnitOfWork
from hearthos_core.users.service import (
    SYSTEM_ACTOR,
    RoleNotEnabledInM0Error,
    UsernameTakenError,
    create_user,
    set_password,
)
from hearthos_sdk import Actor, DataClass, ResourceRef
from hearthos_sdk.errors import HearthosError

pytestmark = pytest.mark.integration


class SpyPolicy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ResourceRef]] = []

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision:
        self.calls.append((action, resource))
        return Decision.ALLOW


def _uow(db_session: AsyncSession, settings: Settings, policy: SpyPolicy | None = None) -> UnitOfWork:
    factory = async_sessionmaker(bind=db_session.bind, join_transaction_mode="create_savepoint", expire_on_commit=False)
    return UnitOfWork(factory, policy or SpyPolicy(), settings)


async def test_create_user_lowercases_and_hashes(db_session: AsyncSession, db_settings: Settings) -> None:
    spy = SpyPolicy()
    async with _uow(db_session, db_settings, spy) as uow:
        user = await create_user(
            uow, SYSTEM_ACTOR, username="  Anna ", display_name="Anna Adult", password="correct-horse-battery"
        )
    stored = await db_session.get(User, user.id)
    assert stored is not None
    assert stored.username == "anna"
    assert stored.role is UserRole.ADULT
    assert stored.password_hash.startswith("$argon2id$")
    assert spy.calls == [("user.create", ResourceRef("User"))]


async def test_duplicate_username(db_session: AsyncSession, db_settings: Settings) -> None:
    async with _uow(db_session, db_settings) as uow:
        await create_user(uow, SYSTEM_ACTOR, username="dup", display_name="A", password="correct-horse-battery")
    with pytest.raises(UsernameTakenError) as err:
        async with _uow(db_session, db_settings) as uow:
            await create_user(uow, SYSTEM_ACTOR, username="DUP", display_name="B", password="correct-horse-battery")
    assert err.value.status == 409
    assert err.value.code == "username_taken"


@pytest.mark.parametrize("role", ["owner", "teen", "kid", "guest"])
async def test_only_adults_can_be_created(db_session: AsyncSession, db_settings: Settings, role: str) -> None:
    with pytest.raises(RoleNotEnabledInM0Error) as err:
        async with _uow(db_session, db_settings) as uow:
            await create_user(
                uow, SYSTEM_ACTOR, username=f"r{role}", display_name="R", password="correct-horse-battery", role=role
            )
    assert err.value.status == 422


@pytest.mark.parametrize("username", ["a", "has space", "x" * 33, "ümlaut", "-dash-first"])
async def test_username_rules(db_session: AsyncSession, db_settings: Settings, username: str) -> None:
    with pytest.raises(HearthosError) as err:
        async with _uow(db_session, db_settings) as uow:
            await create_user(uow, SYSTEM_ACTOR, username=username, display_name="X", password="correct-horse-battery")
    assert err.value.status == 422


async def test_set_password(db_session: AsyncSession, db_settings: Settings) -> None:
    async with _uow(db_session, db_settings) as uow:
        user = await create_user(uow, SYSTEM_ACTOR, username="pwd", display_name="P", password="correct-horse-battery")
    old_hash = user.password_hash
    async with _uow(db_session, db_settings) as uow:
        await set_password(uow, SYSTEM_ACTOR, "pwd", "another-long-password")
    stored = await db_session.get(User, user.id, populate_existing=True)
    assert stored is not None
    assert stored.password_hash != old_hash
