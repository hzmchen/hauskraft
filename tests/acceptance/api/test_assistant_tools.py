# SPDX-License-Identifier: MIT
"""M2S-E02-03 tool registry and M2S-E02-04 the tasks plugin's tools (ADR 0019), against the demo stack."""

from __future__ import annotations

import json

import pytest

from _support.live import Api, assert_problem, fake_requests, new_chat, say

pytestmark = pytest.mark.live
story = pytest.mark.story
TASK_TOOLS = ["tasks.create", "tasks.delete", "tasks.list", "tasks.update"]
BUDGET_CHARS = 6000  # about 1,500 tokens at four characters per token (the tested approximation, ADR 0019)


def tools_of(owner: Api) -> list[dict]:
    r = owner.get("/assistant/tools")
    assert r.status_code == 200, f"RED (M2S-E02-03): GET /assistant/tools answered {r.status_code}"
    return r.json()


# ---------------------------------------------------------------- M2S-E02-03
@story("M2S-E02-03")
def test_registry_lists_agent_tools_with_their_contract(assistant: Api) -> None:
    tools = tools_of(assistant)
    names = [t["name"] for t in tools]
    assert names == sorted(names, key=lambda n: n), "ordered by plugin, then name"
    for t in tools:
        assert set(t) >= {"name", "wire_name", "plugin_id", "description", "annotations", "data_class", "permission",
                          "enabled"}
        assert t["wire_name"] == t["name"].replace(".", "_")
        assert set(t["annotations"]) == {"read_only", "destructive", "idempotent", "open_world"}


@story("M2S-E02-03")
def test_adult_cannot_list_tools(alex: Api) -> None:
    assert_problem(alex.get("/assistant/tools"), 403, "policy_denied")


@story("M2S-E02-03")
def test_switched_off_tool_is_disabled_and_not_offered(assistant: Api, unique_title) -> None:
    assert assistant.patch("/assistant/settings", json={"tools_disabled": ["tasks.delete"]}).status_code == 200
    by_name = {t["name"]: t for t in tools_of(assistant)}
    assert by_name["tasks.delete"]["enabled"] is False and by_name["tasks.list"]["enabled"] is True
    marker = unique_title("not offered")
    say(assistant, new_chat(assistant), f"Delete '{marker}'")
    sent = fake_requests(marker)
    assert sent and all("tasks_delete" not in r["tools"] for r in sent)


@story("M2S-E02-03")
def test_unknown_tool_cannot_be_switched_off(assistant: Api) -> None:
    assert_problem(assistant.patch("/assistant/settings", json={"tools_disabled": ["tasks.fly"]}), 422,
                   "unknown_tool")


# ---------------------------------------------------------------- M2S-E02-04
@story("M2S-E02-04")
def test_tasks_plugin_exposes_four_tools(assistant: Api) -> None:
    tasks = {t["name"]: t for t in tools_of(assistant) if t["plugin_id"] == "dev.hauskraft.tasks"}
    assert sorted(tasks) == TASK_TOOLS
    assert tasks["tasks.list"]["annotations"]["read_only"] is True
    assert tasks["tasks.delete"]["annotations"]["destructive"] is True
    assert tasks["tasks.create"]["annotations"]["destructive"] is False
    assert tasks["tasks.update"]["annotations"]["idempotent"] is True
    assert {t["data_class"] for t in tasks.values()} == {"household"}
    assert tasks["tasks.list"]["permission"] == "task.read" and tasks["tasks.delete"]["permission"] == "task.delete"


@story("M2S-E02-04")
def test_tools_are_sent_flat_and_within_budget(assistant: Api, unique_title) -> None:
    marker = unique_title("budget")
    say(assistant, new_chat(assistant), f"What is still open? {marker}")
    sent = fake_requests(marker)
    assert sent, "the chat never reached the fake model"
    defs = {t["function"]["name"]: t["function"] for t in sent[0]["body"].get("tools", [])}
    assert {"tasks_list", "tasks_create", "tasks_update", "tasks_delete"} <= set(defs)
    create = defs["tasks_create"]["parameters"]
    assert "title" in create.get("properties", {}), "parameters are the input model, flat"
    assert "task_id" in defs["tasks_update"]["parameters"].get("properties", {})
    size = len(json.dumps([defs[n] for n in ("tasks_list", "tasks_create", "tasks_update", "tasks_delete")]))
    assert size <= BUDGET_CHARS, f"the tasks plugin's tools take {size} characters (budget {BUDGET_CHARS})"
