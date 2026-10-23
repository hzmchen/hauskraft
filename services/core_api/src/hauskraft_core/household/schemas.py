# SPDX-License-Identifier: AGPL-3.0-or-later
"""Household API models (contract: docs/backlog/m1-star/E04-household-settings.md)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from hauskraft_core.household.service import Household

NO_NUL = r"^[^\x00]*$"
HouseholdName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, pattern=NO_NUL)]
Locale = Literal["en", "de"]


class HouseholdOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    timezone: str = Field(description="IANA time zone name; it decides what 'today' means for due dates.")
    locale: Locale = Field(description="Default language for new members.")

    @classmethod
    def of(cls, household: Household) -> HouseholdOut:
        return cls.model_validate(household, from_attributes=True)


class HouseholdPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: HouseholdName | None = None
    timezone: Annotated[str, Field(max_length=64, pattern=NO_NUL)] | None = None  # unknown names: 422 invalid_timezone
    locale: Locale | None = None
