import {
  afterAll,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import {
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  analyzePcm16,
  createFixtureNarration,
  requestSpeech,
  validatePcm16Audio,
  type SpeechInput,
  type SpeechProvider,
} from "../../packages/core/src/audio.js";
import {
  createCaptionCues,
  toSrt,
  toWebVtt,
  validateCaptionCues,
  wrapCaption,
} from "../../packages/core/src/captions.js";
import {
  CAPTION_BAND,
  CAPTION_STYLE,
  CONTENT_RECT,
  VIDEO_PROFILE,
  rectanglesIntersect,
  validateCaptionSafeLayout,
  verticalGap,
} from "../../packages/core/src/layout.js";
import {
  probeMedia,
  renderStandardsTestMedia,
  runFfmpeg,
  verifyMediaProbe,
  type ProcessRunner,
  type RawFfprobeResult,
} from "../../packages/core/src/media.js";
import { renderFrame } from "../../packages/core/src/renderer.js";
import { renderDeterministicSvg, type SvgScene } from "../../packages/core/src/svg.js";

function sinePcm16(
  amplitude: number,
  durationMs: number,
  sampleRate = 8_000,
): Uint8Array {
  const sampleCount = Math.round((durationMs * sampleRate) / 1_000);
  const buffer = Buffer.alloc(sampleCount * 2);
  for (let index = 0; index < sampleCount; index += 1) {
    const sample = Math.round(
      32_767 * amplitude * Math.sin((2 * Math.PI * 440 * index) / sampleRate),
    );
    buffer.writeInt16LE(Math.max(-32_768, Math.min(32_767, sample)), index * 2);
  }
  return buffer;
}

function silenceAndTonePcm16(sampleRate = 1_000): Uint8Array {
  const segments = [
    { durationMs: 600, amplitude: 0 },
    { durationMs: 500, amplitude: 0.25 },
    { durationMs: 1_300, amplitude: 0 },
    { durationMs: 500, amplitude: 0.25 },
    { durationMs: 600, amplitude: 0 },
  ];
  const samples: number[] = [];
  for (const segment of segments) {
    const count = Math.round((segment.durationMs * sampleRate) / 1_000);
    for (let index = 0; index < count; index += 1) {
      samples.push(Math.round(32_767 * segment.amplitude));
    }
  }
  const buffer = Buffer.alloc(samples.length * 2);
  samples.forEach((sample, index) => buffer.writeInt16LE(sample, index * 2));
  return buffer;
}

function captionPayload(sidecar: string): string {
  return sidecar
    .split(/\r?\n/u)
    .filter(
      (line) =>
        line.length > 0 &&
        line !== "WEBVTT" &&
        !/^\d+$/u.test(line) &&
        !/-->/u.test(line),
    )
    .join(" ")
    .replace(/\s+/gu, " ")
    .trim();
}

const representativeScene: SvgScene = {
  id: "tempo-boundary",
  kind: "architecture",
  eyebrow: "TEMPO · GOVERNED BUILD",
  title: "Evidence becomes bounded build authority",
  body: ["Evidence", "Assessment", "Human warrant", "MVP start"],
  burnedCaption: "TEMPO separates evidence from authority.",
  accent: "#6ee7d8",
};

describe("Understand Video narration, captions, rendering, and media", () => {
  let mediaDirectory = "";
  let validMediaPath = "";
  let realProbe: RawFfprobeResult;

  beforeAll(() => {
    mediaDirectory = mkdtempSync(join(tmpdir(), "understand-video-media-"));
    validMediaPath = join(mediaDirectory, "valid.mp4");
    renderStandardsTestMedia(validMediaPath, { durationSeconds: 0.5 });
    realProbe = probeMedia(validMediaPath);
  }, 30_000);

  afterAll(() => {
    if (mediaDirectory.length > 0) {
      rmSync(mediaDirectory, { recursive: true, force: true });
    }
  });

  it("UV-021 produces deterministic fixture narration for identical inputs", () => {
    const first = createFixtureNarration([
      "TEMPO starts with evidence.",
      "A warrant bounds implementation.",
    ]);
    const second = createFixtureNarration([
      "TEMPO starts with evidence.",
      "A warrant bounds implementation.",
    ]);
    expect(first).toStrictEqual(second);
    expect(first.textSha256).toMatch(/^[0-9a-f]{64}$/u);
  });

  it("UV-022 prevents a speech provider from receiving raw source content", async () => {
    const synthesize = vi.fn<SpeechProvider["synthesize"]>(
      async () => new Uint8Array([1, 2, 3]),
    );
    const provider: SpeechProvider = { synthesize };
    await requestSpeech(provider, {
      narration: "Approved explanation prose only.",
      providerId: "voice-provider",
      voiceId: "natural-en",
      mode: "fixture",
    });
    expect(synthesize).toHaveBeenCalledWith({
      text: "Approved explanation prose only.",
      voiceId: "natural-en",
    });
    expect(Object.keys(synthesize.mock.calls[0]?.[0] ?? {})).toStrictEqual([
      "text",
      "voiceId",
    ]);

    const malicious = {
      narration: "Approved prose.",
      providerId: "voice-provider",
      voiceId: "natural-en",
      mode: "fixture",
      rawSource: "SECRET=do-not-send",
    } as unknown as SpeechInput;
    await expect(requestSpeech(provider, malicious)).rejects.toThrow(
      /prohibited source-bearing fields/u,
    );
    expect(synthesize).toHaveBeenCalledTimes(1);
  });

  it("UV-023 requires an approved voice-sample checkpoint for production mode", async () => {
    const provider: SpeechProvider = {
      synthesize: vi.fn(async () => new Uint8Array([7])),
    };
    const base = {
      narration: "This is the approved production narration.",
      providerId: "natural-provider",
      voiceId: "voice-a",
      mode: "production" as const,
    };
    await expect(requestSpeech(provider, base)).rejects.toThrow(
      "VOICE_SAMPLE_APPROVAL_REQUIRED",
    );
    await expect(
      requestSpeech(provider, {
        ...base,
        approval: {
          providerId: "natural-provider",
          voiceId: "voice-a",
          sampleSha256: "a".repeat(64),
          approvedBy: "human:founder",
          approvedAt: "2026-07-19T00:00:00Z",
        },
      }),
    ).resolves.toEqual(new Uint8Array([7]));
  });

  it("UV-024 rejects narration clips containing digital clipping", () => {
    const clipped = Buffer.alloc(8_000 * 2);
    for (let offset = 0; offset < clipped.length; offset += 2) {
      clipped.writeInt16LE(32_767, offset);
    }
    const result = validatePcm16Audio(analyzePcm16(clipped, 8_000));
    expect(result.ok).toBe(false);
    expect(result.errors).toContain("DIGITAL_CLIPPING");
    expect(result.metrics.clippedSamples).toBeGreaterThan(0);
  });

  it("UV-025 rejects integrated loudness outside -18 through -14 LUFS", () => {
    const result = validatePcm16Audio(
      analyzePcm16(sinePcm16(0.02, 1_000), 8_000),
    );
    expect(result.metrics.integratedLufs).toBeLessThan(-18);
    expect(result.errors).toContain("LOUDNESS_OUT_OF_RANGE");
  });

  it("UV-026 rejects true peak above -1 dBTP", () => {
    const result = validatePcm16Audio(
      analyzePcm16(sinePcm16(0.95, 1_000), 8_000),
    );
    expect(result.metrics.truePeakDbtp).toBeGreaterThan(-1);
    expect(result.errors).toContain("TRUE_PEAK_TOO_HIGH");
  });

  it("UV-027 rejects excessive edge or internal silence", () => {
    const result = validatePcm16Audio(
      analyzePcm16(silenceAndTonePcm16(), 1_000),
    );
    expect(result.metrics.leadingSilenceMs).toBe(600);
    expect(result.metrics.trailingSilenceMs).toBe(600);
    expect(result.metrics.maximumInternalSilenceMs).toBe(1_300);
    expect(result.errors).toEqual(
      expect.arrayContaining([
        "EDGE_SILENCE_TOO_LONG",
        "INTERNAL_SILENCE_TOO_LONG",
      ]),
    );
  });

  it("UV-028 produces monotonic SRT cues within media duration", () => {
    const cues = createCaptionCues(
      "Evidence is observed before policy and a bounded warrant authorizes only the declared implementation scope.",
      250,
      8_000,
    );
    const validation = validateCaptionCues(cues, 8_000);
    expect(validation).toStrictEqual({ ok: true, errors: [] });
    expect(toSrt(cues)).toMatch(
      /1\n00:00:00,250 --> 00:00:\d{2},\d{3}/u,
    );
    expect(cues.at(-1)?.endMs).toBe(8_000);
  });

  it("UV-029 produces semantically equivalent WebVTT cues", () => {
    const cues = createCaptionCues(
      "The planner binds every explanation to a source location.",
      0,
      4_000,
    );
    const srt = toSrt(cues);
    const webVtt = toWebVtt(cues);
    expect(webVtt.startsWith("WEBVTT\n\n")).toBe(true);
    expect(captionPayload(webVtt)).toBe(captionPayload(srt));
  });

  it("UV-030 wraps captions to 42 characters, two lines, 52 px / 64 px", () => {
    const lines = wrapCaption(
      "A warrant limits task lane action path and the available build window.",
    );
    expect(lines.length).toBeLessThanOrEqual(2);
    expect(lines.every((line) => line.length <= 42)).toBe(true);
    expect(CAPTION_STYLE).toMatchObject({
      maximumLatinCharactersPerLine: 42,
      maximumLines: 2,
      fontSizePx: 52,
      lineHeightPx: 64,
    });
  });

  it("UV-031 reserves the 1920x1080 caption band in every visual mode", () => {
    expect(VIDEO_PROFILE).toMatchObject({ width: 1920, height: 1080 });
    expect(CAPTION_BAND).toStrictEqual({
      x: 96,
      y: 820,
      width: 1728,
      height: 188,
    });
    for (const kind of ["title", "architecture", "code", "summary"] as const) {
      const svg = renderDeterministicSvg({
        ...representativeScene,
        id: `scene-${kind}`,
        kind,
      });
      expect(svg).toContain('id="caption-reserved-band"');
      expect(svg).toContain('y="820"');
    }
  });

  it("UV-032 reports zero intersection and a 40px diagram-caption gap", () => {
    const diagram = {
      name: "claim-flow",
      kind: "diagram" as const,
      ...CONTENT_RECT,
    };
    const validation = validateCaptionSafeLayout([diagram]);
    expect(rectanglesIntersect(diagram, CAPTION_BAND)).toBe(false);
    expect(verticalGap(diagram, CAPTION_BAND)).toBe(40);
    expect(validation).toMatchObject({ ok: true, minimumGapPx: 40 });
  });

  it("UV-033 reports zero intersection and a 40px code-caption gap", () => {
    const code = {
      name: "source-panel",
      kind: "code" as const,
      x: 96,
      y: 330,
      width: 1728,
      height: 450,
    };
    const validation = validateCaptionSafeLayout([code]);
    expect(rectanglesIntersect(code, CAPTION_BAND)).toBe(false);
    expect(verticalGap(code, CAPTION_BAND)).toBe(40);
    expect(validation.errors).toHaveLength(0);
  });

  it("UV-034 renders identical deterministic SVG frames for identical inputs", () => {
    const first = renderDeterministicSvg(representativeScene);
    const second = renderDeterministicSvg({ ...representativeScene });
    expect(first).toBe(second);
    expect(first).toContain('width="1920" height="1080"');
    expect(first).not.toContain("undefined");
  });

  it("UV-035 falls back to SVG when Hyperframes is unavailable", () => {
    const result = renderFrame(representativeScene, {
      preferredRenderer: "hyperframes",
      hyperframes: {
        id: "hyperframes-test-adapter",
        isAvailable: () => false,
        renderSvg: () => {
          throw new Error("must not render");
        },
      },
    });
    expect(result).toMatchObject({
      renderer: "svg",
      rendererId: "understand-video-svg-v1",
      fallbackReason: "unavailable",
    });
    expect(result.svg).toBe(renderDeterministicSvg(representativeScene));
  });

  it("UV-036 invokes FFmpeg with argv and shell:false, rejecting injection", () => {
    const runner = vi.fn<ProcessRunner>(() => ({
      status: 0,
      stdout: "ffmpeg version fixture",
      stderr: "",
    }));
    runFfmpeg(["-version"], { runner });
    expect(runner).toHaveBeenCalledTimes(1);
    expect(runner.mock.calls[0]?.[1]).toStrictEqual(["-version"]);
    expect(runner.mock.calls[0]?.[2]).toMatchObject({ shell: false });
    expect(() =>
      runFfmpeg(["-i", "video.mp4; Remove-Item secrets"], { runner }),
    ).toThrow(/unsafe shell metacharacter/u);
    expect(runner).toHaveBeenCalledTimes(1);
  });

  it("UV-037 produces a real H.264 video stream and AAC audio stream", () => {
    const verification = verifyMediaProbe(realProbe);
    expect(verification.videoCodec).toBe("h264");
    expect(verification.audioCodec).toBe("aac");
    expect(verification.errors).not.toEqual(
      expect.arrayContaining(["VIDEO_CODEC_NOT_H264", "AUDIO_CODEC_NOT_AAC"]),
    );
  });

  it("UV-038 produces real 1920x1080 media at constant 30 fps", () => {
    const verification = verifyMediaProbe(probeMedia(validMediaPath));
    expect(verification).toMatchObject({
      ok: true,
      width: 1920,
      height: 1080,
      framesPerSecond: 30,
    });
    expect(verification.frameCount).toBeGreaterThan(0);
  });

  it("UV-039 rejects final duration greater than or equal to 180000ms", () => {
    const overLimit: RawFfprobeResult = {
      ...realProbe,
      format: { ...realProbe.format, duration: "180.000" },
    };
    const verification = verifyMediaProbe(overLimit);
    expect(verification.durationMs).toBe(180_000);
    expect(verification.errors).toContain(
      "DURATION_NOT_STRICTLY_UNDER_180_SECONDS",
    );
  });

  it("UV-040 rejects missing, undecodable, truncated, or zero-frame media", () => {
    expect(() => probeMedia(join(mediaDirectory, "missing.mp4"))).toThrow();

    const undecodableRunner: ProcessRunner = () => ({
      status: 0,
      stdout: "not-json",
      stderr: "",
    });
    expect(() =>
      probeMedia("undecodable.mp4", { runner: undecodableRunner }),
    ).toThrow(/undecodable metadata/u);

    const truncatedPath = join(mediaDirectory, "truncated.mp4");
    writeFileSync(truncatedPath, readFileSync(validMediaPath).subarray(0, 64));
    const truncatedVerification = verifyMediaProbe(probeMedia(truncatedPath));
    expect(truncatedVerification.ok).toBe(false);
    expect(truncatedVerification.errors).toEqual(
      expect.arrayContaining(["MISSING_VIDEO_STREAM", "ZERO_VIDEO_FRAMES"]),
    );

    const zeroFrame: RawFfprobeResult = {
      ...realProbe,
      streams: (realProbe.streams ?? []).map((stream) =>
        stream.codec_type === "video"
          ? { ...stream, nb_read_frames: "0", nb_frames: "0" }
          : stream,
      ),
    };
    expect(verifyMediaProbe(zeroFrame).errors).toContain("ZERO_VIDEO_FRAMES");
  });
});
