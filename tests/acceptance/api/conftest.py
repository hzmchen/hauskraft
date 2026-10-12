# SPDX-License-Identifier: MIT
"""Fixtures for live API acceptance tests. Every module here sets `pytestmark = pytest.mark.live`."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from _support.live import Api, logged_in, reachable


@pytest.fixture
def anon() -> Iterator[Api]:
    reachable()
    api = Api()
    yield api
    api.close()


@pytest.fixture
def demo() -> Iterator[Api]:
    with logged_in("demo") as api:
        yield api


@pytest.fixture
def alex() -> Iterator[Api]:
    with logged_in("alex") as api:
        yield api


@pytest.fixture
def make_task(demo: Api) -> Iterator:
    """Create tasks through the API and delete them afterwards."""
    created: list[str] = []

    def _make(title: str, due_on: str | None = None, api: Api | None = None) -> dict:
        client = api or demo
        body = {"title": title}
        if due_on is not None:
            body["due_on"] = due_on
        r = client.post("/tasks", json=body)
        assert r.status_code == 201, r.text
        task = r.json()
        created.append(task["id"])
        return task

    yield _make
    for task_id in created:
        demo.delete(f"/tasks/{task_id}")
