import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { isSha256 } from "./canonical.js";
import { GovernanceError } from "./errors.js";
import type { EnforcedGovernanceBinding, FixtureGovernanceBinding, GovernanceBinding } from "./receipt.js";

export interface TempoBaseline {
  readonly repository: string;
  readonly branch: string;
  readonly commit: string;
  readonly relationship?: string;
  readonly vendored_files?: readonly string[];
}

export interface ExpectedStart {
  readonly taskId: string;
  readonly lane: string;
  readonly action: string;
  readonly path: string;
}

export interface CommandResult {
  readonly status: number | null;
  readonly stdout: string;
  readonly stderr: string;
  readonly error?: Error;
}

export interface CommandOptions {
  readonly cwd?: string;
}

export type CommandRunner = (
  command: string,
  args: readonly string[],
  options?: CommandOptions,
) => CommandResult;

export const runCommand: CommandRunner = (command, args, options = {}) => {
  const result = spawnSync(command, [...args], {
    cwd: options.cwd,
    encoding: "utf8",
    shell: false,
    windowsHide: true,
  });
  const response: CommandResult = {
    status: result.status,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
  if (result.error !== undefined) {
    return { ...response, error: result.error };
  }
  return response;
};

interface TempoStatus {
  readonly authorization_valid: boolean;
  readonly build_allowed: boolean;
  readonly expires_at: string | null;
  readonly mvp_state: string;
  readonly ok: boolean;
  readonly warrant_id: string | null;
}

interface WarrantRecord {
  readonly allowed_actions: readonly string[];
  readonly allowed_lanes: readonly string[];
  readonly allowed_scope: readonly string[];
  readonly assessment_ref: string;
  readonly expires_at: string;
  readonly hash_set: { readonly [key: string]: string };
  readonly revocation: { readonly revoked: boolean };
  readonly state: string;
  readonly warrant_id: string;
}

interface ActiveRecord {
  readonly action: string;
  readonly lane: string;
  readonly path: string;
  readonly task_id: string;
  readonly warrant_id: string;
}

interface AssessmentRecord {
  readonly assessment_hash: string;
  readonly assessment_id: string;
}

interface LedgerEvent {
  readonly details?: { readonly action?: string; readonly lane?: string; readonly path?: string };
  readonly event_hash: string;
  readonly event_id: string;
  readonly event_type: string;
  readonly relevant_ids: {
    readonly assessment_id?: string;
    readonly task_id?: string;
    readonly warrant_id?: string;
  };
}

export interface FixtureGovernanceOptions {
  readonly mode: "fixture";
  readonly baselinePath: string;
}

export interface EnforcedGovernanceOptions {
  readonly mode: "enforced";
  readonly baselinePath: string;
  readonly tempoCheckout: string;
  readonly governanceRoot: string;
  readonly expectedStart: ExpectedStart;
  readonly pythonCommand?: string;
  readonly now?: Date;
  readonly runner?: CommandRunner;
}

export type GovernanceOptions = FixtureGovernanceOptions | EnforcedGovernanceOptions;

function readJson<T>(path: string, code: "BASELINE_INVALID" | "WARRANT_INVALID" | "START_RECEIPT_MISSING"): T {
  try {
    return JSON.parse(readFileSync(path, "utf8")) as T;
  } catch (error) {
    throw new GovernanceError(code, `Cannot read valid JSON from ${path}: ${String(error)}`);
  }
}

export function validateBaselineMetadata(baseline: TempoBaseline): void {
  if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?$/.test(baseline.repository)) {
    throw new GovernanceError("BASELINE_INVALID", "TEMPO baseline repository must be an explicit GitHub HTTPS URL");
  }
  if (!/^[0-9a-f]{40}$/.test(baseline.commit)) {
    throw new GovernanceError("BASELINE_INVALID", "TEMPO baseline must contain a full lowercase Git commit SHA");
  }
  if (baseline.branch.length === 0) {
    throw new GovernanceError("BASELINE_INVALID", "TEMPO baseline branch is missing");
  }
  if (baseline.vendored_files !== undefined && baseline.vendored_files.length > 0) {
    throw new GovernanceError("BASELINE_INVALID", "TEMPO framework files must not be vendored into the product");
  }
}

function normalizeRepository(value: string): string {
  return value.trim().replace(/\.git$/i, "").replace(/\/$/, "").toLowerCase();
}

function requireCommand(result: CommandResult, purpose: string): string {
  if (result.error !== undefined || result.status !== 0) {
    throw new GovernanceError(
      "TEMPO_COMMAND_FAILED",
      `${purpose} failed (${String(result.status)}): ${result.stderr.trim() || result.error?.message || "no diagnostic"}`,
    );
  }
  return result.stdout.trim();
}

function parseCommandJson<T>(result: CommandResult, purpose: string): T {
  const output = requireCommand(result, purpose);
  try {
    return JSON.parse(output) as T;
  } catch (error) {
    throw new GovernanceError("TEMPO_RESPONSE_INVALID", `${purpose} returned invalid JSON: ${String(error)}`);
  }
}

function normalizeGovernedPath(value: string): string {
  const path = value.replace(/\\/g, "/").replace(/^\.\//, "");
  if (path.length === 0 || path.startsWith("/") || /^[A-Za-z]:\//.test(path) || path.split("/").includes("..")) {
    throw new GovernanceError("START_SCOPE_MISMATCH", `Unsafe governed path: ${value}`);
  }
  return path;
}

function scopeAllows(path: string, allowedScope: readonly string[]): boolean {
  const normalized = normalizeGovernedPath(path);
  return allowedScope.some((entry) => {
    const rule = normalizeGovernedPath(entry);
    if (rule.endsWith("/**")) {
      const prefix = rule.slice(0, -3);
      return normalized === prefix || normalized.startsWith(`${prefix}/`);
    }
    return normalized === rule;
  });
}

function requireStartMatch(actual: ActiveRecord, expected: ExpectedStart, warrantId: string): void {
  if (
    actual.task_id !== expected.taskId ||
    actual.lane !== expected.lane ||
    actual.action !== expected.action ||
    normalizeGovernedPath(actual.path) !== normalizeGovernedPath(expected.path) ||
    actual.warrant_id !== warrantId
  ) {
    throw new GovernanceError("START_SCOPE_MISMATCH", "Active TEMPO start does not match task, lane, action, path, and warrant");
  }
}

function findStartEvent(events: readonly LedgerEvent[], active: ActiveRecord): LedgerEvent {
  const event = [...events].reverse().find(
    (candidate) =>
      candidate.event_type === "mvp_started" &&
      candidate.relevant_ids.warrant_id === active.warrant_id &&
      candidate.relevant_ids.task_id === active.task_id,
  );
  if (event === undefined) {
    throw new GovernanceError("START_RECEIPT_MISSING", "Verified ledger has no matching mvp_started event");
  }
  if (
    event.details?.lane !== active.lane ||
    event.details.action !== active.action ||
    normalizeGovernedPath(event.details.path ?? "") !== normalizeGovernedPath(active.path)
  ) {
    throw new GovernanceError("START_SCOPE_MISMATCH", "Ledger start event does not match the active start record");
  }
  if (!isSha256(event.event_hash)) {
    throw new GovernanceError("START_RECEIPT_MISSING", "Start event has no canonical event hash");
  }
  return event;
}

function readLedger(path: string): LedgerEvent[] {
  try {
    return readFileSync(path, "utf8")
      .split(/\r?\n/)
      .filter((line) => line.trim().length > 0)
      .map((line) => JSON.parse(line) as LedgerEvent);
  } catch (error) {
    throw new GovernanceError("LEDGER_INVALID", `Cannot parse external TEMPO ledger: ${String(error)}`);
  }
}

export function validateGovernance(options: GovernanceOptions): GovernanceBinding {
  const baseline = readJson<TempoBaseline>(resolve(options.baselinePath), "BASELINE_INVALID");
  validateBaselineMetadata(baseline);

  if (options.mode === "fixture") {
    const binding: FixtureGovernanceBinding = {
      mode: "fixture",
      authoritative: false,
      baselineCommit: baseline.commit,
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
    };
    return binding;
  }

  const checkout = resolve(options.tempoCheckout);
  const governanceRoot = resolve(options.governanceRoot);
  if (!existsSync(checkout) || !statSync(checkout).isDirectory()) {
    throw new GovernanceError("TEMPO_CHECKOUT_MISSING", `Independent TEMPO checkout is missing: ${checkout}`);
  }
  if (!existsSync(governanceRoot) || !statSync(governanceRoot).isDirectory()) {
    throw new GovernanceError("GOVERNANCE_ROOT_MISSING", `External governance root is missing: ${governanceRoot}`);
  }

  const runner = options.runner ?? runCommand;
  const head = requireCommand(runner("git", ["-C", checkout, "rev-parse", "HEAD"]), "TEMPO HEAD check");
  if (head !== baseline.commit) {
    throw new GovernanceError("TEMPO_CHECKOUT_DRIFT", `TEMPO checkout is ${head}; expected ${baseline.commit}`);
  }
  const dirty = requireCommand(runner("git", ["-C", checkout, "status", "--porcelain"]), "TEMPO cleanliness check");
  if (dirty.length > 0) {
    throw new GovernanceError("TEMPO_CHECKOUT_DIRTY", "TEMPO checkout contains uncommitted or untracked changes");
  }
  const origin = requireCommand(runner("git", ["-C", checkout, "remote", "get-url", "origin"]), "TEMPO origin check");
  if (normalizeRepository(origin) !== normalizeRepository(baseline.repository)) {
    throw new GovernanceError("TEMPO_ORIGIN_MISMATCH", `TEMPO origin ${origin} does not match ${baseline.repository}`);
  }

  const tempoCli = join(checkout, "bin", "tempo");
  if (!existsSync(tempoCli)) {
    throw new GovernanceError("TEMPO_CHECKOUT_MISSING", `Pinned checkout has no bin/tempo entrypoint: ${tempoCli}`);
  }
  const commonArgs = [
    tempoCli,
    "--root",
    governanceRoot,
    "--actor",
    "agent:understand-video",
    "--session",
    "understand-video:governance-adapter",
    "--json",
  ];
  const python = options.pythonCommand ?? "python";
  const status = parseCommandJson<TempoStatus>(
    runner(python, [...commonArgs, "mvp", "status"], { cwd: checkout }),
    "TEMPO mvp status",
  );
  const ledgerStatus = parseCommandJson<{ readonly ok: boolean; readonly outcome: string }>(
    runner(python, [...commonArgs, "ledger", "verify"], { cwd: checkout }),
    "TEMPO ledger verify",
  );
  if (!ledgerStatus.ok || ledgerStatus.outcome !== "LEDGER_VALID") {
    throw new GovernanceError("LEDGER_INVALID", "TEMPO ledger verification did not return LEDGER_VALID");
  }

  const warrantPath = join(governanceRoot, "plan", "authorization-warrant.json");
  if (!existsSync(warrantPath)) {
    throw new GovernanceError("WARRANT_MISSING", `Warrant is missing: ${warrantPath}`);
  }
  const warrant = readJson<WarrantRecord>(warrantPath, "WARRANT_INVALID");
  if (warrant.revocation.revoked || warrant.state !== "active") {
    throw new GovernanceError("WARRANT_REVOKED", "Warrant is revoked or non-active");
  }
  const expiry = Date.parse(warrant.expires_at);
  const now = (options.now ?? new Date()).getTime();
  if (!Number.isFinite(expiry) || expiry <= now) {
    throw new GovernanceError("WARRANT_EXPIRED", `Warrant expired at ${warrant.expires_at}`);
  }
  if (
    !status.ok ||
    !status.authorization_valid ||
    !status.build_allowed ||
    status.mvp_state !== "BUILDING" ||
    status.warrant_id !== warrant.warrant_id ||
    status.expires_at !== warrant.expires_at
  ) {
    throw new GovernanceError("WARRANT_INVALID", "TEMPO status does not confirm the active build warrant");
  }

  const expected = options.expectedStart;
  if (
    !warrant.allowed_actions.includes(expected.action) ||
    !warrant.allowed_lanes.includes(expected.lane) ||
    !scopeAllows(expected.path, warrant.allowed_scope)
  ) {
    throw new GovernanceError("START_SCOPE_MISMATCH", "Expected start is outside the warrant's action, lane, or scope");
  }

  const activePath = join(governanceRoot, ".tempo", "run", "active.json");
  const active = readJson<ActiveRecord>(activePath, "START_RECEIPT_MISSING");
  requireStartMatch(active, expected, warrant.warrant_id);
  const events = readLedger(join(governanceRoot, ".tempo", "ledger.jsonl"));
  const startEvent = findStartEvent(events, active);
  const assessmentPath = join(governanceRoot, ".tempo", "assessments", `${warrant.assessment_ref}.json`);
  const assessment = readJson<AssessmentRecord>(assessmentPath, "WARRANT_INVALID");
  if (assessment.assessment_id !== warrant.assessment_ref || !isSha256(assessment.assessment_hash)) {
    throw new GovernanceError("WARRANT_INVALID", "Warrant assessment reference does not resolve to a hash-bound assessment");
  }

  const binding: EnforcedGovernanceBinding = {
    mode: "enforced",
    authoritative: true,
    baselineCommit: baseline.commit,
    assessmentId: warrant.assessment_ref,
    assessmentHash: assessment.assessment_hash,
    warrantId: warrant.warrant_id,
    warrantExpiresAt: warrant.expires_at,
    taskId: active.task_id,
    lane: active.lane,
    action: active.action,
    path: active.path,
    startEventId: startEvent.event_id,
    startEventHash: startEvent.event_hash as `sha256:${string}`,
  };
  return binding;
}
