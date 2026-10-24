# SPDX-License-Identifier: MIT
"""Fixtures for live API acceptance tests. Every module here sets `pytestmark = pytest.mark.live`."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from _support.live import MEMBER_PASSWORD, TEMP_PASSWORD, Api, configure_fake, logged_in, reachable, tasks_titled


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


# ---------------------------------------------------------------- M1*: throwaway members on the demo stack
@pytest.fixture
def new_member(demo: Api) -> Iterator:
    """Create members as the demo owner (never touch demo or alex); deactivate them afterwards.

    Returns the created ``Member`` plus the ``password`` it was created with.
    """
    created: list[str] = []

    def _make(role: str = "adult", password: str = TEMP_PASSWORD, display_name: str | None = None) -> dict:
        username = "acc" + uuid.uuid4().hex[:8]
        body = {"username": username, "display_name": display_name or f"Acceptance {username}", "password": password}
        if role != "adult":  # the default; leaving it out keeps M0*-era stories testable on their own
            body["role"] = role
        r = demo.post("/users", json=body)
        assert r.status_code == 201, r.text
        member = {**r.json(), "password": password}
        created.append(member["id"])
        return member

    yield _make
    for user_id in created:
        demo.post(f"/users/{user_id}/deactivate")


@pytest.fixture
def ready_member(new_member) -> Iterator:
    """A member who has signed in and replaced the temporary password; returns ``(member, api)``."""
    apis: list[Api] = []

    def _make(role: str = "adult") -> tuple[dict, Api]:
        member = new_member(role=role)
        api = Api()
        apis.append(api)
        assert api.login(member["username"], member["password"]).status_code == 200
        r = api.post("/me/password", json={"current_password": member["password"], "new_password": MEMBER_PASSWORD})
        assert r.status_code == 204, r.text
        member["password"] = MEMBER_PASSWORD
        return member, api

    yield _make
    for api in apis:
        api.close()


# ---------------------------------------------------------------- M2*: the assistant on the demo stack
@pytest.fixture
def assistant(demo: Api) -> Iterator[Api]:
    """The demo owner with the assistant pointed at the fake model (`fake-tools`); left that way afterwards."""
    configure_fake(demo)
    demo.patch("/assistant/settings", json={"tools_disabled": []})
    yield demo
    configure_fake(demo)
    demo.patch("/assistant/settings", json={"tools_disabled": []})


@pytest.fixture
def cleanup_titles(demo: Api) -> Iterator[list[str]]:
    """Titles of tasks a test made the assistant create; every task with one of them is deleted afterwards."""
    titles: list[str] = []
    yield titles
    for title in titles:
        for task in tasks_titled(demo, title):
            demo.delete(f"/tasks/{task['id']}")


@pytest.fixture
def unique_title() -> Iterator:
    def _make(label: str) -> str:
        return f"acc-{uuid.uuid4().hex[:8]} {label}"
    yield _make

