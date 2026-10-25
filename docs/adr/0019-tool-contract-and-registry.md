---
status: Proposed
date: 2026-10-24
---

# One tool contract and an in-core registry; MCP at the edges

## Context and problem statement

M2* lets an LLM assistant act through plugin functions (spec §8.0). The spec left open how plugins reach agents
(§14 item 14): one Hauskraft MCP gateway aggregating every plugin's tools, one MCP server per plugin, or agent skills on
top of a smaller tool surface. Every plugin today runs in-process (§5.6, tier 4), the only agent is Hauskraft's own
assistant, and the model endpoint speaks OpenAI Chat Completions with function calling. How do plugins declare what an
agent may do, and how does the assistant find and call it?

## Decision drivers

* Plugin authors decide whether a function is exposed at all; owners can switch tools off.
* Writes keep going through the plugin's service functions (`authorize()` first, exactly one event, AGENTS.md rule 1).
* Few, small tool sets per run: every tool costs tokens on every request, and small models pick worse from long
  lists.
* Later: outside agents (Claude Desktop, Home Assistant) using household tools, connectors wrapping tools that already
  ship an MCP server, schedules, a gateway with policy and audit (§8.2).

## Considered options

* One tool contract in the SDK, an in-core registry, skills on top, MCP as adapters at the edges
* An MCP server per plugin, aggregated by a gateway, even for in-process plugins
* Agent skills only (prompt bundles), with tools reached through the plugins' REST APIs

## Decision outcome

Chosen option: "One tool contract and an in-core registry", decided with the project owner on 2026-10-24.

* **Contract.** A plugin declares tools in `contributes.tools[]` (name `<plugin>.<verb>`, English description for
  models, annotations, data class, permission, the `agent` exposure switch) and registers the same tools in code with
  `hauskraft_sdk.tools.ToolSpec`: Pydantic input and output models and an async handler that calls the plugin's
  service functions. Missing annotations count as destructive, write and open-world (§5.3). Core refuses a plugin
  whose manifest and code disagree.
* **Wire names.** Function names in Chat Completions may not contain dots, so `tasks.create` is sent as
  `tasks_create`. The registry maps both ways and rejects collisions.
* **Registry and selection.** Core collects every tool once and builds its JSON schema. Each run gets
  `select(actor, run_kind, skill, page_hint)`: the tools the person's role permits (the permission table of ADR 0016),
  that the owner has not switched off, whose data class the endpoint may see, and that the running skill allows. A
  later `find_tools` lookup and the §8.2 gateway attach here.
* **Budgets.** Each plugin's serialized tool definitions stay under about 1,500 tokens (6,000 characters as the
  tested approximation), and outputs are compact (needed fields only, capped lists).
* **Skills** are declarative bundles on top of the registry (ADR 0023).
* **MCP** is an adapter, not the internal protocol: exposing the registry to outside agents (Streamable HTTP with
  per-person tokens) and wrapping outside MCP servers as registry tools both come later.

### Consequences

* Good, because in-process plugins need no extra transport, process or serialisation layer, and tests can call tools
  directly.
* Good, because the same registry feeds the assistant now and an MCP server, a gateway or schedules later.
* Good, because selection per run keeps token cost and model confusion low as plugins grow.
* Bad, because the manifest and the code both list tools. The load-time check and a contract test keep them aligned.
* Bad, because outside agents can't use household tools until the MCP adapter exists.

## More information

Spec §5.3, §8.0, §14 item 14; ADR 0016, ADR 0020, ADR 0023; stories M2S-E02-01 to M2S-E02-04.
