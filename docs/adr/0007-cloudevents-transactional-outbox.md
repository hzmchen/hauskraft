---
status: Accepted
date: 2026-10-12
---

# CloudEvents and a transactional outbox

Status: Accepted

## Context and problem statement

Activity feeds, future workflows and the audit log all need a reliable stream of what happened. Publishing to a broker after commit can lose events; publishing before commit can announce writes that rolled back.

## Decision drivers

* No event without its write, no write without its event.
* A standard envelope that future consumers understand.
* No broker in M0*.

## Considered options

* CloudEvents in a transactional outbox table
* Publish to a broker after commit
* Postgres LISTEN/NOTIFY only

## Decision outcome

Chosen option: "CloudEvents 1.0 structured JSON in a transactional outbox". Services append each event to `outbox_events` in the same transaction as the write. A relay inside core marks events published (logging them in M0*; brokers and `subscribes[]` delivery later). The table is append-only (a trigger rejects deletes and updates other than `published_at` and `attempts`). Two extension attributes are used: `dataclass` (the data class) and `actorid` (the acting user or agent); they are spelled without underscores because CloudEvents attribute names may contain only lower-case letters and digits. JSON bodies, DB columns and manifests keep `data_class`.

### Consequences

* Good, because rollback removes both row and event
* Good, because the outbox is the feed for the M1 hash-chained audit log
* Bad, because consumers see events only after the relay polls (2 s in M0*)

## More information

Spec §3.2, §8.6; decision D1; stories M0S-E04-03, M0S-E10-01 … M0S-E10-03.
