// SPDX-License-Identifier: MIT
// Tasks plugin web module (M0S-E09-01..03). The shell loads it through the build-time registry.
import { definePluginWeb } from "@hearthos/sdk-ts";

import { de, en } from "./locales";
import { TasksWidget } from "./widgets/TasksWidget";

export const pluginId = "org.hearthos.tasks";

// The page component arrives with M0S-E09-02.
export default definePluginWeb({
  widgets: { "tasks.list": TasksWidget },
  pages: {},
  locales: { en, de },
});
