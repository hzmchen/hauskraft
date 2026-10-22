---
status: Proposed
date: 2026-10-22
---

# Static role permission table behind `authorize()` for M1*

## Context and problem statement

M1* enables a second role. Owners manage members, household settings, the household theme and plugins; adults use
everything else (spec §2.3). M0* allows every write (`NoOpPolicy`). The spec names Cedar as the policy engine
(§4.1, §8.3), but in M1* there are two roles, no agents, no spend limits and no data-class routing to decide. How do
we enforce owner-only actions without building the policy engine early?

## Decision drivers

* Handlers must not grow role checks (AGENTS.md rule 6); the `authorize()` seam (ADR-0006) stays the only place.
* Swapping in Cedar later must not touch routers or services.
* No new dependency for a two-row table.
* Denials must be predictable and testable as black boxes (403 `policy_denied`, no row, no event).

## Considered options

* A static permission table in code, implementing the existing `Policy` protocol
* Cedar now (`cedarpy`), with a two-role policy file
* Role checks in routers or FastAPI dependencies

## Decision outcome

Chosen option: "A static permission table in code". `RolePolicy` implements `Policy.authorize(actor, action,
resource, data_class, capability)` by looking the action up in one mapping from action name to the set of roles
allowed (`owner`, `adult`). Actions not in the table are denied, so a new write path fails closed until someone adds
it. Rules about a member's own account are structural rather than table lookups. The `me.*` actions (profile,
password, sessions) are allowed for both roles, and their services only ever touch the caller's own account. The
`user.*` actions on other accounts are owner-only. Business invariants that are not permissions stay in the
services: the last active owner, the one-time setup, and the forced password change. `HAUSKRAFT_POLICY` accepts `roles` (the new default), `noop` (tests only) and `deny_all`
(tests only). The system actor used by the CLI and the seed has the `owner` role.

### Consequences

* Good, because owner-only rules are enforced in one place with no new dependency.
* Good, because Cedar can replace `RolePolicy` behind the same protocol later; the table becomes the first policy
  file and its tests become the regression suite.
* Bad, because the table is code, not data: changing a permission needs a release.
* Bad, because the rules are not analysable the way Cedar policies are. That's acceptable for two roles.

## More information

Spec §2.3, §8.3; ADR-0006; stories M1S-E02-01 and M1S-E02-02.
