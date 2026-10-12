---
status: Accepted
date: 2026-10-12
---

# Widget grid: react-grid-layout v2

Status: Accepted

## Context and problem statement

The Today dashboard places widgets on a grid that users can drag and resize. Layouts are stored per user and must stay valid across themes.

## Decision drivers

* React-native API with TypeScript types.
* Explicit layout state we can persist.
* The grid must not depend on the theme.

## Considered options

* react-grid-layout v2
* gridstack.js
* CSS grid with a custom drag layer

## Decision outcome

Chosen option: "react-grid-layout v2": React-native, typed, hooks API (`useContainerWidth`), explicit `layout` state persisted per user via the API. The grid has **12 columns in every theme**; density changes only row height and gutters (CSS variables), so switching theme never invalidates a saved layout.

### Consequences

* Good, because layouts are plain JSON and theme-independent
* Bad, because positioning uses inline styles, which requires `style-src 'unsafe-inline'` in the CSP until nonces are introduced

## More information

Spec §10.3; story M0S-E08-06.
