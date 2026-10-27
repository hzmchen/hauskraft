# SPDX-License-Identifier: MIT
"""M2S-E09-01: tool calls are read from a run's stored history; the harness's output tool isn't one of them."""

from typing import Any

import pytest
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)

from hauskraft_core.assistant.runs import OUTPUT_TOOL
from hauskraft_evals.household import tool_calls

pytestmark = pytest.mark.unit


def _history(*messages: ModelRequest | ModelResponse) -> list[Any]:
    return ModelMessagesTypeAdapter.dump_python(list(messages), mode="json")


def test_calls_are_named_and_marked_by_their_result() -> None:
    history = _history(
        ModelResponse(parts=[ToolCallPart("tasks_list", {"status": "all"}, tool_call_id="a")]),
        ModelRequest(parts=[ToolReturnPart("tasks_list", {"items": []}, tool_call_id="a")]),
        ModelResponse(parts=[ToolCallPart("tasks_update", {"task_id": "x", "done": True}, tool_call_id="b")]),
        ModelRequest(parts=[RetryPromptPart("task_not_found", tool_name="tasks_update", tool_call_id="b")]),
    )
    calls = tool_calls(history, lambda wire: wire.replace("_", ".", 1))
    assert [(c.name, c.args, c.ok) for c in calls] == [
        ("tasks.list", {"status": "all"}, True),
        ("tasks.update", {"task_id": "x", "done": True}, False),
    ]


def test_the_harness_output_tool_is_not_a_tool_call() -> None:
    history = _history(
        ModelResponse(parts=[ToolCallPart(OUTPUT_TOOL, {"tasks": []}, tool_call_id="out")]),
        ModelRequest(parts=[ToolReturnPart(OUTPUT_TOOL, "Final result processed.", tool_call_id="out")]),
    )
    assert tool_calls(history, lambda wire: wire) == []
