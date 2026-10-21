# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deployment settings services (M0S-E13-04): ``authorize()`` first, one event in the same transaction."""

from __future__ import annotations

import uuid

from hauskraft_core.events.outbox import emit
from hauskraft_core.settings_store import repository
from hauskraft_core.themes.model import ThemeReport
from hauskraft_core.themes.registry import THEME_SETTING, ThemeRegistry
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor, ResourceRef
from hauskraft_sdk.errors import ConflictError, NotFoundError


class UnknownThemeError(NotFoundError):
    code = "unknown_theme"
    title = "Unknown theme"


class ThemeInvalidError(ConflictError):
    def __init__(self, report: ThemeReport) -> None:
        super().__init__(
            "theme_invalid",
            f"{report.theme_id} failed validation and cannot be selected.",
            extra={"errors": [i.as_dict() for i in report.errors]},
        )


async def set_theme(uow: UnitOfWork, actor: Actor, registry: ThemeRegistry, theme_id: str) -> ThemeReport:
    """Make ``theme_id`` the household theme; emits ``hauskraft.settings.theme_changed`` ``{from, to}``."""
    await uow.authorize(
        actor, "settings.theme.set", ResourceRef("DeploymentSetting", THEME_SETTING), "household", "settings:write"
    )
    report = registry.get(theme_id)
    if report is None:
        raise UnknownThemeError(f"No theme {theme_id!r} is installed.")
    if not report.valid:
        raise ThemeInvalidError(report)
    stored = await repository.get_for_update(uow.session, THEME_SETTING)
    if stored == theme_id:
        return report  # already the household theme: nothing written, no event
    previous = registry.resolve(stored if isinstance(stored, str) else None)
    updated_by = uuid.UUID(actor.id) if actor.kind == "user" else None
    await repository.upsert(uow.session, THEME_SETTING, theme_id, updated_by)
    await emit(
        "hauskraft.settings.theme_changed",
        f"settings/{THEME_SETTING}",
        {"from": previous.theme_id if previous else registry.default_id, "to": theme_id},
        "household",
    )
    return report
