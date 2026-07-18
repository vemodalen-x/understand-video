#!/usr/bin/env node

// packages/cli/src/main.ts
import { resolve as resolve2 } from "node:path";
import { fileURLToPath } from "node:url";

// packages/cli/src/judge.ts
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

// packages/governance-adapter/src/adapter.ts
import { spawnSync } from "node:child_process";

// packages/governance-adapter/src/canonical.ts
import { createHash } from "node:crypto";
function normalize(value, path) {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError(`Non-finite number at ${path}`);
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((entry, index) => normalize(entry, `${path}[${index}]`));
  }
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      const entry = value[key];
      if (entry === void 0) {
        throw new TypeError(`Undefined value at ${path}.${key}`);
      }
      result[key] = normalize(entry, `${path}.${key}`);
    }
    return result;
  }
  throw new TypeError(`Unsupported canonical value at ${path}`);
}
function canonicalJson(value) {
  return JSON.stringify(normalize(value, "$"));
}
function sha256Bytes(value) {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}
function canonicalHash(value) {
  return sha256Bytes(canonicalJson(value));
}
function isSha256(value) {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
}

// packages/governance-adapter/src/errors.ts
var GovernanceError = class extends Error {
  code;
  constructor(code, message) {
    super(message);
    this.name = "GovernanceError";
    this.code = code;
  }
};

// packages/governance-adapter/src/adapter.ts
var runCommand = (command, args, options = {}) => {
  const result = spawnSync(command, [...args], {
    cwd: options.cwd,
    encoding: "utf8",
    shell: false,
    windowsHide: true
  });
  const response = {
    status: result.status,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? ""
  };
  if (result.error !== void 0) {
    return { ...response, error: result.error };
  }
  return response;
};

// packages/governance-adapter/src/receipt.ts
var REQUIRED_ARTIFACT_BINDINGS = [
  "snapshot",
  "claims",
  "storyboard",
  "narration",
  "captions",
  "media"
];
function validateBindings(artifacts) {
  for (const name of REQUIRED_ARTIFACT_BINDINGS) {
    const binding = artifacts[name];
    if (binding === void 0) {
      throw new GovernanceError("RECEIPT_INVALID", `Missing receipt binding: ${name}`);
    }
    if (!isSha256(binding.sha256)) {
      throw new GovernanceError("RECEIPT_INVALID", `Invalid SHA-256 binding: ${name}`);
    }
    if (!Number.isSafeInteger(binding.sizeBytes) || binding.sizeBytes < 0) {
      throw new GovernanceError("RECEIPT_INVALID", `Invalid size binding: ${name}`);
    }
    if (binding.path.length === 0 || binding.path.includes("\0")) {
      throw new GovernanceError("RECEIPT_INVALID", `Invalid artifact path: ${name}`);
    }
  }
}
function createProductReceipt(input) {
  validateBindings(input.artifacts);
  const usesFixture = input.governance.mode === "fixture" || input.provider.plannerMode === "fixture" || input.provider.voiceMode === "fixture";
  const body = {
    schemaVersion: "understand-video-receipt/v1",
    generatedAt: input.generatedAt,
    authoritative: !usesFixture && input.governance.authoritative,
    target: input.target,
    artifacts: input.artifacts,
    provider: input.provider,
    governance: input.governance,
    verification: input.verification
  };
  return { ...body, receiptHash: canonicalHash(body) };
}
function verifyProductReceipt(receipt, resolveArtifact) {
  const { receiptHash, ...body } = receipt;
  validateBindings(body.artifacts);
  if (!isSha256(receiptHash) || canonicalHash(body) !== receiptHash) {
    throw new GovernanceError("RECEIPT_TAMPERED", "Canonical receipt hash does not match its body");
  }
  const usesFixture = body.governance.mode === "fixture" || body.provider.plannerMode === "fixture" || body.provider.voiceMode === "fixture";
  if (usesFixture && body.authoritative) {
    throw new GovernanceError("RECEIPT_INVALID", "Fixture receipts must be authoritative:false");
  }
  if (resolveArtifact !== void 0) {
    for (const name of REQUIRED_ARTIFACT_BINDINGS) {
      const binding = body.artifacts[name];
      const bytes = resolveArtifact(name, binding.path);
      if (sha256Bytes(bytes) !== binding.sha256) {
        throw new GovernanceError("BOUND_ARTIFACT_TAMPERED", `Bound artifact changed: ${name}`);
      }
      const byteLength = typeof bytes === "string" ? Buffer.byteLength(bytes) : bytes.byteLength;
      if (byteLength !== binding.sizeBytes) {
        throw new GovernanceError("BOUND_ARTIFACT_TAMPERED", `Bound artifact size changed: ${name}`);
      }
    }
  }
}
function bindArtifact(path, bytes) {
  return {
    path,
    sha256: sha256Bytes(bytes),
    sizeBytes: typeof bytes === "string" ? Buffer.byteLength(bytes) : bytes.byteLength
  };
}

// packages/cli/src/judge.ts
var FIXTURE_REVISION = "1111111111111111111111111111111111111111";
var TEMPO_BASELINE_COMMIT = "4a73350f6eefff80b11d862a5ac65b7194530442";
function writeUtf8(path, value) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, value, "utf8");
}
function writeJson(path, value) {
  writeUtf8(path, `${JSON.stringify(value, null, 2)}
`);
}
function requireTool(command, args, purpose) {
  const result = runCommand(command, args);
  if (result.error !== void 0 || result.status !== 0) {
    throw new Error(`${purpose} unavailable: ${result.stderr.trim() || result.error?.message || "unknown error"}`);
  }
  return result;
}
function paths(workspace) {
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
    receipt: join(root, "receipt.json")
  };
}
function doctor() {
  if (Number.parseInt(process.versions.node.split(".")[0] ?? "0", 10) < 22) {
    throw new Error("Node.js 22 or newer is required");
  }
  requireTool("git", ["--version"], "Git");
  requireTool("ffmpeg", ["-version"], "FFmpeg");
  requireTool("ffprobe", ["-version"], "FFprobe");
  return { ok: true, summary: "Node, Git, FFmpeg, and FFprobe are available" };
}
function inspect(context) {
  if (!context.offline) {
    throw new Error("The judge fixture is intentionally offline-only");
  }
  const output = paths(context.workspace);
  const source = [
    "export function authorize(hasWarrant: boolean): boolean {",
    "  return hasWarrant;",
    "}",
    ""
  ].join("\n");
  writeUtf8(output.fixtureSource, source);
  writeJson(output.snapshot, {
    schemaVersion: "understand-video-snapshot/v1",
    repository: "fixture://governed-framework",
    revision: FIXTURE_REVISION,
    strict: true,
    authoritative: false
  });
  writeJson(output.claims, {
    schemaVersion: "understand-video-claims/v1",
    claims: [
      {
        id: "C-FIXTURE-001",
        text: "The synthetic gate returns its explicit warrant input.",
        source: { path: "src/gate.ts", startLine: 1, endLine: 3 }
      }
    ],
    authoritative: false
  });
  return { ok: true, summary: "synthetic snapshot and one grounded claim inspected", artifactPath: output.snapshot };
}
function plan(context) {
  const output = paths(context.workspace);
  readFileSync(output.snapshot, "utf8");
  readFileSync(output.claims, "utf8");
  writeJson(output.storyboard, {
    schemaVersion: "understand-video-storyboard/v1",
    profile: "judge-fixture",
    durationMs: 2e3,
    scenes: [
      {
        id: "fixture-gate",
        type: "source-callout",
        claimIds: ["C-FIXTURE-001"],
        startMs: 0,
        endMs: 2e3
      }
    ],
    plannerMode: "fixture",
    authoritative: false
  });
  return { ok: true, summary: "credential-free fixture storyboard planned", artifactPath: output.storyboard };
}
function render(context) {
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
      output.media
    ],
    "fixture render"
  );
  if (ffmpeg.status !== 0) {
    throw new Error("Fixture render failed");
  }
  return { ok: true, summary: "deterministic fixture inputs rendered through FFmpeg argv", artifactPath: output.media };
}
function verify(context) {
  const output = paths(context.workspace);
  const probeResult = requireTool(
    "ffprobe",
    ["-v", "error", "-show_streams", "-show_format", "-of", "json", output.media],
    "fixture media verification"
  );
  const probe = JSON.parse(probeResult.stdout);
  const video = probe.streams?.find((stream) => stream.codec_type === "video");
  const audio = probe.streams?.find((stream) => stream.codec_type === "audio");
  const durationSeconds = Number.parseFloat(probe.format?.duration ?? "NaN");
  if (video?.codec_name !== "h264" || audio?.codec_name !== "aac" || video.width !== 1920 || video.height !== 1080 || video.avg_frame_rate !== "30/1" || !Number.isFinite(durationSeconds) || durationSeconds <= 0 || durationSeconds >= 180) {
    throw new Error("Fixture media failed codec, canvas, frame-rate, or duration checks");
  }
  const artifactPaths = {
    snapshot: output.snapshot,
    claims: output.claims,
    storyboard: output.storyboard,
    narration: output.narration,
    captions: output.captions,
    media: output.media
  };
  const artifacts = Object.fromEntries(
    Object.entries(artifactPaths).map(([name, path]) => [name, bindArtifact(path, readFileSync(path))])
  );
  const receipt = createProductReceipt({
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
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
      startEventHash: null
    },
    verification: {
      passed: true,
      profile: "judge-fixture",
      checks: ["source-grounding", "h264-aac", "1920x1080", "30fps", "duration-under-180s", "receipt"]
    }
  });
  verifyProductReceipt(receipt, (name) => readFileSync(artifactPaths[name]));
  writeJson(output.receipt, receipt);
  return { ok: true, summary: "media and all six receipt bindings verified; authoritative:false", artifactPath: output.receipt };
}
function createJudgeHandlers() {
  return { doctor, inspect, plan, render, verify };
}

// packages/cli/src/orchestrator.ts
var PIPELINE_STAGES = ["doctor", "inspect", "plan", "render", "verify"];
var DEMO_SUCCESS_SENTINEL = "UNDERSTAND_VIDEO_DEMO_PASSED";
async function runPipeline(handlers, context, stages = PIPELINE_STAGES, write = () => void 0) {
  const completed = [];
  const results = {};
  for (const stage of stages) {
    write(`[${stage}] running`);
    let result;
    try {
      result = await handlers[stage](context);
    } catch (error) {
      write(`[${stage}] failed: ${error instanceof Error ? error.message : String(error)}`);
      return { ok: false, completed, results, failedStage: stage };
    }
    results[stage] = result;
    if (!result.ok) {
      write(`[${stage}] failed: ${result.summary}`);
      return { ok: false, completed, results, failedStage: stage };
    }
    completed.push(stage);
    write(`[${stage}] passed: ${result.summary}`);
  }
  return { ok: true, completed, results, failedStage: null };
}
async function runDemo(handlers, context, write) {
  const run = await runPipeline(handlers, context, PIPELINE_STAGES, write);
  if (run.ok && run.completed.length === PIPELINE_STAGES.length) {
    write(DEMO_SUCCESS_SENTINEL);
  }
  return run;
}

// packages/cli/src/main.ts
function parseArguments(argv) {
  const command = argv[0];
  if (command !== "demo" && !PIPELINE_STAGES.includes(command)) {
    throw new Error("Usage: understand-video <doctor|inspect|plan|render|verify|demo> --offline [--workdir PATH]");
  }
  let workspace = resolve2(".understand-video", "judge-demo");
  let offline = false;
  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--offline") {
      offline = true;
    } else if (token === "--workdir") {
      const value = argv[index + 1];
      if (value === void 0 || value.startsWith("--")) {
        throw new Error("--workdir requires a path");
      }
      workspace = resolve2(value);
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${String(token)}`);
    }
  }
  if (!offline) {
    throw new Error("This MVP command surface currently requires --offline; provider/network use is not implicit");
  }
  return { command, workspace, offline };
}
async function main(argv = process.argv.slice(2)) {
  try {
    const parsed = parseArguments(argv);
    const handlers = createJudgeHandlers();
    const context = { workspace: parsed.workspace, offline: parsed.offline };
    const write = (line) => process.stdout.write(`${line}
`);
    const result = parsed.command === "demo" ? await runDemo(handlers, context, write) : await runPipeline(handlers, context, [parsed.command], write);
    return result.ok ? 0 : 2;
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}
`);
    return 2;
  }
}
var entrypoint = process.argv[1];
if (entrypoint !== void 0 && /(?:^|[\\/])main\.(?:ts|[cm]?js)$/.test(entrypoint) && resolve2(entrypoint) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}

// packages/cli/src/judge-entry.ts
process.exitCode = await main(process.argv.slice(2).length === 0 ? ["demo", "--offline"] : process.argv.slice(2));
