// SPDX-License-Identifier: AGPL-3.0-or-later
// Every page behind sign-in lives under this layout (M0S-E08-03). The navigation joins in M0S-E08-05.
import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { sessionQuery } from "../session";
import { AccountMenu } from "../shell/AccountMenu";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ context, location }) => {
    const session = await context.queryClient.ensureQueryData(sessionQuery);
    if (!session) throw redirect({ to: "/login", search: { redirect: location.href } });
    return { session };
  },
  component: AppLayout,
});

function AppLayout() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-svh flex-col">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:p-2"
      >
        {t("nav.skip_to_content")}
      </a>
      <header className="flex items-center justify-between gap-density border-b bg-nav px-density py-2 text-nav-foreground">
        <span className="font-heading text-lg font-bold">{t("app.name")}</span>
        <AccountMenu />
      </header>
      <main id="content" tabIndex={-1} className="flex-1 p-density outline-none">
        <Outlet />
      </main>
    </div>
  );
}
