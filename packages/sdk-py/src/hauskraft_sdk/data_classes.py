# SPDX-License-Identifier: MIT
"""Data classes (spec §5.5, ADR-0008): ordered tags for entities, events and manifests."""

from __future__ import annotations

from enum import StrEnum
from functools import total_ordering


@total_ordering
class DataClass(StrEnum):
    """Ordered from least to most sensitive. ``max()`` of inputs gives the propagated taint."""

    PUBLIC = "public"
    HOUSEHOLD = "household"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    TENANT = "tenant"
    CHILD = "child"
    HEALTH = "health"
    SECRET = "secret"  # noqa: S105 - a data class name, not a credential

    @property
    def rank(self) -> int:
        return _ORDER.index(self)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DataClass):
            return NotImplemented
        return self.rank < other.rank


_ORDER: list[DataClass] = list(DataClass)
