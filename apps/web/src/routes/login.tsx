// SPDX-License-Identifier: AGPL-3.0-or-later
// Sign-in (M0S-E08-03). One message for every credential failure, so it never reveals which field was wrong.
import { authLogin } from "@hearthos/sdk-ts";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@hearthos/ui";
import { createFileRoute, redirect, useRouter } from "@tanstack/react-router";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { LOCALE_STORAGE_KEY, isLanguage } from "../i18n";
import { rememberSession, safeRedirect, sessionQuery } from "../session";

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): { redirect?: string } =>
    typeof search.redirect === "string" ? { redirect: search.redirect } : {},
  beforeLoad: async ({ context, search }) => {
    if (await context.queryClient.ensureQueryData(sessionQuery)) {
      throw redirect({ href: safeRedirect(search.redirect) });
    }
  },
  component: Login,
});

function hasDeviceLanguage(): boolean {
  try {
    return localStorage.getItem(LOCALE_STORAGE_KEY) !== null;
  } catch {
    return false;
  }
}

function Login() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { redirect: target } = Route.useSearch();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const ids = { title: useId(), username: useId(), password: useId() };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    const { data, response } = await authLogin({
      body: { username: String(form.get("username") ?? ""), password: String(form.get("password") ?? "") },
    });
    setPending(false);
    if (!data) {
      const status = response?.status;
      setError(
        t(status === 401 ? "login.error_credentials" : status === 429 ? "login.error_rate_limited" : "errors.generic"),
      );
      return;
    }
    rememberSession(router.options.context.queryClient, data);
    if (!hasDeviceLanguage() && isLanguage(data.user.locale)) await i18n.changeLanguage(data.user.locale);
    await router.navigate({ href: safeRedirect(target) });
  }

  return (
    <main id="content" className="grid min-h-svh place-items-center p-density">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>
            <h1 id={ids.title} className="text-xl font-bold">
              {t("login.title")}
            </h1>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form aria-labelledby={ids.title} onSubmit={submit} className="flex flex-col gap-3">
            <label htmlFor={ids.username} className="font-medium">
              {t("login.username")}
            </label>
            <Input id={ids.username} name="username" autoComplete="username" required />
            <label htmlFor={ids.password} className="font-medium">
              {t("login.password")}
            </label>
            <Input id={ids.password} name="password" type="password" autoComplete="current-password" required />
            {error ? (
              <p role="alert" className="text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" disabled={pending}>
              {t("login.submit")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
