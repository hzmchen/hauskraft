# SPDX-License-Identifier: AGPL-3.0-or-later
"""FastAPI application factory (M0S-E03-01).

Run with ``uvicorn hearthos_core.app:create_app --factory``. Every route lives under ``/api/v1``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from hearthos_core.auth.providers import provider_from_settings
from hearthos_core.auth.ratelimit import LoginRateLimiter
from hearthos_core.errors import install_error_handlers
from hearthos_core.events.relay import run_relay
from hearthos_core.health import install_core_checks
from hearthos_core.logging import RequestContextMiddleware, configure_logging, get_logger
from hearthos_core.plugins.loader import load_plugins
from hearthos_core.policy import policy_from_settings
from hearthos_core.settings import Settings, get_settings
from hearthos_core.themes.registry import install as install_themes
from hearthos_core.themes.registry import log_active_theme

API_PREFIX = "/api/v1"
API_VERSION = "0.1.0"


def _operation_id(route: APIRoute) -> str:
    """Stable operation ids like ``tasks_list``: first tag plus the route function name."""
    tag = str(route.tags[0]) if route.tags else "core"
    return f"{tag}_{route.name}"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    await _sync_plugin_records(app)
    await log_active_theme(app)
    stop = asyncio.Event()
    relay = asyncio.create_task(run_relay(app.state.sessionmaker, stop)) if settings.relay_enabled else None
    try:
        yield
    finally:
        stop.set()
        if relay is not None:
            await relay
        await engine.dispose()
        app.state.engine = None
        app.state.sessionmaker = None


async def _sync_plugin_records(app: FastAPI) -> None:
    """Upsert the ``plugins`` table and apply its ``enabled`` flags; tolerate an unreachable database."""
    from hearthos_core.plugins.repository import upsert_loaded
    from hearthos_core.uow import UnitOfWork
    from hearthos_core.users.service import SYSTEM_ACTOR
    from hearthos_sdk import ResourceRef

    try:
        async with UnitOfWork(app.state.sessionmaker, app.state.policy, app.state.settings) as uow:
            await uow.authorize(SYSTEM_ACTOR, "plugin.sync", ResourceRef("Plugin"), "household", "plugins:write")
            enabled = await upsert_loaded(uow.session, app.state.plugins.values())
    except Exception as exc:  # readiness reports the database problem
        get_logger("hearthos.plugins").warning("plugin.sync_failed", error_type=type(exc).__name__)
        return
    app.state.disabled_plugins = {pid for pid, on in enabled.items() if not on}
    for pid in app.state.disabled_plugins:
        app.state.plugin_load_errors.pop(pid, None)  # a disabled plugin does not block readiness


def build_api_router() -> APIRouter:
    """Core routers; later stories add auth, users, plugins, themes, activity and dashboards."""
    from hearthos_core import health
    from hearthos_core.activity import router as activity
    from hearthos_core.auth import router as auth
    from hearthos_core.dashboard import router as dashboard
    from hearthos_core.plugins import router as plugins
    from hearthos_core.themes import router as themes
    from hearthos_core.users import router as users

    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(users.router)
    router.include_router(plugins.router)
    router.include_router(activity.router)
    router.include_router(themes.router)
    router.include_router(dashboard.router)
    return router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="HearthOS core API",
        version=API_VERSION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=f"{API_PREFIX}/docs/oauth2-redirect",
        generate_unique_id_function=_operation_id,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.policy = policy_from_settings(settings)
    app.state.login_limiter = LoginRateLimiter()
    app.state.identity_provider = provider_from_settings(settings)
    app.state.engine = None
    app.state.sessionmaker = None
    install_error_handlers(app)
    install_core_checks(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(build_api_router(), prefix=API_PREFIX)
    load_plugins(app, settings.plugin_paths, settings.theme_paths)
    install_themes(app)
    return app
