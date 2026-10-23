# SPDX-License-Identifier: AGPL-3.0-or-later
"""User service (M0S-E05-01). Writes go through ``authorize()``; account events follow in M1* (ADR 0018)."""

from __future__ import annotations

import re

from sqlalchemy import func, select

from hauskraft_core.auth.passwords import check_password_policy, hash_password
from hauskraft_core.db.models import User, UserRole
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor, ResourceRef
from hauskraft_sdk.errors import ConflictError, HauskraftError, NotFoundError

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
) -> User:
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
    )
    uow.session.add(user)
    await uow.session.flush()
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
