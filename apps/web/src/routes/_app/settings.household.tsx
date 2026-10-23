// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute, redirect } from "@tanstack/react-router";

import { mayOpen } from "../../settings/sections";
import { HouseholdSettings } from "../../settings/Household";

export const Route = createFileRoute("/_app/settings/household")({
  // Owners only (M1S-E08-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("household", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  component: HouseholdSettings,
});
