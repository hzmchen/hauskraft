// SPDX-License-Identifier: MIT
// The title as a button ("Edit '<title>'"); clicking it edits inline. Enter saves, Escape cancels.
import { Input, cn } from "@hearthos/ui";
import { useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

export function TaskTitle({
  title,
  done,
  onRename,
}: {
  title: string;
  done: boolean;
  onRename: (title: string) => void;
}) {
  const { t } = useTranslation("tasks");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);

  if (!editing) {
    return (
      <button
        type="button"
        aria-label={t("a11y.edit", { title })}
        onClick={() => {
          setDraft(title);
          setEditing(true);
        }}
        className={cn("min-w-0 flex-1 truncate text-left", done && "text-muted-foreground line-through")}
      >
        {title}
      </button>
    );
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setEditing(false);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const next = draft.trim();
      if (next && next !== title) onRename(next);
      setEditing(false);
    }
  }

  return (
    <Input
      aria-label={t("a11y.title_input")}
      value={draft}
      maxLength={200}
      // Editing starts from the user's click, so moving focus into the field is expected.
      ref={(input) => input?.focus()}
      onChange={(event) => setDraft(event.target.value)}
      onKeyDown={onKeyDown}
      onBlur={() => setEditing(false)}
      className="h-8 flex-1"
    />
  );
}
