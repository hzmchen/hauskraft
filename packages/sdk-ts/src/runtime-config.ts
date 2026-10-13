// SPDX-License-Identifier: MIT
// Runtime settings for the generated client: same origin (paths already start with /api/v1) and the
// session cookie on every request.
import type { CreateClientConfig } from "./client/client.gen";

export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: "",
  credentials: "include",
});
