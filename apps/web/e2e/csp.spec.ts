// SPDX-License-Identifier: AGPL-3.0-or-later
// M0S-E11-01: the web front door sends a strict CSP, and no built-in theme triggers a CSP violation
// (no remote fonts or images, the colour-mode script allowed by hash). Runs against the Compose stack:
//   HEARTHOS_BASE_URL=http://localhost:8080 pnpm --filter web exec playwright test
import { expect, request, test } from "@playwright/test";

const BASE_URL = process.env.HEARTHOS_BASE_URL ?? "http://localhost:8080";
const THEMES = ["org.hearthos.theme.default", "org.hearthos.theme.paper", "org.hearthos.theme.hackspace"];
const VIEWS = ["/login", "/today", "/p/tasks", "/activity", "/settings/appearance"];

async function setTheme(themeId: string) {
  const api = await request.newContext({ baseURL: `${BASE_URL}/api/v1/`, extraHTTPHeaders: { Origin: BASE_URL } });
  const session = await (
    await api.post("auth/login", { data: { username: "demo", password: "hearthos-demo" } })
  ).json();
  const res = await api.put("settings/theme", {
    data: { theme_id: themeId },
    headers: { "X-CSRF-Token": session.csrf_token },
  });
  expect(res.ok(), await res.text()).toBe(true);
  await api.dispose();
}

test.afterAll(async () => setTheme(THEMES[0]!));

test("every page is served with the strict CSP", async ({ request: http }) => {
  for (const path of ["/", "/today"]) {
    const csp = (await http.get(`${BASE_URL}${path}`)).headers()["content-security-policy"] ?? "";
    for (const directive of [
      "default-src 'self'",
      "font-src 'self'",
      "img-src 'self' data:",
      "frame-ancestors 'none'",
    ]) {
      expect(csp, `${path}: ${directive}`).toContain(directive);
    }
    expect(csp).toMatch(/script-src 'self' 'sha256-[A-Za-z0-9+/=]+'/);
  }
});

for (const themeId of THEMES) {
  for (const colorScheme of ["light", "dark"] as const) {
    test(`no CSP violations in ${themeId} (${colorScheme})`, async ({ browser }) => {
      await setTheme(themeId);
      const context = await browser.newContext({ colorScheme });
      const page = await context.newPage();
      const violations: string[] = [];
      page.on("console", (message) => {
        if (/Content.Security.Policy/i.test(message.text())) violations.push(message.text());
      });
      await page.addInitScript(() =>
        document.addEventListener("securitypolicyviolation", (e) =>
          console.error(`Content-Security-Policy violation: ${e.violatedDirective} ${e.blockedURI}`),
        ),
      );
      await page.goto(`${BASE_URL}/login`);
      await page.getByRole("textbox", { name: "Username" }).fill("demo");
      await page.getByLabel("Password").fill("hearthos-demo");
      await page.getByRole("button", { name: "Sign in" }).click();
      await page.waitForURL(/\/today$/);
      for (const view of VIEWS.slice(1)) {
        await page.goto(`${BASE_URL}${view}`);
        await expect.poll(() => page.evaluate(() => document.documentElement.dataset.hearthTheme)).toBe(themeId);
        await page.waitForLoadState("networkidle");
      }
      expect(violations).toEqual([]);
      await context.close();
    });
  }
}
