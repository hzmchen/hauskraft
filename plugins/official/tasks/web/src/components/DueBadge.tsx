// SPDX-License-Identifier: MIT
// Due badge: always words ("Overdue", "Today", "Due 14 Oct"), colour only as a second signal.
import { Icon, cn } from "@hearthos/ui";
import { useTranslation } from "react-i18next";

import { todayIso } from "../api";

function formatDue(iso: string, language: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-US", { day: "numeric", month: "short" }).format(
    new Date(y!, m! - 1, d!),
  );
}

export function DueBadge({ due, done }: { due: string | null | undefined; done: boolean }) {
  const { t, i18n } = useTranslation("tasks");
  if (!due) return null;
  const today = todayIso();
  const kind = done || due > today ? "later" : due === today ? "today" : "overdue";
  const label =
    kind === "overdue"
      ? t("due.overdue")
      : kind === "today"
        ? t("due.today")
        : t("due.on", { date: formatDue(due, i18n.language) });
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-sm px-1.5 text-xs",
        kind === "overdue" && "bg-destructive text-destructive-foreground",
        kind === "today" && "bg-warning text-warning-foreground",
        kind === "later" && "bg-muted text-muted-foreground",
      )}
    >
      <Icon name={kind === "overdue" ? "status.overdue" : "status.due"} />
      {label}
    </span>
  );
}
