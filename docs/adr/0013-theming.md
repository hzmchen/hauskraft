---
status: Accepted
date: 2026-10-12
---

# Theming: data-only theme packages and validator thresholds

Status: Accepted

## Context and problem statement

Households want to change how the cockpit looks without changing how it works (principle P7). Themes must be safe to install from third parties and must never hide, rename or reorder functions.

## Decision drivers

* Function invariance across all themes.
* No code or raw CSS in themes (CSS injection, tracking beacons, supply chain).
* Readability is function: a control nobody can read is effectively hidden.
* Interoperate with design-tool pipelines (Figma, Tokens Studio, Penpot).

## Considered options

* Data-only theme packages with fixed tokens, variants and layout options
* Custom CSS per theme
* In-app theme editor

## Decision outcome

Chosen option: "Data-only theme packages".

* A theme is a plugin of type `theme` with `runtime.kind: declarative`; it carries no code. One theme is active per deployment; colour mode (system, light, dark) is chosen per device and never stored on the server. Any adult may switch the theme in M0*; owner-only once RBAC lands. Per-user and per-device theme overrides are deferred.
* Tokens use the DTCG Format 2025.10, one file for light and one for dark, and are compiled server-side into one stylesheet. Component variants and limited layout options (navigation style, density, content width) are fixed enums applied through data attributes. No custom CSS, no scripts, no editor.
* Function invariance is enforced by ARIA-snapshot comparison across themes in CI plus hard contrast rules.

**Validator thresholds (normative, used by `hauskraft themes validate`, the theme registry and the acceptance suite):**

| Rule | Threshold | Issue code |
|---|---|---|
| Text contrast for every pair in `tokens-v1.json` `contrast.text`, both modes | ≥ **4.5**:1 (WCAG 2.2 AA) | `contrast.text` |
| Non-text contrast for `color.border`, `color.input`, `color.ring` against `color.background` and `color.surface`, both modes | ≥ **3**:1 | `contrast.non_text` |
| `color.destructive` vs `color.primary`, both modes | OKLab distance (ΔE OK) ≥ **0.15** | `distinct.destructive_primary` |
| Size of any single asset | ≤ **2 MB** | `asset.size` |
| Total size of all assets | ≤ **10 MB** | `asset.limit` |
| Font files | ≤ **8** | `asset.limit` |
| Symbols in an icon sprite | ≤ **500** | `asset.limit` |

Colours with alpha are composited over their background before contrast is computed. These numbers are mirrored in `packages/schemas/theme/tokens-v1.json` and `tests/_support/theme_contract.py`.

### Consequences

* Good, because a theme can never make "Delete" look like "Save" or hide a control
* Good, because third-party themes cannot inject CSS or load remote resources
* Bad, because some designs are impossible without custom CSS; demand is watched (spec §14 item 10)

## More information

Spec §10.2, §11.1; decisions D4–D6, D8; stories in epic E13.
