import { createHash } from "node:crypto";

export interface FixtureNarration {
  readonly mode: "fixture";
  readonly text: string;
  readonly textSha256: string;
}

export function createFixtureNarration(
  parts: string | readonly string[],
): FixtureNarration {
  const values = typeof parts === "string" ? [parts] : parts;
  const text = values
    .map((part) => part.replace(/\s+/gu, " ").trim())
    .filter(Boolean)
    .join(" ");
  if (text.length === 0) {
    throw new Error("fixture narration must not be empty");
  }
  return {
    mode: "fixture",
    text,
    textSha256: createHash("sha256").update(text, "utf8").digest("hex"),
  };
}

export interface VoiceSampleApproval {
  readonly providerId: string;
  readonly voiceId: string;
  readonly sampleSha256: string;
  readonly approvedBy: `human:${string}`;
  readonly approvedAt: string;
}

export interface SpeechInput {
  readonly narration: string;
  readonly providerId: string;
  readonly voiceId: string;
  readonly mode: "fixture" | "production";
  readonly approval?: VoiceSampleApproval;
}

export interface SpeechProviderRequest {
  readonly text: string;
  readonly voiceId: string;
}

export interface SpeechProvider {
  synthesize(request: SpeechProviderRequest): Promise<Uint8Array>;
}

const SPEECH_INPUT_KEYS = new Set([
  "narration",
  "providerId",
  "voiceId",
  "mode",
  "approval",
]);

function validateSpeechInputShape(input: SpeechInput): void {
  const unexpected = Object.keys(input).filter((key) => !SPEECH_INPUT_KEYS.has(key));
  if (unexpected.length > 0) {
    throw new Error(
      `speech input contains prohibited source-bearing fields: ${unexpected.join(", ")}`,
    );
  }
  if (input.narration.trim().length === 0) {
    throw new Error("approved narration must not be empty");
  }
}

export function assertVoiceSampleApproved(input: SpeechInput): void {
  if (input.mode !== "production") {
    return;
  }
  const approval = input.approval;
  if (
    approval === undefined ||
    approval.providerId !== input.providerId ||
    approval.voiceId !== input.voiceId ||
    !/^human:.+/u.test(approval.approvedBy) ||
    !/^[0-9a-f]{64}$/u.test(approval.sampleSha256) ||
    !Number.isFinite(Date.parse(approval.approvedAt))
  ) {
    throw new Error("VOICE_SAMPLE_APPROVAL_REQUIRED");
  }
}

/**
 * The provider receives a fresh allow-listed object containing approved prose
 * only. Runtime extra fields (for example rawSource or repositoryText) fail
 * before a provider method can be called.
 */
export async function requestSpeech(
  provider: SpeechProvider,
  input: SpeechInput,
): Promise<Uint8Array> {
  validateSpeechInputShape(input);
  assertVoiceSampleApproved(input);
  return provider.synthesize({ text: input.narration, voiceId: input.voiceId });
}

export interface Pcm16Metrics {
  readonly sampleRate: number;
  readonly channels: number;
  readonly durationMs: number;
  readonly integratedLufs: number;
  readonly truePeakDbtp: number;
  readonly clippedSamples: number;
  readonly leadingSilenceMs: number;
  readonly trailingSilenceMs: number;
  readonly maximumInternalSilenceMs: number;
}

export interface AudioValidation {
  readonly ok: boolean;
  readonly errors: readonly string[];
  readonly metrics: Pcm16Metrics;
}

function decibels(value: number): number {
  return value <= 0 ? Number.NEGATIVE_INFINITY : 20 * Math.log10(value);
}

export function analyzePcm16(
  bytes: Uint8Array,
  sampleRate: number,
  channels = 1,
  silenceThresholdDbfs = -50,
): Pcm16Metrics {
  if (!Number.isInteger(sampleRate) || sampleRate <= 0) {
    throw new RangeError("sample rate must be a positive integer");
  }
  if (!Number.isInteger(channels) || channels <= 0) {
    throw new RangeError("channel count must be a positive integer");
  }
  if (bytes.byteLength === 0 || bytes.byteLength % (2 * channels) !== 0) {
    throw new Error("PCM16 data must contain complete, interleaved frames");
  }

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const sampleCount = bytes.byteLength / 2;
  const frameCount = sampleCount / channels;
  const silentFrames: boolean[] = new Array(frameCount);
  const silenceThreshold = 10 ** (silenceThresholdDbfs / 20);
  let peak = 0;
  let sumSquares = 0;
  let clippedSamples = 0;

  for (let frame = 0; frame < frameCount; frame += 1) {
    let framePeak = 0;
    for (let channel = 0; channel < channels; channel += 1) {
      const integer = view.getInt16((frame * channels + channel) * 2, true);
      const magnitude = Math.abs(integer);
      if (magnitude >= 32_767) {
        clippedSamples += 1;
      }
      const normalized = magnitude / 32_768;
      framePeak = Math.max(framePeak, normalized);
      peak = Math.max(peak, normalized);
      sumSquares += normalized * normalized;
    }
    silentFrames[frame] = framePeak <= silenceThreshold;
  }

  let leadingFrames = 0;
  while (leadingFrames < frameCount && silentFrames[leadingFrames]) {
    leadingFrames += 1;
  }
  let trailingFrames = 0;
  while (
    trailingFrames < frameCount - leadingFrames &&
    silentFrames[frameCount - trailingFrames - 1]
  ) {
    trailingFrames += 1;
  }

  let maximumInternalFrames = 0;
  let currentSilentFrames = 0;
  const internalEnd = frameCount - trailingFrames;
  for (let frame = leadingFrames; frame < internalEnd; frame += 1) {
    if (silentFrames[frame]) {
      currentSilentFrames += 1;
      maximumInternalFrames = Math.max(maximumInternalFrames, currentSilentFrames);
    } else {
      currentSilentFrames = 0;
    }
  }

  const meanSquare = sumSquares / sampleCount;
  const frameToMilliseconds = (frames: number): number =>
    (frames * 1_000) / sampleRate;
  return {
    sampleRate,
    channels,
    durationMs: frameToMilliseconds(frameCount),
    integratedLufs:
      meanSquare <= 0
        ? Number.NEGATIVE_INFINITY
        : -0.691 + 10 * Math.log10(meanSquare),
    truePeakDbtp: decibels(peak),
    clippedSamples,
    leadingSilenceMs: frameToMilliseconds(leadingFrames),
    trailingSilenceMs: frameToMilliseconds(trailingFrames),
    maximumInternalSilenceMs: frameToMilliseconds(maximumInternalFrames),
  };
}

export function validatePcm16Audio(metrics: Pcm16Metrics): AudioValidation {
  const errors: string[] = [];
  if (metrics.clippedSamples !== 0) {
    errors.push("DIGITAL_CLIPPING");
  }
  if (metrics.integratedLufs < -18 || metrics.integratedLufs > -14) {
    errors.push("LOUDNESS_OUT_OF_RANGE");
  }
  if (metrics.truePeakDbtp > -1) {
    errors.push("TRUE_PEAK_TOO_HIGH");
  }
  if (metrics.leadingSilenceMs > 500 || metrics.trailingSilenceMs > 500) {
    errors.push("EDGE_SILENCE_TOO_LONG");
  }
  if (metrics.maximumInternalSilenceMs > 1_200) {
    errors.push("INTERNAL_SILENCE_TOO_LONG");
  }
  return { ok: errors.length === 0, errors, metrics };
}

