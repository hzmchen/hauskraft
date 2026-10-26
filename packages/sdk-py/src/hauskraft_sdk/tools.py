# SPDX-License-Identifier: MIT
"""Agent tools: the contract plugins register in code (M2S-E02-02, ADR 0019, spec §5.3).

A plugin lists each tool in its manifest (``contributes.tools[]``) and registers the same tool here, in
``PluginRegistration.tools``. Core refuses a plugin whose manifest and code disagree. The handler calls the plugin's
service functions, so ``authorize()`` and one event per write still hold; it runs as the person using the assistant.

Models see the tool as a Chat Completions function named ``wire_name`` (``tasks.create`` -> ``tasks_create``) whose
parameters are the input model's JSON schema, flat.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from hauskraft_sdk.data_classes import DataClass
from hauskraft_sdk.plugin import Actor, PluginContext

NAME = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
PERMISSION = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
DESCRIPTION_MAX = 400


@dataclass(frozen=True, slots=True)
class ToolAnnotations:
    """MCP-style hints. The defaults are the cautious ones: a tool that says nothing counts as a destructive,
    open-world write (spec §5.3)."""

    read_only: bool = False
    destructive: bool = True
    idempotent: bool = False
    open_world: bool = True

    def as_dict(self) -> dict[str, bool]:
        return {
            "read_only": self.read_only,
            "destructive": self.destructive,
            "idempotent": self.idempotent,
            "open_world": self.open_world,
        }


@dataclass(frozen=True, slots=True)
class RecordRef:
    """What a tool call touched, for action and confirmation cards: e.g. ``RecordRef("Task", id, "Buy milk")``."""

    type: str
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class UndoCall:
    """The call that reverses a tool call, run as the same person if they choose Undo (ADR 0020)."""

    tool: str
    args: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    """What a handler returns. ``output`` goes back to the model, so keep it compact: the fields it needs, short
    lists. ``summary_key`` is an i18n key of the plugin's namespace (``tasks:tool.create.done``) that the web app
    renders with ``record.label``."""

    output: Any
    record: RecordRef | None = None
    summary_key: str | None = None
    undo: UndoCall | None = None


Handler = Callable[[PluginContext, Actor, Any], Awaitable[ToolOutcome]]
Preview = Callable[[PluginContext, Actor, Any], Awaitable[RecordRef | None]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """One agent tool. ``handler(ctx, actor, args)`` receives a validated ``input_model`` instance.

    ``preview`` (optional) names the record a confirmation is about ("Delete task 'Buy milk'?") before the call runs.
    Raise the SDK's errors (``NotFoundError``, ``ConflictError``, ...) for problems: their ``code`` reaches the model,
    so it can recover or explain.
    """

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Handler
    permission: str
    data_class: DataClass | str = "household"
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)
    agent: bool = True
    preview: Preview | None = None

    def __post_init__(self) -> None:
        if not NAME.match(self.name):
            raise ValueError(f"tool name {self.name!r} must be <plugin>.<verb> in lower case")
        if self.agent and not 1 <= len(self.description) <= DESCRIPTION_MAX:
            raise ValueError(f"{self.name}: an agent tool needs a description of 1 to {DESCRIPTION_MAX} characters")
        if not PERMISSION.match(self.permission):
            raise ValueError(f"{self.name}: permission {self.permission!r} must be an action name such as task.create")

    @property
    def wire_name(self) -> str:
        return self.name.replace(".", "_")

    def parameters(self) -> dict[str, Any]:
        """The input model's JSON schema: the function's parameters, flat."""
        return self.input_model.model_json_schema()
