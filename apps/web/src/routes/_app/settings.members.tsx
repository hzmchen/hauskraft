// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { mayOpen } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings/members")({
  // Owners only (M1S-E08-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("members", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  component: MembersSettings,
});

function MembersSettings() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-bold">{t("settings.members")}</h1>;
}
