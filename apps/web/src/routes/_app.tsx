// SPDX-License-Identifier: AGPL-3.0-or-later
// Every page behind sign-in (M0S-E08-03) inside the shell (M0S-E08-05): skip link, navigation from the
// NavModel, account menu and one main landmark.
import { pluginsListOptions } from "@hauskraft/sdk-ts";
import { cn } from "@hauskraft/ui";
import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { hasDeviceLanguage, isLanguage } from "../i18n";
import { loadPluginModule } from "../plugins/load";
import { pluginRegistry } from "../plugins/registry.gen";
import { useWebPlugins } from "../plugins/usePlugins";
import { sessionQuery } from "../session";
import { AccountMenu } from "../shell/AccountMenu";
import { DocumentTitle } from "../shell/DocumentTitle";
import { buildNavModel } from "../shell/nav/model";
import { NavRenderer, useNavStyle } from "../shell/nav/NavRenderer";
import { RouterHost } from "../shell/RouterHost";
import { useThemeLayout } from "../shell/ThemeRuntime";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ context, location }) => {
    const session = await context.queryClient.ensureQueryData(sessionQuery);
    if (!session) throw redirect({ to: "/login", search: { redirect: location.href } });
    // The account's language applies on every load, unless this device chose its own (account menu).
    const locale = session.user.locale;
    if (!hasDeviceLanguage() && isLanguage(locale) && context.i18n.resolvedLanguage !== locale) {
      await context.i18n.changeLanguage(locale);
      document.documentElement.lang = locale;
    }
    // A temporary password comes first (M1S-E07-02); afterwards the member continues to this page.
    if (session.user.must_change_password)
      throw redirect({ to: "/change-password", search: { redirect: location.href } });
    return { session };
  },
  // Load enabled plugins' web modules up front: the navigation needs their strings.
  loader: async ({ context }) => {
    try {
      const plugins = await context.queryClient.ensureQueryData(pluginsListOptions());
      await Promise.all(
        plugins
          .filter((p) => p.enabled && !p.load_error && pluginRegistry[p.id])
          .map((p) => loadPluginModule(p.id, pluginRegistry[p.id]!, context.i18n)),
      );
    } catch {
      // A plugin list or module that fails to load must not lock anyone out of the shell.
    }
  },
  component: AppLayout,
});

function AppLayout() {
  const { t } = useTranslation();
  const { plugins } = useWebPlugins();
  const items = useMemo(() => buildNavModel(plugins), [plugins]);
  const layout = useThemeLayout();
  const style = useNavStyle(layout.navigation);
  return (
    <div className="flex min-h-svh">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:p-2"
      >
        {t("nav.skip_to_content")}
      </a>
      {style === "sidebar" ? <NavRenderer style={style} items={items} /> : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-density border-b bg-nav px-density py-2 text-nav-foreground">
          <div className="flex min-w-0 items-center gap-density">
            {style === "drawer" ? <NavRenderer style={style} items={items} /> : null}
            <span className="font-heading text-lg font-bold">{t("app.name")}</span>
            {style === "topbar" ? <NavRenderer style={style} items={items} /> : null}
          </div>
          <AccountMenu />
        </header>
        <main
          id="content"
          tabIndex={-1}
          className={cn(
            "w-full flex-1 p-density outline-none",
            layout.content_width === "contained" && "mx-auto max-w-content",
            style === "bottom-tabs" && "pb-20",
          )}
        >
          <RouterHost>
            <Outlet />
          </RouterHost>
        </main>
        <DocumentTitle />
        {style === "bottom-tabs" ? <NavRenderer style={style} items={items} /> : null}
      </div>
    </div>
  );
}
