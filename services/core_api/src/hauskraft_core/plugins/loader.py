# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-process plugin loader (M0S-E06-03, ADR-0004).

At app creation every ``*/hauskraft.plugin.json`` under ``HAUSKRAFT_PLUGIN_PATHS`` and ``HAUSKRAFT_THEME_PATHS``
is validated against the manifest schema and its ``hauskraft_api`` range checked against the SDK.

* ``inprocess``: the entrypoint is imported, ``register(ctx)`` called and the router mounted at
  ``/api/v1{api_prefix}`` with the plugin's short name as tag. No database is needed, so the OpenAPI export
  sees plugin routes too. A plugin disabled in the ``plugins`` table answers 404 until the next restart.
* ``declarative`` plugins of type ``theme`` go to the theme registry; nothing is imported for them.
* Anything else is recorded with ``load_error = "runtime not supported in M0*"``.

A failure never crashes the app: it is stored in ``load_error`` and fails readiness.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from semantic_version import NpmSpec, Version
from sqlalchemy import MetaData

from hauskraft_core import schemas
from hauskraft_core.logging import get_logger
from hauskraft_core.plugins.context import CorePluginContext
from hauskraft_core.plugins.manifests import DiscoveredManifest, discover
from hauskraft_sdk import HAUSKRAFT_API_VERSION, Plugin, PluginRegistration
from hauskraft_sdk.tools import ToolAnnotations

if TYPE_CHECKING:
    from fastapi import FastAPI

MANIFEST_SCHEMA = "manifest/hauskraft.plugin.schema.json"
UNSUPPORTED = "runtime not supported in M0*"
CORE_PREFIXES = frozenset(
    {
        "/auth",
        "/me",
        "/users",
        "/plugins",
        "/themes",
        "/theme",
        "/settings",
        "/activity",
        "/healthz",
        "/readyz",
        "/dashboard",
        "/household",
        "/setup",
        "/assistant",
    }
)

_log = get_logger("hauskraft.plugins")


@dataclass
class LoadedPlugin:
    id: str
    folder: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    kind: str
    type: list[str]
    enabled: bool = True
    load_error: str | None = None
    registration: PluginRegistration | None = field(default=None, repr=False)

    @property
    def is_theme(self) -> bool:
        return self.type == ["theme"]


def short_name(plugin_id: str) -> str:
    return plugin_id.rsplit(".", 1)[-1]


def _check_manifest(found: DiscoveredManifest) -> str | None:
    if found.error:
        return f"manifest: {found.error}"
    problems = schemas.errors(MANIFEST_SCHEMA, found.manifest)
    if problems:
        return "manifest invalid: " + "; ".join(problems[:5])
    try:
        if not NpmSpec(str(found.manifest["hauskraft_api"])).match(Version(HAUSKRAFT_API_VERSION)):
            return f"hauskraft_api {found.manifest['hauskraft_api']!r} does not include {HAUSKRAFT_API_VERSION}"
    except ValueError as exc:
        return f"hauskraft_api is not a valid range: {exc}"
    return None


def _manifest_tool(entry: dict[str, Any]) -> dict[str, Any]:
    """A manifest tool with the cautious defaults filled in (spec §5.3), comparable with a ``ToolSpec``."""
    given = entry.get("annotations") or {}
    return {
        "annotations": ToolAnnotations(
            read_only=given.get("read_only", False),
            destructive=given.get("destructive", True),
            idempotent=given.get("idempotent", False),
            open_world=given.get("open_world", True),
        ),
        "permission": entry.get("permission"),
        "data_class": entry.get("data_class"),
    }


def check_tools(
    manifest: dict[str, Any], registration: PluginRegistration, owners: dict[str, str], plugin_id: str
) -> str | None:
    """The agent tools in the manifest and in code must be the same tools with the same contract (M2S-E02-02)."""
    listed = {
        str(entry["name"]): _manifest_tool(entry)
        for entry in (manifest.get("contributes") or {}).get("tools") or []
        if entry.get("agent", True)
    }
    coded = {tool.name: tool for tool in registration.tools if tool.agent}
    if set(listed) != set(coded):
        only_code = sorted(set(coded) - set(listed))
        only_manifest = sorted(set(listed) - set(coded))
        return (
            "tools differ from the manifest: "
            + (f"not in the manifest: {', '.join(only_code)}" if only_code else "")
            + ("; " if only_code and only_manifest else "")
            + (f"not registered in code: {', '.join(only_manifest)}" if only_manifest else "")
        )
    for name, tool in coded.items():
        entry = listed[name]
        if entry["annotations"] != tool.annotations:
            return f"tool {name}: annotations differ between the manifest and the code"
        if entry["permission"] not in (None, tool.permission):
            return f"tool {name}: permission differs between the manifest and the code"
        if entry["data_class"] not in (None, str(tool.data_class)):
            return f"tool {name}: data_class differs between the manifest and the code"
        if tool.wire_name in owners:
            return f"tool {name} collides with a tool of plugin {owners[tool.wire_name]}"
    return None


def _import_entrypoint(entrypoint: str) -> Plugin:
    module_name, _, attribute = entrypoint.partition(":")
    obj = getattr(importlib.import_module(module_name), attribute)
    if not isinstance(obj, Plugin):
        raise TypeError(f"{entrypoint} is not a hauskraft_sdk.Plugin")
    return obj


def _enabled_guard(plugin_id: str) -> Any:
    async def guard(request: Request) -> None:
        if plugin_id in request.app.state.disabled_plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} is disabled.")

    return Depends(guard)


def _load_one(found: DiscoveredManifest, app: FastAPI, prefixes_in_use: dict[str, str]) -> LoadedPlugin:
    manifest = found.manifest
    runtime = found.runtime
    loaded = LoadedPlugin(
        id=found.id,
        folder=found.folder,
        manifest=manifest,
        manifest_sha256=found.sha256,
        kind=str(runtime.get("kind", "unknown")),
        type=list(manifest.get("type") or []),
    )
    loaded.load_error = _check_manifest(found)
    if loaded.is_theme:
        # Themes go to the theme registry even when broken: it records why, and only a broken built-in
        # Default theme fails readiness (M0S-E13-03).
        app.state.theme_manifests.append(found)
        if not loaded.load_error and loaded.kind != "declarative":
            loaded.load_error = "theme plugins must be declarative"
        return loaded
    if loaded.load_error:
        return loaded
    if loaded.kind != "inprocess":
        loaded.load_error = UNSUPPORTED
        return loaded
    prefix = str(runtime.get("api_prefix") or f"/{short_name(loaded.id)}").rstrip("/")
    first_segment = "/" + prefix.strip("/").split("/", 1)[0]
    if first_segment in CORE_PREFIXES:
        loaded.load_error = f"api_prefix {prefix!r} collides with a core route"
        return loaded
    if first_segment in prefixes_in_use:
        loaded.load_error = f"api_prefix {prefix!r} collides with plugin {prefixes_in_use[first_segment]}"
        return loaded
    try:
        plugin = _import_entrypoint(str(runtime.get("entrypoint", "")))
        registration = plugin.register(CorePluginContext(loaded.id, manifest, app))
    except Exception as exc:  # a broken plugin must not take core down
        loaded.load_error = f"{type(exc).__name__}: {exc}"
        _log.exception("plugin.load_failed", plugin_id=loaded.id)
        return loaded
    tool_problem = check_tools(manifest, registration, app.state.tool_owners, loaded.id)
    if tool_problem:
        loaded.load_error = tool_problem
        return loaded
    loaded.registration = registration
    for tool in registration.tools:
        app.state.tool_owners[tool.wire_name] = loaded.id
        app.state.tool_names.add(tool.name)
    prefixes_in_use[first_segment] = loaded.id
    mounted = APIRouter(dependencies=[_enabled_guard(loaded.id)])
    mounted.include_router(registration.router, prefix=prefix, tags=[short_name(loaded.id)])
    app.include_router(mounted, prefix="/api/v1")
    _log.info("plugin.loaded", plugin_id=loaded.id, prefix=prefix)
    return loaded


def load_plugins(app: FastAPI, plugin_paths: Iterable[Path], theme_paths: Iterable[Path]) -> None:
    app.state.plugins = {}
    app.state.tool_owners = {}  # wire name -> plugin id (M2S-E02-02)
    app.state.tool_names = set()
    app.state.theme_manifests = []
    app.state.disabled_plugins = set()
    prefixes: dict[str, str] = {}
    for found in [*discover(plugin_paths), *discover(theme_paths)]:
        if found.id in app.state.plugins:
            _log.warning("plugin.duplicate_id", plugin_id=found.id, folder=str(found.folder))
            continue
        loaded = _load_one(found, app, prefixes)
        app.state.plugins[loaded.id] = loaded
        if loaded.load_error and not loaded.is_theme:
            app.state.plugin_load_errors[loaded.id] = loaded.load_error


def plugin_metadata(app: FastAPI) -> list[MetaData]:
    return [
        p.registration.metadata
        for p in app.state.plugins.values()
        if p.registration is not None and p.registration.metadata is not None
    ]
