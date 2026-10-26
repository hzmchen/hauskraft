<!-- SPDX-License-Identifier: MIT -->

# The assistant

Hauskraft's assistant does household work for you when you ask in plain language: "Add 'Buy milk', due tomorrow",
"What is still open?", "Mark 'Plan the garden' as done". It works through the tools that plugins offer, with exactly
your permissions, and everything it changes shows in **Activity** as "… via assistant …". This page is for owners who
set it up and for everyone who uses it. The background is in [spec §8.0](spec/hauskraft-spec-v0.4.md) and ADRs
[0019](adr/0019-tool-contract-and-registry.md) to [0023](adr/0023-skill-format.md).

## Choose a model

The assistant talks to any OpenAI-compatible **Chat Completions** endpoint that supports tool calls:

- **A cloud provider** (OpenAI, an OpenRouter-style router, or another compatible API). Prefer an account with
  **zero data retention (ZDR)**, so the provider doesn't keep what the assistant sends. Create a dedicated API key for
  Hauskraft with a **spend limit** at the provider; that limit is your real budget, because Hauskraft only shows
  usage so far.
- **A local server** on your network (Ollama, llama.cpp, vLLM, LM Studio, a LiteLLM proxy). Nothing leaves your home.
  Small local models often struggle with tool calls; check one with the evals before relying on it
  ([evals backlog](backlog/m2-star/E09-evals.md)).

What the model sees: the system prompt (household name, today's date and time zone, your name, role and language),
your messages, and the results of the tools it uses (for tasks: titles, due dates, done or open). It never sees
passwords, other people's chats or plugins you switched off.

## Set it up (owners)

**Settings → Assistant → Endpoint:**

1. Enter the **Base URL** (for example `https://api.openai.com/v1`), the **Model** and the **API key**, choose
   **Model location** (Cloud or Local) and **Save endpoint**.
2. Click **Test connection**. It sends one tiny request and shows four checks: server reachable, API key accepted,
   model found, tool calls supported. All four must say OK.
3. The **Assistant** button now appears at the top of every page for owners and adults.

**Remove endpoint** deletes the URL, model and key; nobody can use the assistant until you set it up again.

### How the key is stored

The API key is **encrypted** in the database (AES-GCM, with a key derived from `HAUSKRAFT_SECRET_KEY`), and the page
only ever shows its last four characters. That protects you when a **backup** or database dump ends up somewhere it
shouldn't. It does **not** protect against someone who controls the running server: the server needs the key to call
the model, so it holds both halves. Keep the server updated, use a dedicated key with a spend limit, and rotate it if
in doubt.

Outside production (`HAUSKRAFT_ENV` other than `production`), `HAUSKRAFT_SECRET_KEY` is generated anew on every start,
so after a restart the page says "Enter the API key again" and you re-enter it. In production the variable is
required and stays the same.

## Use it

Open the **Assistant** panel at the top of any page. On a wide screen it sits beside the page, so you see your tasks
change; on a phone it covers the page below the header. The panel remembers whether it was open on this device.

- Your **chats are private**: nobody else sees them, owners included. They are kept until you delete them
  (**Delete chat** in the list).
- Every change appears as a card: "Added task 'Buy milk' · Open · **Undo**". **Undo** reverses additions and changes.
- Anything that **deletes** waits for you to confirm: a card asks "Delete task 'Buy milk'?" and nothing happens until
  you click **Delete**. **Cancel** leaves everything as it is.
- **Add from text** on All tasks: paste a note or an email, and the assistant suggests tasks; you pick which to add.
  The pasted text is treated as data, so instructions hidden in it can't make the assistant do anything.
- The **Weekly overview** widget (add it to Today with **Edit layout**) writes a short overview of the week's tasks
  when you click **Create now**.

If the assistant can't finish, it says why: the model isn't reachable, the key was refused, or the request took too
many steps.

## Govern it (owners)

- **Tools:** Settings → Assistant → Tools lists every tool plugins offer, with what it does ("Reads only", "Changes
  data", "Deletes – asks first"). Switch a tool off and the assistant is never offered it.
- **Usage:** the **Usage** tables show requests and tokens per day, per member and per model for today, the last 7
  or the last 30 days. Requests whose tokens the server didn't report are counted as "unknown". Enter your provider's
  prices per million tokens to see an estimated cost. This is an overview, not a limit: set the limit at the provider.
- **Activity** shows everything the assistant changed, with the person it acted for.

## Not there yet

These come later, one at a time ([backlog](backlog/m2-star/README.md), § Deferred): schedules (an overview every
Monday), an approval inbox and a smarter gate that asks less often, budget limits in Hauskraft, streaming answers,
voice, an MCP server for other assistants such as Claude Desktop or Home Assistant, routing sensitive data to a local
model, and more than one model.
