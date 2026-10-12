---
status: Accepted
date: 2026-10-12
---

# TypeScript 6.0 for M0*

Status: Accepted

## Context and problem statement

TypeScript 7 (the native port) is released, but its compiler API is not stable until 7.1. typescript-eslint and other tools depend on that API.

## Decision drivers

* Tooling (typescript-eslint, hey-api) must work.
* Avoid churn during M0*.

## Considered options

* Stay on TypeScript `~6.0`
* Move to 7.x now

## Decision outcome

Chosen option: "Stay on `~6.0`" for every package in the workspace until 7.x ships a stable compiler API. Re-evaluate at M1.

### Consequences

* Good, because the lint and codegen toolchain keeps working
* Bad, because we miss 7.x compile-speed gains for now

## More information

AGENTS.md rule 8 (respect pins); story M0S-E01-03.
