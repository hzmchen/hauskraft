// SPDX-License-Identifier: MIT
import { defineConfig } from "vitest/config";

// RuleTester registers its cases with the global describe/it.
export default defineConfig({ test: { globals: true, include: ["*.test.js"] } });
