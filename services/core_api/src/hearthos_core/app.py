# SPDX-License-Identifier: AGPL-3.0-or-later
"""FastAPI application factory (M0S-E03-01).

Run with ``uvicorn hearthos_core.app:create_app --factory``. Every route lives under ``/api/v1``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from hearthos_core.auth.providers import provider_from_settings
from hearthos_core.auth.ratelimit import LoginRateLimiter
from hearthos_core.errors import install_error_handlers
from hearthos_core.health import install_core_checks
from hearthos_core.logging import RequestContextMiddleware, configure_logging
from hearthos_core.plugins.loader import load_plugins
from hearthos_core.policy import policy_from_settings
from hearthos_core.settings import Settings, get_settings

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
    try:
        yield
    finally:
        await engine.dispose()
        app.state.engine = None
        app.state.sessionmaker = None


def build_api_router() -> APIRouter:
    """Core routers; later stories add auth, users, plugins, themes, activity and dashboards."""
    from hearthos_core import health
    from hearthos_core.auth import router as auth
    from hearthos_core.users import router as users

    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(users.router)
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
    return app
