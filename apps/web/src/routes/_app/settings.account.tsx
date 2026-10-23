// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export const Route = createFileRoute("/_app/settings/account")({
  component: AccountSettings,
});

function AccountSettings() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-bold">{t("settings.account")}</h1>;
}
