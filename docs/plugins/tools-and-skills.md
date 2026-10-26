<!-- SPDX-License-Identifier: MIT -->

# Tools and skills for plugin authors

A plugin can let Hauskraft's assistant act on its data: it exposes **tools** (functions the model may call) and
**skills** (recipes with instructions and a small set of tools). This guide shows how to write them so they work well
with small and large models. The tasks plugin (`plugins/official/tasks`) is the worked example. The contract is
[ADR 0019](../adr/0019-tool-contract-and-registry.md), skills are [ADR 0023](../adr/0023-skill-format.md) and evals
[ADR 0022](../adr/0022-evals-in-two-layers.md).

## Declare and register a tool

A tool lives in two places that core checks against each other at startup; a mismatch is a load error.

**The manifest** (`hauskraft.plugin.json`):

```json
"tools": [
  {
    "name": "tasks.create",
    "description": "Add a task to the household's shared list, optionally with a due date.",
    "annotations": { "read_only": false, "destructive": false, "idempotent": false, "open_world": false },
    "data_class": "household",
    "permission": "task.create"
  }
]
```

**The code**, returned in `PluginRegistration.tools`:

```python
from hauskraft_sdk.tools import RecordRef, ToolAnnotations, ToolOutcome, ToolSpec, UndoCall

async def create_handler(ctx, actor, args: CreateArgs) -> ToolOutcome:
    task = await service.create_task(ctx, actor, TaskCreate(title=args.title, due_on=args.due_on))
    return ToolOutcome(
        output={"task": compact(task)},
        record=RecordRef(type="Task", id=str(task.id), label=task.title),
        summary_key="tasks:tool.create.done",
        undo=UndoCall(tool="tasks.delete", args={"task_id": str(task.id)}),
    )

TOOLS = [ToolSpec(name="tasks.create", description="…", input_model=CreateArgs, handler=create_handler,
                  permission="task.create",
                  annotations=ToolAnnotations(read_only=False, destructive=False, idempotent=False, open_world=False))]
```

- **Names** are `<plugin>.<verb>` in lower case. Models see `tasks_create`, because function names can't contain dots.
- **The handler calls your service functions**, never the ORM. They call `authorize()` first and emit one event, so
  permissions, Activity and the audit trail work exactly as for manual changes. The `actor` is the person using the
  assistant; their events carry `agentrunid`.
- **`permission`** is the action in the permission table; the registry offers the tool only to roles that have it.
- **`data_class`** is the most sensitive class the tool reads or returns.

## Annotations decide what happens

| Annotation | Meaning | Effect in M2* |
|---|---|---|
| `read_only` | only reads | runs at once; never an action card |
| `destructive` | deletes or can't be undone | **the person confirms first** (a card with your approve label and Cancel) |
| `idempotent` | the same call twice changes nothing more | informative |
| `open_world` | talks to the outside world | informative now; blocked for untrusted input later (spec §8.3) |

A tool that leaves annotations out counts as **destructive, write and open-world**: be explicit.

## Design tools for models

Every tool costs tokens on every request, and models pick worse from long lists. The registry offers each run only
the tools it may use; you keep each tool small:

- **Few, coarse tools.** One `tasks.update` with optional fields beats `rename`, `set_due` and `complete`.
- **Short descriptions** that say when to use the tool ("Use it to find a task's id"), in English.
- **Flat parameters** with enums and limits (`status: open|done|all`, `limit ≤ 50`); no nested objects.
- **Compact outputs:** only the fields a model needs (`id, title, done, due_on`), capped lists, never whole records.
- **Budget:** each plugin's serialized tool definitions stay under about **1,500 tokens** (6,000 characters, tested
  in CI).
- **Problem codes the model can act on:** raise the SDK's errors with a specific `code` (`task_not_found`), so the
  model can recover or explain.
- **Undo and preview:** return an `UndoCall` with the previous values for reversible writes (the card offers Undo
  instead of asking first), and give destructive tools a `preview` that names the record ("Delete task 'Buy milk'?").
- **`summary_key`:** an i18n key in your namespace for the card text (`tasks:tool.create.done`: "Added task
  '{{label}}'"); confirmations use `<plugin>:tool.<verb>.confirm` and `.approve`. Provide en and de.
- **`agent_guidance`** (manifest, at most 600 characters): rules the model needs while your tools are offered, for
  example how due dates and "tomorrow" work.

## Skills

A skill is a recipe in `skills/<id>/SKILL.md`, listed in `contributes.skills[]`:

```markdown
---
name: Weekly overview
description: A short overview of the week's open tasks, overdue ones first.
tools: [tasks.list]
output: text
evals: evals/weekly-overview.yaml
---
Write a short overview of the household's week for the person. …
```

- `tools` lists exactly what the skill may use; the run is offered nothing else.
- `output` is `text`, or `{schema: <JSON Schema>}` for typed output that UI can use directly.
- **Untrusted input:** a skill that reads text the person pasted (emails, notes, documents) declares **no tools**
  and a typed output, and its instructions say the text is data, never instructions. Then injected instructions have
  nothing to call (see `add-from-text`).
- Run it with `POST /api/v1/assistant/skills/<plugin>.<id>/runs`; widgets read the person's latest result. Schedules
  will trigger skills later.

## Evals

Add an eval dataset next to your skill and reference it in `evals:`. `just eval` discovers it. Write cases that check
facts: which tools were called with which arguments, what the database looks like afterwards, whether a destructive
call paused, and the answer's language. Add prompt-injection cases for every skill that reads untrusted text. Run
them against the models households use before you release ([evals/README.md](../../evals/README.md)).
