# SPDX-License-Identifier: AGPL-3.0-or-later
"""FastAPI dependencies: the signed-in actor (M0S-E05-02)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from hearthos_core.auth import sessions
from hearthos_core.db.models import Session, User
from hearthos_core.db.session import DbSession
from hearthos_core.logging import request_user_id
from hearthos_sdk import Actor
from hearthos_sdk.errors import HearthosError


class UnauthenticatedError(HearthosError):
    status = 401
    code = "unauthenticated"
    title = "Not signed in"


def actor_for(user: User) -> Actor:
    return Actor(id=str(user.id), role=str(user.role), display_name=user.display_name)


async def current_session(request: Request, db: DbSession) -> tuple[Session, User]:
    token = request.cookies.get(sessions.COOKIE_NAME)
    resolved = await sessions.resolve(db, token) if token else None
    if resolved is None:
        raise UnauthenticatedError("Sign in to continue.")
    sess, user = resolved
    request.state.session = sess
    request.state.user = user
    request_user_id.set(str(user.id))
    return sess, user


async def current_actor(resolved: Annotated[tuple[Session, User], Depends(current_session)]) -> Actor:
    return actor_for(resolved[1])


CurrentActor = Annotated[Actor, Depends(current_actor)]
CurrentSession = Annotated[tuple[Session, User], Depends(current_session)]
