# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E13-03: the theme registry built at startup, fallback to Default, and the ``theme`` readiness check."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import FastAPI

from hearthos_core.app import create_app
from hearthos_core.settings import Settings
from hearthos_core.themes.registry import BUILTIN_DEFAULT
from tests.theme_helpers import FIXTURES
from tests.theme_helpers import builtin_default as _builtin_default

pytestmark = pytest.mark.unit


def _app(tmp_path: Path, theme_paths: list[Path], default_theme: str = BUILTIN_DEFAULT) -> FastAPI:
    return create_app(
        Settings(
            env="test",
            plugin_paths=[tmp_path / "plugins"],
            theme_paths=theme_paths,
            default_theme=default_theme,
            relay_enabled=False,
            database_url="postgresql+psycopg://x:y@127.0.0.1:9/z",
        )
    )


def _theme_check(app: FastAPI) -> tuple[bool, str]:
    result: tuple[bool, str] = asyncio.run(app.state.readiness_checks["theme"]())
    return result


def test_every_theme_is_validated_and_valid_ones_compiled(tmp_path: Path) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path), FIXTURES])
    registry = app.state.themes
    assert registry.get(BUILTIN_DEFAULT).css.startswith(f"/* {BUILTIN_DEFAULT} ")
    broken = registry.get("org.example.theme.invalid-low-contrast")
    assert not broken.valid
    assert broken.css is None
    assert {i.code for i in broken.errors} == {"contrast.text"}
    assert len(registry.reports) == len(json.loads((FIXTURES / "expected.json").read_text())["themes"]) + 1


def test_broken_theme_manifests_do_not_fail_the_plugins_check(tmp_path: Path) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path), FIXTURES])
    assert "org.example.theme.invalid-manifest-capabilities" not in app.state.plugin_load_errors
    report = app.state.themes.get("org.example.theme.invalid-manifest-capabilities")
    assert {i.code for i in report.errors} == {"manifest.invalid"}


def test_summary_shape(tmp_path: Path) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path), FIXTURES])
    summaries = {s.theme_id: s for s in app.state.themes.summaries(BUILTIN_DEFAULT)}
    default = summaries[BUILTIN_DEFAULT]
    assert default.origin == "builtin"
    assert default.active
    assert default.valid
    assert default.preview.swatches.light
    assert all(s.startswith("rgb(") for s in default.preview.swatches.dark)
    fixture = summaries["org.example.theme.invalid-border-contrast"]
    assert fixture.origin == "installed"
    assert not fixture.active
    assert not fixture.valid
    assert fixture.errors[0].code == "contrast.non_text"
    assert fixture.errors[0].path.startswith("tokens.dark.json#/")


@pytest.mark.parametrize(
    ("requested", "served"),
    [
        (None, BUILTIN_DEFAULT),
        ("org.example.theme.warn-no-preview", "org.example.theme.warn-no-preview"),
        ("org.example.theme.invalid-alias-cycle", BUILTIN_DEFAULT),
        ("org.example.theme.not-installed", BUILTIN_DEFAULT),
    ],
)
def test_unusable_choice_falls_back_to_default(tmp_path: Path, requested: str | None, served: str) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path), FIXTURES])
    assert app.state.themes.resolve(requested).theme_id == served


def test_configured_default_theme_is_used_when_nothing_is_stored(tmp_path: Path) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path), FIXTURES], default_theme="org.example.theme.warn-no-licence")
    assert app.state.themes.resolve(None).theme_id == "org.example.theme.warn-no-licence"


def test_readiness_passes_with_invalid_installed_themes(tmp_path: Path) -> None:
    ok, detail = _theme_check(_app(tmp_path, [_builtin_default(tmp_path), FIXTURES]))
    assert ok, detail


def test_readiness_fails_when_builtin_default_is_invalid(tmp_path: Path) -> None:
    app = _app(tmp_path, [_builtin_default(tmp_path, source="invalid-low-contrast")])
    ok, detail = _theme_check(app)
    assert not ok
    assert "contrast.text" in detail
    assert app.state.themes.resolve(None) is None


def test_readiness_fails_without_builtin_default(tmp_path: Path) -> None:
    ok, detail = _theme_check(_app(tmp_path, [FIXTURES]))
    assert not ok
    assert "not installed" in detail
