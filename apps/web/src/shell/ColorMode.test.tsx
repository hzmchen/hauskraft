// SPDX-License-Identifier: AGPL-3.0-or-later
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { ColorModeControl, ColorModeProvider, MODE_STORAGE_KEY } from "./ColorMode";

type Listener = (event: { matches: boolean }) => void;

function fakeSystem(dark: boolean) {
  const listeners: Listener[] = [];
  const query = {
    matches: dark,
    addEventListener: (_: string, listener: Listener) => listeners.push(listener),
    removeEventListener: (_: string, listener: Listener) => listeners.splice(listeners.indexOf(listener), 1),
  };
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => query),
  );
  return {
    change(nowDark: boolean) {
      query.matches = nowDark;
      for (const listener of [...listeners]) listener({ matches: nowDark });
    },
  };
}

function renderControl() {
  return render(
    <I18nextProvider i18n={createI18n({ lng: "en" })}>
      <ColorModeProvider>
        <ColorModeControl />
      </ColorModeProvider>
    </I18nextProvider>,
  );
}

const isDark = () => document.documentElement.classList.contains("dark");

beforeEach(() => {
  localStorage.clear();
  document.documentElement.className = "";
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("colour mode", () => {
  it("defaults to System and follows the OS", () => {
    fakeSystem(true);
    renderControl();
    expect((screen.getByRole("radio", { name: "System" }) as HTMLInputElement).checked).toBe(true);
    expect(isDark()).toBe(true);
  });

  it("Dark sets the class and remembers it on this device only", async () => {
    fakeSystem(false);
    renderControl();
    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(isDark()).toBe(true);
    expect(localStorage.getItem(MODE_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("radiogroup", { name: "Colour mode" })).toBeDefined();
  });

  it("restores the stored mode", () => {
    fakeSystem(true);
    localStorage.setItem(MODE_STORAGE_KEY, "light");
    renderControl();
    expect((screen.getByRole("radio", { name: "Light" }) as HTMLInputElement).checked).toBe(true);
    expect(isDark()).toBe(false);
  });

  it("System reacts live to OS changes, a fixed mode does not", async () => {
    const system = fakeSystem(false);
    renderControl();
    act(() => system.change(true));
    expect(isDark()).toBe(true);
    await userEvent.click(screen.getByRole("radio", { name: "Light" }));
    act(() => system.change(true));
    expect(isDark()).toBe(false);
  });

  it("works for the session when storage is blocked", async () => {
    fakeSystem(false);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    renderControl();
    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(isDark()).toBe(true);
  });
});

describe("pre-paint script in index.html", () => {
  const html = readFileSync(resolve(__dirname, "../../index.html"), "utf8");
  const script = /<script>([\s\S]*?)<\/script>/.exec(html)?.[1] ?? "";

  it("is small and sets .dark from storage or the OS before React loads", () => {
    expect(script.length).toBeGreaterThan(0);
    expect(new TextEncoder().encode(script).length).toBeLessThanOrEqual(1024);
    fakeSystem(false);
    localStorage.setItem(MODE_STORAGE_KEY, "dark");
    new Function(script)();
    expect(isDark()).toBe(true);
    localStorage.setItem(MODE_STORAGE_KEY, "system");
    document.documentElement.className = "";
    fakeSystem(true);
    new Function(script)();
    expect(isDark()).toBe(true);
  });

  it("has its CSP hash documented", () => {
    const hash = `sha256-${createHash("sha256").update(script).digest("base64")}`;
    expect(readFileSync(resolve(__dirname, "../../CSP.md"), "utf8")).toContain(hash);
  });
});
