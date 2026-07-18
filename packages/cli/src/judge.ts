import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

import {
  bindArtifact,
  createProductReceipt,
  runCommand,
  verifyProductReceipt,
  type ArtifactBindingName,
  type CommandResult,
} from "../../governance-adapter/src/index.js";
import type { PipelineContext, PipelineHandlers, StageResult } from "./orchestrator.js";

const FIXTURE_REVISION = "1111111111111111111111111111111111111111";
const TEMPO_BASELINE_COMMIT = "4afc6a3f5ceba0240f7fdd2eece96241253d6e60";

function writeUtf8(path: string, value: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, value, "utf8");
}

function writeJson(path: string, value: unknown): void {
  writeUtf8(path, `${JSON.stringify(value, null, 2)}\n`);
}

function requireTool(command: string, args: readonly string[], purpose: string): CommandResult {
  const result = runCommand(command, args);
  if (result.error !== undefined || result.status !== 0) {
    throw new Error(`${purpose} unavailable: ${result.stderr.trim() || result.error?.message || "unknown error"}`);
  }
  return result;
}

function paths(workspace: string) {
  const root = resolve(workspace);
  return {
    root,
    fixtureSource: join(root, "fixture-repo", "src", "gate.ts"),
    snapshot: join(root, "snapshot.json"),
    claims: join(root, "claims.json"),
    storyboard: join(root, "storyboard.json"),
    narration: join(root, "narration.txt"),
    captions: join(root, "captions.json"),
    srt: join(root, "captions.srt"),
    vtt: join(root, "captions.vtt"),
    media: join(root, "demo.mp4"),
    receipt: join(root, "receipt.json"),
  };
}

function doctor(): StageResult {
  if (Number.parseInt(process.versions.node.split(".")[0] ?? "0", 10) < 22) {
    throw new Error("Node.js 22 or newer is required");
  }
  requireTool("git", ["--version"], "Git");
  requireTool("ffmpeg", ["-version"], "FFmpeg");
  requireTool("ffprobe", ["-version"], "FFprobe");
  return { ok: true, summary: "Node, Git, FFmpeg, and FFprobe are available" };
}

function inspect(context: PipelineContext): StageResult {
  if (!context.offline) {
    throw new Error("The judge fixture is intentionally offline-only");
  }
  const output = paths(context.workspace);
  const source = [
    "export function authorize(hasWarrant: boolean): boolean {",
    "  return hasWarrant;",
    "}",
    "",
  ].join("\n");
  writeUtf8(output.fixtureSource, source);
  writeJson(output.snapshot, {
    schemaVersion: "understand-video-snapshot/v1",
    repository: "fixture://governed-framework",
    revision: FIXTURE_REVISION,
    strict: true,
    authoritative: false,
  });
  writeJson(output.claims, {
    schemaVersion: "understand-video-claims/v1",
    claims: [
      {
        id: "C-FIXTURE-001",
        text: "The synthetic gate returns its explicit warrant input.",
        source: { path: "src/gate.ts", startLine: 1, endLine: 3 },
      },
    ],
    authoritative: false,
  });
  return { ok: true, summary: "synthetic snapshot and one grounded claim inspected", artifactPath: output.snapshot };
}

function plan(context: PipelineContext): StageResult {
  const output = paths(context.workspace);
  readFileSync(output.snapshot, "utf8");
  readFileSync(output.claims, "utf8");
  writeJson(output.storyboard, {
    schemaVersion: "understand-video-storyboard/v1",
    profile: "judge-fixture",
    durationMs: 2000,
    scenes: [
      {
        id: "fixture-gate",
        type: "source-callout",
        claimIds: ["C-FIXTURE-001"],
        startMs: 0,
        endMs: 2000,
      },
    ],
    plannerMode: "fixture",
    authoritative: false,
  });
  return { ok: true, summary: "credential-free fixture storyboard planned", artifactPath: output.storyboard };
}

function render(context: PipelineContext): StageResult {
  const output = paths(context.workspace);
  readFileSync(output.storyboard, "utf8");
  const narration = "Fixture narration. A warrant input controls this synthetic gate.\n";
  const srt = "1\n00:00:00,000 --> 00:00:02,000\nFixture mode: synthetic gate.\n";
  const vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nFixture mode: synthetic gate.\n";
  writeUtf8(output.narration, narration);
  writeUtf8(output.srt, srt);
  writeUtf8(output.vtt, vtt);
  writeJson(output.captions, { srt, vtt, mode: "sidecar", authoritative: false });

  mkdirSync(output.root, { recursive: true });
  const ffmpeg = requireTool(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-y",
      "-f",
      "lavfi",
      "-i",
      "color=c=0x0b1020:s=1920x1080:r=30:d=2",
      "-f",
      "lavfi",
      "-i",
      "sine=frequency=440:sample_rate=48000:duration=2",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-r",
      "30",
      "-c:a",
      "aac",
      "-shortest",
      output.media,
    ],
    "fixture render",
  );
  if (ffmpeg.status !== 0) {
    throw new Error("Fixture render failed");
  }
  return { ok: true, summary: "deterministic fixture inputs rendered through FFmpeg argv", artifactPath: output.media };
}

interface ProbeOutput {
  readonly streams?: readonly {
    readonly codec_name?: string;
    readonly codec_type?: string;
    readonly width?: number;
    readonly height?: number;
    readonly avg_frame_rate?: string;
  }[];
  readonly format?: { readonly duration?: string };
}

function verify(context: PipelineContext): StageResult {
  const output = paths(context.workspace);
  const probeResult = requireTool(
    "ffprobe",
    ["-v", "error", "-show_streams", "-show_format", "-of", "json", output.media],
    "fixture media verification",
  );
  const probe = JSON.parse(probeResult.stdout) as ProbeOutput;
  const video = probe.streams?.find((stream) => stream.codec_type === "video");
  const audio = probe.streams?.find((stream) => stream.codec_type === "audio");
  const durationSeconds = Number.parseFloat(probe.format?.duration ?? "NaN");
  if (
    video?.codec_name !== "h264" ||
    audio?.codec_name !== "aac" ||
    video.width !== 1920 ||
    video.height !== 1080 ||
    video.avg_frame_rate !== "30/1" ||
    !Number.isFinite(durationSeconds) ||
    durationSeconds <= 0 ||
    durationSeconds >= 180
  ) {
    throw new Error("Fixture media failed codec, canvas, frame-rate, or duration checks");
  }

  const artifactPaths: Record<ArtifactBindingName, string> = {
    snapshot: output.snapshot,
    claims: output.claims,
    storyboard: output.storyboard,
    narration: output.narration,
    captions: output.captions,
    media: output.media,
  };
  const artifacts = Object.fromEntries(
    Object.entries(artifactPaths).map(([name, path]) => [name, bindArtifact(path, readFileSync(path))]),
  ) as Record<ArtifactBindingName, ReturnType<typeof bindArtifact>>;
  const receipt = createProductReceipt({
    generatedAt: new Date().toISOString(),
    target: { repository: "fixture://governed-framework", revision: FIXTURE_REVISION },
    artifacts,
    provider: { plannerMode: "fixture", voiceMode: "fixture", model: null, requestId: null },
    governance: {
      mode: "fixture",
      authoritative: false,
      baselineCommit: TEMPO_BASELINE_COMMIT,
      assessmentId: null,
      assessmentHash: null,
      warrantId: null,
      warrantExpiresAt: null,
      taskId: null,
      lane: null,
      action: null,
      path: null,
      startEventId: null,
      startEventHash: null,
    },
    verification: {
      passed: true,
      profile: "judge-fixture",
      checks: ["source-grounding", "h264-aac", "1920x1080", "30fps", "duration-under-180s", "receipt"],
    },
  });
  verifyProductReceipt(receipt, (name) => readFileSync(artifactPaths[name]));
  writeJson(output.receipt, receipt);
  return { ok: true, summary: "media and all six receipt bindings verified; authoritative:false", artifactPath: output.receipt };
}

export function createJudgeHandlers(): PipelineHandlers {
  return { doctor, inspect, plan, render, verify };
}
