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

## Run the five post-MVP observations

Follow [`protocol.md`](protocol.md) exactly. Use the predetermined assignments
in [`assignments.csv`](assignments.csv), give each condition ZIP only when that
condition starts, and, after the MVP is distributed to external developers,
record one JSON observation per participant using
[`observation.example.json`](observation.example.json) as the shape.

### Use the local form instead of writing JSON by hand

Open [`observation-form.html`](observation-form.html) in a modern browser. It
is a standalone local page: it makes no network request, stores no identities,
and produces only the exact observation JSON consumed by the existing compiler.
It locks the committed counterbalanced assignment for each participant ID,
requires the protocol fields, records both conditions, and previews the exact
file before it is saved.

The right-hand media panel loads the verified local proof segment for the
participant's assigned video module. If the ignored local proof artifact is not
present, choose the `video.mp4` from that participant's extracted video-condition
bundle. Raw JSON and the five-observation compilation instructions are kept in
the collapsed **Developer debug data** disclosure rather than the participant's
primary workflow.

Only the participant's current condition is visible. The second condition is
locked until all four first-condition answers and its duration are complete.
For counterbalanced participants whose unguided condition is first, the media
panel explicitly withholds video until the video condition is unlocked.

In Chromium-based browsers, click **Save to observations folder** and choose
`.tempo/experiments/learning-comparison/observations/`. Otherwise click
**Download JSON** and move the downloaded `P-001.json` through `P-005.json`
files into that directory. The form allows a deviation or ineligible result to
be preserved truthfully, but marks it as non-compilable; it does not erase or
relabel unfavorable observations.

This is a **post-MVP learning validation**. One founder/developer building the
MVP must not use this form as a substitute for five independent developer
comparisons. The proposed staged route for a one-person founder MVP is recorded
in [`../../../plan/proposals/founder-mvp-staging.md`](../../../plan/proposals/founder-mvp-staging.md);
it becomes effective only after the required human-signed policy, decision
brief, charter, and warrant changes are valid.

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
