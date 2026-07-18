# Code-explainer MVP plan after the TEMPO iteration

Status: implementation proposal only. This document does not grant a warrant.

## Product outcome

Generate a concise, source-grounded video that helps a developer form a correct
high-level model of an unfamiliar repository. The first public-facing demo
explains `vemodalen-x/TEMPO` and shows a real local workflow, while keeping all
architectural claims linked to the pinned source revision.

The repository-owner reports that five developer text-versus-video comparisons
were completed and that the video was more reading-friendly. TEMPO records that
as useful indirect evidence. Under the current active policy, product
authorization still requires the five raw anonymous observations defined by
`X-LEARNING-COMPARISON-001`, or a human-signed decision that explicitly
acknowledges why the registered threshold was not met. The requested one-person
founder-MVP-first alternative is a separate, non-authoritative staging proposal
at `plan/proposals/founder-mvp-staging.md`; it does not relabel the founder's
delivery self-check as learner evidence.

## MVP user path

1. Select a local repository and pin its revision.
2. Extract a source graph and architecture claims with file/line provenance.
3. Produce a storyboard with a claim-to-source map.
4. Approve a short voice sample and representative caption-safe keyframes.
5. Render a draft with natural narration and SRT/VTT sidecars.
6. Run deterministic media, traceability, and duration verification.
7. Preview locally; publication and submission remain separate human actions.

## Product requirements

- **Grounded explanation:** every architecture claim maps to a pinned source
  location; unsupported claims fail the render.
- **Natural speech:** use an approved neural voice, reject clipping and obvious
  synthetic artifacts, and require a human voice-sample checkpoint.
- **Non-obstructive captions:** default to SRT/VTT sidecars. Burned captions are
  allowed only in a dedicated layout band that does not intersect diagrams or
  code regions.
- **Readable visuals:** diagrams and code use declared safe regions, minimum
  font sizes, restrained motion, and enough dwell time to read.
- **Review-friendly navigation:** chapters expose architecture, control flow,
  safety boundaries, working demo, and takeaway.
- **Devpost demo mode:** final duration under three minutes; show the working
  project; narration explains what was built and the roles of Codex and
  GPT-5.6. Public YouTube upload is a later human-authorized action.
- **Honest receipts:** fixture, local-integrity, human-preview, and external
  observation evidence remain visibly distinct.

## Acceptance checks

| Area | Deterministic check | Human checkpoint |
| --- | --- | --- |
| Source grounding | All claim references resolve at the pinned revision | Explanation matches reviewer mental model |
| Audio | Audio stream, loudness, peak, clipping, silence, and speech rate pass | Voice sounds natural and pronunciation is acceptable |
| Captions | SRT/VTT parse; cues stay within duration; safe-zone intersections are zero | Captions are easy to follow and never distract from diagrams |
| Visuals | Resolution, frame rate, minimum text size metadata, and dwell-time rules pass | Code and diagrams remain readable at normal playback |
| Demo | Receipt proves the captured command completed locally | The viewer can see the product working |
| Submission mode | Duration is below 180 seconds and required topics are present | Final narrative is coherent and credible |

## Implementation order after authorization

1. Consume the TEMPO experiment-spec and checkpoint API.
2. Add repository snapshot and claim-to-source models.
3. Add storyboard generation and layout-safe scene contracts.
4. Integrate the approved narration provider behind a replaceable adapter.
5. Add sidecar-caption generation and optional dedicated-band burn-in.
6. Add the deterministic media verifier and receipt.
7. Render the TEMPO explainer, then distribute it and run the five raw
   comparisons; ingest every supporting and contradictory observation.
8. Reassess readiness before any upload or Devpost submission.

## Current blocks

- `mvp assess` reports unsigned readiness policy and decision brief.
- `H-LEARNING-001` still lacks the registered direct observed measurements.
- The proposed one-person founder-MVP route has not been signed into the active
  policy, decision brief, charter, or warrant.
- `mvp start` reports `WARRANT_MISSING`.
- The active task excludes video upload and Devpost submission.

Until those blocks are resolved, permitted work is limited to planning,
documentation, fixtures, and evidence records.
