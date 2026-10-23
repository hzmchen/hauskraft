// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { AccountSettings } from "../../settings/Account";

export const Route = createFileRoute("/_app/settings/account")({
  component: AccountSettings,
});
