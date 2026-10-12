# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structured JSON logging and request ids (M0S-E03-03).

structlog renders JSON; stdlib loggers (uvicorn, SQLAlchemy, alembic) are bridged through the same
renderer. ``RequestContextMiddleware`` assigns ``X-Request-ID`` and writes one access line per request.
"""

from __future__ import annotations

import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_var: ContextVar[str | None] = ContextVar("hearthos_request_id", default=None)
request_user_id: ContextVar[str | None] = ContextVar("hearthos_request_user_id", default=None)

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_configured = False


def _add_request_context(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    rid = request_id_var.get()
    if rid and "request_id" not in event_dict:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Idempotent: route structlog and stdlib logging through one JSON renderer on stderr."""
    global _configured
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_request_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, structlog.processors.JSONRenderer()],
    )
    root = logging.getLogger()
    if not _configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        handler.set_name("hearthos-json")
        root.addHandler(handler)
        logging.getLogger("uvicorn.access").disabled = True  # replaced by hearthos.access
        _configured = True
    root.setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


_access = structlog.get_logger("hearthos.access")


class RequestContextMiddleware:
    """Assigns a request id, echoes it as ``X-Request-ID`` and logs one JSON access line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        rid_token = request_id_var.set(rid)
        user_token = request_user_id.set(None)
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                MutableHeaders(scope=message)["X-Request-ID"] = rid
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            # Unhandled errors bypass the app's exception handlers (Starlette renders them outside user
            # middleware), so answer here while the request id is still known.
            if response_started:
                raise
            from hearthos_core.errors import internal_error_response

            get_logger("hearthos.errors").exception("unhandled_error", error_type=type(exc).__name__)
            await internal_error_response()(scope, receive, send_with_id)
        finally:
            _access.info(
                "http.request",
                request_id=rid,
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                user_id=request_user_id.get(),
            )
            request_user_id.reset(user_token)
            request_id_var.reset(rid_token)
