---
status: Proposed
date: 2026-10-22
---

# First-run setup in the browser: the first visitor becomes owner

## Context and problem statement

In M0* a fresh install either gets the demo household (`HAUSKRAFT_SEED_DEMO`) or has no account at all. In that case
the only way in is `hauskraft users create` inside the container. M1* wants a household to start from the browser
(spec §2.2 journey 12). Who may create the first account?

## Decision drivers

* No CLI step for a normal install.
* Simple to explain and to test.
* Setup must be impossible to repeat once an account exists, even under concurrent requests.
* The install is LAN-only by default (§11.3).

## Considered options

* Web wizard; the first visitor wins (like Home Assistant onboarding)
* Web wizard protected by a one-time setup code printed in the server log
* CLI only

## Decision outcome

Chosen option: "Web wizard; the first visitor wins", decided by the project owner on 2026-10-22. `GET /api/v1/setup`
is public and says whether setup is required, which is true while the `users` table is empty. `POST /api/v1/setup`
is public too: it checks the Origin like login does, but has no CSRF token because there is no session yet. It
creates the household settings and the first `owner` in one transaction under a transaction-scoped advisory lock,
emits `hauskraft.user.created` and signs the new owner in. Once any account exists, it answers 409 `setup_done`.
This holds for any account: one from the wizard, the CLI or the demo seed.

### Consequences

* Good, because installing needs a browser only.
* Good, because the endpoint has no state beyond "is there a user?", so there is no token to leak or expire.
* Bad, because anyone who reaches the port before the operator can claim the install. Mitigations:
  - From M1*, Compose publishes the web port on `127.0.0.1` unless `HAUSKRAFT_WEB_BIND` says otherwise. That matches
    §11.3: LAN exposure needs TLS anyway.
  - The docs say to finish setup right after `docker compose up`.
  - An unwanted owner can be removed by wiping the volume. If the install is meant for a LAN, a setup code can be added later behind the same
  endpoint without breaking clients.

## More information

Spec §2.3, §11.3, §14 item 15; stories M1S-E03-01 and M1S-E03-02.
