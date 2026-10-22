# SPDX-License-Identifier: MIT
"""M1S-E03-01 first-run setup (ADR 0017) and the last-owner rule (M1S-E06-02/03).

The ``fresh`` tests need the unseeded stack (HAUSKRAFT_FRESH_BASE_URL, M1S-E01-01). The module resets it once, sets
it up in the first test and runs the rest in order on that household, whose only owner is known.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from _support.live import (
    FRESH_BASE_URL, MEMBER_PASSWORD, TEMP_PASSWORD, Api, assert_problem, reset_fresh_stack, sign_in,
    wait_for_activity,
)

pytestmark = pytest.mark.live
story = pytest.mark.story
fresh = pytest.mark.fresh

OWNER = {"username": "mia", "display_name": "Mia", "password": "mia-household-pass-2026"}
HOUSEHOLD = {"name": "Familie Müller", "timezone": "Europe/Berlin", "locale": "de"}


def _setup_body(**owner) -> dict:
    return {"household": dict(HOUSEHOLD), "owner": {**OWNER, **owner}}


# ---------------------------------------------------------------- demo stack: setup is closed
@story("M1S-E03-01")
def test_setup_is_not_required_on_a_seeded_stack(anon: Api) -> None:
    r = anon.get("/setup")
    assert r.status_code == 200 and r.json() == {"required": False}


@story("M1S-E03-01")
def test_setup_cannot_run_again_on_a_seeded_stack(anon: Api) -> None:
    body = _setup_body(username="intruder" + uuid.uuid4().hex[:6])
    assert_problem(anon.post("/setup", json=body), 409, "setup_done")
    assert anon.login(body["owner"]["username"], body["owner"]["password"]).status_code == 401


# ---------------------------------------------------------------- fresh stack
@pytest.fixture(scope="module")
def fresh_household() -> dict:
    """Reset the fresh stack, then remember what the tests below create on it."""
    reset_fresh_stack()
    return {}


@fresh
@story("M1S-E03-01", "M1S-E01-01")
def test_fresh_stack_requires_setup(fresh_household: dict) -> None:
    r = httpx.get(f"{FRESH_BASE_URL}/api/v1/setup", timeout=5)
    assert r.status_code == 200 and r.json() == {"required": True}
    anon = Api(base_url=FRESH_BASE_URL)
    try:
        assert anon.login("demo").status_code == 401, "no demo users on the fresh stack"
    finally:
        anon.close()


@fresh
@story("M1S-E03-01")
@pytest.mark.parametrize(("change", "code"), [
    ({"household": {**HOUSEHOLD, "timezone": "Mars/Olympus_Mons"}}, "invalid_timezone"),
    ({"owner": {**OWNER, "password": "short"}}, "password_policy"),
    ({"owner": {**OWNER, "username": "No Spaces Allowed"}}, "invalid_username"),
    ({"household": {**HOUSEHOLD, "name": "  "}}, None),
    ({"household": {**HOUSEHOLD, "locale": "fr"}}, None),
])
def test_invalid_setup_stores_nothing(fresh_household: dict, change: dict, code: str | None) -> None:
    anon = Api(base_url=FRESH_BASE_URL)
    try:
        assert_problem(anon.post("/setup", json={**_setup_body(), **change}), 422, code)
        assert anon.get("/setup").json() == {"required": True}
    finally:
        anon.close()


@fresh
@story("M1S-E03-01")
def test_setup_from_a_foreign_origin_is_rejected(fresh_household: dict) -> None:
    evil = Api(base_url=FRESH_BASE_URL, origin="http://evil.example")
    try:
        assert_problem(evil.post("/setup", json=_setup_body()), 403, "csrf_failed")
    finally:
        evil.close()


@fresh
@story("M1S-E03-01")
def test_concurrent_setup_has_exactly_one_winner(fresh_household: dict) -> None:
    def attempt(i: int) -> tuple[int, httpx.Response]:
        api = Api(base_url=FRESH_BASE_URL)
        try:
            return i, api.post("/setup", json=_setup_body(username=f"{OWNER['username']}{i}" if i else "mia"))
        finally:
            api.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(attempt, range(5)))
    statuses = sorted(r.status_code for _, r in results)
    assert statuses == [201, 409, 409, 409, 409], statuses
    winner_index, winner = next((i, r) for i, r in results if r.status_code == 201)
    for _, r in results:
        if r.status_code == 409:
            assert_problem(r, 409, "setup_done")
    session = winner.json()
    assert session["user"]["role"] == "owner" and session["user"]["must_change_password"] is False
    assert {"settings.household.set", "user.create"} <= set(session["permissions"])
    assert winner.headers.get("set-cookie", "").startswith("hauskraft_session=")
    fresh_household["owner_username"] = session["user"]["username"]
    fresh_household["owner_id"] = session["user"]["id"]


@fresh
@story("M1S-E03-01")
def test_setup_stored_the_household_and_signed_in_the_owner(fresh_household: dict) -> None:
    assert "owner_username" in fresh_household, "setup did not succeed in the previous test"
    owner = sign_in(fresh_household["owner_username"], OWNER["password"], base_url=FRESH_BASE_URL)
    try:
        assert owner.get("/household").json() == HOUSEHOLD
        me = owner.get("/me").json()
        assert me["locale"] == "de", "the owner gets the household language"
        assert me["display_name"] == "Mia"
        assert owner.get("/setup").json() == {"required": False}
        assert_problem(owner.post("/setup", json=_setup_body(username="second")), 409, "setup_done")
        entry = wait_for_activity(owner, f"user/{fresh_household['owner_id']}", "hauskraft.user.created")
        assert entry, "setup emits hauskraft.user.created"
        assert entry["actor"]["display_name"] == "Mia"
    finally:
        owner.close()


# ---------------------------------------------------------------- last owner (fresh stack: one owner)
@pytest.fixture
def owner_api(fresh_household: dict):
    if "owner_username" not in fresh_household:
        pytest.fail("setup did not succeed earlier in this module", pytrace=False)
    api = sign_in(fresh_household["owner_username"], OWNER["password"], base_url=FRESH_BASE_URL)
    yield api
    api.close()


@fresh
@story("M1S-E06-02")
def test_last_owner_cannot_demote_themself(owner_api: Api, fresh_household: dict) -> None:
    r = owner_api.patch(f"/users/{fresh_household['owner_id']}", json={"role": "adult"})
    assert_problem(r, 409, "last_owner")
    assert owner_api.get("/me").json()["role"] == "owner"


@fresh
@story("M1S-E06-03")
def test_last_owner_cannot_deactivate_themself(owner_api: Api, fresh_household: dict) -> None:
    assert_problem(owner_api.post(f"/users/{fresh_household['owner_id']}/deactivate"), 409, "last_owner")
    assert owner_api.get("/me").status_code == 200


@fresh
@story("M1S-E06-03")
def test_with_a_second_owner_the_first_can_step_down(owner_api: Api, fresh_household: dict) -> None:
    body = {"username": "jonas", "display_name": "Jonas", "password": TEMP_PASSWORD, "role": "owner"}
    r = owner_api.post("/users", json=body)
    assert r.status_code == 201, r.text
    jonas = sign_in("jonas", TEMP_PASSWORD, base_url=FRESH_BASE_URL)
    try:
        assert jonas.post("/me/password", json={"current_password": TEMP_PASSWORD,
                                                "new_password": MEMBER_PASSWORD}).status_code == 204
        r = jonas.patch(f"/users/{fresh_household['owner_id']}", json={"role": "adult"})
        assert r.status_code == 200 and r.json()["role"] == "adult"
        assert_problem(jonas.patch(f"/users/{jonas.get('/me').json()['id']}", json={"role": "adult"}), 409,
                       "last_owner")
        # Restore: Mia is owner again, so later runs see the same household.
        assert jonas.patch(f"/users/{fresh_household['owner_id']}", json={"role": "owner"}).status_code == 200
    finally:
        jonas.close()
