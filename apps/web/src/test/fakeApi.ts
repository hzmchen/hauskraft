// SPDX-License-Identifier: AGPL-3.0-or-later
// Test helper: answer the generated client's requests from a table instead of a server.
import { client } from "@hauskraft/sdk-ts";
import { vi } from "vitest";

export type Handler = (request: Request) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function problem(status: number, code: string): Response {
  return new Response(JSON.stringify({ status, code, title: code, detail: code }), {
    status,
    headers: { "Content-Type": "application/problem+json" },
  });
}

/** Routes like "GET /api/v1/auth/session". Unknown routes answer 404. Returns the request log. */
export function fakeApi(routes: Record<string, Handler>): Request[] {
  const seen: Request[] = [];
  client.setConfig({ baseUrl: "http://hauskraft.test" });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      seen.push(request);
      const key = `${request.method} ${new URL(request.url).pathname}`;
      const handler = routes[key];
      return handler ? handler(request) : problem(404, "not_found");
    }),
  );
  return seen;
}

export const DEMO_SESSION = {
  user: {
    id: "0199f390-1111-7aaa-8bbb-cccccccccccc",
    username: "demo",
    display_name: "Demo Adult",
    role: "adult",
    locale: "en",
    must_change_password: false,
  },
  csrf_token: "csrf-123",
  expires_at: "2099-01-01T00:00:00Z",
  permissions: [
    "dashboard.layout.set",
    "session.create",
    "session.revoke",
    "task.create",
    "task.delete",
    "task.update",
    "user.change_password",
    "user.update_self",
  ],
};

/** The same session for an owner (M1S-E02-04): every permission of the table. */
export const OWNER_SESSION = {
  ...DEMO_SESSION,
  user: { ...DEMO_SESSION.user, role: "owner" },
  permissions: [
    ...DEMO_SESSION.permissions,
    "plugin.toggle",
    "settings.household.set",
    "settings.theme.set",
    "user.create",
    "user.deactivate",
    "user.list",
    "user.reactivate",
    "user.reset_password",
    "user.update",
  ].sort(),
};
