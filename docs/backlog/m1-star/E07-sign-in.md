# E07 · Sign-in

**Goal:** Signing in handles the cases a real household meets: a temporary password, an expired session and a
deactivated account, with clear messages and password-manager-friendly forms (spec §2.3).
**Out of scope:** "Remember me" options, MFA, password-reset email, account lockout beyond the M0* rate limit.
**Dependencies:** E05-01, E06-03.

---

## Contract: forced password change

- `users.must_change_password` (boolean, default false) is set for accounts an owner creates through `POST /users`
  and for passwords an owner resets (E06-04). It is cleared by `POST /me/password`. Setup, the demo seed and the CLI
  without `--temporary` leave it false.
- While it is true, every authenticated API request answers 403 `password_change_required`, except:
  `GET /auth/session`, `POST /auth/logout`, `POST /auth/logout-everywhere`, `GET /me`, `POST /me/password`,
  `GET /household`, `GET /theme`, `GET /theme/active.css`, `GET /theme/assets/…`.
- `User.must_change_password` is part of `GET /me` and `Session.user`.

## Contract: messages (en; de in the locale files)

| Case | Where | Text |
|---|---|---|
| Session ended (any 401 while the app believed it was signed in) | login page, role `status` | "Your session has ended. Please sign in again." |
| Account deactivated (403 `account_deactivated`) | login page, role `alert` | "This account is deactivated. Ask an owner of your household." |
| Password rules | every form that sets a password | "At least 12 characters" (visible before typing) |

---

## M1S-E07-01 · Forced password change (API)
- **Story:** As an owner who handed out a temporary password, I want the member to replace it before doing anything
  else, so that only they know their password.
- **AC:**
  - Given an account an owner just created (or reset), when it signs in, then `Session.user.must_change_password` is
    true, `GET /tasks` answers 403 `password_change_required`, and the allowlisted requests work.
  - After `POST /me/password` succeeds, the flag is false and `GET /tasks` works in the same session.
  - Accounts from setup, the demo seed or the CLI without `--temporary` are not affected.
- **Tech:** Core Alembic migration (`must_change_password`); a dependency next to `current_actor` that enforces the
  allowlist; `users/service.py` sets the flag in `create_user(…, temporary=True)`.
- **Tests:** Live: `tests/acceptance/api/test_members.py`, `test_account.py`. Unit: allowlist.
- **Deps:** E05-01, E02-02, E04-01 · **Est:** S · **Labels:** area:auth, security

## M1S-E07-02 · Choose a new password page
- **Story:** As a member with a temporary password, I want to be taken straight to a page where I choose my own,
  so that I'm not confused by errors.
- **AC:**
  - Given `must_change_password`, after signing in (or on any app route) I am sent to `/change-password`
    ("Choose a new password"), which explains why and asks for the current (temporary) password, the new one and the
    repeat, with the hint "At least 12 characters".
  - "Save password" saves and continues to the original `redirect` target or `/today`.
  - The page has no navigation besides the account menu's "Sign out".
- **Tech:** `apps/web/src/routes/change-password.tsx`; the `_app` guard checks the flag from the session query.
- **Tests:** E2E: `tests/e2e/account.spec.ts`, `tests/e2e/basics.spec.ts` steps 4 and 7.
- **Deps:** E07-01 · **Est:** S · **Labels:** area:web, a11y

## M1S-E07-03 · Session ended
- **Story:** As a member whose session ended (expired, signed out elsewhere, or deactivated), I want to understand
  what happened and get back to where I was, so that I don't lose my place.
- **AC:**
  - Given an open app page, when a request answers 401, then the app clears its cache and goes to
    `/login?redirect=<current path and search>&reason=expired`, which shows "Your session has ended. Please sign in
    again." as a status message.
  - Signing in returns to the `redirect` target. Only same-origin relative paths starting with a single `/` are
    accepted; anything else falls back to `/today`.
  - Signing out on purpose shows no such message.
- **Tech:** One global handler in the QueryClient (query and mutation caches) in `apps/web`.
- **Tests:** E2E: `tests/e2e/account.spec.ts`, `tests/e2e/basics.spec.ts` step 11. Vitest: redirect sanitising.
- **Deps:** — (M0* done) · **Est:** S · **Labels:** area:web, security

## M1S-E07-04 · Deactivated message, password hints, autocomplete
- **Story:** As a member, I want clear messages and forms my password manager understands, so that signing in is easy.
- **AC:**
  - Given a deactivated account with the correct password, the login page shows the deactivated message as an alert.
    A wrong password still shows the M0* generic message.
  - `autocomplete`: Username `username`; the login password `current-password`; every "Current password"
    `current-password`; every new or temporary password field `new-password`.
  - Every form that sets a password shows "At least 12 characters" before typing.
- **Tech:** `routes/login.tsx` and the password forms.
- **Tests:** E2E: `tests/e2e/account.spec.ts`, `tests/e2e/basics.spec.ts` step 8.
- **Deps:** E06-03, E07-02 · **Est:** S · **Labels:** area:web, a11y
