import { chmodSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

import { build } from "esbuild";

const outputDirectory = resolve("submission", "judge-bundle");
mkdirSync(outputDirectory, { recursive: true });

await build({
  entryPoints: [resolve("packages", "cli", "src", "judge-entry.ts")],
  outfile: resolve(outputDirectory, "understand-video-demo.mjs"),
  bundle: true,
  platform: "node",
  target: "node22",
  format: "esm",
  sourcemap: false,
  legalComments: "none",
  banner: { js: "#!/usr/bin/env node" },
});

try {
  chmodSync(resolve(outputDirectory, "understand-video-demo.mjs"), 0o755);
} catch {
  // Windows does not rely on POSIX mode bits; run.ps1 invokes Node explicitly.
}

process.stdout.write(`Judge bundle built at ${outputDirectory}\n`);
