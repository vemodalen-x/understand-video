import {
  ProviderProvenanceSchema,
  StoryboardSchema,
  type FixtureProviderProvenance,
  type ProviderProvenance,
  type RealProviderProvenance,
  type Storyboard,
  type StoryboardScene,
} from "../../contracts/src/index.js";
import { hashJson } from "./hash.js";

export const DEVPOST_DURATION_LIMIT_MS = 180_000;
export const DEFAULT_PLANNING_BUDGET_MS = DEVPOST_DURATION_LIMIT_MS - 1;

export class PlannerContractError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "PlannerContractError";
  }
}

export class DurationBudgetError extends Error {
  public constructor(message = "required narration exceeds the video duration budget") {
    super(message);
    this.name = "DurationBudgetError";
  }
}

export interface ClaimPlanInput {
  readonly sourceRevision: string;
  readonly claims: readonly {
    readonly id: string;
    readonly required: boolean;
  }[];
}

export interface PrunedStoryboard {
  readonly storyboard: Storyboard;
  readonly durationMs: number;
  readonly removedSceneIds: readonly string[];
}

export interface PlanVideoInput {
  readonly plannerOutput: string | unknown;
  readonly claims: ClaimPlanInput;
  readonly maxDurationMs?: number;
}

export interface VideoPlan extends PrunedStoryboard {
  readonly provenance: ProviderProvenance;
}

export function fixtureProviderProvenance(): FixtureProviderProvenance {
  return Object.freeze({
    mode: "fixture" as const,
    provider: "fixture" as const,
    model: null,
    requestHash: null,
  });
}

export function realProviderProvenance(input: {
  readonly provider: string;
  readonly model: string;
  readonly request: unknown;
}): RealProviderProvenance {
  return ProviderProvenanceSchema.parse({
    mode: "real",
    provider: input.provider,
    model: input.model,
    requestHash: hashJson(input.request),
  }) as RealProviderProvenance;
}

export function parsePlannerJson(input: string): Storyboard {
  let parsed: unknown;
  try {
    parsed = JSON.parse(input) as unknown;
  } catch {
    throw new PlannerContractError("planner response is not valid JSON");
  }
  try {
    return StoryboardSchema.parse(parsed);
  } catch {
    throw new PlannerContractError("planner response does not satisfy the strict storyboard contract");
  }
}

function parsePlannerOutput(input: string | unknown): Storyboard {
  if (typeof input === "string") {
    return parsePlannerJson(input);
  }
  try {
    return StoryboardSchema.parse(input);
  } catch {
    throw new PlannerContractError("planner response does not satisfy the strict storyboard contract");
  }
}

export function storyboardDurationMs(storyboardInput: unknown): number {
  return StoryboardSchema.parse(storyboardInput).scenes.reduce(
    (total, scene) => total + scene.estimatedDurationMs,
    0,
  );
}

function validateBudget(maxDurationMs: number): void {
  if (!Number.isInteger(maxDurationMs) || maxDurationMs <= 0 || maxDurationMs >= DEVPOST_DURATION_LIMIT_MS) {
    throw new DurationBudgetError("duration budget must be a positive integer below 180000 ms");
  }
}

export function pruneStoryboardToDuration(
  storyboardInput: unknown,
  maxDurationMs: number = DEFAULT_PLANNING_BUDGET_MS,
  requiredClaimIds: ReadonlySet<string> = new Set<string>(),
): PrunedStoryboard {
  validateBudget(maxDurationMs);
  const storyboard = StoryboardSchema.parse(storyboardInput);
  const isProtected = (scene: StoryboardScene): boolean =>
    scene.required || scene.claimIds.some((claimId) => requiredClaimIds.has(claimId));
  const requiredDuration = storyboard.scenes
    .filter(isProtected)
    .reduce((total, scene) => total + scene.estimatedDurationMs, 0);
  if (requiredDuration > maxDurationMs) {
    throw new DurationBudgetError();
  }

  const kept = [...storyboard.scenes];
  const removedSceneIds: string[] = [];
  let durationMs = storyboardDurationMs(storyboard);
  for (let index = kept.length - 1; index >= 0 && durationMs > maxDurationMs; index -= 1) {
    const scene = kept[index];
    if (scene === undefined) {
      continue;
    }
    if (isProtected(scene)) {
      continue;
    }
    kept.splice(index, 1);
    durationMs -= scene.estimatedDurationMs;
    removedSceneIds.unshift(scene.id);
  }
  if (durationMs > maxDurationMs || kept.length === 0) {
    throw new DurationBudgetError();
  }
  const pruned = StoryboardSchema.parse({ ...storyboard, scenes: kept });
  return Object.freeze({
    storyboard: pruned,
    durationMs,
    removedSceneIds: Object.freeze(removedSceneIds),
  });
}

export function validateStoryboardClaims(storyboardInput: unknown, claims: ClaimPlanInput): Storyboard {
  const storyboard = StoryboardSchema.parse(storyboardInput);
  if (storyboard.sourceRevision !== claims.sourceRevision) {
    throw new PlannerContractError("storyboard revision does not match the grounded claims");
  }
  const claimIds = new Set(claims.claims.map((claim) => claim.id));
  const usedClaimIds = new Set<string>();
  for (const scene of storyboard.scenes) {
    for (const claimId of scene.claimIds) {
      if (!claimIds.has(claimId)) {
        throw new PlannerContractError("storyboard references an unknown claim");
      }
      usedClaimIds.add(claimId);
    }
  }
  for (const claim of claims.claims) {
    if (claim.required && !usedClaimIds.has(claim.id)) {
      throw new PlannerContractError("storyboard omitted a required grounded claim");
    }
  }
  return storyboard;
}

export function planVideo(input: PlanVideoInput): VideoPlan {
  const storyboard = parsePlannerOutput(input.plannerOutput);
  validateStoryboardClaims(storyboard, input.claims);
  const requiredClaimIds = new Set(
    input.claims.claims.filter((claim) => claim.required).map((claim) => claim.id),
  );
  const pruned = pruneStoryboardToDuration(
    storyboard,
    input.maxDurationMs ?? DEFAULT_PLANNING_BUDGET_MS,
    requiredClaimIds,
  );
  validateStoryboardClaims(pruned.storyboard, input.claims);
  return Object.freeze({ ...pruned, provenance: pruned.storyboard.provider });
}
