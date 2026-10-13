// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { PluginPage } from "../../plugins/PluginPage";
import { useWebPlugins } from "../../plugins/usePlugins";

import { stringSearch } from "../../shell/RouterHost";

// Plugin pages keep their own state in the URL; the shell passes string values through and the page
// validates what it reads (useHost().search).
export const Route = createFileRoute("/_app/p/$pageId")({
  validateSearch: (search: Record<string, unknown>) => stringSearch(search),
  component: PluginPageRoute,
});

function PluginPageRoute() {
  const { pageId } = Route.useParams();
  const { plugins } = useWebPlugins();
  return <PluginPage pageId={pageId} plugins={plugins} />;
}
