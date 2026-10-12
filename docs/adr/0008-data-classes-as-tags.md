---
status: Accepted
date: 2026-10-12
---

# Data classes as tags

Status: Accepted

## Context and problem statement

Household data ranges from public to secret. Later milestones route data to local or cloud models and restrict access by class; the tagging must exist before the enforcement.

## Decision drivers

* Tag data at the plugin boundary from day one.
* A total order so taint can propagate as a maximum.
* Do not block M0* on enforcement.

## Considered options

* Eight ordered classes, declared but not enforced in M0*
* Free-form tags
* Enforce from day one

## Decision outcome

Chosen option: "Eight ordered classes": `public` < `household` < `personal` < `financial` < `tenant` < `child` < `health` < `secret`. Entities, events (`dataclass`) and manifests (`data_classes.reads/writes/emits`) carry them. M0* records and validates the values but does not enforce routing or access; undeclared use is logged as a governance warning.

### Consequences

* Good, because routing and access rules can be added without a data migration
* Good, because manifests show what a plugin touches
* Bad, because tags can be wrong until enforcement and review exist

## More information

Spec §5.5, §8.5.
