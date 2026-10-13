// SPDX-License-Identifier: MIT
// A native date input (labelled per task) plus a clear button. Dates are plain YYYY-MM-DD, no time zone.
import type { TaskOut } from "@hearthos/sdk-ts";
import { Button, Icon, Input } from "@hearthos/ui";
import { useTranslation } from "react-i18next";

import { useUpdateTask } from "../api";

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function DueDatePicker({ task }: { task: TaskOut }) {
  const { t } = useTranslation("tasks");
  const update = useUpdateTask();
  return (
    <span className="flex shrink-0 items-center gap-1">
      <Input
        type="date"
        aria-label={t("due_input.set", { title: task.title })}
        value={task.due_on ?? ""}
        onChange={(event) => {
          const value = event.target.value;
          if (value === "" || ISO_DATE.test(value)) update(task.id, { due_on: value || null });
        }}
        className="h-8 w-auto"
      />
      {task.due_on ? (
        // Named by its (visually hidden) text, not aria-label: "Due date for '<title>'" must stay a unique
        // label for the date input, and label lookups match aria-label substrings.
        <Button variant="ghost" size="icon-sm" onClick={() => update(task.id, { due_on: null })}>
          <Icon name="action.cancel" />
          <span className="sr-only">{t("due_input.clear", { title: task.title })}</span>
        </Button>
      ) : null}
    </span>
  );
}
