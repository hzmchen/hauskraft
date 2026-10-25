# E01 · Fake model & CI

**Goal:** Every assistant test runs against a deterministic, free, OpenAI-compatible fake model, locally and in CI
(spec §8.0, ADR 0022).
**Out of scope:** Real-model evals (E09), recording and replaying real provider traffic.
**Dependencies:** none.

---

## The fake model (contract)
The server is spec-owned: `tests/fixtures/fake-llm/server.py` (Python standard library only) and
`tests/fixtures/fake-llm/scenarios.json`. Its behaviour is described in `tests/fixtures/fake-llm/README.md`. This epic
runs it; it does not change it.

| Variable | Meaning | Default |
|---|---|---|
| `HAUSKRAFT_FAKE_LLM_URL` | Base URL the **API container** uses (what an owner enters in Settings → Assistant) | `http://fake-llm:8090/v1` |
| `HAUSKRAFT_FAKE_LLM_ADMIN_URL` | URL the **tests** use for `GET /_requests` and `POST /_reset` | `http://localhost:8090` |

---

## M2S-E01-01 · Fake model in the test stack
- **Story:** As a test author, I want the fake model running next to the demo stack, so that assistant tests need no
  real provider.
- **AC:**
  - Given `docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait`, then a `fake-llm` service
    runs `tests/fixtures/fake-llm/server.py` on port 8090, reachable from the API container as `fake-llm:8090` and
    from the host on `127.0.0.1:8090` only.
  - `GET http://localhost:8090/v1/models` lists `fake-tools`; the service has a health check.
  - `just fake-llm-reset` clears its recorded requests.
  - The production Compose file has no `fake-llm` service.
- **Tech:** `python:3.13-slim` image with the fixture folder mounted read-only; no extra packages.
- **Tests:** Static: `tests/acceptance/repo/test_m2_test_infra.py`. Live: `tests/acceptance/api/test_assistant_settings.py` (fake reachable).
- **Deps:** — · **Est:** S · **Labels:** area:ci, area:deploy

## M2S-E01-02 · CI runs the assistant suites against the fake model
- **Story:** As a maintainer, I want CI to run the assistant's live and e2e tests on every PR, so that the harness
  can't break silently.
- **AC:**
  - The `acceptance` live run and the `e2e` job start the stack with the test override (including `fake-llm`) and set
    `HAUSKRAFT_FAKE_LLM_URL` and `HAUSKRAFT_FAKE_LLM_ADMIN_URL`.
  - No CI job needs a real model or a provider secret, except the manual `evals` workflow (E09-03).
- **Tech:** `.github/workflows/e2e.yml`, `.github/workflows/ci.yml`.
- **Tests:** Static: `tests/acceptance/repo/test_m2_test_infra.py`.
- **Deps:** E01-01 · **Est:** S · **Labels:** area:ci
