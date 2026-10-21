# E03 · Backend core API

**Goal:** A FastAPI app factory with settings, health, logging, errors, the service-layer seam and OpenAPI export.
**Out of scope:** gateway; graph API beyond tasks.
**Dependencies:** E01.

---

## M0S-E03-01 · App factory and settings
- **Story:** As an operator, I want env-driven configuration, so that the same image runs in dev, CI and the demo.
- **AC:**
  - Given `HAUSKRAFT_DATABASE_URL` and `HAUSKRAFT_SECRET_KEY`, when I call `create_app()`, then the app starts.
  - A missing secret in `HAUSKRAFT_ENV=production` raises at startup.
  - All routes are under `/api/v1`.
- **Tech:**
  - `hauskraft_core/app.py` (`create_app()`; lifespan opens the async engine, loads plugins and themes).
  - `settings.py` with pydantic-settings, env prefix `HAUSKRAFT_`. Settings known now: `DATABASE_URL`, `SECRET_KEY`, `ENV`, `COOKIE_SECURE`, `ALLOWED_ORIGINS`, `PLUGIN_PATHS`, `THEME_PATHS`, `DEFAULT_THEME`, `POLICY`, `AUTH_PROVIDER`, `SEED_DEMO`, `RELAY_ENABLED`, `VALIDATE_EVENTS`, `OTEL_ENABLED`.
  - FastAPI `~=0.143`, uvicorn.
- **Tests:** Unit: settings validation; app boots with a test DB URL.
- **Deps:** E01-02 · **Est:** S · **Labels:** area:api

## M0S-E03-02 · Health and readiness
- **Story:** As an operator, I want liveness and readiness endpoints, so that Compose can `--wait` correctly.
- **AC:**
  - Given a running app, `GET /api/v1/healthz` returns `200 {"status":"ok"}` with no DB access.
  - `GET /api/v1/readyz` returns 200 only when the DB answers `SELECT 1`, Alembic is at `heads`, every enabled plugin loaded, and the active theme compiled. Otherwise it returns 503 with failing `checks[]`. Each check is `{name, ok, detail}`; the names are `database`, `migrations`, `plugins` and `theme`.
  - An invalid third-party theme does **not** make readiness fail (it is listed as invalid); a failure to compile the built-in default theme does.
- **Tech:** `health/router.py` with a small readiness-check registry (`register_check(name, fn)`). This story ships the DB, migration and plugin checks; E13-03 registers the theme check. Alembic `ScriptDirectory.get_heads()` vs `alembic_version` comparison.
- **Tests:** Integration: 503 before migration and 200 after.
- **Deps:** E03-01, E04-01 · **Est:** S · **Labels:** area:api

## M0S-E03-03 · Structured logging, request IDs, problem+json errors
- **Story:** As an operator, I want JSON logs and uniform errors, so that issues are diagnosable.
- **AC:**
  - Given any request, then a JSON log line includes `request_id`, `method`, `path`, `status`, `duration_ms` and `user_id` (if authenticated). The response echoes `X-Request-ID`.
  - Errors are `application/problem+json` (RFC 9457) with `type`, `title`, `status`, `detail`, `code`, `request_id`. Validation errors return 422 with `errors[]`.
- **Tech:** structlog with a stdlib bridge; `errors.py` exception handlers. Optional `HAUSKRAFT_OTEL_ENABLED` wires `opentelemetry-instrumentation-fastapi`, off by default.
- **Tests:** Unit: error shape snapshot; log capture.
- **Deps:** E03-01 · **Est:** S · **Labels:** area:api

## M0S-E03-04 · Service layer and `authorize()` seam
- **Story:** As a future gateway or policy implementer, I want every write to pass one hook, so that Cedar can replace the no-op without touching handlers.
- **AC:**
  - Given any service write method (tasks, users, dashboard layout, deployment settings), when it executes, then it calls `await policy.authorize(actor, action, resource, data_class, capability)` before mutating.
  - `NoOpPolicy` returns `Decision.ALLOW` and logs at debug. A test-only `DenyAllPolicy` makes the API return 403 `code=policy_denied`.
- **Tech:**
  - `policy/__init__.py`: `Actor(id, role, kind="user")`, `ResourceRef(type, id)`, `Decision`, `Policy` Protocol.
  - Chosen via `HAUSKRAFT_POLICY=noop`; exposed to plugins through `PluginContext.authorize` (sdk-py).
  - `UnitOfWork` (async session + outbox writer, a single commit).
- **Tests:** Unit: spy policy called with expected args. Integration: DenyAll → 403, no row written, no event written.
- **Deps:** E03-01, E04-01 · **Est:** M · **Labels:** area:api, governance

## M0S-E03-05 · OpenAPI 3.1 export as contract
- **Story:** As a frontend agent, I want a committed OpenAPI file, so that I can generate a client without running the backend.
- **AC:**
  - Given the app, when I run `just gen-openapi`, then `packages/schemas/openapi/core-api.openapi.json` is written deterministically (sorted keys), with `openapi: 3.1.x`, unique stable `operationId`s (`tasks_list`, `tasks_create`, `themes_list`, …) and tags per plugin or core area.
  - CI fails on drift.
- **Tech:** `scripts/export_openapi.py`; `generate_unique_id_function=lambda r: f"{r.tags[0]}_{r.name}"`. Non-JSON endpoints (`/theme/active.css`, theme assets) are documented with their content types.
- **Tests:** Contract: snapshot equality; Schemathesis (pinned at implementation time) runs a stateful fuzz on `/api/v1/tasks` in the contract job.
- **Deps:** E03-01 · **Est:** S · **Labels:** area:api, contract
