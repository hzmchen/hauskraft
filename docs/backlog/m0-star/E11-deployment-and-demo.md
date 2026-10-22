# E11 · Deployment & demo

**Goal:** One-command demo with persistent data, a themes volume and documented test steps.
**Out of scope:** HA add-on build, TLS automation, Kubernetes.
**Dependencies:** E07, E09, E13, E02.

---

## M0S-E11-01 · Images and Compose stack
- **Story:** As an operator, I want `docker compose up` to start everything, so that I can try Hauskraft without a toolchain.
- **AC:** Given the root `compose.yaml` (which `include`s `deploy/compose/compose.yaml`), when I run `docker compose up --wait`, then these services come up healthy:
  - `db` (`postgres:16-alpine`, named volume `hauskraft_pg`, healthcheck `pg_isready`)
  - `migrate` (one-shot: `hauskraft db upgrade && hauskraft seed --if-empty`)
  - `api` (depends on `migrate` completing successfully; healthcheck `/api/v1/readyz`; mounts `./data/themes:/data/themes:ro`, `HAUSKRAFT_THEME_PATHS=/app/themes/builtin,/data/themes`)
  - `web` (Caddy serving the built SPA and `reverse_proxy /api/* api:8000`, published on `8080`).
  - Same-origin, so no CORS. Images run as non-root.
  - Caddy sets a CSP: `default-src 'self'; script-src 'self' 'sha256-<mode-script-hash>'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`. No external origins are allowed, so themes cannot load remote fonts or images.
  - `./data/themes/` exists with a `README.txt` explaining how to drop in a theme folder.
  - `deploy/compose/compose.test.yaml` is an overlay for the acceptance stack: it mounts `./tests/fixtures/themes` read-only and appends it to `HAUSKRAFT_THEME_PATHS`, so the live suite can select fixture themes.
- **Tech:**
  - `services/core_api/Dockerfile`: multi-stage uv build, `python:3.13-slim`, `uv sync --frozen --no-dev`, copies plugins and `themes/builtin`.
  - `apps/web/Dockerfile`: Node 24 build, then `caddy:2-alpine`.
  - `.env.example` covers `HAUSKRAFT_SECRET_KEY`, `HAUSKRAFT_COOKIE_SECURE=false`, `HAUSKRAFT_ALLOWED_ORIGINS=http://localhost:8080`, `HAUSKRAFT_DEFAULT_THEME=dev.hauskraft.theme.default`, `HAUSKRAFT_WEB_PORT=8080`.
  - `style-src 'unsafe-inline'` is needed for react-grid-layout positioning styles; revisit with nonces later.
- **Tests:** CI e2e job; `docker compose config` lint; a Playwright check that the CSP header is present and no console CSP violations occur in any built-in theme.
- **Deps:** E07-03, E09-02, E13-05 · **Est:** M · **Labels:** area:deploy

## M0S-E11-02 · Seed command and demo fixture
- **Story:** As a tester, I want demo users and data on first start, so that I can log in immediately.
- **AC:**
  - Given an empty DB and `HAUSKRAFT_SEED_DEMO=true` (the default in compose), then `hauskraft seed` creates two adults from `fixtures/household/demo.json`: `demo` ("Demo Adult") and `alex` ("Alex Adult"), both with password `hauskraft-demo`, locale `en`, and calls each plugin's `seed()`.
  - The seed writes no theme setting, so the deployment uses `HAUSKRAFT_DEFAULT_THEME` (Default theme) until an adult picks another.
  - The command is a no-op if users exist.
  - Production mode refuses demo passwords unless `--force-demo`.
- **Tech:** `hauskraft_core/seed/`.
- **Tests:** Integration: idempotency; both users can log in.
- **Deps:** E07-04, E05-05 · **Est:** S · **Labels:** area:deploy, fixtures

## M0S-E11-03 · How-to-test doc and demo e2e
- **Story:** As a test user, I want clear instructions and an automated replay, so that anyone can verify M0*.
- **AC:**
  - `docs/how-to-test.md` lists prerequisites (Docker 24+), the 12 milestone steps from the backlog README, how to try a theme package (copy `themes/template` into `./data/themes/my-theme`, edit colours, `docker compose restart api`, pick it in Settings → Appearance), reset (`docker compose down -v`), troubleshooting (port 8080 busy → `HAUSKRAFT_WEB_PORT`; invalid theme → see reasons in Settings → Appearance or run `hauskraft themes validate`), and how to run the acceptance suites (`python -m pytest tests`, the same with `--live` against the stack, and the Playwright specs).
  - `tests/e2e/demo.spec.ts` (already written, spec-owned) automates steps 1–11, using two browser contexts for steps 8–9. CI sets `HAUSKRAFT_E2E_RESTART_CMD` so step 11 restarts the stack.
- **Tech:** Playwright projects: chromium (CI), firefox (nightly).
- **Tests:** `tests/e2e/demo.spec.ts`; `tests/acceptance/repo/test_deploy_files.py`.
- **Deps:** E11-01, E11-02, E10-03, E13-07 · **Est:** M · **Labels:** area:deploy, type:test
