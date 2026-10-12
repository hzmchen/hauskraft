---
status: Accepted
date: 2026-10-12
---

# Licence split: AGPL core, MIT plugin-facing parts

Status: Accepted

## Context and problem statement

HearthOS is a network service whose improvements should flow back, but plugin and theme authors must be able to build on its SDKs without inheriting the core's copyleft. Spec §4.2 sets the split.

## Decision drivers

* Hosted forks of the core must share their changes.
* Plugin authors must not be forced into AGPL by importing the SDK.
* Keep the number of licences small and familiar.
* Provenance must be clean and machine-checkable.

## Considered options

* AGPL core + MIT plugin-facing packages
* AGPL core + MPL-2.0 plugin-facing packages
* Everything MIT
* Everything AGPL

## Decision outcome

Chosen option: "AGPL core + MIT plugin-facing packages". `services/**` and `apps/**` are **AGPL-3.0-or-later**. Everything plugin-facing is **MIT**: `packages/sdk-py`, `packages/sdk-ts`, `packages/ui`, `packages/schemas`, official plugins, built-in themes, the theme template and the HA integration. Bundled fonts are **OFL-1.1**; icon packs keep their own permissive licences (Lucide ISC, Pixelarticons MIT). MPL-2.0 was considered and rejected: its file-level copyleft adds little because a modified SDK is useless without the AGPL core, and MIT is simpler for plugin authors. In-process plugins may import only the MIT packages (lint-enforced). Files carry REUSE-compliant SPDX headers; contributions use DCO sign-off, no CLA. This is not legal advice.

### Consequences

* Good, because plugin and theme authors can choose any licence
* Good, because the core stays copyleft for hosted forks
* Bad, because the licence boundary must be enforced by lint rules and a licence-map check in CI
* Bad, because closed-source in-process plugins remain legally unsettled; out-of-process runtimes are recommended for them

## More information

Spec §4.2; `LICENSING.md`; stories M0S-E12-03 and M0S-E02-04.
