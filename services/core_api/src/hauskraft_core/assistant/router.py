# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/assistant`` (M2*): settings for owners, availability for every member."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from hauskraft_core.assistant.schemas import AssistantSettings, AssistantSettingsPatch, AssistantStatus
from hauskraft_core.assistant.settings import read_config, remove_chat_endpoint, update_settings
from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.db.models import User
from hauskraft_core.db.session import DbSession
from hauskraft_core.policy import Decision
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import ResourceRef
from hauskraft_sdk.errors import PolicyDeniedError

router = APIRouter(prefix="/assistant", tags=["assistant"])


async def require(request: Request, user: User, action: str) -> None:
    """Assistant reads ask the policy too (``assistant.use``, ``assistant.configure``)."""
    decision = await request.app.state.policy.authorize(
        actor_for(user), action, ResourceRef("Assistant"), "household", "assistant:read"
    )
    if decision is not Decision.ALLOW:
        raise PolicyDeniedError(action)


def _uow(request: Request) -> UnitOfWork:
    return UnitOfWork(request.app.state.sessionmaker, request.app.state.policy, request.app.state.settings)


@router.get("/status", responses={401: {}, 403: {}})
async def status(request: Request, db: DbSession, resolved: CurrentSession) -> AssistantStatus:
    """Whether the assistant can be used: an endpoint with a readable key is set (M2S-E03-02)."""
    await require(request, resolved[1], "assistant.use")
    return AssistantStatus(available=(await read_config(db, request.app.state.settings)).configured)


@router.get("/settings", responses={401: {}, 403: {}})
async def settings_read(request: Request, db: DbSession, resolved: CurrentSession) -> AssistantSettings:
    """The assistant settings; the API key appears only as its last four characters (owners only)."""
    await require(request, resolved[1], "assistant.configure")
    return AssistantSettings.of(await read_config(db, request.app.state.settings))


@router.patch("/settings", responses={401: {}, 403: {}, 422: {}})
async def settings_update(
    body: AssistantSettingsPatch, request: Request, resolved: CurrentSession
) -> AssistantSettings:
    """Change any subset of the assistant settings; ``null`` clears an optional value (owners only)."""
    async with _uow(request) as uow:
        config = await update_settings(
            uow,
            actor_for(resolved[1]),
            request.app.state.settings,
            chat=body.chat.sent() if body.chat else None,
            tools_disabled=body.tools_disabled,
            prices=body.prices.sent() if body.prices else None,
            known_tools=getattr(request.app.state, "tool_names", None),
        )
    return AssistantSettings.of(config)


@router.delete("/settings/chat", status_code=204, responses={401: {}, 403: {}})
async def settings_remove_chat(request: Request, resolved: CurrentSession) -> Response:
    """Remove the endpoint's base URL, model and key (owners only)."""
    async with _uow(request) as uow:
        await remove_chat_endpoint(uow, actor_for(resolved[1]))
    return Response(status_code=204)
