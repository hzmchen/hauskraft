# SPDX-License-Identifier: AGPL-3.0-or-later
"""Liveness and readiness (M0S-E03-02).

``GET /healthz`` never touches the database. ``GET /readyz`` runs every registered check and answers 200
only when all pass; otherwise 503 with the failing checks. Core registers ``database``, ``migrations`` and
``plugins``; the theme registry adds ``theme`` (M0S-E13-03) through ``register_check``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel
from sqlalchemy import Connection, text
from starlette.responses import JSONResponse

from hearthos_core.db import migrations

Check = Callable[[], Awaitable[tuple[bool, str]]]

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str


class CheckResult(BaseModel):
    name: str
    ok: bool
    detail: str


class Readiness(BaseModel):
    status: str
    checks: list[CheckResult]


def register_check(app: FastAPI, name: str, check: Check) -> None:
    app.state.readiness_checks[name] = check


def install_core_checks(app: FastAPI) -> None:
    app.state.readiness_checks = {}
    app.state.plugin_load_errors = {}

    async def database() -> tuple[bool, str]:
        engine = app.state.engine
        if engine is None:
            return False, "database engine not started"
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:  # any driver error means "not ready"
            return False, f"{type(exc).__name__}: database not reachable"
        return True, "SELECT 1 ok"

    async def schema() -> tuple[bool, str]:
        engine = app.state.engine
        settings = app.state.settings

        def at_heads(conn: Connection) -> bool:
            return migrations.heads_applied(settings, conn)

        try:
            async with engine.connect() as conn:
                ok = await conn.run_sync(at_heads)
        except Exception as exc:
            return False, f"{type(exc).__name__}: cannot read alembic_version"
        return (True, "at heads") if ok else (False, "database is not at heads; run `hearthos db upgrade`")

    async def plugins() -> tuple[bool, str]:
        errors: dict[str, str] = app.state.plugin_load_errors
        if errors:
            return False, "; ".join(f"{pid}: {err}" for pid, err in sorted(errors.items()))
        return True, "all enabled plugins loaded"

    register_check(app, "database", database)
    register_check(app, "migrations", schema)
    register_check(app, "plugins", plugins)


@router.get("/healthz")
async def healthz() -> Health:
    return Health(status="ok")


@router.get("/readyz", response_model=Readiness, responses={503: {"model": Readiness}})
async def readyz(request: Request) -> Any:
    results: list[CheckResult] = []
    for name, check in request.app.state.readiness_checks.items():
        try:
            ok, detail = await check()
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: check failed"
        results.append(CheckResult(name=name, ok=ok, detail=detail))
    ready = all(r.ok for r in results)
    body = Readiness(status="ready" if ready else "not_ready", checks=results)
    return JSONResponse(body.model_dump(), status_code=200 if ready else 503)
