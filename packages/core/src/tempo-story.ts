import type { ClaimSet, SourceReference, Storyboard, StoryboardScene } from "../../contracts/src/index.js";
import type { SnapshotReader } from "./git-snapshot.js";
import { hashSourceLineSpan } from "./hash.js";
import { planVideo, realProviderProvenance, type VideoPlan } from "./planner.js";

export const TEMPO_STORY_REVISION = "4afc6a3f5ceba0240f7fdd2eece96241253d6e60";

interface ClaimSpec {
  readonly id: `C-TEMPO-${string}`;
  readonly text: string;
  readonly path: string;
  readonly startLine: number;
  readonly endLine: number;
}

const CLAIM_SPECS: readonly ClaimSpec[] = [
  { id: "C-TEMPO-001", text: "TEMPO separates business readiness from engineering authority.", path: "README.md", startLine: 25, endLine: 39 },
  { id: "C-TEMPO-002", text: "Model output is advisory and cannot carry signing or build authority.", path: "src/tempo/providers.py", startLine: 16, endLine: 47 },
  { id: "C-TEMPO-003", text: "Deterministic readiness can recommend an MVP without authorizing a build.", path: "src/tempo/readiness.py", startLine: 529, endLine: 610 },
  { id: "C-TEMPO-004", text: "A warrant is human-controlled, time-limited, scoped, and hash-bound.", path: "src/tempo/warrant.py", startLine: 350, endLine: 416 },
  { id: "C-TEMPO-005", text: "Every start revalidates task traceability and protected-input integrity.", path: "src/tempo/warrant.py", startLine: 753, endLine: 804 },
  { id: "C-TEMPO-006", text: "The local ledger is serialized and hash-chained with a durable head checkpoint.", path: "src/tempo/ledger.py", startLine: 130, endLine: 194 },
  { id: "C-TEMPO-007", text: "The credential-free demo shows both allowed and rejected paths.", path: "src/tempo/demo.py", startLine: 210, endLine: 305 },
] as const;

export const TEMPO_NARRATION = Object.freeze({
  opening: "A new repository can take hours to understand, and a confident summary can still be wrong. Understand Video starts with one exact TEMPO commit and turns only verified source into this walkthrough.",
  architecture: "TEMPO separates two questions that teams often mix together. Business evidence decides whether an MVP is worth considering. Engineering authority is a separate, human-controlled decision. The repository snapshot and graph keep that boundary visible.",
  advice: "GPT-shaped provider output is treated as untrusted advice. It may propose structured business material, but it cannot sign a charter, issue a warrant, or claim that a build is allowed. Deterministic readiness checks the evidence instead.",
  warrant: "Even when readiness recommends an MVP, implementation remains blocked. A real warrant requires a human-controlled signing path and binds the allowed scope, lane, action, budget, deadline, and protected file hashes. Starting outside those boundaries fails closed.",
  demo: "The credential-free demo makes the control flow concrete. Starting without a warrant returns WARRANT MISSING. One traced in-scope task can start. An out-of-scope path returns SCOPE NOT AUTHORIZED. These fixture results demonstrate the mechanism, not production identity.",
  integrity: "Before every bounded start, TEMPO rechecks task traceability and the current warrant. If a protected input changes, the warrant is permanently invalidated; restoring the old bytes does not revive it. That makes authorization a continuing constraint, not a one-time checkbox.",
  audit: "Every decision event enters a serialized hash chain with a durable head checkpoint. Verification receipts report local integrity honestly, while the compiler leaves the human verdict section blank. Local evidence is auditable, but it is not external notarization.",
  close: "Codex and GPT-5.6 helped build and test this source-grounded pipeline. The result is a short video, readable captions, exact source links, and a receipt for the pinned commit—so reviewers can understand unfamiliar code without trusting a free-form summary.",
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
      scene("SCENE-INTEGRITY", "safety", "Protected drift invalidates authority", TEMPO_NARRATION.integrity, ["C-TEMPO-005"], 22_000),
      scene("SCENE-AUDIT", "control-flow", "Local integrity stays honest", TEMPO_NARRATION.audit, ["C-TEMPO-006"], 20_000),
      scene("SCENE-CLOSE", "takeaway", "Source links, captions, and receipts", TEMPO_NARRATION.close, ["C-TEMPO-001", "C-TEMPO-006"], 15_000),
    ],
  };
}

export function compileTempoVideoPlan(reader: SnapshotReader): { claims: ClaimSet; plan: VideoPlan } {
  const claims = compileTempoClaims(reader);
  const storyboard = compileTempoStoryboard();
  const plan = planVideo({ plannerOutput: storyboard, claims, maxDurationMs: 179_000 });
  return { claims, plan };
}
