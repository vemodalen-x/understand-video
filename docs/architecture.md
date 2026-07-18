# Understand Video MVP architecture

Status: implementation specification only. No product code exists yet, and this
document does not grant build authority.

## Boundary

Understand Video owns the repository-to-video product. TEMPO remains an
external governance checkout and is invoked only through a narrow adapter. No
TEMPO CLI, Python source, schema, hook, test, or governance history is copied
into this repository.

## Proposed product tree

```text
package.json
pnpm-workspace.yaml
pnpm-lock.yaml
tsconfig.base.json
packages/
  cli/                  doctor, inspect, plan, render, verify, preview, demo
  contracts/            snapshot, claim, storyboard, scene, caption, receipt
  governance-adapter/   external TEMPO pin/status/start checks
  source/               safe Git snapshot reader and claim resolver
  planner/              fixture planner and replaceable GPT-5.6 provider
  narration/            fixture voice and approved production provider
  captions/             SRT, VTT, line wrapping, and safe-zone validation
  renderer/             deterministic SVG fallback and Hyperframes adapter
  media/                FFmpeg/FFprobe invocation and audio metrics
  verifier/             grounding, media, receipt, and Devpost profile
tests/video/
samples/governed-framework-video/
docs/
```

## User flow

1. `doctor` verifies Node.js, Git, FFmpeg, FFprobe, the external TEMPO
   governance checkout, and the selected graph/source pair.
2. `inspect` validates a pre-generated Understand-Anything graph against the
   exact clean Git revision, then reads only graph-selected Git objects without
   executing repository code or installing its dependencies.
3. `plan` resolves required claims to graph nodes and file/line references and emits a
   schema-valid storyboard. Fixture mode is credential-free; a real GPT-5.6
   provider must record model and request provenance.
4. `render` measures narration, compiles sidecar captions, reserves caption
   space, renders deterministic visuals, and invokes FFmpeg with argument
   arrays rather than a shell string.
5. `verify` fails closed on source drift, unsupported claims, duration, A/V,
   audio, caption, safe-zone, or receipt errors.
6. `preview` opens only local output. Upload and publication are outside the
   product command surface.

## Rendering strategy

The required fallback is deterministic SVG/HTML frames plus FFmpeg. Developers
use pnpm to build and test; the prepared judge bundle contains compiled
JavaScript and does not require pnpm or a source rebuild.

Hyperframes may be consumed behind `packages/renderer` as a pinned external
adapter. Its source must not be copied into this repository. Because the
available upstream is a Bun-oriented monorepo, Hyperframes cannot become a hard
runtime dependency until its supported package/CLI contract and license pin are
verified against the Node.js judge environment. A missing Hyperframes adapter
must fall back cleanly rather than block the demo.

## Narration and captions

- Fixture narration is deterministic and visibly labeled non-production.
- A production provider receives approved narration text and voice settings
  only, never raw repository source.
- A 10–15 second voice sample requires human approval before a full run.
- SRT and VTT are primary outputs.
- Burned captions are optional and use a dedicated lower band. Diagram and code
  safe regions may never intersect the caption band.
- Target integrated loudness is -16 LUFS with true peak at or below -1 dBTP;
  clipping and excessive silence fail verification.

## Devpost media constants

- Canvas: 1920 x 1080 at constant 30 fps; H.264 video and AAC audio.
- Audio: target -16 LUFS, accepted interval -18 through -14 LUFS, true peak at
  or below -1 dBTP, zero full-scale clipped samples, no more than 500 ms of
  leading or trailing silence, and no internal silent gap longer than 1200 ms.
- Visual safe margin: 96 px left/right and 72 px top/bottom.
- Diagram and code content rectangle: `x=96..1824`, `y=96..780`.
- Caption-reserved band: `x=96..1824`, `y=820..1008`, with at least 40 px
  separating it from code and diagrams. Visual content never enters this band,
  even when captions are delivered as a player-controlled sidecar.
- Burned-caption mode uses a minimum 52 px sans-serif font, 64 px line height,
  at most two lines, and at most 42 Latin characters per line after word wrap.
  SRT and VTT remain the primary deliverables.

## Receipt

The receipt binds target repository/revision, graph identity, selected source
hashes, claim map, storyboard, narration, captions, renderer identity, media
hash, verification results, TEMPO baseline, provider provenance, and
fixture/real mode. In governance-enforced mode it also binds assessment
ID/hash, warrant ID/expiry, task, lane, action, path, and the successful
`mvp start` event/receipt. Fixture mode sets those authority fields to null and
must remain `authoritative: false`. Every receipt records local integrity only
unless a stronger attestation actually occurred.
