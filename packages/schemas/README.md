<!-- SPDX-License-Identifier: MIT -->

# @hauskraft/schemas

MIT-licensed JSON Schemas shared by core, SDKs, plugins and themes: plugin manifest (M0S-E06-01), events (M0S-E10-01), theme contract (M0S-E13-01) and the generated OpenAPI file (M0S-E03-05).

| Path                                    | Schema                                                                                       | Story      |
| --------------------------------------- | -------------------------------------------------------------------------------------------- | ---------- |
| `common/defs.schema.json`               | Shared definitions: data classes, reverse-DNS ids, SemVer, semantic icon names, capabilities | M0S-E06-01 |
| `manifest/hauskraft.plugin.schema.json` | Plugin manifest `hauskraft.plugin.json`, including the theme plugin rule                     | M0S-E06-01 |

## Data classes

Every entity, event and manifest carries a data class from this ordered list (lowest to highest sensitivity, spec §5.5, ADR-0008):

`public` < `household` < `personal` < `financial` < `tenant` < `child` < `health` < `secret`

Taint propagates as the maximum of the inputs. M0* records data classes but does not enforce routing or access.

## Theme plugin rule

A manifest whose `type` is exactly `["theme"]` must use `runtime.kind: "declarative"`, declare no capabilities and no data classes, contribute at least one `themes[]` entry and no widgets, pages, tools or workflows (spec §5.3). The schema enforces this with `if`/`then`.

## Changing a schema

Schemas are contracts. Change them only together with an ADR (ADR-0001), add valid and invalid fixtures under `tests/fixtures/`, and run `just contract`.

## Events

`events/cloudevent.schema.json` is the CloudEvents 1.0.2 envelope with the Hauskraft extensions `dataclass` and `actorid` (attribute names may not contain underscores). Each event type has a data schema `events/<type without "hauskraft.">.data.schema.json` whose `$id` is the envelope's `dataschema` URL. The Python models in `hauskraft_sdk.events` mirror these schemas and are tested against them.

## Generated types

`just gen` (or `just gen-theme-types`) turns the theme contract into `packages/ui/src/theme/contract.gen.ts` (`IconName`, `TokenName`, layout unions) and `packages/sdk-py/src/hauskraft_sdk/theme_contract.py` (`Literal` types). Never edit those files; a contract test fails when they are stale. Numbers and limits are fixed in ADR-0013.
