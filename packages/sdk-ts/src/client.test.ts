// SPDX-License-Identifier: MIT
import { afterEach, describe, expect, it, vi } from "vitest";

import { authLogin, client, setCsrfToken, tasksCreate, tasksList } from "./index";

function stubFetch(): { calls: Request[] } {
  const calls: Request[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request) => {
      calls.push(input);
      return new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return { calls };
}

afterEach(() => {
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("generated client", () => {
  it("talks to the same origin with cookies", async () => {
    const { calls } = stubFetch();
    await tasksList({ client });
    expect(new URL(calls[0]!.url, "http://x").pathname).toBe("/api/v1/tasks");
    expect(calls[0]!.credentials).toBe("include");
  });

  it("sends the CSRF token on unsafe methods only", async () => {
    const { calls } = stubFetch();
    setCsrfToken("t0k3n");
    await tasksList({ client });
    await tasksCreate({ client, body: { title: "Milk" } });
    expect(calls[0]!.headers.get("X-CSRF-Token")).toBeNull();
    expect(calls[1]!.headers.get("X-CSRF-Token")).toBe("t0k3n");
  });

  it("sends no CSRF header before sign-in", async () => {
    const { calls } = stubFetch();
    await authLogin({ client, body: { username: "demo", password: "x" } });
    expect(calls[0]!.headers.get("X-CSRF-Token")).toBeNull();
  });
});
