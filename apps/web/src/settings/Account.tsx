// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings → Account (M1S-E05-03): my profile (display name, language; the username is fixed) and my password.
import { usersMePassword, usersMeUpdate } from "@hauskraft/sdk-ts";
import { Button } from "@hauskraft/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, SelectField, TextField } from "../forms/fields";
import { LANGUAGES, isLanguage, setLanguage, type Language } from "../i18n";
import { sessionQuery, useSession } from "../session";

export function AccountSettings() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("settings.account")}</h1>
      <ProfileSection />
      <PasswordSection />
    </div>
  );
}

function ProfileSection() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const heading = useId();
  const [displayName, setDisplayName] = useState(user.display_name);
  const [locale, setLocale] = useState<Language>(isLanguage(user.locale) ? user.locale : "en");
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">("idle");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    const { error } = await usersMeUpdate({ body: { display_name: displayName, locale } });
    if (error) {
      setState("failed");
      return;
    }
    if (i18n.resolvedLanguage !== locale) await setLanguage(i18n, locale, async () => undefined);
    await queryClient.invalidateQueries({ queryKey: sessionQuery.queryKey });
    setState("saved");
  }

  return (
    <section aria-labelledby={heading} className="flex max-w-md flex-col gap-3">
      <h2 id={heading} className="text-lg font-bold">
        {t("account_page.profile")}
      </h2>
      <p>
        <span className="text-muted-foreground">{t("account_page.username")}: </span>
        <span className="font-medium">{user.username}</span>
      </p>
      <form onSubmit={save} className="flex flex-col gap-3">
        <TextField
          label={t("account_page.display_name")}
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          autoComplete="name"
          required
          maxLength={80}
        />
        <SelectField
          label={t("account.language")}
          value={locale}
          onChange={(value) => isLanguage(value) && setLocale(value)}
          options={LANGUAGES.map((lng) => ({ value: lng, label: t(`language.${lng}`) }))}
        />
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={state === "saving"}>
            {t("account_page.save_profile")}
          </Button>
          <p role="status">
            {state === "saved" ? t("account_page.profile_saved") : state === "failed" ? t("errors.generic") : ""}
          </p>
        </div>
      </form>
    </section>
  );
}

function PasswordSection() {
  const { t } = useTranslation();
  const heading = useId();
  const empty = { current: "", next: "", repeat: "" };
  const [values, setValues] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const [changed, setChanged] = useState(false);
  const [pending, setPending] = useState(false);
  const set = (key: keyof typeof empty) => (event: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: event.target.value }));

  async function change(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setChanged(false);
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
    setError(null);
    setValues(empty);
    setChanged(true);
  }

  return (
    <section aria-labelledby={heading} className="flex max-w-md flex-col gap-3">
      <h2 id={heading} className="text-lg font-bold">
        {t("password.heading")}
      </h2>
      <form onSubmit={change} className="flex flex-col gap-3">
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
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={pending}>
            {t("password.change")}
          </Button>
          <p role="status">{changed ? t("password.changed") : ""}</p>
        </div>
      </form>
    </section>
  );
}
