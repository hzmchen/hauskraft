# SPDX-License-Identifier: MIT
"""M0S-E13-04 · Theme API and the deployment-wide theme setting.

Needs the test overlay (deploy/compose/compose.test.yaml) that mounts tests/fixtures/themes.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx
import pytest

from _support.live import API, Api, assert_problem, reachable

pytestmark = [pytest.mark.live, pytest.mark.story("M0S-E13-04")]
DEFAULT = "dev.hauskraft.theme.default"
HACKSPACE = "dev.hauskraft.theme.hackspace"
FIXTURE_OK = "org.example.theme.valid-minimal"
FIXTURE_BAD = "org.example.theme.invalid-low-contrast"


@pytest.fixture
def restore_theme(demo: Api) -> Iterator[None]:
    before = httpx.get(f"{API}/theme").json()["theme_id"]
    yield
    demo.put("/settings/theme", json={"theme_id": before})


def _themes(api: Api) -> dict[str, dict]:
    r = api.get("/themes")
    assert r.status_code == 200, r.text
    return {t["theme_id"]: t for t in r.json()}


def test_active_theme_is_public() -> None:
    reachable()
    r = httpx.get(f"{API}/theme")
    assert r.status_code == 200, r.text
    body = r.json()
    assert {"theme_id", "name", "hash", "css_url", "components", "layout", "icons"} <= set(body)
    assert set(body["layout"]) >= {"navigation", "density", "content_width"}
    assert set(body["icons"]) >= {"sprite_url", "names"}


def test_active_css_has_etag_and_304() -> None:
    reachable()
    r = httpx.get(f"{API}/theme/active.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    etag = r.headers.get("etag")
    assert etag and not etag.startswith("W/"), "strong ETag required"
    assert "--hauskraft-color-background" in r.text and ":root.dark" in r.text
    assert httpx.get(f"{API}/theme/active.css", headers={"If-None-Match": etag}).status_code == 304


def test_theme_list_needs_session(anon: Api) -> None:
    assert anon.get("/themes").status_code == 401


def test_builtins_and_fixtures_are_listed(demo: Api) -> None:
    themes = _themes(demo)
    for theme_id in (DEFAULT, "dev.hauskraft.theme.paper", HACKSPACE, FIXTURE_OK):
        assert theme_id in themes and themes[theme_id]["valid"] is True, themes.get(theme_id)
    assert themes[DEFAULT]["origin"] == "builtin" and themes[FIXTURE_OK]["origin"] == "installed"
    bad = themes.get(FIXTURE_BAD)
    assert bad and bad["valid"] is False and any(e["code"] == "contrast.text" for e in bad["errors"]), bad
    for t in themes.values():
        assert {"theme_id", "name", "version", "valid", "errors", "warnings", "active", "preview"} <= set(t)
    assert sum(t["active"] for t in themes.values()) == 1


def test_switch_theme_for_everyone(demo: Api, alex: Api, restore_theme) -> None:
    before = httpx.get(f"{API}/theme").json()
    r = demo.put("/settings/theme", json={"theme_id": HACKSPACE})
    assert r.status_code == 200, r.text
    after = httpx.get(f"{API}/theme").json()
    assert after["theme_id"] == HACKSPACE and after["hash"] != before["hash"]
    assert after["layout"]["navigation"] == {"wide": "topbar", "narrow": "bottom-tabs"}
    assert _themes(alex)[HACKSPACE]["active"] is True, "the theme applies to every user"


def test_theme_change_is_an_event(demo: Api, restore_theme) -> None:
    demo.put("/settings/theme", json={"theme_id": FIXTURE_OK})
    deadline, hit = time.time() + 15, None
    while time.time() < deadline and hit is None:
        hit = next((i for i in demo.get("/activity", params={"limit": 20}).json()
                    if i["type"] == "hauskraft.settings.theme_changed" and i["data"].get("to") == FIXTURE_OK), None)
        time.sleep(0.5)
    assert hit and hit["actor"]["display_name"] == "Demo Adult", hit


def test_selected_fixture_theme_compiles_safely(demo: Api, restore_theme) -> None:
    assert demo.put("/settings/theme", json={"theme_id": FIXTURE_OK}).status_code == 200
    css = httpx.get(f"{API}/theme/active.css").text
    assert "@font-face" in css and "Fixture Sans" in css
    assert f"/api/v1/theme/assets/{FIXTURE_OK}/" in css
    assert "--hauskraft-color-primary" in css and "--primary" in css, "tokens and shadcn aliases expected"
    font_url = css.split(f"/api/v1/theme/assets/{FIXTURE_OK}/", 1)[1].split('"', 1)[0].split(")", 1)[0]
    asset = httpx.get(f"{API}/theme/assets/{FIXTURE_OK}/{font_url}")
    assert asset.status_code == 200 and asset.content[:4] == b"wOF2"
    assert asset.headers.get("x-content-type-options") == "nosniff"
    assert "immutable" in asset.headers.get("cache-control", "")


@pytest.mark.parametrize("path", ["..%2Fhauskraft.plugin.json", "../../etc/passwd", "%2e%2e/%2e%2e/etc/passwd",
                                  "tokens.light.json"])
def test_assets_only_serve_asset_files(path: str) -> None:
    reachable()
    r = httpx.get(f"{API}/theme/assets/{FIXTURE_OK}/{path}")
    assert r.status_code in (400, 404), f"{path} -> {r.status_code}"


def test_invalid_theme_cannot_be_selected(demo: Api, restore_theme) -> None:
    body = assert_problem(demo.put("/settings/theme", json={"theme_id": FIXTURE_BAD}), 409, "theme_invalid")
    assert body.get("errors"), "the reasons must be returned"


def test_unknown_theme_is_404(demo: Api) -> None:
    assert_problem(demo.put("/settings/theme", json={"theme_id": "org.example.theme.nope"}), 404, "unknown_theme")


def test_switch_needs_csrf(demo: Api) -> None:
    r = demo.http.put("/settings/theme", json={"theme_id": DEFAULT})
    assert_problem(r, 403, "csrf_failed")
