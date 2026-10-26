# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E03-02 assistant settings API, and M2S-E03-03's raw-row check: the key is stored sealed (ADR 0021)."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

KEY = "sk-integration-test-key-wxyz"
CHAT = {"base_url": "http://fake-llm:8090/v1", "model": "fake-tools", "api_key": KEY}


def _db(settings: Settings, statement: Any) -> list[Any]:
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


@pytest.fixture
def clean(api_settings: Settings) -> Iterator[Settings]:
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))
    yield api_settings
    _db(api_settings, delete(DeploymentSetting).where(DeploymentSetting.key.like("assistant.%")))


@pytest.fixture
def signed_in(clean: Settings, make_user: Callable[..., str]) -> Iterator[Callable[..., TestClient]]:
    opened: list[TestClient] = []

    def _open(role: str, settings: Settings | None = None) -> TestClient:
        c = TestClient(create_app(settings or clean), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": make_user(role=role), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def _events(settings: Settings) -> list[dict[str, Any]]:
    rows = _db(
        settings,
        select(OutboxEvent.envelope)
        .where(OutboxEvent.subject == "setting/assistant")
        .order_by(OutboxEvent.time, OutboxEvent.id),
    )
    return [row[0] for row in rows]


def test_unset_settings_have_defaults(signed_in: Callable[..., TestClient]) -> None:
    body = signed_in("owner").get("/api/v1/assistant/settings").json()
    assert body["configured"] is False
    assert body["chat"]["api_key_set"] is False
    assert body["chat"]["api_key_status"] == "missing"
    assert body["chat"]["locality"] == "cloud"
    assert body["chat"]["max_data_class"] == "household"
    assert body["tools_disabled"] == []
    assert body["prices"] == {"input_per_million": None, "output_per_million": None, "currency": "EUR"}


def test_key_is_sealed_in_the_database_and_never_returned(
    signed_in: Callable[..., TestClient], clean: Settings
) -> None:
    r = signed_in("owner").patch("/api/v1/assistant/settings", json={"chat": CHAT})
    assert r.status_code == 200, r.text
    assert KEY not in r.text
    assert r.json()["chat"]["api_key_hint"] == "…wxyz"
    assert r.json()["configured"] is True
    [(stored,)] = _db(
        clean, select(DeploymentSetting.value).where(DeploymentSetting.key == "assistant.endpoints.chat.api_key")
    )
    assert isinstance(stored, str)
    assert stored.startswith("v1:")
    assert KEY not in stored


def test_one_event_lists_changed_fields_only(signed_in: Callable[..., TestClient], clean: Settings) -> None:
    owner = signed_in("owner")
    before = len(_events(clean))
    owner.patch("/api/v1/assistant/settings", json={"chat": CHAT})
    owner.patch("/api/v1/assistant/settings", json={"chat": {"model": "fake-tools"}})  # unchanged
    owner.patch("/api/v1/assistant/settings", json={"chat": {"temperature": 0.3}, "tools_disabled": ["tasks.delete"]})
    events = _events(clean)[before:]
    assert [e["data"]["changed"] for e in events] == [
        ["chat.api_key", "chat.base_url", "chat.model"],
        ["chat.temperature", "tools_disabled"],
    ]
    assert all(KEY not in str(e) for e in events)
    assert {e["dataclass"] for e in events} == {"household"}


def test_null_clears_optional_values(signed_in: Callable[..., TestClient]) -> None:
    owner = signed_in("owner")
    owner.patch("/api/v1/assistant/settings", json={"chat": {**CHAT, "temperature": 0.5}})
    body = owner.patch("/api/v1/assistant/settings", json={"chat": {"temperature": None}}).json()
    assert body["chat"]["temperature"] is None


def test_another_secret_needs_the_key_again(signed_in: Callable[..., TestClient], clean: Settings) -> None:
    signed_in("owner").patch("/api/v1/assistant/settings", json={"chat": CHAT})
    restarted = clean.model_copy(update={"secret_key": clean.secret_key.__class__("z" * 48)})  # type: ignore[union-attr]
    body = signed_in("owner", restarted).get("/api/v1/assistant/settings").json()
    assert body["chat"]["api_key_status"] == "needs_reentry"
    assert body["configured"] is False


def test_removing_the_endpoint(signed_in: Callable[..., TestClient], clean: Settings) -> None:
    owner = signed_in("owner")
    owner.patch("/api/v1/assistant/settings", json={"chat": CHAT})
    assert owner.delete("/api/v1/assistant/settings/chat").status_code == 204
    assert owner.get("/api/v1/assistant/settings").json()["configured"] is False
    assert _events(clean)[-1]["data"]["changed"] == ["chat"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"chat": {"base_url": "ftp://x/v1"}}, "invalid_base_url"),
        ({"chat": {"base_url": "relative/v1"}}, "invalid_base_url"),
        ({"tools_disabled": ["nodots"]}, "validation_failed"),
    ],
)
def test_invalid_values(signed_in: Callable[..., TestClient], body: dict, code: str) -> None:
    r = signed_in("owner").patch("/api/v1/assistant/settings", json=body)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == code, r.text


def test_adults_use_but_do_not_configure(signed_in: Callable[..., TestClient]) -> None:
    signed_in("owner").patch("/api/v1/assistant/settings", json={"chat": CHAT})
    adult = signed_in("adult")
    assert adult.get("/api/v1/assistant/status").json() == {"available": True}
    for method, path in [
        ("get", "/assistant/settings"),
        ("patch", "/assistant/settings"),
        ("delete", "/assistant/settings/chat"),
    ]:
        r = getattr(adult, method)(f"/api/v1{path}", **({"json": {}} if method == "patch" else {}))
        assert r.status_code == 403, (path, r.text)
        assert r.json()["code"] == "policy_denied", (path, r.text)
