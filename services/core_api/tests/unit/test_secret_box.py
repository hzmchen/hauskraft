# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E03-03: secrets encrypted at rest with AES-GCM under a key derived from HAUSKRAFT_SECRET_KEY (ADR 0021)."""

import base64

import pytest

from hauskraft_core.secret_box import SecretBoxError, seal, unseal

pytestmark = pytest.mark.unit

SECRET = "x" * 48
OTHER = "y" * 48
KEY = "sk-live-0123456789abcdef"
CONTEXT = "assistant.endpoints.chat.api_key"


def test_round_trip() -> None:
    assert unseal(seal(KEY, SECRET, CONTEXT), SECRET, CONTEXT) == KEY


def test_format_is_versioned_and_never_holds_the_plain_key() -> None:
    token = seal(KEY, SECRET, CONTEXT)
    version, nonce, ciphertext = token.split(":")
    assert version == "v1"
    assert len(base64.urlsafe_b64decode(nonce + "==")) == 12
    assert base64.urlsafe_b64decode(ciphertext + "==")
    assert KEY not in token


def test_every_seal_uses_a_new_nonce() -> None:
    assert seal(KEY, SECRET, CONTEXT) != seal(KEY, SECRET, CONTEXT)


def test_another_secret_cannot_open_it() -> None:
    with pytest.raises(SecretBoxError):
        unseal(seal(KEY, SECRET, CONTEXT), OTHER, CONTEXT)


def test_a_value_moved_to_another_setting_cannot_be_opened() -> None:
    with pytest.raises(SecretBoxError):
        unseal(seal(KEY, SECRET, CONTEXT), SECRET, "assistant.endpoints.speech.api_key")


@pytest.mark.parametrize("token", ["", "plain-text", "v2:abc:def", "v1:not-base64!:x", "v1:AAAA"])
def test_malformed_values_fail_cleanly(token: str) -> None:
    with pytest.raises(SecretBoxError):
        unseal(token, SECRET, CONTEXT)
