# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assistant runs (M2S-E04-02, -04, -05, -06, spec §8.0, ADR 0020).

A run is one agent execution: a chat turn (or its continuation after a confirmation) or a skill run. Tools come from
the registry's ``select()`` and run as the person, with ``Actor.via`` set to the run id so their events carry
``agentrunid``. Every call passes the gate; a destructive call pauses the run until the person answers. Endpoint
failures never become server errors: the run ends ``failed`` with a stable code.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_ai import (
    Agent,
    ApprovalRequired,
    DeferredToolRequests,
    DeferredToolResults,
    ModelMessagesTypeAdapter,
    ModelRetry,
    RunContext,
    StructuredDict,
    Tool,
    ToolDenied,
    UsageLimits,
    capture_run_messages,
)
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    RunTimedOut,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.assistant import conversations, gate
from hauskraft_core.assistant.endpoint import chat_model, model_settings, require_configured
from hauskraft_core.assistant.prompt import PromptContext, prompt_version, render
from hauskraft_core.assistant.registry import RegisteredTool, ToolRegistry, tools_hash
from hauskraft_core.assistant.settings import AssistantConfig, read_config
from hauskraft_core.assistant.skills import Skill
from hauskraft_core.db.models import (
    AssistantAction,
    AssistantMessage,
    AssistantRun,
    AssistantUsage,
    User,
)
from hauskraft_core.household.service import read_household
from hauskraft_core.logging import get_logger
from hauskraft_sdk import Actor
from hauskraft_sdk.errors import ConflictError, HauskraftError, NotFoundError

REQUEST_LIMIT = 8
RUN_TIMEOUT_S = 60.0
HISTORY_CHAR_CAP = 24_000
TOOL_RETRIES = 2

_log = get_logger("hauskraft.assistant")


class NotAwaitingConfirmationError(ConflictError):
    def __init__(self) -> None:
        super().__init__("not_awaiting_confirmation", "This run is not waiting for a confirmation.")


class UndoUnavailableError(ConflictError):
    def __init__(self) -> None:
        super().__init__("undo_unavailable", "This action can't be undone.")


@dataclass
class _Recorder:
    """What happened during one agent execution, persisted afterwards."""

    actions: list[AssistantAction] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RunResultData:
    run: AssistantRun
    messages: list[AssistantMessage]
    actions: list[AssistantAction]
    confirmations: list[dict[str, Any]]
    output: Any = None


def actor_for_run(user: User, run_id: uuid.UUID | None) -> Actor:
    return Actor(
        id=str(user.id), role=str(user.role), display_name=user.display_name, via=str(run_id) if run_id else None
    )


def _namespace(tool: RegisteredTool) -> str:
    return tool.plugin_id.rsplit(".", 1)[-1]


def confirm_key(tool: RegisteredTool) -> str:
    """The confirmation card's text key: ``<plugin>:tool.<verb>.confirm``, e.g. tasks:tool.delete.confirm."""
    return f"{_namespace(tool)}:tool.{tool.spec.name.split('.', 1)[1]}.confirm"


def _record(ref: Any) -> dict[str, str] | None:
    return {"type": ref.type, "id": ref.id, "label": ref.label} if ref is not None else None


def _wrap(
    tool: RegisteredTool, actor: Actor, recorder: _Recorder, gate_ctx: gate.GateContext, run_id: uuid.UUID
) -> Tool[Any]:
    spec = tool.spec

    async def call(ctx: RunContext[None], **kwargs: Any) -> Any:
        decision, reason = gate.decide(tool, kwargs, actor, gate_ctx, approved=bool(ctx.tool_call_approved))
        recorder.decisions.append(
            {"tool": spec.name, "decision": decision, "reason": reason, "tool_call_id": ctx.tool_call_id}
        )
        if decision == "deny":
            raise ModelRetry(f"tool_not_available: {spec.wire_name} may not be used in this run.")
        if decision == "confirm":
            raise ApprovalRequired()
        try:
            args = spec.input_model.model_validate(kwargs)
        except ValidationError as exc:
            raise ModelRetry(f"invalid_arguments: {exc.errors(include_url=False, include_context=False)}") from exc
        try:
            outcome = await spec.handler(tool.context, actor, args)  # type: ignore[arg-type]
        except HauskraftError as exc:
            if not spec.annotations.read_only:
                recorder.actions.append(
                    AssistantAction(
                        run_id=run_id, user_id=uuid.UUID(actor.id), tool=spec.name, status="failed", error_code=exc.code
                    )
                )
            raise ModelRetry(f"{exc.code}: {exc}") from exc
        if not spec.annotations.read_only:
            undo = {"tool": outcome.undo.tool, "args": dict(outcome.undo.args)} if outcome.undo else None
            recorder.actions.append(
                AssistantAction(
                    run_id=run_id,
                    user_id=uuid.UUID(actor.id),
                    tool=spec.name,
                    status="done",
                    summary_key=outcome.summary_key,
                    record=_record(outcome.record),
                    undo=undo,
                )
            )
        output = outcome.output
        return output.model_dump(mode="json") if isinstance(output, BaseModel) else output

    return Tool.from_schema(
        call, name=spec.wire_name, description=spec.description, json_schema=spec.parameters(), takes_ctx=True
    )


def _trim(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Drop the oldest turns (each starting with a user prompt) until the history fits the character cap."""
    while len(messages) > 1 and len(ModelMessagesTypeAdapter.dump_json(messages)) > HISTORY_CHAR_CAP:
        starts = [
            i
            for i, m in enumerate(messages)
            if isinstance(m, ModelRequest) and any(isinstance(p, UserPromptPart) for p in m.parts)
        ]
        later = [i for i in starts if i > 0]
        if not later:
            break
        messages = messages[later[0] :]
    return messages


def _usage(response: ModelResponse, user: User, run: AssistantRun, kind: str) -> AssistantUsage:
    """One model request's tokens; a server that reports none is stored as unknown (M2S-E08-01)."""
    usage = response.usage
    unknown = not usage.input_tokens and not usage.output_tokens
    return AssistantUsage(
        user_id=user.id,
        run_id=run.id,
        kind=kind,
        model=response.model_name or run.model,
        input_tokens=None if unknown else usage.input_tokens,
        output_tokens=None if unknown else usage.output_tokens,
        cached_tokens=None if unknown else usage.cache_read_tokens,
        status="ok",
    )


def _error_code(exc: BaseException, *, structured: bool = False) -> str:
    if structured and isinstance(exc, UnexpectedModelBehavior):
        return "invalid_output"
    if isinstance(exc, UsageLimitExceeded):
        return "run_limit"
    if isinstance(exc, (RunTimedOut, asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    if isinstance(exc, ModelHTTPError) and exc.status_code in (401, 403):
        return "auth_failed"
    return "model_unavailable"


@dataclass
class Harness:
    """Everything a run needs from the app: database, settings, registry, disabled plugins."""

    sessionmaker: Any
    settings: Any
    registry: ToolRegistry
    disabled_plugins: set[str]
    skills: dict[str, Skill] = field(default_factory=dict)

    @classmethod
    def of(cls, state: Any) -> Harness:
        return cls(
            state.sessionmaker,
            state.settings,
            state.tool_registry,
            state.disabled_plugins,
            getattr(state, "skills", {}),
        )

    # ------------------------------------------------------------------ helpers
    async def _prompt(
        self,
        session: AsyncSession,
        user: User,
        tools: Sequence[RegisteredTool],
        *,
        skill_id: str | None = None,
        skill_instructions: str | None = None,
        channel: str = "text",
    ) -> str:
        household = await read_household(session, self.settings)
        ctx = PromptContext(
            now=dt.datetime.now(dt.UTC),
            timezone=household.timezone,
            household=household.name,
            person=user.display_name,
            role=str(user.role),
            locale=user.locale or household.locale,
        )
        plugins = sorted({t.plugin_id for t in tools})
        guidance = [self.registry.guidance[pid] for pid in plugins if pid in self.registry.guidance]
        return render(ctx, guidance=guidance, skill_id=skill_id, skill_instructions=skill_instructions, channel=channel)

    def select(
        self, user: User, config: AssistantConfig, skill_tools: Sequence[str] | None = None
    ) -> list[RegisteredTool]:
        return self.registry.select(
            role=str(user.role),
            disabled_tools=config.tools_disabled,
            disabled_plugins=self.disabled_plugins,
            max_data_class=config.chat.max_data_class,
            skill_tools=skill_tools,
        )

    async def _execute(
        self,
        *,
        run: AssistantRun,
        user: User,
        config: AssistantConfig,
        tools: Sequence[RegisteredTool],
        instructions: str,
        prompt: str | None,
        history: list[ModelMessage],
        deferred: DeferredToolResults | None = None,
        output_type: Any = None,
    ) -> tuple[Any, list[ModelMessage], _Recorder, list[ModelResponse], str | None]:
        """Run the agent; returns (output, all messages, recorder, new model responses, error code)."""
        recorder = _Recorder()
        actor = actor_for_run(user, run.id)
        gate_ctx = gate.GateContext(offered=frozenset(t.spec.name for t in tools), channel=run.channel)  # type: ignore[arg-type]
        agent: Agent[None, Any] = Agent(
            chat_model(config.chat),
            output_type=output_type or [str, DeferredToolRequests],
            tools=[_wrap(t, actor, recorder, gate_ctx, run.id) for t in tools],
            retries=TOOL_RETRIES,
            model_settings=model_settings(config.chat),
        )
        with capture_run_messages() as captured:
            try:
                async with asyncio.timeout(RUN_TIMEOUT_S):
                    result = await agent.run(
                        user_prompt=prompt,
                        message_history=history or None,
                        deferred_tool_results=deferred,
                        instructions=instructions,
                        usage_limits=UsageLimits(request_limit=REQUEST_LIMIT),
                    )
            except (ModelAPIError, UnexpectedModelBehavior, UsageLimitExceeded, RunTimedOut, TimeoutError) as exc:
                _log.info("assistant.run_failed", run_id=str(run.id), error=type(exc).__name__)
                made = [m for m in captured[len(history) :] if isinstance(m, ModelResponse)]
                return None, history, recorder, made, _error_code(exc, structured=output_type is not None)
        new = [m for m in result.new_messages() if isinstance(m, ModelResponse)]
        return result.output, _trim(list(result.all_messages())), recorder, new, None

    async def _persist(
        self,
        run: AssistantRun,
        user: User,
        tools: Sequence[RegisteredTool],
        outcome: tuple[Any, list[ModelMessage], _Recorder, list[ModelResponse], str | None],
        *,
        kind: str,
        conversation_id: uuid.UUID | None,
        attempts: int = 0,
    ) -> RunResultData:
        output, messages, recorder, responses, error = outcome
        async with self.sessionmaker() as session, session.begin():
            row = await session.get(AssistantRun, run.id, with_for_update=True)
            if row is None:  # pragma: no cover - the run was deleted with its chat meanwhile
                raise NotFoundError("No such run.")
            row.history = ModelMessagesTypeAdapter.dump_python(messages, mode="json")
            row.decisions = [*row.decisions, *recorder.decisions]
            new_messages: list[AssistantMessage] = []
            confirmations: list[dict[str, Any]] = []
            for action in recorder.actions:
                session.add(action)
            if error:
                row.status, row.error_code = "failed", error
            elif isinstance(output, DeferredToolRequests):
                row.status = "awaiting_confirmation"
                confirmations = await self._pending(output, user, row.id)
                row.pending = confirmations
            else:
                row.status = "done"
                row.output = output if not isinstance(output, BaseModel) else output.model_dump(mode="json")
                if kind == "chat" and conversation_id and isinstance(output, str):
                    message = AssistantMessage(
                        conversation_id=conversation_id, run_id=row.id, role="assistant", text=output
                    )
                    session.add(message)
                    new_messages.append(message)
            if row.status != "awaiting_confirmation":
                row.pending = []
                row.finished_at = dt.datetime.now(dt.UTC)
            for response in responses:
                session.add(_usage(response, user, row, kind))
            if error and not responses:  # the request itself failed: count it, tokens unknown
                session.add(AssistantUsage(user_id=user.id, run_id=row.id, kind=kind, model=row.model, status="error"))
            await session.flush()
            for m in new_messages:
                await session.refresh(m)
            for a in recorder.actions:
                await session.refresh(a)
            await session.refresh(row)
        return RunResultData(
            run=row, messages=new_messages, actions=recorder.actions, confirmations=confirmations, output=row.output
        )

    async def _pending(self, requests: DeferredToolRequests, user: User, run_id: uuid.UUID) -> list[dict[str, Any]]:
        pending = []
        for part in requests.approvals:
            tool = self.registry.by_wire_name(part.tool_name)
            args = part.args_as_dict()
            record = None
            if tool.spec.preview is not None:
                try:
                    parsed = tool.spec.input_model.model_validate(args)
                    record = _record(await tool.spec.preview(tool.context, actor_for_run(user, run_id), parsed))  # type: ignore[arg-type]
                except (HauskraftError, ValidationError):
                    record = None
            pending.append(
                {
                    "id": part.tool_call_id,
                    "run_id": str(run_id),
                    "tool": tool.spec.name,
                    "args": args,
                    "summary_key": confirm_key(tool),
                    "record": record,
                }
            )
        return pending

    # ------------------------------------------------------------------ chat
    async def chat(self, user: User, conversation_id: uuid.UUID, text: str, channel: str = "text") -> RunResultData:
        async with self.sessionmaker() as session, session.begin():
            conversation = await conversations.get_own(session, user.id, conversation_id, for_update=True)
            config = await read_config(session, self.settings)
            require_configured(config.chat)
            previous = await session.scalar(
                select(AssistantRun.history)
                .where(AssistantRun.conversation_id == conversation_id)
                .order_by(AssistantRun.created_at.desc(), AssistantRun.id.desc())
                .limit(1)
            )
            tools = self.select(user, config)
            run = AssistantRun(
                user_id=user.id,
                conversation_id=conversation_id,
                kind="chat",
                channel=channel,
                status="running",
                model=config.chat.model,
                prompt_version=prompt_version(),
                tools_hash=tools_hash(tools),
            )
            session.add(run)
            await session.flush()
            asked = AssistantMessage(conversation_id=conversation_id, run_id=run.id, role="user", text=text)
            session.add(asked)
            await conversations.touch(session, conversation, text)
            instructions = await self._prompt(session, user, tools, channel=channel)
            await session.flush()
            await session.refresh(asked)
        history = list(ModelMessagesTypeAdapter.validate_python(previous)) if previous else []
        outcome = await self._execute(
            run=run, user=user, config=config, tools=tools, instructions=instructions, prompt=text, history=history
        )
        result = await self._persist(run, user, tools, outcome, kind="chat", conversation_id=conversation_id)
        result.messages.insert(0, asked)
        return result

    # ------------------------------------------------------------------ confirmations
    async def answer(self, user: User, run_id: uuid.UUID, decisions: dict[str, bool]) -> RunResultData:
        async with self.sessionmaker() as session, session.begin():
            run = await session.scalar(
                select(AssistantRun).where(AssistantRun.id == run_id, AssistantRun.user_id == user.id).with_for_update()
            )
            if run is None:
                raise NotFoundError("No such run.")
            if run.status != "awaiting_confirmation":
                raise NotAwaitingConfirmationError()
            pending = {p["id"]: p for p in run.pending}
            if set(decisions) != set(pending):
                raise HauskraftError(
                    "Answer every pending confirmation of this run.", code="invalid_decisions", status=422
                )
            config = await read_config(session, self.settings)
            require_configured(config.chat)
            denied: list[AssistantAction] = []
            for call_id, approve in decisions.items():
                if not approve:
                    p = pending[call_id]
                    action = AssistantAction(
                        run_id=run.id,
                        user_id=user.id,
                        tool=p["tool"],
                        status="denied",
                        summary_key=p["summary_key"],
                        record=p["record"],
                    )
                    session.add(action)
                    denied.append(action)
            run.status = "running"
            run.pending = []
            tools = self.select(user, config)
            instructions = await self._prompt(session, user, tools, channel=run.channel)
            await session.flush()
            for action in denied:
                await session.refresh(action)
            history = list(ModelMessagesTypeAdapter.validate_python(run.history))
        approvals: dict[str, Any] = {cid: True if ok else ToolDenied() for cid, ok in decisions.items()}
        outcome = await self._execute(
            run=run,
            user=user,
            config=config,
            tools=tools,
            instructions=instructions,
            prompt=None,
            history=history,
            deferred=DeferredToolResults(approvals=approvals),
        )
        result = await self._persist(run, user, tools, outcome, kind=run.kind, conversation_id=run.conversation_id)
        result.actions = [*denied, *result.actions]
        return result

    # ------------------------------------------------------------------ undo
    async def undo(self, user: User, action_id: uuid.UUID) -> AssistantAction:
        async with self.sessionmaker() as session, session.begin():
            action = await session.scalar(
                select(AssistantAction)
                .where(AssistantAction.id == action_id, AssistantAction.user_id == user.id)
                .with_for_update()
            )
            if action is None:
                raise NotFoundError("No such action.")
            if action.status != "done" or not action.undo:
                raise UndoUnavailableError()
            inverse = dict(action.undo)
        try:
            tool = self.registry.by_name(inverse["tool"])
        except KeyError as exc:
            raise UndoUnavailableError() from exc
        args = tool.spec.input_model.model_validate(inverse["args"])
        await tool.spec.handler(tool.context, actor_for_run(user, None), args)  # type: ignore[arg-type]
        async with self.sessionmaker() as session, session.begin():
            row: AssistantAction | None = await session.get(AssistantAction, action_id, with_for_update=True)
            if row is None:  # pragma: no cover - deleted with its chat meanwhile
                raise NotFoundError("No such action.")
            row.status = "undone"
            await session.flush()
            await session.refresh(row)
        return row

    # ------------------------------------------------------------------ skills (M2S-E05-02)
    def skill(self, skill_id: str) -> Skill:
        found = self.skills.get(skill_id)
        if found is None or found.plugin_id in self.disabled_plugins:
            raise NotFoundError("No such skill.")
        return found

    async def run_skill(self, user: User, skill_id: str, text: str | None) -> RunResultData:
        """Run a skill as the caller with exactly its tools; the run has no chat (schedules can trigger it later)."""
        skill = self.skill(skill_id)
        async with self.sessionmaker() as session, session.begin():
            config = await read_config(session, self.settings)
            require_configured(config.chat)
            tools = self.select(user, config, skill_tools=skill.tools)
            run = AssistantRun(
                user_id=user.id,
                kind="skill",
                skill_id=skill.id,
                status="running",
                model=config.chat.model,
                prompt_version=prompt_version(),
                tools_hash=tools_hash(tools),
            )
            session.add(run)
            instructions = await self._prompt(
                session, user, tools, skill_id=skill.id, skill_instructions=skill.instructions
            )
            await session.flush()
        output_type: Any = StructuredDict(skill.output, name="final_result") if isinstance(skill.output, dict) else str
        outcome = await self._execute(
            run=run,
            user=user,
            config=config,
            tools=tools,
            instructions=instructions,
            prompt=text or "Run the skill now.",
            history=[],
            output_type=output_type,
        )
        return await self._persist(run, user, tools, outcome, kind="skill", conversation_id=None)

    async def latest_skill_run(self, user: User, skill_id: str) -> AssistantRun:
        self.skill(skill_id)
        async with self.sessionmaker() as session:
            run: AssistantRun | None = await session.scalar(
                select(AssistantRun)
                .where(
                    AssistantRun.user_id == user.id, AssistantRun.skill_id == skill_id, AssistantRun.status == "done"
                )
                .order_by(AssistantRun.created_at.desc(), AssistantRun.id.desc())
                .limit(1)
            )
        if run is None:
            raise NotFoundError("No run of this skill yet.")
        return run
