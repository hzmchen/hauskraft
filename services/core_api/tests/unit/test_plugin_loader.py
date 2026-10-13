# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E06-03: manifests are validated, version-checked and routed by runtime kind."""

import json
import sys
import textwrap
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hearthos_core.app import create_app
from hearthos_core.plugins.context import CorePluginContext
from hearthos_core.plugins.loader import CORE_PREFIXES
from hearthos_core.settings import Settings
from hearthos_sdk import PluginContext

pytestmark = pytest.mark.unit

PLUGIN_CODE = """
from fastapi import APIRouter, Depends
from hearthos_sdk import Actor, PluginRegistration

class _Plugin:
    id = "{plugin_id}"

    def register(self, ctx):
        router = APIRouter()

        @router.get("/ping")
        async def ping() -> dict:
            return {{"plugin": ctx.plugin_id}}

        @router.get("/whoami")
        async def whoami(actor: Actor = Depends(ctx.current_actor)) -> dict:
            return {{"id": actor.id}}

        return PluginRegistration(router=router)

plugin = _Plugin()
"""


def _manifest(plugin_id: str, **overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "id": plugin_id,
        "name": "Probe",
        "version": "0.1.0",
        "type": ["domain"],
        "hearthos_api": "^0.1.0",
        "license": "MIT",
        "authors": [{"name": "t"}],
        "source": "x",
        "runtime": {"kind": "inprocess", "entrypoint": "", "api_prefix": "/probe"},
        "capabilities": ["graph:write:Probe"],
        "data_classes": {"reads": ["household"], "writes": ["household"], "emits": ["household"]},
        "contributes": {"widgets": [], "pages": []},
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def plugin_dir(tmp_path: Path) -> Iterator[Callable[..., str]]:
    root = tmp_path / "plugins"
    root.mkdir()
    sys.path.insert(0, str(tmp_path / "py"))
    added: list[str] = []

    def _make(prefix: str = "/probe", code: str | None = PLUGIN_CODE, **overrides: Any) -> str:
        plugin_id = f"org.example.p{uuid.uuid4().hex[:6]}"
        module = plugin_id.replace(".", "_")
        if code is not None:
            pkg = tmp_path / "py"
            pkg.mkdir(exist_ok=True)
            (pkg / f"{module}.py").write_text(textwrap.dedent(code.format(plugin_id=plugin_id)))
            added.append(module)
        manifest = _manifest(plugin_id, **overrides)
        if manifest["runtime"].get("kind") == "inprocess":
            manifest["runtime"] = {**manifest["runtime"], "entrypoint": f"{module}:plugin", "api_prefix": prefix}
        folder = root / plugin_id
        folder.mkdir()
        (folder / "hearthos.plugin.json").write_text(json.dumps(manifest))
        return plugin_id

    yield _make
    sys.path.remove(str(tmp_path / "py"))
    for module in added:
        sys.modules.pop(module, None)


def _app(tmp_path: Path, theme_paths: list[Path] | None = None):  # type: ignore[no-untyped-def]
    return create_app(
        Settings(
            env="test",
            plugin_paths=[tmp_path / "plugins"],
            theme_paths=theme_paths or [],
            relay_enabled=False,
            database_url="postgresql+psycopg://x:y@127.0.0.1:9/z",
        )
    )


def test_inprocess_plugin_is_mounted_under_its_prefix_with_its_short_name_tag(
    tmp_path: Path, plugin_dir: Callable[..., str]
) -> None:
    pid = plugin_dir()
    app = _app(tmp_path)
    assert app.state.plugins[pid].load_error is None
    with TestClient(app) as client:
        assert client.get("/api/v1/probe/ping").json() == {"plugin": pid}
        assert client.get("/api/v1/probe/whoami").status_code == 401, "ctx.current_actor is core's dependency"
    op = app.openapi()["paths"]["/api/v1/probe/ping"]["get"]
    assert op["tags"] == [pid.rsplit(".", 1)[1]]
    assert op["operationId"] == f"{pid.rsplit('.', 1)[1]}_ping"


@pytest.mark.parametrize("prefix", sorted(CORE_PREFIXES))
def test_core_prefixes_are_reserved(tmp_path: Path, plugin_dir: Callable[..., str], prefix: str) -> None:
    pid = plugin_dir(prefix=prefix)
    app = _app(tmp_path)
    assert "collides" in (app.state.plugins[pid].load_error or "")
    assert pid in app.state.plugin_load_errors


def test_invalid_manifest_is_recorded(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(version="v1")
    app = _app(tmp_path)
    assert "manifest" in (app.state.plugins[pid].load_error or "")


def test_incompatible_api_range(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(hearthos_api=">=2.0.0")
    assert "hearthos_api" in (_app(tmp_path).state.plugins[pid].load_error or "")


def test_unsupported_runtime(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(code=None, runtime={"kind": "container", "image": "x"})
    assert _app(tmp_path).state.plugins[pid].load_error == "runtime not supported in M0*"


def test_failing_plugin_does_not_crash_the_app(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(code="raise ImportError('broken on purpose')\n")
    app = _app(tmp_path)
    assert "ImportError" in (app.state.plugins[pid].load_error or "")
    with TestClient(app) as client:
        assert client.get("/api/v1/healthz").status_code == 200


def test_theme_manifests_go_to_the_theme_registry_without_imports(tmp_path: Path) -> None:
    folder = tmp_path / "themes" / "probe"
    folder.mkdir(parents=True)
    manifest = _manifest(
        "org.example.theme.probe",
        type=["theme"],
        runtime={"kind": "declarative"},
        capabilities=[],
        data_classes={"reads": [], "writes": [], "emits": []},
        contributes={"themes": [{"id": "probe", "file": "theme.json"}]},
    )
    (folder / "hearthos.plugin.json").write_text(json.dumps(manifest))
    app = _app(tmp_path, theme_paths=[tmp_path / "themes"])
    loaded = app.state.plugins["org.example.theme.probe"]
    assert loaded.kind == "declarative"
    assert loaded.load_error is None
    assert [d.id for d in app.state.theme_manifests] == ["org.example.theme.probe"]


def test_core_context_satisfies_the_sdk_protocol(tmp_path: Path) -> None:
    ctx = CorePluginContext("org.example.x", {"capabilities": [], "data_classes": {}}, _app(tmp_path))
    assert isinstance(ctx, PluginContext)
