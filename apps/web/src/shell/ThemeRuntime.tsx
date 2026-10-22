// SPDX-License-Identifier: AGPL-3.0-or-later
// Applies the household theme (M0S-E13-05). index.html already links /api/v1/theme/active.css; this keeps
// it current: GET /theme every 60 s and on focus, and when the hash changes it loads the new stylesheet
// next to the old one and removes the old one only once the new one has loaded (no unstyled frame, no
// reload, form input kept). It also sets the variant hooks on <html> and feeds icons and layout.
import { themesActiveOptions, type ActiveTheme } from "@hauskraft/sdk-ts";
import { IconProvider } from "@hauskraft/ui";
import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, type ReactNode } from "react";

import type { NavLayout } from "./nav/NavRenderer";

/** GET /theme, polled every 60 s and on focus. A function: the generated options capture client config. */
export function themeQueryOptions() {
  return { ...themesActiveOptions(), refetchInterval: 60_000, refetchOnWindowFocus: true, staleTime: 0 } as const;
}

export interface ThemeLayout {
  navigation: NavLayout;
  density: string;
  content_width: string;
}

const DEFAULT_LAYOUT: ThemeLayout = {
  navigation: { wide: "sidebar", narrow: "drawer" },
  density: "comfortable",
  content_width: "full",
};

const LayoutContext = createContext<ThemeLayout>(DEFAULT_LAYOUT);

export function useThemeLayout(): ThemeLayout {
  return useContext(LayoutContext);
}

const LINK_SELECTOR = "link[data-hauskraft-theme-css]";

/** Point the page at `cssUrl`, keeping the old sheet until the new one has loaded. */
function swapStylesheet(theme: ActiveTheme): void {
  const current = [...document.head.querySelectorAll<HTMLLinkElement>(LINK_SELECTOR)];
  const newest = current.at(-1);
  if (!newest) return;
  if (!newest.dataset.hash) {
    newest.dataset.hash = theme.hash; // the sheet index.html loaded is the active theme's
    return;
  }
  if (newest.dataset.hash === theme.hash) return;
  const next = document.createElement("link");
  next.rel = "stylesheet";
  next.href = theme.css_url;
  next.dataset.hauskraftThemeCss = "";
  next.dataset.hash = theme.hash;
  const done = () => {
    for (const old of current) old.remove();
  };
  next.addEventListener("load", done, { once: true });
  next.addEventListener("error", done, { once: true });
  newest.after(next);
}

function applyAttributes(theme: ActiveTheme): void {
  const html = document.documentElement.dataset;
  html.hauskraftTheme = theme.theme_id;
  html.hauskraftChrome = theme.components.widget.chrome;
  html.hauskraftHeader = theme.components.widget.header;
  html.hauskraftButton = theme.components.button.primary;
  html.hauskraftCheckbox = theme.components.checkbox.style;
  html.hauskraftDensity = theme.layout.density;
  html.hauskraftContent = theme.layout.content_width;
}

export function ThemeRuntime({ children }: { children: ReactNode }) {
  const { data: theme } = useQuery(themeQueryOptions());

  useEffect(() => {
    if (!theme) return;
    swapStylesheet(theme);
    applyAttributes(theme);
  }, [theme]);

  const layout: ThemeLayout = theme
    ? {
        navigation: theme.layout.navigation as NavLayout,
        density: theme.layout.density,
        content_width: theme.layout.content_width,
      }
    : DEFAULT_LAYOUT;

  return (
    <LayoutContext.Provider value={layout}>
      <IconProvider spriteUrl={theme?.icons.sprite_url ?? null} names={theme?.icons.names ?? []}>
        {children}
      </IconProvider>
    </LayoutContext.Provider>
  );
}
