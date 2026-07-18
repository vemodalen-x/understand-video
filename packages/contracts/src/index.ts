import { z } from "zod";

/**
 * Runtime contracts shared by the repository inspector and the media pipeline.
 * Every object is strict on purpose: an upstream graph or model response cannot
 * smuggle instructions or undeclared behavior through an ignored property.
 */

export const SHA256_PATTERN = /^sha256:[0-9a-f]{64}$/u;
export const GIT_OID_PATTERN = /^[0-9a-f]{40,64}$/u;
export const SAFE_ID_PATTERN = /^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$/u;

export const Sha256Schema = z.string().regex(SHA256_PATTERN);
export const GitOidSchema = z.string().regex(GIT_OID_PATTERN);
export const SafeIdSchema = z.string().regex(SAFE_ID_PATTERN);

export const SnapshotFileSchema = z
  .object({
    path: z.string().min(1),
    oid: GitOidSchema,
    mode: z.enum(["100644", "100755", "120000"]),
    kind: z.enum(["file", "symlink"]),
    byteLength: z.number().int().nonnegative(),
    contentHash: Sha256Schema,
    symlinkTarget: z.string().min(1).optional(),
  })
  .strict()
  .superRefine((value, context) => {
    const isSymlink = value.mode === "120000" || value.kind === "symlink";
    if (isSymlink !== (value.symlinkTarget !== undefined)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "symlink files must declare symlinkTarget and regular files must not",
        path: ["symlinkTarget"],
      });
    }
    if (isSymlink !== (value.kind === "symlink")) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "mode and kind disagree",
        path: ["kind"],
      });
    }
  });

export const RepositorySnapshotSchema = z
  .object({
    schemaVersion: z.literal(1),
    repositoryRoot: z.string().min(1),
    revision: GitOidSchema,
    treeOid: GitOidSchema,
    strict: z.boolean(),
    dirty: z.boolean(),
    files: z.array(SnapshotFileSchema),
  })
  .strict()
  .superRefine((value, context) => {
    if (value.strict && value.dirty) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "a strict snapshot cannot be dirty",
        path: ["dirty"],
      });
    }
    const paths = new Set<string>();
    for (const [index, file] of value.files.entries()) {
      if (paths.has(file.path)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "snapshot paths must be unique",
          path: ["files", index, "path"],
        });
      }
      paths.add(file.path);
    }
  });

export type SnapshotFile = z.infer<typeof SnapshotFileSchema>;
export type RepositorySnapshot = z.infer<typeof RepositorySnapshotSchema>;

export const SourceReferenceSchema = z
  .object({
    path: z.string().min(1),
    startLine: z.number().int().positive(),
    endLine: z.number().int().positive(),
    lineHash: Sha256Schema,
  })
  .strict()
  .refine((value) => value.endLine >= value.startLine, {
    message: "endLine must be greater than or equal to startLine",
    path: ["endLine"],
  });

export const ClaimSchema = z
  .object({
    id: SafeIdSchema,
    text: z.string().min(1).max(1_000),
    material: z.boolean(),
    required: z.boolean(),
    sources: z.array(SourceReferenceSchema).min(1),
  })
  .strict();

export const ClaimSetSchema = z
  .object({
    schemaVersion: z.literal(1),
    sourceRevision: GitOidSchema,
    claims: z.array(ClaimSchema).min(1),
  })
  .strict()
  .superRefine((value, context) => {
    const ids = new Set<string>();
    for (const [index, claim] of value.claims.entries()) {
      if (ids.has(claim.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "claim ids must be unique",
          path: ["claims", index, "id"],
        });
      }
      ids.add(claim.id);
    }
  });

export type SourceReference = z.infer<typeof SourceReferenceSchema>;
export type Claim = z.infer<typeof ClaimSchema>;
export type ClaimSet = z.infer<typeof ClaimSetSchema>;

export const GraphNodeSchema = z
  .object({
    id: z.string().min(1).max(160),
    kind: z.enum(["entrypoint", "module", "component", "boundary", "data", "decision"]),
    label: z.string().min(1).max(300),
    source: SourceReferenceSchema.optional(),
  })
  .strict();

export const GraphEdgeSchema = z
  .object({
    from: z.string().min(1).max(160),
    to: z.string().min(1).max(160),
    relation: z.enum(["calls", "imports", "reads", "writes", "guards", "emits", "contains"]),
  })
  .strict();

export const RepositoryGraphSchema = z
  .object({
    schemaVersion: z.literal(1),
    sourceRevision: GitOidSchema,
    generator: z
      .object({
        name: z.string().min(1),
        version: z.string().min(1),
        mode: z.enum(["fixture", "real"]),
      })
      .strict(),
    nodes: z.array(GraphNodeSchema).min(1),
    edges: z.array(GraphEdgeSchema),
  })
  .strict();

export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type GraphEdge = z.infer<typeof GraphEdgeSchema>;
export type RepositoryGraph = z.infer<typeof RepositoryGraphSchema>;

export const FixtureProviderProvenanceSchema = z
  .object({
    mode: z.literal("fixture"),
    provider: z.literal("fixture"),
    model: z.null(),
    requestHash: z.null(),
  })
  .strict();

export const RealProviderProvenanceSchema = z
  .object({
    mode: z.literal("real"),
    provider: z.string().min(1).refine((value) => value !== "fixture"),
    model: z.string().min(1),
    requestHash: Sha256Schema,
  })
  .strict();

export const ProviderProvenanceSchema = z.discriminatedUnion("mode", [
  FixtureProviderProvenanceSchema,
  RealProviderProvenanceSchema,
]);

export type FixtureProviderProvenance = z.infer<typeof FixtureProviderProvenanceSchema>;
export type RealProviderProvenance = z.infer<typeof RealProviderProvenanceSchema>;
export type ProviderProvenance = z.infer<typeof ProviderProvenanceSchema>;

export const SceneTypeSchema = z.enum([
  "title",
  "architecture",
  "control-flow",
  "safety",
  "working-demo",
  "takeaway",
]);

export const StoryboardSceneSchema = z
  .object({
    id: SafeIdSchema,
    sceneType: SceneTypeSchema,
    title: z.string().min(1).max(160),
    narration: z.string().min(1).max(4_000),
    claimIds: z.array(SafeIdSchema),
    required: z.boolean(),
    estimatedDurationMs: z.number().int().positive(),
  })
  .strict();

export const StoryboardSchema = z
  .object({
    schemaVersion: z.literal(1),
    sourceRevision: GitOidSchema,
    provider: ProviderProvenanceSchema,
    scenes: z.array(StoryboardSceneSchema).min(1),
  })
  .strict()
  .superRefine((value, context) => {
    const ids = new Set<string>();
    for (const [index, scene] of value.scenes.entries()) {
      if (ids.has(scene.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "scene ids must be unique",
          path: ["scenes", index, "id"],
        });
      }
      ids.add(scene.id);
    }
  });

export type SceneType = z.infer<typeof SceneTypeSchema>;
export type StoryboardScene = z.infer<typeof StoryboardSceneSchema>;
export type Storyboard = z.infer<typeof StoryboardSchema>;

export function validateRepositorySnapshot(input: unknown): RepositorySnapshot {
  return RepositorySnapshotSchema.parse(input);
}

export function validateClaim(input: unknown): Claim {
  return ClaimSchema.parse(input);
}

export function validateClaimSet(input: unknown): ClaimSet {
  return ClaimSetSchema.parse(input);
}

export function validateRepositoryGraph(input: unknown): RepositoryGraph {
  return RepositoryGraphSchema.parse(input);
}

export function validateStoryboard(input: unknown): Storyboard {
  return StoryboardSchema.parse(input);
}

export function validateProviderProvenance(input: unknown): ProviderProvenance {
  return ProviderProvenanceSchema.parse(input);
}

