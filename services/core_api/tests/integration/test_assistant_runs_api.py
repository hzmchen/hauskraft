# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E04-02, -04, -05, -06, -07 and M2S-E08-01: chat runs against the fake model (run in-process)."""

import importlib.util
import threading
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import AssistantUsage, DeploymentSetting, OutboxEvent
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[4]
API = "/api/v1/assistant"


@pytest.fixture(scope="module")
def fake() -> Iterator[tuple[str, Any]]:
    spec = importlib.util.spec_from_file_location(
        "fake_llm_runs", REPO / "tests" / "fixtures" / "fake-llm" / "server.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1", module
    server.shutdown()


def _db(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


@pytest.fixture
def client(
    api_settings: Settings, make_user: Callable[..., str], fake: tuple[str, Any]
) -> Iterator[Callable[..., TestClient]]:
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))
    opened: list[TestClient] = []

    def _open(role: str = "owner", model: str = "fake-tools", key: str = "sk-run-tests") -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": make_user(role=role), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        if role == "owner":
            body = {"chat": {"base_url": fake[0], "model": model, "api_key": key}, "tools_disabled": []}
            assert c.patch(f"{API}/settings", json=body).status_code == 200
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def say(c: TestClient, text: str, conversation: str | None = None) -> dict[str, Any]:
    cid = conversation or c.post(f"{API}/conversations").json()["id"]
    r = c.post(f"{API}/conversations/{cid}/messages", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def task(c: TestClient, title: str) -> dict[str, Any] | None:
    items = c.get("/api/v1/tasks", params={"status": "all", "limit": 100}).json()["items"]
    return next((t for t in items if t["title"] == title), None)


def title(label: str) -> str:
    return f"it-{uuid.uuid4().hex[:6]} {label}"


def test_chat_creates_a_task_as_the_person(client: Callable[..., TestClient], api_settings: Settings) -> None:
    c = client()
    name = title("Buy milk")
    result = say(c, f"Add '{name}', due tomorrow")
    assert result["run"]["status"] == "done"
    created = task(c, name)
    assert created is not None
    assert created["due_on"] is not None
    [action] = result["actions"]
    assert action["summary_key"] == "tasks:tool.create.done"
    assert action["record"]["label"] == name
    assert action["undo_available"] is True
    [(envelope,)] = _db(
        api_settings, select(OutboxEvent.envelope).where(OutboxEvent.subject == f"task/{created['id']}")
    )
    assert envelope["agentrunid"] == result["run"]["id"]
    assert envelope["actorid"] == created["created_by"]["id"]


def test_delete_waits_then_deny_and_approve(client: Callable[..., TestClient]) -> None:
    c = client()
    name = title("Delete me")
    c.post("/api/v1/tasks", json={"title": name})
    waiting = say(c, f"Delete '{name}'")
    assert waiting["run"]["status"] == "awaiting_confirmation"
    [confirmation] = waiting["confirmations"]
    assert confirmation["summary_key"] == "tasks:tool.delete.confirm"
    assert confirmation["record"]["label"] == name
    run = waiting["run"]["id"]
    denied = c.post(
        f"{API}/runs/{run}/confirmations", json={"decisions": [{"id": confirmation["id"], "approve": False}]}
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["messages"][-1]["text"] == f"I did not delete '{name}'."
    assert [a["status"] for a in denied.json()["actions"]] == ["denied"]
    assert task(c, name) is not None
    again = c.post(
        f"{API}/runs/{run}/confirmations", json={"decisions": [{"id": confirmation["id"], "approve": False}]}
    )
    assert again.status_code == 409
    waiting = say(c, f"Delete '{name}'")
    [confirmation] = waiting["confirmations"]
    approved = c.post(
        f"{API}/runs/{waiting['run']['id']}/confirmations",
        json={"decisions": [{"id": confirmation["id"], "approve": True}]},
    ).json()
    assert approved["messages"][-1]["text"] == f"Deleted '{name}'."
    assert task(c, name) is None


def test_undo_reverses_a_create(client: Callable[..., TestClient]) -> None:
    c = client()
    name = title("Undo me")
    [action] = say(c, f"Add '{name}'")["actions"]
    r = c.post(f"{API}/actions/{action['id']}/undo")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "undone"
    assert task(c, name) is None
    assert c.post(f"{API}/actions/{action['id']}/undo").status_code == 409


@pytest.mark.parametrize(
    ("model", "key", "code"),
    [
        ("fake-broken", "sk-run-tests", "model_unavailable"),
        ("fake-tools", "wrong-key", "auth_failed"),
        ("fake-loop", "sk-run-tests", "run_limit"),
    ],
)
def test_failures_end_the_run_cleanly(client: Callable[..., TestClient], model: str, key: str, code: str) -> None:
    result = say(client(model=model, key=key), "Hello!")
    assert result["run"]["status"] == "failed"
    assert result["run"]["error_code"] == code


def test_tool_errors_reach_the_model(client: Callable[..., TestClient]) -> None:
    result = say(client(), f"Complete the task with id {uuid.uuid4()}")
    assert result["messages"][-1]["text"] == "That task doesn't exist."


def test_every_model_request_is_counted(client: Callable[..., TestClient], api_settings: Settings) -> None:
    c = client()
    [(before,)] = _db(api_settings, select(func.count()).select_from(AssistantUsage))
    say(c, "What is still open?")  # two model requests: tasks_list, then the answer
    [(after,)] = _db(api_settings, select(func.count()).select_from(AssistantUsage))
    assert after == before + 2


def test_prompt_contract_reaches_the_model(client: Callable[..., TestClient], fake: tuple[str, Any]) -> None:
    marker = title("prompt")
    say(client(), f"Hello! {marker}")
    record = next(r for r in fake[1]._records if marker in str(r["messages"]))
    system = record["messages"][0]["content"]
    assert system.rstrip().splitlines()[-1].startswith("Language: English")
    assert {"tasks_list", "tasks_create", "tasks_update", "tasks_delete"} <= set(record["tools"])
