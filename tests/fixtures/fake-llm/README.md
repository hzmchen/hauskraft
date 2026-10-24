<!-- SPDX-License-Identifier: MIT -->

# Fake model for assistant tests

A small OpenAI-compatible Chat Completions server (`server.py`, Python standard library only) that answers from
scripted scenarios (`scenarios.json`) and records every request. Live and Playwright tests point the assistant at it,
so CI needs no real provider and every answer is deterministic (ADR 0022). It is spec-owned: change it only together
with the tests that rely on it.

Run it locally with `python tests/fixtures/fake-llm/server.py --port 8090`; the test stack runs it as the `fake-llm`
service (M2S-E01-01).

## Endpoints

| Method & path | What it does |
|---|---|
| `POST /v1/chat/completions` | Answers from the scenarios (below). Non-streaming only. |
| `GET /v1/models` | Lists `fake-tools`, `fake-no-tools`, `fake-broken`, `fake-loop`, `fake-no-usage`. |
| `GET /_requests?contains=<text>&limit=<n>` | Recorded requests whose messages contain `<text>`, oldest first: `at`, `authorization`, `model`, `tools` (offered function names), `messages`, `body`. |
| `POST /_reset` | Forgets every recorded request. |
| `GET /healthz` | `{"status": "ok"}` |

## Behaviour

- **Key:** a missing bearer token or the key `wrong-key` gets 401 (`invalid_api_key`).
- **Models:** an unknown model gets 404 (`model_not_found`); `fake-broken` always answers 500; `fake-no-tools`
  answers 400 when the request offers tools; `fake-loop` calls `tasks_list` on every request; `fake-no-usage` leaves
  out `usage`. `"stream": true` gets 400.
- **Scenarios:** the first scenario whose `system` regex is found in the system prompt and whose `match` regex matches
  the whole latest user message (case-insensitive) is used. The number of assistant messages since that user message
  picks the step:
  - `call`: tool calls. If a named tool was not offered, the answer is "I can't do that: the tool `<name>` is not
    available." instead.
  - `say`: a text answer; `say_denied` replaces it when the latest tool result says the call was denied,
    `say_failed` when it contains `not_found` or `error`.
  - `output` / `output_from_lines`: structured output, sent the way the request asks for it (`response_format`, an
    output tool whose name starts with `final_result`, or JSON text). `output_from_lines` turns every user-message line
    that starts with `- ` or `* ` into `{"title": …, "due_on": null}` and ignores all other lines.
- **Templates:** `{{g:name}}` (a named regex group), `{{date:+N}}` (the system prompt's `Today: YYYY-MM-DD` line plus
  N days; `NO-DATE-IN-CONTEXT` if missing), `{{find:<title>}}` (the `id` next to that title in the latest tool
  results; `NOT-FOUND` if missing), `{{titles}}` (the titles in the newest tool result), `{{user}}`, `{{null}}`.
- **Usage:** `prompt_tokens` is a quarter of the characters of the messages and tools, `completion_tokens` a quarter of
  the answer's characters plus one.
- Without a matching scenario the answer is `FAKE: no scenario matches: <message>`.
