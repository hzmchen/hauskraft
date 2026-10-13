// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { ColorModeProvider } from "../shell/ColorMode";
import { fakeApi, json } from "../test/fakeApi";
import { AppearanceSettings } from "./Appearance";

const summary = (id: string, name: string, extra: Record<string, unknown> = {}) => ({
  theme_id: id,
  name,
  description: "",
  version: "0.1.0",
  authors: ["HearthOS contributors"],
  licence: "MIT",
  origin: "builtin",
  valid: true,
  errors: [],
  warnings: [],
  active: false,
  preview: {
    swatches: { light: ["rgb(255 255 255)"], dark: ["rgb(0 0 0)"] },
    navigation: { wide: "sidebar", narrow: "drawer" },
    density: "comfortable",
    widget_chrome: "outlined",
  },
  ...extra,
});

const THEMES = [
  summary("org.hearthos.theme.default", "Default", { active: true }),
  summary("org.hearthos.theme.paper", "Paper"),
  summary("org.example.theme.broken", "Broken", {
    origin: "installed",
    valid: false,
    errors: [
      { code: "contrast.text", message: "muted text is 1.5:1", path: "tokens.light.json#/color/muted-foreground" },
    ],
  }),
];

let puts: unknown[] = [];

async function show() {
  puts = [];
  fakeApi({
    "GET /api/v1/themes": () => json(THEMES),
    "GET /api/v1/theme": () => json({}),
    "PUT /api/v1/settings/theme": async (request) => {
      puts.push(await request.json());
      return json({ ...THEMES[1], active: true });
    },
  });
  await act(async () => {
    render(
      <I18nextProvider i18n={createI18n({ lng: "en" })}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <ColorModeProvider>
            <AppearanceSettings />
          </ColorModeProvider>
        </QueryClientProvider>
      </I18nextProvider>,
    );
  });
  return within(await screen.findByRole("radiogroup", { name: "Household theme" }));
}

// hidden: a modal dialog hides the page behind it from assistive tech while it is open.
const radio = (group: ReturnType<typeof within>, name: string) =>
  group.getByRole("radio", { name, hidden: true }) as HTMLInputElement;

beforeEach(() =>
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} })),
);
afterEach(() => vi.unstubAllGlobals());

describe("Appearance", () => {
  it("explains who is affected and lists the themes, active one checked", async () => {
    const group = await show();
    const household = screen.getByRole("region", { name: "Household theme" });
    expect(household.textContent).toContain("Applies to everyone on every device");
    expect(radio(group, "Default").checked).toBe(true);
    expect(within(household).getByText("Active")).toBeDefined();
    expect(screen.getByRole("region", { name: "This device" }).textContent).toContain("Only this device");
    expect(screen.getByRole("radiogroup", { name: "Colour mode" })).toBeDefined();
  });

  it("asks before changing the look for everyone, then saves", async () => {
    const group = await show();
    await userEvent.click(radio(group, "Paper"));
    expect(radio(group, "Paper").checked).toBe(true);
    const dialog = await screen.findByRole("dialog", { name: "Change the look for everyone?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Change theme" }));
    await vi.waitFor(() => expect(puts).toEqual([{ theme_id: "org.hearthos.theme.paper" }]));
  });

  it("cancelling keeps the current theme", async () => {
    const group = await show();
    await userEvent.click(radio(group, "Paper"));
    const dialog = await screen.findByRole("dialog", { name: "Change the look for everyone?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(puts).toEqual([]);
    expect(radio(group, "Default").checked).toBe(true);
  });

  it("invalid themes cannot be selected and explain why", async () => {
    const group = await show();
    expect(radio(group, "Broken").disabled).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Show problems" }));
    expect(screen.getByText(/muted text is 1.5:1/).textContent).toContain("muted text is 1.5:1");
    expect(screen.getByText(/tokens.light.json#\/color\/muted-foreground/)).toBeDefined();
  });

  it("has no free-form input", async () => {
    await show();
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  });
});
