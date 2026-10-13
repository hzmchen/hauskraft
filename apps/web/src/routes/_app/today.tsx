// SPDX-License-Identifier: AGPL-3.0-or-later
import { dashboardGetOptions } from "@hearthos/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { TodayDashboard } from "../../dashboard/Today";
import { loadPluginModule } from "../../plugins/load";
import { pluginRegistry } from "../../plugins/registry.gen";

export const Route = createFileRoute("/_app/today")({
  // Render with the layout and the widgets' data, not an empty grid that fills in later. Prefetching only:
  // a failure must not replace the page; the components' own queries load and report it.
  // Prefetch on entering the page only; search changes (filters, sort) must not wait for it.
  shouldReload: false,
  loader: async ({ context }) => {
    try {
      const { layout } = await context.queryClient.ensureQueryData(
        dashboardGetOptions({ path: { dashboard_id: "today" } }),
      );
      const plugins = [...new Set(layout.map((cell) => cell.plugin_id))].filter((id) => pluginRegistry[id]);
      await Promise.all(
        plugins.map(async (id) => {
          const module = await loadPluginModule(id, pluginRegistry[id]!, context.i18n);
          await module.prefetch?.(context.queryClient);
        }),
      );
    } catch {
      // see above
    }
  },
  component: TodayDashboard,
});
