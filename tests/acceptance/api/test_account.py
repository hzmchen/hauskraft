# SPDX-License-Identifier: MIT
"""M1S-E05 my account (password, sessions) and M1S-E07-01 forced password change, against the demo stack.

Every test works on throwaway members created by the demo owner; demo's and alex's passwords never change.
"""

from __future__ import annotations

import re

import pytest

from _support.live import MEMBER_PASSWORD, Api, assert_problem, sign_in

pytestmark = pytest.mark.live
story = pytest.mark.story
NEW_PASSWORD = "another-chosen-pass-9012"


def _session_ids(api: Api) -> list[dict]:
    r = api.get("/me/sessions")
    assert r.status_code == 200, f"RED: GET /me/sessions answered {r.status_code}"
    return r.json()


# ---------------------------------------------------------------- M1S-E05-01 change my password
@story("M1S-E05-01")
def test_change_password_keeps_this_session_and_ends_the_others(ready_member) -> None:
    member, api = ready_member()
    other = sign_in(member["username"], member["password"])
    try:
        r = api.post("/me/password", json={"current_password": member["password"], "new_password": NEW_PASSWORD})
        assert r.status_code == 204, r.text
        assert api.get("/me").status_code == 200, "the session that changed the password stays signed in"
        assert other.get("/me").status_code == 401, "other sessions end"
    finally:
        other.close()
    fresh = Api()
    try:
        assert fresh.login(member["username"], member["password"]).status_code == 401, "old password no longer works"
        assert fresh.login(member["username"], NEW_PASSWORD).status_code == 200
    finally:
        fresh.close()


@story("M1S-E05-01")
def test_wrong_current_password_is_rejected(ready_member) -> None:
    member, api = ready_member()
    r = api.post("/me/password", json={"current_password": "not-my-password-at-all", "new_password": NEW_PASSWORD})
    assert_problem(r, 422, "wrong_password")
    again = Api()
    try:
        assert again.login(member["username"], member["password"]).status_code == 200, "nothing changed"
    finally:
        again.close()


@story("M1S-E05-01")
def test_new_password_must_meet_the_policy(ready_member) -> None:
    member, api = ready_member()
    r = api.post("/me/password", json={"current_password": member["password"], "new_password": "short"})
    assert_problem(r, 422, "password_policy")


@story("M1S-E05-01")
def test_change_password_needs_csrf_token(ready_member) -> None:
    member, api = ready_member()
    r = api.http.post("/me/password", json={"current_password": member["password"], "new_password": NEW_PASSWORD})
    assert_problem(r, 403, "csrf_failed")


@story("M1S-E05-01")
def test_repeated_wrong_current_passwords_are_rate_limited(ready_member) -> None:
    _, api = ready_member()
    codes = [api.post("/me/password", json={"current_password": f"wrong-password-{i:04d}",
                                            "new_password": NEW_PASSWORD}).status_code for i in range(6)]
    assert codes[:5] == [422] * 5 and codes[5] == 429, codes


# ---------------------------------------------------------------- M1S-E05-02 my sessions
@story("M1S-E05-02")
def test_sessions_list_marks_the_current_one(ready_member) -> None:
    member, api = ready_member()
    other = sign_in(member["username"], member["password"])
    try:
        sessions = _session_ids(api)
        assert len(sessions) == 2, sessions
        assert [s["current"] for s in sessions].count(True) == 1
        for s in sessions:
            assert {"id", "device", "created_at", "last_seen_at", "current"} == set(s), s
            assert s["device"]
    finally:
        other.close()


@story("M1S-E05-02")
def test_sessions_list_leaks_no_secrets(ready_member) -> None:
    member, api = ready_member()
    raw = api.get("/me/sessions").text
    cookie = api.http.cookies.get("hauskraft_session") or ""
    assert cookie and cookie not in raw, "the session token must never be returned"
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", raw), "no IP addresses"
    assert not re.search(r"\b[0-9a-f]{64}\b", raw), "no token hashes"
    assert api.csrf not in raw


@story("M1S-E05-02")
def test_end_another_session(ready_member) -> None:
    member, api = ready_member()
    other = sign_in(member["username"], member["password"])
    try:
        target = next(s for s in _session_ids(api) if not s["current"])
        assert api.delete(f"/me/sessions/{target['id']}").status_code == 204
        assert other.get("/me").status_code == 401
        assert [s for s in _session_ids(api) if s["id"] == target["id"]] == []
    finally:
        other.close()


@story("M1S-E05-02")
def test_cannot_end_someone_elses_session(ready_member) -> None:
    _, api_a = ready_member()
    _, api_b = ready_member()
    theirs = next(s for s in _session_ids(api_b) if s["current"])
    assert_problem(api_a.delete(f"/me/sessions/{theirs['id']}"), 404)
    assert api_b.get("/me").status_code == 200
    assert_problem(api_a.delete("/me/sessions/does-not-exist"), 404)


@story("M1S-E05-02")
def test_sign_out_everywhere(ready_member) -> None:
    member, api = ready_member()
    other = sign_in(member["username"], member["password"])
    try:
        r = api.post("/auth/logout-everywhere")
        assert r.status_code == 204, r.text
        assert api.get("/auth/session").status_code == 401
        assert other.get("/auth/session").status_code == 401
    finally:
        other.close()


# ---------------------------------------------------------------- M1S-E07-01 forced password change
@story("M1S-E07-01")
def test_new_account_must_change_password_first(new_member) -> None:
    member = new_member()
    api = Api()
    try:
        r = api.login(member["username"], member["password"])
        assert r.status_code == 200
        assert r.json()["user"]["must_change_password"] is True
        assert_problem(api.get("/tasks"), 403, "password_change_required")
        assert_problem(api.post("/tasks", json={"title": "blocked"}), 403, "password_change_required")
        for path in ("/auth/session", "/me", "/household", "/theme"):
            assert api.get(path).status_code == 200, path
        r = api.post("/me/password", json={"current_password": member["password"], "new_password": MEMBER_PASSWORD})
        assert r.status_code == 204, r.text
        assert api.get("/me").json()["must_change_password"] is False
        assert api.get("/tasks").status_code == 200, "unlocked in the same session"
    finally:
        api.close()


@story("M1S-E07-01")
def test_seeded_accounts_need_no_password_change(demo: Api, alex: Api) -> None:
    assert demo.get("/me").json()["must_change_password"] is False
    assert alex.get("/me").json()["must_change_password"] is False
