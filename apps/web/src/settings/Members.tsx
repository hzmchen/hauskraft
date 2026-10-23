// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings → Members (M1S-E06-05, owners): everyone in the household with role and status, and the everyday
// admin in dialogs: add with a temporary password, edit name and role, reset a password, deactivate (after
// confirming) and reactivate. The API keeps at least one active owner; the page says so when it refuses.
import {
  usersUsersCreate,
  usersUsersDeactivate,
  usersUsersListOptions,
  usersUsersListQueryKey,
  usersUsersReactivate,
  usersUsersResetPassword,
  usersUsersUpdate,
  type MemberOut,
} from "@hauskraft/sdk-ts";
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "@hauskraft/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, SelectField, TextField } from "../forms/fields";
import { sessionQuery, useSession } from "../session";

type Open =
  | { kind: "add" }
  | { kind: "edit"; member: MemberOut }
  | { kind: "reset"; member: MemberOut }
  | { kind: "deactivate"; member: MemberOut }
  | null;

const ROLES = ["owner", "adult"] as const;

/** The message for a failed members call, by problem code. */
function useProblemText() {
  const { t } = useTranslation();
  return (error: unknown) => {
    const code = problemCode(error);
    const known: Record<string, string> = {
      last_owner: "members.last_owner",
      username_taken: "members.username_taken",
      invalid_username: "members.invalid_username",
      password_policy: "password.policy",
    };
    return t(known[code ?? ""] ?? "errors.generic");
  };
}

export function MembersSettings() {
  const { t } = useTranslation();
  const session = useSession();
  const queryClient = useQueryClient();
  const problemText = useProblemText();
  const { data: members = [] } = useQuery(usersUsersListOptions());
  const [open, setOpen] = useState<Open>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  async function refresh(member?: MemberOut) {
    await queryClient.invalidateQueries({ queryKey: usersUsersListQueryKey() });
    // My own role changes what I may do: the session's permissions follow.
    if (member?.id === session.user.id) await queryClient.invalidateQueries({ queryKey: sessionQuery.queryKey });
  }

  async function deactivate(member: MemberOut) {
    setOpen(null);
    const { error } = await usersUsersDeactivate({ path: { user_id: member.id } });
    if (error) {
      setPageError(problemText(error));
      return;
    }
    setPageError(null);
    await refresh(member);
  }

  async function reactivate(member: MemberOut) {
    const { error } = await usersUsersReactivate({ path: { user_id: member.id } });
    setPageError(error ? problemText(error) : null);
    await refresh(member);
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("settings.members")}</h1>
      <div className="flex flex-col gap-2">
        <Button className="self-start" onClick={() => setOpen({ kind: "add" })}>
          {t("members.add")}
        </Button>
        {pageError ? (
          <p role="alert" className="text-destructive">
            {pageError}
          </p>
        ) : null}
      </div>
      <ul aria-label={t("settings.members")} className="flex flex-col divide-y rounded-md border">
        {members.map((member) => (
          <li key={member.id} className="flex flex-wrap items-center justify-between gap-2 p-density">
            <span className="flex flex-col">
              <span className="font-medium">{member.display_name}</span>
              <span className="text-sm text-muted-foreground">
                {member.username} · {t(`roles.${member.role}`, { defaultValue: member.role })}
                {member.is_active ? "" : ` · ${t("members.deactivated")}`}
              </span>
            </span>
            <span className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                aria-label={t("members.edit_named", { name: member.display_name })}
                onClick={() => setOpen({ kind: "edit", member })}
              >
                {t("members.edit")}
              </Button>
              {member.id !== session.user.id ? (
                <Button
                  variant="outline"
                  size="sm"
                  aria-label={t("members.reset_named", { name: member.display_name })}
                  onClick={() => setOpen({ kind: "reset", member })}
                >
                  {t("members.reset")}
                </Button>
              ) : null}
              {member.is_active ? (
                <Button
                  variant="outline"
                  size="sm"
                  aria-label={t("members.deactivate_named", { name: member.display_name })}
                  onClick={() => setOpen({ kind: "deactivate", member })}
                >
                  {t("members.deactivate")}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  aria-label={t("members.reactivate_named", { name: member.display_name })}
                  onClick={() => void reactivate(member)}
                >
                  {t("members.reactivate")}
                </Button>
              )}
            </span>
          </li>
        ))}
      </ul>
      {open?.kind === "add" ? <AddMember onClose={() => setOpen(null)} onDone={() => refresh()} /> : null}
      {open?.kind === "edit" ? (
        <EditMember member={open.member} onClose={() => setOpen(null)} onDone={() => refresh(open.member)} />
      ) : null}
      {open?.kind === "reset" ? <ResetPassword member={open.member} onClose={() => setOpen(null)} /> : null}
      <Dialog open={open?.kind === "deactivate"} onOpenChange={(isOpen) => !isOpen && setOpen(null)}>
        {open?.kind === "deactivate" ? (
          <DialogContent role="alertdialog" showCloseButton={false}>
            <DialogTitle>{t("members.deactivate_title", { name: open.member.display_name })}</DialogTitle>
            <DialogDescription>{t("members.deactivate_body")}</DialogDescription>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(null)}>
                {t("settings.cancel")}
              </Button>
              <Button variant="destructive" onClick={() => void deactivate(open.member)}>
                {t("members.deactivate")}
              </Button>
            </DialogFooter>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  );
}

function FormDialog({
  title,
  submit,
  error,
  pending,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submit: string;
  error: string | null;
  pending: boolean;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <Dialog open onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent showCloseButton={false}>
        <DialogTitle>{title}</DialogTitle>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          {children}
          {error ? (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              {t("settings.cancel")}
            </Button>
            <Button type="submit" disabled={pending}>
              {submit}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RoleField({ value, onChange }: { value: string; onChange: (role: "owner" | "adult") => void }) {
  const { t } = useTranslation();
  return (
    <SelectField
      label={t("members.role")}
      value={value}
      onChange={(role) => onChange(role === "owner" ? "owner" : "adult")}
      options={ROLES.map((role) => ({ value: role, label: t(`roles.${role}`) }))}
    />
  );
}

function AddMember({ onClose, onDone }: { onClose: () => void; onDone: () => Promise<void> }) {
  const { t } = useTranslation();
  const problemText = useProblemText();
  const [values, setValues] = useState({
    display_name: "",
    username: "",
    role: "adult" as "owner" | "adult",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const { error: problem } = await usersUsersCreate({ body: values });
    setPending(false);
    if (problem) {
      setError(problemText(problem));
      return;
    }
    await onDone();
    onClose();
  }

  return (
    <FormDialog
      title={t("members.add")}
      submit={t("members.add")}
      error={error}
      pending={pending}
      onClose={onClose}
      onSubmit={add}
    >
      <TextField
        label={t("account_page.display_name")}
        value={values.display_name}
        onChange={(event) => setValues((v) => ({ ...v, display_name: event.target.value }))}
        required
        maxLength={80}
      />
      <TextField
        label={t("account_page.username")}
        value={values.username}
        onChange={(event) => setValues((v) => ({ ...v, username: event.target.value }))}
        autoComplete="off"
        required
      />
      <RoleField value={values.role} onChange={(role) => setValues((v) => ({ ...v, role }))} />
      <TextField
        label={t("members.temporary_password")}
        hint={t("password.hint")}
        type="password"
        autoComplete="new-password"
        value={values.password}
        onChange={(event) => setValues((v) => ({ ...v, password: event.target.value }))}
        required
      />
    </FormDialog>
  );
}

function EditMember({
  member,
  onClose,
  onDone,
}: {
  member: MemberOut;
  onClose: () => void;
  onDone: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const problemText = useProblemText();
  const [values, setValues] = useState({
    display_name: member.display_name,
    role: (member.role === "owner" ? "owner" : "adult") as "owner" | "adult",
  });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const { error: problem } = await usersUsersUpdate({ path: { user_id: member.id }, body: values });
    setPending(false);
    if (problem) {
      setError(problemText(problem));
      return;
    }
    await onDone();
    onClose();
  }

  return (
    <FormDialog
      title={t("members.edit_title")}
      submit={t("members.save")}
      error={error}
      pending={pending}
      onClose={onClose}
      onSubmit={save}
    >
      <TextField
        label={t("account_page.display_name")}
        value={values.display_name}
        onChange={(event) => setValues((v) => ({ ...v, display_name: event.target.value }))}
        required
        maxLength={80}
      />
      <RoleField value={values.role} onChange={(role) => setValues((v) => ({ ...v, role }))} />
    </FormDialog>
  );
}

function ResetPassword({ member, onClose }: { member: MemberOut; onClose: () => void }) {
  const { t } = useTranslation();
  const problemText = useProblemText();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function reset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const { error: problem } = await usersUsersResetPassword({ path: { user_id: member.id }, body: { password } });
    setPending(false);
    if (problem) {
      setError(problemText(problem));
      return;
    }
    onClose();
  }

  return (
    <FormDialog
      title={t("members.reset_title")}
      submit={t("members.reset")}
      error={error}
      pending={pending}
      onClose={onClose}
      onSubmit={reset}
    >
      <TextField
        label={t("members.temporary_password")}
        hint={t("password.hint")}
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />
    </FormDialog>
  );
}
