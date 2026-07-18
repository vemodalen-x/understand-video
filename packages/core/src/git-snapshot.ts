import { spawnSync } from "node:child_process";
import { realpathSync } from "node:fs";
import path from "node:path";

import {
  RepositorySnapshotSchema,
  type RepositorySnapshot,
  type SnapshotFile,
} from "../../contracts/src/index.js";
import { sha256Bytes } from "./hash.js";

const MAX_GIT_OUTPUT_BYTES = 256 * 1024 * 1024;
const SAFE_REVISION = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$/u;
const decoder = new TextDecoder("utf-8", { fatal: true });

export class SnapshotSecurityError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "SnapshotSecurityError";
  }
}

export class UnknownRevisionError extends Error {
  public constructor() {
    super("the requested Git revision does not resolve to a commit");
    this.name = "UnknownRevisionError";
  }
}

export class DirtyRepositoryError extends Error {
  public constructor() {
    super("strict snapshot mode requires a clean Git working tree");
    this.name = "DirtyRepositoryError";
  }
}

export interface GitCommandAuditEntry {
  readonly executable: "git";
  readonly operation: string;
}

export interface SnapshotOptions {
  readonly root: string;
  readonly revision: string;
  readonly strict?: boolean;
  readonly selectedPaths?: readonly string[];
}

export interface SnapshotReader {
  readonly manifest: RepositorySnapshot;
  readonly processAudit: readonly GitCommandAuditEntry[];
  readText(sourcePath: string): string;
}

function validateRevisionInput(revision: string): void {
  if (!SAFE_REVISION.test(revision) || revision.includes("..") || revision.includes("//")) {
    throw new SnapshotSecurityError("the Git revision contains unsafe syntax");
  }
}

export function normalizeSafeSourcePath(sourcePath: string): string {
  if (
    sourcePath.length === 0 ||
    sourcePath.includes("\0") ||
    sourcePath.includes("\\") ||
    path.posix.isAbsolute(sourcePath) ||
    path.win32.isAbsolute(sourcePath) ||
    /^[A-Za-z]:/u.test(sourcePath)
  ) {
    throw new SnapshotSecurityError("source path must be a relative Git path");
  }
  const parts = sourcePath.split("/");
  if (parts.some((part) => part.length === 0 || part === "." || part === "..")) {
    throw new SnapshotSecurityError("source path contains traversal or ambiguous segments");
  }
  const normalized = path.posix.normalize(sourcePath);
  if (normalized !== sourcePath || normalized.startsWith("../")) {
    throw new SnapshotSecurityError("source path escapes the snapshot");
  }
  return normalized;
}

export function resolveSafeSymlinkTarget(linkPath: string, target: string): string {
  const safeLinkPath = normalizeSafeSourcePath(linkPath);
  if (
    target.length === 0 ||
    target.includes("\0") ||
    target.includes("\\") ||
    path.posix.isAbsolute(target) ||
    path.win32.isAbsolute(target) ||
    /^[A-Za-z]:/u.test(target)
  ) {
    throw new SnapshotSecurityError("symlink target must stay inside the snapshot");
  }
  const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(safeLinkPath), target));
  if (resolved === ".." || resolved.startsWith("../") || path.posix.isAbsolute(resolved)) {
    throw new SnapshotSecurityError("symlink target escapes the snapshot");
  }
  normalizeSafeSourcePath(resolved);
  return resolved;
}

interface GitResult {
  readonly status: number;
  readonly stdout: Buffer;
}

class GitObjectSnapshot implements SnapshotReader {
  public readonly manifest: RepositorySnapshot;
  readonly #root: string;
  readonly #audit: GitCommandAuditEntry[];
  readonly #fileByPath: ReadonlyMap<string, SnapshotFile>;

  public constructor(
    root: string,
    manifest: RepositorySnapshot,
    audit: GitCommandAuditEntry[],
  ) {
    this.#root = root;
    this.manifest = manifest;
    this.#audit = audit;
    this.#fileByPath = new Map(manifest.files.map((file) => [file.path, file]));
  }

  public get processAudit(): readonly GitCommandAuditEntry[] {
    return Object.freeze([...this.#audit]);
  }

  public readText(sourcePath: string): string {
    const safePath = normalizeSafeSourcePath(sourcePath);
    const file = this.#fileByPath.get(safePath);
    if (file === undefined) {
      throw new SnapshotSecurityError("source path is not present in the immutable snapshot");
    }
    if (file.kind !== "file") {
      throw new SnapshotSecurityError("symlinks cannot be read as source documents");
    }
    const result = runGit(this.#root, ["cat-file", "blob", file.oid], this.#audit, "read-blob");
    if (result.status !== 0) {
      throw new SnapshotSecurityError("the selected Git blob could not be read");
    }
    if (result.stdout.includes(0)) {
      throw new SnapshotSecurityError("binary Git blobs cannot be read as source text");
    }
    try {
      return decoder.decode(result.stdout);
    } catch {
      throw new SnapshotSecurityError("source text is not valid UTF-8");
    }
  }
}

function runGit(
  root: string,
  args: readonly string[],
  audit: GitCommandAuditEntry[],
  operation: string,
): GitResult {
  audit.push(Object.freeze({ executable: "git", operation }));
  const hardenedArgs = [
    "-c",
    "core.fsmonitor=false",
    "-c",
    `core.hooksPath=${path.join(root, ".understand-video-no-hooks")}`,
    ...args,
  ];
  const result = spawnSync("git", hardenedArgs, {
    cwd: root,
    encoding: null,
    windowsHide: true,
    maxBuffer: MAX_GIT_OUTPUT_BYTES,
    env: {
      ...process.env,
      GIT_OPTIONAL_LOCKS: "0",
      GIT_PAGER: "cat",
      GIT_TERMINAL_PROMPT: "0",
    },
  });
  if (result.error !== undefined) {
    throw new SnapshotSecurityError(`Git ${operation} failed without executing target code`);
  }
  return {
    status: result.status ?? 3,
    stdout: Buffer.isBuffer(result.stdout) ? result.stdout : Buffer.alloc(0),
  };
}

function decodeUtf8(value: Buffer, context: string): string {
  try {
    return decoder.decode(value);
  } catch {
    throw new SnapshotSecurityError(`${context} is not valid UTF-8`);
  }
}

function splitNull(value: Buffer): Buffer[] {
  const parts: Buffer[] = [];
  let start = 0;
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === 0) {
      parts.push(value.subarray(start, index));
      start = index + 1;
    }
  }
  if (start !== value.length) {
    throw new SnapshotSecurityError("Git returned a malformed NUL-delimited record");
  }
  return parts.filter((part) => part.length > 0);
}

function workingTreeIsDirty(root: string, audit: GitCommandAuditEntry[]): boolean {
  const tracked = runGit(
    root,
    ["diff-index", "--quiet", "--no-ext-diff", "HEAD", "--"],
    audit,
    "check-tracked-drift",
  );
  if (tracked.status > 1) {
    throw new SnapshotSecurityError("Git could not verify tracked working-tree state");
  }
  const untracked = runGit(
    root,
    ["ls-files", "--others", "--exclude-standard", "-z"],
    audit,
    "check-untracked-files",
  );
  if (untracked.status !== 0) {
    throw new SnapshotSecurityError("Git could not verify untracked working-tree state");
  }
  return tracked.status === 1 || untracked.stdout.length > 0;
}

function parseTreeEntry(entry: Buffer): { mode: string; oid: string; sourcePath: string } {
  const tab = entry.indexOf(9);
  if (tab < 0) {
    throw new SnapshotSecurityError("Git returned a malformed tree entry");
  }
  const metadata = decodeUtf8(entry.subarray(0, tab), "Git tree metadata").split(" ");
  if (metadata.length !== 3 || metadata[1] !== "blob") {
    throw new SnapshotSecurityError("Git tree entry has an unsupported object type");
  }
  const mode = metadata[0];
  const oid = metadata[2];
  if (mode === undefined || oid === undefined) {
    throw new SnapshotSecurityError("Git tree entry is incomplete");
  }
  if ((mode !== "100644" && mode !== "100755" && mode !== "120000") || !/^[0-9a-f]{40,64}$/u.test(oid)) {
    throw new SnapshotSecurityError("Git tree entry has an unsupported mode or object id");
  }
  const sourcePath = normalizeSafeSourcePath(decodeUtf8(entry.subarray(tab + 1), "Git path"));
  return { mode, oid, sourcePath };
}

export function snapshotGitRepository(options: SnapshotOptions): SnapshotReader {
  validateRevisionInput(options.revision);
  const root = realpathSync(options.root);
  const audit: GitCommandAuditEntry[] = [];
  const topLevelResult = runGit(root, ["rev-parse", "--show-toplevel"], audit, "resolve-root");
  if (topLevelResult.status !== 0) {
    throw new SnapshotSecurityError("snapshot root is not a Git working tree");
  }
  const topLevel = realpathSync(decodeUtf8(topLevelResult.stdout, "Git root").trim());
  if (path.normalize(topLevel).toLocaleLowerCase() !== path.normalize(root).toLocaleLowerCase()) {
    throw new SnapshotSecurityError("snapshot root must be the Git repository root");
  }

  const commitResult = runGit(
    root,
    ["rev-parse", "--verify", "--end-of-options", `${options.revision}^{commit}`],
    audit,
    "resolve-commit",
  );
  if (commitResult.status !== 0) {
    throw new UnknownRevisionError();
  }
  const revision = decodeUtf8(commitResult.stdout, "Git commit id").trim();
  if (!/^[0-9a-f]{40,64}$/u.test(revision)) {
    throw new SnapshotSecurityError("Git returned an invalid commit id");
  }

  const dirty = workingTreeIsDirty(root, audit);
  const strict = options.strict ?? true;
  if (strict && dirty) {
    throw new DirtyRepositoryError();
  }

  const treeResult = runGit(
    root,
    ["rev-parse", "--verify", "--end-of-options", `${revision}^{tree}`],
    audit,
    "resolve-tree",
  );
  if (treeResult.status !== 0) {
    throw new SnapshotSecurityError("Git could not resolve the selected commit tree");
  }
  const treeOid = decodeUtf8(treeResult.stdout, "Git tree id").trim();

  const treeEntries = runGit(
    root,
    ["ls-tree", "-r", "-z", "--full-tree", revision],
    audit,
    "list-tree",
  );
  if (treeEntries.status !== 0) {
    throw new SnapshotSecurityError("Git could not list the selected commit tree");
  }
  const selected = options.selectedPaths?.map(normalizeSafeSourcePath);
  const selectedSet = selected === undefined ? undefined : new Set(selected);
  const files: SnapshotFile[] = [];
  for (const rawEntry of splitNull(treeEntries.stdout)) {
    const { mode, oid, sourcePath } = parseTreeEntry(rawEntry);
    if (selectedSet !== undefined && !selectedSet.has(sourcePath)) {
      continue;
    }
    const blob = runGit(root, ["cat-file", "blob", oid], audit, "hash-blob");
    if (blob.status !== 0) {
      throw new SnapshotSecurityError("Git could not read a selected blob");
    }
    const kind = mode === "120000" ? "symlink" : "file";
    const symlinkTarget = kind === "symlink" ? decodeUtf8(blob.stdout, "symlink target") : undefined;
    if (symlinkTarget !== undefined) {
      resolveSafeSymlinkTarget(sourcePath, symlinkTarget);
    }
    files.push({
      path: sourcePath,
      oid,
      mode: mode as SnapshotFile["mode"],
      kind,
      byteLength: blob.stdout.length,
      contentHash: sha256Bytes(blob.stdout),
      ...(symlinkTarget === undefined ? {} : { symlinkTarget }),
    });
    selectedSet?.delete(sourcePath);
  }
  if (selectedSet !== undefined && selectedSet.size > 0) {
    throw new SnapshotSecurityError("one or more selected source paths do not exist at the pinned revision");
  }
  files.sort((left, right) => left.path.localeCompare(right.path, "en"));
  const manifest = RepositorySnapshotSchema.parse({
    schemaVersion: 1,
    repositoryRoot: root,
    revision,
    treeOid,
    strict,
    dirty,
    files,
  });
  return new GitObjectSnapshot(root, manifest, audit);
}

export function assertSnapshotRevision(snapshot: RepositorySnapshot, actualRevision: string): void {
  RepositorySnapshotSchema.parse(snapshot);
  if (snapshot.revision !== actualRevision) {
    throw new SnapshotSecurityError("target revision drifted after inspection");
  }
}
