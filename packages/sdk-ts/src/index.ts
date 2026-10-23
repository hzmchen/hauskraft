// SPDX-License-Identifier: MIT
// @hauskraft/sdk-ts: widget/page contracts and the generated API client (M0S-E06-05).
import "./csrf";

export const HAUSKRAFT_API_VERSION = "0.1.0";

export * from "./client";
export { client } from "./client/client.gen";
export * from "./client/@tanstack/react-query.gen";
export { definePluginWeb, type PageProps, type PluginWebModule, type WidgetProps } from "./contract";
export { getCsrfToken, setCsrfToken } from "./csrf";
export { HauskraftClientProvider, useHauskraftClient } from "./hooks";
export { browserHost, HostProvider, useHost, type Host } from "./host";
