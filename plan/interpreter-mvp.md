# Understand Video code-explainer MVP plan

Status: implementation proposal only. This document does not grant a warrant.

## Product outcome

Generate a concise, source-grounded video that helps a developer form a correct
high-level model of an unfamiliar repository. The first public-facing demo
explains `vemodalen-x/TEMPO` and shows a real local workflow, while keeping all
architectural claims linked to the pinned source revision.

The repository-owner reports that five developer text-versus-video comparisons
were completed and that the video was more reading-friendly. TEMPO records that
as useful indirect evidence, not direct observed behavior. The unsigned version
2 packet makes technical feasibility Rank 1 for the one-developer Stage A and
defers direct multi-developer learning measurement to Stage B. External
assessment `A-1806DDA390B2496D` passes that technical threshold, exposes the
media defects as contradictory evidence, but grants no
authority until the human-owned records are signed and a warrant is issued. The
founder's delivery self-check is never relabeled as learner evidence.

## MVP user path

1. Select a local repository and pin its revision.
2. Validate a pre-generated Understand-Anything graph against that exact
   revision, then select architecture claims with file/line provenance.
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

1. Validate the external TEMPO baseline, third governance root, warrant, and
   exact `mvp start` result through an adapter; do not import or vendor the
   framework source.
2. Add repository snapshot, pre-generated graph, and claim-to-source models.
3. Add storyboard generation and layout-safe scene contracts.
4. Integrate the approved narration provider behind a replaceable adapter.
5. Add sidecar-caption generation and optional dedicated-band burn-in.
6. Add the deterministic media verifier and receipt.
7. Render and verify the TEMPO explainer locally.
8. After MVP completion and a separate human distribution decision, run the
   multi-developer comparison and ingest every supporting and contradictory
   observation.
9. Reassess readiness before any upload or Devpost submission.

## Current blocks

- External assessment `A-1806DDA390B2496D` reports only an unsigned readiness
  policy and decision brief; its charter and warrant remain unsigned/missing.
- `H-LEARNING-001` still lacks direct observed measurements, so Stage A cannot
  claim learner value even if the technical MVP succeeds.
- The external TEMPO start gate reports `WARRANT_MISSING`.
- Upload and Devpost submission remain outside the proposed product scope.

Until the human-only authorization sequence completes, permitted work remains
limited to planning, documentation, fixtures, and evidence records.
