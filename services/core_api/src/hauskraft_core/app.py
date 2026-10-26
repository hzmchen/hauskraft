# SPDX-License-Identifier: AGPL-3.0-or-later
"""FastAPI application factory (M0S-E03-01).

Run with ``uvicorn hauskraft_core.app:create_app --factory``. Every route lives under ``/api/v1``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from hauskraft_core.assistant.registry import ToolRegistry
from hauskraft_core.auth.providers import provider_from_settings
from hauskraft_core.auth.ratelimit import LoginRateLimiter
from hauskraft_core.errors import install_error_handlers
from hauskraft_core.events.relay import run_relay
from hauskraft_core.health import install_core_checks
from hauskraft_core.logging import RequestContextMiddleware, configure_logging, get_logger
from hauskraft_core.plugins.loader import load_plugins
from hauskraft_core.policy import policy_from_settings
from hauskraft_core.settings import Settings, get_settings
from hauskraft_core.themes.registry import install as install_themes
from hauskraft_core.themes.registry import log_active_theme

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
    from hauskraft_core.plugins.repository import upsert_loaded
    from hauskraft_core.uow import UnitOfWork
    from hauskraft_core.users.service import SYSTEM_ACTOR
    from hauskraft_sdk import ResourceRef

    try:
        async with UnitOfWork(app.state.sessionmaker, app.state.policy, app.state.settings) as uow:
            await uow.authorize(SYSTEM_ACTOR, "plugin.sync", ResourceRef("Plugin"), "household", "plugins:write")
            enabled = await upsert_loaded(uow.session, app.state.plugins.values())
    except Exception as exc:  # readiness reports the database problem
        get_logger("hauskraft.plugins").warning("plugin.sync_failed", error_type=type(exc).__name__)
        return
    app.state.disabled_plugins = {pid for pid, on in enabled.items() if not on}
    for pid in app.state.disabled_plugins:
        app.state.plugin_load_errors.pop(pid, None)  # a disabled plugin does not block readiness


def build_api_router() -> APIRouter:
    """Core routers; later stories add auth, users, plugins, themes, activity and dashboards."""
    from hauskraft_core import health
    from hauskraft_core.activity import router as activity
    from hauskraft_core.assistant import router as assistant
    from hauskraft_core.auth import router as auth
    from hauskraft_core.dashboard import router as dashboard
    from hauskraft_core.household import router as household
    from hauskraft_core.plugins import router as plugins
    from hauskraft_core.setup import router as setup
    from hauskraft_core.themes import router as themes
    from hauskraft_core.users import router as users

    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(users.router)
    router.include_router(plugins.router)
    router.include_router(activity.router)
    router.include_router(themes.router)
    router.include_router(dashboard.router)
    router.include_router(household.router)
    router.include_router(setup.router)
    router.include_router(assistant.router)
    return router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Hauskraft core API",
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
    app.state.tool_registry = ToolRegistry.from_plugins(app.state.plugins)
    install_themes(app)
    return app
