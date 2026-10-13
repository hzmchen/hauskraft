# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-04: login goes through an IdentityProvider chosen by HEARTHOS_AUTH_PROVIDER."""

import pytest

from hearthos_core.auth.providers import (
    IdentityProvider,
    LocalPasswordProvider,
    OidcProvider,
    PasswordCredentials,
    provider_from_settings,
)
from hearthos_core.settings import Settings

pytestmark = pytest.mark.unit


def test_local_is_the_default() -> None:
    assert isinstance(provider_from_settings(Settings(env="test")), LocalPasswordProvider)


def test_oidc_can_be_selected() -> None:
    assert isinstance(provider_from_settings(Settings(env="test", auth_provider="oidc")), OidcProvider)


def test_providers_satisfy_the_protocol() -> None:
    assert isinstance(LocalPasswordProvider(), IdentityProvider)
    assert isinstance(OidcProvider(), IdentityProvider)


async def test_oidc_is_a_stub_until_m1() -> None:
    with pytest.raises(NotImplementedError, match="M1"):
        await OidcProvider().authenticate(None, PasswordCredentials("demo", "x" * 12))  # type: ignore[arg-type]
