// SPDX-License-Identifier: MIT
// What the shell offers plugin web code besides the API client: in-app navigation, the current page's URL search
// parameters and the household time zone (plugins never import the router or core). The shell provides a router-backed host;
// without one, the browser location is used.
import { createContext, createElement, useContext, type ReactNode } from "react";

export interface Host {
  /** Go to an in-app path such as "/p/tasks" without reloading the page. */
  navigate: (href: string) => void;
  /** The current page's search parameters, already validated as strings. */
  search: Readonly<Record<string, string>>;
  /** Change search parameters; `undefined` removes one. */
  setSearch: (updates: Record<string, string | undefined>) => void;
  /** The household's IANA time zone (M1S-E04-03). It decides what "today" means, not the device's zone. */
  timeZone: string;
}

/** The fallback without a shell: the browser's location and time zone. */
export const browserHost: Host = {
  navigate: (href) => window.location.assign(href),
  get search() {
    return Object.fromEntries(new URLSearchParams(window.location.search));
  },
  setSearch: (updates) => {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(updates)) {
      if (value === undefined) params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  },
  get timeZone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  },
};

const HostContext = createContext<Host>(browserHost);

export function HostProvider({ host, children }: { host: Host; children: ReactNode }) {
  return createElement(HostContext.Provider, { value: host }, children);
}

export function useHost(): Host {
  return useContext(HostContext);
}
