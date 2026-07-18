import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

import { renderFrame } from "../../core/src/renderer.js";

const outputDirectory = resolve(
  ".understand-video",
  "runs",
  "tempo-4afc6a3",
  "checkpoints",
);
mkdirSync(outputDirectory, { recursive: true });

const frame = renderFrame({
  id: "voice-sample",
  kind: "architecture",
  eyebrow: "VOICE + CAPTION CHECKPOINT",
  title: "A source-grounded walkthrough",
  body: [
    "Pinned commit",
    "Validated graph",
    "Grounded claims",
    "Verified video",
  ],
  burnedCaption: "Pinned commit. Source-linked explanation.",
  accent: "#63e6be",
});

writeFileSync(resolve(outputDirectory, "voice-sample.svg"), frame.svg, "utf8");
process.stdout.write(
  `${JSON.stringify({ renderer: frame.renderer, rendererId: frame.rendererId })}\n`,
);
