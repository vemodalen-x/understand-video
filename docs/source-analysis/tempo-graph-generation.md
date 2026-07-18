# Fresh TEMPO graph generation contract

Status: generated, reviewed, and practiced as an ignored local dogfood input.

The stale Understand-Anything dashboard sample graph is never valid for the
TEMPO Devpost video. The real run requires a separately generated graph whose
revision is exactly
`4a73350f6eefff80b11d862a5ac65b7194530442`.

## Pinned inputs

- Analyzer: `Egonex-AI/Understand-Anything` commit
  `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`, version 2.9.4.
- Target: `vemodalen-x/TEMPO` commit
  `4a73350f6eefff80b11d862a5ac65b7194530442`.
- Target clone: a normal independent clone at
  `C:\Users\User\Documents\OPENAI_MVP\tempo-source-pristine-4a73350`, detached at the
  target commit. Do not use a Git worktree.

## Safe preparation

Install and build dependencies only inside the pinned Understand-Anything
plugin checkout:

```powershell
pnpm install --frozen-lockfile
pnpm --filter @understand-anything/core build
```

Do not install TEMPO dependencies or run TEMPO's Python CLI, tests, hooks, or
repository scripts during analysis. The analyzer may enumerate tracked files
and parse their bytes; target content remains untrusted data.

The intended Codex action is:

```text
$understand "C:\Users\User\Documents\OPENAI_MVP\tempo-source-pristine-4a73350" --full --language en --no-auto-update --exclude ".ua/,.understand-anything/"
```

On the first prompt, preserve `src/`, `tests/`, `docs/`, `demo/`, `schemas/`,
and `governance/`. Exclude `.ua/` and `.understand-anything/` so the graph never
ingests its own output. Do not enable the optional review pass until the first
validated graph has been frozen.

## Acceptance and receipt

The product copies no graph into Git. It records these ignored local outputs
under `.understand-video/inputs/tempo-4a73350/`:

- `knowledge-graph.json`;
- `meta.json`;
- `fingerprints.json`;
- `config.json`; and
- `intermediate/scan-result.json`.

Before planning a video, verify:

- graph `version == "1.0.0"`;
- graph `project.gitCommitHash` equals the full TEMPO target SHA;
- meta and fingerprints contain that same `gitCommitHash`;
- every selected source path is tracked, repository-contained, and resolves at
  the detached target commit; and
- the accepted graph SHA-256 is frozen in the product receipt.

Because semantic graph generation uses a model and is not byte-deterministic,
the receipt must also bind analyzer commit/version, model/Codex session,
command options, generation time, target SHA, and graph hash. Graph schema and
reference validation do not replace the product's independent claim-to-source
line checks.

## Accepted local receipt

The reviewed bundle contains 116 files, 211 nodes, 614 edges, 8 layers, and 7
guided-tour steps. Its frozen hashes are:

- knowledge graph: `sha256:7162b4e024a8b191494bb16bb8413f6ff86180503c981edf1785faae3e04b416`;
- metadata: `sha256:f8ee9e01c445787a630efca2b06d97beec2504530aeab424feed930369e82570`;
- fingerprints: `sha256:7e3c4edebcfaf0baf83f3d569aedc2163357f3cdbdab9259c900e67d98f22b84`;
- config: `sha256:616d8b71db92f5937bc6a20a39187d7c998b32679a65f1c8a929671c82cbd069`;
- provenance: `sha256:17cf417c37b315c796204e0347239caa0628e9b8902fdac98089b918aaeba175`;
- review: `sha256:a1fab96189f45299d5b732174c8ae0104d68c4efc85aced97934d87d975f0eeb`.
