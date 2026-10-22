# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-01: argon2id at or above the OWASP minimum, rehash on parameter change, length policy."""

import re

import pytest
from pwdlib.hashers.argon2 import Argon2Hasher

from hauskraft_core.auth.passwords import (
    PasswordPolicyError,
    check_password_policy,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit
OWASP = {"m": 19456, "t": 2, "p": 1}


def _params(hashed: str) -> dict[str, int]:
    match = re.match(r"^\$argon2id\$v=19\$m=(\d+),t=(\d+),p=(\d+)\$", hashed)
    assert match, hashed
    return {"m": int(match[1]), "t": int(match[2]), "p": int(match[3])}


async def test_hash_is_argon2id_at_or_above_the_owasp_minimum() -> None:
    hashed = await hash_password("correct-horse-battery")
    assert hashed.startswith("$argon2id$")
    params = _params(hashed)
    assert all(params[k] >= OWASP[k] for k in OWASP), params


async def test_verify() -> None:
    hashed = await hash_password("correct-horse-battery")
    assert await verify_password("correct-horse-battery", hashed) == (True, None)
    assert (await verify_password("wrong-horse-battery", hashed))[0] is False


async def test_old_parameters_are_upgraded_on_verify() -> None:
    weak = Argon2Hasher(time_cost=2, memory_cost=19456, parallelism=1).hash("correct-horse-battery")
    ok, updated = await verify_password("correct-horse-battery", weak)
    assert ok is True
    assert updated is not None
    assert _params(updated) != _params(weak)


async def test_garbage_hash_does_not_verify() -> None:
    assert await verify_password("x" * 12, "not-a-hash") == (False, None)


@pytest.mark.parametrize("password", ["x" * 12, "y" * 128, "Ünïcødé-passwörd"])
def test_policy_accepts(password: str) -> None:
    check_password_policy(password)


@pytest.mark.parametrize("password", ["", "short", "x" * 11, "x" * 129])
def test_policy_rejects(password: str) -> None:
    with pytest.raises(PasswordPolicyError) as err:
        check_password_policy(password)
    assert err.value.status == 422
