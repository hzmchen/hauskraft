// SPDX-License-Identifier: AGPL-3.0-or-later
import { usersMeSessionsOptions } from "@hauskraft/sdk-ts";
import { createFileRoute } from "@tanstack/react-router";

import { AccountSettings } from "../../settings/Account";

export const Route = createFileRoute("/_app/settings/account")({
  // Render with the current devices list, fetched on every visit, not an empty or stale list that changes later
  // (same accessibility tree in every theme). A failure must not replace the page.
  loader: ({ context }) =>
    context.queryClient.fetchQuery({ ...usersMeSessionsOptions(), staleTime: 0 }).catch(() => undefined),
  component: AccountSettings,
});
