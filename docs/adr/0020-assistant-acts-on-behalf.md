---
status: Accepted
date: 2026-10-24
---

# The assistant acts on behalf of a person, through a swappable gate

## Context and problem statement

From M2* an assistant calls tools that change household data (spec §8.0). Who is the actor in `authorize()` and in
events, how does Activity tell assistant actions apart, and how is a destructive call stopped before it happens? Later
milestones add schedules (nobody watching), an approval inbox (§8.4), a risk classifier and voice. M2* must not block
them, and asking before every action leads to confirmation fatigue.

## Decision drivers

* The assistant never has more rights than the person using it.
* The household sees what the assistant did, with the same events as manual changes.
* Destructive calls need a human decision in M2*; reversible ones should not interrupt.
* One decision point that later rules, a classifier or the inbox can replace.

## Considered options

* The person is the actor; events carry the run id; one gate function decides allow, confirm or deny
* A separate agent principal with its own permissions
* Confirmation for every write

## Decision outcome

Chosen option: "The person is the actor, events carry the run id, one gate", decided with the project owner on
2026-10-24.

* **Actor.** Tool handlers receive the person's `Actor` with `via` set to the run id. `authorize()` checks the
  person's role, unchanged. Every event the run causes carries the CloudEvents extension attribute `agentrunid` (the
  run id, lower-case letters and digits only as CloudEvents requires); `actorid` stays the person. Activity renders
  "Mia via assistant added 'Buy milk'" (de: "Mia über den Assistenten …").
* **Gate.** `gate.decide(tool, args, actor, ctx) -> allow | confirm | deny`, where `ctx` holds the run kind
  (`interactive` now, `scheduled` later), the channel (`text` now, `voice` later), taint and history. The M2* rule:
  a tool outside the run's selected set is denied; a `destructive` tool needs confirmation; everything else is
  allowed. Every decision is stored on the run with its reason, so confirmation rates can be measured.
* **Confirmation.** "Confirm" pauses the run (`awaiting_confirmation`) with the pending calls (Pydantic AI deferred
  tool requests). The chat shows a card; the answer resumes the run. When nobody is present (schedules later), the
  same stored request becomes an approval-inbox item.
* **Undo instead of asking.** A tool may declare an inverse (create → delete, update → restore the previous values).
  Its action card offers Undo, which runs the inverse as a normal write with its own event.

### Consequences

* Good, because permissions, events and Activity work exactly as for manual changes.
* Good, because schedules, the inbox, a risk classifier ("auto mode") and voice change the gate's rule, not its
  callers.
* Good, because stored decisions make confirmation fatigue measurable before anyone tunes the rules.
* Bad, because a person's permissions are the only limit on the assistant in M2*. Per-agent allowlists and
  data-class routing come with §8.2 and §8.5.

## More information

Spec §3.2, §8.0, §8.4; ADR 0016, ADR 0018, ADR 0019; stories M2S-E04-02, M2S-E04-04, M2S-E04-06, M2S-E04-07.
