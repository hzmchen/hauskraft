---
status: Accepted
date: 2026-10-12
---

# UUIDv7 IDs generated in the app

Status: Accepted

## Context and problem statement

Rows need IDs that are unique across plugins and sort roughly by creation time for pagination and event ordering.

## Decision drivers

* Time-ordered IDs for indexes and feeds.
* Postgres 16 has no native `uuidv7()`.
* Python 3.13's `uuid` module has no `uuid7()`.

## Considered options

* UUIDv7 generated in Python
* Bigint sequences
* UUIDv4

## Decision outcome

Chosen option: "UUIDv7 generated in the application" (via a small library such as `uuid6` or an equivalent implementation). Revisit native `uuidv7()` if the project moves to Postgres 18.

### Consequences

* Good, because IDs are globally unique, unguessable enough for URLs and roughly time-ordered
* Bad, because one extra dependency until the standard library or Postgres provides UUIDv7

## More information

Story M0S-E04-02.
