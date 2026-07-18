import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { createJudgeHandlers } from "./judge.js";
import {
  PIPELINE_STAGES,
  runDemo,
  runPipeline,
  type PipelineStage,
} from "./orchestrator.js";

interface ParsedArguments {
  readonly command: PipelineStage | "demo";
  readonly workspace: string;
  readonly offline: boolean;
}

function parseArguments(argv: readonly string[]): ParsedArguments {
  const command = argv[0];
  if (command !== "demo" && !PIPELINE_STAGES.includes(command as PipelineStage)) {
    throw new Error("Usage: understand-video <doctor|inspect|plan|render|verify|demo> --offline [--workdir PATH]");
  }
  let workspace = resolve(".understand-video", "judge-demo");
  let offline = false;
  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--offline") {
      offline = true;
    } else if (token === "--workdir") {
      const value = argv[index + 1];
      if (value === undefined || value.startsWith("--")) {
        throw new Error("--workdir requires a path");
      }
      workspace = resolve(value);
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${String(token)}`);
    }
  }
  if (!offline) {
    throw new Error("This MVP command surface currently requires --offline; provider/network use is not implicit");
  }
  return { command: command as PipelineStage | "demo", workspace, offline };
}

export async function main(argv: readonly string[] = process.argv.slice(2)): Promise<number> {
  try {
    const parsed = parseArguments(argv);
    const handlers = createJudgeHandlers();
    const context = { workspace: parsed.workspace, offline: parsed.offline };
    const write = (line: string) => process.stdout.write(`${line}\n`);
    const result =
      parsed.command === "demo"
        ? await runDemo(handlers, context, write)
        : await runPipeline(handlers, context, [parsed.command], write);
    return result.ok ? 0 : 2;
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    return 2;
  }
}

const entrypoint = process.argv[1];
if (
  entrypoint !== undefined &&
  /(?:^|[\\/])main\.(?:ts|[cm]?js)$/.test(entrypoint) &&
  resolve(entrypoint) === fileURLToPath(import.meta.url)
) {
  process.exitCode = await main();
}
