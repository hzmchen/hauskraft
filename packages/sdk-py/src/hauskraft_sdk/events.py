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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    model_serializer,
    model_validator,
)

from hauskraft_sdk.data_classes import DataClass

ReverseDnsId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(\.[a-z0-9-]+)+$")]
ThemeId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(\.[a-z0-9-]+)+(:[a-z0-9-]+)?$")]
Username = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{1,31}$")]
DisplayName = Annotated[str, Field(min_length=1, max_length=80)]
Role = Literal["owner", "adult"]
"""The roles that exist in M1* (ADR 0016)."""
HouseholdName = Annotated[str, Field(min_length=1, max_length=80)]
TimeZoneName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)*$")]
Locale = Literal["en", "de"]
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


class UserRef(_Strict):
    """An account after the change (ADR 0018). Never carries a password, hash or session."""

    id: UUID
    username: Username
    display_name: DisplayName
    role: Role


class Change[T](_Strict):
    from_: Annotated[T, Field(alias="from")]
    to: T

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)


class _Changes(_Strict):
    """Changed fields only: at least one, and unchanged fields are omitted when serialised."""

    @model_validator(mode="after")
    def _at_least_one(self) -> _Changes:
        if all(getattr(self, name) is None for name in type(self).model_fields):
            raise ValueError("at least one change is required")
        return self

    @model_serializer(mode="wrap")
    def _omit_unchanged(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        return {k: v for k, v in handler(self).items() if v is not None}


class UserChanges(_Changes):
    display_name: Change[DisplayName] | None = None
    role: Change[Role] | None = None


class UserData(_Strict):
    """Data of hauskraft.user.created, .deactivated, .reactivated, .password_reset and .password_changed."""

    user: UserRef


class UserUpdatedData(_Strict):
    user: UserRef
    changes: UserChanges


class HouseholdChanges(_Changes):
    name: Change[HouseholdName] | None = None
    timezone: Change[TimeZoneName] | None = None
    locale: Change[Locale] | None = None


class HouseholdChangedData(_Strict):
    changes: HouseholdChanges


DATA_MODELS: dict[str, type[BaseModel]] = {
    "hauskraft.task.created": TaskCreatedData,
    "hauskraft.task.updated": TaskUpdatedData,
    "hauskraft.task.completed": TaskCompletedData,
    "hauskraft.task.deleted": TaskDeletedData,
    "hauskraft.plugin.toggled": PluginToggledData,
    "hauskraft.settings.theme_changed": ThemeChangedData,
    "hauskraft.user.created": UserData,
    "hauskraft.user.updated": UserUpdatedData,
    "hauskraft.user.deactivated": UserData,
    "hauskraft.user.reactivated": UserData,
    "hauskraft.user.password_reset": UserData,
    "hauskraft.user.password_changed": UserData,
    "hauskraft.settings.household_changed": HouseholdChangedData,
}

DATA_SCHEMA_URL = "https://hauskraft.dev/schema/events/{suffix}/v1.json"


def data_schema_url(event_type: str) -> str:
    """The `dataschema` URL for a Hauskraft event type, e.g. hauskraft.task.created."""
    return DATA_SCHEMA_URL.format(suffix=event_type.removeprefix("hauskraft."))
