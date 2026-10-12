<!-- SPDX-License-Identifier: MIT -->

# @hearthos/schemas

MIT-licensed JSON Schemas shared by core, SDKs, plugins and themes: plugin manifest (M0S-E06-01), events (M0S-E10-01), theme contract (M0S-E13-01) and the generated OpenAPI file (M0S-E03-05).

| Path                                   | Schema                                                                                       | Story      |
| -------------------------------------- | -------------------------------------------------------------------------------------------- | ---------- |
| `common/defs.schema.json`              | Shared definitions: data classes, reverse-DNS ids, SemVer, semantic icon names, capabilities | M0S-E06-01 |
| `manifest/hearthos.plugin.schema.json` | Plugin manifest `hearthos.plugin.json`, including the theme plugin rule                      | M0S-E06-01 |

## Data classes

Every entity, event and manifest carries a data class from this ordered list (lowest to highest sensitivity, spec §5.5, ADR-0008):

`public` < `household` < `personal` < `financial` < `tenant` < `child` < `health` < `secret`

Taint propagates as the maximum of the inputs. M0* records data classes but does not enforce routing or access.

## Theme plugin rule

A manifest whose `type` is exactly `["theme"]` must use `runtime.kind: "declarative"`, declare no capabilities and no data classes, contribute at least one `themes[]` entry and no widgets, pages, tools or workflows (spec §5.3). The schema enforces this with `if`/`then`.

## Changing a schema

Schemas are contracts. Change them only together with an ADR (ADR-0001), add valid and invalid fixtures under `tests/fixtures/`, and run `just contract`.
