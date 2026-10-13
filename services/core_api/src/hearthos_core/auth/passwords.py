# SPDX-License-Identifier: AGPL-3.0-or-later
"""Password hashing with argon2id via pwdlib (M0S-E05-01, ADR-0005).

pwdlib's recommended parameters (m=64 MiB, t=3, p=4) exceed the OWASP minimum (m=19 MiB, t=2, p=1).
Hashing is CPU-bound, so it runs in a worker thread.
"""

from __future__ import annotations

from anyio import to_thread
from pwdlib import PasswordHash

from hearthos_sdk.errors import HearthosError

MIN_LENGTH = 12
MAX_LENGTH = 128

_hasher = PasswordHash.recommended()


class PasswordPolicyError(HearthosError):
    status = 422
    code = "password_policy"
    title = "Password does not meet the policy"


def check_password_policy(password: str) -> None:
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        raise PasswordPolicyError(f"Passwords must have {MIN_LENGTH} to {MAX_LENGTH} characters.")


async def hash_password(password: str) -> str:
    return await to_thread.run_sync(_hasher.hash, password)


async def verify_password(password: str, hashed: str) -> tuple[bool, str | None]:
    """Return ``(ok, new_hash)``; ``new_hash`` is set when the stored parameters are outdated."""

    def _verify() -> tuple[bool, str | None]:
        try:
            return _hasher.verify_and_update(password, hashed)
        except Exception:  # unknown or corrupt hash format: treat as a failed login
            return False, None

    return await to_thread.run_sync(_verify)


async def dummy_verify(password: str) -> None:
    """Spend the same work as a real verification (timing parity for unknown users)."""
    await verify_password(password, _DUMMY_HASH)


_DUMMY_HASH = _hasher.hash("hearthos-timing-parity-dummy")
