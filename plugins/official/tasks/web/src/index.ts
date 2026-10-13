// SPDX-License-Identifier: MIT
// Tasks plugin web module (M0S-E09-01..03). The shell loads it through the build-time registry.
import { definePluginWeb } from "@hearthos/sdk-ts";

export const pluginId = "org.hearthos.tasks";

// The widget and page components arrive with M0S-E09-01/02, the full locale files with M0S-E09-03.
export default definePluginWeb({
  widgets: {},
  pages: {},
  locales: {
    en: { widget: { title: "Tasks" }, page: { title: "Tasks" } },
    de: { widget: { title: "Aufgaben" }, page: { title: "Aufgaben" } },
  },
});
