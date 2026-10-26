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

from hauskraft_core.app import create_app
from hauskraft_core.plugins.context import CorePluginContext
from hauskraft_core.plugins.loader import CORE_PREFIXES
from hauskraft_core.settings import Settings
from hauskraft_sdk import PluginContext

pytestmark = pytest.mark.unit

PLUGIN_CODE = """
from fastapi import APIRouter, Depends
from hauskraft_sdk import Actor, PluginRegistration

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
        "hauskraft_api": "^0.1.0",
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
        (folder / "hauskraft.plugin.json").write_text(json.dumps(manifest))
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
    pid = plugin_dir(hauskraft_api=">=2.0.0")
    assert "hauskraft_api" in (_app(tmp_path).state.plugins[pid].load_error or "")


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
    (folder / "hauskraft.plugin.json").write_text(json.dumps(manifest))
    app = _app(tmp_path, theme_paths=[tmp_path / "themes"])
    loaded = app.state.plugins["org.example.theme.probe"]
    assert loaded.kind == "declarative"
    assert loaded.load_error is None
    assert [d.id for d in app.state.theme_manifests] == ["org.example.theme.probe"]


def test_core_context_satisfies_the_sdk_protocol(tmp_path: Path) -> None:
    ctx = CorePluginContext("org.example.x", {"capabilities": [], "data_classes": {}}, _app(tmp_path))
    assert isinstance(ctx, PluginContext)


# ---------------------------------------------------------------- M2S-E02-02: tools in the manifest and in code
TOOL_CODE = """
from fastapi import APIRouter
from pydantic import BaseModel
from hauskraft_sdk import PluginRegistration
from hauskraft_sdk.tools import ToolAnnotations, ToolOutcome, ToolSpec

class Args(BaseModel):
    text: str

async def handle(ctx, actor, args):
    return ToolOutcome(output={{"echo": args.text}})

class _Plugin:
    id = "{plugin_id}"

    def register(self, ctx):
        return PluginRegistration(router=APIRouter(), tools=[{tools}])

plugin = _Plugin()
"""
ECHO = (
    'ToolSpec(name="{{short}}.echo", description="Echo the text.", input_model=Args, handler=handle, '
    "annotations=ToolAnnotations(read_only=True, destructive=False, idempotent=True, open_world=False), "
    'permission="task.read", data_class="household")'
)
ECHO_MANIFEST = {
    "description": "Echo the text.",
    "annotations": {"read_only": True, "destructive": False, "idempotent": True, "open_world": False},
    "permission": "task.read",
    "data_class": "household",
}


def test_tools_matching_the_manifest_are_registered(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(
        prefix="/echo",
        code=TOOL_CODE.replace("{tools}", ECHO),
        contributes={"widgets": [], "pages": [], "tools": [{"name": "SHORT.echo", **ECHO_MANIFEST}]},
    )
    _fix_short_names(tmp_path, pid)
    app = _app(tmp_path)
    loaded = app.state.plugins[pid]
    assert loaded.load_error is None, loaded.load_error
    short = pid.rsplit(".", 1)[1]
    assert [t.name for t in loaded.registration.tools] == [f"{short}.echo"]
    assert f"{short}.echo" in app.state.tool_names


def test_a_tool_missing_from_the_manifest_is_a_load_error(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(prefix="/echo2", code=TOOL_CODE.replace("{tools}", ECHO))
    _fix_short_names(tmp_path, pid)
    app = _app(tmp_path)
    assert "echo" in (app.state.plugins[pid].load_error or "")


def test_annotations_must_agree(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(
        prefix="/echo3",
        code=TOOL_CODE.replace("{tools}", ECHO),
        contributes={"widgets": [], "pages": [], "tools": [{"name": "SHORT.echo", **ECHO_MANIFEST, "annotations": {}}]},
    )
    _fix_short_names(tmp_path, pid)
    app = _app(tmp_path)
    assert "annotations" in (app.state.plugins[pid].load_error or "")


def test_hidden_manifest_tools_need_no_code(tmp_path: Path, plugin_dir: Callable[..., str]) -> None:
    pid = plugin_dir(
        prefix="/echo4", contributes={"widgets": [], "pages": [], "tools": [{"name": "SHORT.reindex", "agent": False}]}
    )
    _fix_short_names(tmp_path, pid)
    assert _app(tmp_path).state.plugins[pid].load_error is None


def _fix_short_names(tmp_path: Path, pid: str) -> None:
    """Replace the placeholders with the generated plugin's short name, in its manifest and its code."""
    short = pid.rsplit(".", 1)[1]
    manifest = tmp_path / "plugins" / pid / "hauskraft.plugin.json"
    manifest.write_text(manifest.read_text().replace("SHORT.", f"{short}."))
    code = tmp_path / "py" / f"{pid.replace('.', '_')}.py"
    if code.exists():
        code.write_text(code.read_text().replace("{short}", short))
