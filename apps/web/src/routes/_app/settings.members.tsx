// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute, redirect } from "@tanstack/react-router";

import { MembersSettings } from "../../settings/Members";
import { mayOpen } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings/members")({
  // Owners only (M1S-E08-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("members", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  component: MembersSettings,
});
