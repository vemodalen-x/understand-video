import { createHash } from "node:crypto";

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

function normalize(value: unknown, path: string): JsonValue {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return value;
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError(`Non-finite number at ${path}`);
    }
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((entry, index) => normalize(entry, `${path}[${index}]`));
  }

  if (typeof value === "object") {
    const result: Record<string, JsonValue> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      const entry = (value as Record<string, unknown>)[key];
      if (entry === undefined) {
        throw new TypeError(`Undefined value at ${path}.${key}`);
      }
      result[key] = normalize(entry, `${path}.${key}`);
    }
    return result;
  }

  throw new TypeError(`Unsupported canonical value at ${path}`);
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(normalize(value, "$"));
}

export function sha256Bytes(value: string | Uint8Array): `sha256:${string}` {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

export function canonicalHash(value: unknown): `sha256:${string}` {
  return sha256Bytes(canonicalJson(value));
}

export function isSha256(value: unknown): value is `sha256:${string}` {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
}
