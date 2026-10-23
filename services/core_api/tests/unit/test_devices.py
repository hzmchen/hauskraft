# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E05-02: short device descriptions from the User-Agent, without a parser dependency."""

import pytest

from hauskraft_core.auth.devices import UNKNOWN_DEVICE, describe

pytestmark = pytest.mark.unit

FIREFOX_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
EDGE_WINDOWS = CHROME_WINDOWS + " Edg/141.0.0.0"
SAFARI_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.0 Mobile/15E148 Safari/604.1"
)
CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile "
    "Safari/537.36"
)
FIREFOX_IPAD = (
    "Mozilla/5.0 (iPad; CPU OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/140.0 "
    "Mobile/15E148 Safari/605.1.15"
)
CHROME_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "CriOS/141.0.0.0 Mobile/15E148 Safari/604.1"
)
OPERA_WINDOWS = CHROME_WINDOWS + " OPR/120.0.0.0"
CHROMEOS = (
    "Mozilla/5.0 (X11; CrOS x86_64 16328.55.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (FIREFOX_LINUX, "Firefox on Linux"),
        (CHROME_WINDOWS, "Chrome on Windows"),
        (EDGE_WINDOWS, "Edge on Windows"),
        (OPERA_WINDOWS, "Opera on Windows"),
        (SAFARI_MAC, "Safari on macOS"),
        (SAFARI_IPHONE, "Safari on iPhone"),
        (FIREFOX_IPAD, "Firefox on iPad"),
        (CHROME_IOS, "Chrome on iPhone"),
        (CHROME_ANDROID, "Chrome on Android"),
        (CHROMEOS, "Chrome on ChromeOS"),
    ],
)
def test_browser_on_system(user_agent: str, expected: str) -> None:
    assert describe(user_agent) == expected


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        ("Mozilla/5.0 (X11; Linux x86_64) SomethingNew/1.0", "Browser on Linux"),
        ("Firefox/140.0", "Firefox"),
    ],
)
def test_partial_matches(user_agent: str, expected: str) -> None:
    assert describe(user_agent) == expected


@pytest.mark.parametrize("user_agent", [None, "", "   ", "python-httpx/0.28.1", "curl/8.12.1"])
def test_unknown_devices(user_agent: str | None) -> None:
    assert describe(user_agent) == UNKNOWN_DEVICE == "Unknown device"
