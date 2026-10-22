# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dashboard API models. The grid has 12 columns in every theme (ADR-0012)."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

COLUMNS = 12
Id = Annotated[str, StringConstraints(min_length=1, max_length=200, pattern=r"^[^\x00]*$")]


class DashboardCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    i: Id
    plugin_id: Id
    widget_id: Id
    x: Annotated[int, Field(ge=0, lt=COLUMNS)]
    y: Annotated[int, Field(ge=0, le=10_000)]
    w: Annotated[int, Field(ge=1, le=COLUMNS)]
    h: Annotated[int, Field(ge=1, le=100)]

    @model_validator(mode="after")
    def _inside_grid(self) -> Self:
        if self.x + self.w > COLUMNS:
            raise ValueError(f"cell {self.i!r} ends at column {self.x + self.w}; the grid has {COLUMNS} columns")
        return self


class LayoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Annotated[list[DashboardCell], Field(max_length=100)]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [cell.i for cell in self.layout]
        if len(ids) != len(set(ids)):
            raise ValueError("cell ids must be unique")
        return self


class Dashboard(BaseModel):
    dashboard_id: str
    layout: list[DashboardCell]
