# SPDX-License-Identifier: AGPL-3.0-or-later
"""UUIDv7 ids generated in the app (ADR-0009): time-ordered, so indexes and feeds stay sorted."""

import uuid

from uuid6 import uuid7


def new_id() -> uuid.UUID:
    return uuid.UUID(bytes=uuid7().bytes)
