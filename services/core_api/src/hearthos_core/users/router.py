# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/me`` (M0S-E05-02)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hearthos_core.auth.deps import CurrentSession, actor_for
from hearthos_core.auth.schemas import MePatch, UserOut
from hearthos_core.db.models import User
from hearthos_core.uow import UnitOfWork
from hearthos_sdk import ResourceRef

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
