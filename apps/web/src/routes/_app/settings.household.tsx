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
  // Render the form with the current values, fetched on every visit (another owner may just have changed them).
  loader: ({ context }) => context.queryClient.fetchQuery({ ...householdQuery(), staleTime: 0 }).catch(() => undefined),
  component: HouseholdSettings,
});
