// SPDX-License-Identifier: AGPL-3.0-or-later
import { usersUsersListOptions } from "@hauskraft/sdk-ts";
import { createFileRoute, redirect } from "@tanstack/react-router";

import { MembersSettings } from "../../settings/Members";
import { mayOpen } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings/members")({
  // Owners only (M1S-E08-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("members", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  // Render with the current members list: fetched on every visit (another owner or the member may just have
  // changed it), so the page never starts from a stale cache. A failure must not replace the page.
  loader: ({ context }) =>
    context.queryClient.fetchQuery({ ...usersUsersListOptions(), staleTime: 0 }).catch(() => undefined),
  component: MembersSettings,
});
