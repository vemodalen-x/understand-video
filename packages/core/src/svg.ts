import {
  CAPTION_BAND,
  CAPTION_STYLE,
  CONTENT_RECT,
  VIDEO_PROFILE,
} from "./layout.js";
import { wrapCaption } from "./captions.js";

export type VisualSceneKind =
  | "title"
  | "architecture"
  | "code"
  | "workflow"
  | "evidence"
  | "summary";

export interface SvgScene {
  readonly id: string;
  readonly kind: VisualSceneKind;
  readonly title: string;
  readonly eyebrow?: string;
  readonly body?: readonly string[];
  readonly code?: readonly string[];
  readonly burnedCaption?: string;
  readonly accent?: string;
}

function escapeXml(value: string): string {
  return value
    .replace(/&/gu, "&amp;")
    .replace(/</gu, "&lt;")
    .replace(/>/gu, "&gt;")
    .replace(/"/gu, "&quot;")
    .replace(/'/gu, "&apos;");
}

function normalizeLine(value: string): string {
  return value.replace(/\s+/gu, " ").trim();
}

function wrapVisualText(value: string, maximumLength: number): readonly string[] {
  const normalized = normalizeLine(value);
  if (normalized.length <= maximumLength) {
    return [normalized];
  }
  const lines: string[] = [];
  let line = "";
  for (const word of normalized.split(" ")) {
    const candidate = line.length === 0 ? word : `${line} ${word}`;
    if (candidate.length <= maximumLength) {
      line = candidate;
    } else {
      if (line.length > 0) {
        lines.push(line);
      }
      line = word.slice(0, maximumLength);
    }
  }
  if (line.length > 0) {
    lines.push(line);
  }
  return lines;
}

function renderBody(scene: SvgScene, accent: string): string {
  const body = scene.body ?? [];
  if (scene.kind === "architecture" || scene.kind === "workflow") {
    const nodes = body.slice(0, 4);
    return nodes
      .map((text, index) => {
        const x = CONTENT_RECT.x + index * 420;
        const connector =
          index === 0
            ? ""
            : `<path d="M ${x - 68} 500 H ${x - 20}" stroke="${accent}" stroke-width="6" stroke-linecap="round"/><path d="M ${x - 34} 486 L ${x - 20} 500 L ${x - 34} 514" fill="none" stroke="${accent}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>`;
        const lines = wrapVisualText(text, 18).slice(0, 3);
        const labels = lines
          .map(
            (line, lineIndex) =>
              `<text x="${x + 170}" y="${472 + lineIndex * 40}" text-anchor="middle" class="node-text">${escapeXml(line)}</text>`,
          )
          .join("");
        return `${connector}<rect x="${x}" y="400" width="340" height="190" rx="28" class="node"/>${labels}`;
      })
      .join("");
  }

  const visualLines = body
    .flatMap((value) => wrapVisualText(value, 62))
    .slice(0, 7);
  return visualLines
    .map(
      (line, index) =>
        `<g transform="translate(${CONTENT_RECT.x + 20} ${378 + index * 62})"><circle cx="10" cy="-14" r="7" fill="${accent}"/><text x="38" y="0" class="body-text">${escapeXml(line)}</text></g>`,
    )
    .join("");
}

function renderCode(scene: SvgScene): string {
  if (scene.kind !== "code" && (scene.code?.length ?? 0) === 0) {
    return "";
  }
  const code = (scene.code ?? []).slice(0, 12);
  return `<rect x="96" y="330" width="1728" height="450" rx="28" class="code-panel"/><circle cx="140" cy="370" r="9" fill="#ff6b6b"/><circle cx="172" cy="370" r="9" fill="#ffd166"/><circle cx="204" cy="370" r="9" fill="#66d9a7"/>${code
    .map(
      (line, index) =>
        `<text x="140" y="${425 + index * 28}" class="code-text"><tspan fill="#71809d">${String(index + 1).padStart(2, "0")}</tspan><tspan dx="24">${escapeXml(line.slice(0, 110))}</tspan></text>`,
    )
    .join("")}`;
}

/** Produces a complete deterministic SVG; it performs no I/O or clock reads. */
export function renderDeterministicSvg(scene: SvgScene): string {
  const accent = /^#[0-9a-fA-F]{6}$/u.test(scene.accent ?? "")
    ? (scene.accent as string).toLowerCase()
    : "#6ee7d8";
  const eyebrow = normalizeLine(scene.eyebrow ?? scene.kind.toUpperCase());
  const titleLines = wrapVisualText(scene.title, 38).slice(0, 2);
  const title = titleLines
    .map(
      (line, index) =>
        `<text x="96" y="${190 + index * 86}" class="title">${escapeXml(line)}</text>`,
    )
    .join("");
  const body = scene.kind === "code" ? "" : renderBody(scene, accent);
  const code = renderCode(scene);
  const captionLines =
    scene.burnedCaption === undefined ? [] : wrapCaption(scene.burnedCaption);
  const captions = captionLines
    .map(
      (line, index) =>
        `<text x="960" y="${890 + index * CAPTION_STYLE.lineHeightPx}" text-anchor="middle" class="caption">${escapeXml(line)}</text>`,
    )
    .join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${VIDEO_PROFILE.width}" height="${VIDEO_PROFILE.height}" viewBox="0 0 ${VIDEO_PROFILE.width} ${VIDEO_PROFILE.height}" role="img" aria-labelledby="scene-title"><title id="scene-title">${escapeXml(scene.title)}</title><defs><linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#08111f"/><stop offset="1" stop-color="#111d35"/></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#000000" flood-opacity="0.28"/></filter></defs><style>.eyebrow{font-family:"Segoe UI",Arial,sans-serif;font-size:25px;font-weight:700;letter-spacing:5px;fill:${accent}}.title{font-family:"Segoe UI",Arial,sans-serif;font-size:68px;font-weight:700;fill:#f6f8ff}.body-text{font-family:"Segoe UI",Arial,sans-serif;font-size:36px;font-weight:500;fill:#c9d4e8}.node{fill:#152641;stroke:${accent};stroke-width:3;filter:url(#shadow)}.node-text{font-family:"Segoe UI",Arial,sans-serif;font-size:30px;font-weight:600;fill:#eef4ff}.code-panel{fill:#08101d;stroke:#293d5d;stroke-width:2;filter:url(#shadow)}.code-text{font-family:Consolas,"Cascadia Mono",monospace;font-size:28px;font-weight:500;fill:#d5e2f5}.caption{font-family:"Segoe UI",Arial,sans-serif;font-size:${CAPTION_STYLE.fontSizePx}px;font-weight:650;fill:#ffffff;paint-order:stroke;stroke:#07101d;stroke-width:8px;stroke-linejoin:round}</style><rect width="1920" height="1080" fill="url(#background)"/><path d="M0 0H720L420 1080H0Z" fill="#0d1a2d" opacity=".72"/><text x="96" y="108" class="eyebrow">${escapeXml(eyebrow)}</text>${title}${body}${code}<rect id="caption-reserved-band" x="${CAPTION_BAND.x}" y="${CAPTION_BAND.y}" width="${CAPTION_BAND.width}" height="${CAPTION_BAND.height}" rx="24" fill="#07101d" opacity="${captionLines.length > 0 ? ".88" : ".18"}"/>${captions}<text x="1824" y="1040" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="20" fill="#71809d">UNDERSTAND VIDEO · ${escapeXml(scene.id)}</text></svg>`;
}
