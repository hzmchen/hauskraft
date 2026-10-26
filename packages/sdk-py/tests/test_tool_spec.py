# SPDX-License-Identifier: MIT
"""M2S-E02-02: the tool contract plugins register in code (ADR 0019)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

import hauskraft_sdk
from hauskraft_sdk import Actor, PluginContext
from hauskraft_sdk.tools import RecordRef, ToolAnnotations, ToolOutcome, ToolSpec, UndoCall

pytestmark = pytest.mark.unit


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    due_on: str | None = None


async def handler(ctx: PluginContext, actor: Actor, args: BaseModel) -> ToolOutcome:
    return ToolOutcome(output={"ok": True})


def spec(**overrides: object) -> ToolSpec:
    values: dict[str, object] = {
        "name": "tasks.create",
        "description": "Add a task.",
        "input_model": Args,
        "handler": handler,
        "permission": "task.create",
        "data_class": "household",
    }
    values.update(overrides)
    return ToolSpec(**values)  # type: ignore[arg-type]


def test_exports() -> None:
    for name in ("ToolSpec", "ToolAnnotations", "ToolOutcome", "RecordRef", "UndoCall"):
        assert hasattr(hauskraft_sdk.tools, name)


def test_wire_name_and_flat_parameters() -> None:
    s = spec()
    assert s.wire_name == "tasks_create"
    params = s.parameters()
    assert params["type"] == "object"
    assert set(params["properties"]) == {"title", "due_on"}
    assert params["required"] == ["title"]


def test_missing_annotations_count_as_destructive_and_open_world() -> None:
    a = ToolAnnotations()
    assert (a.read_only, a.destructive, a.idempotent, a.open_world) == (False, True, False, True)


@pytest.mark.parametrize("name", ["create", "Tasks.create", "tasks.Create", "tasks..create", "tasks.create.now"])
def test_names_are_plugin_dot_verb(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        spec(name=name)


def test_agent_tools_need_a_short_description() -> None:
    with pytest.raises(ValueError, match="description"):
        spec(description="")
    with pytest.raises(ValueError, match="description"):
        spec(description="x" * 401)
    assert spec(description="", agent=False).agent is False


def test_permission_is_an_action_name() -> None:
    with pytest.raises(ValueError, match="permission"):
        spec(permission="Create tasks")


def test_outcome_carries_record_summary_and_undo() -> None:
    outcome = ToolOutcome(
        output={"task": {"id": "t1"}},
        record=RecordRef(type="Task", id="t1", label="Buy milk"),
        summary_key="tasks:tool.create.done",
        undo=UndoCall(tool="tasks.delete", args={"task_id": "t1"}),
    )
    assert outcome.record is not None
    assert outcome.record.label == "Buy milk"
    assert outcome.undo is not None
    assert outcome.undo.tool == "tasks.delete"


def test_registration_accepts_tools() -> None:
    from fastapi import APIRouter

    reg = hauskraft_sdk.PluginRegistration(router=APIRouter(), tools=[spec()])
    assert [t.name for t in reg.tools] == ["tasks.create"]
    assert hauskraft_sdk.PluginRegistration(router=APIRouter()).tools == ()
