# SPDX-License-Identifier: MIT
"""M2S-E04-04 the gate and confirmations, M2S-E04-06 Undo (ADR 0020). Against the demo stack with the fake model."""

from __future__ import annotations

import pytest

from _support.live import Api, assert_problem, new_chat, say, tasks_titled

pytestmark = pytest.mark.live
story = pytest.mark.story


def decide(api: Api, result: dict, approve: bool) -> dict:
    run = result["run"]
    decisions = [{"id": c["id"], "approve": approve} for c in result["confirmations"]]
    r = api.post(f"/assistant/runs/{run['id']}/confirmations", json={"decisions": decisions}, timeout=90)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- M2S-E04-04
@story("M2S-E04-04")
def test_delete_waits_for_confirmation(assistant: Api, make_task, unique_title) -> None:
    title = unique_title("Delete me")
    task = make_task(title)
    result = say(assistant, new_chat(assistant), f"Delete '{title}'")
    assert result["run"]["status"] == "awaiting_confirmation"
    [confirmation] = result["confirmations"]
    assert confirmation["tool"] == "tasks.delete"
    assert confirmation["args"] == {"task_id": task["id"]}
    assert confirmation["record"] == {"type": "Task", "id": task["id"], "label": title}
    assert confirmation["summary_key"] == "tasks:tool.delete.confirm"
    assert assistant.get(f"/tasks/{task['id']}").status_code == 200, "nothing happens before the answer"


@story("M2S-E04-04")
def test_denied_confirmation_changes_nothing(assistant: Api, make_task, unique_title) -> None:
    title = unique_title("Keep me")
    task = make_task(title)
    waiting = say(assistant, new_chat(assistant), f"Delete '{title}'")
    result = decide(assistant, waiting, approve=False)
    assert result["run"]["status"] == "done"
    assert result["messages"][-1]["text"] == f"I did not delete '{title}'."
    assert [a["status"] for a in result["actions"]] == ["denied"]
    assert assistant.get(f"/tasks/{task['id']}").status_code == 200


@story("M2S-E04-04")
def test_approved_confirmation_runs_the_tool(assistant: Api, make_task, unique_title) -> None:
    title = unique_title("Delete me now")
    task = make_task(title)
    waiting = say(assistant, new_chat(assistant), f"Delete '{title}'")
    result = decide(assistant, waiting, approve=True)
    assert result["run"]["status"] == "done"
    assert result["messages"][-1]["text"] == f"Deleted '{title}'."
    [action] = result["actions"]
    assert action["tool"] == "tasks.delete" and action["status"] == "done"
    assert assistant.get(f"/tasks/{task['id']}").status_code == 404


@story("M2S-E04-04")
def test_answering_twice_or_someone_elses_run(assistant: Api, alex: Api, make_task, unique_title) -> None:
    title = unique_title("Twice")
    make_task(title)
    waiting = say(assistant, new_chat(assistant), f"Delete '{title}'")
    path = f"/assistant/runs/{waiting['run']['id']}/confirmations"
    body = {"decisions": [{"id": waiting["confirmations"][0]["id"], "approve": False}]}
    assert_problem(alex.post(path, json=body), 404, "not_found")
    assert assistant.post(path, json=body, timeout=90).status_code == 200
    assert_problem(assistant.post(path, json=body), 409, "not_awaiting_confirmation")


@story("M2S-E04-04")
def test_writes_that_are_not_destructive_run_at_once(assistant: Api, cleanup_titles: list, unique_title) -> None:
    title = unique_title("No question")
    cleanup_titles.append(title)
    result = say(assistant, new_chat(assistant), f"Add '{title}'")
    assert result["run"]["status"] == "done" and result["confirmations"] == []
    assert tasks_titled(assistant, title)


# ---------------------------------------------------------------- M2S-E04-06
@story("M2S-E04-06")
def test_undo_a_created_task(assistant: Api, cleanup_titles: list, unique_title) -> None:
    title = unique_title("Undo create")
    cleanup_titles.append(title)
    [action] = say(assistant, new_chat(assistant), f"Add '{title}'")["actions"]
    assert action["undo_available"] is True
    r = assistant.post(f"/assistant/actions/{action['id']}/undo")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "undone" and r.json()["undo_available"] is False
    assert tasks_titled(assistant, title) == []
    assert_problem(assistant.post(f"/assistant/actions/{action['id']}/undo"), 409, "undo_unavailable")


@story("M2S-E04-06")
def test_undo_a_rename_restores_the_title(assistant: Api, make_task, unique_title) -> None:
    old, new = unique_title("Old name"), unique_title("New name")
    task = make_task(old)
    actions = say(assistant, new_chat(assistant), f"Rename '{old}' to '{new}'")["actions"]
    [action] = [a for a in actions if a["tool"] == "tasks.update"]
    assert assistant.get(f"/tasks/{task['id']}").json()["title"] == new
    assert assistant.post(f"/assistant/actions/{action['id']}/undo").status_code == 200
    assert assistant.get(f"/tasks/{task['id']}").json()["title"] == old


@story("M2S-E04-06")
def test_deletes_have_no_undo_and_others_cannot_undo(assistant: Api, alex: Api, make_task, cleanup_titles: list,
                                                     unique_title) -> None:
    title = unique_title("Not yours")
    cleanup_titles.append(title)
    [action] = say(assistant, new_chat(assistant), f"Add '{title}'")["actions"]
    assert_problem(alex.post(f"/assistant/actions/{action['id']}/undo"), 404, "not_found")
    gone = unique_title("Gone")
    make_task(gone)
    waiting = say(assistant, new_chat(assistant), f"Delete '{gone}'")
    [deleted] = decide(assistant, waiting, approve=True)["actions"]
    assert deleted["undo_available"] is False
    assert_problem(assistant.post(f"/assistant/actions/{deleted['id']}/undo"), 409, "undo_unavailable")
