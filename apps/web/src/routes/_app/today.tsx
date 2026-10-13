// SPDX-License-Identifier: AGPL-3.0-or-later
import { dashboardGetOptions } from "@hearthos/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { TodayDashboard } from "../../dashboard/Today";

export const Route = createFileRoute("/_app/today")({
  // Render with the layout, not an empty grid that fills in later.
  // Prefetch only: a failure must not replace the page; the component's own query loads and reports it.
  loader: ({ context }) =>
    context.queryClient
      .ensureQueryData(dashboardGetOptions({ path: { dashboard_id: "today" } }))
      .catch(() => undefined),
  component: TodayDashboard,
});
