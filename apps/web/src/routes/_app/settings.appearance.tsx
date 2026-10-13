// SPDX-License-Identifier: AGPL-3.0-or-later
import { themesListOptions } from "@hearthos/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { AppearanceSettings } from "../../settings/Appearance";

export const Route = createFileRoute("/_app/settings/appearance")({
  // Render with the theme list, not an empty radio group that fills in later.
  // Prefetch only: a failure must not replace the page; the component's own query loads and reports it.
  loader: ({ context }) => context.queryClient.ensureQueryData(themesListOptions()).catch(() => undefined),
  component: AppearanceSettings,
});
