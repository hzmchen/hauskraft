# SPDX-License-Identifier: MIT
"""M1S-E04-01 household settings API and M1S-E03-03 demo household values, against the demo stack."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from _support.live import Api, activity_types_for, assert_problem, unique, wait_for_activity

pytestmark = pytest.mark.live
story = pytest.mark.story
CHANGED = "hauskraft.settings.household_changed"


@pytest.fixture
def household(demo: Api) -> Iterator[dict]:
    """The household settings before the test; restored afterwards."""
    r = demo.get("/household")
    assert r.status_code == 200, f"RED: GET /household answered {r.status_code}"
    before = r.json()
    yield before
    demo.patch("/household", json=before)


# ---------------------------------------------------------------- M1S-E03-03
@story("M1S-E03-03")
def test_demo_household_has_seeded_settings(demo: Api) -> None:
    r = demo.get("/household")
    assert r.status_code == 200
    assert r.json() == {"name": "Demo household", "timezone": "Europe/Berlin", "locale": "en"}


# ---------------------------------------------------------------- M1S-E04-01
@story("M1S-E04-01")
def test_any_member_reads_household(alex: Api) -> None:
    r = alex.get("/household")
    assert r.status_code == 200
    assert set(r.json()) == {"name", "timezone", "locale"}


@story("M1S-E04-01")
def test_household_needs_a_session(anon: Api) -> None:
    assert anon.get("/household").status_code == 401


@story("M1S-E04-01")
def test_owner_updates_household_and_one_event_lists_the_changes(demo: Api, household: dict) -> None:
    name = unique("Household")
    r = demo.patch("/household", json={"name": name, "timezone": "Europe/Vienna"})
    assert r.status_code == 200, r.text
    assert r.json() == {**household, "name": name, "timezone": "Europe/Vienna"}
    assert demo.get("/household").json()["name"] == name
    entry = wait_for_activity(demo, "setting/household", CHANGED)
    assert entry, "household_changed never reached the activity feed"
    changes = entry["data"]["changes"]
    assert changes["name"] == {"from": household["name"], "to": name}
    assert changes["timezone"] == {"from": household["timezone"], "to": "Europe/Vienna"}
    assert "locale" not in changes, "only changed fields are listed"


@story("M1S-E04-01")
def test_unchanged_patch_emits_nothing(demo: Api, household: dict) -> None:
    before = activity_types_for(demo, "setting/household").count(CHANGED)
    assert demo.patch("/household", json={"name": household["name"]}).status_code == 200
    assert activity_types_for(demo, "setting/household").count(CHANGED) == before


@story("M1S-E04-01")
@pytest.mark.parametrize("body", [{"timezone": "Mars/Olympus_Mons"}, {"timezone": ""}])
def test_unknown_time_zone_is_rejected(demo: Api, household: dict, body: dict) -> None:
    assert_problem(demo.patch("/household", json=body), 422, "invalid_timezone")
    assert demo.get("/household").json() == household


@story("M1S-E04-01")
@pytest.mark.parametrize("body", [{"name": "   "}, {"name": "x" * 81}, {"locale": "fr"}, {"colour": "red"}])
def test_invalid_household_values_are_rejected(demo: Api, household: dict, body: dict) -> None:
    assert_problem(demo.patch("/household", json=body), 422)
    assert demo.get("/household").json() == household
