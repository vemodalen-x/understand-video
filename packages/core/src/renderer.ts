import {
  renderDeterministicSvg,
  type SvgScene,
} from "./svg.js";

export interface HyperframesAdapter {
  readonly id: string;
  isAvailable(): boolean;
  renderSvg(scene: SvgScene): string;
}

export interface RenderOptions {
  readonly preferredRenderer?: "svg" | "hyperframes";
  readonly hyperframes?: HyperframesAdapter;
}

export interface RenderedFrame {
  readonly renderer: "svg" | "hyperframes";
  readonly rendererId: string;
  readonly svg: string;
  readonly fallbackReason?: "unavailable" | "adapter-error";
}

function isCompleteSvg(value: string): boolean {
  return /^<svg\b/u.test(value) && /<\/svg>$/u.test(value);
}

/**
 * Hyperframes is an optional external adapter, never a hard dependency. An
 * absent, unhealthy, or malformed adapter falls back to the audited SVG path.
 */
export function renderFrame(
  scene: SvgScene,
  options: RenderOptions = {},
): RenderedFrame {
  if (options.preferredRenderer === "hyperframes") {
    const adapter = options.hyperframes;
    if (adapter === undefined || !adapter.isAvailable()) {
      return {
        renderer: "svg",
        rendererId: "understand-video-svg-v1",
        svg: renderDeterministicSvg(scene),
        fallbackReason: "unavailable",
      };
    }
    try {
      const svg = adapter.renderSvg(scene);
      if (!isCompleteSvg(svg)) {
        throw new Error("Hyperframes returned malformed SVG");
      }
      return { renderer: "hyperframes", rendererId: adapter.id, svg };
    } catch {
      return {
        renderer: "svg",
        rendererId: "understand-video-svg-v1",
        svg: renderDeterministicSvg(scene),
        fallbackReason: "adapter-error",
      };
    }
  }
  return {
    renderer: "svg",
    rendererId: "understand-video-svg-v1",
    svg: renderDeterministicSvg(scene),
  };
}

