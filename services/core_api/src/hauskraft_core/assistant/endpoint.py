# SPDX-License-Identifier: AGPL-3.0-or-later
"""The configured Chat Completions endpoint (ADR 0021): the Pydantic AI model and the connection test (M2S-E03-04).

Optional model settings (temperature, max_tokens, parallel_tool_calls) are sent only when an owner set them, because
compatible servers differ.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import openai
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from hauskraft_core.assistant.settings import ChatEndpoint
from hauskraft_sdk.errors import HauskraftError

TEST_TIMEOUT_S = 15.0
PING_TOOL = {
    "type": "function",
    "function": {
        "name": "hauskraft_ping",
        "description": "Answers pong. Used only to check that the endpoint accepts tools.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


class AssistantNotConfiguredError(HauskraftError):
    status = 409
    code = "assistant_not_configured"
    title = "The assistant is not set up"


def require_configured(chat: ChatEndpoint) -> ChatEndpoint:
    if not chat.configured:
        raise AssistantNotConfiguredError("An owner has to set up the assistant's endpoint first.")
    return chat


def provider(chat: ChatEndpoint, *, timeout: float = 60.0, max_retries: int = 1) -> OpenAIProvider:
    client = openai.AsyncOpenAI(base_url=chat.base_url, api_key=chat.api_key, timeout=timeout, max_retries=max_retries)
    return OpenAIProvider(openai_client=client)


def chat_model(chat: ChatEndpoint) -> OpenAIChatModel:
    require_configured(chat)
    return OpenAIChatModel(str(chat.model), provider=provider(chat))


def model_settings(chat: ChatEndpoint) -> OpenAIChatModelSettings:
    settings: OpenAIChatModelSettings = {}
    if chat.temperature is not None:
        settings["temperature"] = chat.temperature
    if chat.max_tokens is not None:
        settings["max_tokens"] = chat.max_tokens
    if chat.parallel_tool_calls is not None:
        settings["parallel_tool_calls"] = chat.parallel_tool_calls
    return settings


@dataclass
class ConnectionResult:
    ok: bool = False
    checks: dict[str, bool] = field(
        default_factory=lambda: {"reachable": False, "auth": False, "model": False, "tool_calls": False}
    )
    latency_ms: int = 0
    error_code: str | None = None
    requests: list[tuple[int | None, int | None]] = field(default_factory=list)  # (input, output) tokens each


async def check_connection(chat: ChatEndpoint) -> ConnectionResult:
    """Send one minimal request with one harmless tool and name the first check that fails."""
    require_configured(chat)
    client = provider(chat, timeout=TEST_TIMEOUT_S, max_retries=0).client
    result = ConnectionResult()
    started = time.monotonic()
    request = {
        "model": str(chat.model),
        "messages": [{"role": "user", "content": "Reply with the word OK."}],
        "max_tokens": 16,
    }
    try:
        response = await client.chat.completions.create(**request, tools=[PING_TOOL])  # type: ignore[call-overload]
        result.requests.append(_tokens(response))
        result.checks = dict.fromkeys(result.checks, True)
        result.ok = True
    except (openai.APIConnectionError, openai.APITimeoutError):
        result.error_code = "unreachable"
    except openai.AuthenticationError:
        result.checks["reachable"] = True
        result.error_code = "auth_failed"
    except openai.NotFoundError:
        result.checks.update(reachable=True, auth=True)
        result.error_code = "model_not_found"
    except openai.BadRequestError:
        result.checks.update(reachable=True, auth=True)
        result.requests.append((None, None))
        try:
            response = await client.chat.completions.create(**request)  # type: ignore[call-overload]
            result.requests.append(_tokens(response))
            result.checks["model"] = True
            result.error_code = "tool_calls_unsupported"
        except openai.APIError:
            result.error_code = "model_error"
    except openai.APIError:
        result.checks.update(reachable=True, auth=True)
        result.error_code = "model_error"
    finally:
        result.latency_ms = int((time.monotonic() - started) * 1000)
        if not result.requests:
            result.requests.append((None, None))
    return result


def _tokens(response: object) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None
    return getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None)
