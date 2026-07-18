import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { normalizeSafeSourcePath } from "./git-snapshot.js";
import { sha256Bytes, stableJson } from "./hash.js";

const REQUIRED_FILES = [
  "config.json",
  "fingerprints.json",
  "knowledge-graph.json",
  "meta.json",
  "provenance.json",
  "review.json",
] as const;

export interface UnderstandAnythingExpectation {
  readonly targetRepository: string;
  readonly targetCommit: string;
  readonly upstreamRepository: string;
  readonly upstreamCommit: string;
  readonly hashes: Readonly<Record<(typeof REQUIRED_FILES)[number], `sha256:${string}`>>;
}

export interface UnderstandAnythingBundle {
  readonly directory: string;
  readonly targetCommit: string;
  readonly upstreamCommit: string;
  readonly nodeCount: number;
  readonly edgeCount: number;
  readonly layerCount: number;
  readonly tourCount: number;
  readonly fileCount: number;
  readonly hashes: UnderstandAnythingExpectation["hashes"];
  readonly graph: Readonly<Record<string, unknown>>;
  readonly provenance: Readonly<Record<string, unknown>>;
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function array(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(`${label} must be an array`);
  }
  return value;
}

function string(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function boolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(`${label} must be a boolean`);
  }
  return value;
}

function parseJson(raw: string, label: string): Record<string, unknown> {
  try {
    return record(JSON.parse(raw) as unknown, label);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function readBoundFile(root: string, name: (typeof REQUIRED_FILES)[number]): { raw: string; hash: `sha256:${string}` } {
  const path = join(root, name);
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink()) {
    throw new Error(`${name} must be a regular non-symlink file`);
  }
  const real = realpathSync(path);
  const relation = relative(root, real);
  if (relation.startsWith("..") || resolve(root, relation) !== real) {
    throw new Error(`${name} escapes the bundle directory`);
  }
  const raw = readFileSync(real, "utf8");
  return { raw, hash: sha256Bytes(raw) };
}

export function loadUnderstandAnythingBundle(
  directory: string,
  expected: UnderstandAnythingExpectation,
): UnderstandAnythingBundle {
  const root = realpathSync(resolve(directory));
  const raws = {} as Record<(typeof REQUIRED_FILES)[number], string>;
  const hashes = {} as Record<(typeof REQUIRED_FILES)[number], `sha256:${string}`>;
  for (const name of REQUIRED_FILES) {
    const file = readBoundFile(root, name);
    raws[name] = file.raw;
    hashes[name] = file.hash;
    if (file.hash !== expected.hashes[name]) {
      throw new Error(`${name} hash does not match the reviewed bundle`);
    }
  }

  const graph = parseJson(raws["knowledge-graph.json"], "knowledge graph");
  const meta = parseJson(raws["meta.json"], "metadata");
  const provenance = parseJson(raws["provenance.json"], "provenance");
  const fingerprints = parseJson(raws["fingerprints.json"], "fingerprints");
  const review = parseJson(raws["review.json"], "review");

  if (
    meta.gitCommitHash !== expected.targetCommit ||
    graph.project === undefined ||
    record(graph.project, "graph.project").gitCommitHash !== expected.targetCommit ||
    provenance.targetGitCommitHash !== expected.targetCommit ||
    provenance.targetRepository !== expected.targetRepository ||
    provenance.understandAnythingGitCommitHash !== expected.upstreamCommit ||
    provenance.understandAnythingRepository !== expected.upstreamRepository
  ) {
    throw new Error("bundle repository or commit provenance does not match the requested snapshot");
  }
  const safety = record(provenance.safety, "provenance.safety");
  const synthesis = record(provenance.semanticSynthesis, "provenance.semanticSynthesis");
  if (
    boolean(safety.targetSourceExecuted, "targetSourceExecuted") ||
    boolean(safety.targetDependenciesInstalled, "targetDependenciesInstalled") ||
    boolean(synthesis.nativeFullUnderstandExecution, "nativeFullUnderstandExecution")
  ) {
    throw new Error("bundle safety/provenance claims are inconsistent with the reviewed static-analysis mode");
  }
  if (stableJson(meta.provenance) !== stableJson(provenance)) {
    throw new Error("metadata and standalone provenance records disagree");
  }

  const nodes = array(graph.nodes, "graph.nodes").map((item, index) => record(item, `node ${index}`));
  const edges = array(graph.edges, "graph.edges").map((item, index) => record(item, `edge ${index}`));
  const layers = array(graph.layers, "graph.layers").map((item, index) => record(item, `layer ${index}`));
  const tour = array(graph.tour, "graph.tour").map((item, index) => record(item, `tour ${index}`));
  const nodeIds = new Set<string>();
  for (const node of nodes) {
    const id = string(node.id, "node.id");
    if (nodeIds.has(id)) {
      throw new Error(`duplicate graph node: ${id}`);
    }
    nodeIds.add(id);
    if (node.filePath !== undefined) {
      normalizeSafeSourcePath(string(node.filePath, `${id}.filePath`));
    }
  }
  const edgeIds = new Set<string>();
  for (const edge of edges) {
    const source = string(edge.source, "edge.source");
    const target = string(edge.target, "edge.target");
    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      throw new Error(`graph edge has a dangling endpoint: ${source} -> ${target}`);
    }
    const identity = `${source}\u0000${string(edge.type, "edge.type")}\u0000${target}`;
    if (edgeIds.has(identity)) {
      throw new Error(`duplicate graph edge: ${source} -> ${target}`);
    }
    edgeIds.add(identity);
  }
  for (const group of [...layers, ...tour]) {
    for (const nodeId of array(group.nodeIds, "group.nodeIds")) {
      if (!nodeIds.has(string(nodeId, "group.nodeId"))) {
        throw new Error(`layer or tour references an unknown node: ${String(nodeId)}`);
      }
    }
  }

  const fingerprintFiles = record(fingerprints.files, "fingerprints.files");
  for (const [path, value] of Object.entries(fingerprintFiles)) {
    normalizeSafeSourcePath(path);
    const fingerprint = record(value, `fingerprint ${path}`);
    if (!/^[0-9a-f]{64}$/u.test(string(fingerprint.contentHash, `${path}.contentHash`))) {
      throw new Error(`fingerprint hash is invalid: ${path}`);
    }
  }
  if (fingerprints.gitCommitHash !== expected.targetCommit || meta.analyzedFiles !== Object.keys(fingerprintFiles).length) {
    throw new Error("fingerprint manifest does not match metadata");
  }
  if (review.success !== true || array(review.issues, "review.issues").length !== 0) {
    throw new Error("Understand-Anything review did not pass cleanly");
  }

  return Object.freeze({
    directory: root,
    targetCommit: expected.targetCommit,
    upstreamCommit: expected.upstreamCommit,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    layerCount: layers.length,
    tourCount: tour.length,
    fileCount: Object.keys(fingerprintFiles).length,
    hashes: Object.freeze({ ...hashes }),
    graph: Object.freeze(graph),
    provenance: Object.freeze(provenance),
  });
}
