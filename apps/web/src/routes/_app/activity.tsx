// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { ActivityFeed } from "../../activity/Activity";

export const Route = createFileRoute("/_app/activity")({ component: ActivityFeed });
