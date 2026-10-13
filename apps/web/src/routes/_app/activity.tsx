// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export const Route = createFileRoute("/_app/activity")({ component: Activity });

// The activity feed arrives with the web part of M0S-E10-03.
function Activity() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-bold">{t("nav.activity")}</h1>;
}
