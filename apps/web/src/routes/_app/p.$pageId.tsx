// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

import { PluginPage } from "../../plugins/PluginPage";
import { useWebPlugins } from "../../plugins/usePlugins";

export const Route = createFileRoute("/_app/p/$pageId")({ component: PluginPageRoute });

function PluginPageRoute() {
  const { pageId } = Route.useParams();
  const { plugins } = useWebPlugins();
  return <PluginPage pageId={pageId} plugins={plugins} />;
}
