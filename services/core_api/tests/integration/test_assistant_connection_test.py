# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E03-04: the connection test names the failing check (against the fake model, run in-process)."""

import importlib.util
import threading
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration
REPO = __import__("pathlib").Path(__file__).resolve().parents[4]
KEY = "sk-connection-test-1234"


@pytest.fixture(scope="module")
def fake_llm() -> Iterator[tuple[str, Any]]:
    spec = importlib.util.spec_from_file_location("fake_llm", REPO / "tests" / "fixtures" / "fake-llm" / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1", module
    server.shutdown()


@pytest.fixture
def owner(api_settings: Settings, make_user: Callable[..., str]) -> Iterator[TestClient]:
    engine = create_engine(api_settings.database_url)
    with engine.begin() as conn:
        conn.execute(delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))
    engine.dispose()
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as c:
        r = c.post("/api/v1/auth/login", json={"username": make_user(role="owner"), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        yield c


def configure(c: TestClient, **chat: str) -> None:
    assert c.patch("/api/v1/assistant/settings", json={"chat": chat}).status_code == 200


def test_not_configured_is_409(owner: TestClient) -> None:
    r = owner.post("/api/v1/assistant/settings/test")
    assert r.status_code == 409
    assert r.json()["code"] == "assistant_not_configured"


def test_passes_and_sends_the_key(owner: TestClient, fake_llm: tuple[str, Any]) -> None:
    url, module = fake_llm
    module._records.clear()
    configure(owner, base_url=url, model="fake-tools", api_key=KEY)
    body = owner.post("/api/v1/assistant/settings/test").json()
    assert body["ok"] is True
    assert body["checks"] == {"reachable": True, "auth": True, "model": True, "tool_calls": True}
    assert body["error_code"] is None
    assert module._records[-1]["authorization"] == f"Bearer {KEY}"
    assert module._records[-1]["tools"], "the test offers one tool"


@pytest.mark.parametrize(
    ("chat", "failed", "code"),
    [
        ({"model": "fake-tools", "api_key": "wrong-key"}, "auth", "auth_failed"),
        ({"model": "fake-no-tools", "api_key": KEY}, "tool_calls", "tool_calls_unsupported"),
        ({"model": "no-such-model", "api_key": KEY}, "model", "model_not_found"),
        ({"model": "fake-broken", "api_key": KEY}, "model", "model_error"),
    ],
)
def test_names_the_failing_check(
    owner: TestClient, fake_llm: tuple[str, Any], chat: dict, failed: str, code: str
) -> None:
    configure(owner, base_url=fake_llm[0], **chat)
    body = owner.post("/api/v1/assistant/settings/test").json()
    assert body["ok"] is False
    assert body["error_code"] == code
    assert body["checks"][failed] is False


def test_unreachable(owner: TestClient) -> None:
    configure(owner, base_url="http://127.0.0.1:9/v1", model="fake-tools", api_key=KEY)
    body = owner.post("/api/v1/assistant/settings/test").json()
    assert body["checks"]["reachable"] is False
    assert body["error_code"] == "unreachable"
