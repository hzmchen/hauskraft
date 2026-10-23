# E02 · Roles & permissions

**Goal:** Two roles, `owner` and `adult`, enforced in one place behind `authorize()` (spec §2.3, ADR 0016), and
known to the web app without duplicating the rules.
**Out of scope:** Cedar, approvals, roles other than owner and adult, per-resource sharing.
**Dependencies:** none beyond M0*.

---

## Contract: the permission table

`RolePolicy.authorize(actor, action, …)` allows an action when the actor's role is in the action's set. Actions that
are not listed are denied. A denial raises `PolicyDeniedError`: 403 problem+json with `code` `policy_denied`, no row
and no event.

| Action | `owner` | `adult` | Used by |
|---|---|---|---|
| `task.create`, `task.update`, `task.delete` | ✓ | ✓ | tasks plugin |
| `dashboard.layout.set` | ✓ | ✓ | own Today layout |
| `session.create`, `session.revoke` | ✓ | ✓ | sign-in, sign-out, own sessions |
| `user.update_self`, `user.change_password` | ✓ | ✓ | `/me` (own account only, structurally) |
| `settings.theme.set` | ✓ | — | household theme |
| `settings.household.set` | ✓ | — | household settings |
| `plugin.toggle` | ✓ | — | enable or disable plugins |
| `user.list`, `user.create`, `user.update`, `user.deactivate`, `user.reactivate`, `user.reset_password` | ✓ | — | members |

The system actor (CLI, seed, plugin sync, setup) has role `owner`; `plugin.sync` and `setup.complete` are allowed
for `kind == "system"` only. `HAUSKRAFT_POLICY` accepts `roles` (default), `noop` and `deny_all` (both test-only).

`Session` (from `POST /auth/login`, `GET /auth/session`, `POST /setup`) gains `permissions`: the sorted list of
actions from this table that the signed-in user's role allows. The web app uses it to show or hide owner-only
controls; the API stays the authority.

---

## M1S-E02-01 · `RolePolicy` behind `authorize()`
- **Story:** As an owner, I want only owners to change household-wide things, so that the household's setup doesn't
  change by accident.
- **AC:**
  - Given an adult, when they `PUT /settings/theme`, `PATCH /plugins/{id}` or `PATCH /household`, then the response is
    403 `policy_denied`, and the theme, the plugin and the settings are unchanged with no new Activity entry.
  - Given an adult, task writes and their own dashboard layout still succeed.
  - Given an owner, all of the above succeed.
  - An action missing from the table is denied (unit test with a made-up action).
  - `HAUSKRAFT_POLICY` defaults to `roles`; `noop` and `deny_all` keep working for tests.
- **Tech:** `policy/__init__.py` (`RolePolicy`, the table as one mapping), `settings.py`. No router changes: services
  already call `authorize()`.
- **Tests:** Unit: every row of the table for both roles, unknown action, system actor. Live:
  `tests/acceptance/api/test_roles_and_permissions.py`.
- **Deps:** — (M0* done) · **Est:** M · **Labels:** area:auth, security

## M1S-E02-02 · Owner role in the users API
- **Story:** As an owner, I want to add another owner, so that two parents can both run the household.
- **AC:**
  - Given an owner, when they `POST /users` with `role` `owner` or `adult` (default `adult`), then the account is
    created with that role.
  - Any other role (`teen`, `kid`, `caregiver`, `property_manager`, `tenant`, `guest`) answers 422 `role_not_enabled`.
  - An adult calling `POST /users` gets 403 `policy_denied` (the M0* "any adult may create users" rule ends here).
  - `RoleNotEnabledInM0Error` is renamed to `RoleNotEnabledError`; the problem `code` stays `role_not_enabled`.
- **Tech:** `users/service.py`, `auth/schemas.py` (`UserCreate.role`).
- **Tests:** Live: `test_members.py`, `test_roles_and_permissions.py`, and the M0* `test_auth_and_users.py`
  (`test_role_cannot_be_chosen` now uses `kid`). Unit: role guard.
- **Deps:** E02-01 · **Est:** S · **Labels:** area:auth

## M1S-E02-03 · Owner migration and demo roles
- **Story:** As an operator upgrading from M0*, I want my household to have an owner afterwards, so that someone can
  still change the theme and manage members.
- **AC:**
  - Given a database without an active owner, when `hauskraft db upgrade` runs, then the oldest active account (by
    `created_at`, then `id`) becomes `owner`. A database with an owner, or with no accounts, is left unchanged.
  - Given an empty database and `HAUSKRAFT_SEED_DEMO=true`, then the seed creates `demo` as `owner` and `alex` as
    `adult` (display names unchanged: "Demo Adult", "Alex Adult").
- **Tech:** Core Alembic data migration; `fixtures/household/demo.json` gains `role` per user.
- **Tests:** Integration (Testcontainers): the migration on three datasets (no owner, owner, empty). Live:
  `test_roles_and_permissions.py` (demo is owner, alex is adult).
- **Deps:** E02-02 · **Est:** S · **Labels:** area:db, fixtures

## M1S-E02-04 · Permissions in the session
- **Story:** As the web app, I want to know what the signed-in user may do, so that I can show owner-only controls
  only to owners without copying the rules.
- **AC:**
  - Given an owner, `GET /auth/session` returns `permissions` containing at least `settings.theme.set`,
    `settings.household.set`, `plugin.toggle` and `user.create`.
  - Given an adult, `permissions` contains `task.create` and none of the owner-only actions.
  - `permissions` comes from the same table as `RolePolicy` (single source; unit test).
- **Tech:** `auth/schemas.py` (`SessionOut.permissions`), `just gen` for the TS client.
- **Tests:** Live: `test_roles_and_permissions.py`. Contract: OpenAPI.
- **Deps:** E02-01 · **Est:** S · **Labels:** area:auth, area:api
