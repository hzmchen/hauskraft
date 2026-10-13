# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-memory theme registry (M0S-E13-03).

Built once at startup from the theme plugins the loader hands over: every theme is validated and either
compiled or kept with its errors. The active theme falls back to the built-in Default when the chosen one is
missing or invalid; readiness fails only when Default itself is broken.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.db.models import DeploymentSetting
from hearthos_core.health import register_check
from hearthos_core.logging import get_logger
from hearthos_core.plugins.manifests import DiscoveredManifest
from hearthos_core.themes.model import ThemeReport
from hearthos_core.themes.validate import validate_theme

BUILTIN_DEFAULT = "org.hearthos.theme.default"
THEME_SETTING = "theme_id"

_log = get_logger("hearthos.themes")


class IssueOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    path: str


class Swatches(BaseModel):
    model_config = ConfigDict(extra="forbid")
    light: list[str]
    dark: list[str]


class NavigationStyles(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wide: str
    narrow: str


class ThemePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    swatches: Swatches
    navigation: NavigationStyles
    density: str
    widget_chrome: str


class ThemeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme_id: str
    name: str
    description: str
    version: str
    authors: list[str]
    licence: str
    origin: Literal["builtin", "installed"]
    valid: bool
    errors: list[IssueOut]
    warnings: list[IssueOut]
    active: bool
    preview: ThemePreview


@dataclass
class ThemeRegistry:
    default_id: str = BUILTIN_DEFAULT
    reports: dict[str, ThemeReport] = field(default_factory=dict)
    origins: dict[str, Literal["builtin", "installed"]] = field(default_factory=dict)
    _fallbacks_logged: set[str] = field(default_factory=set)

    def add(self, report: ThemeReport, origin: Literal["builtin", "installed"]) -> None:
        if report.theme_id in self.reports:
            _log.warning("theme.duplicate_id", theme_id=report.theme_id, folder=str(report.folder))
            return
        self.reports[report.theme_id] = report
        self.origins[report.theme_id] = origin
        if report.valid:
            _log.info("theme.loaded", theme_id=report.theme_id, warnings=len(report.warnings))
        else:
            _log.warning("theme.invalid", theme_id=report.theme_id, codes=sorted({i.code for i in report.errors}))

    def get(self, theme_id: str) -> ThemeReport | None:
        return self.reports.get(theme_id)

    def fallback(self) -> ThemeReport | None:
        """Default (configured, then built-in), else nothing: the shell then runs on its baked-in styles."""
        for candidate in (self.default_id, BUILTIN_DEFAULT):
            report = self.reports.get(candidate)
            if report is not None and report.valid:
                return report
        return None

    def resolve(self, requested: str | None) -> ThemeReport | None:
        """The theme to serve for a stored choice; logs ``theme.fallback`` with reasons when it cannot be used."""
        if requested is None:
            requested = self.default_id
        report = self.reports.get(requested)
        if report is not None and report.valid:
            return report
        chosen = self.fallback()
        if requested in self._fallbacks_logged:  # the API resolves on every request; say it once
            return chosen
        self._fallbacks_logged.add(requested)
        reasons = ["not installed"] if report is None else [f"{i.code}: {i.message}" for i in report.errors]
        _log.warning("theme.fallback", requested=requested, served=chosen.theme_id if chosen else None, reasons=reasons)
        return chosen

    def summary(self, report: ThemeReport, active_id: str | None) -> ThemeSummary:
        manifest, theme = report.manifest, report.theme
        layout = theme.get("layout") or {}
        navigation = layout.get("navigation") or {}
        return ThemeSummary(
            theme_id=report.theme_id,
            name=report.name,
            description=str(theme.get("description") or manifest.get("description") or ""),
            version=report.version,
            authors=[_author(a) for a in manifest.get("authors") or []],
            licence=str(manifest.get("license") or manifest.get("licence") or ""),
            origin=self.origins.get(report.theme_id, "installed"),
            valid=report.valid,
            errors=[IssueOut(**i.as_dict()) for i in report.errors],
            warnings=[IssueOut(**i.as_dict()) for i in report.warnings],
            active=report.theme_id == active_id,
            preview=ThemePreview(
                swatches=Swatches(light=report.preview.get("light", []), dark=report.preview.get("dark", [])),
                navigation=NavigationStyles(
                    wide=str(navigation.get("wide", "")), narrow=str(navigation.get("narrow", ""))
                ),
                density=str(layout.get("density", "")),
                widget_chrome=str(((theme.get("components") or {}).get("widget") or {}).get("chrome", "")),
            ),
        )

    def summaries(self, active_id: str | None) -> list[ThemeSummary]:
        return [self.summary(r, active_id) for _, r in sorted(self.reports.items())]


def _author(author: Any) -> str:
    return str(author.get("name", "")) if isinstance(author, dict) else str(author)


def _origin(found: DiscoveredManifest) -> Literal["builtin", "installed"]:
    return "builtin" if found.folder.parent.name == "builtin" and found.id.startswith("org.hearthos.") else "installed"


def build_registry(found: Iterable[DiscoveredManifest], default_id: str = BUILTIN_DEFAULT) -> ThemeRegistry:
    registry = ThemeRegistry(default_id=default_id)
    for item in found:
        themes = ((item.manifest.get("contributes") or {}).get("themes")) or [None]
        for entry in themes:
            key = entry.get("id") if isinstance(entry, dict) else None
            registry.add(validate_theme(item.folder, key), _origin(item))
    return registry


async def stored_theme_id(session: AsyncSession) -> str | None:
    value = await session.scalar(select(DeploymentSetting.value).where(DeploymentSetting.key == THEME_SETTING))
    return str(value) if isinstance(value, str) else None


def install(app: FastAPI) -> None:
    """Validate and compile every theme handed over by the plugin loader; register the ``theme`` check."""
    registry = build_registry(app.state.theme_manifests, app.state.settings.default_theme)
    app.state.themes = registry

    async def theme() -> tuple[bool, str]:
        default = registry.get(BUILTIN_DEFAULT)
        if default is None:
            return False, f"built-in theme {BUILTIN_DEFAULT} is not installed"
        if not default.valid:
            return False, f"built-in theme {BUILTIN_DEFAULT} is invalid: " + ", ".join(
                sorted({i.code for i in default.errors})
            )
        invalid = sum(1 for r in registry.reports.values() if not r.valid)
        return True, f"{len(registry.reports) - invalid} valid, {invalid} invalid"

    register_check(app, "theme", theme)


async def log_active_theme(app: FastAPI) -> None:
    """At startup: resolve the stored choice once so an unusable theme is logged as ``theme.fallback``."""
    try:
        async with app.state.sessionmaker() as session:
            requested = await stored_theme_id(session)
    except Exception as exc:  # readiness reports the database problem
        _log.warning("theme.setting_unreadable", error_type=type(exc).__name__)
        requested = None
    app.state.themes.resolve(requested)
