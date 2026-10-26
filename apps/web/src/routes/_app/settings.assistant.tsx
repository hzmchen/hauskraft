// SPDX-License-Identifier: AGPL-3.0-or-later
import { assistantSettingsReadOptions, assistantToolsListOptions } from "@hauskraft/sdk-ts";
import { createFileRoute, redirect } from "@tanstack/react-router";

import { AssistantSettings } from "../../settings/Assistant";
import { mayOpen } from "../../settings/sections";

export const Route = createFileRoute("/_app/settings/assistant")({
  // Owners only (M2S-E07-01); everyone else lands on Appearance.
  beforeLoad: ({ context }) => {
    if (!mayOpen("assistant", context.session.permissions)) throw redirect({ to: "/settings/appearance" });
  },
  // Render with the current settings and tools, fetched on every visit. A failure must not replace the page.
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.fetchQuery({ ...assistantSettingsReadOptions(), staleTime: 0 }),
      context.queryClient.fetchQuery({ ...assistantToolsListOptions(), staleTime: 0 }),
    ]).catch(() => undefined),
  component: AssistantSettings,
});
