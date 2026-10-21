# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plugin registry API (M0S-E06-04)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from hearthos_core.auth.deps import CurrentActor
from hearthos_core.db.models import PluginRecord
from hearthos_core.db.session import DbSession
from hearthos_core.events.outbox import emit
from hearthos_core.plugins.loader import LoadedPlugin
from hearthos_core.uow import UnitOfWork
from hearthos_sdk import ResourceRef
from hearthos_sdk.errors import HearthosError, NotFoundError

router = APIRouter(prefix="/plugins", tags=["plugins"])


class UseThemeSettingsError(HearthosError):
    status = 422
    code = "use_theme_settings"
    title = "Themes are chosen in the theme settings"


class PluginOut(BaseModel):
    id: str
    name: str
    version: str
    kind: str
    type: list[str]
    enabled: bool
    contributes: dict[str, Any]
    load_error: str | None


class PluginToggled(PluginOut):
    restart_required: bool


class PluginPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def _out(p: LoadedPlugin, enabled: bool) -> PluginOut:
    return PluginOut(
        id=p.id,
        name=str(p.manifest.get("name", p.id)),
        version=str(p.manifest.get("version", "")),
        kind=p.kind,
        type=p.type,
        enabled=enabled,
        contributes=dict(p.manifest.get("contributes") or {}),
        load_error=p.load_error,
    )


async def _enabled_map(db: DbSession) -> dict[str, bool]:
    from sqlalchemy import select

    rows = await db.execute(select(PluginRecord.id, PluginRecord.enabled))
    return {pid: enabled for pid, enabled in rows.all()}


@router.get("", responses={401: {}})
async def list_(request: Request, db: DbSession, actor: CurrentActor) -> list[PluginOut]:
    enabled = await _enabled_map(db)
    return [_out(p, enabled.get(p.id, True)) for p in request.app.state.plugins.values()]


@router.patch("/{plugin_id}", responses={401: {}, 403: {}, 404: {}, 422: {}})
async def update(plugin_id: str, body: PluginPatch, request: Request, actor: CurrentActor) -> PluginToggled:
    loaded: LoadedPlugin | None = request.app.state.plugins.get(plugin_id)
    if loaded is None:
        raise NotFoundError(f"No plugin {plugin_id!r}.")
    if loaded.is_theme:
        raise UseThemeSettingsError("Theme plugins are chosen in Settings → Appearance, not switched on or off.")
    state = request.app.state
    async with UnitOfWork(state.sessionmaker, state.policy, state.settings) as uow:
        await uow.authorize(actor, "plugin.toggle", ResourceRef("Plugin", plugin_id), "household", "plugins:write")
        record = await uow.session.get(PluginRecord, plugin_id)
        if record is None:
            raise NotFoundError(f"No plugin record for {plugin_id!r}.")
        record.enabled = body.enabled
        await emit(
            "hearthos.plugin.toggled",
            f"plugin/{plugin_id}",
            {"plugin_id": plugin_id, "enabled": body.enabled},
            "household",
        )
    return PluginToggled(**_out(loaded, body.enabled).model_dump(), restart_required=True)
