// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { AppearanceSettings } from "../../settings/Appearance";

export const Route = createFileRoute("/_app/settings/appearance")({ component: AppearanceSettings });
