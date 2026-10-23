// SPDX-License-Identifier: AGPL-3.0-or-later
import { pluginsListOptions } from "@hauskraft/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { loadPluginModule } from "../../plugins/load";
import { PluginPage } from "../../plugins/PluginPage";
import { pluginRegistry } from "../../plugins/registry.gen";
import { useWebPlugins } from "../../plugins/usePlugins";
import { pluginPages } from "../../shell/nav/model";
import { stringSearch } from "../../shell/RouterHost";

// Plugin pages keep their own state in the URL; the shell passes string values through and the page
// validates what it reads (useHost().search).
export const Route = createFileRoute("/_app/p/$pageId")({
  validateSearch: (search: Record<string, unknown>) => stringSearch(search),
  // Load the owning plugin's module and its default data first, so the page renders complete. Prefetching
  // only: a failure must not replace the page; its own queries load and report it.
  // Prefetch on every visit (others change the data too), but search changes (filters, sort) must not wait for it.
  shouldReload: ({ cause }) => cause === "enter",
  loader: async ({ context, params }) => {
    try {
      const plugins = await context.queryClient.ensureQueryData(pluginsListOptions());
      const owner = plugins.find(
        (plugin) => pluginRegistry[plugin.id] && pluginPages(plugin).some((page) => page.id === params.pageId),
      );
      if (!owner) return;
      const module = await loadPluginModule(owner.id, pluginRegistry[owner.id]!, context.i18n);
      await module.prefetch?.(context.queryClient);
    } catch {
      // see above
    }
  },
  component: PluginPageRoute,
});

function PluginPageRoute() {
  const { pageId } = Route.useParams();
  const { plugins } = useWebPlugins();
  return <PluginPage pageId={pageId} plugins={plugins} />;
}
