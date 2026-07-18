import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

import { Resvg } from "@resvg/resvg-js";

import { createCaptionCues, toSrt, toWebVtt, type CaptionCue } from "../../core/src/captions.js";
import { snapshotGitRepository } from "../../core/src/git-snapshot.js";
import { hashJson, sha256Bytes } from "../../core/src/hash.js";
import { verifyMediaFile } from "../../core/src/media.js";
import { renderFrame } from "../../core/src/renderer.js";
import { compileTempoVideoPlan, TEMPO_STORY_REVISION } from "../../core/src/tempo-story.js";
import { loadUnderstandAnythingBundle } from "../../core/src/understand-anything.js";
import type { StoryboardScene } from "../../contracts/src/index.js";

interface Options {
  readonly tempoCheckout: string;
  readonly graphDirectory: string;
  readonly outputDirectory: string;
  readonly edgePython: string;
}

function option(argv: readonly string[], name: string, fallback: string): string {
  const index = argv.indexOf(name);
  if (index < 0) return resolve(fallback);
  const value = argv[index + 1];
  if (value === undefined || value.startsWith("--")) throw new Error(`${name} requires a value`);
  return resolve(value);
}

function parseOptions(argv: readonly string[]): Options {
  const edgePython = process.platform === "win32"
    ? join(".understand-video", "tools", "edge-tts", "Scripts", "python.exe")
    : join(".understand-video", "tools", "edge-tts", "bin", "python");
  return {
    tempoCheckout: option(
      argv,
      "--tempo",
      process.env["TEMPO_CHECKOUT"] ?? join(".understand-video", "inputs", "tempo-checkout"),
    ),
    graphDirectory: option(argv, "--graph", join(".understand-video", "inputs", "tempo-4afc6a3")),
    outputDirectory: option(argv, "--output", join(".understand-video", "runs", "tempo-4afc6a3", "devpost-draft")),
    edgePython: option(argv, "--edge-python", edgePython),
  };
}

interface ProcessOutput {
  readonly stdout: string;
  readonly stderr: string;
}

function runCapture(command: string, args: readonly string[]): ProcessOutput {
  const result = spawnSync(command, [...args], {
    encoding: "utf8",
    shell: false,
    windowsHide: true,
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.error !== undefined || result.status !== 0) {
    throw new Error(`${basename(command)} failed: ${result.stderr || result.error?.message || String(result.status)}`);
  }
  return { stdout: result.stdout, stderr: result.stderr };
}

function run(command: string, args: readonly string[]): string {
  return runCapture(command, args).stdout;
}

function writeJson(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function concatEntry(path: string): string {
  return `file '${resolve(path).replace(/'/gu, "'\\''").replace(/\\/gu, "/")}'`;
}

function audioDurationMs(path: string): number {
  const output = run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "json", path]);
  const parsed = JSON.parse(output) as { format?: { duration?: string } };
  const milliseconds = Number(parsed.format?.duration) * 1_000;
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) throw new Error(`invalid audio duration: ${path}`);
  return Math.round(milliseconds);
}

interface AudioQuality {
  readonly ok: boolean;
  readonly errors: readonly string[];
  readonly integratedLufs: number;
  readonly truePeakDbtp: number;
  readonly loudnessRangeLu: number;
  readonly maximumInternalSilenceMs: number;
  readonly leadingSilenceMs: number;
  readonly trailingSilenceMs: number;
}

function analyzeAudio(path: string, durationMs: number): AudioQuality {
  const loudnessOutput = runCapture("ffmpeg", [
    "-hide_banner", "-nostats", "-i", path,
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-",
  ]).stderr;
  const jsonMatch = /\{[\s\S]*?"input_i"[\s\S]*?\}/gu.exec(loudnessOutput);
  if (jsonMatch === null) throw new Error("ffmpeg did not return loudness analysis JSON");
  const loudness = JSON.parse(jsonMatch[0]) as {
    input_i: string;
    input_tp: string;
    input_lra: string;
  };
  const integratedLufs = Number(loudness.input_i);
  const truePeakDbtp = Number(loudness.input_tp);
  const loudnessRangeLu = Number(loudness.input_lra);

  const silenceOutput = runCapture("ffmpeg", [
    "-hide_banner", "-nostats", "-i", path,
    "-af", "silencedetect=noise=-45dB:d=0.5", "-f", "null", "-",
  ]).stderr;
  const spans: Array<{ startMs: number; endMs: number }> = [];
  let openStartMs: number | null = null;
  for (const line of silenceOutput.split(/\r?\n/gu)) {
    const start = /silence_start:\s*([0-9.]+)/u.exec(line);
    if (start !== null) openStartMs = Number(start[1]) * 1_000;
    const end = /silence_end:\s*([0-9.]+)/u.exec(line);
    if (end !== null && openStartMs !== null) {
      spans.push({ startMs: openStartMs, endMs: Number(end[1]) * 1_000 });
      openStartMs = null;
    }
  }
  if (openStartMs !== null) spans.push({ startMs: openStartMs, endMs: durationMs });
  const leadingSilenceMs = spans[0]?.startMs === 0 ? spans[0].endMs : 0;
  const lastSpan = spans.at(-1);
  const trailingSilenceMs = lastSpan !== undefined && Math.abs(lastSpan.endMs - durationMs) <= 100
    ? lastSpan.endMs - lastSpan.startMs
    : 0;
  const internalSpans = spans.filter((span) => span.startMs > 0 && span.endMs < durationMs - 100);
  const maximumInternalSilenceMs = internalSpans.reduce(
    (maximum, span) => Math.max(maximum, span.endMs - span.startMs),
    0,
  );
  const errors: string[] = [];
  if (integratedLufs < -18 || integratedLufs > -14) errors.push(`integrated loudness ${integratedLufs} LUFS is outside -18..-14`);
  if (truePeakDbtp > -1) errors.push(`true peak ${truePeakDbtp} dBTP exceeds -1 dBTP`);
  if (leadingSilenceMs > 500) errors.push(`leading silence ${leadingSilenceMs}ms exceeds 500ms`);
  if (trailingSilenceMs > 500) errors.push(`trailing silence ${trailingSilenceMs}ms exceeds 500ms`);
  if (maximumInternalSilenceMs > 1_200) errors.push(`internal silence ${maximumInternalSilenceMs}ms exceeds 1200ms`);
  return {
    ok: errors.length === 0,
    errors,
    integratedLufs,
    truePeakDbtp,
    loudnessRangeLu,
    maximumInternalSilenceMs: Math.round(maximumInternalSilenceMs),
    leadingSilenceMs: Math.round(leadingSilenceMs),
    trailingSilenceMs: Math.round(trailingSilenceMs),
  };
}

function visual(scene: StoryboardScene): {
  kind: "title" | "architecture" | "code" | "workflow" | "evidence" | "summary";
  body?: readonly string[];
  code?: readonly string[];
  accent: string;
} {
  switch (scene.id) {
    case "SCENE-OPENING":
      return { kind: "title", body: ["Pinned commit 4afc6a3", "188 graph nodes", "97 inspected files"], accent: "#6ee7d8" };
    case "SCENE-ARCHITECTURE":
      return { kind: "architecture", body: ["Evidence", "Readiness", "Human warrant", "Bounded build"], accent: "#6ee7d8" };
    case "SCENE-ADVICE":
      return { kind: "workflow", body: ["Model advice", "Deterministic checks", "Human decision", "No implied authority"], accent: "#8ab4ff" };
    case "SCENE-WARRANT":
      return { kind: "code", code: ["warrant = human_authorize(...) ", "scope + lane + action", "budget + deadline", "protected input hashes", "start(...)  # revalidate everything"], accent: "#ffd166" };
    case "SCENE-DEMO":
      return { kind: "code", code: ["$ python bin/tempo demo", "WARRANT_MISSING", "VALID_WARRANT_AND_SCOPE", "SCOPE_NOT_AUTHORIZED", "JUDGE_DEMO_PASSED"], accent: "#66d9a7" };
    case "SCENE-INTEGRITY":
      return { kind: "workflow", body: ["Hash inputs", "Validate start", "Detect drift", "Invalidate warrant"], accent: "#ff8a8a" };
    case "SCENE-AUDIT":
      return { kind: "architecture", body: ["Event", "Hash chain", "Head checkpoint", "Receipt"], accent: "#c4a7ff" };
    default:
      return { kind: "summary", body: ["Exact source links", "Readable captions", "Verified MP4", "Honest provenance"], accent: "#6ee7d8" };
  }
}

function renderPng(scene: StoryboardScene, caption: string, path: string): void {
  const frame = renderFrame({
    id: scene.id,
    title: scene.title,
    eyebrow: "SOURCE-GROUNDED TEMPO WALKTHROUGH",
    burnedCaption: caption,
    ...visual(scene),
  });
  const png = new Resvg(frame.svg, { fitTo: { mode: "width", value: 1920 } }).render().asPng();
  writeFileSync(path, png);
}

async function main(): Promise<void> {
  const options = parseOptions(process.argv.slice(2));
  const output = options.outputDirectory;
  const audioDirectory = join(output, "audio");
  const frameDirectory = join(output, "frames");
  const segmentDirectory = join(output, "segments");
  mkdirSync(audioDirectory, { recursive: true });
  mkdirSync(frameDirectory, { recursive: true });
  mkdirSync(segmentDirectory, { recursive: true });

  const snapshot = snapshotGitRepository({ root: options.tempoCheckout, revision: TEMPO_STORY_REVISION, strict: true });
  const compiled = compileTempoVideoPlan(snapshot);
  const ua = loadUnderstandAnythingBundle(options.graphDirectory, {
    targetRepository: "https://github.com/vemodalen-x/TEMPO",
    targetCommit: TEMPO_STORY_REVISION,
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

  const audioPaths: string[] = [];
  const durations: number[] = [];
  for (const [index, scene] of compiled.plan.storyboard.scenes.entries()) {
    const audioPath = join(audioDirectory, `${String(index + 1).padStart(2, "0")}-${scene.id}.mp3`);
    run(options.edgePython, [
      "-m", "edge_tts", "--voice", "en-US-BrianMultilingualNeural", "--rate=-2%", "--pitch=-2Hz",
      "--text", scene.narration, "--write-media", audioPath,
    ]);
    audioPaths.push(audioPath);
    durations.push(audioDurationMs(audioPath));
  }

  const cues: CaptionCue[] = [];
  const videoSegments: string[] = [];
  let cursor = 0;
  let segmentIndex = 0;
  for (const [sceneIndex, scene] of compiled.plan.storyboard.scenes.entries()) {
    const duration = durations[sceneIndex];
    if (duration === undefined) throw new Error("missing synthesized scene duration");
    const sceneCues = createCaptionCues(scene.narration, cursor, cursor + duration);
    for (const cue of sceneCues) {
      segmentIndex += 1;
      cues.push(cue);
      const stem = `${String(segmentIndex).padStart(3, "0")}-${scene.id}`;
      const pngPath = join(frameDirectory, `${stem}.png`);
      const segmentPath = join(segmentDirectory, `${stem}.mp4`);
      renderPng(scene, cue.text.replace(/\n/gu, " "), pngPath);
      run("ffmpeg", [
        "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", pngPath,
        "-t", ((cue.endMs - cue.startMs) / 1_000).toFixed(3), "-r", "30", "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", segmentPath,
      ]);
      videoSegments.push(segmentPath);
    }
    cursor += duration;
  }
  if (cursor >= 180_000) throw new Error(`synthesized narration exceeds Devpost limit: ${cursor}ms`);

  const visualList = join(output, "visual-concat.txt");
  const audioList = join(output, "audio-concat.txt");
  writeFileSync(visualList, `${videoSegments.map(concatEntry).join("\n")}\n`, "utf8");
  writeFileSync(audioList, `${audioPaths.map(concatEntry).join("\n")}\n`, "utf8");
  const silentVideo = join(output, "visual.mp4");
  const narrationAudio = join(output, "narration.m4a");
  const finalVideo = join(output, "tempo-understand-video-devpost-draft.mp4");
  run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", visualList, "-c", "copy", silentVideo]);
  run("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", audioList,
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", narrationAudio,
  ]);
  run("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y", "-i", silentVideo, "-i", narrationAudio,
    "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", finalVideo,
  ]);

  const narration = compiled.plan.storyboard.scenes.map((scene) => scene.narration).join("\n\n");
  const captions = { srt: toSrt(cues), vtt: toWebVtt(cues) };
  writeFileSync(join(output, "narration.txt"), `${narration}\n`, "utf8");
  writeFileSync(join(output, "captions.srt"), captions.srt, "utf8");
  writeFileSync(join(output, "captions.vtt"), captions.vtt, "utf8");
  writeJson(join(output, "claims.json"), compiled.claims);
  writeJson(join(output, "storyboard.json"), compiled.plan.storyboard);
  const media = verifyMediaFile(finalVideo);
  if (!media.ok) throw new Error(`final media failed: ${media.errors.join(", ")}`);
  const audio = analyzeAudio(finalVideo, media.durationMs);
  if (!audio.ok) throw new Error(`final audio failed: ${audio.errors.join(", ")}`);
  const report = {
    schemaVersion: "understand-video-draft-report/v1",
    authoritative: false,
    publicationAuthorized: false,
    target: { repository: "https://github.com/vemodalen-x/TEMPO", revision: TEMPO_STORY_REVISION },
    upstream: { repository: "https://github.com/Egonex-AI/Understand-Anything", revision: ua.upstreamCommit },
    provider: { id: "microsoft-edge-speech", voice: "en-US-BrianMultilingualNeural", rate: "-2%", pitch: "-2Hz" },
    artifacts: {
      claims: hashJson(compiled.claims), storyboard: hashJson(compiled.plan.storyboard), narration: sha256Bytes(narration),
      captions: sha256Bytes(captions.vtt), media: sha256Bytes(readFileSync(finalVideo)), graph: ua.hashes["knowledge-graph.json"],
    },
    media,
    audio,
    captionCueCount: cues.length,
    zeroContentCaptionOverlapByLayoutContract: true,
    graphSummary: { nodes: ua.nodeCount, edges: ua.edgeCount, layers: ua.layerCount, tour: ua.tourCount, files: ua.fileCount },
  };
  writeJson(join(output, "verification-report.json"), report);
  process.stdout.write(`${JSON.stringify({ ok: true, finalVideo, report: join(output, "verification-report.json"), media })}\n`);
}

await main();
