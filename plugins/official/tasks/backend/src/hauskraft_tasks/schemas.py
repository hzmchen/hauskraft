# SPDX-License-Identifier: MIT
"""Tasks API models (M0S-E07-02). Unknown fields are rejected (422)."""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

# PostgreSQL text cannot hold NUL bytes; reject them as 422 instead of failing the insert.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\x00]*$")]
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _iso_date_only(value: object) -> object:
    """Accept only ``YYYY-MM-DD`` (or a date object), never numbers or timestamps coerced into a date."""
    if value is None or isinstance(value, dt.date):
        return value
    if isinstance(value, str) and ISO_DATE.match(value):
        return value
    raise ValueError("due_on must be a date in YYYY-MM-DD format")


DueOn = Annotated[dt.date | None, BeforeValidator(_iso_date_only)]
Status = Literal["open", "done", "all"]
Sort = Literal["created_at", "-created_at", "due_on", "-due_on"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(_In):
    title: Title
    due_on: DueOn = None


class TaskPatch(_In):
    """Only fields that are present change; ``due_on: null`` clears the due date."""

    title: Title | None = None
    due_on: DueOn = None
    done: Annotated[bool | None, Field(strict=True)] = None
    version: Annotated[int, Field(ge=1)] | None = None


class UserRef(BaseModel):
    id: uuid.UUID
    display_name: str


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    done: bool
    done_at: dt.datetime | None
    due_on: dt.date | None
    data_class: str
    version: int
    created_by: UserRef
    updated_by: UserRef
    created_at: dt.datetime
    updated_at: dt.datetime


class TaskPage(BaseModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int
