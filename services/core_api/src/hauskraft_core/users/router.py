# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/me`` (M0S-E05-02), the member's own sessions (M1S-E05-02) and the owners' members API (M1S-E06)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response

from hauskraft_core.auth import sessions
from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.auth.ratelimit import client_ip
from hauskraft_core.auth.router import RateLimitedError
from hauskraft_core.auth.schemas import (
    MemberOut,
    MemberPatch,
    MePatch,
    PasswordChange,
    SessionInfo,
    TemporaryPassword,
    UserCreate,
    UserOut,
)
from hauskraft_core.db.models import User
from hauskraft_core.db.session import DbSession
from hauskraft_core.household.service import read_household
from hauskraft_core.policy import Decision
from hauskraft_core.uow import UnitOfWork
from hauskraft_core.users.service import (
    WrongPasswordError,
    change_own_password,
    create_user,
    deactivate_member,
    get_member,
    list_members,
    reactivate_member,
    reset_member_password,
    update_member,
    update_own_profile,
)
from hauskraft_sdk import ResourceRef
from hauskraft_sdk.errors import NotFoundError, PolicyDeniedError

router = APIRouter(tags=["users"])


@router.get("/me", responses={401: {}})
async def me_get(resolved: CurrentSession) -> UserOut:
    return UserOut.of(resolved[1])


@router.patch("/me", responses={401: {}, 403: {}, 422: {}})
async def me_update(body: MePatch, request: Request, resolved: CurrentSession) -> UserOut:
    _, user = resolved
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        row = await update_own_profile(
            uow, actor_for(user), user.id, display_name=body.display_name, locale=body.locale
        )
        out = UserOut.of(row)
    return out


@router.post("/me/password", status_code=204, responses={401: {}, 403: {}, 422: {}, 429: {}})
async def me_password(body: PasswordChange, request: Request, resolved: CurrentSession) -> Response:
    """Change my password (M1S-E05-01). Wrong current passwords count towards the login rate limit."""
    sess, user = resolved
    limiter, ip = request.app.state.login_limiter, client_ip(request)
    wait = limiter.retry_after(user.username, ip)
    if wait:
        raise RateLimitedError(wait)
    try:
        async with UnitOfWork(
            request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings
        ) as uow:
            await change_own_password(
                uow,
                actor_for(user),
                user.id,
                current_session_id=sess.id,
                current_password=body.current_password,
                new_password=body.new_password,
            )
    except WrongPasswordError:
        limiter.failed(user.username, ip)
        raise
    limiter.succeeded(user.username, ip)
    return Response(status_code=204)


@router.get("/me/sessions", responses={401: {}})
async def me_sessions(db: DbSession, resolved: CurrentSession) -> list[SessionInfo]:
    """The member's signed-in sessions, most recently used first."""
    current, user = resolved
    return [SessionInfo.of(row, current) for row in await sessions.live_for(db, user)]


@router.delete("/me/sessions/{session_id}", status_code=204, responses={401: {}, 403: {}, 404: {}})
async def me_session_end(session_id: str, request: Request, resolved: CurrentSession) -> Response:
    """End one of the member's sessions; that browser gets 401 on its next request."""
    _, user = resolved
    try:
        public_id = uuid.UUID(session_id)
    except ValueError:
        raise NotFoundError("No such session.") from None
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        await uow.authorize(
            actor_for(user), "session.revoke", ResourceRef("Session", session_id), "personal", "auth:logout"
        )
        if not await sessions.revoke_public(uow.session, user, public_id):
            raise NotFoundError("No such session.")
    return Response(status_code=204)


async def _require(request: Request, user: User, action: str) -> None:
    """Reads that only some roles may do ask the policy too (``user.list`` for the members API)."""
    decision = await request.app.state.policy.authorize(
        actor_for(user), action, ResourceRef("User"), "personal", "graph:read:User"
    )
    if decision is not Decision.ALLOW:
        raise PolicyDeniedError(action)


@router.get("/users", responses={401: {}, 403: {}})
async def users_list(request: Request, db: DbSession, resolved: CurrentSession) -> list[MemberOut]:
    """Every member, deactivated ones included, by display name (M1S-E06-01). Owners only."""
    await _require(request, resolved[1], "user.list")
    return [MemberOut.of(member) for member in await list_members(db)]


@router.get("/users/{user_id}", responses={401: {}, 403: {}, 404: {}})
async def users_get(user_id: uuid.UUID, request: Request, db: DbSession, resolved: CurrentSession) -> MemberOut:
    await _require(request, resolved[1], "user.list")
    return MemberOut.of(await get_member(db, user_id))


@router.patch("/users/{user_id}", responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}})
async def users_update(user_id: uuid.UUID, body: MemberPatch, request: Request, resolved: CurrentSession) -> MemberOut:
    """Change a member's display name or role (M1S-E06-02). 409 ``last_owner`` if no active owner would remain."""
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        member = await update_member(
            uow, actor_for(resolved[1]), user_id, display_name=body.display_name, role=body.role
        )
        out = MemberOut.of(member)
    return out


@router.post("/users/{user_id}/deactivate", responses={401: {}, 403: {}, 404: {}, 409: {}})
async def users_deactivate(user_id: uuid.UUID, request: Request, resolved: CurrentSession) -> MemberOut:
    """Switch an account off (M1S-E06-03): its sessions end and sign-in answers 403 ``account_deactivated``."""
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        out = MemberOut.of(await deactivate_member(uow, actor_for(resolved[1]), user_id))
    return out


@router.post("/users/{user_id}/reactivate", responses={401: {}, 403: {}, 404: {}})
async def users_reactivate(user_id: uuid.UUID, request: Request, resolved: CurrentSession) -> MemberOut:
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        out = MemberOut.of(await reactivate_member(uow, actor_for(resolved[1]), user_id))
    return out


@router.post("/users/{user_id}/password", status_code=204, responses={401: {}, 403: {}, 404: {}, 422: {}})
async def users_reset_password(
    user_id: uuid.UUID, body: TemporaryPassword, request: Request, resolved: CurrentSession
) -> Response:
    """Set a temporary password for a member (M1S-E06-04); they must replace it at their next sign-in."""
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        await reset_member_password(uow, actor_for(resolved[1]), user_id, body.password)
    return Response(status_code=204)


@router.post("/users", status_code=201, responses={401: {}, 403: {}, 409: {}, 422: {}})
async def users_create(body: UserCreate, request: Request, resolved: CurrentSession) -> MemberOut:
    """Create an owner or adult account with a temporary password (M0S-E05-05, M1S-E02-02, M1S-E06-01).

    Owners only (``user.create``). The language defaults to the household's.
    """
    settings = request.app.state.settings
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, settings) as uow:
        locale = body.locale or (await read_household(uow.session, settings)).locale
        user = await create_user(
            uow,
            actor_for(resolved[1]),
            username=body.username,
            display_name=body.display_name,
            password=body.password,
            role=body.role,
            locale=locale,
            temporary=True,
        )
        out = MemberOut.of(user)
    return out
