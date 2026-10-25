# SPDX-License-Identifier: AGPL-3.0-or-later
# Hauskraft task runner. `just --list` shows every recipe; `just check` before every push.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Python test roots next to their code (the spec-owned suite in tests/ runs via `just acceptance`).
py_tests := "services/core_api/tests packages/sdk-py/tests plugins/official/tasks/backend/tests"

# List recipes
default:
    @just --list

# Install Python and Node dependencies and the git hooks (run once)
setup:
    uv sync --all-packages
    pnpm install --frozen-lockfile
    uv tool run pre-commit install

# Start Postgres, the API with reload and the Vite dev server (Ctrl+C stops both)
dev: db
    trap 'kill 0' EXIT; \
    uv run uvicorn hauskraft_core.app:create_app --factory --reload --port 8000 & \
    pnpm --filter web dev & \
    wait

# Start only the database
db:
    docker compose up db -d --wait

# Lint Python and TypeScript, check formatting
lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm lint
    pnpm format:check

# Format Python and TypeScript
fmt:
    uv run ruff check --fix .
    uv run ruff format .
    pnpm format

# Type-check Python (mypy --strict) and TypeScript (tsc --noEmit)
typecheck:
    uv run mypy
    pnpm typecheck

# Unit tests (Python: -m unit; web: Vitest)
test:
    @just _pytest unit
    pnpm -r --if-present --filter '!@hauskraft/acceptance-e2e' test

# Integration tests against Testcontainers Postgres (needs Docker)
test-int:
    @just _pytest integration

# Contract tests (schemas, OpenAPI snapshot)
contract:
    @just _pytest contract

# Regenerate OpenAPI, the TS client, the web plugin registry and theme types
gen: gen-openapi gen-client gen-plugins gen-theme-types gen-theme-fallback

# Export the OpenAPI contract (M0S-E03-05)
gen-openapi:
    {{ if path_exists("scripts/export_openapi.py") == "true" { "uv run python scripts/export_openapi.py" } else { "echo 'gen-openapi: not implemented yet (M0S-E03-05)'" } }}

# Generate the TypeScript API client (M0S-E06-05)
gen-client:
    {{ if path_exists("packages/sdk-ts/openapi-ts.config.ts") == "true" { "pnpm --filter @hauskraft/sdk-ts gen" } else { "echo 'gen-client: not implemented yet (M0S-E06-05)'" } }}

# Generate the build-time web plugin registry (M0S-E06-06)
gen-plugins:
    node scripts/gen-plugin-registry.mjs

# Generate theme types from packages/schemas/theme (M0S-E13-01)
gen-theme-types:
    {{ if path_exists("scripts/gen-theme-types.mjs") == "true" { "node scripts/gen-theme-types.mjs && uv run python scripts/gen_theme_types.py" } else { "echo 'gen-theme-types: not implemented yet (M0S-E13-01)'" } }}

# Default theme tokens as @hauskraft/ui's fallback stylesheet (M0S-E08-01)
gen-theme-fallback:
    uv run python scripts/gen_fallback_css.py

# Playwright end-to-end tests against a running stack (just demo)
e2e *args:
    pnpm --filter @hauskraft/acceptance-e2e exec playwright test {{ args }}

# Theme function-invariance suite
invariance:
    pnpm --filter @hauskraft/acceptance-e2e exec playwright test theme-invariance.spec.ts

# Spec-owned acceptance suite as CI runs it (add --live with the stack running)
acceptance *args:
    uv run python scripts/backlog_tools.py check
    uv run pytest tests --strict-status {{ args }}

# Build and start the full Compose demo (http://localhost:8080)
demo:
    docker compose up --build --wait

# Start the fresh, unseeded stack next to the demo (http://localhost:8081, M1S-E01-01)
fresh-up:
    docker compose -p hauskraft-fresh -f compose.yaml -f deploy/compose/compose.fresh.yaml up --wait

# Forget the fake model's recorded requests (the test stack's fake-llm service, M2S-E01-01)
fake-llm-reset:
    curl -fsS -X POST http://localhost:8090/_reset

# Empty the fresh stack: remove its containers and database volume, then start it again
fresh-reset:
    docker compose -p hauskraft-fresh -f compose.yaml -f deploy/compose/compose.fresh.yaml down -v
    docker compose -p hauskraft-fresh -f compose.yaml -f deploy/compose/compose.fresh.yaml up --wait

# Validate the built-in themes and the template, and doc-test the authoring guide (M0S-E13-09)
themes-validate *args:
    for theme in themes/builtin/*/ themes/template/; do uv run hauskraft themes validate --strict {{ args }} "$theme" || exit 1; done
    uv run python scripts/check-theme-docs.py

# lint + typecheck + unit tests
check: lint typecheck test

# Run package tests with one marker; missing folders are skipped and "no tests" (exit 5) is not a failure.
[private]
_pytest marker:
    dirs=$(for d in {{ py_tests }}; do if [ -d "$d" ]; then echo "$d"; fi; done); \
    uv run pytest $dirs -m {{ marker }} -q || [ $? -eq 5 ]
