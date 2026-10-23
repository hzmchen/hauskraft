# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E04-01: household settings validation and change detection (no I/O)."""

import pytest

from hauskraft_core.household.service import Household, InvalidTimezoneError, changes, check_timezone

pytestmark = pytest.mark.unit

BERLIN = Household(name="Familie Müller", timezone="Europe/Berlin", locale="de")


@pytest.mark.parametrize("name", ["Europe/Berlin", "Pacific/Kiritimati", "UTC", "America/Argentina/Buenos_Aires"])
def test_known_time_zones(name: str) -> None:
    check_timezone(name)


@pytest.mark.parametrize("name", ["", " ", "Mars/Olympus_Mons", "europe/berlin", "../../etc/passwd", "Europe/Berlin/"])
def test_unknown_time_zones(name: str) -> None:
    with pytest.raises(InvalidTimezoneError) as err:
        check_timezone(name)
    assert err.value.status == 422
    assert err.value.code == "invalid_timezone"


def test_changes_list_only_what_changed() -> None:
    after = Household(name="Familie Müller-Schmidt", timezone="Europe/Berlin", locale="en")
    assert changes(BERLIN, after) == {
        "name": {"from": "Familie Müller", "to": "Familie Müller-Schmidt"},
        "locale": {"from": "de", "to": "en"},
    }


def test_no_change_is_empty() -> None:
    assert changes(BERLIN, BERLIN) == {}
