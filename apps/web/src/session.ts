// SPDX-License-Identifier: AGPL-3.0-or-later
// The signed-in session (M0S-E08-03). GET /auth/session answers 401 when signed out; the CSRF token
// from the session is kept in memory by @hauskraft/sdk-ts and sent on every unsafe request.
import { authLogout, authSession, setCsrfToken, type SessionOut } from "@hauskraft/sdk-ts";
import { queryOptions, type QueryClient } from "@tanstack/react-query";

export const sessionQuery = queryOptions({
  queryKey: ["session"] as const,
  queryFn: async (): Promise<SessionOut | null> => {
    const { data, response } = await authSession();
    if (response?.status === 401) {
      setCsrfToken(null);
      return null;
    }
    if (!data) throw new Error("Could not check the session.");
    setCsrfToken(data.csrf_token);
    return data;
  },
  staleTime: 60_000,
});

/** Where to go after sign-in: only paths on this site, never `//host` or absolute URLs. */
export function safeRedirect(target: unknown): string {
  return typeof target === "string" && /^\/(?![/\\])/.test(target) ? target : "/today";
}

export function rememberSession(queryClient: QueryClient, session: SessionOut): void {
  setCsrfToken(session.csrf_token);
  queryClient.setQueryData(sessionQuery.queryKey, session);
}

/** End the session, forget every cached query and the CSRF token. */
export async function signOut(queryClient: QueryClient): Promise<void> {
  await authLogout();
  setCsrfToken(null);
  queryClient.clear();
}
