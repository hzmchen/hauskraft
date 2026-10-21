# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validation results shared by the validator, compiler, registry, API and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Issue:
    """One problem or warning. ``path`` points into the theme files, e.g. ``tokens.dark.json#/color/ring``."""

    code: str
    message: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass
class ThemeReport:
    theme_id: str
    folder: Path
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    theme: dict[str, Any] = field(default_factory=dict)
    css_values: dict[str, dict[str, str]] = field(default_factory=dict)  # mode -> token -> CSS value
    preview: dict[str, list[str]] = field(default_factory=dict)
    icon_names: list[str] = field(default_factory=list)
    hash: str = ""
    css: str | None = None

    @property
    def valid(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str, path: str) -> None:
        self.errors.append(Issue(code, message, path))

    def warn(self, code: str, message: str, path: str) -> None:
        self.warnings.append(Issue(code, message, path))

    @property
    def name(self) -> str:
        return str(self.theme.get("name") or self.manifest.get("name") or self.theme_id)

    @property
    def version(self) -> str:
        return str(self.manifest.get("version", "0.0.0"))
