// SPDX-License-Identifier: AGPL-3.0-or-later
// Activity (M0S-E10-03, web): who did what, newest first. Summaries are i18n keys from the API
// (summary_key) filled with the actor's name and the task title, theme name or account name (M1S-E09-02).
import { activityList, themesListOptions, type ActivityItem } from "@hauskraft/sdk-ts";
import { Button } from "@hauskraft/ui";
import { infiniteQueryOptions, useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import { isLanguage } from "../i18n";

const PAGE = 50;

interface EventData {
  task?: { title?: string };
  user?: { display_name?: string };
  to?: string;
  plugin_id?: string;
  enabled?: boolean;
}

/** The feed, newest first; the route prefetches the first page so the page renders with its data. */
export const activityQuery = infiniteQueryOptions({
  queryKey: ["activity"],
  queryFn: async ({ pageParam }) => {
    const { data } = await activityList({
      query: { limit: PAGE, ...(pageParam ? { before: pageParam } : {}) },
      throwOnError: true,
    });
    return data;
  },
  initialPageParam: undefined as string | undefined,
  getNextPageParam: (last) => (last.length > 0 ? last.at(-1)?.time : undefined),
  refetchInterval: 15_000,
});

export function summarise(item: ActivityItem, t: TFunction, themeName: (id: string) => string): string {
  const data = (item.data ?? {}) as EventData;
  const actor = item.actor?.display_name ?? t("activity.system");
  return t(item.summary_key, {
    actor,
    title: data.task?.title ?? "",
    theme: data.to ? themeName(data.to) : "",
    plugin: data.plugin_id ?? "",
    name: data.user?.display_name ?? "",
    ...(item.type === "hauskraft.plugin.toggled" ? { context: data.enabled ? "on" : "off" } : {}),
    defaultValue: t("activity.unknown", { actor, type: item.type }),
  });
}

export function ActivityFeed() {
  const { t, i18n } = useTranslation();
  const language = isLanguage(i18n.resolvedLanguage) ? i18n.resolvedLanguage : "en";
  const { data: themes = [] } = useQuery(themesListOptions());
  const feed = useInfiniteQuery(activityQuery);
  const themeName = (id: string) => themes.find((theme) => theme.theme_id === id)?.name ?? id;
  const when = new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const items = feed.data?.pages.flat() ?? [];
  const exhausted = feed.data?.pages.at(-1)?.length === 0;

  return (
    <div className="flex flex-col gap-density">
      <h1 className="text-2xl font-bold">{t("nav.activity")}</h1>
      {feed.data && items.length === 0 ? <p className="text-muted-foreground">{t("activity.empty")}</p> : null}
      <ul aria-label={t("nav.activity")} className="flex flex-col divide-y">
        {items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
            <span>{summarise(item, t, themeName)}</span>
            {/* Plain text, not <time>: each entry stays one line in the accessibility tree. */}
            <span className="text-sm text-muted-foreground">{when.format(new Date(item.time))}</span>
          </li>
        ))}
      </ul>
      {items.length > 0 && !exhausted ? (
        <Button
          variant="outline"
          className="self-start"
          disabled={feed.isFetchingNextPage}
          onClick={() => void feed.fetchNextPage()}
        >
          {t("activity.show_older")}
        </Button>
      ) : null}
    </div>
  );
}
