---
status: Accepted
date: 2026-10-12
---

# Auth for M0*: local accounts and server-side sessions

Status: Accepted

## Context and problem statement

M0* needs logins for adults on a LAN demo. OIDC is planned for M1 and must plug in without touching routers.

## Decision drivers

* Safe password storage and session handling on plain HTTP localhost.
* Protection against CSRF for cookie-authenticated writes.
* A seam for OIDC later.

## Considered options

* Local accounts + server-side sessions + synchronizer CSRF token
* JWT bearer tokens in local storage
* OIDC from day one

## Decision outcome

Chosen option: "Local accounts + server-side sessions". Passwords are hashed with argon2id via `pwdlib` (parameters at or above the OWASP minimum m=19 MiB, t=2, p=1). Sessions are random 256-bit tokens in an HttpOnly, SameSite=Lax cookie (`Secure` when configured); only their SHA-256 is stored. State-changing requests need a synchronizer CSRF token (`X-CSRF-Token`) and an allowed `Origin`. Login goes through an `IdentityProvider` interface (`LocalPasswordProvider` now); an `OidcProvider` stub raises `NotImplementedError` until M1.

### Consequences

* Good, because no tokens are readable by page scripts
* Good, because OIDC can replace the provider without router changes
* Bad, because sessions need server-side storage and cleanup
* Bad, because the demo runs without `Secure` cookies; any LAN exposure needs TLS first

## More information

Spec §2.1, §11.3; stories M0S-E05-01 … M0S-E05-05.
