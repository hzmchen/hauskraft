// SPDX-License-Identifier: MIT
import type { TaskOut } from "@hearthos/sdk-ts";
import { Checkbox } from "@hearthos/ui";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useUpdateTask } from "../api";
import { DueBadge } from "./DueBadge";
import { TaskTitle } from "./TaskTitle";

/** One task: done checkbox (theme style, fixed label), editable title, due badge, optional extras. */
export function TaskRow({ task, children }: { task: TaskOut; children?: ReactNode }) {
  const { t } = useTranslation("tasks");
  const update = useUpdateTask();
  return (
    <li className="flex min-h-9 items-center gap-2">
      <Checkbox
        aria-label={t("a11y.mark_done", { title: task.title })}
        checked={task.done}
        onCheckedChange={(checked) => update(task.id, { done: checked === true })}
      />
      <TaskTitle title={task.title} done={task.done} onRename={(title) => update(task.id, { title })} />
      <DueBadge due={task.due_on} done={task.done} />
      {children}
    </li>
  );
}
