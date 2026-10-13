// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({ component: Home });

// Placeholder until the shell (M0S-E08-05) redirects to /today.
function Home() {
  return <h1 className="text-2xl font-bold">HearthOS</h1>;
}
