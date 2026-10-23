# SPDX-License-Identifier: MIT
"""M1S-E02 roles and permissions (spec §2.3, ADR 0016), black-box against the demo stack.

Writes that an adult may not do are sent with values that change nothing (the active theme, an enabled plugin),
so a red implementation that still allows them can't break the shared demo household.
"""

from __future__ import annotations

import uuid

import pytest

from _support.live import Api, assert_problem, unique

pytestmark = pytest.mark.live
story = pytest.mark.story

OWNER_ONLY = {"settings.theme.set", "settings.household.set", "plugin.toggle", "user.create"}


# ---------------------------------------------------------------- M1S-E02-03 demo roles
@story("M1S-E02-03")
def test_demo_is_owner_and_alex_is_adult(demo: Api, alex: Api) -> None:
    assert demo.get("/me").json()["role"] == "owner"
    assert alex.get("/me").json()["role"] == "adult"


# ---------------------------------------------------------------- M1S-E02-01 RolePolicy
@story("M1S-E02-01")
def test_adult_cannot_set_the_household_theme(alex: Api, demo: Api) -> None:
    active = demo.get("/theme").json()["theme_id"]
    assert_problem(alex.put("/settings/theme", json={"theme_id": active}), 403, "policy_denied")
    assert demo.get("/theme").json()["theme_id"] == active


@story("M1S-E02-01")
def test_owner_can_set_the_household_theme(demo: Api) -> None:
    active = demo.get("/theme").json()["theme_id"]
    assert demo.put("/settings/theme", json={"theme_id": active}).status_code == 200


@story("M1S-E02-01")
def test_adult_cannot_toggle_plugins(alex: Api) -> None:
    assert_problem(alex.patch("/plugins/dev.hauskraft.tasks", json={"enabled": True}), 403, "policy_denied")


@story("M1S-E02-01", "M1S-E04-01")
def test_adult_cannot_change_household_settings(alex: Api, demo: Api) -> None:
    before = demo.get("/household")
    assert before.status_code == 200, "RED: GET /household is not available yet"
    r = alex.patch("/household", json={"name": unique("not allowed")})
    try:
        assert_problem(r, 403, "policy_denied")
        assert demo.get("/household").json() == before.json()
    finally:
        if r.status_code == 200:
            demo.patch("/household", json=before.json())


@story("M1S-E02-01")
def test_adult_still_writes_tasks_and_own_layout(alex: Api, make_task) -> None:
    task = make_task(unique("adult task"), api=alex)
    assert alex.patch(f"/tasks/{task['id']}", json={"done": True}).status_code == 200
    layout = alex.get("/dashboard/today").json()["layout"]
    assert alex.put("/dashboard/today", json={"layout": layout}).status_code == 200


# ---------------------------------------------------------------- M1S-E02-02 creating accounts
@story("M1S-E02-02")
def test_adult_cannot_create_accounts(alex: Api) -> None:
    body = {"username": "acc" + uuid.uuid4().hex[:8], "display_name": "Denied", "password": "correct-horse-battery"}
    assert_problem(alex.post("/users", json=body), 403, "policy_denied")


@story("M1S-E06-01")
def test_adult_cannot_list_members(alex: Api) -> None:
    assert_problem(alex.get("/users"), 403, "policy_denied")


# ---------------------------------------------------------------- M1S-E02-04 permissions in the session
@story("M1S-E02-04")
def test_owner_session_lists_owner_permissions(demo: Api) -> None:
    perms = demo.get("/auth/session").json().get("permissions")
    assert isinstance(perms, list), "RED: Session.permissions missing"
    assert OWNER_ONLY <= set(perms) and "task.create" in perms
    assert perms == sorted(perms)


@story("M1S-E02-04")
def test_adult_session_has_no_owner_permissions(alex: Api) -> None:
    perms = alex.get("/auth/session").json().get("permissions")
    assert isinstance(perms, list), "RED: Session.permissions missing"
    assert "task.create" in perms
    assert not OWNER_ONLY & set(perms)


@story("M1S-E02-04")
def test_login_returns_permissions(anon: Api) -> None:
    r = anon.login("demo")
    assert r.status_code == 200
    assert OWNER_ONLY <= set(r.json().get("permissions", []))
