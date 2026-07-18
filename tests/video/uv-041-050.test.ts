import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

import { describe, expect, test } from "vitest";

import {
  REQUIRED_ARTIFACT_BINDINGS,
  TEMPO_GOLDEN_SOURCES,
  bindArtifact,
  createProductReceipt,
  validateGovernance,
  verifyGoldenSourcesAtCommit,
  verifyProductReceipt,
  type ArtifactBindingName,
  type CommandRunner,
  type EnforcedGovernanceOptions,
  type ProductReceipt,
} from "../../packages/governance-adapter/src/index.js";
import {
  DEMO_SUCCESS_SENTINEL,
  PIPELINE_STAGES,
  runDemo,
  runPipeline,
  type PipelineHandlers,
} from "../../packages/cli/src/orchestrator.js";

const PINNED_COMMIT = "4afc6a3f5ceba0240f7fdd2eece96241253d6e60";
const REPOSITORY = "https://github.com/vemodalen-x/TEMPO";
const EXPECTED_START = {
  taskId: "T-20260718-UNDERSTAND-VIDEO-FOUNDER-MVP",
  lane: "video-core",
  action: "implementation_write",
  path: "product/packages/cli/src/main.ts",
} as const;

interface GovernanceFixture {
  readonly root: string;
  readonly checkout: string;
  readonly governanceRoot: string;
  readonly baselinePath: string;
  readonly warrantPath: string;
  readonly status: Record<string, unknown>;
  readonly runner: CommandRunner;
  readonly options: EnforcedGovernanceOptions;
}

function json(path: string, value: unknown): void {
  mkdirSync(resolve(path, ".."), { recursive: true });
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function makeGovernanceFixture(overrides: { readonly head?: string; readonly expiresAt?: string } = {}): GovernanceFixture {
  const root = mkdtempSync(join(tmpdir(), "understand-video-governance-"));
  const checkout = join(root, "tempo");
  const governanceRoot = join(root, "governance");
  const baselinePath = join(root, "TEMPO_BASELINE.json");
  const warrantPath = join(governanceRoot, "plan", "authorization-warrant.json");
  const warrantId = "W-TESTGOVERNANCE001";
  const assessmentId = "A-TESTASSESSMENT01";
  const expiresAt = overrides.expiresAt ?? "2030-01-01T00:00:00Z";
  mkdirSync(join(checkout, "bin"), { recursive: true });
  writeFileSync(join(checkout, "bin", "tempo"), "external fixture entrypoint\n", "utf8");
  json(baselinePath, {
    repository: REPOSITORY,
    branch: "main",
    commit: PINNED_COMMIT,
    relationship: "external_governance_dependency",
    vendored_files: [],
  });
  json(warrantPath, {
    allowed_actions: ["implementation_write", "test", "build", "local_demo"],
    allowed_lanes: ["video-core"],
    allowed_scope: ["product/packages/**", "product/tests/video/**", "product/submission/**"],
    assessment_ref: assessmentId,
    expires_at: expiresAt,
    hash_set: { mvp_charter: `sha256:${"a".repeat(64)}` },
    revocation: { revoked: false },
    state: "active",
    warrant_id: warrantId,
  });
  json(join(governanceRoot, ".tempo", "assessments", `${assessmentId}.json`), {
    assessment_id: assessmentId,
    assessment_hash: `sha256:${"b".repeat(64)}`,
  });
  json(join(governanceRoot, ".tempo", "run", "active.json"), {
    action: EXPECTED_START.action,
    lane: EXPECTED_START.lane,
    path: EXPECTED_START.path,
    task_id: EXPECTED_START.taskId,
    warrant_id: warrantId,
  });
  writeFileSync(
    join(governanceRoot, ".tempo", "ledger.jsonl"),
    `${JSON.stringify({
      event_type: "mvp_started",
      event_id: "EVT-TESTSTART0001",
      event_hash: `sha256:${"c".repeat(64)}`,
      relevant_ids: { task_id: EXPECTED_START.taskId, warrant_id: warrantId },
      details: { action: EXPECTED_START.action, lane: EXPECTED_START.lane, path: EXPECTED_START.path },
    })}\n`,
    "utf8",
  );
  const status: Record<string, unknown> = {
    authorization_valid: true,
    build_allowed: true,
    expires_at: expiresAt,
    mvp_state: "BUILDING",
    ok: true,
    warrant_id: warrantId,
  };
  const runner: CommandRunner = (command, args) => {
    const joined = `${command} ${args.join(" ")}`;
    if (joined.includes("rev-parse HEAD")) {
      return { status: 0, stdout: `${overrides.head ?? PINNED_COMMIT}\n`, stderr: "" };
    }
    if (joined.includes("status --porcelain")) {
      return { status: 0, stdout: "", stderr: "" };
    }
    if (joined.includes("remote get-url origin")) {
      return { status: 0, stdout: `${REPOSITORY}.git\n`, stderr: "" };
    }
    if (joined.includes("mvp status")) {
      return { status: 0, stdout: JSON.stringify(status), stderr: "" };
    }
    if (joined.includes("ledger verify")) {
      return { status: 0, stdout: JSON.stringify({ ok: true, outcome: "LEDGER_VALID" }), stderr: "" };
    }
    return { status: 99, stdout: "", stderr: `unexpected argv: ${joined}` };
  };
  return {
    root,
    checkout,
    governanceRoot,
    baselinePath,
    warrantPath,
    status,
    runner,
    options: {
      mode: "enforced",
      baselinePath,
      tempoCheckout: checkout,
      governanceRoot,
      expectedStart: EXPECTED_START,
      now: new Date("2026-07-19T00:00:00Z"),
      runner,
    },
  };
}

function makeReceipt(): { readonly receipt: ProductReceipt; readonly bytes: Record<ArtifactBindingName, Buffer> } {
  const bytes = Object.fromEntries(
    REQUIRED_ARTIFACT_BINDINGS.map((name) => [name, Buffer.from(`${name}-artifact`, "utf8")]),
  ) as Record<ArtifactBindingName, Buffer>;
  const artifacts = Object.fromEntries(
    REQUIRED_ARTIFACT_BINDINGS.map((name) => [name, bindArtifact(`artifacts/${name}`, bytes[name])]),
  ) as Record<ArtifactBindingName, ReturnType<typeof bindArtifact>>;
  const receipt = createProductReceipt({
    generatedAt: "2026-07-19T00:00:00Z",
    target: { repository: "fixture://repo", revision: "1".repeat(40) },
    artifacts,
    provider: { plannerMode: "fixture", voiceMode: "fixture", model: null, requestId: null },
    governance: {
      mode: "fixture",
      authoritative: false,
      baselineCommit: PINNED_COMMIT,
      assessmentId: null,
      assessmentHash: null,
      warrantId: null,
      warrantExpiresAt: null,
      taskId: null,
      lane: null,
      action: null,
      path: null,
      startEventId: null,
      startEventHash: null,
    },
    verification: { passed: true, profile: "test", checks: ["all-bound"] },
  });
  return { receipt, bytes };
}

function memoryHandlers(failAt?: keyof PipelineHandlers): PipelineHandlers {
  return Object.fromEntries(
    PIPELINE_STAGES.map((stage) => [
      stage,
      () => ({ ok: stage !== failAt, summary: stage === failAt ? "intentional failure" : `${stage} complete` }),
    ]),
  ) as unknown as PipelineHandlers;
}

describe("Governance, receipt, and judge acceptance", () => {
  test("UV-041 rejects a missing independent TEMPO checkout only in enforced mode", () => {
    const fixture = makeGovernanceFixture();
    const fixtureBinding = validateGovernance({ mode: "fixture", baselinePath: fixture.baselinePath });
    expect(fixtureBinding).toMatchObject({ mode: "fixture", authoritative: false, warrantId: null });
    expect(() =>
      validateGovernance({
        ...fixture.options,
        tempoCheckout: join(fixture.root, "missing-tempo-checkout"),
      }),
    ).toThrowError(expect.objectContaining({ code: "TEMPO_CHECKOUT_MISSING" }));
  });

  test("UV-042 rejects enforced checkout drift while fixture mode validates baseline metadata", () => {
    const drifted = makeGovernanceFixture({ head: "d".repeat(40) });
    expect(() => validateGovernance(drifted.options)).toThrowError(
      expect.objectContaining({ code: "TEMPO_CHECKOUT_DRIFT" }),
    );
    json(drifted.baselinePath, { repository: REPOSITORY, branch: "main", commit: "4afc6a3", vendored_files: [] });
    expect(() => validateGovernance({ mode: "fixture", baselinePath: drifted.baselinePath })).toThrowError(
      expect.objectContaining({ code: "BASELINE_INVALID" }),
    );
  });

  test("UV-043 rejects missing, expired, revoked, and status-invalidated warrants", () => {
    const missing = makeGovernanceFixture();
    unlinkSync(missing.warrantPath);
    expect(() => validateGovernance(missing.options)).toThrowError(expect.objectContaining({ code: "WARRANT_MISSING" }));

    const expired = makeGovernanceFixture({ expiresAt: "2020-01-01T00:00:00Z" });
    expect(() => validateGovernance(expired.options)).toThrowError(expect.objectContaining({ code: "WARRANT_EXPIRED" }));

    const revoked = makeGovernanceFixture();
    const revokedWarrant = JSON.parse(readFileSync(revoked.warrantPath, "utf8")) as Record<string, unknown>;
    revokedWarrant["revocation"] = { revoked: true };
    json(revoked.warrantPath, revokedWarrant);
    expect(() => validateGovernance(revoked.options)).toThrowError(expect.objectContaining({ code: "WARRANT_REVOKED" }));

    const invalidated = makeGovernanceFixture();
    invalidated.status["authorization_valid"] = false;
    invalidated.status["build_allowed"] = false;
    expect(() => validateGovernance(invalidated.options)).toThrowError(expect.objectContaining({ code: "WARRANT_INVALID" }));
  });

  test("UV-044 rejects task execution outside the warrant path, lane, action, or task start", () => {
    const fixture = makeGovernanceFixture();
    expect(() =>
      validateGovernance({
        ...fixture.options,
        expectedStart: { ...EXPECTED_START, path: "product/private/secret.txt" },
      }),
    ).toThrowError(expect.objectContaining({ code: "START_SCOPE_MISMATCH" }));
  });

  test("UV-045 binds snapshot, claims, storyboard, narration, captions, media, and provider mode", () => {
    const { receipt, bytes } = makeReceipt();
    expect(Object.keys(receipt.artifacts).sort()).toEqual([...REQUIRED_ARTIFACT_BINDINGS].sort());
    expect(receipt).toMatchObject({
      schemaVersion: "understand-video-receipt/v1",
      authoritative: false,
      provider: { plannerMode: "fixture", voiceMode: "fixture" },
    });
    expect(() => verifyProductReceipt(receipt, (name) => bytes[name])).not.toThrow();
  });

  test("UV-046 detects canonical receipt and bound-artifact hash tampering", () => {
    const { receipt, bytes } = makeReceipt();
    const changedReceipt = JSON.parse(JSON.stringify(receipt)) as ProductReceipt;
    (changedReceipt.target as { repository: string }).repository = "fixture://tampered";
    expect(() => verifyProductReceipt(changedReceipt)).toThrowError(
      expect.objectContaining({ code: "RECEIPT_TAMPERED" }),
    );
    expect(() =>
      verifyProductReceipt(receipt, (name) => (name === "media" ? Buffer.from("tampered") : bytes[name])),
    ).toThrowError(expect.objectContaining({ code: "BOUND_ARTIFACT_TAMPERED" }));
  });

  test("UV-047 completes the credential-free offline inspect-to-verify orchestration", async () => {
    const output: string[] = [];
    const result = await runPipeline(
      memoryHandlers(),
      { workspace: join(tmpdir(), "uv-offline"), offline: true },
      PIPELINE_STAGES,
      (line) => output.push(line),
    );
    expect(result).toMatchObject({ ok: true, failedStage: null, completed: PIPELINE_STAGES });
    expect(output.filter((line) => line.endsWith("running"))).toHaveLength(5);
    expect(process.env["OPENAI_API_KEY"]).not.toBe("required-by-fixture");
  });

  test("UV-048 runs the prepared judge bundle without pnpm, node_modules, or a source rebuild", () => {
    const isolated = mkdtempSync(join(tmpdir(), "understand-video-judge-bundle-"));
    const sourceBundle = resolve("submission", "judge-bundle", "understand-video-demo.mjs");
    const isolatedBundle = join(isolated, "understand-video-demo.mjs");
    copyFileSync(sourceBundle, isolatedBundle);
    const result = spawnSync(process.execPath, [isolatedBundle, "demo", "--offline", "--workdir", join(isolated, ".understand-video")], {
      cwd: isolated,
      encoding: "utf8",
      shell: false,
      windowsHide: true,
      env: { ...process.env, OPENAI_API_KEY: "" },
    });
    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain(DEMO_SUCCESS_SENTINEL);
    expect(result.stdout.split(DEMO_SUCCESS_SENTINEL)).toHaveLength(2);
    expect(result.stdout).toContain("authoritative:false");
  }, 30_000);

  test("UV-049 resolves every required TEMPO golden source reference at the pinned commit", () => {
    const calls: string[] = [];
    const resolved = verifyGoldenSourcesAtCommit(PINNED_COMMIT, (commit, path) => {
      calls.push(`${commit}:${path}`);
      const reference = TEMPO_GOLDEN_SOURCES.find((candidate) => candidate.path === path);
      if (reference === undefined) {
        throw new Error(`unexpected source ${path}`);
      }
      return `fixture prefix ${reference.contains} fixture suffix`;
    });
    expect(resolved).toHaveLength(TEMPO_GOLDEN_SOURCES.length);
    expect(calls).toEqual(TEMPO_GOLDEN_SOURCES.map((reference) => `${PINNED_COMMIT}:${reference.path}`));
  });

  test("UV-050 emits the success sentinel only after every required stage passes", async () => {
    const failedOutput: string[] = [];
    const failed = await runDemo(
      memoryHandlers("verify"),
      { workspace: join(tmpdir(), "uv-failed-demo"), offline: true },
      (line) => failedOutput.push(line),
    );
    expect(failed.ok).toBe(false);
    expect(failedOutput).not.toContain(DEMO_SUCCESS_SENTINEL);

    const passedOutput: string[] = [];
    const passed = await runDemo(
      memoryHandlers(),
      { workspace: join(tmpdir(), "uv-passed-demo"), offline: true },
      (line) => passedOutput.push(line),
    );
    expect(passed.ok).toBe(true);
    expect(passedOutput.at(-1)).toBe(DEMO_SUCCESS_SENTINEL);
    expect(passedOutput.filter((line) => line === DEMO_SUCCESS_SENTINEL)).toHaveLength(1);
  });
});
