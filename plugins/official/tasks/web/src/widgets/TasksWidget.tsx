// SPDX-License-Identifier: MIT
// The Today widget (M0S-E09-01): quick add, open tasks first, "Show done (n)", link to All tasks.
import { useHost, type WidgetProps } from "@hearthos/sdk-ts";
import { Button, Icon, Input } from "@hearthos/ui";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useCreateTask, useOpenAndDone } from "../api";
import { TaskRow } from "../components/TaskRow";

export function TasksWidget({ instanceId }: WidgetProps) {
  const { t } = useTranslation("tasks");
  const host = useHost();
  const { open, done } = useOpenAndDone();
  const create = useCreateTask();
  const [title, setTitle] = useState("");
  const [showDone, setShowDone] = useState(false);

  function add(event: FormEvent) {
    event.preventDefault();
    const clean = title.trim();
    if (!clean) return;
    create.mutate({ body: { title: clean } });
    setTitle("");
  }

  const doneCount = done.data?.total ?? 0;
  return (
    <div data-widget-instance={instanceId} className="flex flex-col gap-3">
      <form onSubmit={add} className="flex gap-2">
        <Input
          aria-label={t("add.label")}
          placeholder={t("add.placeholder")}
          value={title}
          maxLength={200}
          onChange={(event) => setTitle(event.target.value)}
        />
        <Button type="submit" size="icon" aria-label={t("add.submit")}>
          <Icon name="action.add" />
        </Button>
      </form>
      <ul aria-label={t("list.open")} className="flex flex-col gap-1">
        {open.data?.items.map((task) => (
          <TaskRow key={task.id} task={task} />
        ))}
      </ul>
      {open.data && open.data.items.length === 0 ? (
        <p className="text-muted-foreground">{t("list.empty_open")}</p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-muted-foreground">{t("open_count", { count: open.data?.total ?? 0 })}</span>
        <Button variant="ghost" size="sm" aria-expanded={showDone} onClick={() => setShowDone(!showDone)}>
          <Icon name="status.done" />
          {t(showDone ? "hide_done" : "show_done", { count: doneCount })}
        </Button>
        <a
          href="/p/tasks"
          onClick={(event) => {
            event.preventDefault();
            host.navigate("/p/tasks");
          }}
          className="text-primary underline-offset-4 hover:underline"
        >
          {t("all_tasks")} <span aria-hidden="true">→</span>
        </a>
      </div>
      {showDone ? (
        <ul aria-label={t("list.done")} className="flex flex-col gap-1">
          {done.data?.items.map((task) => (
            <TaskRow key={task.id} task={task} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
