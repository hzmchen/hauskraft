# E05 · Auth & users

**Goal:** Local username/password login with server-side sessions and CSRF protection, plus an OIDC-ready seam.
**Out of scope:** OIDC, password reset email, MFA and RBAC enforcement.
**Dependencies:** E04.

---

## Auth API (contract)

| Method & path | Body | Success | Errors |
|---|---|---|---|
| `POST /api/v1/auth/login` | `{username, password}` | 200 `Session` + `Set-Cookie` | 401 `invalid_credentials`, 429 `rate_limited` |
| `POST /api/v1/auth/logout` | — (CSRF header) | 204, cookie cleared | 401 |
| `GET /api/v1/auth/session` | — | 200 `Session` | 401 |
| `GET /api/v1/me` / `PATCH /api/v1/me` | `{display_name?, locale?}` | 200 `User` | 401, 422 |
| `POST /api/v1/users` | `{username, display_name, password}` | 201 `User` (role adult) | 409 `username_taken`, 422 |

`Session = {user: User, csrf_token: string, expires_at}`; `User = {id, username, display_name, role, locale}`.
Theme and colour mode are **not** user properties in M0* (theme is deployment-wide, mode is per device).

---

## M0S-E05-01 · Password hashing and user service
- **Story:** As an adult household member, I want my password stored safely, so that a DB leak doesn't expose it.
- **AC:**
  - Given a new user, then `password_hash` starts with `$argon2id$` and uses parameters ≥ the OWASP minimum (m=19456 KiB, t=2, p=1). The pwdlib `recommended()` defaults meet or exceed this; assert in a test.
  - Verification upgrades the hash if the parameters changed. Passwords are 12–128 chars.
  - Creating a user with a non-`adult` role raises `RoleNotEnabledInM0` (422).
- **Tech:** `auth/passwords.py` (`pwdlib[argon2]`); `users/service.py` (writes go through `authorize()`; account and session bookkeeping emits no domain events in M0*). Hashing runs in a threadpool.
- **Tests:** Unit: parameter assertion, verify/rehash, role guard.
- **Deps:** E04-02 · **Est:** S · **Labels:** area:auth

## M0S-E05-02 · Login, logout and session cookie
- **Story:** As an adult household member, I want to log in once and stay logged in, so that I can use the dashboard.
- **AC:**
  - Given valid credentials, when I POST `/auth/login`, then a 256-bit random token is set as cookie `hearthos_session` (HttpOnly, SameSite=Lax, Path=/, `Secure` when `HEARTHOS_COOKIE_SECURE=true`). Only `sha256(token)` is stored; expiry 14 days sliding (idle 7 days); the session ID rotates on login.
  - Invalid credentials return a generic 401 after the same dummy-hash work (timing parity).
  - Logout revokes the row.
- **Tech:** `auth/router.py`, `auth/sessions.py`, and a `current_actor` FastAPI dependency returning `Actor`. In-memory rate limit of 5 failures per username+IP per 15 min.
- **Tests:** Integration: login → session → logout → 401; cookie attributes; rate limit.
- **Deps:** E05-01 · **Est:** M · **Labels:** area:auth, security

## M0S-E05-03 · CSRF protection
- **Story:** As an operator, I want state-changing requests protected against CSRF, so that a malicious site can't add or delete tasks or change the theme.
- **AC:**
  - Given an authenticated session, when a POST/PUT/PATCH/DELETE omits a valid `X-CSRF-Token` (equal to `sessions.csrf_token`, constant-time compare) or carries an `Origin` not in `HEARTHOS_ALLOWED_ORIGINS`, then the response is 403 `csrf_failed`.
  - GET is never state-changing. Login is exempt from the token check but subject to the Origin check (login-CSRF).
- **Tech:** Synchronizer token pattern, delivered in the `Session` JSON. The web client attaches it via a hey-api request interceptor.
- **Tests:** Integration: missing, wrong and cross-origin cases → 403; happy path → 2xx.
- **Deps:** E05-02 · **Est:** S · **Labels:** area:auth, security

## M0S-E05-04 · `IdentityProvider` seam
- **Story:** As the M1 implementer, I want auth behind an interface, so that OIDC plugs in without touching routers.
- **AC:** Given `HEARTHOS_AUTH_PROVIDER=local`, then login uses `LocalPasswordProvider`, which implements `IdentityProvider.authenticate(credentials) -> UserRef`. An `OidcProvider` stub raises `NotImplementedError` and is documented in ADR-0005.
- **Tech:** `auth/providers.py`. `users.external_subject` is reserved.
- **Tests:** Unit: provider selection.
- **Deps:** E05-02 · **Est:** S · **Labels:** area:auth

## M0S-E05-05 · Create second adult and CLI
- **Story:** As an operator, I want to create another adult account, so that two household members can share the list.
- **AC:**
  - Given an authenticated adult, when I POST `/api/v1/users`, then a new adult is created.
  - `uv run hearthos users create --username anna` prompts for a password.
  - `hearthos users set-password` exists.
- **Tech:** Typer CLI `hearthos_core/cli.py` (entry point `hearthos`; later also hosts `themes` and `seed` commands).
- **Tests:** Integration API test; CLI unit test with CliRunner.
- **Deps:** E05-01 · **Est:** S · **Labels:** area:auth
