// SPDX-License-Identifier: AGPL-3.0-or-later
// jsdom has no matchMedia; components (colour mode, nav layout, toasts) read it. Tests that care stub
// their own with vi.stubGlobal("matchMedia", …).
if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
