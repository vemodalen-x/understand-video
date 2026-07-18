import { canonicalHash, isSha256, sha256Bytes } from "./canonical.js";
import { GovernanceError } from "./errors.js";

export const REQUIRED_ARTIFACT_BINDINGS = [
  "snapshot",
  "claims",
  "storyboard",
  "narration",
  "captions",
  "media",
] as const;

export type ArtifactBindingName = (typeof REQUIRED_ARTIFACT_BINDINGS)[number];

export interface ArtifactBinding {
  readonly path: string;
  readonly sha256: `sha256:${string}`;
  readonly sizeBytes: number;
}

export interface FixtureGovernanceBinding {
  readonly mode: "fixture";
  readonly authoritative: false;
  readonly baselineCommit: string;
  readonly assessmentId: null;
  readonly assessmentHash: null;
  readonly warrantId: null;
  readonly warrantExpiresAt: null;
  readonly taskId: null;
  readonly lane: null;
  readonly action: null;
  readonly path: null;
  readonly startEventId: null;
  readonly startEventHash: null;
}

export interface EnforcedGovernanceBinding {
  readonly mode: "enforced";
  readonly authoritative: true;
  readonly baselineCommit: string;
  readonly assessmentId: string;
  readonly assessmentHash: `sha256:${string}`;
  readonly warrantId: string;
  readonly warrantExpiresAt: string;
  readonly taskId: string;
  readonly lane: string;
  readonly action: string;
  readonly path: string;
  readonly startEventId: string;
  readonly startEventHash: `sha256:${string}`;
}

export type GovernanceBinding = FixtureGovernanceBinding | EnforcedGovernanceBinding;

export interface ProviderBinding {
  readonly plannerMode: "fixture" | "gpt-5.6";
  readonly voiceMode: "fixture" | "approved-provider";
  readonly model: string | null;
  readonly requestId: string | null;
}

export interface ProductReceiptBody {
  readonly schemaVersion: "understand-video-receipt/v1";
  readonly generatedAt: string;
  readonly authoritative: boolean;
  readonly target: {
    readonly repository: string;
    readonly revision: string;
  };
  readonly artifacts: Readonly<Record<ArtifactBindingName, ArtifactBinding>>;
  readonly provider: ProviderBinding;
  readonly governance: GovernanceBinding;
  readonly verification: {
    readonly passed: true;
    readonly profile: string;
    readonly checks: readonly string[];
  };
}

export interface ProductReceipt extends ProductReceiptBody {
  readonly receiptHash: `sha256:${string}`;
}

export type ArtifactResolver = (binding: ArtifactBindingName, path: string) => string | Uint8Array;

function validateBindings(artifacts: Readonly<Record<ArtifactBindingName, ArtifactBinding>>): void {
  for (const name of REQUIRED_ARTIFACT_BINDINGS) {
    const binding = artifacts[name];
    if (binding === undefined) {
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

export function createProductReceipt(
  input: Omit<ProductReceiptBody, "schemaVersion" | "authoritative">,
): ProductReceipt {
  validateBindings(input.artifacts);

  const usesFixture =
    input.governance.mode === "fixture" ||
    input.provider.plannerMode === "fixture" ||
    input.provider.voiceMode === "fixture";
  const body: ProductReceiptBody = {
    schemaVersion: "understand-video-receipt/v1",
    generatedAt: input.generatedAt,
    authoritative: !usesFixture && input.governance.authoritative,
    target: input.target,
    artifacts: input.artifacts,
    provider: input.provider,
    governance: input.governance,
    verification: input.verification,
  };
  return { ...body, receiptHash: canonicalHash(body) };
}

export function verifyProductReceipt(receipt: ProductReceipt, resolveArtifact?: ArtifactResolver): void {
  const { receiptHash, ...body } = receipt;
  validateBindings(body.artifacts);
  if (!isSha256(receiptHash) || canonicalHash(body) !== receiptHash) {
    throw new GovernanceError("RECEIPT_TAMPERED", "Canonical receipt hash does not match its body");
  }

  const usesFixture =
    body.governance.mode === "fixture" ||
    body.provider.plannerMode === "fixture" ||
    body.provider.voiceMode === "fixture";
  if (usesFixture && body.authoritative) {
    throw new GovernanceError("RECEIPT_INVALID", "Fixture receipts must be authoritative:false");
  }

  if (resolveArtifact !== undefined) {
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

export function bindArtifact(path: string, bytes: string | Uint8Array): ArtifactBinding {
  return {
    path,
    sha256: sha256Bytes(bytes),
    sizeBytes: typeof bytes === "string" ? Buffer.byteLength(bytes) : bytes.byteLength,
  };
}
