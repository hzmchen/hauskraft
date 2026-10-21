// SPDX-License-Identifier: AGPL-3.0-or-later
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { renderRegistry } from "../../../../scripts/gen-plugin-registry.mjs";

const manifest = (id: string, extra: Record<string, unknown>) => ({
  id,
  type: ["widget"],
  runtime: { kind: "inprocess" },
  ...extra,
});

describe("plugin registry generation", () => {
  it("lists web plugins by id with a dynamic import of their package, sorted", () => {
    const out = renderRegistry([
      manifest("org.example.zeta", { runtime: { kind: "inprocess", web: "@example/zeta" } }),
      manifest("dev.hauskraft.tasks", { runtime: { kind: "inprocess", web: "@hauskraft/plugin-tasks" } }),
    ]);
    expect(out).toContain(`"dev.hauskraft.tasks": () => import("@hauskraft/plugin-tasks"),`);
    expect(out.indexOf("org.example.zeta")).toBeLessThan(out.indexOf("dev.hauskraft.tasks"));
    expect(out).toMatch(/^\/\/ GENERATED/m);
  });

  it("skips themes and plugins without web code", () => {
    const out = renderRegistry([
      manifest("dev.hauskraft.theme.paper", { type: ["theme"], runtime: { kind: "declarative", web: "@x/y" } }),
      manifest("org.example.headless", {}),
    ]);
    expect(out).not.toContain("dev.hauskraft.theme.paper");
    expect(out).not.toContain("org.example.headless");
  });

  it("the committed registry is current", async () => {
    const { collectManifests } = await import("../../../../scripts/gen-plugin-registry.mjs");
    const committed = readFileSync(resolve(__dirname, "registry.gen.ts"), "utf8");
    expect(committed).toBe(renderRegistry(collectManifests()));
  });
});
