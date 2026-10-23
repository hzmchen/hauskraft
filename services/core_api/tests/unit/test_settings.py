# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-01: environment-driven settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hauskraft_core.settings import Settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in list(os.environ):
        if key.startswith("HAUSKRAFT_"):
            monkeypatch.delenv(key)


def test_defaults_are_safe_for_development() -> None:
    s = Settings()
    assert s.env == "development"
    assert s.cookie_secure is False
    assert s.policy == "roles"
    assert s.auth_provider == "local"
    assert s.default_theme == "dev.hauskraft.theme.default"
    assert s.secret_key.get_secret_value(), "development gets an ephemeral secret"
    assert s.validate_events is True, "events are validated outside production by default"


def test_reads_hauskraft_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("HAUSKRAFT_SECRET_KEY", "s" * 32)
    monkeypatch.setenv("HAUSKRAFT_ALLOWED_ORIGINS", "http://localhost:8080, http://tablet.lan:8080")
    monkeypatch.setenv("HAUSKRAFT_PLUGIN_PATHS", "plugins/official,/data/plugins")
    monkeypatch.setenv("HAUSKRAFT_THEME_PATHS", "themes/builtin,/data/themes")
    monkeypatch.setenv("HAUSKRAFT_SEED_DEMO", "true")
    monkeypatch.setenv("HAUSKRAFT_RELAY_ENABLED", "false")
    s = Settings()
    assert s.database_url == "postgresql+psycopg://u:p@db:5432/x"
    assert s.secret_key.get_secret_value() == "s" * 32
    assert s.allowed_origins == ["http://localhost:8080", "http://tablet.lan:8080"]
    assert s.plugin_paths == [Path("plugins/official"), Path("/data/plugins")]
    assert s.theme_paths == [Path("themes/builtin"), Path("/data/themes")]
    assert s.seed_demo is True
    assert s.relay_enabled is False


def test_production_requires_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_ENV", "production")
    with pytest.raises(ValidationError, match="HAUSKRAFT_SECRET_KEY"):
        Settings()


def test_production_rejects_a_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_ENV", "production")
    monkeypatch.setenv("HAUSKRAFT_SECRET_KEY", "too-short")
    with pytest.raises(ValidationError, match="32"):
        Settings()


def test_production_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_ENV", "production")
    monkeypatch.setenv("HAUSKRAFT_SECRET_KEY", "p" * 40)
    s = Settings()
    assert s.validate_events is False


@pytest.mark.parametrize(
    ("key", "value"), [("HAUSKRAFT_POLICY", "cedar"), ("HAUSKRAFT_ENV", "staging"), ("HAUSKRAFT_AUTH_PROVIDER", "ldap")]
)
def test_enumerated_settings_reject_unknown_values(monkeypatch: pytest.MonkeyPatch, key: str, value: str) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError):
        Settings()


def test_unknown_hauskraft_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_WEB_PORT", "8080")  # used by Compose, not by the API
    Settings()
