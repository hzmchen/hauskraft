# SPDX-License-Identifier: MIT
"""Tasks API models (M0S-E07-02). Unknown fields are rejected (422)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Status = Literal["open", "done", "all"]
Sort = Literal["created_at", "-created_at", "due_on", "-due_on"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(_In):
    title: Title
    due_on: dt.date | None = None


class TaskPatch(_In):
    """Only fields that are present change; ``due_on: null`` clears the due date."""

    title: Title | None = None
    due_on: dt.date | None = None
    done: bool | None = None
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
