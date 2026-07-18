import {
  RepositoryGraphSchema,
  RepositorySnapshotSchema,
  type RepositoryGraph,
  type RepositorySnapshot,
} from "../../contracts/src/index.js";
import { normalizeSafeSourcePath } from "./git-snapshot.js";

export class GraphValidationError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "GraphValidationError";
  }
}

function assertGraphSemantics(graph: RepositoryGraph): void {
  const ids = new Set<string>();
  for (const node of graph.nodes) {
    if (ids.has(node.id)) {
      throw new GraphValidationError("graph node ids must be unique");
    }
    ids.add(node.id);
    if (node.source !== undefined) {
      normalizeSafeSourcePath(node.source.path);
    }
  }
  const edgeKeys = new Set<string>();
  for (const edge of graph.edges) {
    if (!ids.has(edge.from) || !ids.has(edge.to)) {
      throw new GraphValidationError("every graph edge endpoint must resolve to a node");
    }
    const edgeKey = `${edge.from}\0${edge.relation}\0${edge.to}`;
    if (edgeKeys.has(edgeKey)) {
      throw new GraphValidationError("graph edges must be unique");
    }
    edgeKeys.add(edgeKey);
  }
}

export function validateGraph(input: unknown): RepositoryGraph {
  const graph = RepositoryGraphSchema.parse(input);
  assertGraphSemantics(graph);
  return graph;
}

export function parseGraphJson(input: string): RepositoryGraph {
  let parsed: unknown;
  try {
    parsed = JSON.parse(input) as unknown;
  } catch {
    throw new GraphValidationError("graph input is not valid JSON");
  }
  return validateGraph(parsed);
}

export function validateGraphAgainstSnapshot(
  input: unknown,
  snapshotInput: unknown,
): RepositoryGraph {
  const graph = validateGraph(input);
  const snapshot = RepositorySnapshotSchema.parse(snapshotInput);
  if (graph.sourceRevision !== snapshot.revision) {
    throw new GraphValidationError("graph revision does not match the immutable snapshot");
  }
  const snapshotFiles = new Set(snapshot.files.map((file) => file.path));
  for (const node of graph.nodes) {
    if (node.source !== undefined && !snapshotFiles.has(node.source.path)) {
      throw new GraphValidationError("a graph source no longer exists at the pinned revision");
    }
  }
  return graph;
}

export function graphSourcePaths(graphInput: unknown): string[] {
  const graph = validateGraph(graphInput);
  return [...new Set(graph.nodes.flatMap((node) => (node.source === undefined ? [] : [node.source.path])))].sort(
    (left, right) => left.localeCompare(right, "en"),
  );
}

