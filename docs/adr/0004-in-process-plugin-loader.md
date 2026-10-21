---
status: Accepted
date: 2026-10-12
---

# In-process plugin loader for M0*

Status: Accepted

## Context and problem statement

M0* must prove the plugin skeleton end to end with one native plugin (`dev.hauskraft.tasks`) without building the full plugin host (signing, isolation tiers, registry).

## Decision drivers

* Prove manifests, contributions and the plugin data seam now.
* Keep the manifest format stable for later runtimes.
* Themes are data and must never execute code.

## Considered options

* Manifest-validated in-process loader + build-time web registry
* Subprocess/container runtime from day one
* Hard-coded tasks module in core

## Decision outcome

Chosen option: "Manifest-validated in-process loader". At API start, core reads every `hauskraft.plugin.json` under `HAUSKRAFT_PLUGIN_PATHS` and `HAUSKRAFT_THEME_PATHS`, validates it against the manifest schema and checks `hauskraft_api` against the SDK version. `inprocess` plugins have their Python entrypoint imported, `register(ctx)` called and their router mounted under `/api/v1{api_prefix}`. `declarative` plugins of type `theme` go to the theme registry without importing anything. Other runtimes are recorded as unsupported in M0*. The web side uses a registry generated at build time from manifests with `runtime.web`. The same manifest will drive the subprocess, container and WASM runtimes in `plugin_host` later.

### Consequences

* Good, because the tasks plugin exercises the real contract without core special-casing
* Good, because the manifest stays the single source for all future runtimes
* Bad, because a faulty in-process plugin can crash core; acceptable only for first-party code
* Bad, because code plugins cannot be installed at runtime in M0* (themes can, as data)

## More information

Spec §5; stories M0S-E06-03, M0S-E06-06.
