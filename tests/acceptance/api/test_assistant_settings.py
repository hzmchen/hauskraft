# SPDX-License-Identifier: MIT
"""M2S-E03 assistant permissions, settings and connection test (ADR 0021), plus the fake model in the test stack
(M2S-E01-01). Black-box against the demo stack."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
import pytest

from _support.live import (FAKE_KEY, FAKE_LLM_ADMIN_URL, FAKE_LLM_URL, Api, activity_types_for, assert_problem,
                           configure_fake, fake_requests, wait_for_activity)

pytestmark = pytest.mark.live
story = pytest.mark.story
CHANGED = "hauskraft.settings.assistant_changed"
SUBJECT = "setting/assistant"
ASSISTANT_PERMISSIONS = {"assistant.use", "assistant.configure", "assistant.usage.read"}


@pytest.fixture
def owner(assistant: Api) -> Iterator[Api]:
    yield assistant


# ---------------------------------------------------------------- M2S-E01-01
@story("M2S-E01-01")
def test_fake_model_runs_next_to_the_stack() -> None:
    r = httpx.get(f"{FAKE_LLM_ADMIN_URL}/v1/models", timeout=5)
    assert r.status_code == 200
    assert "fake-tools" in [m["id"] for m in r.json()["data"]]


# ---------------------------------------------------------------- M2S-E03-01
@story("M2S-E03-01")
def test_owner_session_has_every_assistant_permission(demo: Api) -> None:
    assert ASSISTANT_PERMISSIONS <= set(demo.get("/auth/session").json()["permissions"])


@story("M2S-E03-01")
def test_adult_may_use_but_not_configure(alex: Api) -> None:
    perms = set(alex.get("/auth/session").json()["permissions"])
    assert "assistant.use" in perms
    assert not perms & {"assistant.configure", "assistant.usage.read"}


# ---------------------------------------------------------------- M2S-E03-02
@story("M2S-E03-02")
def test_settings_show_a_hint_never_the_key(owner: Api) -> None:
    r = owner.get("/assistant/settings")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    chat = body["chat"]
    assert chat["base_url"] == FAKE_LLM_URL and chat["model"] == "fake-tools"
    assert chat["api_key_set"] is True and chat["api_key_status"] == "ok"
    assert chat["api_key_hint"].endswith("abcd")
    assert chat["locality"] == "cloud" and chat["max_data_class"] == "household"
    assert FAKE_KEY not in r.text
    assert set(body) >= {"configured", "chat", "tools_disabled", "prices"}


@story("M2S-E03-02")
def test_status_is_available_for_every_member(owner: Api, alex: Api) -> None:
    for api in (owner, alex):
        r = api.get("/assistant/status")
        assert r.status_code == 200 and r.json() == {"available": True}


@story("M2S-E03-02")
def test_changes_emit_field_names_only(owner: Api) -> None:
    new_key = "sk-hauskraft-rotated-key-wxyz"
    r = owner.patch("/assistant/settings", json={"chat": {"api_key": new_key, "temperature": 0.2}})
    assert r.status_code == 200, r.text
    assert new_key not in r.text and r.json()["chat"]["api_key_hint"].endswith("wxyz")
    entry = wait_for_activity(owner, SUBJECT, CHANGED)
    assert entry, "assistant_changed never reached the activity feed"
    assert {"chat.api_key", "chat.temperature"} <= set(entry["data"]["changed"])
    assert new_key not in json.dumps(entry) and FAKE_KEY not in json.dumps(entry)
    configure_fake(owner, temperature=None)


@story("M2S-E03-02")
def test_unchanged_patch_emits_nothing(owner: Api) -> None:
    before = activity_types_for(owner, SUBJECT).count(CHANGED)
    assert owner.patch("/assistant/settings", json={"chat": {"model": "fake-tools"}}).status_code == 200
    assert activity_types_for(owner, SUBJECT).count(CHANGED) == before


@story("M2S-E03-02")
@pytest.mark.parametrize("chat", [{"base_url": "ftp://example.org/v1"}, {"base_url": "not a url"},
                                  {"base_url": "/relative/v1"}])
def test_base_url_must_be_http(owner: Api, chat: dict) -> None:
    assert_problem(owner.patch("/assistant/settings", json={"chat": chat}), 422, "invalid_base_url")
    assert owner.get("/assistant/settings").json()["chat"]["base_url"] == FAKE_LLM_URL


@story("M2S-E03-02")
@pytest.mark.parametrize("body", [{"chat": {"model": ""}}, {"chat": {"api_key": ""}}, {"chat": {"locality": "moon"}},
                                  {"chat": {"max_data_class": "everything"}}, {"colour": "red"}])
def test_invalid_values_are_rejected(owner: Api, body: dict) -> None:
    assert_problem(owner.patch("/assistant/settings", json=body), 422)


@story("M2S-E03-02")
def test_adult_cannot_read_or_change_settings(alex: Api) -> None:
    assert_problem(alex.get("/assistant/settings"), 403, "policy_denied")
    assert_problem(alex.patch("/assistant/settings", json={"chat": {"model": "x"}}), 403, "policy_denied")
    assert_problem(alex.post("/assistant/settings/test"), 403, "policy_denied")
    assert_problem(alex.delete("/assistant/settings/chat"), 403, "policy_denied")


@story("M2S-E03-02")
def test_removing_the_endpoint_makes_the_assistant_unavailable(owner: Api, alex: Api) -> None:
    assert owner.delete("/assistant/settings/chat").status_code == 204
    body = owner.get("/assistant/settings").json()
    assert body["configured"] is False and body["chat"]["api_key_set"] is False
    assert alex.get("/assistant/status").json() == {"available": False}
    assert_problem(owner.post("/assistant/settings/test"), 409, "assistant_not_configured")
    configure_fake(owner)
    assert alex.get("/assistant/status").json() == {"available": True}


@story("M2S-E03-02")
def test_settings_need_a_session(anon: Api) -> None:
    assert anon.get("/assistant/settings").status_code == 401
    assert anon.get("/assistant/status").status_code == 401


# ---------------------------------------------------------------- M2S-E03-04
@story("M2S-E03-04")
def test_connection_test_passes_and_sends_the_decrypted_key(owner: Api) -> None:
    before = len(fake_requests())
    r = owner.post("/assistant/settings/test", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["error_code"] is None
    assert body["checks"] == {"reachable": True, "auth": True, "model": True, "tool_calls": True}
    assert isinstance(body["latency_ms"], int) and body["latency_ms"] >= 0
    sent = fake_requests()[before:]
    assert sent, "the connection test never reached the fake model"
    assert sent[-1]["authorization"] == f"Bearer {FAKE_KEY}"
    assert sent[-1]["model"] == "fake-tools" and sent[-1]["tools"], "the test must offer one tool"


@story("M2S-E03-04")
@pytest.mark.parametrize(("change", "failed", "code"), [
    ({"api_key": "wrong-key"}, "auth", "auth_failed"),
    ({"model": "fake-no-tools"}, "tool_calls", "tool_calls_unsupported"),
    ({"model": "no-such-model"}, "model", "model_not_found"),
    ({"base_url": "http://127.0.0.1:9/v1"}, "reachable", "unreachable"),
])
def test_connection_test_names_the_failing_check(owner: Api, change: dict, failed: str, code: str) -> None:
    assert owner.patch("/assistant/settings", json={"chat": change}).status_code == 200
    try:
        r = owner.post("/assistant/settings/test", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False and body["error_code"] == code
        assert body["checks"][failed] is False
    finally:
        configure_fake(owner)
