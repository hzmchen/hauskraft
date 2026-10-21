// SPDX-License-Identifier: MIT
// Test harness for the tasks plugin: a stubbed API (no server), i18n with the plugin's strings, React Query.
import { client } from "@hauskraft/sdk-ts";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render } from "@testing-library/react";
import i18next from "i18next";
import type { ReactNode } from "react";
import { I18nextProvider, initReactI18next } from "react-i18next";
import { vi } from "vitest";

import plugin from "../index";

export type Handler = (request: Request) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** "GET /path?b=2&a=1" → "GET /path?a=1&b=2", so routes match whatever order the client sends. */
function normalise(key: string): string {
  const [head, query] = key.split("?");
  if (!query) return key;
  const params = new URLSearchParams(query);
  params.sort();
  return `${head}?${params.toString()}`;
}

export function fakeApi(routes: Record<string, Handler>): Request[] {
  const seen: Request[] = [];
  const table = Object.fromEntries(Object.entries(routes).map(([key, handler]) => [normalise(key), handler]));
  client.setConfig({ baseUrl: "http://hauskraft.test" });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      seen.push(request.clone());
      const url = new URL(request.url);
      const handler =
        table[normalise(`${request.method} ${url.pathname}${url.search}`)] ??
        table[`${request.method} ${url.pathname}`];
      return handler ? handler(request) : json({ code: "not_found" }, 404);
    }),
  );
  return seen;
}

export function task(title: string, extra: Record<string, unknown> = {}) {
  const user = { id: "0199f390-1111-7aaa-8bbb-cccccccccccc", display_name: "Demo Adult" };
  return {
    id: `id-${title.replace(/\s+/g, "-")}`,
    title,
    done: false,
    done_at: null,
    due_on: null,
    data_class: "household",
    version: 1,
    created_by: user,
    updated_by: user,
    created_at: "2026-10-13T08:00:00Z",
    updated_at: "2026-10-13T08:00:00Z",
    ...extra,
  };
}

export const page = (items: unknown[]) => json({ items, total: items.length, limit: 50, offset: 0 });

export async function renderWithPlugin(ui: ReactNode, lng = "en") {
  const i18n = i18next.createInstance();
  await i18n
    .use(initReactI18next)
    .init({ lng, fallbackLng: "en", resources: {}, interpolation: { escapeValue: false } });
  for (const [language, strings] of Object.entries(plugin.locales)) i18n.addResourceBundle(language, "tasks", strings);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  await act(async () => {
    render(
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
      </I18nextProvider>,
    );
  });
  return { queryClient, i18n };
}
