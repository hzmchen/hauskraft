---
status: Accepted
date: 2026-10-12
---

# Service layer and `authorize()` seam

Status: Accepted

## Context and problem statement

M1 brings Cedar policies and approvals. If routers write to the database directly, adding policy later means touching every handler.

## Decision drivers

* One choke point for every write.
* Policies must live outside the model and outside handlers (spec P3).
* Events and rows must never disagree.

## Considered options

* Service functions that call `authorize()` and emit one event per write
* Policy checks in routers
* Database triggers

## Decision outcome

Chosen option: "Service functions with an `authorize()` seam". Every write to a domain entity or deployment setting goes through a service function that first calls `await policy.authorize(actor, action, resource, data_class, capability)` and then writes the row and exactly one CloudEvent in the same transaction (ADR-0007). The `Policy` protocol is implemented by `NoOpPolicy` (allow, debug log) in M0*; a test-only `DenyAllPolicy` proves the seam. Plugins reach it as `PluginContext.authorize`. Cedar replaces the no-op in M1 without handler changes. Account and session bookkeeping calls `authorize()` but emits no event in M0*.

### Consequences

* Good, because policy can be added later in one place
* Good, because a denied write leaves neither a row nor an event
* Bad, because every write needs the extra service layer, even when it is trivial

## More information

Spec §8.3; AGENTS.md rule 1; story M0S-E03-04.
