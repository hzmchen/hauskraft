# E01 · Fresh stack & CI

**Goal:** First-run behaviour is testable: a second, unseeded stack runs next to the demo stack, locally and in CI,
and tests can reset it.
**Out of scope:** Release images, a production compose file (Linear backlog).
**Dependencies:** none beyond M0*.

---

## Contract: the fresh stack

| Item | Value |
|---|---|
| Overlay | `deploy/compose/compose.fresh.yaml`, used as `docker compose -p hauskraft-fresh -f compose.yaml -f deploy/compose/compose.fresh.yaml up --wait` |
| Seed | `HAUSKRAFT_SEED_DEMO=false` for `migrate` and `api` |
| Web port | `8081` (`HAUSKRAFT_ALLOWED_ORIGINS=http://localhost:8081`) |
| Database port | not published (no clash with the demo stack's `5432`) |
| Test variables | `HAUSKRAFT_FRESH_BASE_URL` (default `http://localhost:8081`), `HAUSKRAFT_FRESH_RESET_CMD` (a shell command that leaves an empty, healthy fresh stack) |
| Shortcuts | `just fresh-up`, `just fresh-reset` (down with volumes, then up `--wait`) |

---

## M1S-E01-01 · Fresh-stack overlay and reset
- **Story:** As a tester, I want an unseeded stack next to the demo stack, so that I can test first-run setup without
  touching the demo household.
- **AC:**
  - Given the repository, when I run `just fresh-up`, then a second stack named `hauskraft-fresh` starts healthy with
    an empty database, serves the app on http://localhost:8081, and the demo stack on 8080 keeps running.
  - `just fresh-reset` removes the fresh stack's volumes and starts it again; afterwards `GET /api/v1/setup` on 8081
    answers `{"required": true}`.
  - The overlay publishes no database port and sets `HAUSKRAFT_SEED_DEMO` to `false`.
  - `docs/testing/README.md` explains the fresh stack and both test variables.
- **Tech:** Compose `!reset`/`!override` for `ports`; project name via `-p`. The overlay is the only new file in
  `deploy/compose/`.
- **Tests:** `tests/acceptance/repo/test_m1_deploy_and_docs.py` (static checks of the overlay and the justfile).
  Manual: both stacks up at once.
- **Deps:** — (M0* done) · **Est:** S · **Labels:** area:deploy, type:test

## M1S-E01-02 · CI runs the fresh-stack suites
- **Story:** As a maintainer, I want CI to run the first-run tests on every PR, so that setup can't silently break.
- **AC:**
  - Given the `e2e` workflow, when it runs, then it starts the fresh stack next to the demo stack and sets
    `HAUSKRAFT_FRESH_BASE_URL` and `HAUSKRAFT_FRESH_RESET_CMD` for both the live pytest step and the Playwright step.
  - Fresh-stack logs are uploaded on failure, like the demo stack's.
  - The job stays within its 45-minute limit.
- **Tech:** `.github/workflows/e2e.yml` only.
- **Tests:** `tests/acceptance/repo/test_m1_deploy_and_docs.py` (workflow shape); the first green run of the
  fresh-marked tests.
- **Deps:** E01-01 · **Est:** S · **Labels:** area:ci
