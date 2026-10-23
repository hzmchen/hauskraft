# E05 · My account

**Goal:** Every member manages their own profile, password and signed-in devices (spec §2.3).
**Out of scope:** Avatars, MFA, email, account deletion.
**Dependencies:** E08-01, E09-01.

---

## Account API (contract)

| Method & path | Who | Body | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/me` / `PATCH /api/v1/me` | member | `{display_name?, locale?}` | 200 `User` | 401, 422 |
| `POST /api/v1/me/password` | member | `{current_password, new_password}` | 204 | 422 `wrong_password`, 422 `password_policy`, 429 `rate_limited` |
| `GET /api/v1/me/sessions` | member | — | 200 `[SessionInfo]`, newest `last_seen_at` first | 401 |
| `DELETE /api/v1/me/sessions/{id}` | member | — | 204 | 404 `not_found` (unknown, revoked or another member's) |
| `POST /api/v1/auth/logout-everywhere` | member | — | 204, cookie cleared | 401 |

- `User` gains `must_change_password: boolean` (E07-01).
- `SessionInfo = {id, device, created_at, last_seen_at, current}`. `id` is an opaque public identifier, never the
  cookie token or its stored hash. `device` is a short description derived from the User-Agent (for example
  "Firefox on Linux"), or "Unknown device". IP addresses are not returned.
- Changing the display name emits `hauskraft.user.updated` (ADR 0018); changing only `locale` emits nothing.
- A password change revokes every other session of the member, keeps the current one, clears
  `must_change_password` and emits `hauskraft.user.password_changed`. Wrong current passwords count towards the login
  rate limit for that username.

---

## M1S-E05-01 · Change my password
- **Story:** As a member, I want to change my password, so that I can replace a temporary or leaked one.
- **AC:**
  - Given my correct current password and a new one that meets the policy (12–128 characters), when I
    `POST /me/password`, then I get 204, the new password works for sign-in, the old one doesn't, my other sessions
    end, this session keeps working, and Activity gets `hauskraft.user.password_changed`.
  - A wrong current password answers 422 `wrong_password`; a short new one 422 `password_policy`; nothing changes.
  - Repeated wrong current passwords hit the rate limit (429 `rate_limited`).
  - Changing my display name with `PATCH /me` emits `hauskraft.user.updated`; changing only `locale` emits nothing.
- **Tech:** `users/service.py` (`change_own_password`), `users/router.py`, `auth/sessions.py`
  (`revoke_all_for(user, except_session)`).
- **Tests:** Live: `tests/acceptance/api/test_account.py`, `test_account_events.py`. Unit: revocation.
- **Deps:** E09-01 · **Est:** S · **Labels:** area:auth, security

## M1S-E05-02 · My sessions
- **Story:** As a member, I want to see where I'm signed in and end sessions I don't recognise, so that a lost phone
  doesn't keep access.
- **AC:**
  - Given two signed-in browsers, `GET /me/sessions` lists both with `device`, `created_at`, `last_seen_at`, and
    `current: true` only for the calling session. Revoked and expired sessions are not listed.
  - `DELETE /me/sessions/{id}` for my other session ends it (that browser gets 401 next); an unknown id, or another
    member's, answers 404.
  - `POST /auth/logout-everywhere` ends all my sessions including this one and clears the cookie.
  - No response contains a token, a hash or an IP address.
- **Tech:** `auth/sessions.py` (public id column or derived id), `auth/router.py`, `users/router.py`. A small
  User-Agent parser without a new dependency.
- **Tests:** Live: `tests/acceptance/api/test_account.py`. Unit: device descriptions.
- **Deps:** — (M0* done) · **Est:** M · **Labels:** area:auth, security

## M1S-E05-03 · Settings → Account: profile and password
- **Story:** As a member, I want one page for my name, language and password, so that I find them easily.
- **AC:**
  - Given `/settings/account`, the region "Profile" shows "Display name" and "Language", and "Save profile" saves
    and shows "Profile saved". The UI language switches right away.
  - The region "Password" has "Current password", "New password", "Repeat new password" with the hint "At least 12
    characters"; "Change password" shows "Password changed" on success, "Passwords do not match" without a request,
    and "The current password is wrong." for 422 `wrong_password`.
  - The username is shown read-only.
- **Tech:** `apps/web/src/routes/_app/settings.account.tsx`.
- **Tests:** E2E: `tests/e2e/account.spec.ts`, `tests/e2e/basics.spec.ts` step 6. Vitest: form states.
- **Deps:** E05-01, E08-01 · **Est:** M · **Labels:** area:web, a11y

## M1S-E05-04 · Settings → Account: devices
- **Story:** As a member, I want to see and end my sessions in the app, so that I don't need the API for it.
- **AC:**
  - The region "Devices" contains the list "Signed-in devices": one item per session with its device description and
    last activity. The current one says "This device" and has no sign-out button; every other item has a "Sign out"
    button that ends that session and removes the item.
  - "Sign out everywhere" asks "Sign out everywhere?" (buttons "Sign out everywhere", "Cancel") and then returns to
    the login page.
- **Tech:** Same route as E05-03.
- **Tests:** E2E: `tests/e2e/account.spec.ts`, `tests/e2e/basics.spec.ts` steps 6 and 11.
- **Deps:** E05-02, E05-03 · **Est:** S · **Labels:** area:web
