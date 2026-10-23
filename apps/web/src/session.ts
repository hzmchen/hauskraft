// SPDX-License-Identifier: AGPL-3.0-or-later
// The signed-in session (M0S-E08-03). GET /auth/session answers 401 when signed out; the CSRF token
// from the session is kept in memory by @hauskraft/sdk-ts and sent on every unsafe request.
import { authLogout, authSession, client, setCsrfToken, type SessionOut } from "@hauskraft/sdk-ts";
import { queryOptions, useQuery, type QueryClient } from "@tanstack/react-query";

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

/** The signed-in session inside the shell (the `_app` route guarantees one). */
export function useSession(): SessionOut {
  const { data } = useQuery(sessionQuery);
  if (!data) throw new Error("useSession() needs a signed-in session");
  return data;
}

/** Whether the session's role may do `action` (M1S-E02-04). For showing controls only; the API decides. */
export function can(session: Pick<SessionOut, "permissions">, action: string): boolean {
  return session.permissions.includes(action);
}

/** Where to go after sign-in: only paths on this site, never `//host` or absolute URLs. */
export function safeRedirect(target: unknown): string {
  return typeof target === "string" && /^\/(?![/\\])/.test(target) ? target : "/today";
}

export function rememberSession(queryClient: QueryClient, session: SessionOut): void {
  setCsrfToken(session.csrf_token);
  queryClient.setQueryData(sessionQuery.queryKey, session);
}

let signingOut = false;

/** End the session, forget every cached query and the CSRF token. */
export async function signOut(queryClient: QueryClient): Promise<void> {
  signingOut = true;
  try {
    await authLogout();
    setCsrfToken(null);
    queryClient.clear();
  } finally {
    signingOut = false;
  }
}

/**
 * Any 401 while the app believed it was signed in means the session ended elsewhere: it expired, the member signed
 * out everywhere, or an owner deactivated the account (M1S-E07-03). Forget everything cached and call `onEnded`.
 * A failed sign-in is not an ended session. Returns a function that stops watching.
 */
export function watchForEndedSessions(queryClient: QueryClient, onEnded: () => void): () => void {
  const id = client.interceptors.response.use((response, request) => {
    const signedIn = queryClient.getQueryData(sessionQuery.queryKey) != null;
    if (response.status === 401 && signedIn && !signingOut && !new URL(request.url).pathname.endsWith("/auth/login")) {
      setCsrfToken(null);
      queryClient.clear();
      onEnded();
    }
    return response;
  });
  return () => client.interceptors.response.eject(id);
}
