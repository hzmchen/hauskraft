# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth API: login, logout, session (M0S-E05-02)."""

from __future__ import annotations

import ipaddress

from fastapi import APIRouter, Request, Response

from hauskraft_core.auth import sessions
from hauskraft_core.auth.csrf import check_origin
from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.auth.providers import PasswordCredentials
from hauskraft_core.auth.ratelimit import client_ip
from hauskraft_core.auth.schemas import LoginIn, SessionOut
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import ResourceRef
from hauskraft_sdk.errors import HauskraftError

router = APIRouter(prefix="/auth", tags=["auth"])


class InvalidCredentialsError(HauskraftError):
    status = 401
    code = "invalid_credentials"
    title = "Invalid credentials"

    def __init__(self) -> None:
        super().__init__("The username or password is not correct.")


class AccountDeactivatedError(HauskraftError):
    status = 403
    code = "account_deactivated"
    title = "Account deactivated"

    def __init__(self) -> None:
        super().__init__("This account is deactivated. Ask an owner of your household.")


class RateLimitedError(HauskraftError):
    status = 429
    code = "rate_limited"
    title = "Too many attempts"

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many failed attempts. Try again in {retry_after} seconds.")
        self.headers = {"Retry-After": str(retry_after)}


def inet(value: str) -> str | None:
    """The INET column only takes real addresses (test clients report a host name)."""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def set_session_cookie(response: Response, request: Request, token: str) -> None:
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
    check_origin(request)
    limiter = request.app.state.login_limiter
    ip = client_ip(request)
    wait = limiter.retry_after(body.username, ip)
    if wait:
        raise RateLimitedError(wait)
    uow = UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings)
    async with uow:
        ref = await request.app.state.identity_provider.authenticate(
            uow.session, PasswordCredentials(body.username, body.password)
        )
        if ref is None:
            limiter.failed(body.username, ip)
            raise InvalidCredentialsError
        user, new_hash = ref.user, ref.upgraded_password_hash
        if not user.is_active:
            raise AccountDeactivatedError
        limiter.succeeded(body.username, ip)
        actor = actor_for(user)
        await uow.authorize(actor, "session.create", ResourceRef("Session"), "personal", "auth:login")
        if new_hash:
            user.password_hash = new_hash
        user.last_login_at = sessions.now()
        await sessions.revoke(uow.session, request.cookies.get(sessions.COOKIE_NAME))
        token, row = await sessions.create(uow.session, user, user_agent=request.headers.get("user-agent"), ip=inet(ip))
        out = SessionOut.of(user, row.csrf_token, row.expires_at)
    set_session_cookie(response, request, token)
    return out


@router.post("/logout", status_code=204, responses={401: {}, 403: {}})
async def logout(request: Request, resolved: CurrentSession) -> Response:
    _sess, user = resolved
    uow = UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings)
    async with uow:
        await uow.authorize(actor_for(user), "session.revoke", ResourceRef("Session"), "personal", "auth:logout")
        await sessions.revoke(uow.session, request.cookies.get(sessions.COOKIE_NAME))
    return _signed_out(request)


@router.post("/logout-everywhere", status_code=204, responses={401: {}, 403: {}})
async def logout_everywhere(request: Request, resolved: CurrentSession) -> Response:
    """End every session of the signed-in member, this one included (M1S-E05-02)."""
    _sess, user = resolved
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        await uow.authorize(actor_for(user), "session.revoke", ResourceRef("Session"), "personal", "auth:logout")
        await sessions.revoke_all_for(uow.session, user)
    return _signed_out(request)


def _signed_out(request: Request) -> Response:
    response = Response(status_code=204)
    response.delete_cookie(
        sessions.COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=request.app.state.settings.cookie_secure
    )
    return response


@router.get("/session", responses={401: {}})
async def session(resolved: CurrentSession) -> SessionOut:
    sess, user = resolved
    return SessionOut.of(user, sess.csrf_token, sess.expires_at)
