// SPDX-License-Identifier: MIT
// Types for scripts/gen-plugin-registry.mjs (imported by the web shell's Vite config and tests).
export interface PluginManifest {
  id: string;
  type?: string[];
  runtime?: { kind?: string; web?: string };
  [key: string]: unknown;
}
export const OUT: string;
export function collectManifests(root?: string): PluginManifest[];
export function renderRegistry(manifests: PluginManifest[]): string;
export function writeRegistry(): boolean;
