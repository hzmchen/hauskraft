# SPDX-License-Identifier: MIT
"""The contract between core and an in-process plugin (M0S-E06-02, ADR-0004, ADR-0006)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from fastapi import APIRouter
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_sdk.data_classes import DataClass

HEARTHOS_API_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class Actor:
    """Who is acting: a signed-in user now, an agent on a user's behalf from M1."""

    id: str
    role: str
    display_name: str = ""
    kind: Literal["user", "agent", "system"] = "user"


@dataclass(frozen=True, slots=True)
class ResourceRef:
    """What an action touches, e.g. ``ResourceRef("Task", task_id)``."""

    type: str
    id: str | None = None


@runtime_checkable
class PluginContext(Protocol):
    """Everything core offers a plugin. Plugins never import ``hearthos_core``."""

    plugin_id: str
    logger: logging.Logger
    config: Mapping[str, Any]

    current_actor: Callable[..., Awaitable[Actor]]
    """FastAPI dependency resolving the signed-in actor: ``actor: Actor = Depends(ctx.current_actor)``.

    Answers 401 without a session and 403 ``csrf_failed`` for writes without the CSRF token."""

    def db_session(self) -> AbstractAsyncContextManager[AsyncSession]:
        """A unit of work: one transaction, committed on clean exit, rolled back on error.

        Rows written and events emitted inside it commit or roll back together.
        """
        ...

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> None:
        """Ask the policy before every write; raises ``PolicyDeniedError`` when denied."""
        ...

    async def emit(self, event_type: str, subject: str, data: Any, data_class: DataClass | str) -> str:
        """Append one CloudEvent to the current unit of work's outbox; returns the event id.

        ``source`` is the plugin id and ``actorid`` the actor last authorized in this unit of work.
        Raises outside a unit of work.
        """
        ...


SeedFunction = Callable[[PluginContext, Mapping[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PluginRegistration:
    """What ``Plugin.register`` hands back to core."""

    router: APIRouter
    metadata: MetaData | None = None
    seed: SeedFunction | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class Plugin(Protocol):
    """An in-process plugin object, referenced by ``runtime.entrypoint`` (``module:attribute``)."""

    id: str

    def register(self, ctx: PluginContext) -> PluginRegistration: ...
