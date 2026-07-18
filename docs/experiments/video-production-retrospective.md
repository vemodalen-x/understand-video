# TEMPO experiment-lane retrospective

Status: proposal only; not an implemented TEMPO capability and not build authority.

Date: 2026-07-18

## Outcome

The current TEMPO kernel correctly prevented an aggregate preference report,
fixture output, and a successful local video render from authorizing product
implementation. That separation is valuable. The missing piece is a governed
middle lane between planning and product build: bounded experiments currently
need ad-hoc scripts and documentation even when their only purpose is to
collect decision evidence.

The repository-owner report that five comparisons were completed and that
video was more reading-friendly is retained as indirect supporting evidence.
It is not interchangeable with the registered experiment's five participant
records because the report does not contain correctness, completion time,
eligibility, consent, assignment, or contradictory observations.

## Problems found while producing the proof and demo videos

1. **No first-class experiment lifecycle.** `mvp assess` recommends the next
   experiment, but TEMPO has no deterministic `prepare -> approve -> start ->
   verify -> record -> close` state machine for evidence-only work.
2. **External constraints are not snapshotted.** Submission rules and tool
   requirements can change. A build should bind to a timestamped, untrusted
   constraint snapshot without allowing that snapshot to grant authority.
3. **Generic acceptance criteria miss media failures.** A decodable video can
   still have electronic-sounding speech, subtitles covering diagrams, weak
   source traceability, or excessive duration.
4. **Human preview checkpoints occur too late.** Voice, layout, and pacing
   should be reviewed independently before a full render spends its budget.
5. **Evidence ingestion is stronger than evidence collection.** The comparison
   compiler preserves raw outcomes and counterevidence, but TEMPO does not yet
   issue a bounded collection permit with privacy, cost, network, and path
   limits.
6. **Environment preflight is implicit.** Fonts, codecs, speech providers,
   browser/runtime dependencies, network needs, and output directories should
   fail before expensive work begins.

## Proposed TEMPO iteration: governed evidence-only experiments

Add an experiment object that is intentionally weaker than an MVP warrant. It
may authorize only declared evidence collection and fixture generation. It may
never authorize product implementation, deployment, publication, upload,
human signing, or modification of protected decision history.

Proposed lifecycle:

1. `tempo experiment prepare --spec <path>` validates the proposal and pins
   referenced hypotheses, source revisions, constraints, checks, and budgets.
2. `tempo experiment approve --signer <human>` requires an interactive human
   confirmation and writes a hash-bound, short-lived experiment permit.
3. `tempo experiment start --task <id> --path <path>` verifies permit, scope,
   deadline, cost, data class, network policy, and tool declarations.
4. `tempo experiment checkpoint --stage <name>` records machine checks and an
   optional human preview decision without filling any MVP verdict.
5. `tempo experiment record --input <observation>` preserves supporting and
   contradictory observations with provenance.
6. `tempo experiment close` verifies cleanup and emits a receipt; readiness
   must still be reassessed separately.

Required controls:

- hypothesis and proposed-action references;
- allowed and forbidden paths and actions;
- wall-clock, money, render-count, and network budgets;
- declared services and exact classes of transmitted content;
- source revision and external-constraint snapshots;
- participant privacy fields and retention policy when people are observed;
- ordered preview checkpoints and deterministic machine checks;
- explicit counterevidence retention;
- stop conditions and cleanup steps;
- a statement that experiment approval is not product build authority.

## Media verification adapter

The first adapter should combine deterministic checks with explicit human
preview fields:

- container, codec, resolution, duration, frame rate, and audio-stream checks;
- integrated loudness, true peak, clipping, silence, and speech-rate checks;
- caption sidecar parseability, cue timing, line length, and safe-zone checks;
- layout metadata proving captions do not overlap declared diagram/code regions;
- storyboard-to-transcript topic coverage and source-reference coverage;
- a machine receipt showing a working local demo was captured;
- human checkpoints for voice naturalness, pronunciation, visual hierarchy,
  readability, and pacing.

For the current product, captions should be sidecars by default. If burned-in
captions are requested, the renderer must reserve a dedicated lower band or
relayout content; it must never place captions over diagrams or source code.
Voice approval should use a 10-15 second sample before full narration.

## Checkpoint order for video experiments

1. Environment and source-revision preflight.
2. Voice A/B samples, including the intended final sentence style.
3. Storyboard and source-link review.
4. Representative keyframes with caption safe zones visible.
5. Low-resolution full draft with sidecar captions.
6. Final render and machine verification.
7. Human publication decision, which remains outside the experiment permit.

## Minimum implementation slice after a valid MVP warrant

The smallest framework increment should contain:

- an experiment-spec schema and one non-authoritative fixture;
- a deterministic lifecycle and hash-bound experiment permit;
- path, action, time, cost, network, and data-transmission guards;
- external-constraint snapshot hashing;
- the media verification adapter and machine receipt;
- conformance tests proving experiment authority cannot start product writes,
  deployment, upload, publication, or human-only decisions;
- one credential-free CLI demo.

No framework code may be written until a current, scoped, budgeted, and
deadline-bounded MVP warrant passes `tempo mvp start`.
