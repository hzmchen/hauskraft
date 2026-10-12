# SPDX-License-Identifier: MIT
"""M0S-E10-01 · CloudEvents envelope and event data schemas."""

from __future__ import annotations

import pytest

from _support import FIXTURES
from _support.schemas import errors, load_json, validator

pytestmark = pytest.mark.story("M0S-E10-01")
ENVELOPE = "events/cloudevent.schema.json"

VALID = sorted((FIXTURES / "events" / "valid").glob("*.json"))
INVALID = sorted((FIXTURES / "events" / "invalid").glob("*.json"))


def _data_schema_story(path) -> list:
    """The theme_changed data schema is delivered by M0S-E13-04, the rest by M0S-E10-01."""
    return [pytest.mark.story("M0S-E13-04")] if "theme_changed" in path.name else []


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_envelope_passes(path) -> None:
    assert not errors(validator(ENVELOPE, "M0S-E10-01"), load_json(path))


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_envelope_fails(path) -> None:
    doc = load_json(path)
    assert errors(validator(ENVELOPE, "M0S-E10-01"), doc), doc.get("$comment")


@pytest.mark.parametrize("path", [pytest.param(p, marks=_data_schema_story(p), id=p.stem) for p in VALID])
def test_event_data_matches_its_schema(path) -> None:
    event = load_json(path)
    suffix = event["type"].removeprefix("hearthos.")
    v = validator(f"events/{suffix}.data.schema.json", "M0S-E10-01")
    assert not errors(v, event["data"])


@pytest.mark.parametrize("data_class", ["public", "household", "personal", "financial", "tenant", "child",
                                        "health", "secret"])
def test_every_data_class_is_allowed(data_class: str) -> None:
    event = load_json(FIXTURES / "events" / "valid" / "task.created.json")
    event["dataclass"] = data_class
    assert not errors(validator(ENVELOPE, "M0S-E10-01"), event)


def test_task_data_rejects_unknown_fields() -> None:
    event = load_json(FIXTURES / "events" / "valid" / "task.created.json")
    event["data"]["task"]["password"] = "leak"
    assert errors(validator("events/task.created.data.schema.json", "M0S-E10-01"), event["data"])
