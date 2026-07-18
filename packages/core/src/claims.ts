import {
  ClaimSetSchema,
  RepositorySnapshotSchema,
  type Claim,
  type ClaimSet,
  type RepositorySnapshot,
  type SourceReference,
} from "../../contracts/src/index.js";
import type { SnapshotReader } from "./git-snapshot.js";
import { normalizeSafeSourcePath } from "./git-snapshot.js";
import { hashSourceLineSpan, sha256Bytes, sourceLineSpan } from "./hash.js";

export class ClaimGroundingError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "ClaimGroundingError";
  }
}

export class SourceMissingError extends ClaimGroundingError {
  public constructor() {
    super("a claim source does not exist at the pinned revision");
    this.name = "SourceMissingError";
  }
}

export class SourceDriftError extends ClaimGroundingError {
  public constructor() {
    super("a claim source changed after inspection");
    this.name = "SourceDriftError";
  }
}

export class LineHashDriftError extends ClaimGroundingError {
  public constructor() {
    super("a claim line span no longer matches its recorded hash");
    this.name = "LineHashDriftError";
  }
}

export class SecretBlockedError extends ClaimGroundingError {
  public constructor() {
    super("a claim excerpt contains secret-like material and the active policy blocks it");
    this.name = "SecretBlockedError";
  }
}

export interface SecretRedaction {
  readonly kind: "cloud-key" | "provider-token" | "github-token" | "private-key" | "named-secret";
}

export interface SanitizedText {
  readonly text: string;
  readonly redactions: readonly SecretRedaction[];
}

export interface GroundedSource extends SourceReference {
  readonly excerpt: string;
  readonly untrusted: true;
  readonly redactions: readonly SecretRedaction[];
}

export interface GroundedClaim extends Omit<Claim, "sources"> {
  readonly sources: readonly GroundedSource[];
}

export interface GroundedClaimSet {
  readonly schemaVersion: 1;
  readonly sourceRevision: string;
  readonly claims: readonly GroundedClaim[];
}

export interface GroundClaimsOptions {
  readonly secretPolicy?: "redact" | "block";
}

interface SecretPattern {
  readonly kind: SecretRedaction["kind"];
  readonly expression: RegExp;
}

const SECRET_PATTERNS: readonly SecretPattern[] = [
  { kind: "cloud-key", expression: /\bAKIA[0-9A-Z]{16}\b/gu },
  { kind: "provider-token", expression: /\bsk-[A-Za-z0-9_-]{20,}\b/gu },
  { kind: "github-token", expression: /\bgh[pousr]_[A-Za-z0-9]{20,}\b/gu },
  {
    kind: "private-key",
    expression: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----/gu,
  },
  {
    kind: "named-secret",
    expression:
      /\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\b\s*[:=]\s*["']?[A-Za-z0-9_./+=-]{8,}["']?/giu,
  },
] as const;

export function sanitizeSourceText(
  input: string,
  policy: "redact" | "block" = "redact",
): SanitizedText {
  let text = input;
  const redactions: SecretRedaction[] = [];
  for (const pattern of SECRET_PATTERNS) {
    pattern.expression.lastIndex = 0;
    if (pattern.expression.test(text)) {
      if (policy === "block") {
        throw new SecretBlockedError();
      }
      pattern.expression.lastIndex = 0;
      text = text.replace(pattern.expression, () => {
        redactions.push(Object.freeze({ kind: pattern.kind }));
        return `[REDACTED:${pattern.kind}]`;
      });
    }
  }
  return Object.freeze({ text, redactions: Object.freeze(redactions) });
}

function groundSource(
  reference: SourceReference,
  snapshot: RepositorySnapshot,
  reader: SnapshotReader,
  policy: "redact" | "block",
): GroundedSource {
  const sourcePath = normalizeSafeSourcePath(reference.path);
  const file = snapshot.files.find((candidate) => candidate.path === sourcePath);
  if (file === undefined || file.kind !== "file") {
    throw new SourceMissingError();
  }
  const text = reader.readText(sourcePath);
  if (sha256Bytes(Buffer.from(text, "utf8")) !== file.contentHash) {
    throw new SourceDriftError();
  }
  let excerpt: string;
  let actualLineHash: string;
  try {
    excerpt = sourceLineSpan(text, reference.startLine, reference.endLine);
    actualLineHash = hashSourceLineSpan(text, reference.startLine, reference.endLine);
  } catch {
    throw new ClaimGroundingError("a claim line span falls outside its source file");
  }
  if (actualLineHash !== reference.lineHash) {
    throw new LineHashDriftError();
  }
  const sanitized = sanitizeSourceText(excerpt, policy);
  return Object.freeze({
    ...reference,
    path: sourcePath,
    excerpt: sanitized.text,
    untrusted: true,
    redactions: sanitized.redactions,
  });
}

export function groundClaims(
  input: unknown,
  reader: SnapshotReader,
  options: GroundClaimsOptions = {},
): GroundedClaimSet {
  const claimSet: ClaimSet = ClaimSetSchema.parse(input);
  const snapshot = RepositorySnapshotSchema.parse(reader.manifest);
  if (claimSet.sourceRevision !== snapshot.revision) {
    throw new ClaimGroundingError("claim set revision does not match the immutable snapshot");
  }
  const policy = options.secretPolicy ?? "redact";
  const claims = claimSet.claims.map((claim) =>
    Object.freeze({
      ...claim,
      sources: Object.freeze(claim.sources.map((source) => groundSource(source, snapshot, reader, policy))),
    }),
  );
  return Object.freeze({
    schemaVersion: 1 as const,
    sourceRevision: claimSet.sourceRevision,
    claims: Object.freeze(claims),
  });
}

export function assertEveryMaterialClaimGrounded(claims: readonly GroundedClaim[]): void {
  for (const claim of claims) {
    if (claim.material && claim.sources.length === 0) {
      throw new ClaimGroundingError("every material claim requires at least one resolved source");
    }
  }
}

