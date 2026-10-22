# E08 · Settings shell

**Goal:** Settings becomes an area with sections that follow the user's role and look the same in every theme
(spec §10.1).
**Out of scope:** A Plugins section (later), per-user theme choice.
**Dependencies:** E02-01, E02-04.

---

## Contract: settings sections

| Order | Section | Route | Visible to | de |
|---|---|---|---|---|
| 1 | Appearance | `/settings/appearance` | everyone | Darstellung |
| 2 | Account | `/settings/account` | everyone | Konto |
| 3 | Household | `/settings/household` | owners | Haushalt |
| 4 | Members | `/settings/members` | owners | Mitglieder |

- `/settings` keeps redirecting to `/settings/appearance` (M0* contract, `tests/e2e/demo.spec.ts` step 8).
- The sections are a `navigation` named "Settings" inside `<main>`, built from one settings model filtered by
  `Session.permissions`, not by role names. The main navigation stays Today, Tasks, Activity, Settings for everyone.
- An adult who opens an owner-only route is redirected to `/settings/appearance`.
- Visibility depends on the role, never on the theme: within one role, every theme exposes the same accessibility
  tree (spec §10.2.2).

---

## M1S-E08-01 · Settings layout and sections
- **Story:** As a member, I want settings grouped in sections I can actually use, so that I'm not shown things I'm
  not allowed to change.
- **AC:**
  - Given an owner, the navigation "Settings" lists Appearance, Account, Household, Members in this order, and each
    link opens its page with a level-1 heading of the same name.
  - Given an adult, it lists Appearance, Account only; `/settings/household` and `/settings/members` redirect to
    `/settings/appearance`.
  - The section names are translated (de in the table above).
  - Every settings view passes the invariance and axe checks in the three built-in themes, light and dark, at both
    viewports used by M0*.
- **Tech:** `apps/web/src/routes/_app/settings.tsx` (layout route with `<Outlet>`), a `settingsSections` model next to
  the `NavModel`.
- **Tests:** E2E: `tests/e2e/settings.spec.ts`. Vitest: model filtering.
- **Deps:** E02-04 · **Est:** M · **Labels:** area:web, theme, a11y

## M1S-E08-02 · Appearance for adults
- **Story:** As an adult, I want to see the household theme and still choose my device's colour mode, so that I
  understand why I can't change the theme.
- **AC:**
  - Given an adult on `/settings/appearance`, the radiogroup "Household theme" shows the active theme checked and
    every radio disabled, and the region says "Only owners can change the household theme."
  - The region "This device" and the radiogroup "Colour mode" work as in M0*.
  - Given an owner, the page is unchanged from M0*.
- **Tech:** `routes/_app/settings.appearance.tsx`, reading `Session.permissions`.
- **Tests:** E2E: `tests/e2e/settings.spec.ts`, `tests/e2e/basics.spec.ts` step 5.
- **Deps:** E08-01, E02-01 · **Est:** S · **Labels:** area:web, theme

## M1S-E08-03 · Account settings in the account menu
- **Story:** As a member, I want to reach my account settings from the account menu, so that I find them where I
  expect.
- **AC:**
  - Given the account menu, it has a menuitem "Account settings" (de "Kontoeinstellungen") above "Sign out" that
    opens `/settings/account`.
  - The menu's existing items and the button name "Account menu" are unchanged.
- **Tech:** `apps/web/src/shell/AccountMenu.tsx`.
- **Tests:** E2E: `tests/e2e/settings.spec.ts`.
- **Deps:** E08-01 · **Est:** S · **Labels:** area:web
