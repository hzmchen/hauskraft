# UI contract: accessible names and test hooks

The spec-owned end-to-end tests (`tests/e2e/`) find everything by **role and accessible name**, never by CSS classes or DOM structure. That keeps them independent of the implementation and of the theme. The names below are part of the acceptance criteria of the UI stories (E08, E09, E10-03, E13-05, E13-07). English names are normative; German equivalents are listed where a test uses them.

Changing a name is a contract change: update this file and the e2e tests together, with the spec owner. A meta test (`tests/meta/test_suite_conventions.py`) fails if an e2e test uses a literal name that is not listed here. In the tables, `<title>` stands for a task title and `<n>` for a number.

## Test hooks (not visible to users)

| Hook | Where | Values | Story |
|---|---|---|---|
| `data-hauskraft-theme` | `<html>` | active `theme_id`, e.g. `dev.hauskraft.theme.hackspace` | M0S-E13-05 |
| `data-hauskraft-chrome`, `data-hauskraft-header`, `data-hauskraft-button`, `data-hauskraft-checkbox`, `data-hauskraft-density`, `data-hauskraft-content` | `<html>` | the active theme's variants | M0S-E13-05 |
| `class="dark"` | `<html>` | present in dark mode | M0S-E08-02 |
| `data-nav-style` | the `nav` named "Main" | `sidebar`, `topbar`, `bottom-tabs`, `drawer` | M0S-E13-05 |
| `localStorage["hauskraft.mode"]` | browser | `system`, `light`, `dark` | M0S-E08-02 |

## Login (`/login`) · M0S-E08-03

| Role | Name | Notes |
|---|---|---|
| textbox | Username | |
| textbox (password) | Password | found by label |
| button | Sign in | |
| alert | (text) Wrong username or password | same text for unknown user and wrong password |

## Shell · M0S-E08-05, M0S-E08-04

| Role | Name | Notes |
|---|---|---|
| link | Skip to content | first focusable element |
| navigation | Main | items in this order: **Today, Tasks, Activity, Settings** (de: Heute, Aufgaben, Aktivität, Einstellungen) |
| button | Open menu | only when the navigation style is `drawer` |
| main | | one per page |
| button | Account menu | opens a menu; shows this name as its label, not the user's name (WCAG 2.5.3) |
| menuitem | Sign out | in the account menu |
| menuitemradio | English, Deutsch | language choice in the account menu |
| heading (level 1) | (text) Page not found | for unknown `/p/<id>` routes |

## Today (`/today`) · M0S-E08-06, M0S-E09-01

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Today | de: Heute |
| button | Edit layout / Done editing | toggles grid edit mode |
| region | Tasks | the tasks widget; de: Aufgaben |
| textbox | Add a task | in the widget; Enter adds; de: Aufgabe hinzufügen |
| list | Open tasks | open tasks, newest first |
| list | Done tasks | shown after "Show done" is pressed |
| checkbox | Mark '<title>' as done | one per task, in widget and page; checked when done |
| button | Edit '<title>' | the task title; starts inline editing |
| textbox | Task title | inline editor; Enter saves, Escape cancels |
| button | Show done (<n>) | toggles the done list |
| link | All tasks | goes to `/p/tasks` |
| (text) | Overdue · Today · Due <date> | due badges always carry words, not only colour |

## All tasks (`/p/tasks`) · M0S-E09-02

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | All tasks | |
| tab | Open, Done, All | filter; state in `?status=` |
| combobox | Sort by | options: Created, Due date |
| textbox (date) | Due date for '<title>' | native `input type="date"`, found by label |
| button | Clear due date for '<title>' | |
| button | Delete '<title>' | opens the confirmation |
| dialog or alertdialog | Delete task? | buttons: Delete, Cancel |
| navigation | Pagination | buttons: Previous page, Next page |
| (text) | No tasks yet | empty state |

## Activity (`/activity`) · M0S-E10-03

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Activity | |
| list | Activity | newest first |
| (text) | <actor> added '<title>' · <actor> updated '<title>' · <actor> completed '<title>' · <actor> deleted '<title>' · <actor> switched the theme to <theme name> | summary formats; `<actor>` is the display name |

## Settings → Appearance (`/settings/appearance`) · M0S-E13-07, M0S-E08-02

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Appearance | |
| region | Household theme | contains the text "Applies to everyone on every device" |
| radiogroup | Household theme | one radio per theme, named by the theme's own name (e.g. Default, Paper, Hackspace); invalid themes disabled |
| button | Show problems | per invalid theme; expands the reasons |
| dialog | Change the look for everyone? | buttons: Change theme, Cancel |
| region | This device | contains the text "Only this device" |
| radiogroup | Colour mode | radios: System, Light, Dark |

---

# M1* additions (Household basics)

The names below belong to the M1* UI stories (`docs/backlog/m1-star/`). Password fields are found by their exact
label (`getByLabel(name, { exact: true })`), because several labels on one page contain the word "password".

## Changes to M0* views

| View | Role | Name | Notes | Story |
|---|---|---|---|---|
| Login | status | (text) Your session has ended. Please sign in again. | shown for `?reason=expired` | M1S-E07-03 |
| Login | alert | (text) This account is deactivated. Ask an owner of your household. | after a correct password for a deactivated account | M1S-E07-04 |
| Login | textbox | Username / Password | `autocomplete="username"` / `autocomplete="current-password"` | M1S-E07-04 |
| Shell | menuitem | Account settings | in the account menu, above Sign out; de: Kontoeinstellungen | M1S-E08-03 |
| Shell | button | Kontomenü | the German name of "Account menu" (used by `basics.spec.ts` after setup in Deutsch) | M1S-E03-02 |
| Shell | (document title) | `<page heading> · <household name>` | e.g. "Today · Demo household"; signed-out pages: "Hauskraft" | M1S-E04-04 |
| Appearance | (text) | Only owners can change the household theme. | adults only; the radios of "Household theme" are disabled | M1S-E08-02 |
| Activity | (text) | <actor> added <name> to the household · <actor> updated the account of <name> · <actor> deactivated <name> · <actor> reactivated <name> · <actor> reset the password of <name> · <actor> changed their password · <actor> changed the household settings | de: `<actor> hat <name> zum Haushalt hinzugefügt` and the others in `docs/backlog/m1-star/E09-account-events-and-activity.md` | M1S-E09-02 |

## Setup (`/setup`) · M1S-E03-02

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Set up your household | de: Haushalt einrichten |
| textbox | Household name | |
| combobox | Language | options: English, Deutsch |
| combobox | Time zone | options named by IANA id, e.g. Europe/Berlin |
| textbox | Your name | becomes the display name |
| textbox | Username | `autocomplete="username"` |
| textbox (password) | Password | exact label; `autocomplete="new-password"` |
| textbox (password) | Repeat password | exact label; `autocomplete="new-password"` |
| (text) | At least 12 characters | visible before typing |
| alert | (text) Passwords do not match | client-side check |
| button | Create household | |

## Choose a new password (`/change-password`) · M1S-E07-02

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Choose a new password | |
| (text) | Your password was set by someone else. Choose your own to continue. | |
| textbox (password) | Current password | exact label; `autocomplete="current-password"` |
| textbox (password) | New password | exact label; `autocomplete="new-password"` |
| textbox (password) | Repeat new password | exact label; `autocomplete="new-password"` |
| (text) | At least 12 characters | |
| button | Save password | |

German names (a new member starts in the household language): heading **Neues Passwort wählen**, labels **Aktuelles Passwort**, **Neues Passwort**, **Neues Passwort wiederholen**, button **Passwort speichern**.

## Settings navigation · M1S-E08-01

| Role | Name | Notes |
|---|---|---|
| navigation | Settings | inside `main`; links in this order: **Appearance, Account, Household, Members** for owners, **Appearance, Account** for adults (de: Darstellung, Konto, Haushalt, Mitglieder) |

## Settings → Account (`/settings/account`) · M1S-E05-03, M1S-E05-04

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Account | de: Konto |
| region | Profile | shows the username read-only |
| textbox | Display name | |
| combobox | Language | options: English, Deutsch |
| button | Save profile | then the text "Profile saved" |
| region | Password | |
| textbox (password) | Current password / New password / Repeat new password | exact labels, autocomplete as on `/change-password` |
| button | Change password | then the text "Password changed"; mismatch: alert "Passwords do not match"; 422 `wrong_password`: alert "The current password is wrong." |
| region | Devices | |
| list | Signed-in devices | one listitem per session, newest activity first |
| (text) | This device | in the current session's listitem, which has no sign-out button |
| button | Sign out | in every other listitem |
| button | Sign out everywhere | opens the confirmation |
| alertdialog | Sign out everywhere? | buttons: Sign out everywhere, Cancel |

## Settings → Household (`/settings/household`, owners) · M1S-E04-02

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Household | de: Haushalt |
| textbox | Household name | |
| combobox | Time zone | options named by IANA id |
| combobox | Default language | options: English, Deutsch; hint "Used for new members" |
| button | Save household | then the text "Household saved" |

## Settings → Members (`/settings/members`, owners) · M1S-E06-05

| Role | Name | Notes |
|---|---|---|
| heading (level 1) | Members | de: Mitglieder |
| button | Add member | opens the dialog |
| list | Members | one listitem per account: display name, username, role (Owner / Adult), "Deactivated" when inactive |
| button | Edit <name> | per member; opens "Edit member" |
| button | Reset password for <name> | per member except yourself; opens "Reset password?" |
| button | Deactivate <name> | per active member; opens the confirmation |
| button | Reactivate <name> | per deactivated member; no confirmation |
| dialog | Add member | textbox Display name, textbox Username, combobox Role (Owner, Adult; default Adult), password Temporary password (exact label, `autocomplete="new-password"`), text "At least 12 characters"; buttons: Add member, Cancel |
| dialog | Edit member | textbox Display name, combobox Role; buttons: Save, Cancel |
| dialog | Reset password? | password Temporary password; buttons: Reset password, Cancel |
| alertdialog | Deactivate <name>? | text "They are signed out everywhere and can't sign in until reactivated."; buttons: Deactivate, Cancel |
| alert | (text) The household needs at least one active owner. | on 409 `last_owner` |
