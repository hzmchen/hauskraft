// SPDX-License-Identifier: MIT
// The tasks namespace (en, de). Moves to locales/{en,de}/tasks.json with M0S-E09-03.
export const en = {
  widget: { title: "Tasks" },
  page: { title: "Tasks" },
  add: { label: "Add a task", placeholder: "Add a task…", submit: "Add" },
  list: { open: "Open tasks", done: "Done tasks", empty_open: "Nothing to do." },
  show_done: "Show done ({{count}})",
  hide_done: "Hide done ({{count}})",
  all_tasks: "All tasks",
  due: { overdue: "Overdue", today: "Today", on: "Due {{date}}" },
  a11y: { mark_done: "Mark '{{title}}' as done", edit: "Edit '{{title}}'", title_input: "Task title" },
  errors: { save: "Couldn't save the task. Please try again." },
};

export const de: typeof en = {
  widget: { title: "Aufgaben" },
  page: { title: "Aufgaben" },
  add: { label: "Aufgabe hinzufügen", placeholder: "Aufgabe hinzufügen …", submit: "Hinzufügen" },
  list: { open: "Offene Aufgaben", done: "Erledigte Aufgaben", empty_open: "Nichts zu tun." },
  show_done: "Erledigte anzeigen ({{count}})",
  hide_done: "Erledigte ausblenden ({{count}})",
  all_tasks: "Alle Aufgaben",
  due: { overdue: "Überfällig", today: "Heute", on: "Fällig {{date}}" },
  a11y: {
    mark_done: "'{{title}}' als erledigt markieren",
    edit: "'{{title}}' bearbeiten",
    title_input: "Titel der Aufgabe",
  },
  errors: { save: "Die Aufgabe konnte nicht gespeichert werden. Bitte versuche es noch einmal." },
};
