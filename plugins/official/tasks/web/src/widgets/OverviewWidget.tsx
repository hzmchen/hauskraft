// SPDX-License-Identifier: MIT
// The "Weekly overview" widget (M2S-E06-06): the person's latest overview from the weekly-overview skill and
// "Create now". Schedules can fill it later without changing the widget.
import { assistantSkillsRun, type WidgetProps } from "@hauskraft/sdk-ts";
import { Button } from "@hauskraft/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { WEEKLY_OVERVIEW, latestOverviewOptions, useAssistantAvailable } from "../assistant";

function ago(iso: string, language: string): string {
  const minutes = Math.round((Date.parse(iso) - Date.now()) / 60_000);
  const format = new Intl.RelativeTimeFormat(language, { numeric: "auto" });
  if (Math.abs(minutes) < 60) return format.format(minutes, "minute");
  if (Math.abs(minutes) < 60 * 24) return format.format(Math.round(minutes / 60), "hour");
  return format.format(Math.round(minutes / 1440), "day");
}

export function OverviewWidget({ instanceId }: WidgetProps) {
  const { t, i18n } = useTranslation("tasks");
  const available = useAssistantAvailable();
  const queryClient = useQueryClient();
  const latest = useQuery({ ...latestOverviewOptions(), enabled: available });
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function create() {
    setBusy(true);
    setFailed(false);
    const { data } = await assistantSkillsRun({ path: { skill_id: WEEKLY_OVERVIEW }, body: { input: {} } });
    if (data?.run.status === "done") queryClient.setQueryData(latestOverviewOptions().queryKey, data);
    else setFailed(true);
    setBusy(false);
  }

  if (!available)
    return (
      <p data-widget-instance={instanceId} className="text-muted-foreground">
        {t("overview.unavailable")}
      </p>
    );
  const text = typeof latest.data?.output === "string" ? latest.data.output : null;
  return (
    <div data-widget-instance={instanceId} className="flex flex-col gap-2">
      {text ? (
        <>
          <p className="whitespace-pre-line">{text}</p>
          <p className="text-sm text-muted-foreground">
            {t("overview.created", { when: ago(latest.data!.created_at, i18n.language) })}
          </p>
        </>
      ) : (
        <p className="text-muted-foreground">{t("overview.empty")}</p>
      )}
      {failed ? (
        <p role="alert" className="text-destructive">
          {t("overview.failed")}
        </p>
      ) : null}
      <Button variant="outline" size="sm" className="self-start" onClick={() => void create()} disabled={busy}>
        {t("overview.create")}
      </Button>
    </div>
  );
}
