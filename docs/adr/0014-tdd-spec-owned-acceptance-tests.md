---
status: Accepted
date: 2026-10-12
---

# Test-driven development with spec-owned acceptance tests

Status: Accepted

## Context and problem statement

Many agents implement stories in parallel. Without executable acceptance criteria, "done" drifts and contracts erode.

## Decision drivers

* Every story has an objective definition of done.
* Tests must not be weakened to get to green.
* The suite must stay runnable while most stories are unbuilt.

## Considered options

* Spec-owned acceptance suite + per-story red/green switch
* Tests written by each implementer only
* Manual QA against the demo script

## Decision outcome

Chosen option: "Spec-owned acceptance suite". Every story is built red → green → refactor. `tests/` holds acceptance tests and fixtures written from the spec before the code. `tests/story-status.json` marks each story red or green: red stories run as expected failures, green stories are hard gates, and CI fails when a red story's tests all pass, so the switch cannot be forgotten. Acceptance tests and fixtures change only with the spec owner (and an ADR when a contract changes). Tests are black-box first: live API tests over HTTP, the CLI via `--json`, linters via stdin, the UI via roles and accessible names (`docs/testing/ui-contract.md`). Implementers write their own unit and integration tests first inside each story.

### Consequences

* Good, because "done" is objective and checked on every PR
* Good, because implementers keep freedom inside modules
* Bad, because writing tests before code costs time up front
* Bad, because a wrong spec-owned test blocks a story until the spec owner fixes it

## More information

Spec §13.3; decision D9; `docs/testing/README.md`.
