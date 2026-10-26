// SPDX-License-Identifier: AGPL-3.0-or-later
// The assistant side panel (M2S-E06-01..04): chats, the message log, the input, progress, errors and the action and
// confirmation cards. Beside the page on wide screens, covering it below 768 px. Part of the shell, so every theme
// renders the same functions.
import {
  assistantActionsUndo,
  assistantConversationsCreate,
  assistantConversationsDelete,
  assistantConversationsListOptions,
  assistantConversationsListQueryKey,
  assistantConversationsMessage,
  assistantConversationsReadOptions,
  assistantConversationsReadQueryKey,
  assistantRunsConfirm,
  type ActionOut,
  type ConfirmationOut,
  type ConversationDetail,
  type RunResult,
} from "@hauskraft/sdk-ts";
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle, Icon, cn } from "@hauskraft/ui";
import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode } from "../forms/fields";
import { useIsWide } from "../shell/nav/NavRenderer";
import { ActionCard, ConfirmationCard } from "./Cards";
import { Markdown } from "./Markdown";
import { useAssistantAvailable, useBottomEdge, usePanel } from "./state";

const CURRENT = "hauskraft.assistant.chat";

function rememberedChat(): string | null {
  try {
    return localStorage.getItem(CURRENT);
  } catch {
    return null;
  }
}

function remember(id: string | null) {
  try {
    if (id) localStorage.setItem(CURRENT, id);
    else localStorage.removeItem(CURRENT);
  } catch {
    // storage blocked
  }
}

/** After the assistant changed something, every list that might show it refetches (the Tasks widget, Activity). */
function refreshEverythingElse(queryClient: QueryClient) {
  void queryClient.invalidateQueries({
    predicate: (q) => !String((q.queryKey[0] as { _id?: string } | undefined)?._id ?? "").startsWith("assistant"),
  });
}

export function AssistantButton() {
  const { t } = useTranslation();
  const { open, setOpen, buttonRef } = usePanel();
  if (!useAssistantAvailable()) return null;
  return (
    <Button ref={buttonRef} variant="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
      {t("assistant.button")}
    </Button>
  );
}

export function AssistantPanel() {
  const { t } = useTranslation();
  const wide = useIsWide();
  const { open, setOpen, buttonRef, headerRef } = usePanel();
  const available = useAssistantAvailable();
  const headerBottom = useBottomEdge(headerRef);
  // The panel appears with its chat list loaded, never with an empty list first (an error still opens it).
  const chats = useQuery({ ...assistantConversationsListOptions(), enabled: available && open });
  if (!available || !open || !chats.isFetched) return null;
  function close() {
    setOpen(false);
    buttonRef.current?.focus();
  }
  return (
    <aside
      aria-label={t("assistant.panel")}
      className={cn(
        "flex flex-col gap-density bg-background p-density",
        wide ? "sticky top-0 h-svh w-96 shrink-0 border-l" : "fixed inset-x-0 bottom-0 z-40",
      )}
      style={wide ? undefined : { top: headerBottom }}
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-bold">{t("assistant.panel")}</h2>
        <Button variant="ghost" size="sm" onClick={close}>
          {t("assistant.close")}
        </Button>
      </div>
      <Chat />
    </aside>
  );
}

function Chat() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [current, setCurrent] = useState<string | null>(rememberedChat);
  const [text, setText] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<ConfirmationOut[]>([]);
  const [deleting, setDeleting] = useState<{ id: string; title: string } | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { data: chats = [] } = useQuery(assistantConversationsListOptions());
  const { data: detail, isError: detailError } = useQuery({
    ...assistantConversationsReadOptions({ path: { conversation_id: current ?? "" } }),
    enabled: current !== null,
    retry: false,
  });

  // A chat deleted elsewhere (another tab) can't be read any more: start a new one.
  useEffect(() => {
    if (current && detailError) select(null);
  }, [current, detailError]);

  function select(id: string | null) {
    setCurrent(id);
    remember(id);
    setPending([]);
    setError(null);
  }

  async function refresh(id: string) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: assistantConversationsListQueryKey() }),
      queryClient.invalidateQueries({
        queryKey: assistantConversationsReadQueryKey({ path: { conversation_id: id } }),
      }),
    ]);
  }

  function settle(result: RunResult | undefined, failure: unknown, id: string) {
    if (!result) {
      setError(
        t(`assistant.errors.${problemCode(failure) ?? "generic"}`, { defaultValue: t("assistant.errors.generic") }),
      );
      return;
    }
    setPending(result.confirmations);
    setError(
      result.run.status === "failed"
        ? t(`assistant.errors.${result.run.error_code ?? "generic"}`, { defaultValue: t("assistant.errors.generic") })
        : null,
    );
    if (result.actions.length) refreshEverythingElse(queryClient);
    void refresh(id);
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const message = text.trim();
    if (!message || working) return;
    setWorking(true);
    setError(null);
    try {
      let id = current;
      if (!id) {
        const { data } = await assistantConversationsCreate();
        if (!data) throw new Error("no chat");
        id = data.id;
        select(id);
      }
      setText("");
      const { data, error: failure } = await assistantConversationsMessage({
        path: { conversation_id: id },
        body: { text: message },
      });
      settle(data, failure, id);
    } finally {
      setWorking(false);
      inputRef.current?.focus();
    }
  }

  async function answer(confirmation: ConfirmationOut, approve: boolean) {
    if (!current) return;
    setWorking(true);
    try {
      const { data, error: failure } = await assistantRunsConfirm({
        path: { run_id: confirmation.run_id },
        body: { decisions: [{ id: confirmation.id, approve }] },
      });
      settle(data, failure, current);
    } finally {
      setWorking(false);
    }
  }

  async function undo(action: ActionOut) {
    setWorking(true);
    try {
      await assistantActionsUndo({ path: { action_id: action.id } });
      refreshEverythingElse(queryClient);
      if (current) await refresh(current);
    } finally {
      setWorking(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await assistantConversationsDelete({ path: { conversation_id: deleting.id } });
    if (deleting.id === current) select(null);
    setDeleting(null);
    await queryClient.invalidateQueries({ queryKey: assistantConversationsListQueryKey() });
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-density">
      <div className="flex flex-col gap-1">
        <Button variant="outline" size="sm" onClick={() => select(null)}>
          {t("assistant.new_chat")}
        </Button>
        <ul aria-label={t("assistant.chats")} className="flex max-h-40 flex-col gap-1 overflow-y-auto">
          {chats.map((chat) => {
            const title = chat.title ?? t("assistant.untitled");
            return (
              <li key={chat.id} className="flex items-center gap-1">
                <Button
                  variant={chat.id === current ? "secondary" : "ghost"}
                  size="sm"
                  className="flex-1 justify-start truncate"
                  aria-current={chat.id === current ? "true" : undefined}
                  onClick={() => select(chat.id)}
                >
                  {title}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t("assistant.delete_chat", { title })}
                  onClick={() => setDeleting({ id: chat.id, title })}
                >
                  <Icon name="action.delete" />
                </Button>
              </li>
            );
          })}
        </ul>
      </div>
      <Log detail={current ? detail : undefined} pending={pending} busy={working} onAnswer={answer} onUndo={undo} />
      {working ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("assistant.working")}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <form onSubmit={send} className="flex gap-2">
        <textarea
          ref={inputRef}
          aria-label={t("assistant.input")}
          value={text}
          rows={2}
          maxLength={4000}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={working}
          className="min-w-0 flex-1 resize-none rounded-md border bg-background p-2"
        />
        <Button type="submit" disabled={working || !text.trim()}>
          {t("assistant.send")}
        </Button>
      </form>
      <Dialog open={deleting !== null} onOpenChange={(isOpen) => !isOpen && setDeleting(null)}>
        {deleting ? (
          <DialogContent role="alertdialog" showCloseButton={false}>
            <DialogTitle>{t("assistant.delete_title")}</DialogTitle>
            <DialogDescription>{t("assistant.delete_body")}</DialogDescription>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleting(null)}>
                {t("assistant.cancel")}
              </Button>
              <Button variant="destructive" onClick={() => void confirmDelete()}>
                {t("assistant.delete")}
              </Button>
            </DialogFooter>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  );
}

function Log({
  detail,
  pending,
  busy,
  onAnswer,
  onUndo,
}: {
  detail: ConversationDetail | undefined;
  pending: ConfirmationOut[];
  busy: boolean;
  onAnswer: (c: ConfirmationOut, approve: boolean) => void;
  onUndo: (a: ActionOut) => void;
}) {
  const { t } = useTranslation();
  const messages = detail?.messages ?? [];
  const actions = detail?.actions ?? [];
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(
    // Braces matter: Chrome's scrollIntoView returns a promise, which React would take for a cleanup function.
    () => {
      endRef.current?.scrollIntoView?.({ block: "end" });
    },
    [messages.length, actions.length, pending.length],
  );
  // Cards follow the last message of their run, so a chat reads in order.
  const lastOfRun = new Map<string, number>();
  messages.forEach((m, i) => m.run_id && lastOfRun.set(m.run_id, i));
  return (
    <div
      role="log"
      aria-label={t("assistant.messages")}
      aria-live="polite"
      className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto"
    >
      {messages.length === 0 && pending.length === 0 ? (
        <p className="text-muted-foreground">{t("assistant.empty")}</p>
      ) : null}
      {messages.map((m, i) => (
        <div key={m.id} className="flex flex-col gap-2">
          <div className={cn("rounded-md p-2", m.role === "user" ? "self-end bg-secondary" : "bg-muted")}>
            {m.role === "user" ? <p className="whitespace-pre-line">{m.text}</p> : <Markdown text={m.text} />}
          </div>
          {m.run_id && lastOfRun.get(m.run_id) === i
            ? actions
                .filter((a) => a.run_id === m.run_id)
                .map((a) => <ActionCard key={a.id} action={a} busy={busy} onUndo={() => onUndo(a)} />)
            : null}
        </div>
      ))}
      {pending.map((c) => (
        <ConfirmationCard key={c.id} confirmation={c} busy={busy} onAnswer={(approve) => onAnswer(c, approve)} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
