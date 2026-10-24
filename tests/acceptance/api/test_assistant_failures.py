# SPDX-License-Identifier: MIT
"""M2S-E04-05 run limits and failures: a run reports a stable error code instead of a server error."""

from __future__ import annotations

import uuid

import pytest

from _support.live import Api, configure_fake, fake_requests, new_chat, say

pytestmark = pytest.mark.live
story = pytest.mark.story


@pytest.mark.parametrize(("change", "code"), [
    ({"model": "fake-broken"}, "model_unavailable"),
    ({"api_key": "wrong-key"}, "auth_failed"),
])
@story("M2S-E04-05")
def test_endpoint_errors_fail_the_run_cleanly(assistant: Api, change: dict, code: str) -> None:
    configure_fake(assistant, **change)
    try:
        result = say(assistant, new_chat(assistant), "Hello!")
        assert result["run"]["status"] == "failed" and result["run"]["error_code"] == code
    finally:
        configure_fake(assistant)


@story("M2S-E04-05")
def test_endless_tool_calls_hit_the_run_limit(assistant: Api) -> None:
    marker = f"loop-{uuid.uuid4().hex[:8]}"
    configure_fake(assistant, model="fake-loop")
    try:
        result = say(assistant, new_chat(assistant), f"Keep going {marker}")
        assert result["run"]["status"] == "failed" and result["run"]["error_code"] == "run_limit"
        assert len(fake_requests(marker)) <= 8, "at most 8 model requests per run"
    finally:
        configure_fake(assistant)


@story("M2S-E04-05")
def test_tool_errors_reach_the_model(assistant: Api) -> None:
    missing = str(uuid.uuid4())
    result = say(assistant, new_chat(assistant), f"Complete the task with id {missing}")
    assert result["run"]["status"] == "done"
    assert result["messages"][-1]["text"] == "That task doesn't exist."
    sent = fake_requests(missing)
    tool_messages = [m for m in sent[-1]["messages"] if m.get("role") == "tool"]
    assert tool_messages and "task_not_found" in str(tool_messages[-1].get("content"))
