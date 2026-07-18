import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { loadUnderstandAnythingBundle } from "../../packages/core/src/understand-anything.js";

const bundlePath = resolve(".understand-video", "inputs", "tempo-4afc6a3");

describe("reviewed Understand-Anything bundle", () => {
  it.runIf(existsSync(bundlePath))("binds the real TEMPO graph and provenance", () => {
    const bundle = loadUnderstandAnythingBundle(bundlePath, {
      targetRepository: "https://github.com/vemodalen-x/TEMPO",
      targetCommit: "4afc6a3f5ceba0240f7fdd2eece96241253d6e60",
      upstreamRepository: "https://github.com/Egonex-AI/Understand-Anything",
      upstreamCommit: "b9ac6be178b2fbc68ae45456cd9a902bdcac6dac",
      hashes: {
        "knowledge-graph.json": "sha256:39167ad858811f5b7109572bbf9ba8ed63f0ed9c31cbf82301c4cb0cc14fce99",
        "meta.json": "sha256:fb02c3f8923405bec73d0044420e378c08838990b91376af1a681914226e7509",
        "fingerprints.json": "sha256:4e9197bb12cada7cfb2bed56705ab53a85ac31f19a2d704ac4bd5e3cc15aa461",
        "provenance.json": "sha256:b24d051058faf2571b0d8ca130b14f1b7c020fb91e43003ee0dc08749540c906",
        "config.json": "sha256:cccb1d2ad9ba819dd7bb50824e575d18a531857d3039d0224f2ca200631d4f9e",
        "review.json": "sha256:3f78fb1da47dc32a64592ee49d8c56b2ca0499d95aa473467ab4974d2422149c",
      },
    });

    expect(bundle.nodeCount).toBe(188);
    expect(bundle.edgeCount).toBe(566);
    expect(bundle.layerCount).toBe(8);
    expect(bundle.tourCount).toBe(7);
    expect(bundle.fileCount).toBe(97);
  });
});
