# SPDX-License-Identifier: MIT
"""The household the evals run in: a migrated database, the app in-process, an owner and an adult.

Everything goes through the HTTP API with the real harness, the real tools and the real permission checks. Only
two things differ from production, both through ``app.state`` (``Harness.of``): the prompt's clock is the case's
"today", and tests may swap in another model (Pydantic AI's ``FunctionModel``).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import secrets
import time
import uuid
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hauskraft_core.app import create_app
from hauskraft_core.db.models import AssistantRun, AssistantUsage
from hauskraft_core.policy import NoOpPolicy
from hauskraft_core.settings import Settings
from hauskraft_core.uow import UnitOfWork
from hauskraft_core.users.service import SYSTEM_ACTOR, create_user
from hauskraft_evals.checks import Outcome, ToolCall
from hauskraft_evals.datasets import EvalCase

ORIGIN = "http://testserver"
API = "/api/v1"


class HouseholdError(RuntimeError):
    """The app refused a setup step; the message names the request and the answer."""


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    api_key: str
    model: str


@dataclass
class _Person:
    cookies: dict[str, str]
    csrf: str


class Household:
    def __init__(self, settings: Settings, *, endpoint: Endpoint | None = None, model: Model | None = None) -> None:
        if endpoint is None and model is None:
            raise ValueError("an endpoint or a model is needed")
        self.settings = settings.model_copy(update={"allowed_origins": [ORIGIN]})
        self.endpoint = endpoint or Endpoint("http://model.invalid/v1", "unused", "function-model")
        self.model = model
        self._people: dict[str, _Person] = {}

    # ------------------------------------------------------------------ lifecycle
    def __enter__(self) -> Self:
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, headers={"Origin": ORIGIN})
        self.client.__enter__()
        for role in ("owner", "adult"):
            username, password = f"eval-{role}-{uuid.uuid4().hex[:6]}", secrets.token_urlsafe(18)
            asyncio.run(self._create_user(username, password, role))
            self.client.cookies.clear()
            r = self.client.post(f"{API}/auth/login", json={"username": username, "password": password})
            self._ok(r, "log in")
            cookies = {c.name: c.value or "" for c in self.client.cookies.jar}
            self._people[role] = _Person(cookies, r.json()["csrf_token"])
        chat = {"base_url": self.endpoint.base_url, "model": self.endpoint.model, "api_key": self.endpoint.api_key}
        self._call("owner", "PATCH", "/assistant/settings", json={"chat": chat, "tools_disabled": []})
        if self.model is not None:
            self.app.state.assistant_model = self.model
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.client.__exit__(exc_type, exc, tb)

    async def _create_user(self, username: str, password: str, role: str) -> None:
        engine = create_async_engine(self.settings.database_url, poolclass=NullPool)
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with UnitOfWork(sessions, NoOpPolicy(), self.settings) as uow:
                name = f"Eval {role.title()}"
                await create_user(uow, SYSTEM_ACTOR, username=username, display_name=name, password=password, role=role)
        finally:
            await engine.dispose()

    # ------------------------------------------------------------------ requests
    @staticmethod
    def _ok(response: Any, what: str) -> None:
        if response.status_code >= 400:
            raise HouseholdError(f"{what}: {response.status_code} {response.text[:300]}")

    def _call(self, role: str, method: str, path: str, **kwargs: Any) -> Any:
        person = self._people[role]
        self.client.cookies.clear()
        self.client.cookies.update(person.cookies)
        r = self.client.request(method, API + path, headers={"X-CSRF-Token": person.csrf}, **kwargs)
        self._ok(r, f"{method} {path}")
        return r.json() if r.content else None

    def tasks(self) -> list[dict[str, Any]]:
        items = self._call("owner", "GET", "/tasks", params={"status": "all", "limit": 200})["items"]
        return [{"title": t["title"], "done": t["done"], "due_on": t.get("due_on")} | {"id": t["id"]} for t in items]

    # ------------------------------------------------------------------ one case
    def prepare(self, case: EvalCase) -> None:
        """Reset the household to the case's fixture and fix the prompt's clock to its today."""
        fx = case.fixture
        for task in self.tasks():
            self._call("owner", "DELETE", f"/tasks/{task['id']}")
        self._call("owner", "PATCH", "/household", json={"timezone": fx.timezone})
        self._call(fx.role, "PATCH", "/me", json={"locale": fx.language})
        for t in fx.tasks:
            body: dict[str, Any] = {"title": t.title, "due_on": t.due_on.isoformat() if t.due_on else None}
            created = self._call("owner", "POST", "/tasks", json=body)
            if t.done:
                self._call("owner", "PATCH", f"/tasks/{created['id']}", json={"done": True})
        now = dt.datetime.combine(fx.today, fx.time, tzinfo=ZoneInfo(fx.timezone)).astimezone(dt.UTC)
        self.app.state.assistant_clock = lambda: now

    def run(self, case: EvalCase) -> Outcome:
        """Run the case's input as its person and collect what happened."""
        role, inp = case.fixture.role, case.input
        started = time.monotonic()
        paused = False
        if inp.message is not None:
            cid = self._call(role, "POST", "/assistant/conversations")["id"]
            result = self._call(role, "POST", f"/assistant/conversations/{cid}/messages", json={"text": inp.message})
            paused = result["run"]["status"] == "awaiting_confirmation"
            if paused and inp.confirm is not None:
                decisions = [{"id": c["id"], "approve": inp.confirm == "approved"} for c in result["confirmations"]]
                result = self._call(
                    role, "POST", f"/assistant/runs/{result['run']['id']}/confirmations", json={"decisions": decisions}
                )
            said = [m["text"] for m in result["messages"] if m["role"] == "assistant"]
            answer = said[-1] if said else ""
        else:
            assert inp.skill is not None  # noqa: S101 - CaseInput guarantees a message or a skill
            result = self._call(role, "POST", f"/assistant/skills/{inp.skill}/runs", json={"input": {"text": inp.text}})
            answer = _as_text(result["output"])
        latency = (time.monotonic() - started) * 1000
        run = result["run"]
        calls, tokens = self._inspect(uuid.UUID(run["id"]))
        return Outcome(
            answer=answer,
            tool_calls=calls,
            paused=paused,
            tasks=self.tasks(),
            status=run["status"],
            error_code=run["error_code"],
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            latency_ms=latency,
        )

    def _inspect(self, run_id: uuid.UUID) -> tuple[list[ToolCall], tuple[int, int]]:
        """The run's tool calls (from its stored history) and its tokens (from its usage rows)."""
        engine = create_engine(self.settings.database_url)
        try:
            with engine.connect() as conn:
                history = conn.execute(select(AssistantRun.history).where(AssistantRun.id == run_id)).scalar_one()
                used = conn.execute(
                    select(
                        func.coalesce(func.sum(AssistantUsage.input_tokens), 0),
                        func.coalesce(func.sum(AssistantUsage.output_tokens), 0),
                    ).where(AssistantUsage.run_id == run_id)
                ).one()
        finally:
            engine.dispose()
        registry = self.app.state.tool_registry
        calls: dict[str, ToolCall] = {}
        for message in ModelMessagesTypeAdapter.validate_python(history):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and isinstance(message, ModelResponse):
                    try:
                        name = registry.by_wire_name(part.tool_name).spec.name
                    except KeyError:
                        name = part.tool_name  # a tool the run wasn't offered: the gate denied it
                    calls[part.tool_call_id] = ToolCall(name, part.args_as_dict(), None)
                elif isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id].ok = True
                elif isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id].ok = False
        return list(calls.values()), (int(used[0] or 0), int(used[1] or 0))


def _as_text(output: Any) -> str:
    """A skill's output as the checks read it: text as is, suggested tasks as ``title | due_on`` lines."""
    if isinstance(output, str):
        return output
    if isinstance(output, dict) and isinstance(output.get("tasks"), list):
        return "\n".join(f"{t.get('title')} | {t.get('due_on') or '-'}" for t in output["tasks"])
    return "" if output is None else str(output)
