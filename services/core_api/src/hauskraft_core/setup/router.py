# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/setup`` (M1S-E03-01): no session needed; the POST is Origin-checked like login."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from hauskraft_core.auth import sessions
from hauskraft_core.auth.csrf import check_origin
from hauskraft_core.auth.ratelimit import client_ip
from hauskraft_core.auth.router import inet, set_session_cookie
from hauskraft_core.auth.schemas import SessionOut
from hauskraft_core.db.session import DbSession
from hauskraft_core.household.service import Household
from hauskraft_core.setup.schemas import SetupIn, SetupStatus
from hauskraft_core.setup.service import complete_setup, setup_required
from hauskraft_core.uow import UnitOfWork

router = APIRouter(tags=["setup"])


@router.get("/setup")
async def status(db: DbSession) -> SetupStatus:
    return SetupStatus(required=await setup_required(db))


@router.post("/setup", status_code=201, responses={403: {}, 409: {}, 422: {}})
async def complete(body: SetupIn, request: Request, response: Response) -> SessionOut:
    """Create the household and its first owner, and sign the owner in. Only while no account exists."""
    check_origin(request)
    async with UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings) as uow:
        owner = await complete_setup(
            uow,
            Household(name=body.household.name, timezone=body.household.timezone, locale=body.household.locale),
            username=body.owner.username,
            display_name=body.owner.display_name,
            password=body.owner.password,
        )
        owner.last_login_at = sessions.now()
        token, row = await sessions.create(
            uow.session, owner, user_agent=request.headers.get("user-agent"), ip=inet(client_ip(request))
        )
        out = SessionOut.of(owner, row.csrf_token, row.expires_at)
    set_session_cookie(response, request, token)
    return out
