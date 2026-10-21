# SPDX-License-Identifier: MIT
"""Typed event contracts (M0S-E10-01). Mirrors packages/schemas/events/*.schema.json.

The envelope is CloudEvents 1.0.2 structured JSON. The Hauskraft extension attributes are spelled
``dataclass`` and ``actorid`` because CloudEvents attribute names allow only lower-case letters and
digits (decision D1); payloads and database columns keep ``data_class``.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, StringConstraints, model_serializer

from hauskraft_sdk.data_classes import DataClass

ReverseDnsId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(\.[a-z0-9-]+)+$")]
ThemeId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(\.[a-z0-9-]+)+(:[a-z0-9-]+)?$")]
CORE_SOURCE = "dev.hauskraft.core"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CloudEvent(_Strict):
    """CloudEvents 1.0.2 envelope with Hauskraft extensions."""

    specversion: Literal["1.0"] = "1.0"
    id: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1)]
    type: Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(\.[a-z0-9_]+)+$")]
    subject: str | None = None
    time: dt.datetime | None = None
    datacontenttype: str | None = "application/json"
    dataschema: str | None = None
    dataclass: DataClass
    actorid: str | None = None
    data: Any = None


class TaskSnapshot(_Strict):
    id: UUID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    done: bool
    due_on: dt.date | None
    version: Annotated[int, Field(ge=1)]


class TaskCreatedData(_Strict):
    task: TaskSnapshot


class TaskChanges(_Strict):
    """Changed fields as ``(old, new)``; unchanged fields are omitted when serialised."""

    title: tuple[str, str] | None = None
    due_on: tuple[dt.date | None, dt.date | None] | None = None
    done: tuple[bool, bool] | None = None

    @model_serializer(mode="wrap")
    def _omit_unchanged(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        return {k: v for k, v in handler(self).items() if v is not None}


class TaskUpdatedData(_Strict):
    task: TaskSnapshot
    changes: TaskChanges


class TaskCompletedData(_Strict):
    task: TaskSnapshot
    completed_at: dt.datetime


class TaskDeletedData(_Strict):
    task: TaskSnapshot


class PluginToggledData(_Strict):
    plugin_id: ReverseDnsId
    enabled: bool


class ThemeChangedData(_Strict):
    from_: Annotated[ThemeId, Field(alias="from")]
    to: ThemeId

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)


DATA_MODELS: dict[str, type[BaseModel]] = {
    "hauskraft.task.created": TaskCreatedData,
    "hauskraft.task.updated": TaskUpdatedData,
    "hauskraft.task.completed": TaskCompletedData,
    "hauskraft.task.deleted": TaskDeletedData,
    "hauskraft.plugin.toggled": PluginToggledData,
    "hauskraft.settings.theme_changed": ThemeChangedData,
}

DATA_SCHEMA_URL = "https://hauskraft.dev/schema/events/{suffix}/v1.json"


def data_schema_url(event_type: str) -> str:
    """The `dataschema` URL for a Hauskraft event type, e.g. hauskraft.task.created."""
    return DATA_SCHEMA_URL.format(suffix=event_type.removeprefix("hauskraft."))
