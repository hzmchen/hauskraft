# SPDX-License-Identifier: AGPL-3.0-or-later
"""Environment-driven configuration (M0S-E03-01). Every variable uses the HAUSKRAFT_ prefix."""

from __future__ import annotations

import secrets
import zoneinfo
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_SECRET_LENGTH = 32


def _split_csv(value: Any) -> Any:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAUSKRAFT_", extra="ignore", validate_default=True)

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://hauskraft:hauskraft@localhost:5432/hauskraft"
    secret_key: SecretStr | None = None
    cookie_secure: bool = False
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8080", "http://localhost:5173"]
    )
    plugin_paths: Annotated[list[Path], NoDecode] = Field(default_factory=lambda: [Path("plugins/official")])
    theme_paths: Annotated[list[Path], NoDecode] = Field(default_factory=lambda: [Path("themes/builtin")])
    default_theme: str = "dev.hauskraft.theme.default"
    default_timezone: str = "Europe/Berlin"  # the household time zone until an owner sets one (M1S-E04-01)
    policy: Literal["roles", "noop", "deny_all"] = "roles"
    auth_provider: Literal["local", "oidc"] = "local"
    seed_demo: bool = False
    relay_enabled: bool = True
    validate_events: bool | None = None
    otel_enabled: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("default_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        if value not in zoneinfo.available_timezones():
            raise ValueError(f"HAUSKRAFT_DEFAULT_TIMEZONE {value!r} is not a time zone this system knows")
        return value

    @field_validator("allowed_origins", "plugin_paths", "theme_paths", mode="before")
    @classmethod
    def _csv(cls, value: Any) -> Any:
        return _split_csv(value)

    @model_validator(mode="after")
    def _environment_rules(self) -> Self:
        if self.env == "production":
            if self.secret_key is None:
                raise ValueError("HAUSKRAFT_SECRET_KEY is required when HAUSKRAFT_ENV=production")
            if len(self.secret_key.get_secret_value()) < MIN_SECRET_LENGTH:
                raise ValueError(f"HAUSKRAFT_SECRET_KEY must have at least {MIN_SECRET_LENGTH} characters")
        elif self.secret_key is None:
            # Development and tests get an ephemeral key; sessions do not survive a restart.
            self.secret_key = SecretStr(secrets.token_urlsafe(48))
        if self.validate_events is None:
            self.validate_events = self.env != "production"
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
