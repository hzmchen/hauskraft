# SPDX-License-Identifier: AGPL-3.0-or-later
"""User service (M0S-E05-01). Writes go through ``authorize()``; account events follow in M1* (ADR 0018)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.auth import sessions
from hauskraft_core.auth.passwords import check_password_policy, hash_password, verify_password
from hauskraft_core.db.models import User, UserRole
from hauskraft_core.events.outbox import emit
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor, ResourceRef
from hauskraft_sdk.errors import ConflictError, HauskraftError, NotFoundError
from hauskraft_sdk.events import Change, UserChanges, UserData, UserRef, UserUpdatedData

USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")
SYSTEM_ACTOR = Actor(id="system", role="owner", display_name="System", kind="system")
"""Acts for the CLI and the demo seed, which run without a signed-in user."""


ENABLED_ROLES = frozenset({UserRole.OWNER, UserRole.ADULT})
"""The roles accounts can have in M1* (ADR 0016); the other six exist in the enum only."""


class RoleNotEnabledError(HauskraftError):
    status = 422
    code = "role_not_enabled"
    title = "Role not available"

    def __init__(self, role: str) -> None:
        super().__init__(f"Accounts can be owners or adults, not {role!r}.")


class WrongPasswordError(HauskraftError):
    status = 422
    code = "wrong_password"
    title = "Wrong password"


class InvalidUsernameError(HauskraftError):
    status = 422
    code = "invalid_username"
    title = "Invalid username"


class UsernameTakenError(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__("username_taken", f"The username {username!r} is already taken.")


def normalise_username(raw: str) -> str:
    username = raw.strip().lower()
    if not USERNAME.match(username):
        raise InvalidUsernameError("Usernames have 2 to 32 characters: a-z, 0-9, '.', '_' or '-'.")
    return username


async def get_by_username(uow: UnitOfWork, username: str) -> User | None:
    result = await uow.session.execute(select(User).where(User.username == username.strip().lower()))
    return result.scalar_one_or_none()


async def create_user(
    uow: UnitOfWork,
    actor: Actor,
    *,
    username: str,
    display_name: str,
    password: str,
    role: str = UserRole.ADULT,
    locale: str = "en",
    temporary: bool = False,
) -> User:
    """Create an account. ``temporary``: the password came from an owner, so the member must replace it first."""
    if role not in ENABLED_ROLES:
        raise RoleNotEnabledError(role)
    name = normalise_username(username)
    check_password_policy(password)
    await uow.authorize(actor, "user.create", ResourceRef("User"), "personal", "graph:write:User")
    taken = await uow.session.scalar(select(func.count()).select_from(User).where(User.username == name))
    if taken:
        raise UsernameTakenError(name)
    user = User(
        username=name,
        display_name=display_name.strip(),
        password_hash=await hash_password(password),
        role=UserRole(role),
        locale=locale,
        must_change_password=temporary,
    )
    uow.session.add(user)
    await uow.session.flush()
    await uow.session.refresh(user)
    data = UserData(user=user_ref(user))
    await emit("hauskraft.user.created", f"user/{user.id}", data.model_dump(mode="json"), "personal")
    return user


async def list_members(session: AsyncSession) -> list[User]:
    """Every account, deactivated ones included, by display name (case-insensitive), then username."""
    return list(await session.scalars(select(User).order_by(func.lower(User.display_name), User.username)))


async def get_member(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("No such member.")
    return user


async def set_password(uow: UnitOfWork, actor: Actor, username: str, password: str) -> User:
    check_password_policy(password)
    user = await get_by_username(uow, username)
    if user is None:
        raise NotFoundError(f"No user {username!r}.")
    await uow.authorize(actor, "user.reset_password", ResourceRef("User", str(user.id)), "personal", "graph:write:User")
    user.password_hash = await hash_password(password)
    await uow.session.flush()
    return user


def user_ref(user: User) -> UserRef:
    """The account as account events carry it (ADR 0018): never a password, hash or session."""
    return UserRef.model_validate(
        {"id": user.id, "username": user.username, "display_name": user.display_name, "role": str(user.role)}
    )


async def _own_row(uow: UnitOfWork, user_id: uuid.UUID) -> User:
    row = await uow.session.get(User, user_id)
    if row is None:  # pragma: no cover - the session just resolved this user
        raise NotFoundError(f"No user {user_id}.")
    return row


async def update_own_profile(
    uow: UnitOfWork, actor: Actor, user_id: uuid.UUID, *, display_name: str | None, locale: str | None
) -> User:
    """Change my display name and language. A new display name emits ``hauskraft.user.updated``; a language doesn't."""
    await uow.authorize(actor, "user.update_self", ResourceRef("User", str(user_id)), "personal", "graph:write:User")
    user = await _own_row(uow, user_id)
    before = user.display_name
    if display_name is not None:
        user.display_name = display_name
    if locale is not None:
        user.locale = locale
    await uow.session.flush()
    if user.display_name != before:
        changes = UserChanges(display_name=Change(from_=before, to=user.display_name))
        data = UserUpdatedData(user=user_ref(user), changes=changes)
        await emit("hauskraft.user.updated", f"user/{user.id}", data.model_dump(mode="json"), "personal")
    return user


async def change_own_password(
    uow: UnitOfWork,
    actor: Actor,
    user_id: uuid.UUID,
    *,
    current_session_id: str,
    current_password: str,
    new_password: str,
) -> None:
    """Replace my password: my other sessions end, this one stays; emits ``hauskraft.user.password_changed``."""
    await uow.authorize(
        actor, "user.change_password", ResourceRef("User", str(user_id)), "personal", "graph:write:User"
    )
    user = await _own_row(uow, user_id)
    matches, _ = await verify_password(current_password, user.password_hash)
    if not matches:
        raise WrongPasswordError("The current password is wrong.")
    check_password_policy(new_password)
    user.password_hash = await hash_password(new_password)
    user.must_change_password = False
    await sessions.revoke_all_for(uow.session, user, except_id=current_session_id)
    data = UserData(user=user_ref(user))
    await emit("hauskraft.user.password_changed", f"user/{user.id}", data.model_dump(mode="json"), "personal")
