import type { ClaimSet, SourceReference, Storyboard, StoryboardScene } from "../../contracts/src/index.js";
import type { SnapshotReader } from "./git-snapshot.js";
import { hashSourceLineSpan } from "./hash.js";
import { planVideo, realProviderProvenance, type VideoPlan } from "./planner.js";

export const TEMPO_STORY_REVISION = "4a73350f6eefff80b11d862a5ac65b7194530442";

interface ClaimSpec {
  readonly id: `C-TEMPO-${string}`;
  readonly text: string;
  readonly path: string;
  readonly startLine: number;
  readonly endLine: number;
}

const CLAIM_SPECS: readonly ClaimSpec[] = [
  { id: "C-TEMPO-001", text: "TEMPO separates business readiness from engineering authority.", path: "README.md", startLine: 25, endLine: 46 },
  { id: "C-TEMPO-002", text: "Model output is advisory and cannot carry signing or build authority.", path: "src/tempo/providers.py", startLine: 80, endLine: 116 },
  { id: "C-TEMPO-003", text: "Deterministic readiness can recommend an MVP without authorizing a build.", path: "src/tempo/readiness.py", startLine: 600, endLine: 649 },
  { id: "C-TEMPO-004", text: "A warrant is human-controlled, time-limited, scoped, and hash-bound, but does not itself allow a build.", path: "src/tempo/warrant.py", startLine: 251, endLine: 419 },
  { id: "C-TEMPO-005", text: "Build leases are exact and same-owner path rotation is task-bound, receipted, and failure-atomic.", path: "src/tempo/warrant.py", startLine: 799, endLine: 1020 },
  { id: "C-TEMPO-006", text: "The local ledger is serialized and hash-chained with a durable head checkpoint.", path: "src/tempo/ledger.py", startLine: 130, endLine: 194 },
  { id: "C-TEMPO-007", text: "The credential-free demo shows both allowed and rejected paths.", path: "src/tempo/demo.py", startLine: 210, endLine: 334 },
] as const;

export const TEMPO_NARRATION = Object.freeze({
  opening: "A new repository can take hours to understand, and a confident summary can still be wrong. Understand Video starts with one exact TEMPO commit and turns only verified source into this walkthrough.",
  architecture: "TEMPO separates two questions that teams often mix together. Business evidence decides whether an MVP is worth considering. Engineering authority is a separate, human-controlled decision. The repository snapshot and reviewed graph keep that boundary visible.",
  advice: "GPT-shaped provider output is treated as untrusted advice. It may propose structured business material, but it cannot sign a charter, issue a warrant, or claim that a build is allowed. Deterministic readiness checks the evidence instead.",
  warrant: "Even when readiness recommends an MVP, implementation remains blocked. A real warrant requires a human-controlled signing path and binds the allowed scope, lane, action, budget, deadline, and protected file hashes. Build permission appears only after one exact task and path start.",
  demo: "The credential-free demo makes the control flow concrete. Starting without a warrant returns WARRANT MISSING. One traced in-scope task can start. An out-of-scope path returns SCOPE NOT AUTHORIZED. These fixture results demonstrate the mechanism, not production identity.",
  integrity: "A multi-file task can rotate its exact lease only within the same actor, session, task, and warrant. Every rotation gets a unique ledger receipt and rolls back if receipt writing fails. Protected-input drift still invalidates the warrant permanently.",
  audit: "Every decision event enters a serialized hash chain with a durable head checkpoint. Verification receipts report local integrity honestly, while the compiler leaves the human verdict section blank. Local evidence is auditable, but it is not external notarization.",
  close: "This closing terminal is a real credential-free Understand Video judge run. Codex and GPT-5.6 helped build and test the source-grounded pipeline; the runtime here uses authored claims and a disclosed speech provider, not an unrecorded OpenAI API call. The output stays a technical draft until a human approves publication.",
});

function sourceReference(reader: SnapshotReader, spec: ClaimSpec): SourceReference {
  const text = reader.readText(spec.path);
  return {
    path: spec.path,
    startLine: spec.startLine,
    endLine: spec.endLine,
    lineHash: hashSourceLineSpan(text, spec.startLine, spec.endLine),
  };
}

export function compileTempoClaims(reader: SnapshotReader): ClaimSet {
  if (reader.manifest.revision !== TEMPO_STORY_REVISION) {
    throw new Error("TEMPO story requires the reviewed pinned revision");
  }
  return {
    schemaVersion: 1,
    sourceRevision: TEMPO_STORY_REVISION,
    claims: CLAIM_SPECS.map((spec) => ({
      id: spec.id,
      text: spec.text,
      material: true,
      required: true,
      sources: [sourceReference(reader, spec)],
    })),
  };
}

function scene(
  id: string,
  sceneType: StoryboardScene["sceneType"],
  title: string,
  narration: string,
  claimIds: StoryboardScene["claimIds"],
  estimatedDurationMs: number,
): StoryboardScene {
  return { id, sceneType, title, narration, claimIds, required: true, estimatedDurationMs } as StoryboardScene;
}

export function compileTempoStoryboard(): Storyboard {
  const provider = realProviderProvenance({
    provider: "openai-codex-build-session",
    model: "gpt-5.6",
    request: { story: "TEMPO source-grounded Devpost walkthrough", revision: TEMPO_STORY_REVISION, narration: TEMPO_NARRATION },
  });
  return {
    schemaVersion: 1,
    sourceRevision: TEMPO_STORY_REVISION,
    provider,
    scenes: [
      scene("SCENE-OPENING", "title", "Understand TEMPO from source", TEMPO_NARRATION.opening, ["C-TEMPO-001"], 12_000),
      scene("SCENE-ARCHITECTURE", "architecture", "Readiness is not authority", TEMPO_NARRATION.architecture, ["C-TEMPO-001"], 17_000),
      scene("SCENE-ADVICE", "control-flow", "Model output remains advice", TEMPO_NARRATION.advice, ["C-TEMPO-002", "C-TEMPO-003"], 22_000),
      scene("SCENE-WARRANT", "safety", "A human warrant sets the boundary", TEMPO_NARRATION.warrant, ["C-TEMPO-004"], 27_000),
      scene("SCENE-DEMO", "working-demo", "Allowed and rejected paths", TEMPO_NARRATION.demo, ["C-TEMPO-007"], 24_000),
      scene("SCENE-INTEGRITY", "safety", "Exact leases rotate without widening scope", TEMPO_NARRATION.integrity, ["C-TEMPO-005"], 22_000),
      scene("SCENE-AUDIT", "control-flow", "Local integrity stays honest", TEMPO_NARRATION.audit, ["C-TEMPO-006"], 20_000),
      scene("SCENE-CLOSE", "takeaway", "Working product and build evidence", TEMPO_NARRATION.close, ["C-TEMPO-001", "C-TEMPO-006"], 15_000),
    ],
  };
}

export function compileTempoVideoPlan(reader: SnapshotReader): { claims: ClaimSet; plan: VideoPlan } {
  const claims = compileTempoClaims(reader);
  const storyboard = compileTempoStoryboard();
  const plan = planVideo({ plannerOutput: storyboard, claims, maxDurationMs: 179_000 });
  return { claims, plan };
}
