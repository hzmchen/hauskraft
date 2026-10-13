# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth and user API models (contract: docs/backlog/m0-star/E05-auth-and-users.md)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from hearthos_core.db.models import User

Locale = Literal["en", "de"]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserOut(_Model):
    id: uuid.UUID
    username: str
    display_name: str
    role: str
    locale: Locale

    @classmethod
    def of(cls, user: User) -> UserOut:
        locale: Locale = "de" if user.locale == "de" else "en"
        return cls(
            id=user.id, username=user.username, display_name=user.display_name, role=str(user.role), locale=locale
        )


class SessionOut(_Model):
    user: UserOut
    csrf_token: str
    expires_at: dt.datetime


class LoginIn(_Model):
    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class MePatch(_Model):
    display_name: DisplayName | None = None
    locale: Locale | None = None
