// SPDX-License-Identifier: MIT
// All tasks (M0S-E09-02): filter, sort, due dates, delete, 50 per page. Filter, sort and page live in the
// URL (useHost().search), validated here.
import { useHost, type PageProps } from "@hauskraft/sdk-ts";
import { Button, Tabs, TabsContent, TabsList, TabsTrigger } from "@hauskraft/ui";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { useTaskList, type Status } from "../api";
import { DeleteTaskDialog } from "../components/DeleteTaskDialog";
import { DueDatePicker } from "../components/DueDatePicker";
import { TaskRow } from "../components/TaskRow";

const PAGE_SIZE = 50;
const STATUSES = ["open", "done", "all"] as const;
const SORTS = { created: "-created_at", due: "due_on" } as const;
type SortKey = keyof typeof SORTS;

/** Read the page state from the URL; anything unknown falls back to the defaults. */
export function readSearch(search: Readonly<Record<string, string>>) {
  const status: Status = (STATUSES as readonly string[]).includes(search.status ?? "")
    ? (search.status as Status)
    : "open";
  const sort: SortKey = search.sort === "due" ? "due" : "created";
  const page = Math.max(1, Number.parseInt(search.page ?? "1", 10) || 1);
  return { status, sort, page };
}

export function TasksPage({ pluginId }: PageProps) {
  const { t } = useTranslation("tasks");
  const host = useHost();
  const { status, sort, page } = readSearch(host.search);
  const list = useTaskList({ status, sort: SORTS[sort], limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  const sortId = useId();
  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div data-plugin={pluginId} className="flex flex-col gap-density">
      <h1 className="text-2xl font-bold">{t("page_heading")}</h1>
      <Tabs value={status} onValueChange={(value) => host.setSearch({ status: value, page: undefined })}>
        <div className="flex flex-wrap items-center justify-between gap-density">
          <TabsList>
            {STATUSES.map((value) => (
              <TabsTrigger key={value} value={value}>
                {t(`filter.${value}`)}
              </TabsTrigger>
            ))}
          </TabsList>
          <span className="flex items-center gap-2">
            <label htmlFor={sortId}>{t("sort.label")}</label>
            <select
              id={sortId}
              value={sort}
              onChange={(event) => host.setSearch({ sort: event.target.value, page: undefined })}
              className="h-control rounded-md border border-input bg-background px-2 text-foreground"
            >
              <option value="created">{t("sort.created")}</option>
              <option value="due">{t("sort.due")}</option>
            </select>
          </span>
        </div>
        <TabsContent value={status} className="pt-density">
          {list.data && list.data.items.length === 0 ? (
            <p className="text-muted-foreground">{t("empty")}</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {list.data?.items.map((task) => (
                <TaskRow key={task.id} task={task}>
                  <DueDatePicker task={task} />
                  <DeleteTaskDialog task={task} />
                </TaskRow>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
      {pages > 1 ? (
        <nav aria-label={t("pagination.label")} className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => host.setSearch({ page: String(page - 1) })}
          >
            {t("pagination.previous")}
          </Button>
          <span>{t("pagination.status", { page, pages })}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => host.setSearch({ page: String(page + 1) })}
          >
            {t("pagination.next")}
          </Button>
        </nav>
      ) : null}
    </div>
  );
}
