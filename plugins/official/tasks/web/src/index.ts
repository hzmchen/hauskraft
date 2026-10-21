// SPDX-License-Identifier: MIT
// Tasks plugin web module (M0S-E09-01..03). The shell loads it through the build-time registry.
import { definePluginWeb } from "@hauskraft/sdk-ts";

import { prefetchTasks } from "./api";

import de from "./locales/de/tasks.json";
import en from "./locales/en/tasks.json";
import { TasksPage } from "./pages/TasksPage";
import { TasksWidget } from "./widgets/TasksWidget";

export const pluginId = "dev.hauskraft.tasks";

export default definePluginWeb({
  widgets: { "tasks.list": TasksWidget },
  pages: { TasksPage },
  locales: { en, de },
  prefetch: prefetchTasks,
});
