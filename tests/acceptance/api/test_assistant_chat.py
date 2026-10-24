# SPDX-License-Identifier: MIT
"""M2S-E04-02 chat runs with tools, the system prompt contract, and M2S-E04-07 "via assistant" (ADR 0020).
Against the demo stack with the fake model."""

from __future__ import annotations

import datetime as dt
import re
import uuid
from zoneinfo import ZoneInfo

import pytest

from _support.live import (Api, assert_problem, configure_fake, fake_requests, new_chat, say, system_prompt,
                           tasks_titled, wait_for_activity)

pytestmark = pytest.mark.live
story = pytest.mark.story


def tomorrow_in(tz: str) -> str:
    return (dt.datetime.now(ZoneInfo(tz)).date() + dt.timedelta(days=1)).isoformat()


@story("M2S-E04-02")
def test_adding_a_task_runs_the_tool_as_the_person(assistant: Api, cleanup_titles: list, unique_title) -> None:
    title = unique_title("Buy milk")
    cleanup_titles.append(title)
    result = say(assistant, new_chat(assistant), f"Add '{title}', due tomorrow")
    assert result["run"]["status"] == "done" and result["run"]["kind"] == "chat"
    tz = assistant.get("/household").json()["timezone"]
    [task] = tasks_titled(assistant, title)
    assert task["due_on"] == tomorrow_in(tz), "tomorrow is counted in the household time zone"
    assert task["created_by"]["id"] == assistant.session["user"]["id"]
    [action] = result["actions"]
    assert action["tool"] == "tasks.create" and action["status"] == "done"
    assert action["record"] == {"type": "Task", "id": task["id"], "label": title}
    assert action["summary_key"] == "tasks:tool.create.done"
    assert [m["role"] for m in result["messages"]] == ["user", "assistant"]
    assert result["messages"][1]["text"].startswith(f"Added '{title}'")


@story("M2S-E04-02")
def test_listing_and_completing(assistant: Api, make_task, unique_title) -> None:
    title = unique_title("Plan the garden")
    task = make_task(title)
    cid = new_chat(assistant)
    assert title in say(assistant, cid, "What is still open?")["messages"][-1]["text"]
    done = say(assistant, cid, f"Mark '{title}' as done")
    assert done["run"]["status"] == "done"
    assert [a["tool"] for a in done["actions"]] == ["tasks.update"], "read-only calls are not actions"
    assert done["actions"][0]["summary_key"] == "tasks:tool.complete.done"
    assert assistant.get(f"/tasks/{task['id']}").json()["done"] is True


@story("M2S-E04-02")
def test_system_prompt_follows_the_contract(assistant: Api, unique_title) -> None:
    marker = unique_title("prompt")
    say(assistant, new_chat(assistant), f"Hello! {marker}")
    [sent] = fake_requests(marker)
    prompt = system_prompt(sent)
    household = assistant.get("/household").json()
    me = assistant.session["user"]
    today = dt.datetime.now(ZoneInfo(household["timezone"])).date()
    dates = "|".join((today + dt.timedelta(days=d)).isoformat() for d in (-1, 0, 1))
    lines = prompt.rstrip().splitlines()
    tail = lines[-4:]
    assert re.fullmatch(rf"Today: ({dates}) \([A-Z][a-z]+\), \d\d:\d\d in {re.escape(household['timezone'])}",
                        tail[0]), tail
    assert tail[1] == f"Household: {household['name']}"
    assert tail[2] == f"Person: {me['display_name']} ({me['role']})"
    assert re.fullmatch(r"Language: English\b.*", tail[3]), "the context block ends the prompt, in this order"
    assert "Skill:" not in prompt
    assert sent["model"] == "fake-tools" and sent["body"].get("stream") in (None, False)


@story("M2S-E04-02")
def test_a_german_member_gets_german_answers(assistant: Api, ready_member, unique_title) -> None:
    _, api = ready_member()
    assert api.patch("/me", json={"locale": "de"}).status_code == 200
    marker = unique_title("sprache")
    say(api, new_chat(api), f"Hallo {marker}")
    [sent] = fake_requests(marker)
    prompt = system_prompt(sent)
    assert re.search(r"(?m)^Language: German\b", prompt)
    assert re.search(r"(?m)^Person: .+ \(adult\)$", prompt)


@story("M2S-E04-02")
def test_earlier_turns_are_sent_again(assistant: Api, unique_title) -> None:
    first, second = unique_title("first"), unique_title("second")
    cid = new_chat(assistant)
    say(assistant, cid, f"Hello! {first}")
    say(assistant, cid, f"Hello! {second}")
    [sent] = fake_requests(second)
    texts = " ".join(str(m.get("content")) for m in sent["messages"])
    assert first in texts, "the conversation's earlier turns are part of the request"


@story("M2S-E04-02")
def test_not_configured_answers_409(assistant: Api) -> None:
    cid = new_chat(assistant)
    assert assistant.delete("/assistant/settings/chat").status_code == 204
    try:
        r = assistant.post(f"/assistant/conversations/{cid}/messages", json={"text": "Hello!"})
        assert_problem(r, 409, "assistant_not_configured")
    finally:
        configure_fake(assistant)
        assistant.delete(f"/assistant/conversations/{cid}")


# ---------------------------------------------------------------- M2S-E04-07
@story("M2S-E04-07")
def test_events_carry_the_run_and_the_person(assistant: Api, cleanup_titles: list, unique_title) -> None:
    title = unique_title("via assistant")
    cleanup_titles.append(title)
    result = say(assistant, new_chat(assistant), f"Add '{title}'")
    [task] = tasks_titled(assistant, title)
    entry = wait_for_activity(assistant, f"task/{task['id']}", "hauskraft.task.created")
    assert entry, "task.created never reached the activity feed"
    assert entry.get("agentrunid") == result["run"]["id"], entry
    assert entry["actor"]["id"] == assistant.session["user"]["id"], "the person stays the actor"
    assert entry["actor"]["display_name"] == assistant.session["user"]["display_name"]


@story("M2S-E04-07")
def test_manual_changes_have_no_run(demo: Api, make_task) -> None:
    task = make_task(f"acc-{uuid.uuid4().hex[:8]} manual")
    entry = wait_for_activity(demo, f"task/{task['id']}", "hauskraft.task.created")
    assert entry and not entry.get("agentrunid")
