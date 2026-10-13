# SPDX-License-Identifier: AGPL-3.0-or-later
"""CSRF protection (M0S-E05-03, ADR-0005): synchronizer token plus Origin allowlist.

Every state-changing request from a signed-in session must carry ``X-CSRF-Token`` equal to the session's
token (constant-time compare) and, if it sends ``Origin``, an origin from ``HEARTHOS_ALLOWED_ORIGINS``.
Login has no session yet, so it gets the Origin check only (login CSRF). GET never changes state.
"""

from __future__ import annotations

import hmac

from fastapi import Request

from hearthos_sdk.errors import HearthosError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
HEADER = "X-CSRF-Token"


class CsrfFailedError(HearthosError):
    status = 403
    code = "csrf_failed"
    title = "Request blocked"


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in {
        o.rstrip("/") for o in request.app.state.settings.allowed_origins
    }:
        raise CsrfFailedError("This origin may not change data here.")


def check_request(request: Request, session_token: str) -> None:
    if request.method in SAFE_METHODS:
        return
    check_origin(request)
    sent = request.headers.get(HEADER, "")
    if not sent or not hmac.compare_digest(sent.encode(), session_token.encode()):
        raise CsrfFailedError(f"Missing or wrong {HEADER} header.")
