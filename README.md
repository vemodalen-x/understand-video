# Understand Video

Understand Video is a code-explanation product that turns a pinned repository
snapshot into a source-grounded, narrated, caption-safe learning video. The
first demo target is [`vemodalen-x/TEMPO`](https://github.com/vemodalen-x/TEMPO).

This repository contains only Understand Video product material: product
plans, source analysis, experiment fixtures, the bilingual observation UI, and
future translator implementation. It does **not** vendor TEMPO's CLI, schemas,
enforcement hooks, tests, governance records, or submission package.

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
- Five-person post-MVP learning comparison and bilingual form:
  [`docs/experiments/learning-comparison/`](docs/experiments/learning-comparison/)
- One-person founder-MVP staging proposal:
  [`plan/proposals/founder-mvp-staging.md`](plan/proposals/founder-mvp-staging.md)
- Understand-Anything source pin: [`UPSTREAM_BASELINE.json`](UPSTREAM_BASELINE.json)
- Prior-work boundary: [`docs/HACKATHON_DELTA.md`](docs/HACKATHON_DELTA.md)

## Status

The checked-in work remains planning, documentation, fixtures, and evidence.
It does not claim that the translator MVP is implemented, deployed, uploaded,
or submitted. Product implementation starts only after the external TEMPO
workspace reports a current, scoped human warrant for this repository.

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
