# SPDX-License-Identifier: AGPL-3.0-or-later
"""``/dashboard/{dashboard_id}`` (M0S-E08-06): the signed-in user's layout, or the default."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Request

from hauskraft_core.auth.deps import CurrentSession, actor_for
from hauskraft_core.dashboard.schemas import Dashboard, LayoutIn
from hauskraft_core.dashboard.service import default_layout, save_layout, stored_layout
from hauskraft_core.db.session import DbSession
from hauskraft_core.uow import UnitOfWork

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DashboardId = Annotated[str, Path(pattern=r"^[a-z0-9-]{1,40}$")]


def _contributed_widgets(request: Request) -> list[tuple[str, dict[str, Any]]]:
    """Widgets of loaded, enabled plugins, in a stable order."""
    disabled = request.app.state.disabled_plugins
    out: list[tuple[str, dict[str, Any]]] = []
    for plugin_id, loaded in sorted(request.app.state.plugins.items()):
        if loaded.load_error or plugin_id in disabled or loaded.is_theme:
            continue
        widgets = (loaded.manifest.get("contributes") or {}).get("widgets") or []
        out.extend((plugin_id, widget) for widget in widgets if isinstance(widget, dict) and "id" in widget)
    return out


@router.get("/{dashboard_id}", responses={401: {}, 422: {}})
async def get(dashboard_id: DashboardId, request: Request, db: DbSession, resolved: CurrentSession) -> Dashboard:
    layout = await stored_layout(db, resolved[1].id, dashboard_id)
    if layout is None:
        layout = default_layout(_contributed_widgets(request))
    return Dashboard(dashboard_id=dashboard_id, layout=layout)


@router.put("/{dashboard_id}", responses={401: {}, 403: {}, 422: {}})
async def put(dashboard_id: DashboardId, body: LayoutIn, request: Request, resolved: CurrentSession) -> Dashboard:
    state = request.app.state
    async with UnitOfWork(state.sessionmaker, state.policy, state.settings) as uow:
        layout = await save_layout(uow, actor_for(resolved[1]), dashboard_id, body.layout)
    return Dashboard(dashboard_id=dashboard_id, layout=layout)
