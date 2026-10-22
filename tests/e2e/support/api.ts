// SPDX-License-Identifier: MIT
// Thin API helper for e2e setup and clean-up (login with CSRF, theme switching, tasks).
import { request, type APIRequestContext } from "@playwright/test";

export const BASE_URL = process.env.HAUSKRAFT_BASE_URL ?? "http://localhost:8080";
export const PASSWORD = process.env.HAUSKRAFT_DEMO_PASSWORD ?? "hauskraft-demo";
export const THEMES = {
  default: "dev.hauskraft.theme.default",
  paper: "dev.hauskraft.theme.paper",
  hackspace: "dev.hauskraft.theme.hackspace",
} as const;

export class Api {
  private constructor(
    readonly ctx: APIRequestContext,
    private csrf: string,
  ) {}

  static async login(username = "demo", password = PASSWORD): Promise<Api> {
    const ctx = await request.newContext({ baseURL: `${BASE_URL}/api/v1/`, extraHTTPHeaders: { Origin: BASE_URL } });
    const r = await ctx.post("auth/login", { data: { username, password } });
    if (!r.ok()) throw new Error(`RED: cannot log in as ${username}: ${r.status()} ${await r.text()}`);
    return new Api(ctx, (await r.json()).csrf_token);
  }

  private headers() {
    return { "X-CSRF-Token": this.csrf };
  }

  async setTheme(themeId: string): Promise<void> {
    const r = await this.ctx.put("settings/theme", { data: { theme_id: themeId }, headers: this.headers() });
    if (!r.ok()) throw new Error(`cannot switch theme to ${themeId}: ${r.status()} ${await r.text()}`);
  }

  async activeTheme(): Promise<{ theme_id: string; hash: string }> {
    return (await this.ctx.get("theme")).json();
  }

  async createTask(title: string, due_on?: string): Promise<{ id: string; title: string }> {
    const r = await this.ctx.post("tasks", { data: due_on ? { title, due_on } : { title }, headers: this.headers() });
    if (r.status() !== 201) throw new Error(`cannot create task: ${r.status()} ${await r.text()}`);
    return r.json();
  }

  async patchTask(id: string, body: Record<string, unknown>): Promise<void> {
    await this.ctx.patch(`tasks/${id}`, { data: body, headers: this.headers() });
  }

  async findTask(title: string): Promise<{ id: string; due_on: string | null }> {
    const r = await this.ctx.get("tasks", { params: { limit: 200 } });
    const task = ((await r.json()).items as { id: string; title: string; due_on: string | null }[]).find(
      (t) => t.title === title,
    );
    if (!task) throw new Error(`no task titled '${title}'`);
    return task;
  }

  async deleteTask(id: string): Promise<void> {
    await this.ctx.delete(`tasks/${id}`, { headers: this.headers() });
  }

  async setLocale(locale: "en" | "de"): Promise<void> {
    await this.ctx.patch("me", { data: { locale }, headers: this.headers() });
  }

  async dispose(): Promise<void> {
    await this.ctx.dispose();
  }
}

/** Today plus `offsetDays` in Europe/Berlin, the browser time zone set in playwright.config.ts. */
export function isoDate(offsetDays: number): string {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin" }).format(new Date());
  const d = new Date(`${today}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function unique(label: string): string {
  return `e2e-${Math.random().toString(16).slice(2, 8)} ${label}`;
}
