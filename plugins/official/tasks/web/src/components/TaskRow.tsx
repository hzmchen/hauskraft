// SPDX-License-Identifier: MIT
import type { TaskOut } from "@hearthos/sdk-ts";
import { Checkbox } from "@hearthos/ui";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useUpdateTask } from "../api";
import { DueBadge } from "./DueBadge";
import { TaskTitle } from "./TaskTitle";

/** One task: done checkbox (theme style, fixed label), editable title, due badge, optional extras. */
export function TaskRow({ task, children }: { task: TaskOut; children?: ReactNode }) {
  const { t } = useTranslation("tasks");
  const update = useUpdateTask();
  // Show the new state on the click itself; the optimistic cache update follows a tick later and the
  // server's answer after that. Cleared when the save settles (success or rollback).
  const [pending, setPending] = useState<boolean | null>(null);
  const checked = pending ?? task.done;
  return (
    <li className="flex min-h-9 items-center gap-2">
      <Checkbox
        aria-label={t("a11y.mark_done", { title: task.title })}
        checked={checked}
        onCheckedChange={(value) => {
          const done = value === true;
          setPending(done);
          update(task.id, { done }, () => setPending(null));
        }}
      />
      <TaskTitle title={task.title} done={task.done} onRename={(title) => update(task.id, { title })} />
      <DueBadge due={task.due_on} done={task.done} />
      {children}
    </li>
  );
}
