# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E06-04: plugin records are upserted at startup; /plugins lists them; code plugins toggle after restart."""

import json
import sys
import textwrap
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from hearthos_core.app import create_app
from hearthos_core.db.models import OutboxEvent, PluginRecord
from hearthos_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

CODE = '''
from fastapi import APIRouter
from hearthos_sdk import PluginRegistration

class _P:
    id = "{pid}"
    def register(self, ctx):
        r = APIRouter()
        @r.get("/ping")
        async def ping() -> dict:
            return {{"ok": True}}
        return PluginRegistration(router=r)

plugin = _P()
'''


def _manifest(pid: str, **extra: object) -> dict[str, object]:
    return {"id": pid, "name": "Probe", "version": "0.2.0", "type": ["domain", "widget"], "hearthos_api": "^0.1.0",
            "license": "MIT", "authors": [{"name": "t"}], "source": "x", "capabilities": [],
            "data_classes": {"reads": [], "writes": [], "emits": []},
            "contributes": {"widgets": [{"id": "probe.w", "title": "W", "component": "W"}],
                            "pages": [{"id": "probe", "title": "P", "component": "P"}]}, **extra}


@pytest.fixture
def paths(tmp_path: Path) -> Iterator[tuple[str, str, Settings]]:
    pid = f"org.example.r{uuid.uuid4().hex[:6]}"
    module = pid.replace(".", "_")
    (tmp_path / "py").mkdir()
    (tmp_path / "py" / f"{module}.py").write_text(textwrap.dedent(CODE.format(pid=pid)))
    sys.path.insert(0, str(tmp_path / "py"))
    plugin = tmp_path / "plugins" / "probe"
    plugin.mkdir(parents=True)
    (plugin / "hearthos.plugin.json").write_text(json.dumps(_manifest(
        pid, runtime={"kind": "inprocess", "entrypoint": f"{module}:plugin", "api_prefix": f"/{module}"}))))
    theme_id = f"org.example.theme.t{uuid.uuid4().hex[:6]}"
    theme = tmp_path / "themes" / "t"
    theme.mkdir(parents=True)
    (theme / "hearthos.plugin.json").write_text(json.dumps(_manifest(
        theme_id, type=["theme"], runtime={"kind": "declarative"},
        contributes={"themes": [{"id": "t", "file": "theme.json"}]})))
    yield pid, theme_id, Settings(plugin_paths=[tmp_path / "plugins"], theme_paths=[tmp_path / "themes"])
    sys.path.remove(str(tmp_path / "py"))
    sys.modules.pop(module, None)


def _client(api_settings: Settings, extra: Settings) -> TestClient:
    settings = api_settings.model_copy(update={"plugin_paths": extra.plugin_paths, "theme_paths": extra.theme_paths})
    return TestClient(create_app(settings), headers={"Origin": "http://testserver"})


def _record(url: str, pid: str) -> PluginRecord:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return conn.execute(select(PluginRecord).where(PluginRecord.id == pid)).one()  # type: ignore[return-value]
    finally:
        engine.dispose()


def test_records_upserted_and_listed(api_settings: Settings, make_user: Callable[..., str],
                                     paths: tuple[str, str, Settings]) -> None:
    pid, theme_id, extra = paths
    with _client(api_settings, extra) as client:
        assert client.get("/api/v1/plugins").status_code == 401
        client.post("/api/v1/auth/login", json={"username": make_user(), "password": PASSWORD})
        items = {p["id"]: p for p in client.get("/api/v1/plugins").json()}
    probe = items[pid]
    assert probe == {"id": pid, "name": "Probe", "version": "0.2.0", "kind": "inprocess",
                     "type": ["domain", "widget"], "enabled": True, "load_error": None,
                     "contributes": probe["contributes"]}
    assert [w["id"] for w in probe["contributes"]["widgets"]] == ["probe.w"]
    assert items[theme_id]["kind"] == "declarative"
    assert items[theme_id]["type"] == ["theme"]
    record = _record(api_settings.database_url, pid)
    assert record.manifest_sha256 and len(record.manifest_sha256) == 64
    assert record.loaded_at is not None


def test_toggle_takes_effect_after_restart_and_emits(api_settings: Settings, make_user: Callable[..., str],
                                                      paths: tuple[str, str, Settings]) -> None:
    pid, theme_id, extra = paths
    module = pid.replace(".", "_")
    username = make_user()
    with _client(api_settings, extra) as client:
        csrf = {"X-CSRF-Token": client.post("/api/v1/auth/login",
                                             json={"username": username, "password": PASSWORD}).json()["csrf_token"]}
        r = client.patch(f"/api/v1/plugins/{pid}", json={"enabled": False}, headers=csrf)
        assert r.status_code == 200, r.text
        assert r.json()["restart_required"] is True
        assert r.json()["enabled"] is False
        assert client.get(f"/api/v1/{module}/ping").status_code == 200, "still active until restart"
        theme = client.patch(f"/api/v1/plugins/{theme_id}", json={"enabled": False}, headers=csrf)
        assert theme.status_code == 422
        assert theme.json()["code"] == "use_theme_settings"
        assert client.patch("/api/v1/plugins/org.example.nope", json={"enabled": True},
                            headers=csrf).status_code == 404
    with _client(api_settings, extra) as restarted:
        assert restarted.get(f"/api/v1/{module}/ping").status_code == 404
        restarted.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        assert {p["id"]: p for p in restarted.get("/api/v1/plugins").json()}[pid]["enabled"] is False
    engine = create_engine(api_settings.database_url)
    with engine.connect() as conn:
        events = conn.execute(select(OutboxEvent).where(OutboxEvent.subject == f"plugin/{pid}")).scalars().all()
    engine.dispose()
    assert [e.envelope["data"] for e in events] == [{"plugin_id": pid, "enabled": False}]
