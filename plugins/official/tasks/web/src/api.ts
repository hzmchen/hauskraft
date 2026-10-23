// SPDX-License-Identifier: MIT
// Task queries and mutations on the generated client, with optimistic updates (M0S-E09-01).
import {
  tasksCreateMutation,
  tasksDeleteMutation,
  tasksListOptions,
  tasksUpdateMutation,
  type TaskOut,
  type TaskPage,
  type TaskPatch,
} from "@hauskraft/sdk-ts";
import { toast } from "@hauskraft/ui";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQueries,
  type Query,
  type QueryClient,
} from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

export type Status = "open" | "done" | "all";
export type Sort = "-created_at" | "due_on";

type ListQuery = { status: Status; sort: Sort; limit?: number; offset?: number };
const listOptions = (query: ListQuery) => tasksListOptions({ query: { limit: 50, offset: 0, ...query } });

/** One task list. Keeps showing the previous result while a new filter or sort loads (no empty flash); the
 * first render finds the default list prefetched by the shell. */
export function useTaskList(query: ListQuery) {
  return useQuery({ ...listOptions(query), placeholderData: keepPreviousData });
}

const widgetLists = () =>
  (["open", "done"] as const).map((status) => tasksListOptions({ query: { limit: 50, status, sort: "-created_at" } }));

/** Load what the widget and the All tasks page show by default, ahead of rendering (PluginWebModule.prefetch). */
export function prefetchTasks(queryClient: QueryClient): Promise<unknown> {
  const page = listOptions({ status: "open", sort: "-created_at" });
  return Promise.all([...widgetLists(), page].map((options) => queryClient.ensureQueryData(options)));
}

/** The widget's open and done lists, suspending until both have loaded so it appears complete at once. */
export function useOpenAndDone() {
  const [open, done] = useSuspenseQueries({ queries: widgetLists() });
  return { open: open!, done: done! };
}

interface ListKey {
  _id?: string;
  query?: { status?: Status };
}

const listKey = (query: Query): ListKey | undefined => {
  const key = query.queryKey[0] as ListKey | undefined;
  return key?._id === "tasksList" ? key : undefined;
};
const isTaskList = (query: Query) => listKey(query) !== undefined;
const fits = (query: Query, task: TaskOut) => {
  const status = listKey(query)?.query?.status ?? "all";
  return status === "all" || (status === "done") === task.done;
};

type Snapshot = [readonly unknown[], unknown][];

async function snapshot(queryClient: QueryClient): Promise<Snapshot> {
  await queryClient.cancelQueries({ predicate: isTaskList });
  return queryClient.getQueriesData({ predicate: isTaskList });
}

function restore(queryClient: QueryClient, saved: Snapshot | undefined) {
  for (const [key, data] of saved ?? []) queryClient.setQueryData(key, data);
}

function edit(queryClient: QueryClient, change: (page: TaskPage, query: Query) => TaskPage) {
  for (const query of queryClient.getQueryCache().findAll({ predicate: isTaskList })) {
    const data = query.state.data as TaskPage | undefined;
    if (data) queryClient.setQueryData(query.queryKey, change(data, query));
  }
}

function useInvalidate() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ predicate: isTaskList });
}

function useSaveFailed() {
  const { t } = useTranslation("tasks");
  return () => toast.error(t("errors.save"));
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  const failed = useSaveFailed();
  return useMutation({
    ...tasksCreateMutation(),
    onMutate: async ({ body }) => {
      const saved = await snapshot(queryClient);
      const now = new Date().toISOString();
      const nobody = { id: "", display_name: "" };
      const draft: TaskOut = {
        id: `draft-${now}`,
        title: body.title.trim(),
        done: false,
        done_at: null,
        due_on: body.due_on ?? null,
        data_class: "household",
        version: 0,
        created_by: nobody,
        updated_by: nobody,
        created_at: now,
        updated_at: now,
      };
      edit(queryClient, (page, query) =>
        fits(query, draft) ? { ...page, items: [draft, ...page.items], total: page.total + 1 } : page,
      );
      return saved;
    },
    onError: (_error, _variables, saved) => {
      restore(queryClient, saved);
      failed();
    },
    onSettled: invalidate,
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  const failed = useSaveFailed();
  const mutation = useMutation({
    ...tasksUpdateMutation(),
    onMutate: async ({ path, body }) => {
      const saved = await snapshot(queryClient);
      // Change rows in place: a ticked task stays visible (checked, struck through) until the refetch
      // after the save moves it to the other list.
      edit(queryClient, (page) => ({
        ...page,
        items: page.items.map((task) => (task.id === path.task_id ? ({ ...task, ...body } as TaskOut) : task)),
      }));
      return saved;
    },
    onError: (_error, _variables, saved) => {
      restore(queryClient, saved);
      failed();
    },
    onSettled: invalidate,
  });
  return (taskId: string, body: TaskPatch, onSettled?: () => void) =>
    mutation.mutate({ path: { task_id: taskId }, body }, onSettled ? { onSettled } : undefined);
}

export function useDeleteTask() {
  const invalidate = useInvalidate();
  const failed = useSaveFailed();
  const mutation = useMutation({ ...tasksDeleteMutation(), onError: failed, onSettled: invalidate });
  return (taskId: string) => mutation.mutateAsync({ path: { task_id: taskId } });
}

/** Today's calendar date on this device, YYYY-MM-DD (due dates have no time zone). */
/** Today's date as YYYY-MM-DD in `timeZone` (the household's, M1S-E04-03), or in the browser's zone. */
export function todayIso(now = new Date(), timeZone?: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(now)
    .reduce<Record<string, string>>((acc, part) => ({ ...acc, [part.type]: part.value }), {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}
