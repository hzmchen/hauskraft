# E02 · CI & quality gates

**Goal:** Every PR is gated by lint, typecheck, unit, contract, theme invariance, e2e and DCO.
**Out of scope:** release publishing and image signing.
**Dependencies:** E01.

---

## M0S-E02-01 · CI workflow: lint + typecheck + unit
- **Story:** As a maintainer, I want fast PR feedback, so that broken code never lands.
- **AC:**
  - Given a PR, when CI runs, then jobs `lint`, `typecheck`, `unit-py`, `unit-web` and `acceptance` run in parallel, finish in under 8 min, and failing any of them blocks merge.
  - The `acceptance` job runs `python scripts/backlog_tools.py check` and `python -m pytest tests --strict-status`. Red stories report as xfail; a red story whose tests all pass fails the job until it is flipped to green; a green story's failing test fails the job.
- **Tech:**
  - `.github/workflows/ci.yml` with `astral-sh/setup-uv` (cache on `uv.lock`), `actions/setup-node` with the pnpm cache, and `concurrency` cancel-in-progress.
  - Commands: `uv run pytest -m unit` and `pnpm -r test -- --run`.
- **Tests:** Self-verifying.
- **Deps:** E01-04 · **Est:** S · **Labels:** area:ci

## M0S-E02-02 · Integration and contract job
- **Story:** As a maintainer, I want DB-backed tests and contract checks in CI, so that API drift is caught.
- **AC:**
  - Given a PR, when the `contract` job runs, then `pytest -m "integration or contract"` uses Testcontainers Postgres 16.
  - `just gen && git diff --exit-code` fails if the OpenAPI file, generated TS client or plugin registry is stale.
  - All `hauskraft.plugin.json` files validate against the manifest schema, and all `themes/builtin/*` pass `hauskraft themes validate` (once E13-09 lands).
- **Tech:** Ubuntu runners have Docker. Keep the Testcontainers Ryuk default (enabled).
- **Tests:** Self-verifying.
- **Deps:** E02-01, E04-04 · **Est:** S · **Labels:** area:ci

## M0S-E02-03 · E2E job with Compose and Playwright
- **Story:** As a maintainer, I want the demo script and the theme invariance suite executed on every PR to `main`, so that "a test user can interact" and "themes never change function" stay true.
- **AC:** Given a PR, when `e2e.yml` runs, then it builds images, runs `docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait`, runs `python -m pytest tests --live --strict-status` and `pnpm --filter @hauskraft/acceptance-e2e exec playwright test` (specs `demo`, `tasks`, `theme-invariance` in `tests/e2e/`) against `http://localhost:8080` with `HAUSKRAFT_E2E_RESTART_CMD` set, and uploads trace and report on failure.
- **Tech:** `@playwright/test@1.64.x`; `npx playwright install --with-deps chromium`; `reuseExistingServer` off in CI.
- **Tests:** `tests/e2e/demo.spec.ts` (E11-03), `tests/e2e/theme-invariance.spec.ts` (E13-08), `tests/acceptance/api/`.
- **Deps:** E11-01 · **Est:** M · **Labels:** area:ci

## M0S-E02-04 · DCO, REUSE and licence checks
- **Story:** As a maintainer, I want sign-off and licence headers verified, so that provenance is clean for the AGPL core and the MIT plugin-facing parts.
- **AC:**
  - Given a PR with an unsigned commit, when CI runs, then the DCO check fails with instructions (`git commit -s --amend`).
  - `reuse lint` passes.
  - A path check enforces the licence map: `AGPL-3.0-or-later` under `services/**` and `apps/**`; `MIT` under `packages/**`, `plugins/official/**`, `themes/**` and `integrations/**`; font files under `themes/**/assets/fonts/` carry `OFL-1.1`.
- **Tech:**
  - DCO GitHub App or a DCO action. `REUSE.toml` annotations cover generated and binary files (fonts, images, sprites).
  - `scripts/check-licence-map.py [--root DIR]` (default: repo root) reads SPDX headers / REUSE annotations, compares against the map, lists every offending file and exits non-zero on any mismatch.
  - Dependency licence allowlist (`pip-licenses` / `license-checker`) runs non-blocking in M0*.
- **Tests:** Unit test for `check-licence-map.py` with a fixture tree.
- **Deps:** E12-03 · **Est:** S · **Labels:** area:ci, legal

## M0S-E02-05 · Dependency hygiene
- **Story:** As an operator, I want pinned, auto-updated dependencies and a supply-chain check, so that incidents like the May 11, 2026 TanStack npm compromise (GHSA-g7cv-rxg3-hmpx: 84 malicious versions across 42 `@tanstack/*` packages) are caught.
- **AC:** Given the repo, then Dependabot (uv, npm, github-actions, docker) opens weekly grouped PRs, `pnpm audit --prod` and `uv` lock checks run in CI, and the lockfile contains no denylisted versions.
- **Tech:** `.github/dependabot.yml`. Denylist script `scripts/check-denylist.mjs [lockfile]` (default `pnpm-lock.yaml`; prints offending versions and exits non-zero) covers `@tanstack/react-router@1.169.5|1.169.8` and `@tanstack/router-plugin@1.167.38|1.167.41`.
- **Tests:** Unit test for the denylist script.
- **Deps:** E02-01 · **Est:** S · **Labels:** area:ci
