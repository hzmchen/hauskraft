---
status: Proposed
date: 2026-10-24
---

# Owner-configured Chat Completions endpoint with the key encrypted at rest

## Context and problem statement

The assistant needs a model. Households will mostly use a cloud API with zero data retention, some a local server
(Ollama, llama.cpp, vLLM, LM Studio) or a proxy (LiteLLM, OpenRouter). The owner sets it up in the web UI. Which API
do we speak, where does the API key live, and what does storing it protect against?

## Decision drivers

* The widest compatibility across providers and local servers.
* Owners configure it in the browser, without editing files or restarting.
* The key must not leak through backups, dumps, events, logs or API responses.
* Room for more purposes later: speech-to-text and text-to-speech for voice, several models for routing.

## Considered options

* OpenAI Chat Completions; key AES-GCM-encrypted in the database under a key derived from `HAUSKRAFT_SECRET_KEY`
* The same, but the key only from an environment variable or Docker secret
* The OpenAI Responses API

## Decision outcome

Chosen option: "Chat Completions with the key encrypted in the database", decided with the project owner on
2026-10-24.

* **API.** OpenAI-compatible Chat Completions with function calling, through Pydantic AI's `OpenAIChatModel` and
  `OpenAIProvider(base_url, api_key)`. Optional model settings (`temperature`, `max_tokens`, `parallel_tool_calls`)
  are sent only when set, because compatible servers differ. Responses arrive whole in M2*; streaming comes later.
* **Settings by purpose.** `assistant.endpoints.chat.{base_url, model, api_key, locality, max_data_class, …}`.
  `transcription`, `speech` and more models are later siblings.
* **Key at rest.** AES-GCM (`cryptography`) with a key from HKDF-SHA256 over `HAUSKRAFT_SECRET_KEY` and the label
  `hauskraft/settings-secret/v1`, so session signing and encryption never share a key. Stored as
  `v1:<nonce>:<ciphertext>`; the version prefix allows rotation. The API returns `api_key_set` and the last four
  characters only. The key never appears in events (they list changed field names), logs, exports or diagnostics.
* **Threat model, stated in the docs.** Encryption at rest protects against leaks of the database alone: a backup or
  dump that ends up elsewhere, a copied volume, read access through a bug. It does not protect against anyone who
  controls the running API process or host, which holds both halves, nor against code running in-process, which
  includes in-process plugins. The strongest controls sit with the provider: a dedicated key per installation with a
  spend limit and zero data retention, rotated when in doubt.
* **Outside production** `HAUSKRAFT_SECRET_KEY` is generated at random on every start, so a stored key can't be
  decrypted after a restart. The API then reports that the key needs re-entering; the owner accepted this for now.

### Consequences

* Good, because nearly every provider and local server speaks Chat Completions.
* Good, because a leaked backup doesn't leak the key.
* Bad, because a compromised server still exposes the key. An environment override, a rotation command and
  out-of-process plugins are deferred hardening steps.
* Bad, because Responses-only features (server-side state, built-in tools) are unavailable until a second provider
  type is added behind the same settings.

## More information

Spec §8.0, §8.9; ADR 0019, ADR 0020; stories M2S-E03-02, M2S-E03-03, M2S-E03-04.
