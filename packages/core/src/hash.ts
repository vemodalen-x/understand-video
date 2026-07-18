import { createHash } from "node:crypto";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { readonly [key: string]: JsonValue };

export function sha256Bytes(value: string | Uint8Array): `sha256:${string}` {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

export function normalizeNewlines(value: string): string {
  return value.replace(/\r\n?/gu, "\n");
}

export function splitSourceLines(value: string): string[] {
  const normalized = normalizeNewlines(value);
  const lines = normalized.split("\n");
  if (lines.length > 1 && lines.at(-1) === "") {
    lines.pop();
  }
  return lines;
}

export function sourceLineSpan(value: string, startLine: number, endLine: number): string {
  if (!Number.isInteger(startLine) || !Number.isInteger(endLine) || startLine < 1 || endLine < startLine) {
    throw new RangeError("invalid source line span");
  }
  const lines = splitSourceLines(value);
  if (endLine > lines.length) {
    throw new RangeError("source line span exceeds file length");
  }
  return lines.slice(startLine - 1, endLine).join("\n");
}

export function hashSourceLineSpan(
  value: string,
  startLine: number,
  endLine: number,
): `sha256:${string}` {
  return sha256Bytes(sourceLineSpan(value, startLine, endLine));
}

function canonicalize(value: unknown, ancestors: Set<object>): JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError("canonical JSON does not support non-finite numbers");
    }
    return Object.is(value, -0) ? 0 : value;
  }
  if (Array.isArray(value)) {
    if (ancestors.has(value)) {
      throw new TypeError("canonical JSON does not support cyclic values");
    }
    ancestors.add(value);
    const result = value.map((item) => canonicalize(item, ancestors));
    ancestors.delete(value);
    return result;
  }
  if (typeof value === "object") {
    if (ancestors.has(value)) {
      throw new TypeError("canonical JSON does not support cyclic values");
    }
    ancestors.add(value);
    const record = value as Record<string, unknown>;
    const result: Record<string, JsonValue> = {};
    for (const key of Object.keys(record).sort()) {
      const child = record[key];
      if (child === undefined) {
        continue;
      }
      if (typeof child === "function" || typeof child === "symbol" || typeof child === "bigint") {
        throw new TypeError(`canonical JSON does not support ${typeof child} values`);
      }
      result[key] = canonicalize(child, ancestors);
    }
    ancestors.delete(value);
    return result;
  }
  throw new TypeError(`canonical JSON does not support ${typeof value} values`);
}

export function stableJson(value: unknown): string {
  return JSON.stringify(canonicalize(value, new Set<object>()));
}

export function hashJson(value: unknown): `sha256:${string}` {
  return sha256Bytes(stableJson(value));
}

