# SPDX-License-Identifier: MIT
"""M0S-E10-01: the SDK's Pydantic event models agree with packages/schemas/events in both directions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from referencing import Registry, Resource

from hearthos_sdk.events import DATA_MODELS, CloudEvent

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[3]
SCHEMAS = REPO / "packages" / "schemas"
VALID = sorted((REPO / "tests" / "fixtures" / "events" / "valid").glob("*.json"))
INVALID = sorted((REPO / "tests" / "fixtures" / "events" / "invalid").glob("*.json"))


def _validator(rel: str) -> Draft202012Validator:
    resources = [
        (d["$id"], Resource.from_contents(d))
        for d in (json.loads(p.read_text()) for p in SCHEMAS.rglob("*.schema.json"))
    ]
    return Draft202012Validator(json.loads((SCHEMAS / rel).read_text()), registry=Registry().with_resources(resources))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_fixture_round_trips_through_the_models(path: Path) -> None:
    raw = _load(path)
    event = CloudEvent.model_validate(raw)
    data = DATA_MODELS[event.type].model_validate(raw["data"])
    dumped = event.model_dump(mode="json", exclude_none=True) | {"data": data.model_dump(mode="json")}
    assert not list(_validator("events/cloudevent.schema.json").iter_errors(dumped))
    suffix = event.type.removeprefix("hearthos.")
    assert not list(_validator(f"events/{suffix}.data.schema.json").iter_errors(dumped["data"]))


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_envelopes_are_rejected_by_the_model(path: Path) -> None:
    raw = {k: v for k, v in _load(path).items() if k != "$comment"}
    with pytest.raises(ValidationError):
        CloudEvent.model_validate(raw)


def test_every_data_schema_has_a_model() -> None:
    types = {
        "hearthos." + p.name.removesuffix(".data.schema.json") for p in (SCHEMAS / "events").glob("*.data.schema.json")
    }
    assert types == set(DATA_MODELS)


def test_task_snapshot_rejects_unknown_fields() -> None:
    raw = _load(next(p for p in VALID if p.stem == "task.created"))
    raw["data"]["task"]["password"] = "leak"
    with pytest.raises(ValidationError):
        DATA_MODELS["hearthos.task.created"].model_validate(raw["data"])
