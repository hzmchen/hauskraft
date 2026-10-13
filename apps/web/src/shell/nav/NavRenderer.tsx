// SPDX-License-Identifier: AGPL-3.0-or-later
// Picks the renderer for the active theme's layout: `wide` from 768 px, `narrow` below (M0S-E08-05).
// Renderers differ only in presentation; they all get the same model.
import { useSyncExternalStore, type ComponentType } from "react";

import { DrawerNav } from "./DrawerNav";
import type { NavRendererProps } from "./model";
import { SidebarNav } from "./SidebarNav";

export type NavStyle = "sidebar" | "topbar" | "drawer" | "bottom-tabs";
export interface NavLayout {
  wide: NavStyle;
  narrow: NavStyle;
}
export const DEFAULT_NAV_LAYOUT: NavLayout = { wide: "sidebar", narrow: "drawer" };

const WIDE_QUERY = "(min-width: 768px)";

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const query = window.matchMedia(WIDE_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

export function useIsWide(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => typeof window.matchMedia !== "function" || window.matchMedia(WIDE_QUERY).matches,
    () => true,
  );
}

export const RENDERERS: Partial<Record<NavStyle, ComponentType<NavRendererProps>>> = {
  sidebar: SidebarNav,
  drawer: DrawerNav,
};

export function useNavStyle(layout: NavLayout = DEFAULT_NAV_LAYOUT): NavStyle {
  const wide = useIsWide();
  const wanted = wide ? layout.wide : layout.narrow;
  return wanted in RENDERERS ? wanted : wide ? "sidebar" : "drawer";
}

export function NavRenderer({ style, items }: NavRendererProps & { style: NavStyle }) {
  const Renderer = RENDERERS[style] ?? SidebarNav;
  return <Renderer items={items} />;
}
