# Understand-Anything baseline

Retrieved at: `2026-07-17T14:22:50Z`

## Selected source snapshot

- Repository: `https://github.com/Egonex-AI/Understand-Anything`
- Branch: `main`
- Commit: `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`
- Version: `2.9.4`
- License: MIT, copyright Yuxiang Lin and Infinite Universe, Inc.
- Live comparison: the fetched `origin/main` resolved to the same commit. There
  were zero commits between the requested pin and the live default branch.

The project is an upstream dependency and design source. It is not affiliated
with, sponsored by, or owned by this project.

## Architectural findings

- The repository is a pnpm TypeScript monorepo. Node.js 22+ and pnpm 10 are the
  documented development baseline.
- `understand-anything-plugin/packages/core` owns graph types, Zod validation,
  parsing, persistence, search, static analysis, staleness checks, and guided
  tour generation.
- The dashboard is React 19 with React Flow, Zustand, and a graph-first layout.
- New projects use `.ua/`; an existing `.understand-anything/` directory wins
  for backward compatibility.
- `knowledge-graph.json` contains project metadata, nodes, edges, layers, and a
  guided tour. Project metadata includes `gitCommitHash`.
- Graph structure comes from deterministic parsing while summaries, layers,
  and tours use semantic analysis. The proposed video tool will consume this
  graph and will not replace the analyzer.
- Upstream validation checks node and edge schemas plus referential integrity,
  filters dangling layer/tour references, and supports graph normalization.
- Upstream freshness checks distinguish clean, dirty, behind, ahead, diverged,
  unknown commit, and non-Git conditions. The video compiler needs a stricter
  profile-specific policy on top of those results.
- Viewer source reads require a one-time token, normalize relative paths, limit
  source files to 1 MiB, and allow only paths found in the graph. These are
  useful controls but do not by themselves resolve symlink escapes, secret
  scanning, external speech disclosure, or render isolation.

## Inspected source set

The required README, CLAUDE instructions, licenses, root/plugin/dashboard
package manifests, core graph types and schema, tour generator, LearnPanel,
KnowledgeGraphView, explain/onboard builders, agent prompts, four requested
skills, viewer middleware, freshness implementation, and freshness tests were
inspected at the selected commit. File hashes are recorded in
`UPSTREAM_BASELINE.json` through the selected immutable commit rather than by
copying upstream files into this repository.

## Integration decision

Use the exact graph contract from this pin and create a modular video package
whose inputs are validated graph data and source snapshot metadata. Do not fork
the analyzer or claim existing graph, dashboard, tour, explain, onboarding, or
freshness capabilities as new work. No upstream source file has been reused or
modified in the planning phase.
