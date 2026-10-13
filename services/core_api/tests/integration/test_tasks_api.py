# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E07-03: the tasks plugin's REST API, through the real app with the plugin loaded from plugins/official."""

import datetime as dt
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

FIELDS = {
    "id",
    "title",
    "done",
    "done_at",
    "due_on",
    "data_class",
    "version",
    "created_by",
    "updated_by",
    "created_at",
    "updated_at",
}


@pytest.fixture
def h(client: TestClient, make_user: Callable[..., str]) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": make_user("Demo Adult"), "password": PASSWORD})
    return {"X-CSRF-Token": r.json()["csrf_token"]}


def _new(client: TestClient, h: dict[str, str], title: str, due: str | None = None) -> dict:  # type: ignore[type-arg]
    body: dict[str, object] = {"title": title}
    if due:
        body["due_on"] = due
    r = client.post("/api/v1/tasks", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def test_create_get_patch_delete(client: TestClient, h: dict[str, str]) -> None:
    r = client.post("/api/v1/tasks", json={"title": "  Buy milk  "}, headers=h)
    assert r.status_code == 201
    task = r.json()
    assert set(task) == FIELDS
    assert task["title"] == "Buy milk"
    assert task["created_by"]["display_name"] == "Demo Adult"
    assert r.headers["location"].endswith(f"/api/v1/tasks/{task['id']}")
    assert client.get(f"/api/v1/tasks/{task['id']}").json()["id"] == task["id"]
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    patched = client.patch(
        f"/api/v1/tasks/{task['id']}", json={"title": "Buy oat milk", "due_on": tomorrow}, headers=h
    ).json()
    assert patched["version"] == 2
    assert patched["due_on"] == tomorrow
    assert (
        client.patch(f"/api/v1/tasks/{task['id']}", json={"title": "x", "version": 1}, headers=h).json()["code"]
        == "version_conflict"
    )
    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=h).status_code == 204
    missing = client.get(f"/api/v1/tasks/{task['id']}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {},
        {"title": "ok", "colour": "red"},
        {"title": "ok", "due_on": "13.10.2026"},
    ],
)
def test_create_validation(client: TestClient, h: dict[str, str], body: dict[str, object]) -> None:
    r = client.post("/api/v1/tasks", json=body, headers=h)
    assert r.status_code == 422
    assert r.json()["errors"]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 201}, {"offset": -1}, {"status": "maybe"}, {"sort": "title"}]
)
def test_list_parameter_validation(client: TestClient, h: dict[str, str], params: dict[str, object]) -> None:
    assert client.get("/api/v1/tasks", params=params).status_code == 422


def test_filter_sort_and_nulls_last(client: TestClient, h: dict[str, str]) -> None:
    tag = f"sort-{uuid.uuid4().hex[:6]}"
    today = dt.date.today()
    late = _new(client, h, f"{tag} late", (today + dt.timedelta(days=5)).isoformat())
    none = _new(client, h, f"{tag} none")
    soon = _new(client, h, f"{tag} soon", (today + dt.timedelta(days=1)).isoformat())
    done = _new(client, h, f"{tag} done")
    client.patch(f"/api/v1/tasks/{done['id']}", json={"done": True}, headers=h)

    def ids(**params: object) -> list[str]:
        items = client.get("/api/v1/tasks", params={**params, "limit": 200}).json()["items"]
        return [t["id"] for t in items if t["title"].startswith(tag)]

    assert ids(status="open", sort="due_on") == [soon["id"], late["id"], none["id"]]
    assert ids(status="done") == [done["id"]]
    assert ids() == [done["id"], soon["id"], none["id"], late["id"]]


def test_pagination_envelope(client: TestClient, h: dict[str, str]) -> None:
    for i in range(3):
        _new(client, h, f"page {i}")
    body = client.get("/api/v1/tasks", params={"limit": 2, "offset": 1}).json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
    assert body["total"] >= 3


def test_auth_and_csrf_are_enforced(client: TestClient, h: dict[str, str]) -> None:
    assert client.post("/api/v1/tasks", json={"title": "no csrf"}).json()["code"] == "csrf_failed"
    anon = TestClient(client.app)
    assert anon.get("/api/v1/tasks").status_code == 401


def test_openapi_operation_ids(client: TestClient) -> None:
    ops = {
        op["operationId"]: (path, method)
        for path, item in client.app.openapi()["paths"].items()  # type: ignore[attr-defined]
        for method, op in item.items()
    }
    for op_id in ("tasks_list", "tasks_create", "tasks_get", "tasks_update", "tasks_delete"):
        assert op_id in ops, op_id
        assert ops[op_id][0].startswith("/api/v1/tasks")
