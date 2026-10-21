# SPDX-License-Identifier: AGPL-3.0-or-later
"""Demo household seed (M0S-E11-02): users from ``fixtures/household/demo.json``, then each plugin's ``seed()``.

The seed writes through the same services, ``authorize()`` and outbox as the API. It writes no theme
setting, so the deployment uses ``HAUSKRAFT_DEFAULT_THEME`` until an adult picks another.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hauskraft_core.auth.deps import actor_for
from hauskraft_core.db.models import User
from hauskraft_core.logging import get_logger
from hauskraft_core.settings import Settings
from hauskraft_core.uow import UnitOfWork
from hauskraft_core.users import service as users
from hauskraft_sdk.errors import HauskraftError

DEFAULT_FIXTURE = Path(__file__).resolve().parents[5] / "fixtures" / "household" / "demo.json"
DEMO_PASSWORD = "hauskraft-demo"  # noqa: S105 - the documented public demo password (AGENTS.md rule 9)

_log = get_logger("hauskraft.seed")


class DemoPasswordInProductionError(HauskraftError):
    status = 400
    code = "demo_password_in_production"
    title = "Demo passwords are not allowed in production"


@dataclass(frozen=True)
class SeedResult:
    seeded: bool
    reason: str


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


async def run_seed(settings: Settings, fixture: dict[str, Any], *, force_demo: bool = False) -> SeedResult:
    """Seed the household unless seeding is disabled or users already exist (then it is a no-op)."""
    if not settings.seed_demo and not force_demo:
        return SeedResult(False, "demo seed disabled (HAUSKRAFT_SEED_DEMO=false)")
    if (
        settings.is_production
        and not force_demo
        and any(u.get("password") == DEMO_PASSWORD for u in fixture.get("users", []))
    ):
        raise DemoPasswordInProductionError(
            "Refusing to create accounts with the public demo password in production; pass --force-demo."
        )

    from hauskraft_core.app import create_app

    app = create_app(settings)
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with app.state.sessionmaker() as session:
            if await session.scalar(select(func.count()).select_from(User)):
                return SeedResult(False, "users already exist; nothing to seed")
        actors = {}
        for spec in fixture.get("users", []):
            async with UnitOfWork(app.state.sessionmaker, app.state.policy, settings) as uow:
                user = await users.get_by_username(uow, spec["username"])
                if user is None:
                    user = await users.create_user(
                        uow,
                        users.SYSTEM_ACTOR,
                        username=spec["username"],
                        display_name=spec["display_name"],
                        password=spec["password"],
                        locale=spec.get("locale", "en"),
                    )
                actors[spec["key"]] = actor_for(user)
        for plugin_id, section in (fixture.get("plugins") or {}).items():
            loaded = app.state.plugins.get(plugin_id)
            if loaded is None or loaded.registration is None or loaded.registration.seed is None:
                _log.warning("seed.plugin_skipped", plugin_id=plugin_id)
                continue
            from hauskraft_core.plugins.context import CorePluginContext

            ctx = CorePluginContext(plugin_id, loaded.manifest, app)
            await loaded.registration.seed(ctx, {**section, "actors": actors})
    finally:
        await engine.dispose()
    return SeedResult(True, f"seeded {len(actors)} users and {len(fixture.get('plugins') or {})} plugin(s)")
