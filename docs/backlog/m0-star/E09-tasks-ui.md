# E09 · Tasks UI

**Goal:** The tasks widget and page, built only on `@hauskraft/sdk-ts` and `@hauskraft/ui`, working identically in every theme.
**Dependencies:** E07, E08, E13-02.
**UI contract:** the accessible names and test hooks in `docs/testing/ui-contract.md` are part of every UI story's AC; the spec-owned e2e tests in `tests/e2e/` rely on them.

All stories in this epic share these extra acceptance criteria:
- Only `@hauskraft/ui` primitives, semantic utility classes and `<Icon name>` are used; `hauskraft/no-raw-styles` lint passes (E13-08).
- The view passes the theme invariance suite in all three built-in themes, light and dark (E13-08).

---

## M0S-E09-01 · Tasks widget (quick add, toggle, inline title edit)
- **Story:** As an adult household member, I want to add and tick off tasks right on Today, so that the list takes seconds to use.
- **AC:**
  - Given the widget, when I type a title and press Enter, then the task appears at the top optimistically and the input clears. An empty title is blocked client-side, and a server 422 shows a toast.
  - Ticking or unticking the checkbox toggles `done` (strikethrough). The checkbox uses the theme's checkbox style but always keeps its label "Mark '<title>' as done".
  - Clicking a title enables inline edit: Enter saves, Esc cancels.
  - Open tasks are shown first, with a "Show done (n)" toggle and a link "All tasks →" to `/p/tasks`.
  - Every control has an accessible label.
- **Tech:** `plugins/official/tasks/web/src/widgets/TasksWidget.tsx` uses the generated `tasksListOptions` / `tasksCreateMutation` / `tasksUpdateMutation`. Optimistic updates use `onMutate` and roll back on error; `invalidateQueries` on the `tasks` key. Icons: `action.add`, `status.done`, `status.due`.
- **Tests:** Vitest browser mode: add, toggle, edit, rollback on 500 (MSW).
- **Deps:** E07-03, E08-06, E13-02 · **Est:** M · **Labels:** area:tasks, web

## M0S-E09-02 · All tasks page (filter, sort, due date, delete)
- **Story:** As an adult household member, I want a full list with filters and due dates, so that I can review and clean up.
- **AC:**
  - Given `/p/tasks`, I can filter Open / Done / All and sort by Created or Due. Filter state lives in URL search params, validated by the route's `validateSearch`.
  - Pagination shows 50 per page.
  - I can set or clear a due date with a labelled date input (`Due date for '<title>'`, a native `input type="date"` styled by `@hauskraft/ui`) and a `Clear due date for '<title>'` button. Overdue open tasks show a badge using `color.destructive`; due today uses `color.warning`. Badges carry text ("Overdue", "Today"), never colour alone.
  - Delete asks for confirmation in a Dialog and then removes the row. Any adult can delete any task (D3).
  - An empty state is shown when there are no tasks (illustration from the theme if provided, text always).
- **Tech:** `pages/TasksPage.tsx`, `components/{TaskRow,DueDatePicker,DeleteTaskDialog}.tsx`. Dates sent as `YYYY-MM-DD`, no timezone conversion. Icons: `action.edit`, `action.delete`, `status.overdue`.
- **Tests:** Vitest component tests; Playwright `tests/e2e/tasks.spec.ts` (spec-owned) covers filter, sort, due date and delete.
- **Deps:** E09-01, E08-05 · **Est:** M · **Labels:** area:tasks, web

## M0S-E09-03 · Tasks plugin locales (en/de)
- **Story:** As a German-speaking member, I want the tasks UI translated, so that it matches the shell.
- **AC:** Given `web/src/locales/{en,de}/tasks.json`, every visible string in the widget and page uses `t('tasks:…')`, with plural forms for "n open". The key-parity test from E08-04 covers this namespace.
- **Tech:** Keys: `widget.title`, `page.title`, `add.placeholder`, `filter.*`, `sort.*`, `due.*`, `delete.confirm`, `empty`, `a11y.*`.
- **Tests:** Parity test; Playwright checks the German "Aufgaben" heading.
- **Deps:** E09-01, E08-04 · **Est:** S · **Labels:** area:tasks, i18n
