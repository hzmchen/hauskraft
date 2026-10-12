# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-01: the app factory boots with a test database URL and serves everything under /api/v1."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

from hearthos_core.app import create_app
from hearthos_core.settings import Settings

pytestmark = pytest.mark.unit


def _settings() -> Settings:
    # Nothing listens here: the factory and lifespan must not need a live database.
    return Settings(
        database_url="postgresql+psycopg://test:test@127.0.0.1:9/test",
        secret_key="t" * 32,
        env="test",
        relay_enabled=False,
        plugin_paths=[],
        theme_paths=[],
    )


def test_create_app_returns_a_fastapi_app() -> None:
    app = create_app(_settings())
    assert isinstance(app, FastAPI)
    assert app.state.settings.env == "test"


def test_lifespan_starts_and_stops_without_database() -> None:
    app = create_app(_settings())
    with TestClient(app) as client:
        assert app.state.engine is not None
        assert client.get("/api/v1/openapi.json").status_code == 200
    assert app.state.engine is None, "the engine is disposed on shutdown"


def test_every_route_is_under_api_v1() -> None:
    app = create_app(_settings())
    # Plain routes (docs, OpenAPI) are listed directly; included routers show up in the OpenAPI paths.
    paths = [r.path for r in app.routes if isinstance(r, Route)] + list(app.openapi()["paths"])
    assert paths, "no routes registered"
    assert all(p.startswith("/api/v1/") for p in paths), [p for p in paths if not p.startswith("/api/v1/")]


def test_openapi_is_3_1() -> None:
    assert create_app(_settings()).openapi()["openapi"].startswith("3.1")
