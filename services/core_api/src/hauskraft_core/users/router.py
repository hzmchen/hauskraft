# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/me`` (M0S-E05-02) and the member's own sessions (M1S-E05-02)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response

from hauskraft_core.auth import sessions
from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.auth.schemas import MePatch, SessionInfo, UserCreate, UserOut
from hauskraft_core.db.models import User
from hauskraft_core.db.session import DbSession
from hauskraft_core.uow import UnitOfWork
from hauskraft_core.users.service import create_user
from hauskraft_sdk import ResourceRef
from hauskraft_sdk.errors import NotFoundError

router = APIRouter(tags=["users"])


@router.get("/me", responses={401: {}})
async def me_get(resolved: CurrentSession) -> UserOut:
    return UserOut.of(resolved[1])


@router.patch("/me", responses={401: {}, 403: {}, 422: {}})
async def me_update(body: MePatch, request: Request, resolved: CurrentSession) -> UserOut:
    _, user = resolved
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        await uow.authorize(
            actor_for(user), "user.update_self", ResourceRef("User", str(user.id)), "personal", "graph:write:User"
        )
        row = await uow.session.get(User, user.id)
        if row is None:  # pragma: no cover - the session just resolved this user
            raise LookupError(user.id)
        if body.display_name is not None:
            row.display_name = body.display_name
        if body.locale is not None:
            row.locale = body.locale
        await uow.session.flush()
        out = UserOut.of(row)
    return out


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


@router.post("/users", status_code=201, responses={401: {}, 403: {}, 409: {}, 422: {}})
async def users_create(body: UserCreate, request: Request, resolved: CurrentSession) -> UserOut:
    """Create an owner or adult account (M0S-E05-05, M1S-E02-02). Owners only (``user.create``)."""
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        user = await create_user(
            uow,
            actor_for(resolved[1]),
            username=body.username,
            display_name=body.display_name,
            password=body.password,
            role=body.role,
        )
        out = UserOut.of(user)
    return out
