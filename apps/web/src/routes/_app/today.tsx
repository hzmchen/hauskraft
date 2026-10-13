// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { TodayDashboard } from "../../dashboard/Today";

export const Route = createFileRoute("/_app/today")({ component: TodayDashboard });
