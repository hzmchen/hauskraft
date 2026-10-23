// SPDX-License-Identifier: AGPL-3.0-or-later
// Set up your household (M1S-E03-02, ADR 0017): while no account exists, the household and its first owner are
// created here in one step. The owner is signed in afterwards and the app speaks the household's language.
import { setupComplete } from "@hauskraft/sdk-ts";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@hauskraft/ui";
import { createFileRoute, redirect, useRouter } from "@tanstack/react-router";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, SelectField, TextField } from "../forms/fields";
import { LANGUAGES, hasDeviceLanguage, isLanguage, type Language } from "../i18n";
import { rememberSession, sessionQuery } from "../session";
import { browserTimeZone, timeZoneOptions } from "../settings/timeZones";
import { markSetUp, setupRequired } from "../setup";

export const Route = createFileRoute("/setup")({
  beforeLoad: async ({ context }) => {
    if (await setupRequired(context.queryClient)) return;
    const session = await context.queryClient.ensureQueryData(sessionQuery);
    throw redirect({ to: session ? "/today" : "/login" });
  },
  component: Setup,
});

type FieldErrors = Partial<Record<"timezone" | "username" | "password" | "form", string>>;

function Setup() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const ids = { title: useId(), household: useId(), account: useId() };
  const zones = timeZoneOptions(browserTimeZone());
  const [values, setValues] = useState({
    name: "",
    locale: (isLanguage(i18n.resolvedLanguage) ? i18n.resolvedLanguage : "en") as Language,
    timezone: browserTimeZone(),
    displayName: "",
    username: "",
    password: "",
    repeat: "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const set = (key: keyof typeof values) => (event: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: event.target.value }));

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (values.password !== values.repeat) {
      setErrors({ password: t("password.mismatch") });
      return;
    }
    setPending(true);
    const { data, error } = await setupComplete({
      body: {
        household: { name: values.name, timezone: values.timezone, locale: values.locale },
        owner: { username: values.username, display_name: values.displayName, password: values.password },
      },
    });
    setPending(false);
    if (!data) {
      const code = problemCode(error);
      setErrors(
        code === "invalid_timezone"
          ? { timezone: t("household_page.invalid_timezone") }
          : code === "invalid_username"
            ? { username: t("members.invalid_username") }
            : code === "password_policy"
              ? { password: t("password.policy") }
              : code === "setup_done"
                ? { form: t("setup.done") }
                : { form: t("errors.generic") },
      );
      return;
    }
    const queryClient = router.options.context.queryClient;
    markSetUp(queryClient);
    rememberSession(queryClient, data);
    if (!hasDeviceLanguage() && isLanguage(data.user.locale)) await i18n.changeLanguage(data.user.locale);
    await router.navigate({ to: "/today" });
  }

  return (
    <main id="content" className="grid min-h-svh place-items-center p-density">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>
            <h1 id={ids.title} className="text-xl font-bold">
              {t("setup.title")}
            </h1>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-muted-foreground">{t("setup.intro")}</p>
          <form aria-labelledby={ids.title} onSubmit={create} className="flex flex-col gap-4">
            <section aria-labelledby={ids.household} className="flex flex-col gap-3">
              <h2 id={ids.household} className="text-lg font-bold">
                {t("setup.household_heading")}
              </h2>
              <TextField
                label={t("household_page.name")}
                value={values.name}
                onChange={set("name")}
                required
                maxLength={80}
              />
              <SelectField
                label={t("account.language")}
                value={values.locale}
                onChange={(locale) => isLanguage(locale) && setValues((v) => ({ ...v, locale }))}
                options={LANGUAGES.map((lng) => ({ value: lng, label: t(`language.${lng}`) }))}
              />
              <SelectField
                label={t("household_page.timezone")}
                value={values.timezone}
                onChange={(timezone) => setValues((v) => ({ ...v, timezone }))}
                options={zones}
                error={errors.timezone}
              />
            </section>
            <section aria-labelledby={ids.account} className="flex flex-col gap-3">
              <h2 id={ids.account} className="text-lg font-bold">
                {t("setup.account_heading")}
              </h2>
              <TextField
                label={t("setup.your_name")}
                value={values.displayName}
                onChange={set("displayName")}
                autoComplete="name"
                required
                maxLength={80}
              />
              <TextField
                label={t("account_page.username")}
                value={values.username}
                onChange={set("username")}
                autoComplete="username"
                error={errors.username}
                required
              />
              <TextField
                label={t("setup.password")}
                hint={t("password.hint")}
                type="password"
                autoComplete="new-password"
                value={values.password}
                onChange={set("password")}
                error={errors.password}
                required
              />
              <TextField
                label={t("setup.repeat")}
                type="password"
                autoComplete="new-password"
                value={values.repeat}
                onChange={set("repeat")}
                required
              />
            </section>
            {errors.form ? (
              <p role="alert" className="text-destructive">
                {errors.form}
              </p>
            ) : null}
            <Button type="submit" disabled={pending}>
              {t("setup.create")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
