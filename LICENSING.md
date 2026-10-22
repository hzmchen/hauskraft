# Licensing

Hauskraft uses two licences, split by who builds on the code. This summary is not legal advice; the licence texts in `LICENSE` and `LICENSES/` are what counts.

| Part | Paths | Licence |
|---|---|---|
| Core server and web app | `services/**`, `apps/**` | AGPL-3.0-or-later (`LICENSE`) |
| Plugin-facing packages | `packages/sdk-py`, `packages/sdk-ts`, `packages/ui`, `packages/schemas` | MIT |
| Official plugins | `plugins/official/**` | MIT |
| Built-in themes and the theme template | `themes/**` | MIT for theme data; bundled fonts OFL-1.1; icon packs under their own permissive licences |
| Home Assistant integration | `integrations/ha-hauskraft` | MIT |
| Acceptance suite, scripts and fixtures | `tests/**`, `scripts/**` | MIT |
| Docs | `docs/**` | MIT |
| Third-party plugins and themes | elsewhere | the author's choice |

**Why two licences.** The core is a network service, and AGPL makes sure hosted forks share their improvements. Plugins import the SDKs and UI kit, so those must not be AGPL, or every plugin would arguably have to be AGPL too. MIT keeps plugin authors free. MPL-2.0 was considered and dropped: its extra protection adds little when a modified SDK is useless without the AGPL core (ADR-0003).

**Where the boundary sits.**
- Plugins that run out of process (container, subprocess, WASM) and declarative themes are separate works and may use any licence.
- In-process plugins may import only the MIT packages (`hauskraft_sdk`, `@hauskraft/sdk-ts`, `@hauskraft/ui`), never core internals; lint enforces this. MIT code combines with the AGPL core without conflict, so official in-process plugins are fine. Whether a closed-source third-party plugin may run in-process is legally unsettled; use an out-of-process runtime for those.
- Plugin web code bundled into the core SPA build ships as part of the AGPL web app while keeping its own MIT licence.

**Practicalities.** Every file carries an SPDX header or a `REUSE.toml` annotation, and `reuse lint` must pass. The code of conduct is the Contributor Covenant 3.0 under CC-BY-SA-4.0. Licence texts live in `LICENSES/` (fetch more with `reuse download <SPDX-ID>`). Contributions use DCO sign-off (`git commit -s`), no CLA.
