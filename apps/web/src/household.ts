// SPDX-License-Identifier: AGPL-3.0-or-later
// The household settings as the shell uses them (M1S-E04): its name in the browser title and its time zone for
// "today". Refetched every minute, so an owner's change reaches every open device without a reload.
import { householdReadOptions } from "@hauskraft/sdk-ts";

export const householdQuery = { ...householdReadOptions(), refetchInterval: 60_000, staleTime: 30_000 } as const;
