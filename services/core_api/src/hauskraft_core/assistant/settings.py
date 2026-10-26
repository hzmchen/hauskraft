# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assistant settings (M2S-E03-02, ADR 0021).

Deployment settings under ``assistant.*``, keyed by purpose: ``assistant.endpoints.chat.*`` for the Chat Completions
endpoint (``transcription`` and ``speech`` can be siblings later), ``assistant.tools_disabled`` and
``assistant.prices``. The API key is stored sealed (``secret_box``) and never leaves this module in plain text except
to call the endpoint. Writes call ``authorize()`` first and emit one ``hauskraft.settings.assistant_changed`` event
that lists the changed field paths, never values.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.models import DeploymentSetting
from hauskraft_core.events.outbox import emit
from hauskraft_core.secret_box import SecretBoxError, seal, unseal
from hauskraft_core.settings import Settings
from hauskraft_core.settings_store import repository
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk import Actor, ResourceRef
from hauskraft_sdk.errors import HauskraftError
from hauskraft_sdk.events import AssistantChangedData

CHAT_PREFIX = "assistant.endpoints.chat."
CHAT_FIELDS = (
    "base_url",
    "model",
    "api_key",
    "locality",
    "max_data_class",
    "temperature",
    "max_tokens",
    "parallel_tool_calls",
)
TOOLS_KEY = "assistant.tools_disabled"
PRICES_KEY = "assistant.prices"
KEY_CONTEXT = CHAT_PREFIX + "api_key"
SUBJECT = "setting/assistant"
DEFAULTS: dict[str, Any] = {"locality": "cloud", "max_data_class": "household"}

KeyStatus = Literal["ok", "missing", "needs_reentry"]


class InvalidBaseUrlError(HauskraftError):
    status = 422
    code = "invalid_base_url"
    title = "Invalid base URL"


class UnknownToolError(HauskraftError):
    status = 422
    code = "unknown_tool"
    title = "Unknown tool"


@dataclass(frozen=True, slots=True)
class ChatEndpoint:
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None  # plain text, only in memory
    key_status: KeyStatus = "missing"
    locality: str = "cloud"
    max_data_class: str = "household"
    temperature: float | None = None
    max_tokens: int | None = None
    parallel_tool_calls: bool | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model and self.api_key)

    @property
    def key_hint(self) -> str | None:
        return f"…{self.api_key[-4:]}" if self.api_key else None


@dataclass(frozen=True, slots=True)
class AssistantConfig:
    chat: ChatEndpoint = field(default_factory=ChatEndpoint)
    tools_disabled: tuple[str, ...] = ()
    prices: dict[str, float | None] = field(
        default_factory=lambda: {"input_per_million": None, "output_per_million": None}
    )

    @property
    def configured(self) -> bool:
        return self.chat.configured


def check_base_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise InvalidBaseUrlError("The base URL must be an absolute http or https URL.")


def _secret(settings: Settings) -> str:
    if settings.secret_key is None:  # pragma: no cover - Settings fills it in every environment
        raise RuntimeError("HAUSKRAFT_SECRET_KEY is not set")
    return settings.secret_key.get_secret_value()


async def _stored(session: AsyncSession, *, for_update: bool = False) -> dict[str, Any]:
    query = select(DeploymentSetting.key, DeploymentSetting.value).where(DeploymentSetting.key.like("assistant.%"))
    return dict((await session.execute(query.with_for_update() if for_update else query)).all())


def _config(stored: dict[str, Any], settings: Settings) -> AssistantConfig:
    chat: dict[str, Any] = {name: stored.get(CHAT_PREFIX + name, DEFAULTS.get(name)) for name in CHAT_FIELDS}
    sealed = chat.pop("api_key")
    key: str | None = None
    status: KeyStatus = "missing"
    if isinstance(sealed, str) and sealed:
        try:
            key, status = unseal(sealed, _secret(settings), KEY_CONTEXT), "ok"
        except SecretBoxError:
            status = "needs_reentry"
    prices = stored.get(PRICES_KEY) or {}
    return AssistantConfig(
        chat=ChatEndpoint(**chat, api_key=key, key_status=status),
        tools_disabled=tuple(stored.get(TOOLS_KEY) or ()),
        prices={
            "input_per_million": prices.get("input_per_million"),
            "output_per_million": prices.get("output_per_million"),
        },
    )


async def read_config(session: AsyncSession, settings: Settings) -> AssistantConfig:
    return _config(await _stored(session), settings)


async def _authorize(uow: UnitOfWork, actor: Actor) -> None:
    await uow.authorize(
        actor, "assistant.configure", ResourceRef("DeploymentSetting", "assistant"), "household", "settings:write"
    )


async def update_settings(
    uow: UnitOfWork,
    actor: Actor,
    settings: Settings,
    *,
    chat: dict[str, Any] | None = None,
    tools_disabled: list[str] | None = None,
    prices: dict[str, float | None] | None = None,
    known_tools: set[str] | None = None,
) -> AssistantConfig:
    """Change any subset of the assistant settings (owners only, ``assistant.configure``).

    ``chat`` and ``prices`` hold only the fields the caller sent; ``None`` clears an optional value.
    """
    await _authorize(uow, actor)
    if chat and chat.get("base_url") is not None:
        check_base_url(chat["base_url"])
    if tools_disabled is not None and known_tools is not None:
        unknown = sorted(set(tools_disabled) - known_tools)
        if unknown:
            raise UnknownToolError(f"No such tool: {', '.join(unknown)}.")
    before = await read_config(uow.session, settings)
    await _stored(uow.session, for_update=True)
    updated_by = uuid.UUID(actor.id) if actor.kind == "user" else None
    changed: list[str] = []
    for name, value in (chat or {}).items():
        current = getattr(before.chat, name)
        if name == "api_key":
            if before.chat.key_status == "ok" and value == current:
                continue
            await repository.upsert(uow.session, KEY_CONTEXT, seal(value, _secret(settings), KEY_CONTEXT), updated_by)
        elif value == current:
            continue
        else:
            await repository.upsert(uow.session, CHAT_PREFIX + name, value, updated_by)
        changed.append(f"chat.{name}")
    if tools_disabled is not None and sorted(set(tools_disabled)) != sorted(before.tools_disabled):
        await repository.upsert(uow.session, TOOLS_KEY, sorted(set(tools_disabled)), updated_by)
        changed.append("tools_disabled")
    if prices is not None:
        merged = {**before.prices, **prices}
        if merged != before.prices:
            await repository.upsert(uow.session, PRICES_KEY, merged, updated_by)
            changed.append("prices")
    if changed:
        await _emit(sorted(changed))
    return await read_config(uow.session, settings)


async def remove_chat_endpoint(uow: UnitOfWork, actor: Actor) -> None:
    """Forget the endpoint's base URL, model and key (owners only)."""
    await _authorize(uow, actor)
    keys = [CHAT_PREFIX + name for name in ("base_url", "model", "api_key")]
    result = await uow.session.execute(delete(DeploymentSetting).where(DeploymentSetting.key.in_(keys)))
    if getattr(result, "rowcount", 0):
        await _emit(["chat"])


async def _emit(changed: list[str]) -> None:
    data = AssistantChangedData.model_validate({"changed": changed})
    await emit("hauskraft.settings.assistant_changed", SUBJECT, data.model_dump(mode="json"), "household")
