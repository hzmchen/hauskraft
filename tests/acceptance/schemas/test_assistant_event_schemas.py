# SPDX-License-Identifier: MIT
"""M2S-E03-02 · the `settings.assistant_changed` data schema; M2S-E04-07 · `agentrunid` in the envelope (ADR 0020).

Fixtures: tests/fixtures/events/assistant/. Every envelope there is valid; the invalid fixtures break only their data
schema, for the reason given in expected.json.
"""

from __future__ import annotations

import pytest

from _support import FIXTURES
from _support.schemas import errors, load_json, validator

story = pytest.mark.story
ENVELOPE = "events/cloudevent.schema.json"
ROOT = FIXTURES / "events" / "assistant"
CHANGED = "events/settings.assistant_changed.data.schema.json"
VALID_CHANGED = sorted((ROOT / "valid").glob("settings.assistant_changed*.json"))
INVALID = sorted((ROOT / "invalid").glob("*.json"))


@story("M2S-E03-02")
def test_schema_exists_with_stable_id() -> None:
    v = validator(CHANGED, "M2S-E03-02")
    assert v.schema["$id"] == "https://hauskraft.dev/schema/events/settings.assistant_changed/v1.json"
    assert v.schema.get("additionalProperties") is False
    assert "SPDX-License-Identifier: MIT" in v.schema.get("$comment", "")


@story("M2S-E03-02")
@pytest.mark.parametrize("path", VALID_CHANGED, ids=lambda p: p.stem)
def test_valid_data_passes(path) -> None:
    assert not errors(validator(CHANGED, "M2S-E03-02"), load_json(path)["data"])


@story("M2S-E03-02")
@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_data_fails(path) -> None:
    why = load_json(ROOT / "expected.json")["invalid"][path.name]
    assert errors(validator(CHANGED, "M2S-E03-02"), load_json(path)["data"]), f"should fail: {why}"


@story("M2S-E03-02")
def test_expected_index_matches_invalid_fixtures() -> None:
    assert set(load_json(ROOT / "expected.json")["invalid"]) == {p.name for p in INVALID}


@story("M2S-E04-07")
def test_envelope_documents_agentrunid() -> None:
    schema = validator(ENVELOPE, "M2S-E04-07").schema
    prop = schema["properties"].get("agentrunid")
    assert prop is not None, "RED: the envelope does not document agentrunid yet"
    assert prop.get("type") == "string"
    assert "agentrunid" not in schema["required"], "agentrunid is optional: manual changes have none"


@story("M2S-E04-07")
@pytest.mark.parametrize("path", sorted((ROOT / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_fixture_envelopes_are_valid(path) -> None:
    assert not errors(validator(ENVELOPE, "M2S-E04-07"), load_json(path))


@story("M2S-E04-07")
def test_task_event_via_assistant_keeps_its_data_schema() -> None:
    event = load_json(ROOT / "valid" / "task.created-via-assistant.json")
    assert not errors(validator("events/task.created.data.schema.json", "M2S-E04-07"), event["data"])
    assert event["agentrunid"] and event["actorid"], "the run and the person are both recorded"
