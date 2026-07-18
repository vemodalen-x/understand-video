# Founder-MVP-first staging proposal

Status: version 2 review packet prepared but unsigned. Matching draft policy,
decision brief, hypothesis set, charter, and task records now express this
proposal in the product provenance and the independent governance workspace.
They remain non-authoritative until a human signs and TEMPO issues a current
warrant.

## Why split the work

The MVP currently has one developer. A one-person build can test whether the
product can be delivered within a small technical budget. It cannot establish
whether independent developers understand an unfamiliar repository better from
video than from source exploration: the builder has privileged product and
repository context.

The revision is therefore sequencing, not replacing a five-person learning
test with a one-person user-value claim.

| Stage | Who | Decision tested | Permitted evidence | Not established |
| --- | --- | --- | --- | --- |
| A — founder MVP | One repository owner/developer | Can a bounded, source-grounded explainer be built and verified locally? | Technical benchmark, machine receipt, and explicit human media preview | Learner value, demand, independent usability, market fit |
| B — post-MVP distribution | Multiple external developers, anonymously observed; the initial protocol targets five | Does the completed explainer improve correct orientation and time? | `observed_user_behavior` from `X-LEARNING-COMPARISON-001` | Population-level proof or permission to publish |

## Proposed Stage A contract

This contract becomes active only through a new human-signed policy, decision
brief, charter, task, and short-lived warrant.

- **Decision:** whether to proceed from a one-person local founder build to
  external distribution testing.
- **Owner:** `human:repository-owner`.
- **Target:** explain TEMPO commit
  `4afc6a3f5ceba0240f7fdd2eece96241253d6e60` in a local, source-grounded,
  sub-three-minute video.
- **Scope:** repository snapshot, claim map, storyboard, fixture and approved
  narration adapters, caption-safe scenes, local render, deterministic
  verification, offline judge bundle, documentation, and local demo receipt.
- **Budget:** USD 25 maximum; no external speech or model call without a
  narrower declared provider, transmitted-content class, and cost approval.
- **Deadline:** 2026-07-21T08:00:00Z for the implementation warrant. Devpost's
  live submission deadline is 2026-07-22T00:00:00Z.
- **Success:** runnable offline demo, exact source references, duration below
  180 seconds, naturalness checkpoint, zero caption/content overlap, and a
  machine-readable receipt.
- **Stop conditions:** out-of-scope write, stale or dirty target revision,
  source-grounding failure, unsafe caption overlap, unapproved voice sample,
  missing receipt, budget/deadline overrun, secret exposure, or an upload.
- **Exclusions:** measured learning claims, public release, YouTube upload,
  Devpost submission, and any agent-authored human verdict.

The unsigned version 2 packet makes `H-FEASIBILITY-001` the sole Rank-1
implementation hypothesis. `H-LEARNING-001` moves to the Stage B distribution
decision without being declared satisfied.

## Proposed Stage B contract

After Stage A is complete, use
`docs/experiments/learning-comparison/observation-form.html` to collect five
external, anonymous observations. The compiler must receive exactly five JSON
records, preserve every non-win as contradictory evidence, and generate direct
`observed_user_behavior` proposals. No successful build, form, or compiler
output automatically authorizes distribution, publication, or a new build.

## Required human decision

External assessment `A-1806DDA390B2496D` (assessment hash
`sha256:3b72fb52bb8f0a2c2d050f5018e038f47273589eb8c96b1a14882a5aa0c86112`)
scores the unsigned version 2 packet at 82.3. Its exact product-provenance copy
is `plan/assessments/A-1806DDA390B2496D.json`. It exposes
`E-HUMAN-MEDIA-DEFECTS-001` as contradictory evidence,
passes the Rank-1 technical threshold, and reports no floor failures. Its only
blockers are the unsigned readiness policy and decision brief. A human must
explicitly choose one route:

1. Reject or revise the version 2 packet; no build starts.
2. Approve the staged policy and brief, sign the revised charter, reassess, and
   issue a scoped/budgeted/deadline-bounded Stage A warrant interactively.

The current request to resume development is strong decision context but is not
itself a TEMPO warrant. An agent must not populate signatures or issue the
warrant on the human's behalf.
