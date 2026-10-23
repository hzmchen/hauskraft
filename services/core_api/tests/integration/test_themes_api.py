# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E13-04: the deployment theme setting and the theme API, with fixture themes and a stand-in Default."""

import asyncio
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text

from hauskraft_core.app import create_app
from hauskraft_core.db.models import DeploymentSetting, OutboxEvent, User
from hauskraft_core.policy import DenyAllPolicy
from hauskraft_core.settings import Settings
from hauskraft_core.settings_store.service import set_theme
from hauskraft_core.themes.registry import BUILTIN_DEFAULT
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor
from hauskraft_sdk.errors import PolicyDeniedError
from tests.integration.conftest import PASSWORD
from tests.theme_helpers import FIXTURES, builtin_default

pytestmark = pytest.mark.integration
CHANGED = "hauskraft.settings.theme_changed"
OK = "org.example.theme.valid-minimal"
BAD = "org.example.theme.invalid-low-contrast"


def _reset(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM deployment_settings WHERE key = 'theme_id'"))
    engine.dispose()


def _stored(url: str) -> tuple[object, int]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            value = conn.scalar(select(DeploymentSetting.value).where(DeploymentSetting.key == "theme_id"))
            events = conn.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.type == "hauskraft.settings.theme_changed")
            )
            return value, int(events or 0)
    finally:
        engine.dispose()


@pytest.fixture
def theme_settings(api_settings: Settings, tmp_path: Path) -> Iterator[Settings]:
    _reset(api_settings.database_url)
    yield api_settings.model_copy(update={"theme_paths": [builtin_default(tmp_path), FIXTURES]})
    _reset(api_settings.database_url)


@pytest.fixture
def themed(theme_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(theme_settings), headers={"Origin": "http://testserver"}) as c:
        yield c


@pytest.fixture
def actor(theme_settings: Settings, make_user: Callable[..., str]) -> Actor:
    username = make_user("Probe", role="owner")
    engine = create_engine(theme_settings.database_url)
    with engine.connect() as conn:
        user_id = conn.scalar(select(User.id).where(User.username == username))
    engine.dispose()
    return Actor(id=str(user_id), role="owner", display_name="Probe")


@pytest.fixture
def h(themed: TestClient, make_user: Callable[..., str]) -> dict[str, str]:
    r = themed.post("/api/v1/auth/login", json={"username": make_user("Owner", role="owner"), "password": PASSWORD})
    return {"X-CSRF-Token": r.json()["csrf_token"]}


def test_public_endpoints_work_without_a_session(themed: TestClient) -> None:
    active = themed.get("/api/v1/theme")
    assert active.status_code == 200, active.text
    body = active.json()
    assert body["theme_id"] == BUILTIN_DEFAULT
    assert body["css_url"].startswith("/api/v1/theme/active.css")
    assert set(body["components"]) == {"widget", "button", "checkbox"}
    assert set(body["layout"]) == {"navigation", "density", "content_width"}
    assert body["icons"] == {"sprite_url": None, "names": []}
    css = themed.get("/api/v1/theme/active.css")
    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert css.headers["cache-control"] == "no-cache"
    assert css.headers["etag"] == f'"{body["hash"]}"'
    assert css.text.startswith(f"/* {BUILTIN_DEFAULT} ")


def test_active_css_304(themed: TestClient) -> None:
    etag = themed.get("/api/v1/theme/active.css").headers["etag"]
    r = themed.get("/api/v1/theme/active.css", headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.headers["etag"] == etag
    assert not r.content
    assert themed.get("/api/v1/theme/active.css", headers={"If-None-Match": '"nope"'}).status_code == 200


def test_list_needs_a_session(themed: TestClient) -> None:
    assert themed.get("/api/v1/themes").status_code == 401


def test_list_marks_exactly_one_active(themed: TestClient, h: dict[str, str]) -> None:
    themes = {t["theme_id"]: t for t in themed.get("/api/v1/themes", headers=h).json()}
    assert themes[BUILTIN_DEFAULT]["active"]
    assert sum(t["active"] for t in themes.values()) == 1
    assert themes[BAD]["valid"] is False
    assert themes[BAD]["errors"][0]["code"] == "contrast.text"


def test_set_and_get(themed: TestClient, h: dict[str, str], theme_settings: Settings) -> None:
    events_before = _stored(theme_settings.database_url)[1]
    r = themed.put("/api/v1/settings/theme", json={"theme_id": OK}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["theme_id"] == OK
    assert r.json()["active"] is True
    assert themed.get("/api/v1/theme").json()["theme_id"] == OK
    assert _stored(theme_settings.database_url) == (OK, events_before + 1)
    css = themed.get("/api/v1/theme/active.css").text
    assert "Fixture Sans" in css


def test_event_carries_from_and_to(themed: TestClient, h: dict[str, str], theme_settings: Settings) -> None:
    themed.put("/api/v1/settings/theme", json={"theme_id": OK}, headers=h)
    engine = create_engine(theme_settings.database_url)
    with engine.connect() as conn:
        envelope = conn.scalar(
            select(OutboxEvent.envelope).where(OutboxEvent.type == CHANGED).order_by(OutboxEvent.time.desc()).limit(1)
        )
    engine.dispose()
    assert envelope["data"] == {"from": BUILTIN_DEFAULT, "to": OK}
    assert envelope["source"] == "dev.hauskraft.core"
    assert envelope["dataclass"] == "household"
    assert envelope["actorid"]


def test_invalid_theme_is_409_with_errors(themed: TestClient, h: dict[str, str]) -> None:
    r = themed.put("/api/v1/settings/theme", json={"theme_id": BAD}, headers=h)
    assert r.status_code == 409
    assert r.json()["code"] == "theme_invalid"
    assert r.json()["errors"][0]["code"] == "contrast.text"


def test_unknown_theme_is_404(themed: TestClient, h: dict[str, str]) -> None:
    r = themed.put("/api/v1/settings/theme", json={"theme_id": "org.example.theme.nope"}, headers=h)
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_theme"


def test_put_needs_csrf(themed: TestClient, h: dict[str, str]) -> None:
    r = themed.put("/api/v1/settings/theme", json={"theme_id": OK})
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_failed"


def test_assets_are_served_with_safe_headers(themed: TestClient) -> None:
    r = themed.get(f"/api/v1/theme/assets/{OK}/assets/fonts/FixtureSans.woff2?h=abc")
    assert r.status_code == 200
    assert r.content[:4] == b"wOF2"
    assert r.headers["content-type"] == "font/woff2"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


@pytest.mark.parametrize(
    "path", ["tokens.light.json", "hauskraft.plugin.json", "..%2Fhauskraft.plugin.json", "assets/../theme.json"]
)
def test_only_referenced_assets_are_served(themed: TestClient, path: str) -> None:
    assert themed.get(f"/api/v1/theme/assets/{OK}/{path}").status_code in (400, 404)


def test_assets_of_invalid_or_unknown_themes_are_404(themed: TestClient) -> None:
    assert themed.get(f"/api/v1/theme/assets/{BAD}/assets/fonts/FixtureSans.woff2").status_code == 404
    assert themed.get("/api/v1/theme/assets/org.example.nope/assets/x.woff2").status_code == 404


def test_rollback_removes_setting_and_event(themed: TestClient, theme_settings: Settings, actor: Actor) -> None:
    app = themed.app
    before = _stored(theme_settings.database_url)

    async def failing() -> None:
        async with UnitOfWork(app.state.sessionmaker, app.state.policy, theme_settings) as uow:  # type: ignore[attr-defined]
            await set_theme(uow, actor, app.state.themes, OK)  # type: ignore[attr-defined]
            raise RuntimeError("boom after the write")

    with pytest.raises(RuntimeError):
        asyncio.run(failing())
    assert _stored(theme_settings.database_url) == before


def test_deny_all_writes_nothing(themed: TestClient, theme_settings: Settings, actor: Actor) -> None:
    app = themed.app
    before = _stored(theme_settings.database_url)

    async def denied() -> None:
        async with UnitOfWork(app.state.sessionmaker, DenyAllPolicy(), theme_settings) as uow:  # type: ignore[attr-defined]
            await set_theme(uow, actor, app.state.themes, OK)  # type: ignore[attr-defined]

    with pytest.raises(PolicyDeniedError):
        asyncio.run(denied())
    assert _stored(theme_settings.database_url) == before
