// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { json, fakeApi } from "../test/fakeApi";
import { ThemeRuntime, useThemeLayout } from "./ThemeRuntime";

const theme = (id: string, hash: string, extra: Record<string, unknown> = {}) => ({
  theme_id: id,
  name: id,
  hash,
  css_url: `/api/v1/theme/active.css?h=${hash.slice(0, 16)}`,
  components: {
    widget: { chrome: "outlined", header: "inline" },
    button: { primary: "solid" },
    checkbox: { style: "square" },
  },
  layout: { navigation: { wide: "sidebar", narrow: "drawer" }, density: "comfortable", content_width: "full" },
  icons: { sprite_url: null, names: [] },
  ...extra,
});
const HACKSPACE = theme("dev.hauskraft.theme.hackspace", "b".repeat(64), {
  components: {
    widget: { chrome: "tinted", header: "banner" },
    button: { primary: "solid" },
    checkbox: { style: "square" },
  },
  layout: { navigation: { wide: "topbar", narrow: "bottom-tabs" }, density: "compact", content_width: "contained" },
});

function Probe() {
  const layout = useThemeLayout();
  return <p>nav {layout.navigation.wide}</p>;
}

const links = () => [...document.head.querySelectorAll<HTMLLinkElement>("link[data-hauskraft-theme-css]")];
const html = document.documentElement;

beforeEach(() => {
  document.head.innerHTML = '<link rel="stylesheet" href="/api/v1/theme/active.css" data-hauskraft-theme-css />';
});
afterEach(() => vi.unstubAllGlobals());

describe("ThemeRuntime", () => {
  it("sets the variant hooks on <html> from GET /theme", async () => {
    fakeApi({ "GET /api/v1/theme": () => json(HACKSPACE) });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ThemeRuntime>
          <Probe />
        </ThemeRuntime>
      </QueryClientProvider>,
    );
    await screen.findByText("nav topbar");
    expect(html.dataset.hauskraftTheme).toBe("dev.hauskraft.theme.hackspace");
    expect(html.dataset.hauskraftChrome).toBe("tinted");
    expect(html.dataset.hauskraftHeader).toBe("banner");
    expect(html.dataset.hauskraftButton).toBe("solid");
    expect(html.dataset.hauskraftCheckbox).toBe("square");
    expect(html.dataset.hauskraftDensity).toBe("compact");
    expect(html.dataset.hauskraftContent).toBe("contained");
  });

  it("swaps the stylesheet when the hash changes, only after the new one has loaded", async () => {
    let current: ReturnType<typeof theme> = theme("dev.hauskraft.theme.default", "a".repeat(64));
    fakeApi({ "GET /api/v1/theme": () => json(current) });
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ThemeRuntime>
          <input aria-label="draft" defaultValue="keep me" />
        </ThemeRuntime>
      </QueryClientProvider>,
    );
    await vi.waitFor(() => expect(html.dataset.hauskraftTheme).toBe("dev.hauskraft.theme.default"));
    expect(links()).toHaveLength(1);

    current = HACKSPACE;
    await act(() => queryClient.invalidateQueries());
    await vi.waitFor(() => expect(links()).toHaveLength(2));
    const [old, next] = links();
    expect(next!.href).toContain(`h=${"b".repeat(16)}`);
    expect(old!.isConnected).toBe(true); // still styling the page until the new sheet is ready
    act(() => {
      next!.dispatchEvent(new Event("load"));
    });
    expect(links()).toEqual([next]);
    expect(html.dataset.hauskraftTheme).toBe("dev.hauskraft.theme.hackspace");
    expect((screen.getByLabelText("draft") as HTMLInputElement).value).toBe("keep me");
  });

  it("refetches every 60 seconds and on window focus", async () => {
    const { themeQueryOptions } = await import("./ThemeRuntime");
    expect(themeQueryOptions().refetchInterval).toBe(60_000);
    expect(themeQueryOptions().refetchOnWindowFocus).toBe(true);
  });
});
