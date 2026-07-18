# Fresh TEMPO graph generation contract

Status: required dogfood input; not yet generated.

The stale Understand-Anything dashboard sample graph is never valid for the
TEMPO Devpost video. The real run requires a separately generated graph whose
revision is exactly
`4afc6a3f5ceba0240f7fdd2eece96241253d6e60`.

## Pinned inputs

- Analyzer: `Egonex-AI/Understand-Anything` commit
  `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`, version 2.9.4.
- Target: `vemodalen-x/TEMPO` commit
  `4afc6a3f5ceba0240f7fdd2eece96241253d6e60`.
- Target clone: a normal independent clone at
  `C:\Users\User\Documents\OPENAI_MVP\tempo-ua-4afc6a3`, detached at the
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
$understand "C:\Users\User\Documents\OPENAI_MVP\tempo-ua-4afc6a3" --full --language en --no-auto-update --exclude ".ua/,.understand-anything/"
```

On the first prompt, preserve `src/`, `tests/`, `docs/`, `demo/`, `schemas/`,
and `governance/`. Exclude `.ua/` and `.understand-anything/` so the graph never
ingests its own output. Do not enable the optional review pass until the first
validated graph has been frozen.

## Acceptance and receipt

The product copies no graph into Git. It records these ignored local outputs
under `.understand-video/inputs/tempo-4afc6a3/`:

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
