# SPDX-License-Identifier: AGPL-3.0-or-later
"""RFC 9457 problem+json errors with a stable ``code`` (M0S-E03-03, AGENTS.md rule 7)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from hearthos_core.logging import get_logger, request_id_var
from hearthos_sdk.errors import HearthosError

PROBLEM_JSON = "application/problem+json"
PROBLEM_TYPE = "https://hearthos.dev/problems/{code}"

_HTTP_CODES = {
    400: ("bad_request", "Bad request"),
    401: ("unauthenticated", "Not signed in"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
    409: ("conflict", "Conflict"),
    413: ("payload_too_large", "Payload too large"),
    415: ("unsupported_media_type", "Unsupported media type"),
    422: ("validation_failed", "Validation failed"),
    429: ("rate_limited", "Too many requests"),
}
_log = get_logger("hearthos.errors")


def problem(
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    *,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE.format(code=code),
        "title": title,
        "status": status,
        "detail": detail or title,
        "code": code,
        "request_id": request_id_var.get(),
        **extra,
    }
    return JSONResponse(jsonable_encoder(body), status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _hearthos_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HearthosError):  # pragma: no cover - registered for this type only
        raise exc
    return problem(exc.status, exc.code, exc.title, exc.detail, **exc.extra)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - registered for this type only
        raise exc
    code, title = _HTTP_CODES.get(exc.status_code, ("http_error", "HTTP error"))
    detail = exc.detail if isinstance(exc.detail, str) else title
    return problem(exc.status_code, code, title, detail, headers=dict(exc.headers or {}))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - registered for this type only
        raise exc
    errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
    return problem(422, "validation_failed", "Validation failed", "The request is not valid.", errors=errors)


def internal_error_response() -> JSONResponse:
    return problem(500, "internal_error", "Internal error", "Something went wrong on our side.")


async def _unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    _log.exception("unhandled_error", error_type=type(exc).__name__)
    return internal_error_response()


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HearthosError, _hearthos_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
