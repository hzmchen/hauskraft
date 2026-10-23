// SPDX-License-Identifier: AGPL-3.0-or-later
// First-run setup state (M1S-E03-02): asked once per page load and cached, because it only ever changes from
// "required" to "done", which the wizard records itself.
import { setupStatusOptions } from "@hauskraft/sdk-ts";
import type { QueryClient } from "@tanstack/react-query";

export function setupQuery() {
  return { ...setupStatusOptions(), staleTime: Infinity } as const;
}

/** True while the household has no account yet. A server that can't answer is treated as set up. */
export async function setupRequired(queryClient: QueryClient): Promise<boolean> {
  try {
    return (await queryClient.ensureQueryData(setupQuery())).required;
  } catch {
    return false;
  }
}

export function markSetUp(queryClient: QueryClient): void {
  queryClient.setQueryData(setupQuery().queryKey, { required: false });
}
