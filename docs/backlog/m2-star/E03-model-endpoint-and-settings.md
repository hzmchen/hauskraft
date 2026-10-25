# E03 · Model endpoint & settings

**Goal:** Owners connect an OpenAI-compatible Chat Completions endpoint in the browser; the key is encrypted at rest
and never shown again (spec §8.0, ADR 0021).
**Out of scope:** Several endpoints, transcription and speech endpoints, the Responses API, an environment-variable
key override, key rotation.
**Dependencies:** E01-01 for the connection test against the fake model.

---

## Assistant settings API (contract)

| Method & path | Who | Body | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/assistant/status` | any member (`assistant.use`) | — | 200 `{available: bool}` | 401 |
| `GET /api/v1/assistant/settings` | owner (`assistant.configure`) | — | 200 `AssistantSettings` | 401, 403 `policy_denied` |
| `PATCH /api/v1/assistant/settings` | owner | `AssistantSettingsPatch` | 200 `AssistantSettings` | 403, 422 `invalid_base_url` / `unknown_tool` / validation |
| `DELETE /api/v1/assistant/settings/chat` | owner | — | 204 | 403 |
| `POST /api/v1/assistant/settings/test` | owner | — | 200 `ConnectionTest` | 403, 409 `assistant_not_configured` |

```
AssistantSettings = {
  configured: bool,                      # base_url, model and a readable key are set
  chat: {base_url: str|null, model: str|null,
         api_key_set: bool, api_key_hint: str|null,          # last four characters, e.g. "…abcd"
         api_key_status: "ok" | "missing" | "needs_reentry",
         locality: "cloud" | "local", max_data_class: DataClass,
         temperature: number|null, max_tokens: int|null, parallel_tool_calls: bool|null},
  tools_disabled: [tool name],
  prices: {input_per_million: number|null, output_per_million: number|null, currency: "EUR"}
}
AssistantSettingsPatch = {chat?: {base_url?, model?, api_key?, locality?, max_data_class?, temperature?,
                                  max_tokens?, parallel_tool_calls?}, tools_disabled?, prices?}
ConnectionTest = {ok: bool, checks: {reachable: bool, auth: bool, model: bool, tool_calls: bool},
                  latency_ms: int, error_code: null | "unreachable" | "auth_failed" | "model_not_found"
                                         | "tool_calls_unsupported" | "model_error"}
```

OpenAPI component names: `AssistantSettings`, `AssistantChatSettings`, `AssistantSettingsPatch`, `ConnectionTest`.

Defaults: `locality` `cloud`, `max_data_class` `household`, the optional model settings `null` (not sent),
`tools_disabled` empty, prices `null`. Stored as deployment settings under `assistant.*`; the key under
`assistant.endpoints.chat.api_key` as `v1:<nonce>:<ciphertext>`.

A PATCH that changes something emits one `hauskraft.settings.assistant_changed` event (source `dev.hauskraft.core`,
subject `setting/assistant`, `dataclass` `household`) with `data.changed`, the sorted list of changed field paths
(`chat.base_url`, `chat.api_key`, `tools_disabled`, `prices`, …). Never values. An unchanged PATCH emits nothing.
`DELETE /settings/chat` clears base URL, model and key and emits the event with `changed: ["chat"]`.

---

## M2S-E03-01 · Assistant permissions
- **Story:** As an owner, I want the assistant's settings to be mine to change while everyone may use it, so that the
  household can't run up costs by reconfiguring it.
- **AC:**
  - The permission table gains `assistant.use` (owner, adult), `assistant.configure` (owner) and
    `assistant.usage.read` (owner), and `Session.permissions` lists them per role.
- **Tech:** `services/core_api/src/hauskraft_core/policy/__init__.py`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_settings.py`.
- **Deps:** — · **Est:** S · **Labels:** area:auth

## M2S-E03-02 · Assistant settings API
- **Story:** As an owner, I want to set the model endpoint, switch tools and enter prices, so that the assistant uses
  the provider and the rules I chose.
- **AC:**
  - The contract above holds. `GET /assistant/status` answers `{available: true}` only when configured with a readable
    key.
  - The key is write-only: no response, event, Activity entry or log line contains it; responses show
    `api_key_hint` only.
  - `base_url` must be an absolute `http` or `https` URL (422 `invalid_base_url`); `model` 1–200 characters; `api_key`
    1–500 characters; `tools_disabled` entries must be registered tool names (422 `unknown_tool`, once E02-03 exists;
    until then any `<plugin>.<verb>` name is accepted).
  - An adult gets 403 `policy_denied` on everything but `/status`.
  - The event schema `settings.assistant_changed` exists (`additionalProperties: false`, `changed` items only).
- **Tech:** `services/core_api/src/hauskraft_core/assistant/settings.py`, the settings store, the secret box of
  E03-03; `packages/schemas/events/settings.assistant_changed.data.schema.json`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_settings.py`. Static:
  `tests/acceptance/schemas/test_assistant_event_schemas.py`, `test_openapi_m2.py`.
- **Deps:** E03-01, E03-03 · **Est:** M · **Labels:** area:api

## M2S-E03-03 · Secrets encrypted at rest
- **Story:** As an owner, I want the API key stored encrypted, so that a leaked backup doesn't leak the key.
- **AC:**
  - A small `secret_box` module encrypts with AES-GCM under a key derived by HKDF-SHA256 from `HAUSKRAFT_SECRET_KEY`
    with the label `hauskraft/settings-secret/v1`, and stores `v1:<base64 nonce>:<base64 ciphertext>`.
  - Decrypting with another secret fails cleanly (the settings API then reports `api_key_status: "needs_reentry"`).
  - The stored value never contains the plain key; repeated encryption of the same key gives different values.
- **Tech:** `services/core_api/src/hauskraft_core/secret_box.py`; dependency `cryptography` (stated in the PR).
- **Tests:** In-story: unit tests (round trip, wrong secret, nonce uniqueness, format) and an integration test that
  reads the raw settings row.
- **Deps:** — · **Est:** S · **Labels:** area:api

## M2S-E03-04 · Connection test
- **Story:** As an owner, I want to test the endpoint right after entering it, so that I know whether the assistant will
  work before anyone uses it.
- **AC:**
  - `POST /assistant/settings/test` sends a minimal request with one harmless tool and reports the four checks and the
    latency.
  - Against the fake model: model `fake-tools` and a valid key give `ok: true`; the key `wrong-key` gives
    `auth: false`, `error_code: "auth_failed"`; the model `fake-no-tools` gives `tool_calls: false`,
    `error_code: "tool_calls_unsupported"`; an unreachable URL gives `reachable: false`, `error_code: "unreachable"`
    within 15 seconds.
  - Not configured: 409 `assistant_not_configured`.
  - The fake model received the configured key as `Authorization: Bearer <key>` (the key was decrypted correctly).
- **Tech:** Pydantic AI `OpenAIChatModel` with `OpenAIProvider(base_url, api_key)`; dependency
  `pydantic-ai-slim[openai]` (stated in the PR).
- **Tests:** Live: `tests/acceptance/api/test_assistant_settings.py`.
- **Deps:** E03-02, E01-01 · **Est:** S · **Labels:** area:api, area:agent
