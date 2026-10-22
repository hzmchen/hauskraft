# E03 · First-run setup

**Goal:** A household starts from the browser: while no account exists, the app shows a setup wizard that creates
the household settings and the first owner (spec §2.3, ADR 0017).
**Out of scope:** Setup codes, importing data, choosing a theme during setup.
**Dependencies:** E02, E04-01, E09-01.

---

## Setup API (contract)

| Method & path | Who | Body | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/setup` | anyone | — | 200 `{required: boolean}` (true while there is no account) | — |
| `POST /api/v1/setup` | anyone, Origin-checked like login | `{household: {name, timezone, locale}, owner: {username, display_name, password}}` | 201 `Session` (with `permissions`) + `Set-Cookie`, as after login | 409 `setup_done`, 422 `invalid_timezone` / `invalid_username` / `password_policy` / validation, 403 `csrf_failed` (foreign Origin) |

- `name`: 1–80 characters after trimming. `timezone`: an IANA name the server knows (`zoneinfo`). `locale`: `en` or
  `de`. The owner gets `locale` from the household.
- The owner's `must_change_password` is `false`. The new account's `last_login_at` is set.
- Exactly one event: `hauskraft.user.created` with `actorid` = the new owner (ADR 0018).
- Concurrency: the check "no account exists" and the inserts run in one transaction under
  `pg_advisory_xact_lock`; of two simultaneous requests, exactly one gets 201.

---

## M1S-E03-01 · Setup API
- **Story:** As a parent installing Hauskraft, I want to create the household and my account in one step, so that I
  can start without the command line.
- **AC:**
  - Given an empty database, `GET /setup` answers `{"required": true}`. After a successful `POST /setup` it answers
    `{"required": false}`, and every further `POST /setup` answers 409 `setup_done`.
  - Given a valid body, `POST /setup` returns 201 with a `Session` for a new `owner`, sets the session cookie, stores
    the household settings (`GET /household` returns them) and emits `hauskraft.user.created`.
  - An unknown time zone answers 422 `invalid_timezone`; a short password 422 `password_policy`; a bad username 422
    `invalid_username`. Nothing is stored after a 422.
  - A request with a foreign `Origin` answers 403 `csrf_failed`.
  - Five concurrent valid requests produce exactly one 201 and four 409s.
  - Given a database with any account (demo seed or CLI), `GET /setup` is `{"required": false}` and `POST` is 409.
- **Tech:** `services/core_api/src/hauskraft_core/setup/` (router + service). The endpoint needs no session; the
  service acts as the system actor and calls `authorize(system, "setup.complete", …)`.
- **Tests:** Live: `tests/acceptance/api/test_first_run.py` (fresh stack for the happy path and concurrency; demo stack
  for 409). Integration: transaction and lock.
- **Deps:** E02-02, E04-01, E09-01 · **Est:** M · **Labels:** area:auth, area:api

## M1S-E03-02 · Setup wizard
- **Story:** As a parent installing Hauskraft, I want a short, friendly setup page, so that I know exactly what to
  enter.
- **AC:**
  - Given setup is required, when I open `/`, `/login` or any app route, then I am sent to `/setup`.
  - Given setup is not required, `/setup` redirects to `/login` (or `/today` when signed in).
  - The page has the names in `docs/testing/ui-contract.md` ("Set up your household"): household name, language,
    time zone (defaulting to the browser's zone when the server knows it), your name, username, password and repeat
    password, with the hint "At least 12 characters" shown before typing.
  - Mismatched passwords show "Passwords do not match" without a request. API errors show their localised message
    next to the field.
  - On success I land on `/today`, signed in, in the chosen language.
  - The page uses the active deployment theme and passes axe without serious or critical issues. (No owner exists
    yet to switch themes, so cross-theme invariance is not checked for this page.)
- **Tech:** `apps/web/src/routes/setup.tsx`; the root route checks `GET /setup` once per load (TanStack Query, cached).
- **Tests:** E2E: `tests/e2e/basics.spec.ts` steps 1–2 (including axe). Vitest: redirects, mismatch check.
- **Deps:** E03-01 · **Est:** M · **Labels:** area:web, a11y

## M1S-E03-03 · Demo household settings
- **Story:** As a tester, I want the demo household to have household settings too, so that the demo looks like a
  real setup.
- **AC:**
  - Given an empty database and `HAUSKRAFT_SEED_DEMO=true`, then the seed stores the household name "Demo household",
    time zone `Europe/Berlin` and default language `en`.
  - The seed still writes no theme setting.
- **Tech:** `fixtures/household/demo.json` gains a `household` object; `hauskraft_core/seed/`.
- **Tests:** Live: `test_household_settings.py` (demo stack values). Integration: seed idempotency.
- **Deps:** E04-01 · **Est:** S · **Labels:** area:deploy, fixtures

## M1S-E03-04 · Web port on localhost by default
- **Story:** As an operator, I want a fresh install reachable only from my machine until I decide otherwise, so that
  nobody else on the network can claim it during setup.
- **AC:**
  - Given `deploy/compose/compose.yaml`, the `web` port is published as
    `${HAUSKRAFT_WEB_BIND:-127.0.0.1}:${HAUSKRAFT_WEB_PORT:-8080}:8080`.
  - `.env.example` documents `HAUSKRAFT_WEB_BIND` with a warning that LAN exposure needs TLS (spec §11.3).
  - The M0* demo still works on http://localhost:8080.
- **Tech:** Compose and `.env.example` only.
- **Tests:** `tests/acceptance/repo/test_m1_deploy_and_docs.py`.
- **Deps:** — (M0* done) · **Est:** S · **Labels:** area:deploy, security
