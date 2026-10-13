// SPDX-License-Identifier: MIT
// Tasks plugin web module (M0S-E09-01..03). The shell loads it through the build-time registry.
import { definePluginWeb } from "@hearthos/sdk-ts";

import de from "./locales/de/tasks.json";
import en from "./locales/en/tasks.json";
import { TasksPage } from "./pages/TasksPage";
import { TasksWidget } from "./widgets/TasksWidget";

export const pluginId = "org.hearthos.tasks";

export default definePluginWeb({
  widgets: { "tasks.list": TasksWidget },
  pages: { TasksPage },
  locales: { en, de },
});
