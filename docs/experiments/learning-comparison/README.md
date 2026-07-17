# Learning comparison experiment

Experiment ID: `X-LEARNING-COMPARISON-001`

This package tests Rank-1 hypothesis `H-LEARNING-001` without treating model
output or synthetic fixtures as learner evidence. Five real developers compare
a short, source-linked video condition with unguided source exploration.

The package intentionally does **not** contain completed observations. Human
participants and an observing human are required. Do not replace them with
agents, invented answers, or fixture data.

## Build the moderated-test bundle

From the repository root on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  docs/experiments/learning-comparison/tools/build-bundle.ps1
```

Generated participant ZIPs and an observer ZIP are written under the ignored
`.tempo/experiments/learning-comparison/bundle/` directory. The two short video
clips are derived from the already verified feasibility proof and are not final
submission media.

## Run the five observations

Follow [`protocol.md`](protocol.md) exactly. Use the predetermined assignments
in [`assignments.csv`](assignments.csv), give each condition ZIP only when that
condition starts, and record one JSON observation per participant using
[`observation.example.json`](observation.example.json) as the shape.

Do not record names, email addresses, employers, repository credentials, or any
other identifying data. Use only participant IDs `P-001` through `P-005`.

## Compile real observations into TEMPO evidence

Place exactly five completed JSON records in an ignored directory, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  docs/experiments/learning-comparison/tools/compile-evidence.ps1 `
  -InputDirectory .tempo/experiments/learning-comparison/observations `
  -OutputDirectory .tempo/experiments/learning-comparison/evidence
```

The compiler fails closed if consent, unfamiliarity, source snapshot, assignment,
timing, answer, observer, or real-observation declarations are missing. It
calculates scores from the committed answer key and emits both supporting and
contradictory evidence. It never edits the decision brief or grants authority.

After human review, add every generated evidence item through TEMPO and rerun
readiness. Do not omit unfavorable participants:

```powershell
python bin/tempo evidence add --input <generated-evidence-file>
python bin/tempo evidence validate
python bin/tempo mvp assess
```

The fixture directory tests only the compiler mechanics. Fixture mode produces
no TEMPO evidence files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  docs/experiments/learning-comparison/tools/compile-evidence.ps1 `
  -InputDirectory docs/experiments/learning-comparison/fixtures `
  -OutputDirectory .tempo/experiments/learning-comparison/fixture-check `
  -FixtureMode
```
