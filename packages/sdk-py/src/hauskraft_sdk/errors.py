# SPDX-License-Identifier: MIT
"""Errors plugins raise; core renders them as application/problem+json with a stable ``code``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class HauskraftError(Exception):
    """Base error with an HTTP status and a stable machine-readable code."""

    status: int = 400
    code: str = "bad_request"
    title: str = "Bad request"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        title: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
        if title is not None:
            self.title = title
        self.extra: dict[str, Any] = dict(extra or {})


class NotFoundError(HauskraftError):
    status = 404
    code = "not_found"
    title = "Not found"


class ConflictError(HauskraftError):
    status = 409
    code = "conflict"
    title = "Conflict"

    def __init__(self, code: str, detail: str | None = None, *, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__(detail, code=code, extra=extra)


class PolicyDeniedError(HauskraftError):
    """Raised by ``authorize()`` when the policy denies an action."""

    status = 403
    code = "policy_denied"
    title = "Not allowed"

    def __init__(self, action: str, detail: str | None = None) -> None:
        super().__init__(detail or f"The policy does not allow {action!r}.")
        self.action = action
