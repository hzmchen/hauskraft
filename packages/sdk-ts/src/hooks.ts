// SPDX-License-Identifier: MIT
import { createContext, createElement, useContext, type ReactNode } from "react";

import { client } from "./client/client.gen";

type Client = typeof client;
const ClientContext = createContext<Client>(client);

/** Lets tests or the shell swap the client; plugins never need it. */
export function HearthosClientProvider({ client: value, children }: { client: Client; children: ReactNode }) {
  return createElement(ClientContext.Provider, { value }, children);
}

/** The configured API client (cookies, CSRF header). Pass it as `client` to generated calls if needed. */
export function useHearthosClient(): Client {
  return useContext(ClientContext);
}
