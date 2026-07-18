export const PIPELINE_STAGES = ["doctor", "inspect", "plan", "render", "verify"] as const;
export const DEMO_SUCCESS_SENTINEL = "UNDERSTAND_VIDEO_DEMO_PASSED";

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export interface StageResult {
  readonly ok: boolean;
  readonly summary: string;
  readonly artifactPath?: string;
}

export interface PipelineContext {
  readonly workspace: string;
  readonly offline: boolean;
}

export type StageHandler = (context: PipelineContext) => StageResult | Promise<StageResult>;
export type PipelineHandlers = Readonly<Record<PipelineStage, StageHandler>>;
export type OutputWriter = (line: string) => void;

export interface PipelineRun {
  readonly ok: boolean;
  readonly completed: readonly PipelineStage[];
  readonly results: Readonly<Partial<Record<PipelineStage, StageResult>>>;
  readonly failedStage: PipelineStage | null;
}

export async function runPipeline(
  handlers: PipelineHandlers,
  context: PipelineContext,
  stages: readonly PipelineStage[] = PIPELINE_STAGES,
  write: OutputWriter = () => undefined,
): Promise<PipelineRun> {
  const completed: PipelineStage[] = [];
  const results: Partial<Record<PipelineStage, StageResult>> = {};

  for (const stage of stages) {
    write(`[${stage}] running`);
    let result: StageResult;
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

export async function runDemo(
  handlers: PipelineHandlers,
  context: PipelineContext,
  write: OutputWriter,
): Promise<PipelineRun> {
  const run = await runPipeline(handlers, context, PIPELINE_STAGES, write);
  if (run.ok && run.completed.length === PIPELINE_STAGES.length) {
    write(DEMO_SUCCESS_SENTINEL);
  }
  return run;
}
