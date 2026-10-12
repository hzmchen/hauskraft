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

from hearthos_core.errors import install_error_handlers
from hearthos_core.logging import RequestContextMiddleware, configure_logging
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
    """Core routers; later stories add health, auth, users, plugins, themes, activity and dashboards."""
    return APIRouter()


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
    app.state.engine = None
    app.state.sessionmaker = None
    install_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(build_api_router(), prefix=API_PREFIX)
    return app
