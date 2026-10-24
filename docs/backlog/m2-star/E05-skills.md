# E05 · Skills

**Goal:** Recipes the assistant runs with exactly the tools they need: turn pasted notes into tasks, write a weekly
overview (spec §5.2, §8.0, ADR 0023).
**Out of scope:** Skills from the registry, skill authoring in the UI, schedules triggering skills.
**Dependencies:** E02-03, E04-02.

---

## Skill format and API (contract)
`SKILL.md` = YAML frontmatter plus an English body (the instructions). Schema:
`packages/schemas/skill/skill.schema.json`.

| Frontmatter | Rule |
|---|---|
| `name` | required, 1–80 characters |
| `description` | required, 1–300 characters |
| `tools` | required list of registry tool names (may be empty) |
| `output` | required: `text`, or an object `{schema: <JSON Schema>}` |
| `evals` | optional relative path to an eval dataset |

The global skill id is `<plugin short name>.<id>`, e.g. `tasks.add-from-text`.

| Method & path | Who | Body | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/assistant/skills` | `assistant.use` | — | 200 `[SkillInfo]` | 401 |
| `POST /api/v1/assistant/skills/{id}/runs` | `assistant.use` | `{input: {text?: string}}` | 200 `SkillRun` | 404, 409 `assistant_not_configured`, 422 |
| `GET /api/v1/assistant/skills/{id}/runs/latest` | `assistant.use` | — | 200 `SkillRun` (the caller's) | 404 |

`SkillInfo = {id, plugin_id, name, description, tools: [name], output: "text" | "json"}`;
`SkillRun = {run: Run, output: string | object | null, created_at}`. A skill run is a run of kind `skill` without a
conversation; its system prompt contains the skill's instructions and the context line `Skill: <id>`, and the model is
offered exactly the skill's tools (none if the list is empty).

---

## M2S-E05-01 · Skill format and loader
- **Story:** As a plugin author, I want to ship skills as reviewable text files, so that I can add recipes without code.
- **AC:**
  - Core loads every `contributes.skills[]` entry, validates its frontmatter against the schema and lists valid skills
    in `GET /assistant/skills`; an invalid skill is a plugin `load_error` naming the file.
  - A skill listing a tool that isn't registered is invalid.
- **Tech:** `assistant/skills.py`; `packages/schemas/skill/skill.schema.json`.
- **Tests:** Static: `tests/acceptance/schemas/test_skill_schema.py` (fixtures `tests/fixtures/skills/`). Live:
  `tests/acceptance/api/test_assistant_skills.py`.
- **Deps:** E02-03 · **Est:** S · **Labels:** area:agent

## M2S-E05-02 · Skill runs
- **Story:** As a widget or dialog, I want to run a skill and read its latest result, so that skills can power UI
  without a chat.
- **AC:**
  - `POST /skills/{id}/runs` runs the skill as the caller with exactly its tools and returns its output: text, or an
    object valid against the skill's output schema (invalid model output is retried, then the run fails with
    `invalid_output`).
  - `GET /skills/{id}/runs/latest` returns the caller's last successful run; another member's runs are never returned.
  - Skill runs record usage (E08-01) with kind `skill`.
- **Tech:** `assistant/skills.py`, Pydantic AI output types.
- **Tests:** Live: `tests/acceptance/api/test_assistant_skills.py`.
- **Deps:** E05-01, E04-02 · **Est:** M · **Labels:** area:agent

## M2S-E05-03 · `add-from-text` skill
- **Story:** As a member, I want to paste a note and get tasks suggested from it, so that I don't retype my lists.
- **AC:**
  - `tasks.add-from-text` declares no tools and the output `{tasks: [{title: 1–200, due_on: date|null}]}` (at most
    50).
  - Its instructions treat the pasted text as data: they never follow instructions found in it.
  - Against the fake model, a note with three "- " lines and an injected instruction returns exactly the three tasks;
    the request offered no registry tool, and no task changed.
  - The skill only suggests; the web dialog creates the chosen tasks with the person's own session (E06-05).
- **Tech:** `plugins/official/tasks/skills/add-from-text/SKILL.md`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_skills.py`.
- **Deps:** E05-02, E02-04 · **Est:** S · **Labels:** area:tasks, area:agent

## M2S-E05-04 · `weekly-overview` skill
- **Story:** As a member, I want a short overview of what's due this week, so that I see the week at a glance.
- **AC:**
  - `tasks.weekly-overview` declares the tool `tasks.list` only and the output `text`.
  - Its instructions ask for open tasks, overdue first, then due in the next seven days, at most about 120 words, in the
    person's language.
  - Against the fake model, the request offered only `tasks_list`, and the run's output text is returned and kept as
    the caller's latest.
- **Tech:** `plugins/official/tasks/skills/weekly-overview/SKILL.md`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_skills.py`.
- **Deps:** E05-02 · **Est:** S · **Labels:** area:tasks, area:agent
