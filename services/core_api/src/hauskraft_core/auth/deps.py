# SPDX-License-Identifier: AGPL-3.0-or-later
"""FastAPI dependencies: the signed-in actor (M0S-E05-02)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from hauskraft_core.auth import sessions
from hauskraft_core.auth.csrf import check_request
from hauskraft_core.auth.locked import PasswordChangeRequiredError, allowed_while_locked
from hauskraft_core.db.models import Session, User
from hauskraft_core.db.session import DbSession
from hauskraft_core.logging import request_user_id
from hauskraft_sdk import Actor
from hauskraft_sdk.errors import HauskraftError


class UnauthenticatedError(HauskraftError):
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
    check_request(request, sess.csrf_token)
    if user.must_change_password and not allowed_while_locked(request.method, request.url.path):
        raise PasswordChangeRequiredError("Choose a new password before you continue.")
    request.state.session = sess
    request.state.user = user
    request_user_id.set(str(user.id))
    return sess, user


async def current_actor(resolved: Annotated[tuple[Session, User], Depends(current_session)]) -> Actor:
    return actor_for(resolved[1])


CurrentActor = Annotated[Actor, Depends(current_actor)]
CurrentSession = Annotated[tuple[Session, User], Depends(current_session)]
