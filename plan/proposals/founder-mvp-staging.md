# Founder-MVP-first staging proposal

Status: draft proposal only. It does not amend the active policy, decision
brief, charter, task, warrant, or evidence threshold.

## Why split the work

The MVP currently has one developer. A one-person build is a reasonable way to
test whether the product can be delivered within a small technical budget. It
cannot establish whether other developers understand an unfamiliar repository
better from video than from source exploration: the builder knows the product,
has strong prior context, and is not an independent target user.

The correct revision is therefore **sequencing**, not replacing a five-person
learning test with a one-person claim.

| Stage | Who | Decision tested | Permitted evidence | Not established |
| --- | --- | --- | --- | --- |
| A — founder MVP | One named-but-not-public developer | Can a bounded, source-grounded explainer MVP be built and verified locally? | Technical benchmark and internal operational receipt | Learner value, demand, usability for others, market fit |
| B — post-MVP distribution | Five external developers, anonymously observed | Does the completed explainer improve correct orientation and time? | `observed_user_behavior` from `X-LEARNING-COMPARISON-001` | Population-level proof or permission to publish |

## Proposed Stage A contract

This contract should be materialized only through a new human-signed policy,
decision brief, charter, task, and short-lived warrant.

- **Decision:** whether to proceed from a one-person local founder build to
  external distribution testing.
- **Owner:** `human:repository-owner`.
- **Scope:** source snapshot, source-claim map, storyboard, approved voice
  sample, caption-safe scenes, local draft render, deterministic verification,
  and a local working-demo receipt.
- **Budget:** explicitly declare money, wall-clock time, render count, network
  services, and transmitted content before authorization.
- **Success:** a locally playable, source-grounded demo with naturalness and
  caption-layout human checkpoints plus machine media checks.
- **Stop conditions:** out-of-scope write, source-grounding failure, unsafe
  caption overlap, unapproved voice sample, missing receipt, budget/deadline
  overrun, secret/credential exposure, or any deployment/upload request.
- **Exclusions:** user-outcome claims, public release, upload, Devpost
  submission, and changing the human verdict.

Stage A evidence should use a different hypothesis from `H-LEARNING-001`, for
example: “One developer can produce and verify a source-grounded explainer for
a pinned repository within the declared founder-MVP budget.” A single passing
receipt is technical/operational evidence only.

## Proposed Stage B contract

After Stage A is complete, use
`docs/experiments/learning-comparison/observation-form.html` to collect five
external, anonymous observations. The existing compiler must receive exactly
five JSON records, preserve every non-win as contradictory evidence, and
generate the direct `observed_user_behavior` evidence. No observation form,
compiler output, or successful benchmark automatically authorizes publication
or a new build.

## Required human decision before this changes execution

The active policy currently marks `H-LEARNING-001` as Rank-1 and blocks an MVP
while `X-LEARNING-COMPARISON-001` is the cheaper sufficient experiment. A human
must explicitly choose one of these routes:

1. Keep the existing policy: run the five observations before product build.
2. Approve this staged policy: make the founder-MVP technical hypothesis Rank-1
   for a narrowly bounded Stage A warrant, and move the learning comparison to
   a required Stage B distribution decision.

For route 2, the human must update and sign the readiness policy and decision
brief, generate a new charter, reassess, and issue a scoped/budgeted/deadline-
bounded warrant interactively. An agent must not make or sign those changes on
the human's behalf.
