# E06 · Members

**Goal:** Owners bring members in and look after their accounts: add, edit, deactivate, reactivate, reset a password,
always keeping at least one active owner (spec §2.3).
**Out of scope:** Deleting accounts, invitations by email or link, roles other than owner and adult.
**Dependencies:** E02, E07-01, E08-01, E09-01.

---

## Members API (contract, owner only)

| Method & path | Body | Success | Errors |
|---|---|---|---|
| `GET /api/v1/users` | — | 200 `[Member]`, ordered by `lower(display_name)`, then username, including deactivated members | 403 `policy_denied` |
| `GET /api/v1/users/{id}` | — | 200 `Member` | 403, 404 `not_found` |
| `POST /api/v1/users` | `{username, display_name, password, role?, locale?}` | 201 `Member` with `must_change_password: true`; `locale` defaults to the household's | 403, 409 `username_taken`, 422 `role_not_enabled` / `invalid_username` / `password_policy` |
| `PATCH /api/v1/users/{id}` | `{display_name?, role?}` | 200 `Member` | 403, 404, 409 `last_owner`, 422 `role_not_enabled` |
| `POST /api/v1/users/{id}/deactivate` | — | 200 `Member` | 403, 404, 409 `last_owner` |
| `POST /api/v1/users/{id}/reactivate` | — | 200 `Member` | 403, 404 |
| `POST /api/v1/users/{id}/password` | `{password}` (temporary) | 204 | 403, 404, 422 `own_account`, 422 `password_policy` |

- `Member = User + {is_active, created_at, last_login_at}`; `User = {id, username, display_name, role, locale,
  must_change_password}`. Never a hash, a session or an IP address.
- **Last owner:** any change that would leave zero active owners answers 409 `last_owner` and changes nothing. That
  covers demoting or deactivating the last active owner, including yourself.
- **Deactivate:** sets `is_active=false` and revokes all the member's sessions in the same transaction. Signing in
  with the correct password then answers 403 `account_deactivated`; with a wrong password it stays the generic 401.
  Deactivating an inactive member, or reactivating an active one, is a no-op 200 without an event.
- **Reset password:** sets the temporary password and `must_change_password=true`, and revokes all the member's
  sessions. Owners change their own password through `/me/password` (422 `own_account` here).
- **Events (ADR 0018):** `hauskraft.user.created`, `hauskraft.user.updated` (`changes` of `display_name` and/or `role`),
  `hauskraft.user.deactivated`, `hauskraft.user.reactivated`, `hauskraft.user.password_reset`. A PATCH that changes
  nothing emits nothing.

---

## M1S-E06-01 · Members list
- **Story:** As an owner, I want to see everyone in the household with their role and status, so that I know who can
  sign in.
- **AC:**
  - Given an owner, `GET /users` lists every account, deactivated ones included, with the `Member` fields;
    `GET /users/{id}` returns one, 404 for an unknown id.
  - Given an adult, both answer 403 `policy_denied`.
  - `POST /users` returns a `Member` and emits `hauskraft.user.created` (the forced password change for new accounts
    comes with E07-01).
- **Tech:** `users/router.py`, `users/service.py`, `auth/schemas.py` (`MemberOut`).
- **Tests:** Live: `tests/acceptance/api/test_members.py`, `test_account_events.py`.
- **Deps:** E02-01, E04-01, E09-01 · **Est:** S · **Labels:** area:api

## M1S-E06-02 · Edit a member and keep an owner
- **Story:** As an owner, I want to fix a member's display name or make them an owner, so that the household can
  share the admin work.
- **AC:**
  - Given an owner, `PATCH /users/{id}` changes `display_name` and/or `role` (`owner`/`adult`) and emits one
    `hauskraft.user.updated` with the changes.
  - Demoting the last active owner answers 409 `last_owner`.
  - The username can't be changed (unknown field → 422).
  - A role change takes effect at the member's next request: their session's `permissions` change, without
    signing in again.
- **Tech:** `users/service.py` (`update_member`, `_ensure_an_active_owner_remains`), with the owner count taken under
  a row lock to avoid races.
- **Tests:** Live: `test_members.py`, `test_first_run.py` (last-owner cases on the fresh stack). Unit: guard.
- **Deps:** E06-01, E02-02 · **Est:** M · **Labels:** area:api, area:auth

## M1S-E06-03 · Deactivate and reactivate
- **Story:** As an owner, I want to switch off an account without losing its history, so that someone who moved out
  can't sign in.
- **AC:**
  - Given an owner, `POST /users/{id}/deactivate` sets the member inactive, their open sessions get 401 at the next
    request, and their sign-in answers 403 `account_deactivated` (a wrong password still gives the generic 401).
  - Tasks and Activity entries keep the member's display name.
  - `POST /users/{id}/reactivate` lets them sign in again.
  - Deactivating the last active owner (including yourself) answers 409 `last_owner`.
  - Each effective change emits `hauskraft.user.deactivated` / `hauskraft.user.reactivated`.
- **Tech:** `users/service.py`, `auth/router.py` (login check after password verification), `auth/sessions.py`.
- **Tests:** Live: `test_members.py`, `test_first_run.py`, `test_account_events.py`.
- **Deps:** E06-02 · **Est:** M · **Labels:** area:api, area:auth, security

## M1S-E06-04 · Reset a member's password
- **Story:** As an owner, I want to give a member a temporary password, so that someone who forgot theirs can get back
  in without email.
- **AC:**
  - Given an owner, `POST /users/{id}/password` with a valid temporary password answers 204; the member's sessions
    end; signing in with the temporary password works and then requires a new password (E07-01).
  - Targeting yourself answers 422 `own_account`; a short password 422 `password_policy`.
  - Emits `hauskraft.user.password_reset`; the event and the response contain no password.
- **Tech:** `users/service.py` (`reset_password`).
- **Tests:** Live: `test_members.py`, `test_account_events.py`.
- **Deps:** E06-01, E07-01 · **Est:** S · **Labels:** area:api, area:auth, security

## M1S-E06-05 · Settings → Members
- **Story:** As an owner, I want to do all of this on one page, so that I never need the API or the CLI for everyday
  admin.
- **AC:**
  - Given an owner on `/settings/members`, the list "Members" shows each member's display name, username, role and,
    when deactivated, "Deactivated", with the per-member buttons in `docs/testing/ui-contract.md`.
  - "Add member" opens the dialog "Add member" (display name, username, role, temporary password with "At least 12
    characters"); on success the member appears in the list.
  - Edit, reset password and deactivate open their dialogs; deactivating asks for confirmation; reactivate is one
    click. A 409 `last_owner` shows "The household needs at least one active owner."
  - An adult never sees this section (E08-01) and is redirected from the URL.
- **Tech:** `apps/web/src/routes/_app/settings.members.tsx`.
- **Tests:** E2E: `tests/e2e/members.spec.ts`, `tests/e2e/basics.spec.ts` steps 3, 7–9. Vitest: dialogs.
- **Deps:** E06-02, E06-03, E06-04, E08-01 · **Est:** M · **Labels:** area:web, a11y

## M1S-E06-06 · CLI parity for recovery
- **Story:** As an operator, I want the same account operations on the command line, so that I can recover when no
  owner can sign in.
- **AC:**
  - `hauskraft users list [--json]` prints every account with role and status (JSON: a list of `Member`).
  - `hauskraft users create --role owner|adult` (default adult) prompts for the password; `--temporary` sets
    `must_change_password`.
  - `hauskraft users set-password USERNAME [--temporary]` and `hauskraft users deactivate|reactivate USERNAME` exist.
  - The CLI acts as the system actor, keeps the last-owner rule and emits the same events as the API.
- **Tech:** `cli.py` (Typer).
- **Tests:** Unit/integration with `CliRunner` (in-story).
- **Deps:** E06-03, E07-01 · **Est:** S · **Labels:** area:auth
