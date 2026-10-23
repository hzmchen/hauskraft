# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E07-01: what still works while an account must replace its temporary password."""

import pytest

from hauskraft_core.auth.locked import allowed_while_locked

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/auth/session"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/logout-everywhere"),
        ("GET", "/api/v1/me"),
        ("POST", "/api/v1/me/password"),
        ("GET", "/api/v1/household"),
        ("GET", "/api/v1/theme"),
        ("GET", "/api/v1/theme/active.css"),
        ("GET", "/api/v1/theme/assets/dev.hauskraft.theme.paper/fonts/serif.woff2"),
    ],
)
def test_allowlisted(method: str, path: str) -> None:
    assert allowed_while_locked(method, path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/tasks"),
        ("POST", "/api/v1/tasks"),
        ("PATCH", "/api/v1/me"),
        ("GET", "/api/v1/me/sessions"),
        ("PATCH", "/api/v1/household"),
        ("POST", "/api/v1/auth/session"),
        ("GET", "/api/v1/activity"),
        ("GET", "/api/v1/theme/assets"),
        ("GET", "/api/v1/mex"),
    ],
)
def test_everything_else_is_locked(method: str, path: str) -> None:
    assert not allowed_while_locked(method, path)
