// SPDX-License-Identifier: MIT
// "Add from text" on All tasks (M2S-E06-05): paste a note, the add-from-text skill suggests tasks (it has no tools,
// so the note can't make it do anything), the person picks, and this dialog creates them with their own session.
import { assistantSkillsRun, tasksCreate } from "@hauskraft/sdk-ts";
import { Button, Checkbox, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "@hauskraft/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { invalidateTaskLists } from "../api";
import { ADD_FROM_TEXT, useAssistantAvailable, type Suggestion } from "../assistant";

export function AddFromText() {
  const { t } = useTranslation("tasks");
  const available = useAssistantAvailable();
  const queryClient = useQueryClient();
  const textId = useId();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [suggestions, setSuggestions] = useState<(Suggestion & { checked: boolean })[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!available) return null;

  function reset(next: boolean) {
    setOpen(next);
    if (!next) {
      setText("");
      setSuggestions(null);
      setError(null);
    }
  }

  async function suggest() {
    setBusy(true);
    setError(null);
    const { data } = await assistantSkillsRun({ path: { skill_id: ADD_FROM_TEXT }, body: { input: { text } } });
    const tasks = (data?.run.status === "done" ? (data.output as { tasks?: Suggestion[] })?.tasks : undefined) ?? null;
    if (tasks === null) setError(t("from_text.failed"));
    setSuggestions(tasks?.map((s) => ({ ...s, checked: true })) ?? null);
    setBusy(false);
  }

  const chosen = suggestions?.filter((s) => s.checked) ?? [];

  async function add() {
    setBusy(true);
    for (const s of chosen) {
      await tasksCreate({ body: s.due_on ? { title: s.title, due_on: s.due_on } : { title: s.title } });
    }
    await invalidateTaskLists(queryClient);
    setBusy(false);
    reset(false);
  }

  return (
    <>
      <Button variant="outline" onClick={() => reset(true)}>
        {t("from_text.button")}
      </Button>
      <Dialog open={open} onOpenChange={reset}>
        <DialogContent>
          <DialogTitle>{t("from_text.title")}</DialogTitle>
          <DialogDescription>{t("from_text.description")}</DialogDescription>
          <label htmlFor={textId} className="font-medium">
            {t("from_text.text")}
          </label>
          <textarea
            id={textId}
            value={text}
            rows={6}
            maxLength={20000}
            onChange={(event) => setText(event.target.value)}
            className="rounded-md border border-input bg-background p-2 text-foreground"
          />
          <Button variant="outline" onClick={() => void suggest()} disabled={busy || !text.trim()}>
            {t("from_text.suggest")}
          </Button>
          {error ? (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          ) : null}
          {suggestions ? (
            suggestions.length ? (
              <ul aria-label={t("from_text.suggested")} className="flex flex-col gap-1">
                {suggestions.map((s, i) => (
                  <li key={`${i}-${s.title}`} className="flex items-center gap-2">
                    <Checkbox
                      id={`${textId}-${i}`}
                      aria-label={s.title}
                      checked={s.checked}
                      onCheckedChange={(checked) =>
                        setSuggestions((list) =>
                          (list ?? []).map((x, j) => (j === i ? { ...x, checked: checked === true } : x)),
                        )
                      }
                    />
                    <label htmlFor={`${textId}-${i}`}>
                      {s.title}
                      {s.due_on ? ` · ${s.due_on}` : ""}
                    </label>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{t("from_text.nothing")}</p>
            )
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => reset(false)}>
              {t("from_text.cancel")}
            </Button>
            <Button onClick={() => void add()} disabled={busy || chosen.length === 0}>
              {t("from_text.add", { count: chosen.length })}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
