# UI contract: accessible names and test hooks

The spec-owned end-to-end tests (`tests/e2e/`) find everything by **role and accessible name**, never by CSS classes or DOM structure. That keeps them independent of the implementation and of the theme. The names below are part of the acceptance criteria of the UI stories (E08, E09, E10-03, E13-05, E13-07). English names are normative; German equivalents are listed where a test uses them.

Changing a name is a contract change: update this file and the e2e tests together, with the spec owner. A meta test (`tests/meta/test_suite_conventions.py`) fails if an e2e test uses a literal name that is not listed here. In the tables, `<title>` stands for a task title and `<n>` for a number.

## Test hooks (not visible to users)

| Hook | Where | Values | Story |
|---|---|---|---|
| `data-hearth-theme` | `<html>` | active `theme_id`, e.g. `org.hearthos.theme.hackspace` | M0S-E13-05 |
| `data-hearth-chrome`, `data-hearth-header`, `data-hearth-button`, `data-hearth-checkbox`, `data-hearth-density`, `data-hearth-content` | `<html>` | the active theme's variants | M0S-E13-05 |
| `class="dark"` | `<html>` | present in dark mode | M0S-E08-02 |
| `data-nav-style` | the `nav` named "Main" | `sidebar`, `topbar`, `bottom-tabs`, `drawer` | M0S-E13-05 |
| `localStorage["hearthos.mode"]` | browser | `system`, `light`, `dark` | M0S-E08-02 |

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
| button | Account menu | opens a menu |
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
