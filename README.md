# Understand Video

Understand Video is a code-explanation product that turns a pinned repository
snapshot into a source-grounded, narrated, caption-safe learning video. The
first demo target is [`vemodalen-x/TEMPO`](https://github.com/vemodalen-x/TEMPO).

The public [TEMPO judge video](https://youtu.be/3eIxgVo9z4I) was produced by
this repository. TEMPO is the OpenAI Build Week competition entry; Understand
Video is the independent downstream product and implementation evidence.

This repository contains the Understand Video product: its source-grounded
translation pipeline, media renderer, tests, fixtures, bilingual observation
UI, judge bundle, and delivery evidence. It does **not** vendor TEMPO's CLI,
schemas, enforcement hooks, tests, or governance records.

## Repository boundary

| Repository | Owns | Does not own |
| --- | --- | --- |
| [`vemodalen-x/TEMPO`](https://github.com/vemodalen-x/TEMPO) | Governance framework, authorization gates, schemas, experiment-lane proposals | Understand Video product code or product evidence |
| `vemodalen-x/understand-video` | Code-to-video translator, product plans, media UX, and product experiments | A fork or embedded copy of TEMPO |

TEMPO is an external governance dependency pinned in
[`TEMPO_BASELINE.json`](TEMPO_BASELINE.json). TEMPO-generated decision and
evidence records may be checked in as product provenance, but the framework
source stays in its own repository. Runtime artifacts use the ignored
`.understand-video/` directory so the product does not depend on TEMPO's local
workspace layout.

## Current contents

- Product opportunity, hypotheses, charter proposal, and evidence: [`plan/`](plan/)
- MVP product plan: [`plan/interpreter-mvp.md`](plan/interpreter-mvp.md)
- Devpost delivery profile: [`docs/DEVPOST_DELIVERY_PROFILE.md`](docs/DEVPOST_DELIVERY_PROFILE.md)
- Pinned TEMPO explanation map:
  [`docs/source-analysis/tempo-4a73350-video-map.md`](docs/source-analysis/tempo-4a73350-video-map.md)
- Fresh TEMPO graph-generation and provenance contract:
  [`docs/source-analysis/tempo-graph-generation.md`](docs/source-analysis/tempo-graph-generation.md)
- Proposed judge path and product architecture:
  [`docs/judge-path.md`](docs/judge-path.md) and
  [`docs/architecture.md`](docs/architecture.md)
- Devpost video plan and exact 50-case acceptance contract:
  [`docs/devpost-video-script.md`](docs/devpost-video-script.md) and
  [`docs/test-plan.md`](docs/test-plan.md)
- Five-person post-MVP learning comparison and bilingual form:
  [`docs/experiments/learning-comparison/`](docs/experiments/learning-comparison/)
- One-person founder-MVP staging proposal:
  [`plan/proposals/founder-mvp-staging.md`](plan/proposals/founder-mvp-staging.md)
- Historical founder authorization packet, external assessment snapshot, and
  task record preserved as provenance:
  [`plan/proposals/founder-mvp-authorization-packet.md`](plan/proposals/founder-mvp-authorization-packet.md),
  [`plan/assessments/A-6539C42FED42417C.json`](plan/assessments/A-6539C42FED42417C.json), and
  [`tasks/T-20260718-UNDERSTAND-VIDEO-FOUNDER-MVP.json`](tasks/T-20260718-UNDERSTAND-VIDEO-FOUNDER-MVP.json)
- Understand-Anything source pin: [`UPSTREAM_BASELINE.json`](UPSTREAM_BASELINE.json)
- Prior-work boundary: [`docs/HACKATHON_DELTA.md`](docs/HACKATHON_DELTA.md)

## Release status

The founder MVP vertical slice is merged on public `main`. A clean clone of
`4b1d5267ace67d99043305e9b1e610a71bff0ff7` passes installation, TypeScript
type-checking, the 54-case acceptance run (53 pass, 1 optional external-input
skip), judge-bundle rebuild, and the credential-free offline demo. Exact
commands and results are recorded in
[`docs/RELEASE_STATUS.md`](docs/RELEASE_STATUS.md).

The published explanation and video intentionally pin TEMPO commit
`4a73350f6eefff80b11d862a5ac65b7194530442`. Historical planning records refer
to an earlier `4afc6a3` governance snapshot and remain unchanged as provenance;
they are not current release pointers. TEMPO's later public `0edefe3` hardening
is documented by the TEMPO repository and is not misrepresented as having been
re-rendered by this release.

The product validates the pinned repository origin, clean checkout, revision,
and governance lease before a production run. Local technical receipts remain
non-authoritative; publication and the human verdict stay separate actions.

## How Codex and GPT-5.6 were used

Codex with GPT-5.6 Sol was the build-time development partner for the MVP. It
inspected the independent TEMPO and Understand-Anything repositories, helped
turn the product brief into strict contracts, implemented and reviewed the
TypeScript pipeline, exercised the TEMPO gates, wrote the acceptance suite,
and iterated on the narration, renderer, audio checks, and caption-safe layout.

The key human-controlled product decisions were to pin every explanation to an
immutable source snapshot, treat model output as advice rather than authority,
never execute target repository code, require a credential-free judge path,
show a real product run in the demo, and keep publication outside the local
technical receipt. Those decisions are visible in the merged TEMPO
[stabilization](https://github.com/vemodalen-x/TEMPO/pull/4) and
[lease-rotation](https://github.com/vemodalen-x/TEMPO/pull/5) pull requests and
the Understand Video [MVP](https://github.com/vemodalen-x/understand-video/pull/3)
and [working-demo](https://github.com/vemodalen-x/understand-video/pull/4) pull
requests.

The final renderer does not make an unrecorded OpenAI API call. GPT-5.6's role
is accurately disclosed as build-time work through Codex; the generated video
uses authored, source-checked narration and Microsoft Edge Speech. The offline
judge bundle remains deterministic and credential-free.

## Install and verify

Supported development platforms are Windows, macOS, and Linux with Node.js
22+, pnpm 11, Python 3.10+, Git, FFmpeg, and FFprobe on `PATH`.

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:acceptance
pnpm build:judge
node submission/judge-bundle/understand-video-demo.mjs demo --offline
```

The final command is the credential-free judge path. It uses bundled fixtures,
does not require `node_modules` or a source rebuild after the bundle has been
prepared, and ends with `UNDERSTAND_VIDEO_DEMO_PASSED` only after all required
pipeline stages pass.

## Reproduce the TEMPO video draft

Clone TEMPO at the exact revision named above into an independent directory.
Place the reviewed Understand-Anything export in
`.understand-video/inputs/tempo-4a73350/`. Then create an isolated Edge TTS
environment:

```text
python -m venv .understand-video/tools/edge-tts
# Windows
.understand-video/tools/edge-tts/Scripts/python.exe -m pip install edge-tts==7.2.8
# macOS or Linux
.understand-video/tools/edge-tts/bin/python -m pip install edge-tts==7.2.8
```

Render with an explicit independent checkout (PowerShell example):

```powershell
pnpm render:tempo -- `
  --tempo "C:\path\to\independent\TEMPO" `
  --graph ".understand-video\inputs\tempo-4a73350" `
  --output ".understand-video\runs\tempo-4a73350\devpost-draft"
```

On macOS or Linux, use the same options with POSIX paths. `TEMPO_CHECKOUT` can
replace `--tempo`. The render performs a real network call to Microsoft Edge
Speech containing only approved narration, voice ID, rate, and pitch; it does
not transmit repository source. It emits MP4, SRT, WebVTT, claims, storyboard,
and a verification report. A passing report is technical evidence only: the
draft stays non-authoritative and publication remains human-controlled.

The learning-comparison compiler can be exercised independently on fixtures:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  docs/experiments/learning-comparison/tools/compile-evidence.ps1 `
  -InputDirectory docs/experiments/learning-comparison/fixtures `
  -OutputDirectory .understand-video/experiments/learning-comparison/fixture-check `
  -FixtureMode
```

See [`NOTICE`](NOTICE) and
[`docs/THIRD_PARTY_LICENSES.md`](docs/THIRD_PARTY_LICENSES.md) for lineage and
license boundaries.

Public delivery links:

- TEMPO competition repository: <https://github.com/vemodalen-x/TEMPO>
- Understand Video supporting repository: <https://github.com/vemodalen-x/understand-video>
- YouTube demo: <https://youtu.be/3eIxgVo9z4I>
- Devpost entry: <https://devpost.com/software/understand-video>
