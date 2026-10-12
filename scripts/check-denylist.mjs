#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Fail if a pnpm lockfile pins a known-compromised package version (M0S-E02-05).
//
//   node scripts/check-denylist.mjs [lockfile]      (default: pnpm-lock.yaml)
//
// Exit codes: 0 clean, 1 denylisted versions found (all are printed), 2 usage error.
// No dependencies: the lockfile is scanned as text, which covers every pnpm lockfile section
// (importers, packages, snapshots) and peer-suffixed keys such as `pkg@1.2.3(react@19.0.0)`.
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

// GHSA-g7cv-rxg3-hmpx: the May 11, 2026 TanStack npm compromise.
export const DENYLIST = {
  "@tanstack/react-router": ["1.169.5", "1.169.8"],
  "@tanstack/router-plugin": ["1.167.38", "1.167.41"],
};

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");

export function findDenylisted(text) {
  const hits = new Set();
  for (const [name, versions] of Object.entries(DENYLIST)) {
    for (const version of versions) {
      // `name@version` as a key, or `name:` … `version: x` in an importer block.
      const key = new RegExp(`(^|[\\s'"/])${escape(name)}@${escape(version)}(?![0-9A-Za-z.+-])`, "m");
      const importer = new RegExp(
        `^\\s+'?${escape(name)}'?:\\s*\\n(?:\\s+specifier:.*\\n)?\\s+version:\\s*'?${escape(version)}(?![0-9A-Za-z.+-])`,
        "m",
      );
      if (key.test(text) || importer.test(text)) hits.add(`${name}@${version}`);
    }
  }
  return [...hits].sort();
}

function main(argv) {
  const lockfile = resolve(argv[0] ?? "pnpm-lock.yaml");
  if (!existsSync(lockfile)) {
    console.error(`check-denylist: lockfile not found: ${lockfile}`);
    return 2;
  }
  const hits = findDenylisted(readFileSync(lockfile, "utf8"));
  if (hits.length === 0) {
    console.log(`check-denylist: ${lockfile} is clean`);
    return 0;
  }
  for (const hit of hits) console.log(`DENYLISTED ${hit}`);
  console.error(`check-denylist: ${hits.length} compromised version(s) in ${lockfile}; pin a safe version and relock.`);
  return 1;
}

process.exitCode = main(process.argv.slice(2));
