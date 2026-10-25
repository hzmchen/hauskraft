# SPDX-License-Identifier: MIT
"""M2S-E04-01 conversations are private to their writer and kept until deleted (backlog D5), against the demo stack."""

from __future__ import annotations

import pytest

from _support.live import Api, assert_problem, new_chat, say

pytestmark = pytest.mark.live
story = pytest.mark.story


@story("M2S-E04-01")
def test_create_list_read_and_delete(assistant: Api) -> None:
    r = assistant.post("/assistant/conversations")
    assert r.status_code == 201, r.text
    conv = r.json()
    assert set(conv) >= {"id", "title", "created_at", "updated_at"} and conv["title"] is None
    listed = assistant.get("/assistant/conversations").json()
    assert listed[0]["id"] == conv["id"], "newest first"
    detail = assistant.get(f"/assistant/conversations/{conv['id']}").json()
    assert detail["messages"] == [] and detail["actions"] == []
    assert assistant.delete(f"/assistant/conversations/{conv['id']}").status_code == 204
    assert conv["id"] not in [c["id"] for c in assistant.get("/assistant/conversations").json()]
    assert_problem(assistant.get(f"/assistant/conversations/{conv['id']}"), 404, "not_found")


@story("M2S-E04-01")
def test_title_comes_from_the_first_message(assistant: Api) -> None:
    cid = new_chat(assistant)
    say(assistant, cid, "Hello!")
    assert assistant.get(f"/assistant/conversations/{cid}").json()["title"] == "Hello!"
    assistant.delete(f"/assistant/conversations/{cid}")


@story("M2S-E04-01")
def test_messages_are_kept_in_order(assistant: Api) -> None:
    cid = new_chat(assistant)
    say(assistant, cid, "Hello!")
    say(assistant, cid, "Hallo")
    msgs = assistant.get(f"/assistant/conversations/{cid}").json()["messages"]
    assert [(m["role"], m["text"]) for m in msgs] == [
        ("user", "Hello!"), ("assistant", "Hello! How can I help?"),
        ("user", "Hallo"), ("assistant", "Hello! How can I help?"),
    ]
    assistant.delete(f"/assistant/conversations/{cid}")


@story("M2S-E04-01")
def test_chats_are_private_even_from_owners(assistant: Api, alex: Api) -> None:
    alex_chat = new_chat(alex)
    owner_chat = new_chat(assistant)
    try:
        assert alex_chat not in [c["id"] for c in assistant.get("/assistant/conversations").json()]
        assert owner_chat not in [c["id"] for c in alex.get("/assistant/conversations").json()]
        for path in (f"/assistant/conversations/{alex_chat}",):
            assert_problem(assistant.get(path), 404, "not_found")
            assert_problem(assistant.delete(path), 404, "not_found")
        r = assistant.post(f"/assistant/conversations/{alex_chat}/messages", json={"text": "Hello!"})
        assert_problem(r, 404, "not_found")
        assert_problem(alex.get(f"/assistant/conversations/{owner_chat}"), 404, "not_found")
    finally:
        alex.delete(f"/assistant/conversations/{alex_chat}")
        assistant.delete(f"/assistant/conversations/{owner_chat}")


@story("M2S-E04-01")
def test_conversations_need_a_session(anon: Api) -> None:
    assert anon.get("/assistant/conversations").status_code == 401


@story("M2S-E04-01")
@pytest.mark.parametrize("body", [{"text": ""}, {"text": "x" * 4001}, {}])
def test_message_length_is_checked(assistant: Api, body: dict) -> None:
    cid = new_chat(assistant)
    assert_problem(assistant.post(f"/assistant/conversations/{cid}/messages", json=body), 422)
    assistant.delete(f"/assistant/conversations/{cid}")
