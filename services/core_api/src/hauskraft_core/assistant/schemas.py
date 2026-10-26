# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assistant settings API models (contract: docs/backlog/m2-star/E03-model-endpoint-and-settings.md)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from hauskraft_core.assistant.settings import AssistantConfig
from hauskraft_core.db.models import AssistantAction
from hauskraft_sdk.data_classes import DataClass

NO_NUL = r"^[^\x00]*$"
BaseUrl = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500, pattern=NO_NUL)]
ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=NO_NUL)]
ApiKey = Annotated[str, StringConstraints(min_length=1, max_length=500, pattern=NO_NUL)]
ToolName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")]
Locality = Literal["cloud", "local"]
KeyStatus = Literal["ok", "missing", "needs_reentry"]


class AssistantChatSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str | None
    model: str | None
    api_key_set: bool
    api_key_hint: str | None = Field(
        description="The saved key's last four characters; the key itself is never returned."
    )
    api_key_status: KeyStatus
    locality: Locality
    max_data_class: DataClass
    temperature: float | None
    max_tokens: int | None
    parallel_tool_calls: bool | None


class Prices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_per_million: float | None
    output_per_million: float | None
    currency: Literal["EUR"] = "EUR"


class AssistantSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    chat: AssistantChatSettings
    tools_disabled: list[str]
    prices: Prices

    @classmethod
    def of(cls, config: AssistantConfig) -> AssistantSettings:
        c = config.chat
        return cls(
            configured=config.configured,
            chat=AssistantChatSettings.model_validate(
                {
                    "base_url": c.base_url,
                    "model": c.model,
                    "api_key_set": c.key_status != "missing",
                    "api_key_hint": c.key_hint,
                    "api_key_status": c.key_status,
                    "locality": c.locality,
                    "max_data_class": c.max_data_class,
                    "temperature": c.temperature,
                    "max_tokens": c.max_tokens,
                    "parallel_tool_calls": c.parallel_tool_calls,
                }
            ),
            tools_disabled=list(config.tools_disabled),
            prices=Prices(
                input_per_million=config.prices["input_per_million"],
                output_per_million=config.prices["output_per_million"],
            ),
        )


class AssistantChatPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: BaseUrl | None = None
    model: ModelName | None = None
    api_key: ApiKey | None = Field(default=None, description="Write-only.")
    locality: Locality | None = None
    max_data_class: DataClass | None = None
    temperature: Annotated[float, Field(ge=0, le=2)] | None = None
    max_tokens: Annotated[int, Field(ge=1, le=200_000)] | None = None
    parallel_tool_calls: bool | None = None

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> Self:
        for name in ("base_url", "model", "api_key", "locality", "max_data_class"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null; DELETE /assistant/settings/chat removes the endpoint")
        return self

    def sent(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.model_fields_set}


class PricesPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_per_million: Annotated[float, Field(ge=0)] | None = None
    output_per_million: Annotated[float, Field(ge=0)] | None = None

    def sent(self) -> dict[str, float | None]:
        return {name: getattr(self, name) for name in self.model_fields_set}


class AssistantSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: AssistantChatPatch | None = None
    tools_disabled: Annotated[list[ToolName], Field(max_length=500)] | None = None
    prices: PricesPatch | None = None


class AssistantStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool


# ---------------------------------------------------------------- conversations and runs (M2S-E04)
class Conversation(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    title: str | None = Field(description="The first message, cut to 80 characters; null before it.")
    created_at: dt.datetime
    updated_at: dt.datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    text: str
    run_id: uuid.UUID | None
    created_at: dt.datetime


class RecordRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    id: str
    label: str


class ActionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    tool: str
    status: Literal["done", "failed", "denied", "undone"]
    summary_key: str | None = Field(description="An i18n key of the tool's plugin, rendered with record.label.")
    record: RecordRef | None
    undo_available: bool
    error_code: str | None


def action_out(action: AssistantAction) -> ActionOut:
    """An action row as the API shows it; Undo is offered while a done action keeps its inverse."""
    return ActionOut.model_validate(
        {
            "id": action.id,
            "run_id": action.run_id,
            "tool": action.tool,
            "status": action.status,
            "summary_key": action.summary_key,
            "record": action.record,
            "undo_available": action.status == "done" and action.undo is not None,
            "error_code": action.error_code,
        }
    )


class ConversationDetail(Conversation):
    messages: list[MessageOut]
    actions: list[ActionOut]
