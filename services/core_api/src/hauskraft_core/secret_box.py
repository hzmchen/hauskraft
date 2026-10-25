# SPDX-License-Identifier: AGPL-3.0-or-later
"""Secrets encrypted at rest (M2S-E03-03, ADR 0021).

AES-GCM under a key derived with HKDF-SHA256 from ``HAUSKRAFT_SECRET_KEY`` and its own label, so session signing and
encryption never share a key. Values are stored as ``v1:<nonce>:<ciphertext>`` (URL-safe base64, no padding); the
setting's name is bound in as associated data, so a value copied to another setting can't be opened.

This protects leaked backups and dumps, not a compromised server: the running API holds both halves.
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

VERSION = "v1"
LABEL = b"hauskraft/settings-secret/v1"


class SecretBoxError(Exception):
    """The value is malformed or was sealed under another secret or setting."""


def _key(secret: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=LABEL).derive(secret.encode())


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def seal(plain: str, secret: str, context: str) -> str:
    """Encrypt ``plain`` for the setting named ``context``."""
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key(secret)).encrypt(nonce, plain.encode(), context.encode())
    return f"{VERSION}:{_b64(nonce)}:{_b64(ciphertext)}"


def unseal(token: str, secret: str, context: str) -> str:
    """Decrypt a value from :func:`seal`; raises :class:`SecretBoxError` if it can't be opened."""
    parts = token.split(":")
    if len(parts) != 3 or parts[0] != VERSION:
        raise SecretBoxError("not a sealed value")
    try:
        nonce, ciphertext = _unb64(parts[1]), _unb64(parts[2])
        return AESGCM(_key(secret)).decrypt(nonce, ciphertext, context.encode()).decode()
    except (binascii.Error, ValueError, InvalidTag) as exc:
        raise SecretBoxError("cannot open the sealed value") from exc
