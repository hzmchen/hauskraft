---
status: Proposed
date: 2026-10-24
---

# Skills are `SKILL.md` bundles contributed by plugins

## Context and problem statement

Some assistant work is a recipe rather than a conversation: turn pasted notes into tasks, write a weekly overview. A
recipe needs instructions, a small set of allowed tools and a defined output, and later a schedule may trigger it. The
spec lists a `skill` plugin type ("prompt + tool bundle + eval set", §5.2) but no format. Agent Skills (a `SKILL.md`
with a name and description in YAML frontmatter, instructions in the body) has become a common format across agent
tools. What does a Hauskraft skill look like?

## Decision drivers

* Declarative: no code, so skills are safe to load and easy to review.
* Small tool sets per run (ADR 0019); untrusted input never reaches tools (spec §8.1).
* Portable and familiar to people who write skills for other agents.
* Something a schedule can trigger later, with evals next to it.

## Considered options

* `SKILL.md` with Agent Skills frontmatter plus Hauskraft fields, contributed by plugins
* Skills as JSON in the manifest
* Skills as Python code

## Decision outcome

Chosen option: "`SKILL.md` contributed by plugins", decided with the project owner on 2026-10-24.

* **Location.** A plugin lists skills in `contributes.skills[]` as `{id, path}`; the path points at
  `skills/<id>/SKILL.md` inside the plugin.
* **Frontmatter.** `name` and `description` (as in Agent Skills), plus `tools` (the allowed registry tool names, may
  be empty), `output` (`text`, or a JSON schema for typed output) and `evals` (a path to the skill's eval dataset). The
  body holds English instructions. The schema is `packages/schemas/skill/skill.schema.json`.
* **Running.** `POST /api/v1/assistant/skills/{id}/runs` runs the skill as the calling person with exactly its tools,
  and the person's last result is kept for widgets. A skill that reads untrusted text declares no tools and a typed
  output, so injected instructions have nothing to call.
* **M2*** ships two skills in the tasks plugin: `add-from-text` (no tools, output: a list of tasks) and
  `weekly-overview` (`tasks.list` only, output: text).

### Consequences

* Good, because skills are reviewable text, portable in spirit, and need no code execution.
* Good, because schedules can trigger skills later without a new concept.
* Bad, because skills can only combine existing tools; anything new still needs a tool in a plugin.
* Bad, because the Hauskraft fields go beyond Agent Skills, so a plain Agent Skills tool ignores the tool allowlist.

## More information

Spec §5.2, §5.3, §8.0; ADR 0019, ADR 0022; stories M2S-E05-01 to M2S-E05-04.
