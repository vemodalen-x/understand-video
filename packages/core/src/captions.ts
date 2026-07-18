import { CAPTION_STYLE } from "./layout.js";

export interface CaptionCue {
  readonly startMs: number;
  readonly endMs: number;
  readonly text: string;
}

export interface CaptionValidation {
  readonly ok: boolean;
  readonly errors: readonly string[];
}

function normalizeCaptionText(text: string): string {
  return text.replace(/\s+/gu, " ").trim();
}

function splitLongToken(token: string, maximumLength: number): string[] {
  const pieces: string[] = [];
  for (let offset = 0; offset < token.length; offset += maximumLength) {
    pieces.push(token.slice(offset, offset + maximumLength));
  }
  return pieces;
}

/** Wraps one cue without dropping or truncating any words. */
export function wrapCaption(
  text: string,
  maximumLength = CAPTION_STYLE.maximumLatinCharactersPerLine,
  maximumLines = CAPTION_STYLE.maximumLines,
): readonly string[] {
  if (!Number.isInteger(maximumLength) || maximumLength < 1) {
    throw new RangeError("caption maximum line length must be a positive integer");
  }
  if (!Number.isInteger(maximumLines) || maximumLines < 1) {
    throw new RangeError("caption maximum line count must be a positive integer");
  }

  const normalized = normalizeCaptionText(text);
  if (normalized.length === 0) {
    throw new Error("caption text must not be empty");
  }

  const words = normalized
    .split(" ")
    .flatMap((word) => splitLongToken(word, maximumLength));
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current.length === 0 ? word : `${current} ${word}`;
    if (candidate.length <= maximumLength) {
      current = candidate;
      continue;
    }
    lines.push(current);
    current = word;
  }
  if (current.length > 0) {
    lines.push(current);
  }

  if (lines.length > maximumLines) {
    throw new RangeError(
      `caption needs ${lines.length} lines; maximum is ${maximumLines}`,
    );
  }
  return lines;
}

/**
 * Splits narration into cue-sized chunks before applying the strict two-line
 * wrapper. This keeps sidecars semantically complete while avoiding giant cues.
 */
export function segmentCaptionText(text: string): readonly string[] {
  const normalized = normalizeCaptionText(text);
  if (normalized.length === 0) {
    return [];
  }

  const words = normalized.split(" ");
  const chunks: string[] = [];
  let chunk = "";
  for (const rawWord of words) {
    for (const word of splitLongToken(
      rawWord,
      CAPTION_STYLE.maximumLatinCharactersPerLine,
    )) {
      const candidate = chunk.length === 0 ? word : `${chunk} ${word}`;
      try {
        wrapCaption(candidate);
        chunk = candidate;
      } catch (error) {
        if (!(error instanceof RangeError) || chunk.length === 0) {
          throw error;
        }
        chunks.push(chunk);
        chunk = word;
      }
    }
  }
  if (chunk.length > 0) {
    chunks.push(chunk);
  }
  return chunks;
}

export function createCaptionCues(
  text: string,
  startMs: number,
  endMs: number,
): readonly CaptionCue[] {
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || startMs < 0) {
    throw new RangeError("caption timing must use finite non-negative milliseconds");
  }
  if (endMs <= startMs) {
    throw new RangeError("caption end must be later than caption start");
  }

  const chunks = segmentCaptionText(text);
  if (chunks.length === 0) {
    return [];
  }
  const totalWeight = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  let cursor = startMs;
  let cumulativeWeight = 0;
  return chunks.map((chunk, index) => {
    const isLast = index === chunks.length - 1;
    cumulativeWeight += chunk.length;
    const proportionalEnd = Math.round(
      startMs + ((endMs - startMs) * cumulativeWeight) / totalWeight,
    );
    const cueEnd = isLast ? endMs : Math.max(cursor + 1, proportionalEnd);
    const cue: CaptionCue = {
      startMs: cursor,
      endMs: Math.min(cueEnd, endMs),
      text: wrapCaption(chunk).join("\n"),
    };
    cursor = cue.endMs;
    return cue;
  });
}

function formatTimestamp(milliseconds: number, decimalSeparator: "," | "."): string {
  const rounded = Math.round(milliseconds);
  const hours = Math.floor(rounded / 3_600_000);
  const minutes = Math.floor((rounded % 3_600_000) / 60_000);
  const seconds = Math.floor((rounded % 60_000) / 1_000);
  const remainder = rounded % 1_000;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}${decimalSeparator}${String(remainder).padStart(3, "0")}`;
}

export function toSrt(cues: readonly CaptionCue[]): string {
  return `${cues
    .map(
      (cue, index) =>
        `${index + 1}\n${formatTimestamp(cue.startMs, ",")} --> ${formatTimestamp(cue.endMs, ",")}\n${cue.text}`,
    )
    .join("\n\n")}\n`;
}

export function toWebVtt(cues: readonly CaptionCue[]): string {
  return `WEBVTT\n\n${cues
    .map(
      (cue) =>
        `${formatTimestamp(cue.startMs, ".")} --> ${formatTimestamp(cue.endMs, ".")}\n${cue.text}`,
    )
    .join("\n\n")}\n`;
}

export function validateCaptionCues(
  cues: readonly CaptionCue[],
  mediaDurationMs: number,
): CaptionValidation {
  const errors: string[] = [];
  let previousEnd = 0;
  cues.forEach((cue, index) => {
    if (
      !Number.isFinite(cue.startMs) ||
      !Number.isFinite(cue.endMs) ||
      cue.startMs < previousEnd ||
      cue.endMs <= cue.startMs
    ) {
      errors.push(`cue ${index + 1}: non-monotonic or empty timing`);
    }
    if (cue.endMs > mediaDurationMs) {
      errors.push(`cue ${index + 1}: exceeds media duration`);
    }
    const lines = cue.text.split("\n");
    if (lines.length > CAPTION_STYLE.maximumLines) {
      errors.push(`cue ${index + 1}: exceeds two lines`);
    }
    if (
      lines.some(
        (line) => line.length > CAPTION_STYLE.maximumLatinCharactersPerLine,
      )
    ) {
      errors.push(`cue ${index + 1}: exceeds 42 characters per line`);
    }
    previousEnd = cue.endMs;
  });
  return { ok: errors.length === 0, errors };
}
