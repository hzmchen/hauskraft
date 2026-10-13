# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth API: login, logout, session (M0S-E05-02)."""

from __future__ import annotations

import ipaddress

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from hearthos_core.auth import sessions
from hearthos_core.auth.deps import CurrentSession, actor_for
from hearthos_core.auth.passwords import dummy_verify, verify_password
from hearthos_core.auth.schemas import LoginIn, SessionOut, UserOut
from hearthos_core.db.models import User
from hearthos_core.uow import UnitOfWork
from hearthos_sdk import ResourceRef
from hearthos_sdk.errors import HearthosError

router = APIRouter(prefix="/auth", tags=["auth"])


class InvalidCredentialsError(HearthosError):
    status = 401
    code = "invalid_credentials"
    title = "Invalid credentials"

    def __init__(self) -> None:
        super().__init__("The username or password is not correct.")


class RateLimitedError(HearthosError):
    status = 429
    code = "rate_limited"
    title = "Too many attempts"

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many failed attempts. Try again in {retry_after} seconds.")
        self.headers = {"Retry-After": str(retry_after)}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _inet(value: str) -> str | None:
    """The INET column only takes real addresses (test clients report a host name)."""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _set_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        sessions.COOKIE_NAME,
        token,
        max_age=int(sessions.LIFETIME.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.cookie_secure,
    )


@router.post("/login", responses={401: {}, 403: {}, 429: {}})
async def login(body: LoginIn, request: Request, response: Response) -> SessionOut:
    limiter = request.app.state.login_limiter
    ip = _client_ip(request)
    wait = limiter.retry_after(body.username, ip)
    if wait:
        raise RateLimitedError(wait)
    uow = UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings)
    async with uow:
        user = (
            await uow.session.execute(select(User).where(User.username == body.username.strip().lower()))
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            await dummy_verify(body.password)
            ok, new_hash = False, None
        else:
            ok, new_hash = await verify_password(body.password, user.password_hash)
        if not ok or user is None:
            limiter.failed(body.username, ip)
            raise InvalidCredentialsError
        limiter.succeeded(body.username, ip)
        actor = actor_for(user)
        await uow.authorize(actor, "session.create", ResourceRef("Session"), "personal", "auth:login")
        if new_hash:
            user.password_hash = new_hash
        user.last_login_at = sessions.now()
        await sessions.revoke(uow.session, request.cookies.get(sessions.COOKIE_NAME))
        token, row = await sessions.create(
            uow.session, user, user_agent=request.headers.get("user-agent"), ip=_inet(ip)
        )
        out = SessionOut(user=UserOut.of(user), csrf_token=row.csrf_token, expires_at=row.expires_at)
    _set_cookie(response, request, token)
    return out


@router.post("/logout", status_code=204, responses={401: {}, 403: {}})
async def logout(request: Request, resolved: CurrentSession) -> Response:
    _sess, user = resolved
    uow = UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings)
    async with uow:
        await uow.authorize(actor_for(user), "session.revoke", ResourceRef("Session"), "personal", "auth:logout")
        await sessions.revoke(uow.session, request.cookies.get(sessions.COOKIE_NAME))
    response = Response(status_code=204)
    response.delete_cookie(
        sessions.COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=request.app.state.settings.cookie_secure
    )
    return response


@router.get("/session", responses={401: {}})
async def session(resolved: CurrentSession) -> SessionOut:
    sess, user = resolved
    return SessionOut(user=UserOut.of(user), csrf_token=sess.csrf_token, expires_at=sess.expires_at)
