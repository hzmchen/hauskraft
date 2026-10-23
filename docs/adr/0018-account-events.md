---
status: Accepted
date: 2026-10-22
---

# Account changes are CloudEvents

## Context and problem statement

ADR-0006 says that account and session bookkeeping calls `authorize()` but emits no event in M0*. In M1* owners add,
change, deactivate and reactivate members and reset passwords. The household should see these changes in Activity,
and the later audit log (spec §8.6) will consume the outbox. Which account writes emit events, and what may they
contain?

## Decision drivers

* One event per domain write, in the same transaction (ADR-0007, AGENTS.md rule 1).
* Activity must show who changed which account.
* No secrets in events: passwords, hashes, session IDs and IP addresses never leave the auth tables.
* Activity should not fill up with noise such as language switches or sign-ins.

## Considered options

* Events for member and password changes; none for preferences and session bookkeeping
* Events for every account write, including sign-in, sign-out and language changes
* No account events (M0* behaviour)

## Decision outcome

Chosen option: "Events for member and password changes", decided by the project owner on 2026-10-22. The users
service emits `hauskraft.user.created`, `hauskraft.user.updated` (display name or role), `hauskraft.user.deactivated`,
`hauskraft.user.reactivated`, `hauskraft.user.password_reset` (an owner set a temporary password) and
`hauskraft.user.password_changed` (members changing their own). Each has source `dev.hauskraft.core`, subject
`user/<id>` and `dataclass` `personal`. The data carries the account's `id`, `username`, `display_name` and `role`,
plus `changes` (from/to) for updates, and nothing else (`additionalProperties: false`). Household settings changes emit
`hauskraft.settings.household_changed` (`dataclass` `household`). Language preference changes, sign-in, sign-out and
ending sessions emit nothing. This amends the last sentence of ADR-0006's decision outcome for M1*.

### Consequences

* Good, because Activity and the future audit log see every change to who can act in the household.
* Good, because the schemas make it impossible to put a secret into an event by accident.
* Bad, because display names are copied into events and stay in the outbox after a rename. That's acceptable for
  household-internal `personal` data. A future erasure feature has to deal with it (spec §11.2).

## More information

Spec §2.3, §3.2; ADR-0006, ADR-0007; stories M1S-E09-01 and M1S-E09-02.
