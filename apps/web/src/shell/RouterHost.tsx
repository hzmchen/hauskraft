// SPDX-License-Identifier: AGPL-3.0-or-later
// Gives plugin web code navigation, the page's search parameters and the household time zone through
// @hauskraft/sdk-ts (useHost), backed by the router and the household settings, so plugins never import either.
import { browserHost, HostProvider, type Host } from "@hauskraft/sdk-ts";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useMemo, type ReactNode } from "react";

import { householdQuery } from "../household";

/** Search values as strings; anything else (objects, arrays) is not part of the plugin contract. */
export function stringSearch(search: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(search)
      .filter(([, value]) => typeof value === "string" || typeof value === "number" || typeof value === "boolean")
      .map(([key, value]) => [key, String(value)]),
  );
}

export function RouterHost({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useRouterState({ select: (state) => state.location });
  const { data: household } = useQuery(householdQuery());
  const timeZone = household?.timezone ?? browserHost.timeZone;
  const host = useMemo<Host>(
    () => ({
      navigate: (href) => void navigate({ href }),
      search: stringSearch(location.search as Record<string, unknown>),
      setSearch: (updates) => {
        const next = { ...stringSearch(location.search as Record<string, unknown>), ...updates };
        const params = new URLSearchParams();
        for (const [key, value] of Object.entries(next)) if (value !== undefined) params.set(key, value);
        const query = params.toString();
        void navigate({ href: `${location.pathname}${query ? `?${query}` : ""}` });
      },
      timeZone,
    }),
    [navigate, location, timeZone],
  );
  return <HostProvider host={host}>{children}</HostProvider>;
}
