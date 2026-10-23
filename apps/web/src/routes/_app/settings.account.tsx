// SPDX-License-Identifier: AGPL-3.0-or-later
import { usersMeSessionsOptions } from "@hauskraft/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { AccountSettings } from "../../settings/Account";

export const Route = createFileRoute("/_app/settings/account")({
  // Render with the devices list, not an empty list that fills in later (same accessibility tree in every theme).
  // Prefetch only: a failure must not replace the page; the component's own query loads and reports it.
  loader: ({ context }) => context.queryClient.ensureQueryData(usersMeSessionsOptions()).catch(() => undefined),
  component: AccountSettings,
});
