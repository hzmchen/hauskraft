# SPDX-License-Identifier: MIT
"""M1S-E09-01 · Account and household event data schemas (spec §2.3, ADR 0018).

Fixtures live in tests/fixtures/events/accounts/. Every envelope there is valid; the invalid fixtures break only their
data schema, for the reason given in expected.json.
"""

from __future__ import annotations

import pytest

from _support import FIXTURES
from _support.schemas import errors, load_json, validator

pytestmark = pytest.mark.story("M1S-E09-01")
STORY = "M1S-E09-01"
ENVELOPE = "events/cloudevent.schema.json"
ROOT = FIXTURES / "events" / "accounts"
VALID = sorted((ROOT / "valid").glob("*.json"))
INVALID = sorted((ROOT / "invalid").glob("*.json"))
TYPES = ["user.created", "user.updated", "user.deactivated", "user.reactivated", "user.password_reset",
         "user.password_changed", "settings.household_changed"]


def _data_validator(event: dict):
    return validator(f"events/{event['type'].removeprefix('hauskraft.')}.data.schema.json", STORY)


@pytest.mark.parametrize("suffix", TYPES)
def test_schema_exists_with_stable_id(suffix: str) -> None:
    v = validator(f"events/{suffix}.data.schema.json", STORY)
    assert v.schema["$id"] == f"https://hauskraft.dev/schema/events/{suffix}/v1.json"
    assert v.schema.get("additionalProperties") is False
    assert "SPDX-License-Identifier: MIT" in v.schema.get("$comment", "")


def test_every_type_has_a_valid_fixture() -> None:
    covered = {load_json(p)["type"].removeprefix("hauskraft.") for p in VALID}
    assert covered == set(TYPES)


@pytest.mark.parametrize("path", [*VALID, *INVALID], ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_fixture_envelopes_are_valid(path) -> None:
    assert not errors(validator(ENVELOPE, STORY), load_json(path))


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_data_passes(path) -> None:
    event = load_json(path)
    assert not errors(_data_validator(event), event["data"])


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_data_fails(path) -> None:
    event = load_json(path)
    why = load_json(ROOT / "expected.json")["invalid"][path.name]
    assert errors(_data_validator(event), event["data"]), f"should fail: {why}"


def test_expected_index_matches_invalid_fixtures() -> None:
    assert set(load_json(ROOT / "expected.json")["invalid"]) == {p.name for p in INVALID}


@pytest.mark.parametrize("suffix", [t for t in TYPES if t.startswith("user.")])
def test_user_events_reject_secret_fields_anywhere(suffix: str) -> None:
    event = load_json(ROOT / "valid" / f"{suffix}.json")
    v = _data_validator(event)
    for key in ("password", "password_hash", "session_id", "ip", "csrf_token"):
        data = {**event["data"], key: "x"}
        assert errors(v, data), f"{suffix}: top-level {key!r} must be rejected"
        user = {**event["data"]["user"], key: "x"}
        assert errors(v, {**event["data"], "user": user}), f"{suffix}: user.{key} must be rejected"


def test_envelope_schema_is_unchanged() -> None:
    """The account events reuse the M0* envelope; the fixtures' type pattern already fits it."""
    schema = validator(ENVELOPE, STORY).schema
    assert schema["required"] == ["specversion", "id", "source", "type", "dataclass"]
