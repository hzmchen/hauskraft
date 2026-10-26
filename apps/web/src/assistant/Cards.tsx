// SPDX-License-Identifier: AGPL-3.0-or-later
// Action and confirmation cards (M2S-E06-04): each names what happened with the tool's plugin text (summary_key and
// the record's label), so the person sees what the assistant really did, not what it says it did.
import type { ActionOut, ConfirmationOut } from "@hauskraft/sdk-ts";
import { Button } from "@hauskraft/ui";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

function plugin(tool: string): string {
  return tool.split(".", 1)[0] ?? tool;
}

export function useSummary() {
  const { t } = useTranslation();
  return (tool: string, key: string | null, label: string | undefined) =>
    key
      ? t(key, { label: label ?? "", defaultValue: t("assistant.used_tool", { tool }) })
      : t("assistant.used_tool", { tool });
}

export function ActionCard({ action, onUndo, busy }: { action: ActionOut; onUndo: () => void; busy: boolean }) {
  const { t } = useTranslation();
  const summary = useSummary()(action.tool, action.summary_key, action.record?.label);
  return (
    <article
      aria-label={summary}
      className="flex flex-wrap items-center gap-2 rounded-md border bg-card p-2 text-card-foreground"
    >
      <span className="flex-1">{summary}</span>
      {action.status === "undone" ? (
        <span className="text-sm text-muted-foreground">{t("assistant.undone")}</span>
      ) : null}
      {action.status === "denied" ? (
        <span className="text-sm text-muted-foreground">{t("assistant.denied")}</span>
      ) : null}
      {action.status === "failed" ? <span className="text-sm text-destructive">{t("assistant.failed")}</span> : null}
      {action.record && action.status === "done" ? (
        <Link to="/p/$pageId" params={{ pageId: plugin(action.tool) }} className="text-sm underline">
          {t("assistant.open")}
        </Link>
      ) : null}
      {action.undo_available ? (
        <Button size="sm" variant="outline" onClick={onUndo} disabled={busy}>
          {t("assistant.undo")}
        </Button>
      ) : null}
    </article>
  );
}

export function ConfirmationCard({
  confirmation,
  onAnswer,
  busy,
}: {
  confirmation: ConfirmationOut;
  onAnswer: (approve: boolean) => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const summary = useSummary()(confirmation.tool, confirmation.summary_key, confirmation.record?.label);
  const [ns, verb] = confirmation.tool.split(".");
  const approve = t(`${ns}:tool.${verb}.approve`, { defaultValue: t("assistant.confirm") });
  return (
    <article aria-label={summary} className="flex flex-col gap-2 rounded-md border border-destructive p-2">
      <span>{summary}</span>
      <div className="flex gap-2">
        <Button size="sm" variant="destructive" onClick={() => onAnswer(true)} disabled={busy}>
          {approve}
        </Button>
        <Button size="sm" variant="outline" onClick={() => onAnswer(false)} disabled={busy}>
          {t("assistant.cancel")}
        </Button>
      </div>
    </article>
  );
}
