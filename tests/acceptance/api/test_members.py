# SPDX-License-Identifier: MIT
"""M1S-E02-02 owner role and M1S-E06 members API (owner only), against the demo stack.

The demo owner manages throwaway members; the last-owner rule is tested on the fresh stack (test_first_run.py),
where the number of owners is known.
"""

from __future__ import annotations

import uuid

import pytest

from _support.live import MEMBER_PASSWORD, TEMP_PASSWORD, Api, assert_problem, sign_in

pytestmark = pytest.mark.live
story = pytest.mark.story
MEMBER_FIELDS = {"id", "username", "display_name", "role", "locale", "must_change_password", "is_active",
                 "created_at", "last_login_at"}
SECRET_KEYS = {"password", "password_hash", "hash", "session", "sessions", "ip"}


def _body(**overrides) -> dict:
    return {"username": "acc" + uuid.uuid4().hex[:8], "display_name": "Acceptance Member",
            "password": TEMP_PASSWORD, **overrides}


# ---------------------------------------------------------------- M1S-E02-02 owner role
@story("M1S-E02-02")
@pytest.mark.parametrize("role", ["owner", "adult"])
def test_owner_creates_owner_or_adult(demo: Api, new_member, role: str) -> None:
    member = new_member(role=role)
    assert member["role"] == role
    assert demo.get(f"/users/{member['id']}").json()["role"] == role


@story("M1S-E02-02")
def test_role_defaults_to_adult(new_member) -> None:
    assert new_member()["role"] == "adult"


@story("M1S-E02-02")
@pytest.mark.parametrize("role", ["teen", "kid", "caregiver", "property_manager", "tenant", "guest"])
def test_other_roles_are_not_enabled(demo: Api, role: str) -> None:
    assert_problem(demo.post("/users", json=_body(role=role)), 422, "role_not_enabled")


# ---------------------------------------------------------------- M1S-E06-01 list
@story("M1S-E06-01")
def test_members_list_includes_everyone_without_secrets(demo: Api, new_member) -> None:
    member = new_member()
    r = demo.get("/users")
    assert r.status_code == 200, r.text
    rows = r.json()
    by_name = {m["username"]: m for m in rows}
    assert {"demo", "alex", member["username"]} <= set(by_name)
    for row in rows:
        assert set(row) == MEMBER_FIELDS, row
        assert not SECRET_KEYS & set(row)
    keys = [(m["display_name"].casefold(), m["username"]) for m in rows]
    assert keys == sorted(keys), "ordered case-insensitively by display name, then username"


@story("M1S-E06-01")
def test_get_one_member(demo: Api, new_member) -> None:
    member = new_member()
    r = demo.get(f"/users/{member['id']}")
    assert r.status_code == 200 and r.json()["username"] == member["username"]
    assert r.json()["is_active"] is True and r.json()["last_login_at"] is None
    assert_problem(demo.get(f"/users/{uuid.uuid4()}"), 404, "not_found")


@story("M1S-E06-01")
def test_created_member_shape(demo: Api) -> None:
    body = _body()
    r = demo.post("/users", json=body)
    assert r.status_code == 201, r.text
    try:
        assert set(r.json()) == MEMBER_FIELDS
        assert r.json()["locale"] == demo.get("/household").json()["locale"], "locale defaults to the household's"
    finally:
        demo.post(f"/users/{r.json()['id']}/deactivate")


# ---------------------------------------------------------------- M1S-E07-01 new accounts start locked
@story("M1S-E07-01")
def test_created_member_must_change_password(new_member) -> None:
    assert new_member()["must_change_password"] is True


# ---------------------------------------------------------------- M1S-E06-02 edit
@story("M1S-E06-02")
def test_owner_renames_and_promotes_a_member(demo: Api, ready_member) -> None:
    member, api = ready_member()
    r = demo.patch(f"/users/{member['id']}", json={"display_name": "Renamed Member", "role": "owner"})
    assert r.status_code == 200, r.text
    assert r.json()["display_name"] == "Renamed Member" and r.json()["role"] == "owner"
    perms = api.get("/auth/session").json()["permissions"]
    assert "user.create" in perms, "a role change applies at the member's next request"
    r = demo.patch(f"/users/{member['id']}", json={"role": "adult"})
    assert r.status_code == 200 and r.json()["role"] == "adult"
    assert "user.create" not in api.get("/auth/session").json()["permissions"]


@story("M1S-E06-02")
def test_username_is_fixed(demo: Api, new_member) -> None:
    member = new_member()
    assert_problem(demo.patch(f"/users/{member['id']}", json={"username": "renamed"}), 422)


@story("M1S-E06-02")
def test_edit_rejects_disabled_roles_and_unknown_members(demo: Api, new_member) -> None:
    member = new_member()
    assert_problem(demo.patch(f"/users/{member['id']}", json={"role": "kid"}), 422, "role_not_enabled")
    assert_problem(demo.patch(f"/users/{uuid.uuid4()}", json={"display_name": "Nobody"}), 404)


@story("M1S-E06-02")
def test_adult_cannot_edit_members(alex: Api, new_member) -> None:
    member = new_member()
    assert_problem(alex.patch(f"/users/{member['id']}", json={"display_name": "Nope"}), 403, "policy_denied")


# ---------------------------------------------------------------- M1S-E06-03 deactivate / reactivate
@story("M1S-E06-03")
def test_deactivate_ends_sessions_and_blocks_sign_in(demo: Api, ready_member) -> None:
    member, api = ready_member()
    r = demo.post(f"/users/{member['id']}/deactivate")
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False
    assert api.get("/me").status_code == 401, "open sessions end at the next request"
    probe = Api()
    try:
        assert_problem(probe.login(member["username"], member["password"]), 403, "account_deactivated")
        assert_problem(probe.login(member["username"], "wrong-password-0000"), 401, "invalid_credentials")
    finally:
        probe.close()
    listed = {m["username"]: m for m in demo.get("/users").json()}
    assert listed[member["username"]]["is_active"] is False, "deactivated members stay in the list"


@story("M1S-E06-03")
def test_reactivate_allows_sign_in_again(demo: Api, ready_member) -> None:
    member, _ = ready_member()
    assert demo.post(f"/users/{member['id']}/deactivate").status_code == 200
    r = demo.post(f"/users/{member['id']}/reactivate")
    assert r.status_code == 200 and r.json()["is_active"] is True
    sign_in(member["username"], member["password"]).close()


@story("M1S-E06-03")
def test_repeated_deactivate_is_a_no_op(demo: Api, new_member) -> None:
    member = new_member()
    assert demo.post(f"/users/{member['id']}/deactivate").status_code == 200
    r = demo.post(f"/users/{member['id']}/deactivate")
    assert r.status_code == 200 and r.json()["is_active"] is False


@story("M1S-E06-03")
def test_adult_cannot_deactivate(alex: Api, new_member) -> None:
    member = new_member()
    assert_problem(alex.post(f"/users/{member['id']}/deactivate"), 403, "policy_denied")
    assert_problem(alex.post(f"/users/{member['id']}/reactivate"), 403, "policy_denied")


# ---------------------------------------------------------------- M1S-E06-04 reset password
@story("M1S-E06-04")
def test_reset_password_ends_sessions_and_forces_a_change(demo: Api, ready_member) -> None:
    member, api = ready_member()
    temporary = "reset-temporary-pass-42"
    r = demo.post(f"/users/{member['id']}/password", json={"password": temporary})
    assert r.status_code == 204, r.text
    assert api.get("/me").status_code == 401, "the member's sessions end"
    again = Api()
    try:
        assert again.login(member["username"], MEMBER_PASSWORD).status_code == 401
        r = again.login(member["username"], temporary)
        assert r.status_code == 200 and r.json()["user"]["must_change_password"] is True
        assert_problem(again.get("/tasks"), 403, "password_change_required")
    finally:
        again.close()


@story("M1S-E06-04")
def test_reset_rejects_own_account_and_short_passwords(demo: Api, new_member) -> None:
    me = demo.get("/me").json()
    assert_problem(demo.post(f"/users/{me['id']}/password", json={"password": TEMP_PASSWORD}), 422, "own_account")
    member = new_member()
    assert_problem(demo.post(f"/users/{member['id']}/password", json={"password": "short"}), 422, "password_policy")


@story("M1S-E06-04")
def test_adult_cannot_reset_passwords(alex: Api, new_member) -> None:
    member = new_member()
    r = alex.post(f"/users/{member['id']}/password", json={"password": TEMP_PASSWORD})
    assert_problem(r, 403, "policy_denied")
