# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E09-01: evals fix "today" and swap in another model through ``app.state`` (the run itself stays real)."""

import datetime as dt
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import create_engine, delete

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration
API = "/api/v1/assistant"


@pytest.fixture
def owner(api_settings: Settings, make_user: Callable[..., str]) -> Iterator[TestClient]:
    engine = create_engine(api_settings.database_url)
    with engine.begin() as conn:
        conn.execute(delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))
    engine.dispose()
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as c:
        r = c.post("/api/v1/auth/login", json={"username": make_user(role="owner"), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        body = {"chat": {"base_url": "http://unused.invalid/v1", "model": "eval-model", "api_key": "sk-unused"}}
        assert c.patch(f"{API}/settings", json=body).status_code == 200
        yield c


def test_the_clock_and_the_model_come_from_app_state(owner: TestClient) -> None:
    seen: list[str] = []

    def reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info.instructions or "")
        return ModelResponse(parts=[TextPart("Hello from the function model")])

    owner.app.state.assistant_model = FunctionModel(reply)  # type: ignore[attr-defined]
    owner.app.state.assistant_clock = lambda: dt.datetime(2026, 11, 2, 9, 5, tzinfo=dt.UTC)  # type: ignore[attr-defined]
    cid = owner.post(f"{API}/conversations").json()["id"]
    r = owner.post(f"{API}/conversations/{cid}/messages", json={"text": f"Hi {uuid.uuid4().hex[:4]}"})
    assert r.status_code == 200, r.text
    assert r.json()["messages"][-1]["text"] == "Hello from the function model"
    assert "Today: 2026-11-02 (Monday)" in seen[0]
