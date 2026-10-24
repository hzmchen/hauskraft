# SPDX-License-Identifier: MIT
"""M2* endpoints and schemas in the committed OpenAPI 3.1 contract (docs/backlog/m2-star/, API tables per epic)."""

from __future__ import annotations

import re

import pytest

from _support.red import require_json

story = pytest.mark.story
OPENAPI = "packages/schemas/openapi/core-api.openapi.json"


def _doc(sid: str) -> dict:
    return require_json(OPENAPI, sid)


def _operations(sid: str) -> dict[tuple[str, str], dict]:
    ops = {}
    for path, item in _doc(sid).get("paths", {}).items():
        norm = re.sub(r"\{[^}]+\}", "{}", path.removeprefix("/api/v1"))
        for method, op in item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                ops[(method.upper(), norm)] = op
    return ops


ENDPOINTS = [
    ("M2S-E02-03", "GET", "/assistant/tools"),
    ("M2S-E03-02", "GET", "/assistant/status"), ("M2S-E03-02", "GET", "/assistant/settings"),
    ("M2S-E03-02", "PATCH", "/assistant/settings"), ("M2S-E03-02", "DELETE", "/assistant/settings/chat"),
    ("M2S-E03-04", "POST", "/assistant/settings/test"),
    ("M2S-E04-01", "GET", "/assistant/conversations"), ("M2S-E04-01", "POST", "/assistant/conversations"),
    ("M2S-E04-01", "GET", "/assistant/conversations/{}"), ("M2S-E04-01", "DELETE", "/assistant/conversations/{}"),
    ("M2S-E04-02", "POST", "/assistant/conversations/{}/messages"),
    ("M2S-E04-04", "POST", "/assistant/runs/{}/confirmations"),
    ("M2S-E04-06", "POST", "/assistant/actions/{}/undo"),
    ("M2S-E05-01", "GET", "/assistant/skills"),
    ("M2S-E05-02", "POST", "/assistant/skills/{}/runs"), ("M2S-E05-02", "GET", "/assistant/skills/{}/runs/latest"),
    ("M2S-E08-02", "GET", "/assistant/usage"),
]


@pytest.mark.parametrize(("sid", "method", "path"),
                         [pytest.param(*e, marks=story(e[0]), id=f"{e[1]} {e[2]}") for e in ENDPOINTS])
def test_endpoint_is_in_contract(sid: str, method: str, path: str) -> None:
    assert (method, path) in _operations(sid), f"{method} /api/v1{path} missing from {OPENAPI}"


def _props(sid: str, name: str) -> set[str]:
    schemas = _doc(sid).get("components", {}).get("schemas", {})
    hit = next((s for key, s in schemas.items() if key == name or key.endswith(name)), None)
    assert hit is not None, f"component schema {name!r} missing from {OPENAPI}"
    return set(hit.get("properties", {}))


@story("M2S-E03-02")
def test_settings_schema_never_carries_the_key() -> None:
    props = _props("M2S-E03-02", "AssistantChatSettings")
    assert {"base_url", "model", "api_key_set", "api_key_hint", "api_key_status", "locality",
            "max_data_class"} <= props
    assert "api_key" not in props


@story("M2S-E04-02")
def test_run_result_schema() -> None:
    assert {"run", "messages", "actions", "confirmations"} <= _props("M2S-E04-02", "RunResult")
    assert {"id", "kind", "status", "error_code", "channel"} <= _props("M2S-E04-02", "RunOut")


@story("M2S-E04-07")
def test_activity_items_carry_agentrunid() -> None:
    assert "agentrunid" in _props("M2S-E04-07", "ActivityItem")
