// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export const Route = createFileRoute("/_app/today")({ component: Today });

// The dashboard grid arrives with M0S-E08-06.
function Today() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-bold">{t("nav.today")}</h1>;
}
