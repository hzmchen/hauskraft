# E04 · Household settings

**Goal:** The household has a name, a time zone and a default language that owners manage, and the time zone decides
what "today" means everywhere (spec §2.3, §9.1).
**Out of scope:** Week start, date formats, units, address, multiple households.
**Dependencies:** E02-01, E08-01, E09-01.

---

## Household API (contract)

| Method & path | Who | Body | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/household` | any signed-in member | — | 200 `Household` | 401 |
| `PATCH /api/v1/household` | owner | `{name?, timezone?, locale?}` | 200 `Household` | 403 `policy_denied`, 422 `invalid_timezone` / validation |

`Household = {name: string, timezone: string, locale: "en" | "de"}`. Stored as deployment settings
`household.name`, `household.timezone`, `household.locale`. Defaults when unset (for example right after an M0*
upgrade): name "Household", time zone from `HAUSKRAFT_DEFAULT_TIMEZONE` (default `Europe/Berlin`), locale `en`.

A PATCH that changes at least one value emits one `hauskraft.settings.household_changed` event with
`data.changes = {field: {from, to}}` for the changed fields only. A PATCH that changes nothing emits nothing.

---

## M1S-E04-01 · Household settings API
- **Story:** As an owner, I want to name the household and set its time zone and language, so that the app fits us.
- **AC:**
  - Given any member, `GET /household` returns the three values (defaults when unset).
  - Given an owner, `PATCH /household` with any subset updates those values, returns the new state and emits one
    `hauskraft.settings.household_changed` event listing only the changed fields; an unchanged PATCH emits nothing.
  - An unknown time zone answers 422 `invalid_timezone`; an empty name 422.
  - An adult gets 403 `policy_denied` and nothing changes.
- **Tech:** `settings_store/` (service and repository, like `set_theme`), `household/router.py`.
- **Tests:** Live: `tests/acceptance/api/test_household_settings.py`. Unit: validation, change detection.
- **Deps:** E02-01, E09-01 · **Est:** M · **Labels:** area:api

## M1S-E04-02 · Settings → Household
- **Story:** As an owner, I want a page for the household settings, so that I can change them without the API.
- **AC:**
  - Given an owner on `/settings/household`, the form shows the current name, time zone (a list of IANA names) and
    default language with the names in `docs/testing/ui-contract.md`; "Save household" saves and shows "Household
    saved".
  - Validation errors appear next to the field.
  - An adult never sees this section (E08-01) and is redirected from the URL.
- **Tech:** `apps/web/src/routes/_app/settings.household.tsx`.
- **Tests:** E2E: `tests/e2e/settings.spec.ts`, `tests/e2e/basics.spec.ts` step 10. Vitest: form states.
- **Deps:** E04-01, E08-01 · **Est:** S · **Labels:** area:web

## M1S-E04-03 · The household time zone decides "today"
- **Story:** As a household member who travels, I want due badges to count days in our home time zone, so that "Today"
  means the same thing on every device.
- **AC:**
  - Given the household time zone `Pacific/Kiritimati` (UTC+14) and a browser in `Europe/Berlin` at 2026-11-02 23:30,
    when a task is due on 2026-11-03, then its badge says "Today" in the widget and on All tasks, and a task due on
    2026-11-02 says "Overdue".
  - Changing the household time zone updates the badges within one refetch (no reload needed).
- **Tech:** Plugins get the household time zone from the shell through `useHost()` in `@hauskraft/sdk-ts` (no core
  import); `DueBadge` computes "today" with `Intl.DateTimeFormat(…, { timeZone })`.
- **Tests:** E2E: `tests/e2e/household.spec.ts` (fixed browser clock). Vitest: `DueBadge` across zones.
- **Deps:** E04-01 · **Est:** S · **Labels:** area:tasks, area:web

## M1S-E04-04 · Household name in the browser title
- **Story:** As a member with several tabs open, I want the household name in the browser title, so that I can find
  the tab.
- **AC:**
  - Given a signed-in member on any app page, the document title is `<page heading> · <household name>`, for example
    "Today · Demo household" or "Heute · Familie Müller".
  - Signed-out pages (login, setup, change password) use "Hauskraft".
  - The title follows a household rename within one refetch.
- **Tech:** One `useDocumentTitle(pageTitle)` hook in the shell; plugin pages pass their heading through `useHost()`.
  The household query refetches like theme metadata: every 60 seconds and on window focus.
- **Tests:** E2E: `tests/e2e/household.spec.ts`, `tests/e2e/basics.spec.ts`.
- **Deps:** E04-01 · **Est:** S · **Labels:** area:web
