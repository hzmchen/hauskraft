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


class LastOwnerError(ConflictError):
    def __init__(self) -> None:
        super().__init__("last_owner", "The household needs at least one active owner.")


class OwnAccountError(HauskraftError):
    status = 422
    code = "own_account"
    title = "Use your own account settings"


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
    await uow.authorize(actor, "user.create", ResourceRef("User"), "personal", "graph:write:User")
    user = await insert_account(
        uow,
        username=username,
        display_name=display_name,
        password=password,
        role=role,
        locale=locale,
        temporary=temporary,
    )
    await emit_account_event("hauskraft.user.created", user)
    return user


async def insert_account(
    uow: UnitOfWork,
    *,
    username: str,
    display_name: str,
    password: str,
    role: str,
    locale: str,
    temporary: bool = False,
) -> User:
    """Validate and insert an account. The caller has asked the policy and emits ``hauskraft.user.created``."""
    name = normalise_username(username)
    check_password_policy(password)
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
    return user


async def list_members(session: AsyncSession) -> list[User]:
    """Every account, deactivated ones included, by display name (case-insensitive), then username."""
    return list(await session.scalars(select(User).order_by(func.lower(User.display_name), User.username)))


async def get_member(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("No such member.")
    return user


async def _ensure_an_active_owner_remains(session: AsyncSession, leaving: User) -> None:
    """Refuse when ``leaving`` is the only active owner. The owner rows stay locked until the transaction ends, so
    two owners can't demote or deactivate each other at the same moment."""
    owners = await session.scalars(
        select(User.id).where(User.role == UserRole.OWNER, User.is_active.is_(True)).with_for_update()
    )
    if set(owners) <= {leaving.id}:
        raise LastOwnerError


async def update_member(
    uow: UnitOfWork, actor: Actor, user_id: uuid.UUID, *, display_name: str | None, role: str | None
) -> User:
    """Change a member's display name and/or role (owners only); emits ``hauskraft.user.updated`` with the changes."""
    await uow.authorize(actor, "user.update", ResourceRef("User", str(user_id)), "personal", "graph:write:User")
    if role is not None and role not in ENABLED_ROLES:
        raise RoleNotEnabledError(role)
    user = await get_member(uow.session, user_id)
    changes: dict[str, Change[str]] = {}
    if display_name is not None and display_name != user.display_name:
        changes["display_name"] = Change(from_=user.display_name, to=display_name)
        user.display_name = display_name
    if role is not None and role != user.role:
        if user.role == UserRole.OWNER and user.is_active:
            await _ensure_an_active_owner_remains(uow.session, user)
        changes["role"] = Change(from_=str(user.role), to=str(role))
        user.role = UserRole(role)
    if changes:
        await uow.session.flush()
        data = UserUpdatedData(user=user_ref(user), changes=UserChanges.model_validate(changes))
        await emit("hauskraft.user.updated", f"user/{user.id}", data.model_dump(mode="json"), "personal")
    return user


async def deactivate_member(uow: UnitOfWork, actor: Actor, user_id: uuid.UUID) -> User:
    """Switch an account off (owners only): its sessions end and it can't sign in; history keeps its name."""
    await uow.authorize(actor, "user.deactivate", ResourceRef("User", str(user_id)), "personal", "graph:write:User")
    user = await get_member(uow.session, user_id)
    if not user.is_active:
        return user
    if user.role == UserRole.OWNER:
        await _ensure_an_active_owner_remains(uow.session, user)
    user.is_active = False
    await sessions.revoke_all_for(uow.session, user)
    await uow.session.flush()
    await emit(
        "hauskraft.user.deactivated",
        f"user/{user.id}",
        UserData(user=user_ref(user)).model_dump(mode="json"),
        "personal",
    )
    return user


async def reactivate_member(uow: UnitOfWork, actor: Actor, user_id: uuid.UUID) -> User:
    """Let a deactivated account sign in again (owners only)."""
    await uow.authorize(actor, "user.reactivate", ResourceRef("User", str(user_id)), "personal", "graph:write:User")
    user = await get_member(uow.session, user_id)
    if user.is_active:
        return user
    user.is_active = True
    await uow.session.flush()
    await emit(
        "hauskraft.user.reactivated",
        f"user/{user.id}",
        UserData(user=user_ref(user)).model_dump(mode="json"),
        "personal",
    )
    return user


async def reset_member_password(uow: UnitOfWork, actor: Actor, user_id: uuid.UUID, password: str) -> None:
    """Give a member a temporary password (owners only): their sessions end and they must choose a new one."""
    await uow.authorize(actor, "user.reset_password", ResourceRef("User", str(user_id)), "personal", "graph:write:User")
    if str(user_id) == actor.id:
        raise OwnAccountError("Change your own password in your account settings.")
    user = await get_member(uow.session, user_id)
    check_password_policy(password)
    user.password_hash = await hash_password(password)
    user.must_change_password = True
    await sessions.revoke_all_for(uow.session, user)
    await uow.session.flush()
    await emit_account_event("hauskraft.user.password_reset", user)


async def by_username(uow: UnitOfWork, username: str) -> User:
    user = await get_by_username(uow, username)
    if user is None:
        raise NotFoundError(f"No user {username!r}.")
    return user


async def set_password(uow: UnitOfWork, actor: Actor, username: str, password: str, *, temporary: bool = False) -> User:
    """Set an account's password by username (the CLI's recovery path). Like an owner's reset, the account's
    sessions end and ``hauskraft.user.password_reset`` is emitted; ``temporary`` makes them choose a new one."""
    check_password_policy(password)
    user = await by_username(uow, username)
    await uow.authorize(actor, "user.reset_password", ResourceRef("User", str(user.id)), "personal", "graph:write:User")
    user.password_hash = await hash_password(password)
    user.must_change_password = temporary
    await sessions.revoke_all_for(uow.session, user)
    await uow.session.flush()
    await emit_account_event("hauskraft.user.password_reset", user)
    return user


def user_ref(user: User) -> UserRef:
    """The account as account events carry it (ADR 0018): never a password, hash or session."""
    return UserRef.model_validate(
        {"id": user.id, "username": user.username, "display_name": user.display_name, "role": str(user.role)}
    )


async def emit_account_event(event_type: str, user: User) -> None:
    """Emit an account event whose data is the account alone (``{user: UserRef}``, ADR 0018)."""
    await emit(event_type, f"user/{user.id}", UserData(user=user_ref(user)).model_dump(mode="json"), "personal")


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
    await emit_account_event("hauskraft.user.password_changed", user)
