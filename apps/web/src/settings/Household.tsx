// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings → Household (M1S-E04-02, owners): the household name, its time zone (which decides "today") and the
// default language for new members.
import { householdUpdate, type HouseholdOut } from "@hauskraft/sdk-ts";
import { Button } from "@hauskraft/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, SelectField, TextField } from "../forms/fields";
import { householdQuery } from "../household";
import { LANGUAGES } from "../i18n";
import { timeZoneOptions } from "./timeZones";

export function HouseholdSettings() {
  const { t } = useTranslation();
  const { data } = useQuery(householdQuery());
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("settings.household")}</h1>
      {data ? <HouseholdForm household={data} /> : null}
    </div>
  );
}

function HouseholdForm({ household }: { household: HouseholdOut }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [values, setValues] = useState(household);
  const [errors, setErrors] = useState<{ name?: string; timezone?: string; form?: string }>({});
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    const { data, error } = await householdUpdate({ body: values });
    if (error || !data) {
      const code = problemCode(error);
      setErrors(
        code === "invalid_timezone"
          ? { timezone: t("household_page.invalid_timezone") }
          : code === "validation_failed"
            ? { name: t("household_page.invalid_name") }
            : { form: t("errors.generic") },
      );
      setState("idle");
      return;
    }
    setErrors({});
    queryClient.setQueryData(householdQuery().queryKey, data);
    setState("saved");
  }

  return (
    <form onSubmit={save} className="flex max-w-md flex-col gap-3">
      <TextField
        label={t("household_page.name")}
        value={values.name}
        onChange={(event) => setValues((v) => ({ ...v, name: event.target.value }))}
        error={errors.name}
        required
        maxLength={80}
      />
      <SelectField
        label={t("household_page.timezone")}
        value={values.timezone}
        onChange={(timezone) => setValues((v) => ({ ...v, timezone }))}
        options={timeZoneOptions(household.timezone)}
        error={errors.timezone}
      />
      <SelectField
        label={t("household_page.locale")}
        hint={t("household_page.locale_hint")}
        value={values.locale}
        onChange={(locale) => setValues((v) => ({ ...v, locale: locale === "de" ? "de" : "en" }))}
        options={LANGUAGES.map((lng) => ({ value: lng, label: t(`language.${lng}`) }))}
      />
      {errors.form ? (
        <p role="alert" className="text-destructive">
          {errors.form}
        </p>
      ) : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={state === "saving"}>
          {t("household_page.save")}
        </Button>
        <p role="status">{state === "saved" ? t("household_page.saved") : ""}</p>
      </div>
    </form>
  );
}
