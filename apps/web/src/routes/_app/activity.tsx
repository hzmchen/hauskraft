// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { ActivityFeed, activityQuery } from "../../activity/Activity";

export const Route = createFileRoute("/_app/activity")({
  // Prefetch only: a failure must not replace the page; the component's own query loads and reports it.
  // Prefetch on entering the page only; search changes (filters, sort) must not wait for it.
  shouldReload: false,
  loader: ({ context }) => context.queryClient.ensureInfiniteQueryData(activityQuery).catch(() => undefined),
  component: ActivityFeed,
});
