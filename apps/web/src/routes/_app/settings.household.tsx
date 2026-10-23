// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute, redirect } from "@tanstack/react-router";

import { householdQuery } from "../../household";
import { HouseholdSettings } from "../../settings/Household";
import { mayOpen } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings/household")({
  // Owners only (M1S-E08-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("household", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  // Render with the form filled in, not an empty page that fills in later; prefetch only.
  loader: ({ context }) => context.queryClient.ensureQueryData(householdQuery()).catch(() => undefined),
  component: HouseholdSettings,
});
