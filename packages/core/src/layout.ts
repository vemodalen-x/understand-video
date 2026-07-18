export const VIDEO_PROFILE = Object.freeze({
  width: 1920,
  height: 1080,
  framesPerSecond: 30,
  videoCodec: "h264",
  audioCodec: "aac",
  maximumDurationMsExclusive: 180_000,
});

export interface Rectangle {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface NamedRegion extends Rectangle {
  readonly name: string;
  readonly kind: "diagram" | "code" | "other";
}

export const VISUAL_SAFE_MARGIN = Object.freeze({
  left: 96,
  right: 96,
  top: 72,
  bottom: 72,
});

export const CONTENT_RECT: Rectangle = Object.freeze({
  x: 96,
  y: 96,
  width: 1728,
  height: 684,
});

export const CAPTION_BAND: Rectangle = Object.freeze({
  x: 96,
  y: 820,
  width: 1728,
  height: 188,
});

export const CAPTION_STYLE = Object.freeze({
  fontSizePx: 52,
  lineHeightPx: 64,
  maximumLatinCharactersPerLine: 42,
  maximumLines: 2,
  minimumContentGapPx: 40,
});

export function rectangleRight(rectangle: Rectangle): number {
  return rectangle.x + rectangle.width;
}

export function rectangleBottom(rectangle: Rectangle): number {
  return rectangle.y + rectangle.height;
}

export function rectanglesIntersect(left: Rectangle, right: Rectangle): boolean {
  return (
    left.x < rectangleRight(right) &&
    rectangleRight(left) > right.x &&
    left.y < rectangleBottom(right) &&
    rectangleBottom(left) > right.y
  );
}

export function verticalGap(left: Rectangle, right: Rectangle): number {
  if (rectanglesIntersect(left, right)) {
    return 0;
  }
  if (rectangleBottom(left) <= right.y) {
    return right.y - rectangleBottom(left);
  }
  if (rectangleBottom(right) <= left.y) {
    return left.y - rectangleBottom(right);
  }
  return 0;
}

export interface LayoutValidation {
  readonly ok: boolean;
  readonly errors: readonly string[];
  readonly captionBand: Rectangle;
  readonly minimumGapPx: number;
}

/**
 * Validates content geometry independently of whether captions are burned in.
 * The band is always reserved so player-controlled sidecars cannot obscure code.
 */
export function validateCaptionSafeLayout(
  regions: readonly NamedRegion[],
): LayoutValidation {
  const errors: string[] = [];
  let minimumGapPx = Number.POSITIVE_INFINITY;

  for (const region of regions) {
    if (
      region.width <= 0 ||
      region.height <= 0 ||
      region.x < CONTENT_RECT.x ||
      region.y < CONTENT_RECT.y ||
      rectangleRight(region) > rectangleRight(CONTENT_RECT) ||
      rectangleBottom(region) > rectangleBottom(CONTENT_RECT)
    ) {
      errors.push(`${region.name}: outside the declared content rectangle`);
    }

    if (rectanglesIntersect(region, CAPTION_BAND)) {
      errors.push(`${region.name}: intersects the caption-reserved band`);
    }

    const gap = verticalGap(region, CAPTION_BAND);
    minimumGapPx = Math.min(minimumGapPx, gap);
    if (gap < CAPTION_STYLE.minimumContentGapPx) {
      errors.push(
        `${region.name}: caption gap ${gap}px is below ${CAPTION_STYLE.minimumContentGapPx}px`,
      );
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    captionBand: CAPTION_BAND,
    minimumGapPx:
      regions.length === 0 ? CAPTION_STYLE.minimumContentGapPx : minimumGapPx,
  };
}

