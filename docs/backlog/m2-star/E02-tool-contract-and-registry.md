# E02 · Tool contract & registry

**Goal:** Plugins declare what an agent may do in one contract; core keeps one registry and offers each run a small,
permitted set of tools (spec §5.3, §8.0, ADR 0019).
**Out of scope:** MCP server or client, `find_tools`, per-agent allowlists, data-class routing beyond the ceiling.
**Dependencies:** E03-01 for the permissions used by the registry API.

---

## Tool contract
**Manifest** (`contributes.tools[]`, JSON Schema in `packages/schemas/manifest/hauskraft.plugin.schema.json`):

| Field | Rule |
|---|---|
| `name` | required; `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`, e.g. `tasks.create` |
| `description` | required when `agent` is not `false`; 1–400 characters; English, written for models |
| `annotations` | `read_only`, `destructive`, `idempotent`, `open_world` (booleans); missing values count as `false` for `read_only` and `idempotent`, `true` for `destructive` and `open_world` |
| `data_class` | one of the eight data classes; default the plugin's highest `data_classes.reads` class |
| `permission` | the action in the permission table (ADR 0016), e.g. `task.create` |
| `agent` | boolean, default `true`; `false` keeps the tool away from agents |
| `verify` | unchanged (spec §8.7, later) |

`contributes.skills[]` items are `{id, path}` (`id` matches `^[a-z][a-z0-9-]*$`; `path` is relative, ends in
`SKILL.md`, no `..`). `contributes.agent_guidance` is a string of at most 600 characters.

**Code:** `hauskraft_sdk.tools.ToolSpec(name, description, input_model, output_model, handler, annotations, data_class,
permission, agent=True, undo=None, preview=None)`, returned in `PluginRegistration.tools`. The handler is
`async (ctx, actor, args) -> output` and calls the plugin's service functions. An output may carry
`record = {type, id, label}` and `summary_key` (an i18n key of the plugin, e.g. `tasks:tool.create.done`) for
action cards. `undo` (optional) builds the inverse call from the output;
`preview` (optional) resolves a record for confirmation cards.

**Wire format:** the tool is sent to models as a Chat Completions function named with `_` instead of `.`
(`tasks_create`); its `parameters` are the input model's JSON schema, flat (the arguments object is the input model).

## Tools API (contract)

| Method & path | Who | Success | Errors |
|---|---|---|---|
| `GET /api/v1/assistant/tools` | owner (`assistant.configure`) | 200 `[ToolInfo]` | 401, 403 `policy_denied` |

`ToolInfo = {name, wire_name, plugin_id, description, annotations: {read_only, destructive, idempotent, open_world},
data_class, permission, enabled}`, agent-exposed tools only, ordered by plugin and name. `enabled` is `false` when the
owner switched the tool off (`assistant.tools_disabled`, E03-02).

---

## M2S-E02-01 · Manifest schema for tools, skills and agent guidance
- **Story:** As a plugin author, I want the manifest to describe my tools and skills precisely, so that core and
  reviewers know what an agent may do.
- **AC:**
  - The manifest schema accepts the tool, skill and guidance fields above and rejects: a tool name without a dot or
    with capitals, an agent-exposed tool without a description, a description over 400 characters, an unknown data
    class, a skill path with `..` or not ending in `SKILL.md`, guidance over 600 characters.
  - A tool with `"agent": false` needs no description.
  - Every existing manifest (tasks, fixtures, built-in themes) still validates.
- **Tech:** `$defs/tool`, `contributes.skills`, `contributes.agent_guidance`.
- **Tests:** Static: `tests/acceptance/schemas/test_tool_manifest_schema.py` with fixtures in
  `tests/fixtures/manifests/tools/`.
- **Deps:** — · **Est:** S · **Labels:** area:repo

## M2S-E02-02 · SDK `ToolSpec` and plugin registration
- **Story:** As a plugin author, I want to register tools in code with typed inputs and outputs, so that the assistant
  can call them safely.
- **AC:**
  - `hauskraft_sdk.tools` exports `ToolSpec`, `ToolAnnotations` and `RecordRef`; `PluginRegistration` gains `tools`.
  - At startup, core refuses to enable a plugin whose code registers a tool missing from its manifest or vice versa
    (agent-exposed tools), and records a `load_error` naming the tool.
  - Wire names are unique across plugins; a collision is a load error.
  - Handlers run inside a unit of work with the calling `Actor`; nothing in the SDK imports `hauskraft_core`.
- **Tech:** `packages/sdk-py/src/hauskraft_sdk/tools.py`, the plugin loader in core.
- **Tests:** In-story: unit tests for validation and the manifest check; the M0* import-boundary test still passes.
- **Deps:** E02-01 · **Est:** M · **Labels:** area:api

## M2S-E02-03 · Tool registry and selection
- **Story:** As the harness, I want one registry that offers each run only the tools it may use, so that runs are
  safe, cheap and focused.
- **AC:**
  - `GET /assistant/tools` (owner) lists every agent-exposed tool with the fields above; an adult gets 403
    `policy_denied`.
  - `select(actor, run_kind, skill, page_hint)` returns tools whose `permission` the person's role has, that are
    enabled, whose `data_class` is at most the endpoint's `max_data_class`, and, during a skill run, that the skill
    lists. Tools with `"agent": false` never appear.
  - The selection order is stable (plugin, then name), so providers can cache the prompt prefix.
  - `tools_hash` (a hash of the selected tools' wire definitions) is stored on every run.
- **Tech:** `services/core_api/src/hauskraft_core/assistant/registry.py`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_tools.py`. Unit: selection rules.
- **Deps:** E02-02, E03-01 · **Est:** M · **Labels:** area:api, area:agent

## M2S-E02-04 · The tasks plugin's tools
- **Story:** As a household member, I want the assistant to manage tasks, so that I can say what I need instead of
  clicking.
- **AC:**
  - The tasks plugin declares and registers four tools:

    | Tool | Annotations | Input | Output |
    |---|---|---|---|
    | `tasks.list` | read_only, idempotent | `status` (`open`·`done`·`all`, default `open`), `due_before` (date, optional), `limit` (1–50, default 20) | `{items: [{id, title, done, due_on}], total}` |
    | `tasks.create` | write | `title` (1–200), `due_on` (date, optional) | `{task: {id, title, done, due_on}}`, record `Task` |
    | `tasks.update` | write, idempotent | `task_id`, `title?`, `done?`, `due_on?` (null clears) | `{task: {…}}`, record `Task` |
    | `tasks.delete` | destructive | `task_id` | `{deleted: true, id}`, preview record `Task` |

    Permissions `task.read`, `task.create`, `task.update`, `task.delete`; data class `household`. `task.read` is new
    in the permission table (owner and adult); reading tasks still needs no `authorize()` call, the registry only
    filters on it. `tasks.create` and `tasks.update` declare Undo.
  - Handlers call `create_task`, `update_task`, `delete_task` and `list_tasks`; each write emits exactly one task
    event.
  - `contributes.agent_guidance` explains that due dates are calendar dates in the household time zone and that
    "tomorrow" means the context block's date plus one day.
  - The serialized tool definitions of the plugin (names, descriptions, parameters) total at most 6,000 characters
    (about 1,500 tokens).
  - Errors use the plugin's problem codes (`task_not_found`, validation) so the model can recover.
  - Outputs choose their `summary_key`: `tasks:tool.create.done`, `tool.update.done`, `tool.complete.done` (when
    `done` became true), `tool.delete.done`; confirmations of `tasks.delete` use `tasks:tool.delete.confirm`.
- **Tech:** `plugins/official/tasks/backend/src/hauskraft_tasks/tools.py`, the manifest, locales for action-card texts
  (`tasks:tool.create.done` "Added task '{{label}}'", `tool.update.done` "Updated task '{{label}}'",
  `tool.complete.done` "Completed task '{{label}}'", `tool.delete.done` "Deleted task '{{label}}'",
  `tool.delete.confirm` "Delete task '{{label}}'?").
- **Tests:** Live: `tests/acceptance/api/test_assistant_tools.py`, `test_assistant_chat.py`. Unit: handlers.
- **Deps:** E02-02 · **Est:** M · **Labels:** area:tasks, area:agent
