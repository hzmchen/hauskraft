# SPDX-License-Identifier: AGPL-3.0-or-later
"""Setup API models (contract: docs/backlog/m1-star/E03-first-run-setup.md)."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from hauskraft_core.auth.schemas import DisplayName, Username
from hauskraft_core.household.schemas import HouseholdName, Locale


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetupStatus(_Model):
    required: bool = Field(description="True while there is no account yet.")


class SetupHousehold(_Model):
    name: HouseholdName
    timezone: Annotated[str, Field(max_length=64)]  # unknown names: 422 invalid_timezone
    locale: Locale


class SetupOwner(_Model):
    username: Username
    display_name: DisplayName
    password: Annotated[str, Field(min_length=1, max_length=1024)]  # the policy answers 422 password_policy


class SetupIn(_Model):
    household: SetupHousehold
    owner: SetupOwner
