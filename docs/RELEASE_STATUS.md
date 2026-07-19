# Release status

Verified 2026-07-19 UTC from a fresh public clone of
`4b1d5267ace67d99043305e9b1e610a71bff0ff7`.

## Reproduce

Prerequisites: Node.js 22+, pnpm 11, Git, FFmpeg, and FFprobe on Windows,
macOS, or Linux.

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:acceptance
pnpm build:judge
node submission/judge-bundle/understand-video-demo.mjs demo --offline
```

Observed result:

- dependency installation and supply-chain policy check passed;
- TypeScript type-check passed;
- 54 acceptance cases discovered: 53 passed and 1 optional external-input case
  skipped;
- the judge bundle rebuilt without changing the tracked tree; and
- the offline run completed every stage and emitted
  `UNDERSTAND_VIDEO_DEMO_PASSED`.

The prepared judge bundle can be run without pnpm, `node_modules`, or rebuilding
the TypeScript source. Its fixture receipt is deliberately
`authoritative:false`.

## Version boundaries

- Product release: `4b1d5267ace67d99043305e9b1e610a71bff0ff7`.
- Published video source: TEMPO
  `4a73350f6eefff80b11d862a5ac65b7194530442`.
- Historical authorization packet: TEMPO `4afc6a3`; retained as provenance,
  not a current release pointer.
- Current TEMPO code at final audit: `0edefe3`; its later hardening is verified
  in the TEMPO repository and is not claimed as re-rendered here.

## Public delivery

- TEMPO competition repository: <https://github.com/vemodalen-x/TEMPO>
- Understand Video supporting repository: <https://github.com/vemodalen-x/understand-video>
- YouTube demo: <https://youtu.be/3eIxgVo9z4I>
- Devpost entry: <https://devpost.com/software/understand-video>

TEMPO is the OpenAI Build Week entry in Work & Productivity. Understand Video
is independent downstream implementation evidence, not a second competition
entry. Historical task and planning records are preserved rather than rewritten
to manufacture a later authorization state.
