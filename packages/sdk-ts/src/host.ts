// SPDX-License-Identifier: MIT
// What the shell offers plugin web code besides the API client: in-app navigation and the current page's
// URL search parameters (plugins never import the router). The shell provides a router-backed host;
// without one, the browser location is used.
import { createContext, createElement, useContext, type ReactNode } from "react";

export interface Host {
  /** Go to an in-app path such as "/p/tasks" without reloading the page. */
  navigate: (href: string) => void;
  /** The current page's search parameters, already validated as strings. */
  search: Readonly<Record<string, string>>;
  /** Change search parameters; `undefined` removes one. */
  setSearch: (updates: Record<string, string | undefined>) => void;
}

const browserHost: Host = {
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
};

const HostContext = createContext<Host>(browserHost);

export function HostProvider({ host, children }: { host: Host; children: ReactNode }) {
  return createElement(HostContext.Provider, { value: host }, children);
}

export function useHost(): Host {
  return useContext(HostContext);
}
