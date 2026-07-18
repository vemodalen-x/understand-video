import { spawnSync } from "node:child_process";
import type { SpawnSyncOptionsWithStringEncoding } from "node:child_process";
import { VIDEO_PROFILE } from "./layout.js";

export interface ProcessResult {
  readonly status: number | null;
  readonly stdout: string;
  readonly stderr: string;
  readonly error?: Error;
}

export type ProcessRunner = (
  command: string,
  args: readonly string[],
  options: SpawnSyncOptionsWithStringEncoding,
) => ProcessResult;

const defaultRunner: ProcessRunner = (command, args, options) => {
  const result = spawnSync(command, [...args], options);
  return {
    status: result.status,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    ...(result.error === undefined ? {} : { error: result.error }),
  };
};

const SHELL_METACHARACTERS = /(?:[;&|`<>]|\$\(|\r|\n)/u;

export function assertSafeProcessArguments(
  command: string,
  args: readonly string[],
): void {
  if (command.length === 0 || SHELL_METACHARACTERS.test(command)) {
    throw new Error("unsafe process command");
  }
  for (const argument of args) {
    if (argument.includes("\0") || SHELL_METACHARACTERS.test(argument)) {
      throw new Error(`unsafe shell metacharacter in process argument: ${argument}`);
    }
  }
}

function runMediaTool(
  command: string,
  args: readonly string[],
  runner: ProcessRunner,
): ProcessResult {
  assertSafeProcessArguments(command, args);
  const result = runner(command, args, {
    encoding: "utf8",
    shell: false,
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error !== undefined) {
    throw new Error(`${command} could not start: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(`${command} failed with exit ${String(result.status)}: ${result.stderr}`);
  }
  return result;
}

export function runFfmpeg(
  args: readonly string[],
  options: { readonly binary?: string; readonly runner?: ProcessRunner } = {},
): ProcessResult {
  return runMediaTool(
    options.binary ?? "ffmpeg",
    args,
    options.runner ?? defaultRunner,
  );
}

export interface RawFfprobeStream {
  readonly codec_type?: string;
  readonly codec_name?: string;
  readonly width?: number;
  readonly height?: number;
  readonly avg_frame_rate?: string;
  readonly r_frame_rate?: string;
  readonly nb_frames?: string;
  readonly nb_read_frames?: string;
  readonly duration?: string;
  readonly [key: string]: unknown;
}

export interface RawFfprobeResult {
  readonly streams?: readonly RawFfprobeStream[];
  readonly format?: {
    readonly duration?: string;
    readonly format_name?: string;
    readonly [key: string]: unknown;
  };
  readonly [key: string]: unknown;
}

export function probeMedia(
  mediaPath: string,
  options: { readonly binary?: string; readonly runner?: ProcessRunner } = {},
): RawFfprobeResult {
  const result = runMediaTool(
    options.binary ?? "ffprobe",
    [
      "-v",
      "error",
      "-count_frames",
      "-show_streams",
      "-show_format",
      "-of",
      "json",
      mediaPath,
    ],
    options.runner ?? defaultRunner,
  );
  try {
    const parsed: unknown = JSON.parse(result.stdout);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("probe output is not an object");
    }
    return parsed as RawFfprobeResult;
  } catch (error) {
    throw new Error(
      `ffprobe returned undecodable metadata: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function parseRate(rate: string | undefined): number {
  if (rate === undefined) {
    return Number.NaN;
  }
  const [numeratorText, denominatorText = "1"] = rate.split("/");
  const numerator = Number(numeratorText);
  const denominator = Number(denominatorText);
  return denominator === 0 ? Number.NaN : numerator / denominator;
}

function parsePositiveNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : Number.NaN;
}

export interface MediaVerification {
  readonly ok: boolean;
  readonly errors: readonly string[];
  readonly durationMs: number;
  readonly framesPerSecond: number;
  readonly frameCount: number;
  readonly videoCodec: string | null;
  readonly audioCodec: string | null;
  readonly width: number | null;
  readonly height: number | null;
}

export function verifyMediaProbe(probe: RawFfprobeResult): MediaVerification {
  const errors: string[] = [];
  const streams = Array.isArray(probe.streams) ? probe.streams : [];
  const video = streams.find((stream) => stream.codec_type === "video");
  const audio = streams.find((stream) => stream.codec_type === "audio");

  if (video === undefined) {
    errors.push("MISSING_VIDEO_STREAM");
  }
  if (audio === undefined) {
    errors.push("MISSING_AUDIO_STREAM");
  }
  if (video !== undefined && video.codec_name !== VIDEO_PROFILE.videoCodec) {
    errors.push("VIDEO_CODEC_NOT_H264");
  }
  if (audio !== undefined && audio.codec_name !== VIDEO_PROFILE.audioCodec) {
    errors.push("AUDIO_CODEC_NOT_AAC");
  }

  const width = video?.width ?? null;
  const height = video?.height ?? null;
  if (width !== VIDEO_PROFILE.width || height !== VIDEO_PROFILE.height) {
    errors.push("INVALID_VIDEO_DIMENSIONS");
  }

  const averageRate = parseRate(video?.avg_frame_rate);
  const realRate = parseRate(video?.r_frame_rate);
  if (
    !Number.isFinite(averageRate) ||
    !Number.isFinite(realRate) ||
    Math.abs(averageRate - VIDEO_PROFILE.framesPerSecond) > 0.001 ||
    Math.abs(realRate - VIDEO_PROFILE.framesPerSecond) > 0.001 ||
    Math.abs(averageRate - realRate) > 0.001
  ) {
    errors.push("VIDEO_NOT_CONSTANT_30_FPS");
  }

  const frameCount = Number(video?.nb_read_frames ?? video?.nb_frames ?? 0);
  if (!Number.isFinite(frameCount) || frameCount <= 0) {
    errors.push("ZERO_VIDEO_FRAMES");
  }

  const durationSeconds = parsePositiveNumber(
    probe.format?.duration ?? video?.duration ?? audio?.duration,
  );
  const durationMs = durationSeconds * 1_000;
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    errors.push("INVALID_MEDIA_DURATION");
  } else if (durationMs >= VIDEO_PROFILE.maximumDurationMsExclusive) {
    errors.push("DURATION_NOT_STRICTLY_UNDER_180_SECONDS");
  }

  return {
    ok: errors.length === 0,
    errors,
    durationMs,
    framesPerSecond: averageRate,
    frameCount,
    videoCodec: video?.codec_name ?? null,
    audioCodec: audio?.codec_name ?? null,
    width,
    height,
  };
}

export function verifyMediaFile(
  mediaPath: string,
  options: { readonly binary?: string; readonly runner?: ProcessRunner } = {},
): MediaVerification {
  return verifyMediaProbe(probeMedia(mediaPath, options));
}

export interface RenderTestMediaOptions {
  readonly durationSeconds?: number;
  readonly ffmpegBinary?: string;
  readonly runner?: ProcessRunner;
}

/** Generates a short standards-conformant fixture without invoking a shell. */
export function renderStandardsTestMedia(
  outputPath: string,
  options: RenderTestMediaOptions = {},
): void {
  const durationSeconds = options.durationSeconds ?? 0.5;
  if (
    !Number.isFinite(durationSeconds) ||
    durationSeconds <= 0 ||
    durationSeconds >= 180
  ) {
    throw new RangeError("fixture media duration must be greater than zero and under 180 seconds");
  }
  runFfmpeg(
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-y",
      "-f",
      "lavfi",
      "-i",
      `color=c=0x08111f:s=1920x1080:r=30:d=${String(durationSeconds)}`,
      "-f",
      "lavfi",
      "-i",
      `sine=frequency=440:sample_rate=48000:duration=${String(durationSeconds)}`,
      "-shortest",
      "-c:v",
      "libx264",
      "-preset",
      "ultrafast",
      "-pix_fmt",
      "yuv420p",
      "-r",
      "30",
      "-c:a",
      "aac",
      "-b:a",
      "128k",
      "-movflags",
      "+faststart",
      outputPath,
    ],
    {
      ...(options.ffmpegBinary === undefined
        ? {}
        : { binary: options.ffmpegBinary }),
      ...(options.runner === undefined ? {} : { runner: options.runner }),
    },
  );
}
