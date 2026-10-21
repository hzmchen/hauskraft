# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transactional outbox writer (M0S-E10-02).

``emit`` appends one CloudEvent to the active unit of work: an ``outbox_events`` row with a UUIDv7 id, the
source, the actor last authorized in that unit of work (``actorid``), ``time`` = now (UTC) and the full
envelope. Rolling back the unit of work removes the event with the write. Outside production every
envelope and its data are validated against ``packages/schemas/events``.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from hearthos_core import schemas
from hearthos_core.db.ids import new_id
from hearthos_core.db.models import OutboxEvent
from hearthos_core.uow import current_uow
from hearthos_sdk import DataClass
from hearthos_sdk.events import CORE_SOURCE, data_schema_url

ENVELOPE_SCHEMA = "events/cloudevent.schema.json"


class OutsideUnitOfWorkError(RuntimeError):
    """``emit`` was called without an active unit of work."""


class EventValidationError(ValueError):
    """An event does not match its schema (only checked when ``HEARTHOS_VALIDATE_EVENTS`` is on)."""


def _data_schema(event_type: str) -> str:
    return f"events/{event_type.removeprefix('hearthos.')}.data.schema.json"


def _json(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json", by_alias=True)
    return jsonable_encoder(data)


def build_envelope(
    event_id: uuid.UUID,
    event_type: str,
    subject: str | None,
    data: Any,
    data_class: DataClass | str,
    source: str,
    actor_id: str | None,
    time: dt.datetime,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "specversion": "1.0",
        "id": str(event_id),
        "source": source,
        "type": event_type,
        "time": time.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "datacontenttype": "application/json",
        "dataclass": str(DataClass(data_class)),
        "data": _json(data),
    }
    if subject is not None:
        envelope["subject"] = subject
    if schemas.exists(_data_schema(event_type)):
        envelope["dataschema"] = data_schema_url(event_type)
    if actor_id is not None:
        envelope["actorid"] = actor_id
    return envelope


def validate(envelope: dict[str, Any]) -> None:
    problems = schemas.errors(ENVELOPE_SCHEMA, envelope)
    data_schema = _data_schema(envelope["type"])
    if schemas.exists(data_schema):
        problems += [f"data/{p}" for p in schemas.errors(data_schema, envelope.get("data"))]
    if problems:
        raise EventValidationError(f"{envelope['type']}: " + "; ".join(problems))


async def emit(
    event_type: str, subject: str | None, data: Any, data_class: DataClass | str, *, source: str = CORE_SOURCE
) -> str:
    """Append one event to the active unit of work and return its id."""
    try:
        uow = current_uow()
    except LookupError:
        raise OutsideUnitOfWorkError(f"cannot emit {event_type} outside a unit of work") from None
    event_id = new_id()
    time = dt.datetime.now(dt.UTC)
    actor_id = uow.actor.id if uow.actor is not None else None
    envelope = build_envelope(event_id, event_type, subject, data, data_class, source, actor_id, time)
    if uow.settings.validate_events:
        validate(envelope)
    uow.session.add(
        OutboxEvent(
            id=event_id,
            type=event_type,
            source=source,
            subject=subject,
            data_class=envelope["dataclass"],
            actor_id=uuid.UUID(actor_id) if actor_id and uow.actor and uow.actor.kind == "user" else None,
            time=time,
            envelope=envelope,
        )
    )
    await uow.session.flush()
    return str(event_id)
