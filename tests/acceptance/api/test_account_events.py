# SPDX-License-Identifier: MIT
"""Account events in the activity feed (spec §2.3, ADR 0018), black-box via GET /activity on the demo stack.

Each test is tagged with the story whose write emits the event (AGENTS.md rule 1: the write and its event ship
together).
"""

from __future__ import annotations

import json

import pytest

from _support.live import MEMBER_PASSWORD, TEMP_PASSWORD, Api, activity_types_for, wait_for_activity

pytestmark = pytest.mark.live
story = pytest.mark.story
FORBIDDEN_IN_DATA = ("password", "hash", "session", "csrf", "ip")


def _event(api: Api, user_id: str, event_type: str) -> dict:
    entry = wait_for_activity(api, f"user/{user_id}", event_type)
    assert entry, f"{event_type} for user/{user_id} never reached the activity feed"
    return entry


def _assert_clean(entry: dict, *secrets: str) -> None:
    raw = json.dumps(entry["data"]).lower()
    for key in FORBIDDEN_IN_DATA:
        assert f'"{key}' not in raw, f"event data must not carry {key!r}: {entry['data']}"
    for secret in secrets:
        assert secret.lower() not in raw


@story("M1S-E06-01")
def test_member_created_event(demo: Api, new_member) -> None:
    member = new_member()
    entry = _event(demo, member["id"], "hauskraft.user.created")
    assert entry["actor"]["display_name"] == "Demo Adult"
    assert entry["data"]["user"] == {k: member[k] for k in ("id", "username", "display_name", "role")}
    _assert_clean(entry, TEMP_PASSWORD)


@story("M1S-E06-02")
def test_member_updated_event_lists_changes(demo: Api, new_member) -> None:
    member = new_member()
    assert demo.patch(f"/users/{member['id']}", json={"display_name": "Event Rename"}).status_code == 200
    entry = _event(demo, member["id"], "hauskraft.user.updated")
    assert entry["data"]["changes"] == {"display_name": {"from": member["display_name"], "to": "Event Rename"}}


@story("M1S-E06-02")
def test_unchanged_member_patch_emits_nothing(demo: Api, new_member) -> None:
    member = new_member()
    assert demo.patch(f"/users/{member['id']}", json={"display_name": member["display_name"]}).status_code == 200
    _event(demo, member["id"], "hauskraft.user.created")
    assert "hauskraft.user.updated" not in activity_types_for(demo, f"user/{member['id']}")


@story("M1S-E06-03")
def test_deactivate_and_reactivate_events(demo: Api, new_member) -> None:
    member = new_member()
    assert demo.post(f"/users/{member['id']}/deactivate").status_code == 200
    assert demo.post(f"/users/{member['id']}/deactivate").status_code == 200  # no-op: no second event
    assert demo.post(f"/users/{member['id']}/reactivate").status_code == 200
    _event(demo, member["id"], "hauskraft.user.reactivated")
    types = activity_types_for(demo, f"user/{member['id']}")
    assert types.count("hauskraft.user.deactivated") == 1, types


@story("M1S-E06-04")
def test_password_reset_event_has_no_password(demo: Api, new_member) -> None:
    member = new_member()
    temporary = "event-temporary-pass-77"
    assert demo.post(f"/users/{member['id']}/password", json={"password": temporary}).status_code == 204
    _assert_clean(_event(demo, member["id"], "hauskraft.user.password_reset"), temporary, TEMP_PASSWORD)


@story("M1S-E05-01")
def test_own_password_change_event(ready_member) -> None:
    member, api = ready_member()
    entry = _event(api, member["id"], "hauskraft.user.password_changed")
    assert entry["actor"]["display_name"] == member["display_name"]
    _assert_clean(entry, TEMP_PASSWORD, MEMBER_PASSWORD)


@story("M1S-E05-01")
def test_display_name_change_emits_updated_but_language_does_not(ready_member) -> None:
    member, api = ready_member()
    assert api.patch("/me", json={"locale": "de"}).status_code == 200
    assert api.patch("/me", json={"locale": "en"}).status_code == 200
    assert api.patch("/me", json={"display_name": "Self Renamed"}).status_code == 200
    entry = _event(api, member["id"], "hauskraft.user.updated")
    assert entry["data"]["changes"] == {"display_name": {"from": member["display_name"], "to": "Self Renamed"}}
    assert activity_types_for(api, f"user/{member['id']}").count("hauskraft.user.updated") == 1


@story("M1S-E05-02")
def test_session_bookkeeping_emits_nothing(ready_member) -> None:
    member, api = ready_member()
    before = activity_types_for(api, f"user/{member['id']}")
    extra = Api()
    try:
        assert extra.login(member["username"], member["password"]).status_code == 200
        assert extra.post("/auth/logout").status_code == 204
    finally:
        extra.close()
    assert activity_types_for(api, f"user/{member['id']}") == before
