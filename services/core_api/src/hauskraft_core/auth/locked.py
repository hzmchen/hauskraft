# SPDX-License-Identifier: AGPL-3.0-or-later
"""While an account must replace its temporary password, only these requests work (M1S-E07-01).

Everything else answers 403 ``password_change_required``: the member can see who they are, sign out and change the
password, and the app can still load the household name and the theme for that page.
"""

from __future__ import annotations

from hauskraft_sdk.errors import HauskraftError

ALLOWED = frozenset(
    {
        ("GET", "/api/v1/auth/session"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/logout-everywhere"),
        ("GET", "/api/v1/me"),
        ("POST", "/api/v1/me/password"),
        ("GET", "/api/v1/household"),
        ("GET", "/api/v1/theme"),
        ("GET", "/api/v1/theme/active.css"),
    }
)
ALLOWED_PREFIXES = (("GET", "/api/v1/theme/assets/"),)


class PasswordChangeRequiredError(HauskraftError):
    status = 403
    code = "password_change_required"
    title = "Choose a new password first"


def allowed_while_locked(method: str, path: str) -> bool:
    method = method.upper()
    return (method, path) in ALLOWED or any(method == m and path.startswith(prefix) for m, prefix in ALLOWED_PREFIXES)
