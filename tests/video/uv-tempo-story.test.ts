import { existsSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { snapshotGitRepository } from "../../packages/core/src/git-snapshot.js";
import { compileTempoVideoPlan, TEMPO_NARRATION, TEMPO_STORY_REVISION } from "../../packages/core/src/tempo-story.js";

const tempoCheckout = "C:\\Users\\User\\Documents\\OPENAI_MVP\\tempo-source-pristine-4a73350";

describe("authored TEMPO story specification", () => {
  it.runIf(existsSync(tempoCheckout))("grounds every exact narration scene in the pinned snapshot", () => {
    const reader = snapshotGitRepository({ root: tempoCheckout, revision: TEMPO_STORY_REVISION, strict: true });
    const compiled = compileTempoVideoPlan(reader);

    expect(compiled.claims.claims).toHaveLength(7);
    expect(compiled.plan.durationMs).toBe(159_000);
    expect(compiled.plan.storyboard.scenes.map((scene) => scene.narration)).toEqual(Object.values(TEMPO_NARRATION));
    expect(compiled.plan.storyboard.scenes.every((scene) => scene.claimIds.length > 0)).toBe(true);
    expect(reader.processAudit.every((entry) => entry.executable === "git")).toBe(true);
  });
});
