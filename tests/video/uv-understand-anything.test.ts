import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { loadUnderstandAnythingBundle } from "../../packages/core/src/understand-anything.js";

const bundlePath = resolve(".understand-video", "inputs", "tempo-4a73350");

describe("reviewed Understand-Anything bundle", () => {
  it.runIf(existsSync(bundlePath))("binds the real TEMPO graph and provenance", () => {
    const bundle = loadUnderstandAnythingBundle(bundlePath, {
      targetRepository: "https://github.com/vemodalen-x/TEMPO",
      targetCommit: "4a73350f6eefff80b11d862a5ac65b7194530442",
      upstreamRepository: "https://github.com/Egonex-AI/Understand-Anything",
      upstreamCommit: "b9ac6be178b2fbc68ae45456cd9a902bdcac6dac",
      hashes: {
        "knowledge-graph.json": "sha256:7162b4e024a8b191494bb16bb8413f6ff86180503c981edf1785faae3e04b416",
        "meta.json": "sha256:f8ee9e01c445787a630efca2b06d97beec2504530aeab424feed930369e82570",
        "fingerprints.json": "sha256:7e3c4edebcfaf0baf83f3d569aedc2163357f3cdbdab9259c900e67d98f22b84",
        "provenance.json": "sha256:17cf417c37b315c796204e0347239caa0628e9b8902fdac98089b918aaeba175",
        "config.json": "sha256:616d8b71db92f5937bc6a20a39187d7c998b32679a65f1c8a929671c82cbd069",
        "review.json": "sha256:a1fab96189f45299d5b732174c8ae0104d68c4efc85aced97934d87d975f0eeb",
      },
    });

    expect(bundle.nodeCount).toBe(211);
    expect(bundle.edgeCount).toBe(614);
    expect(bundle.layerCount).toBe(8);
    expect(bundle.tourCount).toBe(7);
    expect(bundle.fileCount).toBe(116);
  });
});
