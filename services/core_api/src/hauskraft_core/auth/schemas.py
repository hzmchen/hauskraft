# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth and user API models (contract: docs/backlog/m0-star/E05-auth-and-users.md)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from hauskraft_core.auth.devices import describe
from hauskraft_core.db.models import Session, User, UserRole
from hauskraft_core.policy import permissions_for

Locale = Literal["en", "de"]
NO_NUL = r"^[^\x00]*$"  # PostgreSQL text cannot hold NUL bytes: 422 instead of a failed query
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, pattern=NO_NUL)]
Username = Annotated[str, Field(min_length=1, max_length=64, pattern=NO_NUL)]


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
    permissions: list[str] = Field(
        description="The actions the user's role may do, sorted (spec §2.3). For showing controls; the API decides."
    )

    @classmethod
    def of(cls, user: User, csrf_token: str, expires_at: dt.datetime) -> SessionOut:
        return cls(
            user=UserOut.of(user),
            csrf_token=csrf_token,
            expires_at=expires_at,
            permissions=permissions_for(str(user.role)),
        )


class SessionInfo(_Model):
    """One of the member's signed-in sessions (M1S-E05-02). Never the token, its hash or the IP address."""

    id: uuid.UUID
    device: str
    created_at: dt.datetime
    last_seen_at: dt.datetime
    current: bool

    @classmethod
    def of(cls, row: Session, current: Session) -> SessionInfo:
        return cls(
            id=row.public_id,
            device=describe(row.user_agent),
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            current=row.id == current.id,
        )


class LoginIn(_Model):
    username: Username
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class MePatch(_Model):
    display_name: DisplayName | None = None
    locale: Locale | None = None


class UserCreate(_Model):
    username: Username
    display_name: DisplayName
    password: Annotated[str, Field(min_length=1, max_length=1024)]
    role: UserRole = UserRole.ADULT
