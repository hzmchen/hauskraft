// SPDX-License-Identifier: AGPL-3.0-or-later
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export function NotFound() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-2xl font-bold">{t("errors.not_found")}</h1>
      <p>{t("errors.not_found_hint")}</p>
      <Link to="/today" className="text-primary underline">
        {t("errors.back_home")}
      </Link>
    </div>
  );
}
