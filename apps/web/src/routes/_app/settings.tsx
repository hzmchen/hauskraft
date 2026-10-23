// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings as an area (M1S-E08-01): the "Settings" navigation inside <main>, from the sections model, then the page.
import { Link, Outlet, createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { useSession } from "../../session";
import { visibleSections } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings")({
  component: SettingsLayout,
});

function SettingsLayout() {
  const { t } = useTranslation();
  const session = useSession();
  return (
    <div className="flex flex-col gap-density">
      <nav aria-label={t("nav.settings")}>
        <ul className="flex flex-wrap gap-2 border-b pb-2">
          {visibleSections(session.permissions).map((section) => (
            <li key={section.id}>
              <Link
                to={section.href}
                className="inline-flex h-control items-center rounded-md px-3 text-foreground hover:bg-muted"
                activeProps={{ className: "bg-muted font-bold", "aria-current": "page" }}
              >
                {t(section.labelKey)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </div>
  );
}
