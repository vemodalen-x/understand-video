import type { CommandRunner } from "./adapter.js";
import { runCommand } from "./adapter.js";
import { GovernanceError } from "./errors.js";

export interface GoldenSourceReference {
  readonly claimId: string;
  readonly path: string;
  readonly contains: string;
}

export const TEMPO_GOLDEN_SOURCES: readonly GoldenSourceReference[] = [
  { claimId: "C-TEMPO-001", path: "src/tempo/cli.py", contains: "def main" },
  { claimId: "C-TEMPO-002", path: "src/tempo/providers.py", contains: "provider" },
  { claimId: "C-TEMPO-003", path: "src/tempo/readiness.py", contains: "assessment" },
  { claimId: "C-TEMPO-004", path: "src/tempo/warrant.py", contains: "mvp_started" },
  { claimId: "C-TEMPO-005", path: "src/tempo/guards.py", contains: "scope" },
  { claimId: "C-TEMPO-006", path: "src/tempo/ledger.py", contains: "event_hash" },
] as const;

export type GitObjectReader = (commit: string, path: string) => string;

export function createGitObjectReader(checkout: string, runner: CommandRunner = runCommand): GitObjectReader {
  return (commit, path) => {
    if (!/^[0-9a-f]{40}$/.test(commit) || path.startsWith("/") || path.split(/[\\/]/).includes("..")) {
      throw new GovernanceError("BASELINE_INVALID", "Unsafe Git object reference");
    }
    const result = runner("git", ["-C", checkout, "show", `${commit}:${path}`]);
    if (result.error !== undefined || result.status !== 0) {
      throw new GovernanceError("BASELINE_INVALID", `Cannot resolve ${commit}:${path}`);
    }
    return result.stdout;
  };
}

export function verifyGoldenSourcesAtCommit(
  commit: string,
  reader: GitObjectReader,
  references: readonly GoldenSourceReference[] = TEMPO_GOLDEN_SOURCES,
): readonly string[] {
  if (!/^[0-9a-f]{40}$/.test(commit)) {
    throw new GovernanceError("BASELINE_INVALID", "Golden source resolution requires a full pinned commit");
  }
  return references.map((reference) => {
    const source = reader(commit, reference.path);
    if (!source.includes(reference.contains)) {
      throw new GovernanceError(
        "BASELINE_INVALID",
        `${reference.claimId} marker is missing from ${commit}:${reference.path}`,
      );
    }
    return `${reference.claimId}@${commit}:${reference.path}`;
  });
}
