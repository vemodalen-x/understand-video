import { readFileSync } from "node:fs";

import { describe, expect, test } from "vitest";

import { renderFrame } from "../../packages/core/src/renderer.js";
import { CAPTION_BAND, CAPTION_STYLE, CONTENT_RECT, verticalGap } from "../../packages/core/src/layout.js";

describe("Devpost render delivery contract", () => {
  test("UV-053 renders explicit readable typography and a dedicated caption band", () => {
    const frame = renderFrame({
      id: "SCENE-TEST",
      kind: "code",
      title: "Readable source-grounded explanation",
      code: ["python bin/tempo demo", "JUDGE_DEMO_PASSED"],
      burnedCaption: "Captions stay below code and diagrams.",
      accent: "#6ee7d8",
    });

    expect(frame.svg).toContain("font-size:68px");
    expect(frame.svg).toContain(`font-size:${CAPTION_STYLE.fontSizePx}px`);
    expect(frame.svg).not.toMatch(/(?:^|[;}])font:/u);
    expect(frame.svg).toContain('id="caption-reserved-band"');
    expect(frame.svg).toContain(`y="${CAPTION_BAND.y}"`);
    expect(verticalGap(CONTENT_RECT, CAPTION_BAND)).toBe(CAPTION_STYLE.minimumContentGapPx);
  });

  test("UV-054 records the natural-voice candidate without granting publication authority", () => {
    const provider = JSON.parse(
      readFileSync("samples/governed-framework-video/voice-provider.json", "utf8"),
    ) as Record<string, unknown>;

    expect(provider["voice_id"]).toBe("en-US-BrianMultilingualNeural");
    expect(provider["voice_sample_checkpoint"]).toBe(
      "development_quality_check_passed_publication_review_pending",
    );
    expect(provider["publication_authorized"]).toBe(false);
    expect(provider["raw_source_sent"]).toBe(false);
  });
});
