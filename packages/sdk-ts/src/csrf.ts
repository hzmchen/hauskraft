// SPDX-License-Identifier: MIT
// The CSRF token from the session response lives in memory only (never in storage) and goes out as
// X-CSRF-Token on every unsafe request (spec §8, M0S-E05-02).
import { client } from "./client/client.gen";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function getCsrfToken(): string | null {
  return csrfToken;
}

client.interceptors.request.use((request) => {
  if (csrfToken && !SAFE_METHODS.has(request.method.toUpperCase())) {
    request.headers.set("X-CSRF-Token", csrfToken);
  }
  return request;
});
