<!-- SPDX-License-Identifier: MIT -->

# How to test HearthOS M0*

This page gets you from a clean clone to the M0* demo in a few minutes, then walks through the twelve milestone steps
by hand. Everything here is also automated (see [Run the acceptance suites](#run-the-acceptance-suites)).

## Prerequisites

- Docker 24+ with the Compose plugin (`docker compose version` prints v2.20 or newer).
- A free port 8080 (or pick another, see [Troubleshooting](#troubleshooting)).
- For the automated suites only: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 24 with pnpm (`corepack enable`).

## Start the demo

```bash
git clone https://github.com/hearthos/hearthos.git
cd hearthos
docker compose up --wait
```

Open <http://localhost:8080> and sign in as **demo** / **hearthos-demo**. A second adult, **alex**, uses the same
password. The first start builds the images and seeds the demo household; later starts reuse both.

Settings come from environment variables with demo defaults. To change them, copy
[`deploy/compose/.env.example`](../deploy/compose/.env.example) to `.env` in the repository root and edit it. Before
anyone else on your network can reach the stack, set `HEARTHOS_ENV=production`, a random `HEARTHOS_SECRET_KEY` and
put it behind HTTPS (`HEARTHOS_COOKIE_SECURE=true`).

## The milestone steps

1. `docker compose up --wait` finishes; <http://localhost:8080> shows the login page and
   <http://localhost:8080/api/v1/readyz> returns 200.
2. Sign in as `demo`. You land on **Today** with a **Tasks** widget: three seeded tasks (one done, one with a due
   date), in the **Default** theme.
3. Type "Buy milk" in **Add a task** and press Enter: it appears at the top, without a page reload.
4. Click the title "Buy milk", change it to "Buy oat milk", press Enter. Open **Tasks** (All tasks), set its due date
   to tomorrow, go back to **Today**: the widget shows the new title and a "Due …" badge.
5. Tick its checkbox: it shows as done ("Show done" lists it). Untick it: it is open again.
6. On **All tasks** (`/p/tasks`), filter Open / Done / All, sort by Created or Due date, and delete a task (it asks
   first).
7. **Activity** lists who added, updated, completed and deleted which task, with your name.
8. In **Settings → Appearance**, pick **Hackspace** and confirm. Colours, fonts, cards, icons and the navigation
   style change; every button, link and label from steps 3–7 is still there, in the same order, with the same names.
   A second browser signed in as `alex` shows Hackspace within about a minute, without reloading.
9. Set **This device** to Dark: only this browser turns dark; the other one stays as it was. After a reload each keeps
   its own mode.
10. In the account menu pick **Deutsch**: the interface switches and stays German after a reload. Theme names are not
    translated.
11. Run `docker compose down && docker compose up --wait` and sign in again: tasks, the Hackspace theme and the
    language are all still there.
12. CI is green on `main` (lint, typecheck, unit, contract, invariance, e2e, DCO).

## Try a theme package

1. Copy the template: `cp -r themes/template data/themes/my-theme`.
2. Edit `data/themes/my-theme/hearthos.plugin.json` (give it your own `id` and `name`) and the colours in
   `tokens.light.json` / `tokens.dark.json`. The guide is [docs/themes.md](themes.md).
3. Check it: `docker compose exec api hearthos themes validate /data/themes/my-theme` (or, with a local toolchain,
   `uv run hearthos themes validate data/themes/my-theme`).
4. `docker compose restart api`, then pick it in **Settings → Appearance**. If it has problems, it is listed with
   its reasons and cannot be selected.

## Reset

`docker compose down -v` removes the containers and the database volume. The next `docker compose up --wait` starts
from a fresh demo household. Your own themes in `data/themes/` are kept.

## Troubleshooting

- **Port 8080 is busy:** start with another port, e.g. `HEARTHOS_WEB_PORT=8081 docker compose up --wait`, and set
  `HEARTHOS_ALLOWED_ORIGINS=http://localhost:8081` too (sign-in is refused from origins the API does not know).
- **A theme does not show up or cannot be selected:** Settings → Appearance lists its problems (Show problems), or
  run `hearthos themes validate <folder>` as above. Themes are read when the API starts, so restart `api` after
  changes.
- **Something is not healthy:** `docker compose ps` shows each service; `docker compose logs api` shows the API's JSON
  logs, and <http://localhost:8080/api/v1/readyz> names the failing check (database, migrations, plugins, theme).

## Run the acceptance suites

The spec-owned suites live in [`tests/`](../tests); [docs/testing/README.md](testing/README.md) explains them.

```bash
# Static and contract checks (no stack needed)
uv sync
uv run python -m pytest tests

# API checks against the running stack, with the fixture themes mounted
docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait
HEARTHOS_BASE_URL=http://localhost:8080 uv run python -m pytest tests --live

# Browser checks (demo script, tasks, theme invariance) against the same stack
pnpm install
pnpm --filter @hearthos/acceptance-e2e exec playwright install --with-deps chromium
HEARTHOS_BASE_URL=http://localhost:8080 pnpm --filter @hearthos/acceptance-e2e test
```

`tests/e2e/demo.spec.ts` automates steps 1–11 with two browser sessions for steps 8–9. Step 11 restarts the stack
when `HEARTHOS_E2E_RESTART_CMD` is set, for example
`HEARTHOS_E2E_RESTART_CMD="docker compose -f compose.yaml -f deploy/compose/compose.test.yaml down && docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait"`.
