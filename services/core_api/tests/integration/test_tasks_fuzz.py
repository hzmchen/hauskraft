# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-05: Schemathesis fuzzes /api/v1/tasks from the generated contract as a signed-in adult.

Checks: no server errors, responses match their documented schemas, status codes and content types.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
import schemathesis
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, settings

from hearthos_core.app import create_app
from hearthos_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = [pytest.mark.integration, pytest.mark.contract]

REPO = Path(__file__).resolve().parents[4]
CONTRACT = json.loads((REPO / "packages" / "schemas" / "openapi" / "core-api.openapi.json").read_text())


@pytest.fixture
def fuzz_app(api_settings: Settings, make_user: Callable[..., str]):  # type: ignore[no-untyped-def]
    app = create_app(api_settings)
    with TestClient(app, headers={"Origin": "http://testserver"}) as client:
        r = client.post("/api/v1/auth/login", json={"username": make_user(), "password": PASSWORD})
        app.state.fuzz_auth = {
            "cookie": f"hearthos_session={client.cookies['hearthos_session']}",
            "csrf": r.json()["csrf_token"],
        }
        yield app


schema = schemathesis.openapi.from_dict(CONTRACT).include(path_regex=r"^/api/v1/tasks")


@schema.parametrize()
@settings(max_examples=15, deadline=None, suppress_health_check=list(HealthCheck))
def test_tasks_api_conforms(case: schemathesis.Case, fuzz_app) -> None:  # type: ignore[no-untyped-def]
    auth = fuzz_app.state.fuzz_auth
    headers = {
        **(case.headers or {}),
        "Cookie": auth["cookie"],
        "X-CSRF-Token": auth["csrf"],
        "Origin": "http://testserver",
    }
    kwargs = case.as_transport_kwargs(base_url="http://testserver", headers=headers)
    kwargs.pop("verify", None)
    kwargs.pop("cookies", None)  # the session cookie travels in the Cookie header
    with TestClient(fuzz_app) as client:
        response = client.request(**kwargs)
    assert response.status_code < 500, response.text
    # Starlette lists only the matched route's methods in `Allow` on 405 (GET and POST /tasks are separate
    # routes), so the Allow-header check is excluded; everything else stays on.
    case.validate_response(response, excluded_checks=[schemathesis.checks.allow_header_conformance])
