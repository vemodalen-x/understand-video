# Moderated comparison protocol

## Decision contract

- Rank-1 hypothesis: a developer obtains a correct high-level mental model of
  an unfamiliar repository faster from a concise source-linked video than from
  unguided file-by-file exploration.
- Threshold: at least 3 of 5 eligible observed comparisons are video wins.
- A video win requires all three conditions:
  1. video-condition score is at least 3 of 4;
  2. video-condition score is not lower than the participant's unguided score;
  3. total video-condition time is lower than unguided-condition time.
- Each condition has a hard cap of 360 seconds. Video playback time is included.
- A miss after five eligible observations triggers the declared pivot condition
  `LEARNING_ADVANTAGE_NOT_SUPPORTED`.

## Source and test boundary

- Repository: `Egonex-AI/Understand-Anything`.
- Exact source/graph commit: `58cfb20ac8f3f98cd7dede428d147dbe9cdc94b2`.
- The two modules cover different parts of the same graph mental model. Module
  assignment and condition order are counterbalanced to reduce, but not remove,
  module-difficulty and carryover effects.
- This is a small directional test. It cannot establish general learning impact
  or market demand.

## Participant eligibility

The observer must confirm all of the following before starting:

1. The participant works with software repositories or technical code artifacts.
2. The participant has not previously used or studied Understand-Anything.
3. The participant has not seen the proof video or experiment questions.
4. The participant agrees to an anonymous observation containing only answers,
   condition durations, and protocol flags.
5. The participant uses no AI assistant, search engine, or materials outside the
   supplied condition bundle.

If any item is false, do not record the participant as an eligible observation.

## Privacy and consent script

Read this text verbatim:

> This short test compares two ways of learning a codebase. We record only an
> opaque participant ID, multiple-choice answers, timing, and whether the test
> protocol was followed. We do not record your name, email, employer, audio,
> screen, or source credentials. You may stop at any time. Do you consent to
> continue?

Record only `consent_confirmed: true` or stop the session.

## Procedure

1. Assign the next unused ID from `P-001` through `P-005`; do not substitute or
   choose an assignment based on participant skill.
2. Confirm the assignment against `assignments.csv`.
3. Give the first condition ZIP only. Start the timer immediately before the
   participant opens its instructions.
4. The participant may inspect only supplied files. In a video condition, they
   may watch the clip once and may inspect its linked source extracts.
5. Stop timing when all four answers are submitted or at 360 seconds. Do not
   reveal correctness.
6. Take a two-minute neutral break. Do not discuss the repository.
7. Give the second condition ZIP and repeat the same timing procedure.
8. Record answers exactly as `A`, `B`, `C`, or `D`, duration to one decimal
   second, UTC capture time, and any protocol deviation.
9. If there was AI assistance, an assignment mismatch, a source mismatch, a
   timeout above 360 seconds, or any protocol deviation, do not alter the data;
   record it truthfully. The compiler will fail closed.
10. Never delete or withhold a valid observation because its result is
    unfavorable.

## Condition rules

### Video condition

- Start timing before opening `instructions.md`.
- Watch the supplied module clip once.
- Source extracts are available as traceability links and may be inspected.
- Answer the four module questions.

### Unguided condition

- Start timing before opening `instructions.md`.
- No narration or explanatory video is supplied.
- Explore the supplied source extracts and answer the four module questions.

## Deterministic scoring

The human observer records answers but does not assign scores. The evidence
compiler uses `answer-key.json` and calculates scores. It emits one immutable
evidence proposal per participant, with measurement value `1` for a video win
and `0` otherwise. Non-wins are contradictory evidence and must be preserved and
acknowledged in any later human decision brief.

Fixtures may test compiler mechanics but are always marked non-real and cannot
produce addable evidence.
