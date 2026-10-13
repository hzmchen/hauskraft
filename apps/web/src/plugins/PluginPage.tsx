// SPDX-License-Identifier: AGPL-3.0-or-later
// /p/$pageId (M0S-E08-05): the page component an enabled plugin contributes, or "Page not found".
import type { PluginOut } from "@hearthos/sdk-ts";
import { Suspense, use } from "react";
import { useTranslation } from "react-i18next";

import { pluginPages } from "../shell/nav/model";
import { NotFound } from "../shell/NotFound";
import { ensurePluginLocales, pluginModulePromise } from "./load";
import type { PluginLoaders } from "./PluginWidget";
import { pluginRegistry } from "./registry.gen";

export function PluginPage({
  pageId,
  plugins,
  loaders = pluginRegistry,
}: {
  pageId: string;
  plugins: PluginOut[];
  loaders?: PluginLoaders;
}) {
  const match = plugins
    .filter((plugin) => plugin.enabled && !plugin.load_error && loaders[plugin.id])
    .flatMap((plugin) => pluginPages(plugin).map((page) => ({ plugin, page })))
    .find(({ page }) => page.id === pageId);
  if (!match) return <NotFound />;
  return (
    <Suspense fallback={null}>
      <LoadedPage pluginId={match.plugin.id} component={match.page.component ?? match.page.id} loaders={loaders} />
    </Suspense>
  );
}

function LoadedPage({ pluginId, component, loaders }: { pluginId: string; component: string; loaders: PluginLoaders }) {
  const { i18n } = useTranslation();
  const module = use(pluginModulePromise(loaders[pluginId]!));
  ensurePluginLocales(i18n, pluginId, module);
  const Page = module.pages[component];
  return Page ? <Page pluginId={pluginId} /> : <NotFound />;
}
