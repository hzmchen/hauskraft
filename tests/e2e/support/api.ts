// SPDX-License-Identifier: MIT
// Thin API helper for e2e setup and clean-up (login with CSRF, theme switching, tasks, M1* members and household).
import { request, type APIRequestContext } from "@playwright/test";

export const BASE_URL = process.env.HAUSKRAFT_BASE_URL ?? "http://localhost:8080";
export const PASSWORD = process.env.HAUSKRAFT_DEMO_PASSWORD ?? "hauskraft-demo";
/** Passwords for throwaway accounts (M1*); all meet the 12-character policy. */
export const TEMP_PASSWORD = "temporary-pass-1234";
export const MEMBER_PASSWORD = "member-chosen-pass-5678";
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

  static async login(username = "demo", password = PASSWORD, baseUrl = BASE_URL): Promise<Api> {
    const ctx = await request.newContext({ baseURL: `${baseUrl}/api/v1/`, extraHTTPHeaders: { Origin: baseUrl } });
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

  // ---------------------------------------------------------------- M1*
  async status(method: "GET" | "POST" | "PATCH" | "DELETE", path: string, data?: unknown): Promise<number> {
    const r = await this.ctx.fetch(path, { method, data, headers: this.headers() });
    return r.status();
  }

  async me(): Promise<{ id: string; username: string; display_name: string; role: string }> {
    return (await this.ctx.get("me")).json();
  }

  /** Creates a member as this (owner) session; throws unless 201. */
  async createMember(body: {
    username: string;
    display_name: string;
    password?: string;
    role?: "owner" | "adult";
  }): Promise<{ id: string; username: string; display_name: string }> {
    const r = await this.ctx.post("users", { data: { password: TEMP_PASSWORD, ...body }, headers: this.headers() });
    if (r.status() !== 201) throw new Error(`RED: cannot create member: ${r.status()} ${await r.text()}`);
    return r.json();
  }

  async findMember(username: string): Promise<{ id: string; username: string; is_active: boolean } | undefined> {
    const r = await this.ctx.get("users");
    if (!r.ok()) return undefined;
    return ((await r.json()) as { id: string; username: string; is_active: boolean }[]).find(
      (m) => m.username === username,
    );
  }

  async deactivate(userId: string): Promise<void> {
    await this.ctx.post(`users/${userId}/deactivate`, { headers: this.headers() });
  }

  async changePassword(current: string, next: string): Promise<void> {
    const r = await this.ctx.post("me/password", {
      data: { current_password: current, new_password: next },
      headers: this.headers(),
    });
    if (r.status() !== 204) throw new Error(`RED: cannot change password: ${r.status()} ${await r.text()}`);
  }

  async household(): Promise<{ name: string; timezone: string; locale: "en" | "de" }> {
    const r = await this.ctx.get("household");
    if (!r.ok()) throw new Error(`RED: GET /household answered ${r.status()}`);
    return r.json();
  }

  async setHousehold(body: Partial<{ name: string; timezone: string; locale: "en" | "de" }>): Promise<void> {
    const r = await this.ctx.patch("household", { data: body, headers: this.headers() });
    if (!r.ok()) throw new Error(`RED: cannot update household: ${r.status()} ${await r.text()}`);
  }

  async logoutEverywhere(): Promise<void> {
    await this.ctx.post("auth/logout-everywhere", { headers: this.headers() });
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

/** Today plus `offsetDays` in an arbitrary IANA time zone (household time zone tests, M1S-E04-03). */
export function isoDateIn(timeZone: string, offsetDays = 0): string {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date());
  const d = new Date(`${today}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

/** A throwaway username for members created by e2e tests on the shared demo stack. */
export function memberName(): string {
  return `e2e${Math.random().toString(16).slice(2, 10)}`;
}

export function unique(label: string): string {
  return `e2e-${Math.random().toString(16).slice(2, 8)} ${label}`;
}
