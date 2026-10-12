# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-03: problem+json errors, request ids and JSON access logs."""

import json
import logging

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from hearthos_core.app import create_app
from hearthos_core.logging import request_user_id
from hearthos_core.settings import Settings
from hearthos_sdk.errors import ConflictError, NotFoundError

pytestmark = pytest.mark.unit
PROBLEM = "application/problem+json"


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str


def _app() -> FastAPI:
    app = create_app(Settings(env="test", relay_enabled=False, plugin_paths=[], theme_paths=[]))
    probe = APIRouter(prefix="/api/v1/_probe", tags=["probe"])

    @probe.post("/validate")
    async def validate(body: Body) -> dict[str, str]:
        return {"title": body.title}

    @probe.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Task not found")

    @probe.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("version_conflict", "The task changed meanwhile.", extra={"current_version": 3})

    @probe.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    @probe.get("/user")
    async def user() -> dict[str, bool]:
        request_user_id.set("0199f390-1111-7aaa-8bbb-cccccccccccc")
        return {"ok": True}

    app.include_router(probe)
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


def _problem(r, status: int, code: str) -> dict:  # type: ignore[no-untyped-def]
    assert r.status_code == status
    assert r.headers["content-type"].startswith(PROBLEM)
    body = r.json()
    assert set(body) >= {"type", "title", "status", "detail", "code", "request_id"}
    assert body["status"] == status
    assert body["code"] == code
    assert body["request_id"] == r.headers["x-request-id"]
    return body


def test_unknown_route(client: TestClient) -> None:
    body = _problem(client.get("/api/v1/nope", headers={"X-Request-ID": "req-1"}), 404, "not_found")
    assert body["request_id"] == "req-1"
    assert body["type"] == "https://hearthos.dev/problems/not_found"


def test_method_not_allowed(client: TestClient) -> None:
    _problem(client.delete("/api/v1/_probe/user"), 405, "method_not_allowed")


def test_validation_errors_list_every_field(client: TestClient) -> None:
    body = _problem(client.post("/api/v1/_probe/validate", json={"title": 1, "extra": True}), 422, "validation_failed")
    locs = {tuple(e["loc"]) for e in body["errors"]}
    assert ("body", "title") in locs
    assert ("body", "extra") in locs
    assert all({"loc", "msg", "type"} <= set(e) for e in body["errors"])


def test_hearthos_errors_keep_their_code_and_extras(client: TestClient) -> None:
    _problem(client.get("/api/v1/_probe/missing"), 404, "not_found")
    body = _problem(client.get("/api/v1/_probe/conflict"), 409, "version_conflict")
    assert body["current_version"] == 3


def test_unexpected_errors_hide_internals(client: TestClient) -> None:
    body = _problem(client.get("/api/v1/_probe/boom"), 500, "internal_error")
    assert "secret internals" not in json.dumps(body)


def test_request_id_generated_or_echoed(client: TestClient) -> None:
    generated = client.get("/api/v1/nope").headers["x-request-id"]
    assert len(generated) >= 16
    assert client.get("/api/v1/nope", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"
    unsafe = client.get("/api/v1/nope", headers={"X-Request-ID": "bad id\n<script>"}).headers["x-request-id"]
    assert unsafe != "bad id\n<script>", "untrusted ids are replaced"


def test_access_log_is_one_json_line(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="hearthos.access")
    client.get("/api/v1/_probe/user", headers={"X-Request-ID": "log-1"})
    # structlog hands the event dict to the stdlib record; the JSON renderer turns it into one line.
    lines = [r.msg for r in caplog.records if r.name == "hearthos.access" and isinstance(r.msg, dict)]
    assert lines, "no access log line"
    line = lines[-1]
    assert line["event"] == "http.request"
    assert line["request_id"] == "log-1"
    assert line["method"] == "GET"
    assert line["path"] == "/api/v1/_probe/user"
    assert line["status"] == 200
    assert isinstance(line["duration_ms"], (int, float))
    assert line["user_id"] == "0199f390-1111-7aaa-8bbb-cccccccccccc"
