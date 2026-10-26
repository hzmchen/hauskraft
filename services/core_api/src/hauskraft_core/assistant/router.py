# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/assistant`` (M2*): settings for owners; availability, chats, runs and Undo for every member."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response

from hauskraft_core.assistant import conversations
from hauskraft_core.assistant.endpoint import check_connection
from hauskraft_core.assistant.runs import Harness, RunResultData
from hauskraft_core.assistant.schemas import (
    ActionOut,
    AssistantSettings,
    AssistantSettingsPatch,
    AssistantStatus,
    ConfirmationAnswer,
    ConfirmationOut,
    ConnectionTest,
    Conversation,
    ConversationDetail,
    MessageIn,
    MessageOut,
    RunOut,
    RunResult,
    ToolInfo,
    action_out,
)
from hauskraft_core.assistant.settings import read_config, remove_chat_endpoint, update_settings
from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.db.models import User
from hauskraft_core.db.session import DbSession
from hauskraft_core.policy import Decision
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import DataClass, ResourceRef
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
            known_tools=request.app.state.tool_registry.names(),
        )
    return AssistantSettings.of(config)


@router.post("/settings/test", responses={401: {}, 403: {}, 409: {}})
async def settings_test(request: Request, db: DbSession, resolved: CurrentSession) -> ConnectionTest:
    """Check the endpoint with one minimal request: reachable, key accepted, model found, tools accepted."""
    await require(request, resolved[1], "assistant.configure")
    result = await check_connection((await read_config(db, request.app.state.settings)).chat)
    return ConnectionTest.model_validate(result, from_attributes=True)


@router.delete("/settings/chat", status_code=204, responses={401: {}, 403: {}})
async def settings_remove_chat(request: Request, resolved: CurrentSession) -> Response:
    """Remove the endpoint's base URL, model and key (owners only)."""
    async with _uow(request) as uow:
        await remove_chat_endpoint(uow, actor_for(resolved[1]))
    return Response(status_code=204)


# ---------------------------------------------------------------- conversations (M2S-E04-01)
@router.get("/conversations", responses={401: {}, 403: {}})
async def conversations_list(request: Request, db: DbSession, resolved: CurrentSession) -> list[Conversation]:
    """The caller's own chats, newest first. Nobody else's, owners included."""
    await require(request, resolved[1], "assistant.use")
    return [Conversation.model_validate(c) for c in await conversations.list_for(db, resolved[1].id)]


@router.post("/conversations", status_code=201, responses={401: {}, 403: {}})
async def conversations_create(request: Request, resolved: CurrentSession) -> Conversation:
    await require(request, resolved[1], "assistant.use")
    async with _uow(request) as uow:
        created = await conversations.create(uow.session, resolved[1].id)
        out = Conversation.model_validate(created)
    return out


@router.get("/conversations/{conversation_id}", responses={401: {}, 403: {}, 404: {}})
async def conversations_read(
    conversation_id: uuid.UUID, request: Request, db: DbSession, resolved: CurrentSession
) -> ConversationDetail:
    await require(request, resolved[1], "assistant.use")
    found = await conversations.get_own(db, resolved[1].id, conversation_id)
    return ConversationDetail(
        **Conversation.model_validate(found).model_dump(),
        messages=[MessageOut.model_validate(m) for m in await conversations.messages(db, found.id)],
        actions=[action_out(a) for a in await conversations.actions(db, found.id)],
    )


@router.delete("/conversations/{conversation_id}", status_code=204, responses={401: {}, 403: {}, 404: {}})
async def conversations_delete(conversation_id: uuid.UUID, request: Request, resolved: CurrentSession) -> Response:
    """Delete a chat with its messages, runs and actions; its usage stays counted."""
    await require(request, resolved[1], "assistant.use")
    async with _uow(request) as uow:
        await conversations.delete_own(uow.session, resolved[1].id, conversation_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- tools (M2S-E02-03)
@router.get("/tools", responses={401: {}, 403: {}})
async def tools_list(request: Request, db: DbSession, resolved: CurrentSession) -> list[ToolInfo]:
    """Every agent tool of the enabled plugins, with whether the owner switched it off (owners only)."""
    await require(request, resolved[1], "assistant.configure")
    off = set((await read_config(db, request.app.state.settings)).tools_disabled)
    return [
        ToolInfo(
            name=t.spec.name,
            wire_name=t.spec.wire_name,
            plugin_id=t.plugin_id,
            description=t.spec.description,
            annotations=t.spec.annotations.as_dict(),
            data_class=DataClass(t.spec.data_class),
            permission=t.spec.permission,
            enabled=t.spec.name not in off,
        )
        for t in request.app.state.tool_registry.all()
        if t.plugin_id not in request.app.state.disabled_plugins
    ]


# ---------------------------------------------------------------- runs (M2S-E04-02, -04, -06)
def run_result(data: RunResultData) -> RunResult:
    return RunResult(
        run=RunOut.model_validate(data.run),
        messages=[MessageOut.model_validate(m) for m in data.messages],
        actions=[action_out(a) for a in data.actions],
        confirmations=[ConfirmationOut.model_validate(c) for c in data.confirmations],
    )


@router.post("/conversations/{conversation_id}/messages", responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}})
async def conversations_message(
    conversation_id: uuid.UUID, body: MessageIn, request: Request, resolved: CurrentSession
) -> RunResult:
    """Send a message: the assistant runs with the caller's permissions and answers, acts or asks to confirm.

    A run that fails because of the model endpoint still answers 200, with ``run.status`` failed and an error code.
    """
    await require(request, resolved[1], "assistant.use")
    data = await Harness.of(request.app.state).chat(resolved[1], conversation_id, body.text, body.channel)
    return run_result(data)


@router.post("/runs/{run_id}/confirmations", responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}})
async def runs_confirm(
    run_id: uuid.UUID, body: ConfirmationAnswer, request: Request, resolved: CurrentSession
) -> RunResult:
    """Approve or deny each pending call of a run that waits for confirmation; the run then continues."""
    await require(request, resolved[1], "assistant.use")
    decisions = {d.id: d.approve for d in body.decisions}
    return run_result(await Harness.of(request.app.state).answer(resolved[1], run_id, decisions))


@router.post("/actions/{action_id}/undo", responses={401: {}, 403: {}, 404: {}, 409: {}})
async def actions_undo(action_id: uuid.UUID, request: Request, resolved: CurrentSession) -> ActionOut:
    """Reverse an action the assistant took for the caller, where its tool declared how."""
    await require(request, resolved[1], "assistant.use")
    return action_out(await Harness.of(request.app.state).undo(resolved[1], action_id))
