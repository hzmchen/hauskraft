# SPDX-License-Identifier: AGPL-3.0-or-later
# core-api image (M0S-E11-01): uv workspace install on python:3.13-slim, runs as a non-root user.
# The source tree keeps its repository layout under /app: migrations, JSON schemas, built-in themes
# and the demo fixture are found relative to the code.
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependencies first (cached while only sources change).
COPY pyproject.toml uv.lock ./
COPY services/core_api/pyproject.toml services/core_api/
COPY packages/sdk-py/pyproject.toml packages/sdk-py/
COPY plugins/official/tasks/backend/pyproject.toml plugins/official/tasks/backend/
RUN mkdir -p services/core_api/src/hearthos_core packages/sdk-py/src/hearthos_sdk plugins/official/tasks/backend/src/hearthos_tasks \
 && uv sync --frozen --no-dev --all-packages --no-install-workspace
COPY services/core_api services/core_api
COPY packages/sdk-py packages/sdk-py
COPY packages/schemas packages/schemas
COPY plugins/official plugins/official
COPY themes/builtin themes/builtin
COPY fixtures fixtures
RUN uv sync --frozen --no-dev --all-packages

FROM python:3.13-slim
RUN useradd --system --uid 10001 --home-dir /app hearthos
WORKDIR /app
COPY --from=build --chown=hearthos:hearthos /app /app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HEARTHOS_SCHEMAS_DIR=/app/packages/schemas \
    HEARTHOS_PLUGIN_PATHS=/app/plugins/official \
    HEARTHOS_THEME_PATHS=/app/themes/builtin
USER hearthos
EXPOSE 8000
CMD ["uvicorn", "hearthos_core.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
