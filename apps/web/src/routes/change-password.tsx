// SPDX-License-Identifier: AGPL-3.0-or-later
// Choose a new password (M1S-E07-02): an account with a temporary password lands here after sign-in, and every app
// route sends it back here, until it has chosen its own. Outside the shell: no navigation to wander off to.
import { usersMePassword } from "@hauskraft/sdk-ts";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@hauskraft/ui";
import { createFileRoute, redirect, useRouter } from "@tanstack/react-router";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, TextField } from "../forms/fields";
import { safeRedirect, sessionQuery } from "../session";

export const Route = createFileRoute("/change-password")({
  validateSearch: (search: Record<string, unknown>): { redirect?: string } =>
    typeof search.redirect === "string" ? { redirect: search.redirect } : {},
  beforeLoad: async ({ context, search }) => {
    const session = await context.queryClient.ensureQueryData(sessionQuery);
    if (!session) throw redirect({ to: "/login" });
    if (!session.user.must_change_password) throw redirect({ href: safeRedirect(search.redirect) });
  },
  component: ChangePassword,
});

function ChangePassword() {
  const { t } = useTranslation();
  const router = useRouter();
  const { redirect: target } = Route.useSearch();
  const title = useId();
  const [values, setValues] = useState({ current: "", next: "", repeat: "" });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const set = (key: keyof typeof values) => (event: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: event.target.value }));

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (values.next !== values.repeat) {
      setError(t("password.mismatch"));
      return;
    }
    setPending(true);
    const { error: problem } = await usersMePassword({
      body: { current_password: values.current, new_password: values.next },
    });
    setPending(false);
    if (problem) {
      const code = problemCode(problem);
      setError(
        t(
          code === "wrong_password"
            ? "password.wrong_current"
            : code === "password_policy"
              ? "password.policy"
              : code === "rate_limited"
                ? "login.error_rate_limited"
                : "errors.generic",
        ),
      );
      return;
    }
    const queryClient = router.options.context.queryClient;
    queryClient.setQueryData(sessionQuery.queryKey, (session) =>
      session ? { ...session, user: { ...session.user, must_change_password: false } } : session,
    );
    await router.navigate({ href: safeRedirect(target) });
  }

  return (
    <main id="content" className="grid min-h-svh place-items-center p-density">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>
            <h1 id={title} className="text-xl font-bold">
              {t("change_password.title")}
            </h1>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p>{t("change_password.explain")}</p>
          <form aria-labelledby={title} onSubmit={save} className="flex flex-col gap-3">
            <TextField
              label={t("password.current")}
              type="password"
              autoComplete="current-password"
              value={values.current}
              onChange={set("current")}
              required
            />
            <TextField
              label={t("password.new")}
              hint={t("password.hint")}
              type="password"
              autoComplete="new-password"
              value={values.next}
              onChange={set("next")}
              required
            />
            <TextField
              label={t("password.repeat")}
              type="password"
              autoComplete="new-password"
              value={values.repeat}
              onChange={set("repeat")}
              required
            />
            {error ? (
              <p role="alert" className="text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" disabled={pending}>
              {t("change_password.save")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
