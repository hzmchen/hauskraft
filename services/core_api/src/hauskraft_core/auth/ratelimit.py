# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-memory login rate limit: 5 failures per username and IP within 15 minutes (M0S-E05-02).

Per process and lost on restart, which is acceptable for a single-container household deployment.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class LoginRateLimiter:
    def __init__(self, max_failures: int = MAX_FAILURES, window: float = WINDOW_SECONDS) -> None:
        self.max_failures = max_failures
        self.window = window
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _prune(self, key: tuple[str, str], now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def retry_after(self, username: str, ip: str) -> int:
        """Seconds until the next attempt is allowed; 0 when allowed now."""
        now = time.monotonic()
        q = self._prune((username.lower(), ip), now)
        if len(q) < self.max_failures:
            return 0
        return max(1, int(self.window - (now - q[0])) + 1)

    def failed(self, username: str, ip: str) -> None:
        key = (username.lower(), ip)
        self._prune(key, time.monotonic()).append(time.monotonic())

    def succeeded(self, username: str, ip: str) -> None:
        self._failures.pop((username.lower(), ip), None)
