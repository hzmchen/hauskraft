# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E02-03: one registry offers each run only the tools it may use (ADR 0019)."""

import pytest
from pydantic import BaseModel

from hauskraft_core.assistant.registry import RegisteredTool, ToolRegistry, tools_hash
from hauskraft_sdk import Actor, PluginContext
from hauskraft_sdk.tools import ToolAnnotations, ToolOutcome, ToolSpec

pytestmark = pytest.mark.unit


class Args(BaseModel):
    text: str = ""


async def handle(ctx: PluginContext, actor: Actor, args: BaseModel) -> ToolOutcome:
    return ToolOutcome(output={})


def tool(name: str, permission: str, data_class: str = "household", agent: bool = True) -> ToolSpec:
    return ToolSpec(name=name, description=f"{name} tool", input_model=Args, handler=handle, permission=permission,
                    data_class=data_class, annotations=ToolAnnotations(), agent=agent)


REGISTRY = ToolRegistry([
    RegisteredTool(tool("tasks.list", "task.read"), "dev.hauskraft.tasks", None),
    RegisteredTool(tool("tasks.delete", "task.delete"), "dev.hauskraft.tasks", None),
    RegisteredTool(tool("money.pay", "money.pay", data_class="financial"), "org.example.money", None),
    RegisteredTool(tool("members.add", "user.create"), "org.example.members", None),
    RegisteredTool(tool("tasks.reindex", "task.update", agent=False), "dev.hauskraft.tasks", None),
])


def names(tools: list[RegisteredTool]) -> list[str]:
    return [t.spec.name for t in tools]


def test_agent_false_tools_are_never_listed() -> None:
    assert "tasks.reindex" not in names(REGISTRY.all())


def test_order_is_plugin_then_name() -> None:
    assert names(REGISTRY.all()) == ["tasks.delete", "tasks.list", "members.add", "money.pay"]


def test_role_permissions_filter() -> None:
    adult = REGISTRY.select(role="adult", max_data_class="secret")
    assert "members.add" not in names(adult), "user.create is owner-only"
    assert "members.add" in names(REGISTRY.select(role="owner", max_data_class="secret"))
    assert "money.pay" not in names(adult), "an action missing from the permission table is never offered"


def test_switched_off_tools_and_disabled_plugins() -> None:
    picked = REGISTRY.select(role="owner", disabled_tools={"tasks.delete"}, disabled_plugins={"org.example.members"})
    assert names(picked) == ["tasks.list"]


def test_data_class_ceiling() -> None:
    assert "money.pay" not in names(REGISTRY.select(role="owner", max_data_class="household"))


def test_skill_allowlist() -> None:
    assert names(REGISTRY.select(role="owner", skill_tools=["tasks.list"])) == ["tasks.list"]
    assert REGISTRY.select(role="owner", skill_tools=[]) == []


def test_lookup_by_wire_name() -> None:
    assert REGISTRY.by_wire_name("tasks_list").spec.name == "tasks.list"


def test_tools_hash_is_stable_and_follows_the_set() -> None:
    one = REGISTRY.select(role="owner")
    assert tools_hash(one) == tools_hash(list(one))
    assert tools_hash(one) != tools_hash(one[:1])
    assert len(tools_hash(one)) == 16
